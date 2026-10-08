from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from core.config import get_settings


class EmbeddingCache:
    def __init__(self, cache_dir: Path | None = None) -> None:
        settings = get_settings()
        self.cache_dir = cache_dir or settings.embedding_cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def get(self, text: str, model: str) -> list[float] | None:
        digest = hashlib.sha256(f"{model}:{text}".encode("utf-8")).hexdigest()
        path = self._path(digest)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def put(self, text: str, model: str, vector: list[float]) -> None:
        digest = hashlib.sha256(f"{model}:{text}".encode("utf-8")).hexdigest()
        self._path(digest).write_text(json.dumps(vector), encoding="utf-8")


class HashingEmbedder:
    """Deterministic local embeddings so the pipeline runs without an API key."""

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def embed_one(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        rng = np.random.default_rng(int.from_bytes(digest[:8], "big"))
        vec = rng.normal(size=self.dim).astype(np.float32)
        tokens = text.lower().split()
        for token in tokens[:40]:
            idx = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % self.dim
            vec[idx] += 1.0
        norm = np.linalg.norm(vec) or 1.0
        return (vec / norm).tolist()
