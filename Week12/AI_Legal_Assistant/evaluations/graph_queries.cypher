// Day 3: example Cypher queries on the legal knowledge graph (schema: docs/graph_schema.md).
// Run in the Neo4j / AuraDB browser after `python -m src.graph.load_neo4j`.

// 1. Most important precedents by PageRank (computed with networkx at load time)
MATCH (c:Case) WHERE c.cited_by > 0
RETURN c.name AS case, c.cited_by AS cited_by, c.pagerank AS pagerank
ORDER BY c.pagerank DESC LIMIT 10;

// 2. Which judgments refer to or interpret a provision of the Contract Act, 1872?
MATCH (c:Case)-[r:REFERS_TO|INTERPRETS]->(s:Section)-[:PART_OF]->(a:Act)
WHERE a.name STARTS WITH 'Contract Act'
RETURN c.name AS judgment, c.court AS court, s.label AS provision, type(r) AS relation, r.paragraph AS para, r.page AS page;

// 3. Supreme Court judgments that interpreted Section 23 of the Contract Act, and whether any was later overruled
MATCH (c:Case {court: 'Supreme Court of Pakistan'})-[:INTERPRETS|REFERS_TO]->(:Section {label: 'Section 23'})-[:PART_OF]->(a:Act)
WHERE a.name STARTS WITH 'Contract Act'
OPTIONAL MATCH (later:Case)-[o:OVERRULES]->(c)
RETURN c.name AS judgment, later.name AS overruled_by, o.needs_check AS unverified;

// 4. Overruling candidates found by regex (to be checked by the LLM step)
MATCH (a:Case)-[r:OVERRULES]->(b:Case)
RETURN a.name AS citing, b.name AS cited, r.sentence AS evidence, r.needs_check AS needs_check;

// 5. Precedents a judgment relies on (FOLLOWS) and the provisions it applies
MATCH (c:Case {document_id: 'SC_c.a._333_2024_23092024_hj3'})
OPTIONAL MATCH (c)-[:FOLLOWS]->(p:Case)
OPTIONAL MATCH (c)-[:REFERS_TO]->(s:Section)
RETURN c.name, collect(DISTINCT p.name) AS relies_on, collect(DISTINCT s.label) AS provisions;

// 6. Judges who sat together most often
MATCH (j1:Judge)-[:SAT_ON]->(c:Case)<-[:SAT_ON]-(j2:Judge) WHERE j1.key < j2.key
RETURN j1.name, j2.name, count(c) AS cases ORDER BY cases DESC LIMIT 10;

// 7. Most referenced provisions per court
MATCH (c:Case)-[:REFERS_TO|INTERPRETS]->(s:Section)-[:PART_OF]->(a:Act)
RETURN c.court AS court, a.name AS act, s.label AS provision, count(DISTINCT c) AS judgments
ORDER BY judgments DESC LIMIT 15;

// 8. Visualise one judgment's neighbourhood (open the graph view in the browser)
MATCH p = (c:Case {document_id: 'SC_c.a._140_k_2016'})-[*1..2]-() RETURN p LIMIT 80;
