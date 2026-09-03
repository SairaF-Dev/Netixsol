from pathlib import Path

SUPPORTED_EXTENSIONS = {".md", ".txt"}


def load_documents(directory: str | Path):
    """Load verified text documents using portable corpus-relative sources."""
    directory_path = Path(directory)
    if not directory_path.is_absolute():
        directory_path = Path(__file__).resolve().parent / directory_path
    directory_path = directory_path.resolve()
    if not directory_path.exists():
        raise FileNotFoundError(f"Documents directory not found: {directory_path}")
    if not directory_path.is_dir():
        raise ValueError(f"Not a directory: {directory_path}")
    documents=[]
    for path in sorted(directory_path.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        text=path.read_text(encoding='utf-8').strip()
        if not text: continue
        documents.append({'source': path.relative_to(directory_path).as_posix(), 'text': text})
    return documents
