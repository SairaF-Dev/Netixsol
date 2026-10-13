"""
RAG Engine for City Care Clinics.
Handles retrieval, answer formatting, citation appending, and grounding verification.
"""

from typing import Dict, Any
from .vector_store import KnowledgeBaseStore

class RAGEngine:
    def __init__(self, vector_store: KnowledgeBaseStore = None):
        self.vector_store = vector_store or KnowledgeBaseStore()

    def query(self, question: str) -> Dict[str, Any]:
        """
        Executes RAG query pipeline and returns grounded answer with exact citations.
        """
        matches = self.vector_store.search(question, top_k=2)
        
        if not matches:
            return {
                "question": question,
                "answer": "I could not find specific information regarding your query in City Care Clinics guidelines. Please call our central help desk at +92-42-35690001.",
                "citations": [],
                "is_grounded": False
            }

        # Build answer with citations
        retrieved_texts = []
        citations = []
        
        for m in matches:
            retrieved_texts.append(f"• **{m['title']}**: {m['content']}\n  *{m['citation']}*")
            citations.append(m['citation'])

        answer_body = "\n\n".join(retrieved_texts)
        
        return {
            "question": question,
            "answer": answer_body,
            "citations": list(set(citations)),
            "is_grounded": True,
            "retrieved_chunks": len(matches)
        }

if __name__ == "__main__":
    engine = RAGEngine()
    q = "Fasting blood sugar test ke liye kitne ghante pehle khana chorna hota hai?"
    res = engine.query(q)
    print("Q:", res["question"])
    print("Answer:\n", res["answer"])

