from embeddings import LocalEmbedding
from vector_store import ChromaVectorStore


def main():

    print("=" * 70)
    print("CHROMA VECTOR STORE TEST")
    print("=" * 70)

    embedder = LocalEmbedding()

    store = ChromaVectorStore(
        embedder=embedder,
        persist_directory="./test_chroma_db",
        collection_name="test_collection",
    )

    # Start clean.
    store.clear()

    documents = [
        {
            "source": "test.md",
            "chunk_id": 0,
            "text": (
                "Skyline Residences has a "
                "shared swimming pool and gym."
            ),
        },
        {
            "source": "test.md",
            "chunk_id": 1,
            "text": (
                "The property is located "
                "in Lahore."
            ),
        },
    ]

    result = store.sync_documents(documents)

    print(
        f"\nAdded: {result['added']}"
    )

    print(
        f"Updated: {result['updated']}"
    )

    print(
        f"Skipped: {result['skipped']}"
    )

    print(
        f"Chunks indexed: "
        f"{result['chunks_indexed']}"
    )

    print(
        f"\nIndexed documents: {store.count()}"
    )

    results = store.search(
        "Does the property have a swimming pool?",
        top_k=2,
    )

    print("\nSEARCH RESULTS")
    print("=" * 70)

    if not results:
        print("FAIL: no results returned")
        return

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

    if "swimming pool" in (
        results[0]["text"].lower()
    ):
        print(
            "\nPASS: semantic retrieval works"
        )
    else:
        print(
            "\nFAIL: expected swimming pool "
            "chunk was not ranked first"
        )


if __name__ == "__main__":
    main()