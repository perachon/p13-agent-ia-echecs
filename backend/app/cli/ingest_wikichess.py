from __future__ import annotations

import json
import os
from pathlib import Path

from app.rag.chunking import chunk_text
from app.rag.embeddings import embed_texts
from app.rag.milvus_service import MilvusService, RagDoc


def _guess_text(row: dict) -> str:
    """Best-effort extraction for Wikichess-like rows.

    Expected keys vary by export; we try common names.
    """

    for key in (
        "content",
        "text",
        "body",
        "markdown",
        "html",
        "description",
        "excerpt",
    ):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def main() -> None:
    """Ingest a Wikichess export into Milvus.

    Input format: JSONL (one JSON object per line).
    Path can be provided via env var WIKICHESS_JSONL_PATH.
    """

    default_path = Path(__file__).resolve().parents[2] / "data" / "wikichess.jsonl"
    env_path = os.environ.get("WIKICHESS_JSONL_PATH", "").strip()
    data_path = Path(env_path) if env_path else default_path

    if not data_path.exists():
        raise SystemExit(
            "Wikichess dataset not found. Provide WIKICHESS_JSONL_PATH=/path/to/wikichess.jsonl"
        )

    raw_lines = data_path.read_text(encoding="utf-8").splitlines()

    docs: list[RagDoc] = []
    skipped_invalid_json = 0
    skipped_non_dict = 0
    skipped_empty_text = 0
    total_rows = 0
    for line in raw_lines:
        if not line.strip():
            continue
        total_rows += 1
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            skipped_invalid_json += 1
            continue
        if not isinstance(row, dict):
            skipped_non_dict += 1
            continue

        title = row.get("title")
        title_str = title.strip() if isinstance(title, str) else "Wikichess"
        source = row.get("source")
        source_str = source.strip() if isinstance(source, str) else "wikichess"
        text = _guess_text(row)
        if not text.strip():
            skipped_empty_text += 1
            continue

        for i, chunk in enumerate(chunk_text(text, max_chars=1200, overlap=120), start=1):
            docs.append(
                RagDoc(
                    source=source_str,
                    title=f"{title_str} (chunk {i})",
                    text=chunk,
                )
            )

    if not docs:
        raise SystemExit(
            "No documents extracted from the dataset. "
            f"rows={total_rows} invalid_json={skipped_invalid_json} non_dict={skipped_non_dict} empty_text={skipped_empty_text}"
        )

    embeddings = embed_texts([d.text for d in docs])
    service = MilvusService()
    inserted = service.upsert_documents(docs, embeddings)
    print(f"Inserted {inserted} documents into Milvus (wikichess)")
    print(
        "Skipped rows: "
        f"rows={total_rows} invalid_json={skipped_invalid_json} non_dict={skipped_non_dict} empty_text={skipped_empty_text}"
    )


if __name__ == "__main__":
    main()
