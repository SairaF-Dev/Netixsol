"""
Retriever — Task 2, RAG Pipeline (step 4b/5)

Wraps an embedder + vector store into a single retrieve(query) call.
This is the SEMANTIC half of the structured/semantic split (Task 3) —
used for brochures, descriptions, FAQs. Prices/availability/plot size/
agent names go through retrieval/structured_retrieval.py instead.
"""


class Retriever:
    def __init__(self, embedder, vector_store):
        self.embedder = embedder
        self.vector_store = vector_store

    def retrieve(self, query, top_k=3, metadata_filter=None):
        query_vector = self.embedder.embed(query)
        results = self.vector_store.search(query_vector, top_k=top_k, metadata_filter=metadata_filter)
        return results
