from pathlib import Path

import chromadb

from loader import load_documents
from chunker import chunk_documents
from embeddings import LocalEmbedding


class Retriever:
    """
    Semantic retriever using Sentence Transformers + ChromaDB.
    """

    def __init__(
        self,
        documents_dir="documents",
        persist_directory="chroma_db",
        collection_name="real_estate_knowledge",
        chunk_size=512,
        overlap_sentences=1,
    ):
        self.documents_dir = documents_dir
        self.persist_directory = persist_directory
        self.collection_name = collection_name

        # Load embedding model once.
        self.embedder = LocalEmbedding()

        # Initialize persistent ChromaDB client.
        self.client = chromadb.PersistentClient(
            path=persist_directory
        )

        # Create or reuse collection.
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        # Build knowledge base.
        self._build_index(
            chunk_size=chunk_size,
            overlap_sentences=overlap_sentences,
        )

    def _build_index(self, chunk_size, overlap_sentences):
        """
        Load, chunk and index documents into ChromaDB.
        """

        documents = load_documents(self.documents_dir)

        if not documents:
            raise ValueError(
                f"No documents found in: {self.documents_dir}"
            )

        chunks = chunk_documents(
            documents,
            chunk_size=chunk_size,
            overlap_sentences=overlap_sentences,
        )

        if not chunks:
            raise ValueError("No chunks were created.")

        ids = []
        texts = []
        embeddings = []
        metadatas = []

        for chunk in chunks:

            chunk_id = (
                f"{Path(chunk['source']).name}"
                f"__chunk_{chunk['chunk_id']}"
            )

            ids.append(chunk_id)
            texts.append(chunk["text"])

            embeddings.append(
                self.embedder.embed(chunk["text"])
            )

            metadatas.append(
                {
                    "source": chunk["source"],
                    "chunk_id": chunk["chunk_id"],
                }
            )

        # Replace existing collection contents to avoid duplicates.
        existing = self.collection.get()

        if existing["ids"]:
            self.collection.delete(ids=existing["ids"])

        self.collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        print(f"Loaded documents: {len(documents)}")
        print(f"Created chunks: {len(chunks)}")
        print(f"Indexed chunks: {len(ids)}")

    def retrieve(self, query: str, top_k=4, distance_threshold=0.56):
        """
        Retrieve semantically relevant chunks.

        Only chunks within the allowed cosine-distance threshold
        are returned. This prevents weak/irrelevant matches from
        entering the RAG context.
        """

        if not isinstance(query, str):
            raise TypeError("query must be a string")

        if not query.strip():
            raise ValueError("query cannot be empty")

        if top_k <= 0:
            raise ValueError("top_k must be greater than 0")

        if distance_threshold < 0:
            raise ValueError("distance_threshold cannot be negative")

        query_embedding = self.embedder.embed(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        output = []

        for i in range(len(results["documents"][0])):

            distance = results["distances"][0][i]

            # Reject weak semantic matches
            if distance > distance_threshold:
                continue

            output.append(
                {
                    "text": results["documents"][0][i],
                    "source": results["metadatas"][0][i]["source"],
                    "chunk_id": results["metadatas"][0][i]["chunk_id"],
                    "distance": distance,
                }
            )

        return output

if __name__ == "__main__":

    retriever = Retriever()

    question = "What amenities are listed for Skyline Residences?"

    results = retriever.retrieve(
        question,
        top_k=4,
    )

    print("\nRETRIEVAL RESULTS")
    print("=" * 70)

    for result in results:
        print(f"\nDistance: {result['distance']:.4f}")
        print(f"Source: {result['source']}")
        print(f"Chunk: {result['chunk_id']}")
        print(f"Text: {result['text']}")