"""
Document Loader — Task 2, RAG Pipeline (step 1/5)

Loads unstructured/semi-structured content (FAQs, brochures) into a
common Document format: {id, source, text, metadata}.

Structured tables (prices, availability) are NOT loaded here — those
go through retrieval/structured_retrieval.py instead (see docs/ for the
justification of this split).
"""
import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


class Document:
    def __init__(self, doc_id, source, text, metadata=None):
        self.doc_id = doc_id
        self.source = source
        self.text = text
        self.metadata = metadata or {}

    def __repr__(self):
        return f"Document(id={self.doc_id}, source={self.source}, len={len(self.text)})"


def load_faqs():
    path = os.path.join(DATA_DIR, "faqs.json")
    with open(path, encoding="utf-8") as f:
        faqs = json.load(f)
    docs = []
    for faq in faqs:
        text = f"Q: {faq['question']}\nA: {faq['answer']}"
        docs.append(Document(
            doc_id=faq["id"],
            source="faqs",
            text=text,
            metadata={"category": faq["category"]},
        ))
    return docs


def load_brochures():
    path = os.path.join(DATA_DIR, "brochures.json")
    with open(path, encoding="utf-8") as f:
        brochures = json.load(f)
    docs = []
    for b in brochures:
        docs.append(Document(
            doc_id=f"brochure_{b['property_id']}",
            source="brochures",
            text=b["brochure_text"],
            metadata={"property_id": b["property_id"]},
        ))
    return docs


def load_all_documents():
    return load_faqs() + load_brochures()


if __name__ == "__main__":
    docs = load_all_documents()
    print(f"Loaded {len(docs)} documents")
    for d in docs[:3]:
        print(d)
