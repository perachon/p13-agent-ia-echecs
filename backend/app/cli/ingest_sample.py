from __future__ import annotations

import json
from pathlib import Path

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
        docs.append(RagDoc(source=row["source"], title=row["title"], text=row["text"]))

    embeddings = embed_texts([d.text for d in docs])
    service = MilvusService()
    inserted = service.upsert_documents(docs, embeddings)
    print(f"Inserted {inserted} documents into Milvus")


if __name__ == "__main__":
    main()
