from __future__ import annotations

import re
from functools import lru_cache

from core.tfidf import SimpleTfidf, cosine_similarity
from legal_knowledge.ingestion.seed import ensure_seed_knowledge, seed_records
from llm.client import LLMClient, get_llm_client
from schemas.verification import LegalSource
from stores.vector_store import VectorRecord, get_vector_store


class LegalHybridRetriever:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or get_llm_client()
        self.records = seed_records()
        ensure_seed_knowledge()
        self.store = get_vector_store("legal_store")
        self._ids = [f"{r['document_id']}-s{r['section']}" for r in self.records]
        self._texts = [r["text"] for r in self.records]
        self._tfidf = SimpleTfidf()
        self._matrix = self._tfidf.fit_transform(self._texts)
        self._indexed = False

    def _ensure_index(self) -> None:
        if self._indexed:
            return
        vectors = self.llm.embed(self._texts)
        records = []
        for source_id, record, vector in zip(self._ids, self.records, vectors):
            records.append(
                VectorRecord(
                    id=source_id,
                    text=record["text"],
                    vector=vector,
                    metadata={
                        "store": "legal",
                        "document_id": record["document_id"],
                        "section": str(record["section"]),
                        "document_name": record["document_name"],
                    },
                )
            )
        self.store.upsert(records)
        self._indexed = True

    def search(self, query: str, k: int = 5) -> list[LegalSource]:
        self._ensure_index()
        ranked: dict[str, tuple[float, dict]] = {}

        q = self._tfidf.transform([query])
        tfidf_scores = cosine_similarity(q, self._matrix)[0]
        for idx, score in enumerate(tfidf_scores):
            ranked[self._ids[idx]] = (float(score), self.records[idx])

        vector = self.llm.embed([query])[0]
        for hit in self.store.search(vector, k=k, where={"store": "legal"}):
            record = next((r for r, i in zip(self.records, self._ids) if i == hit.id), None)
            if not record:
                continue
            prev = ranked.get(hit.id, (0.0, record))
            ranked[hit.id] = (max(prev[0], hit.score), record)

        section_match = re.search(r"section\s+([\dA-Za-z-]+)", query, flags=re.I)
        if section_match:
            needle = section_match.group(1).lower()
            for source_id, record in zip(self._ids, self.records):
                if needle in str(record["section"]).lower():
                    prev = ranked.get(source_id, (0.0, record))
                    ranked[source_id] = (max(prev[0], 1.0), record)

        sources: list[LegalSource] = []
        for source_id, (score, record) in sorted(ranked.items(), key=lambda x: x[1][0], reverse=True)[:k]:
            if score <= 0:
                continue
            sources.append(
                LegalSource(
                    source_id=source_id,
                    document_name=record["document_name"],
                    section=str(record["section"]),
                    title=record.get("title"),
                    excerpt=record["text"],
                    authority=record["authority"],
                    source=record["source"],
                    source_url=record.get("source_url"),
                    version_date=record.get("version_date"),
                    score=score,
                )
            )
        return sources


@lru_cache(maxsize=1)
def default_legal_retriever() -> LegalHybridRetriever:
    return LegalHybridRetriever()
