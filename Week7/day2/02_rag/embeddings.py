from sentence_transformers import SentenceTransformer


class LocalEmbedding:
    """
    Local semantic embedding model.

    Generates normalized embeddings locally.
    No external embedding API is required.
    """

    def __init__(
        self,
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    ):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str) -> list[float]:
        """Convert text into a normalized embedding vector."""

        if not isinstance(text, str):
            raise TypeError("text must be a string")

        if not text.strip():
            raise ValueError("text cannot be empty")

        vector = self.model.encode(
            text,
            normalize_embeddings=True,
        )

        return vector.tolist()