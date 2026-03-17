from __future__ import annotations

from functools import lru_cache

import numpy as np

from fastembed import TextEmbedding

from app.core.config import settings


@lru_cache(maxsize=1)
def get_embedding_model() -> TextEmbedding:
    # NOTE: fastembed uses ONNX Runtime and stays light in Docker.
    model_name = settings.embedding_model_name
    if model_name.startswith("sentence-transformers/"):
        model_name = "BAAI/bge-small-en-v1.5"

    return TextEmbedding(model_name=model_name)


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedding_model()
    vectors = list(model.embed(texts))

    # We use IP (inner product) similarity in Milvus; normalize to approximate cosine.
    normalized: list[list[float]] = []
    for vec in vectors:
        arr = np.asarray(vec, dtype=np.float32)
        norm = float(np.linalg.norm(arr))
        if norm > 0:
            arr = arr / norm
        normalized.append(arr.tolist())
    return normalized
