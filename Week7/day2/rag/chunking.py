"""
Chunking — Task 2, RAG Pipeline (step 2/5)

FAQs and brochures in this project are already short (1 Q&A pair, or a
3-5 sentence brochure), so chunking here mainly matters for LONGER
documents (e.g. a future full property legal document or a multi-page
brochure PDF). We still implement + evaluate it as required.

Two strategies:
  - fixed_size_chunks: splits by character count with overlap
  - sentence_chunks: splits by sentence boundary, then groups to target size

See docs/chunk_size_evaluation.md for the comparison across sizes.
"""
import re


def fixed_size_chunks(text, chunk_size=200, overlap=40):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end].strip())
        start += chunk_size - overlap
    return [c for c in chunks if c]


def sentence_chunks(text, target_size=200):
    sentences = re.split(r"(?<=[.!?۔])\s+", text)
    chunks = []
    current = ""
    for sent in sentences:
        if len(current) + len(sent) <= target_size:
            current = (current + " " + sent).strip()
        else:
            if current:
                chunks.append(current)
            current = sent
    if current:
        chunks.append(current)
    return chunks


def chunk_documents(documents, strategy="sentence", chunk_size=200, overlap=40):
    """Chunk a list of loader.Document objects, preserving metadata + a chunk_index."""
    chunked = []
    for doc in documents:
        if strategy == "fixed":
            pieces = fixed_size_chunks(doc.text, chunk_size, overlap)
        else:
            pieces = sentence_chunks(doc.text, chunk_size)
        for i, piece in enumerate(pieces):
            chunked.append({
                "chunk_id": f"{doc.doc_id}_chunk{i}",
                "doc_id": doc.doc_id,
                "source": doc.source,
                "text": piece,
                "metadata": doc.metadata,
            })
    return chunked


if __name__ == "__main__":
    from loader import load_all_documents
    docs = load_all_documents()
    chunks = chunk_documents(docs, strategy="sentence", chunk_size=150)
    print(f"{len(docs)} documents -> {len(chunks)} chunks")
    for c in chunks[:3]:
        print(c["chunk_id"], "|", c["text"][:80])
