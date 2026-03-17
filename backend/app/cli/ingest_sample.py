from __future__ import annotations

import json
from pathlib import Path

from app.rag.chunking import chunk_text
from app.rag.embeddings import embed_texts
from app.rag.milvus_service import MilvusService, RagDoc


def main() -> None:
    data_path = Path(__file__).resolve().parents[2] / "data" / "sample_openings.jsonl"
    raw_lines = data_path.read_text(encoding="utf-8").splitlines()

    docs: list[RagDoc] = []
    for line in raw_lines:
        if not line.strip():
            continue
        row = json.loads(line)
        text = str(row.get("text") or "").strip()
        chunks = chunk_text(text, max_chars=1200, overlap=120) or []
        if not chunks:
            continue

        base_title = str(row.get("title") or "Document").strip()
        for i, chunk in enumerate(chunks, start=1):
            docs.append(
                RagDoc(
                    source=str(row.get("source") or "sample"),
                    title=f"{base_title} (chunk {i})" if len(chunks) > 1 else base_title,
                    text=chunk,
                )
            )

    embeddings = embed_texts([d.text for d in docs])
    service = MilvusService()
    inserted = service.upsert_documents(docs, embeddings)
    print(f"Inserted {inserted} documents into Milvus")


if __name__ == "__main__":
    main()
