from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from core.config import get_settings
from core.exceptions import ConfigurationError


@dataclass
class VectorRecord:
    id: str
    text: str
    vector: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VectorHit:
    id: str
    score: float
    text: str
    metadata: dict[str, Any]


class VectorStore(ABC):
    @abstractmethod
    def upsert(self, records: list[VectorRecord]) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(self, vector: list[float], k: int = 8, where: dict[str, Any] | None = None) -> list[VectorHit]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, ids: list[str]) -> None:
        raise NotImplementedError


class InMemoryVectorStore(VectorStore):
    """Default store. Swap for Chroma/Qdrant/pgvector without changing agents."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._records: dict[str, VectorRecord] = {}

    def upsert(self, records: list[VectorRecord]) -> None:
        for record in records:
            self._records[record.id] = record

    def search(self, vector: list[float], k: int = 8, where: dict[str, Any] | None = None) -> list[VectorHit]:
        if not self._records:
            return []
        query = np.array(vector, dtype=np.float32)
        hits: list[VectorHit] = []
        for record in self._records.values():
            if where and not _metadata_match(record.metadata, where):
                continue
            doc = np.array(record.vector, dtype=np.float32)
            denom = (np.linalg.norm(query) * np.linalg.norm(doc)) or 1.0
            score = float(np.dot(query, doc) / denom)
            hits.append(VectorHit(id=record.id, score=score, text=record.text, metadata=record.metadata))
        hits.sort(key=lambda item: item.score, reverse=True)
        return hits[:k]

    def delete(self, ids: list[str]) -> None:
        for item_id in ids:
            self._records.pop(item_id, None)


def _metadata_match(metadata: dict[str, Any], where: dict[str, Any]) -> bool:
    return all(metadata.get(key) == value for key, value in where.items())


_STORES: dict[str, VectorStore] = {}


def get_vector_store(name: str) -> VectorStore:
    settings = get_settings()
    backend = settings.vector_store_backend.lower()
    if backend not in {"memory", "chroma"}:
        raise ConfigurationError(f"Unsupported VECTOR_STORE_BACKEND: {backend}")
    if name not in _STORES:
        # Chroma is optional; memory is the supported default implementation.
        _STORES[name] = InMemoryVectorStore(name)
    return _STORES[name]


def reset_vector_stores() -> None:
    _STORES.clear()
