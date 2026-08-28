from pathlib import Path


SUPPORTED_EXTENSIONS = {
    ".md",
    ".txt",
}


def load_documents(directory: str | Path):
    """Load supported knowledge-base documents."""

    directory_path = Path(directory)

    # Resolve relative paths from this file's directory.
    if not directory_path.is_absolute():
        directory_path = (
            Path(__file__).resolve().parent
            / directory_path
        )

    directory_path = directory_path.resolve()

    if not directory_path.exists():
        raise FileNotFoundError(
            f"Documents directory not found: "
            f"{directory_path}"
        )

    if not directory_path.is_dir():
        raise ValueError(
            f"Not a directory: {directory_path}"
        )

    documents = []

    for path in sorted(
        directory_path.rglob("*")
    ):
        if not path.is_file():
            continue

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        text = path.read_text(
            encoding="utf-8"
        ).strip()

        if not text:
            continue

        documents.append(
            {
                "source": str(path),
                "text": text,
            }
        )

    return documents


if __name__ == "__main__":

    documents = load_documents("documents")

    print(
        f"Loaded {len(documents)} documents"
    )

    for document in documents:
        print(
            f"- {document['source']}"
        )