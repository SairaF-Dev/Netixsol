from chunker import chunk_documents
from embeddings import LocalEmbedding
from loader import load_documents
from metadata import get_metadata
from vector_store import ChromaVectorStore


class Retriever:
    """
    Production semantic retriever.

    Pipeline:

    Documents
        ↓
    Chunking
        ↓
    Local embeddings
        ↓
    ChromaDB
        ↓
    Semantic retrieval
    """

    def __init__(
        self,
        documents_dir="documents",
        persist_directory="chroma_db",
        collection_name="real_estate_knowledge",
        chunk_size=512,
        overlap_sentences=1,
        distance_threshold=0.56,
    ):
        self.documents_dir = documents_dir
        self.distance_threshold = distance_threshold

        self.embedder = LocalEmbedding()

        self.store = ChromaVectorStore(
            embedder=self.embedder,
            persist_directory=persist_directory,
            collection_name=collection_name,
        )

        self._build_index(
            chunk_size=chunk_size,
            overlap_sentences=overlap_sentences,
        )

    def _build_index(
    self,
    chunk_size,
    overlap_sentences,
):
        """Incrementally synchronize the knowledge base."""

        documents = load_documents(
            self.documents_dir
        )

        if not documents:
            raise ValueError(
                f"No documents found in: "
                f"{self.documents_dir}"
            )

        chunks = chunk_documents(
            documents,
            chunk_size=chunk_size,
            overlap_sentences=overlap_sentences,
        )

        if not chunks:
            raise ValueError(
                "No chunks were created."
            )

        # Attach document metadata.
        for chunk in chunks:

            metadata = get_metadata(
                chunk["source"]
            )

            chunk["property_name"] = (
                metadata["property_name"]
            )

            chunk["property_id"] = (
                metadata["property_id"]
            )

            chunk["document_type"] = (
                metadata["document_type"]
            )

        # Incremental synchronization.
        result = self.store.sync_documents(
            chunks
        )

        print(
            f"Loaded documents: "
            f"{len(documents)}"
        )

        print(
            f"Created chunks: "
            f"{len(chunks)}"
        )

        print(
            f"New documents indexed: "
            f"{result['added']}"
        )

        print(
            f"Updated documents indexed: "
            f"{result['updated']}"
        )

        print(
            f"Unchanged documents skipped: "
            f"{result['skipped']}"
        )

        print(
            f"Chunks newly embedded: "
            f"{result['chunks_indexed']}"
        )

        print(
            f"Total chunks in ChromaDB: "
            f"{self.store.count()}"
        )
        
    def retrieve(
        self,
        query: str,
        top_k=4,
    ):
        """Retrieve relevant verified knowledge chunks."""

        return self.store.search(
            query=query,
            top_k=top_k,
            distance_threshold=(
                self.distance_threshold
            ),
        )


if __name__ == "__main__":

    retriever = Retriever()

    question = (
        "What amenities are listed "
        "for Skyline Residences?"
    )

    results = retriever.retrieve(
        question,
        top_k=4,
    )

    print("\nRETRIEVAL RESULTS")
    print("=" * 70)

    if not results:
        print(
            "No sufficiently relevant "
            "verified context found."
        )

    for result in results:

        print(
            f"\nDistance: "
            f"{result['distance']:.4f}"
        )

        print(
            f"Source: {result['source']}"
        )

        print(
            f"Chunk: {result['chunk_id']}"
        )

        print(
            f"Text: {result['text']}"
        )