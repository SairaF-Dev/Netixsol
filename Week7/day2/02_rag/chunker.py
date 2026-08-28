import re


def clean_text(text: str) -> str:
    """Normalize whitespace while preserving markdown structure."""

    if not isinstance(text, str):
        raise TypeError("text must be a string")

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Remove trailing spaces/tabs.
    text = re.sub(r"[ \t]+", " ", text)

    # Collapse excessive blank lines.
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def split_sections(text: str):
    """
    Split markdown into logical sections.

    A heading stays attached to the content that follows it.
    """

    text = clean_text(text)

    if not text:
        return []

    sections = []
    current = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        if line.startswith("#"):
            if current:
                sections.append("\n".join(current))
                current = []

        current.append(line)

    if current:
        sections.append("\n".join(current))

    return sections


def split_sentences(text: str):
    """Split normal text into complete sentences."""

    return [
        sentence.strip()
        for sentence in re.split(
            r"(?<=[.!?])\s+",
            text,
        )
        if sentence.strip()
    ]


def chunk_text(
    text: str,
    chunk_size: int = 512,
    overlap_sentences: int = 1,
):
    """
    Context-preserving, sentence-aware chunker.
    """

    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if chunk_size <= 0:
        raise ValueError(
            "chunk_size must be greater than 0"
        )

    if overlap_sentences < 0:
        raise ValueError(
            "overlap_sentences cannot be negative"
        )

    sections = split_sections(text)

    chunks = []

    for section in sections:

        if len(section) <= chunk_size:
            chunks.append(section)
            continue

        sentences = split_sentences(section)

        if not sentences:
            chunks.append(section[:chunk_size])
            continue

        current = []

        for sentence in sentences:

            candidate = " ".join(
                current + [sentence]
            )

            if current and len(candidate) > chunk_size:

                chunks.append(
                    " ".join(current)
                )

                overlap = current[
                    -overlap_sentences:
                ] if overlap_sentences else []

                current = overlap + [sentence]

            else:
                current.append(sentence)

        if current:
            chunks.append(
                " ".join(current)
            )

    return chunks


def chunk_documents(
    documents,
    chunk_size=512,
    overlap_sentences=1,
):
    """Chunk documents while preserving source metadata."""

    if not documents:
        return []

    output = []

    for doc in documents:

        if not isinstance(doc, dict):
            raise TypeError(
                "each document must be a dictionary"
            )

        if "source" not in doc:
            raise ValueError(
                "document is missing 'source'"
            )

        if "text" not in doc:
            raise ValueError(
                "document is missing 'text'"
            )

        chunks = chunk_text(
            doc["text"],
            chunk_size=chunk_size,
            overlap_sentences=overlap_sentences,
        )

        for index, chunk in enumerate(chunks):

            output.append(
                {
                    "source": doc["source"],
                    "chunk_id": index,
                    "text": chunk,
                }
            )

    return output


if __name__ == "__main__":

    from loader import load_documents

    documents = load_documents("documents")

    chunks = chunk_documents(
        documents,
        chunk_size=512,
        overlap_sentences=1,
    )

    print(
        f"Loaded documents: {len(documents)}"
    )

    print(
        f"Created chunks: {len(chunks)}"
    )

    print("\nCHUNKS")
    print("=" * 70)

    for chunk in chunks:

        print(
            f"\nSource: {chunk['source']}"
            f"\nChunk: {chunk['chunk_id']}"
            f"\nLength: {len(chunk['text'])}"
            f"\n{chunk['text']}"
        )