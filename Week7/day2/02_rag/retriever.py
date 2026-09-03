from __future__ import annotations
import os
from chunker import chunk_documents
from embeddings import LocalEmbedding
from loader import load_documents
from metadata import get_metadata
from vector_store import ChromaVectorStore

class Retriever:
    def __init__(self,documents_dir='documents',persist_directory='chroma_db',collection_name=None,chunk_size=None,overlap_sentences=None,distance_threshold=None,verbose=False):
        self.documents_dir=documents_dir
        self.distance_threshold=float(distance_threshold if distance_threshold is not None else os.getenv('RAG_DISTANCE_THRESHOLD','0.50'))
        self.chunk_size=int(chunk_size or os.getenv('RAG_CHUNK_SIZE','512'))
        self.overlap_sentences=int(overlap_sentences if overlap_sentences is not None else os.getenv('RAG_OVERLAP_SENTENCES','1'))
        collection_name=collection_name or os.getenv('RAG_COLLECTION','real_estate_knowledge_v3')
        self.verbose=verbose
        self.embedder=LocalEmbedding()
        self.store=ChromaVectorStore(self.embedder,persist_directory,collection_name)
        self.index_stats=self._build_index()
    def _build_index(self):
        docs=load_documents(self.documents_dir)
        if not docs: raise ValueError(f'No documents found in: {self.documents_dir}')
        chunks=chunk_documents(docs,self.chunk_size,self.overlap_sentences)
        if not chunks: raise ValueError('No chunks were created.')
        for c in chunks: c.update(get_metadata(c['source']))
        result=self.store.sync_documents(chunks)
        stats={'documents':len(docs),'chunks':len(chunks),'total_chunks':self.store.count(),**result}
        if self.verbose: print(stats)
        return stats
    def retrieve(self,query,top_k=4,document_type=None):
        filt={'document_type':document_type} if document_type else None
        return self.store.search(query,top_k,self.distance_threshold,filt)
