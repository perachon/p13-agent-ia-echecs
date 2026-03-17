from __future__ import annotations


def chunk_text(text: str, *, max_chars: int = 1200, overlap: int = 120) -> list[str]:
    """Chunk text into overlapping character windows.

    This is a simple, dependency-free chunker suitable for POC ingestion.
    """

    clean = (text or "").strip()
    if not clean:
        return []

    max_chars = max(200, int(max_chars))
    overlap = max(0, min(int(overlap), max_chars - 1))

    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(len(clean), start + max_chars)
        chunk = clean[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(clean):
            break
        start = end - overlap

    return chunks
