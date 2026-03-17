from __future__ import annotations

from dataclasses import dataclass

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

from app.core.config import settings


@dataclass(frozen=True)
class RagDoc:
    source: str
    title: str
    text: str


class MilvusService:
    def __init__(self) -> None:
        self._alias = "default"

    def connect(self) -> None:
        connections.connect(
            alias=self._alias,
            host=settings.milvus_host,
            port=str(settings.milvus_port),
        )

    def ensure_collection(self, dim: int) -> Collection:
        self.connect()
        name = settings.milvus_collection

        if not utility.has_collection(name, using=self._alias):
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=256),
                FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=256),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=8192),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
            ]
            schema = CollectionSchema(fields=fields, description="Opening knowledge base")
            collection = Collection(name=name, schema=schema, using=self._alias)
            index_params = {
                "index_type": "HNSW",
                "metric_type": "IP",
                "params": {"M": 8, "efConstruction": 64},
            }
            collection.create_index(field_name="embedding", index_params=index_params)
            collection.load()
            return collection

        collection = Collection(name=name, using=self._alias)
        collection.load()
        return collection

    def upsert_documents(self, docs: list[RagDoc], embeddings: list[list[float]]) -> int:
        if len(docs) != len(embeddings):
            raise ValueError("docs/embeddings size mismatch")

        dim = len(embeddings[0]) if embeddings else 0
        collection = self.ensure_collection(dim=dim)

        sources = [d.source for d in docs]
        titles = [d.title for d in docs]
        texts = [d.text for d in docs]

        # id is auto-generated
        data = [sources, titles, texts, embeddings]
        insert_result = collection.insert(data)
        collection.flush()
        return len(insert_result.primary_keys)

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[dict]:
        collection = self.ensure_collection(dim=len(query_embedding))

        # Fetch extra candidates to absorb potential duplicates.
        raw_limit = max(top_k, top_k * 3)
        results = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param={"metric_type": "IP", "params": {"ef": 64}},
            limit=raw_limit,
            output_fields=["source", "title", "text"],
        )

        hits: list[dict] = []
        seen: set[tuple[str | None, str | None, str | None]] = set()
        for hit in results[0]:
            source = hit.entity.get("source")
            title = hit.entity.get("title")
            text = hit.entity.get("text")
            key = (source, title, text)
            if key in seen:
                continue
            seen.add(key)

            hits.append(
                {
                    "score": float(hit.score),
                    "source": source,
                    "title": title,
                    "text": text,
                }
            )

            if len(hits) >= top_k:
                break

        return hits
