"""
Knowledge Base Chunker and Vector Store Indexer for City Care Clinics.
Indexes Markdown documents into searchable chunks with rich metadata.
"""

import os
import re
import math
from typing import List, Dict, Any

KB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "knowledge_base")

class DocumentChunk:
    def __init__(self, doc_name: str, title: str, content: str, source_citation: str):
        self.doc_name = doc_name
        self.title = title
        self.content = content
        self.source_citation = source_citation

    def __repr__(self):
        return f"<DocumentChunk doc={self.doc_name} title='{self.title}'>"

class KnowledgeBaseStore:
    def __init__(self, kb_dir: str = KB_DIR):
        self.kb_dir = kb_dir
        self.chunks: List[DocumentChunk] = []
        self._load_and_chunk_documents()

    def _load_and_chunk_documents(self):
        if not os.path.exists(self.kb_dir):
            return

        for filename in os.listdir(self.kb_dir):
            if filename.endswith(".md"):
                filepath = os.path.join(self.kb_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    text = f.read()

                # Split by markdown headers (## )
                sections = re.split(r'\n(?=##\s)', text)
                doc_title = sections[0].strip().split("\n")[0].replace("#", "").strip() if sections else filename

                for sec in sections:
                    lines = sec.strip().split("\n")
                    if not lines:
                        continue
                    header = lines[0].replace("#", "").strip()
                    content = "\n".join(lines[1:]).strip() if len(lines) > 1 else lines[0]
                    
                    if content:
                        citation = f"[Source: {doc_title} - {header}]"
                        self.chunks.append(DocumentChunk(
                            doc_name=filename,
                            title=header,
                            content=content,
                            source_citation=citation
                        ))

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Simple BM25 / TF-IDF style keyword search over knowledge chunks.
        """
        # UrduLish to English medical synonym mapping
        SYNONYMS = {
            "gala": "throat", "kaan": "ear", "bache": "infant child pediatric paediatric",
            "bukhar": "fever", "khansi": "cough", "pait": "stomach abdomen abdominal",
            "parda": "ear", "period": "menstrual pregnancy gynaecology", "chehra": "face facial stroke",
            "dawai": "medicine medication", "sugar": "glucose diabetes", "namak": "salt sodium"
        }

        query_lower = query.lower()
        expanded_query = query_lower
        for u_term, e_terms in SYNONYMS.items():
            if u_term in query_lower:
                expanded_query += " " + e_terms

        query_words = set(re.findall(r'\w+', expanded_query))
        results = []

        for chunk in self.chunks:
            chunk_text = (chunk.title + " " + chunk.content).lower()
            chunk_words = re.findall(r'\w+', chunk_text)
            
            score = 0
            for qw in query_words:
                if len(qw) > 2:
                    count = chunk_words.count(qw)
                    if count > 0:
                        score += (1 + math.log(count))

            if score > 0:
                results.append({
                    "chunk": chunk,
                    "score": score,
                    "citation": chunk.source_citation,
                    "content": chunk.content,
                    "title": chunk.title
                })

        # Sort by relevance score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

if __name__ == "__main__":
    kb = KnowledgeBaseStore()
    print(f"Loaded {len(kb.chunks)} knowledge base chunks.")
    sample_search = kb.search("fasting blood test glucose")
    for r in sample_search:
        print(f"Match: {r['title']} | Citation: {r['citation']}")
