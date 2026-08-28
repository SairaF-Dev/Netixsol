from sentence_transformers import SentenceTransformer


DEFAULT_MODEL = (
    "sentence-transformers/"
    "paraphrase-multilingual-MiniLM-L12-v2"
)


class LocalEmbedding:
    """
    Local multilingual embedding model.

    Embeddings are normalized for cosine similarity.
    """

    def __init__(
        self,
        model_name=DEFAULT_MODEL,
    ):
        self.model_name = model_name

        self.model = SentenceTransformer(
            model_name
        )

    def embed(self, text: str) -> list[float]:
        """Generate one normalized embedding."""

        if not isinstance(text, str):
            raise TypeError(
                "text must be a string"
            )

        text = text.strip()

        if not text:
            raise ValueError(
                "text cannot be empty"
            )

        vector = self.model.encode(
            text,
            normalize_embeddings=True,
        )

        return vector.tolist()

    def embed_many(
        self,
        texts,
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts."""

        if not texts:
            return []

        for text in texts:
            if not isinstance(text, str):
                raise TypeError(
                    "all texts must be strings"
                )

            if not text.strip():
                raise ValueError(
                    "texts cannot contain empty values"
                )

        vectors = self.model.encode(
            texts,
            normalize_embeddings=True,
        )

        return [
            vector.tolist()
            for vector in vectors
        ]