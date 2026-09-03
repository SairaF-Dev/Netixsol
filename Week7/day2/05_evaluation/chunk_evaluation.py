from __future__ import annotations
import shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent; RAG=ROOT/'02_rag'; sys.path.insert(0,str(RAG))
from loader import load_documents
from chunker import chunk_documents
from embeddings import LocalEmbedding
from vector_store import ChromaVectorStore
QUESTIONS=[('How does property search work?','real_estate_faq.md'),('Tell me about Horizon Heights Apartment.','horizon_heights_apartment.md'),('Give me an overview of Park View Residences.','park_view_residences.md'),('Tell me about Bahria Grand Apartments.','bahria_grand_apartments.md')]
def evaluate(size):
    docs=load_documents(RAG/'documents'); chunks=chunk_documents(docs,chunk_size=size,overlap_sentences=1); embedder=LocalEmbedding(); persist=Path(__file__).parent/f'evaluation_chroma_{size}'
    if persist.exists(): shutil.rmtree(persist)
    store=ChromaVectorStore(embedder,str(persist),f'evaluation_{size}'); store.sync_documents(chunks); hits=0
    for q,src in QUESTIONS:
        results=store.search(q,top_k=3,distance_threshold=0.60); hits+=int(any(Path(r['source']).name==src for r in results))
    shutil.rmtree(persist,ignore_errors=True)
    return {'chunk_size':size,'chunks':len(chunks),'questions':len(QUESTIONS),'top3_source_hit_rate':hits/len(QUESTIONS)}
if __name__=='__main__':
    for s in (256,512,1024): print(evaluate(s))
