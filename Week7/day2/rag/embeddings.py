"""
Embedding — Task 2, RAG Pipeline (step 3/5)

Two backends:
  - OpenAIEmbedder: production backend (text-embedding-3-small). Needs
    OPENAI_API_KEY. Use this in the deployed agent.
  - TfidfEmbedder: dependency-free offline fallback so this pipeline is
    runnable/testable without any API key or internet access (useful
    for local dev, CI, and grading without burning API credits).

Swap backends by changing EMBEDDER_BACKEND env var or the `backend`
argument to get_embedder().
"""
import os
import math
from collections import Counter


class TfidfEmbedder:
    """Minimal TF-IDF vectorizer — no external dependencies."""

    def __init__(self):
        self.vocab = {}
        self.idf = {}
        self.fitted = False

    def _tokenize(self, text):
        return [t.lower() for t in text.split() if t.strip()]

    def fit(self, corpus):
        df = Counter()
        for text in corpus:
            tokens = set(self._tokenize(text))
            for t in tokens:
                df[t] += 1
        self.vocab = {term: i for i, term in enumerate(sorted(df.keys()))}
        n_docs = len(corpus)
        self.idf = {term: math.log((n_docs + 1) / (freq + 1)) + 1 for term, freq in df.items()}
        self.fitted = True

    def embed(self, text):
        if not self.fitted:
            raise RuntimeError("Call fit(corpus) before embed().")
        tokens = self._tokenize(text)
        tf = Counter(tokens)
        vec = [0.0] * len(self.vocab)
        for term, count in tf.items():
            if term in self.vocab:
                vec[self.vocab[term]] = count * self.idf.get(term, 0.0)
        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_batch(self, texts):
        return [self.embed(t) for t in texts]


class OpenAIEmbedder:
    """Production embedder using OpenAI's text-embedding-3-small.
    Requires: pip install openai, and OPENAI_API_KEY set in the environment.
    """

    def __init__(self, model="text-embedding-3-small"):
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI()
        return self._client

    def embed(self, text):
        return self.embed_batch([text])[0]

    def embed_batch(self, texts):
        client = self._get_client()
        response = client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]


def get_embedder(backend=None):
    backend = backend or os.environ.get("EMBEDDER_BACKEND", "tfidf")
    if backend == "openai":
        return OpenAIEmbedder()
    return TfidfEmbedder()


if __name__ == "__main__":
    embedder = TfidfEmbedder()
    corpus = ["DHA Phase 6 luxury bungalow", "Bahria Town rental house", "Gulberg apartment for rent"]
    embedder.fit(corpus)
    vec = embedder.embed("Bahria Town house")
    print("Vector length:", len(vec))
