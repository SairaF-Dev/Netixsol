"""
Day 3, Task 3: load the knowledge graph (data/graph/*.csv) into Neo4j and add PageRank.

* The database is cleared first, so the load can be re-run after re-extraction.
* One uniqueness constraint per label on `key`.
* Nodes and relationships are written in batches of 1,000 with UNWIND.
* PageRank over the precedent graph (CITES / FOLLOWS / DISTINGUISHES / OVERRULES between
  cases) is computed once with networkx and stored on each Case as `pagerank`, together
  with `cited_by` (number of citing judgments). AuraDB Free has no Graph Data Science
  library, and the score only changes when the graph is rebuilt.

Run:  python -m src.graph.load_neo4j        (first: python -m src.graph.regex_extract)
"""

import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import networkx as nx

from src.graph.neo4j_client import database, get_driver
from src.utils.logger import setup_logger

logger = setup_logger("load_neo4j")

GRAPH_DIR = Path("data/graph")
BATCH = 1000
PRECEDENT_TYPES = ("CITES", "FOLLOWS", "DISTINGUISHES", "OVERRULES")
_INT = {"year", "page"}
_BOOL = {"in_corpus", "needs_check"}


def _clean(row: Dict[str, str]) -> Dict:
    out = {}
    for key, value in row.items():
        if value in ("", None):
            continue
        if key in _BOOL:
            out[key] = value == "True"
        elif key in _INT:
            try:
                out[key] = int(float(value))
            except ValueError:
                out[key] = value
        else:
            out[key] = value
    return out


def _read(path: Path) -> List[Dict]:
    with path.open(encoding="utf-8") as handle:
        return [_clean(row) for row in csv.DictReader(handle)]


def _batches(rows: List[Dict]):
    for start in range(0, len(rows), BATCH):
        yield rows[start:start + BATCH]


def load() -> Dict[str, int]:
    nodes = {path.stem.removeprefix("nodes_").capitalize(): _read(path) for path in sorted(GRAPH_DIR.glob("nodes_*.csv"))}
    label_of = {row["key"]: label for label, rows in nodes.items() for row in rows}
    edges = {path.stem.removeprefix("edges_").upper(): _read(path) for path in sorted(GRAPH_DIR.glob("edges_*.csv"))}

    # PageRank on the precedent graph.
    precedent = nx.DiGraph()
    precedent.add_nodes_from(row["key"] for row in nodes.get("Case", []))
    for edge_type in PRECEDENT_TYPES:
        for edge in edges.get(edge_type, []):
            precedent.add_edge(edge["src"], edge["dst"])
    pagerank = nx.pagerank(precedent, alpha=0.85)
    cited_by = {key: len({src for src in precedent.predecessors(key)}) for key in precedent.nodes}
    for row in nodes.get("Case", []):
        row["pagerank"] = round(pagerank.get(row["key"], 0.0), 8)
        row["cited_by"] = cited_by.get(row["key"], 0)

    counts = {}
    with get_driver() as driver, driver.session(database=database()) as session:
        session.run("MATCH (n) CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 5000 ROWS").consume()
        for label in nodes:
            session.run(f"CREATE CONSTRAINT {label.lower()}_key IF NOT EXISTS FOR (n:{label}) REQUIRE n.key IS UNIQUE").consume()
        for label, rows in nodes.items():
            for batch in _batches(rows):
                session.run(f"UNWIND $rows AS row CREATE (n:{label}) SET n = row", rows=batch).consume()
            counts[label] = len(rows)
            logger.info("Loaded %d %s nodes", len(rows), label)

        for edge_type, rows in edges.items():
            grouped = defaultdict(list)
            for row in rows:
                src_label, dst_label = label_of.get(row["src"]), label_of.get(row["dst"])
                if src_label and dst_label:
                    props = {k: v for k, v in row.items() if k not in ("src", "dst")}
                    grouped[(src_label, dst_label)].append({"src": row["src"], "dst": row["dst"], "props": props})
            for (src_label, dst_label), group in grouped.items():
                for batch in _batches(group):
                    session.run(f"UNWIND $rows AS row MATCH (a:{src_label} {{key: row.src}}) MATCH (b:{dst_label} {{key: row.dst}}) "
                                f"CREATE (a)-[r:{edge_type}]->(b) SET r = row.props", rows=batch).consume()
            counts[edge_type] = sum(len(g) for g in grouped.values())
            logger.info("Loaded %d %s relationships", counts[edge_type], edge_type)
    return counts


if __name__ == "__main__":
    for name, count in load().items():
        print(f"{name:15} {count}")
