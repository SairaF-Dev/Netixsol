"""Concept graph: load concepts.yaml, validate it, order it, and draw it.

Edge direction: prerequisite -> concept ("learn A before B").

Run:  python -m ilm.graph.concept_graph      (validate + write reports + HTML/PNG)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import networkx as nx
import yaml

from ilm import config
from ilm.content.download import all_lessons

CONCEPTS_FILE = Path(__file__).with_name("concepts.yaml")


@dataclass
class Validation:
    errors: list[str] = field(default_factory=list)    # must be fixed: graph unusable
    warnings: list[str] = field(default_factory=list)  # should be looked at

    @property
    def ok(self) -> bool:
        return not self.errors


def load_concepts(path: Path = CONCEPTS_FILE) -> list[dict]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["concepts"]


def build_graph(concepts: list[dict]) -> nx.DiGraph:
    """Prerequisite edges only. Unknown ids are added as nodes so validate() can report them."""
    g = nx.DiGraph()
    for c in concepts:
        g.add_node(c["id"], name=c["name"], taught_in=c.get("taught_in", []),
                   related=c.get("related", []))
    for c in concepts:
        for p in c.get("prereqs", []):
            g.add_edge(p, c["id"])
    return g


def validate(concepts: list[dict], lesson_ids: set[str]) -> Validation:
    v = Validation()
    ids = [c["id"] for c in concepts]
    known = set(ids)

    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        v.errors.append(f"duplicate concept ids: {dupes}")

    for c in concepts:
        for kind in ("prereqs", "related"):
            for ref in c.get(kind, []):
                if ref not in known:
                    v.errors.append(f"{c['id']}: {kind} refers to unknown concept '{ref}'")
                if ref == c["id"]:
                    v.errors.append(f"{c['id']}: lists itself in {kind}")
        overlap = set(c.get("prereqs", [])) & set(c.get("related", []))
        if overlap:
            v.errors.append(f"{c['id']}: {sorted(overlap)} is both prereq and related")
        for lesson in c.get("taught_in", []):
            if lesson not in lesson_ids:
                v.errors.append(f"{c['id']}: taught_in unknown lesson '{lesson}'")
        if not c.get("taught_in"):
            v.warnings.append(f"coverage gap: '{c['id']}' is not taught in any lesson")

    g = build_graph(concepts)
    if not nx.is_directed_acyclic_graph(g):
        # report one concrete cycle so a human can see where to cut it
        cycle = nx.find_cycle(g)
        v.errors.append("cycle: " + " -> ".join([a for a, _ in cycle] + [cycle[0][0]]))
        return v  # the checks below need a DAG

    # Redundant edge A->C when C is reachable from A another way (A->B->...->C).
    # It is not wrong, but it hides structure and makes the drawing noisy.
    reduced = nx.transitive_reduction(g)
    for a, c in sorted(set(g.edges) - set(reduced.edges)):
        v.warnings.append(f"redundant prereq: {c} <- {a} (already implied through another path)")

    roots = [n for n in g if g.in_degree(n) == 0]
    if len(roots) != 1:
        v.warnings.append(f"expected one starting concept, found {len(roots)}: {roots}")
    return v


def depth_levels(g: nx.DiGraph) -> dict[str, int]:
    """Level = length of the longest prerequisite chain leading to the concept."""
    level: dict[str, int] = {}
    for n in nx.topological_sort(g):
        level[n] = max((level[p] + 1 for p in g.predecessors(n)), default=0)
    return level


def learning_order(g: nx.DiGraph, lesson_rank: dict[str, int]) -> list[str]:
    """A valid study order; ties broken by the lesson that teaches the concept first,
    so the order follows the course where the graph allows it."""
    def key(n: str) -> tuple:
        lessons = g.nodes[n]["taught_in"]
        return (min((lesson_rank[l] for l in lessons), default=99), n)
    return list(nx.lexicographical_topological_sort(g, key=key))


def summary(g: nx.DiGraph, concepts: list[dict], v: Validation, lesson_rank: dict[str, int]) -> dict:
    level = depth_levels(g)
    deepest = max(level, key=level.get)
    chain = nx.dag_longest_path(g)
    return {
        "concepts": g.number_of_nodes(),
        "prerequisite_edges": g.number_of_edges(),
        "related_links": sum(len(c.get("related", [])) for c in concepts),
        "is_dag": nx.is_directed_acyclic_graph(g),
        "levels": max(level.values()) + 1,
        "longest_chain": chain,
        "deepest_concept": deepest,
        "most_depended_on": sorted(((len(nx.descendants(g, n)), n) for n in g), reverse=True)[:5],
        "coverage_gaps": [n for n in g if not g.nodes[n]["taught_in"]],
        "errors": v.errors,
        "warnings": v.warnings,
        "learning_order": learning_order(g, lesson_rank),
    }


def layered_positions(g: nx.DiGraph, sweeps: int = 4) -> dict[str, tuple[float, float]]:
    """x = prerequisite depth; y order inside a column by the barycenter heuristic:
    each node sits at the average height of its neighbours in the previous column,
    which pulls connected nodes together and cuts edge crossings."""
    level = depth_levels(g)
    columns: dict[int, list[str]] = {}
    for n in sorted(g):
        columns.setdefault(level[n], []).append(n)
    rank = {n: i for col in columns.values() for i, n in enumerate(col)}

    def reorder(col: list[str], neighbours) -> list[str]:
        def bary(n: str) -> float:
            nb = [rank[m] for m in neighbours(n)]
            return sum(nb) / len(nb) if nb else rank[n]
        return sorted(col, key=bary)

    for _ in range(sweeps):  # alternate left->right and right->left passes
        for lv in sorted(columns)[1:]:
            columns[lv] = reorder(columns[lv], g.predecessors)
            rank.update({n: i for i, n in enumerate(columns[lv])})
        for lv in sorted(columns)[:-1][::-1]:
            columns[lv] = reorder(columns[lv], g.successors)
            rank.update({n: i for i, n in enumerate(columns[lv])})

    pos = {}
    for lv, col in columns.items():
        for i, n in enumerate(col):  # centre each column vertically
            pos[n] = (lv, (len(col) - 1) / 2 - i)
    return pos


def count_crossings(g: nx.DiGraph, pos: dict) -> int:
    """Number of crossing edge pairs between adjacent-or-further columns (lower is clearer)."""
    edges = [(pos[a], pos[b]) for a, b in g.edges]
    def ccw(p, q, r):
        return (r[1] - p[1]) * (q[0] - p[0]) > (q[1] - p[1]) * (r[0] - p[0])
    crossings = 0
    for i in range(len(edges)):
        for j in range(i + 1, len(edges)):
            (p1, p2), (p3, p4) = edges[i], edges[j]
            if len({p1, p2, p3, p4}) < 4:
                continue  # edges sharing a node don't count
            if ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4):
                crossings += 1
    return crossings


def draw_png(g: nx.DiGraph, path: Path) -> None:
    """Layered static picture: one column per level, prerequisites on the left."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    pos = layered_positions(g)
    lessons = [g.nodes[n]["taught_in"][0] if g.nodes[n]["taught_in"] else None for n in g]
    # Gap colour must not appear in the lesson palette (tab10 has red for lesson 3,
    # which made "try/except" look like an untaught concept).
    gap_color = "black"
    palette = {l: plt.cm.tab10(i % 10) for i, l in enumerate(sorted({l for l in lessons if l}))}
    colors = [palette[l] if l else gap_color for l in lessons]

    fig, ax = plt.subplots(figsize=(24, 15))
    nx.draw_networkx_edges(g, pos, ax=ax, edge_color="#9aa0a6", arrows=True, arrowsize=8, width=0.8,
                           connectionstyle="arc3,rad=0.05")
    nx.draw_networkx_nodes(g, pos, ax=ax, node_color=colors, node_size=380)
    nx.draw_networkx_labels(g, {n: (x, y + 0.38) for n, (x, y) in pos.items()},  # 1 row = 1.0
                            labels={n: g.nodes[n]["name"] for n in g}, font_size=7, ax=ax)
    handles = [plt.Line2D([], [], marker="o", ls="", color=c, label=l) for l, c in palette.items()]
    handles.append(plt.Line2D([], [], marker="o", ls="", color=gap_color, label="no lesson (gap)"))
    ax.legend(handles=handles, loc="lower right", title="first taught in")
    ax.set_title("Python concept graph: arrow = 'learn first'; columns = prerequisite depth")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def draw_html(g: nx.DiGraph, path: Path) -> None:
    """Interactive graph: hover a node to see its lessons; drag to explore."""
    from pyvis.network import Network

    level = depth_levels(g)
    net = Network(height="800px", width="100%", directed=True, cdn_resources="in_line")
    net.set_options('{"layout": {"hierarchical": {"enabled": true, "direction": "LR",'
                    ' "sortMethod": "directed", "levelSeparation": 170}},'
                    ' "physics": {"enabled": false}}')
    for n in g:
        lessons = g.nodes[n]["taught_in"]
        net.add_node(n, label=g.nodes[n]["name"], level=level[n],
                     title=f"{n}\nlessons: {', '.join(lessons) or 'NONE (gap)'}",
                     color="#e57373" if not lessons else None)
    for a, b in g.edges:
        net.add_edge(a, b)
    path.write_text(net.generate_html(), encoding="utf-8")


def main() -> int:
    lesson_rank = {l["id"]: l["order"] for l in all_lessons()}
    concepts = load_concepts()
    v = validate(concepts, set(lesson_rank))
    for e in v.errors:
        print("ERROR  ", e)
    for w in v.warnings:
        print("WARNING", w)
    if not v.ok:
        print("Graph has errors; fix concepts.yaml first.")
        return 1

    g = build_graph(concepts)
    s = summary(g, concepts, v, lesson_rank)
    out = config.REPORTS_DIR / "concept_graph"
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(s, indent=1), encoding="utf-8")
    draw_png(g, out / "concept_graph.png")
    draw_html(g, out / "concept_graph.html")
    print(f"{s['concepts']} concepts, {s['prerequisite_edges']} prerequisite edges, "
          f"{s['related_links']} related links, DAG={s['is_dag']}, {s['levels']} levels")
    print("longest chain:", " -> ".join(s["longest_chain"]))
    print("most depended on:", s["most_depended_on"])
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
