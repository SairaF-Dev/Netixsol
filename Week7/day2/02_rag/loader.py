from pathlib import Path

SUPPORTED_EXTENSIONS = {".md", ".txt"}

def load_documents(directory: str):
    docs = []
    for path in Path(directory).rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            docs.append({
                "source": str(path),
                "text": path.read_text(encoding="utf-8")
            })
    return docs

if __name__ == "__main__":
    docs = load_documents("documents")
    print(f"Loaded {len(docs)} documents")
