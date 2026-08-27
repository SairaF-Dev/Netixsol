from embeddings import LocalEmbedding
from vector_store import ChromaVectorStore


embedder = LocalEmbedding()

store = ChromaVectorStore(
    embedder=embedder,
    persist_directory="./test_chroma_db",
    collection_name="test_collection",
)

documents = [
    {
        "source": "test.md",
        "chunk_id": 0,
        "text": "Skyline Residences has a shared swimming pool and gym.",
    },
    {
        "source": "test.md",
        "chunk_id": 1,
        "text": "The property is located in Lahore.",
    },
]

store.add(documents)

results = store.search(
    "Does the property have a swimming pool?",
    top_k=2,
)

for result in results:
    print(
        f"Distance: {result['distance']:.4f} | "
        f"Source: {result['source']} | "
        f"Text: {result['text']}"
    )