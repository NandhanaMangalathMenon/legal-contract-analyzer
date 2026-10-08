from __future__ import annotations

import re
from dataclasses import dataclass

from core.tfidf import SimpleTfidf, cosine_similarity

from agent1.dependency_graph import ContractDependencyGraph
from llm.client import LLMClient
from schemas.document import Clause, DocumentAnalysis
from stores.vector_store import VectorRecord, VectorStore


@dataclass
class RankedPassage:
    unit_id: str
    text: str
    score: float
    method: str


class HybridContractRetriever:
    """TF-IDF + embeddings + dependency graph + exact cross-reference search."""

    def __init__(self, analysis: DocumentAnalysis, llm: LLMClient, store: VectorStore) -> None:
        self.analysis = analysis
        self.llm = llm
        self.store = store
        self.graph = ContractDependencyGraph(analysis)
        self._units: dict[str, str] = {}
        for clause in analysis.clauses:
            self._units[clause.clause_id] = clause.text
        for definition in analysis.definitions:
            self._units[definition.definition_id] = f"{definition.term}: {definition.text}"
        self._ids = list(self._units.keys())
        self._texts = [self._units[i] for i in self._ids]
        self._tfidf = SimpleTfidf() if self._texts else None
        self._tfidf_matrix = self._tfidf.fit_transform(self._texts) if self._tfidf and self._texts else None
        self._index_embeddings()

    def _index_embeddings(self) -> None:
        if not self._texts:
            return
        vectors = self.llm.embed(self._texts)
        records = [
            VectorRecord(
                id=unit_id,
                text=text,
                vector=vector,
                metadata={"document_id": self.analysis.document_id, "store": "contract"},
            )
            for unit_id, text, vector in zip(self._ids, self._texts, vectors)
        ]
        self.store.upsert(records)

    def retrieve(self, query: str, target_id: str | None = None, k: int = 8) -> list[RankedPassage]:
        ranked: dict[str, RankedPassage] = {}

        def keep(unit_id: str, score: float, method: str) -> None:
            text = self._units.get(unit_id)
            if not text:
                return
            existing = ranked.get(unit_id)
            if existing is None or score > existing.score:
                ranked[unit_id] = RankedPassage(unit_id=unit_id, text=text, score=score, method=method)

        for unit_id, score in self._tfidf_search(query, k=k):
            keep(unit_id, score, "tfidf")
        for unit_id, score in self._embed_search(query, k=k):
            keep(unit_id, score, "embedding")
        for unit_id in self._exact_cross_references(query):
            keep(unit_id, 1.0, "exact_xref")
        if target_id:
            keep(target_id, 1.0, "target")
            for neighbor in self.graph.neighbors(target_id, hops=2):
                keep(neighbor, 0.85, "dependency_graph")
        return sorted(ranked.values(), key=lambda item: item.score, reverse=True)[: max(k, 12)]

    def _tfidf_search(self, query: str, k: int) -> list[tuple[str, float]]:
        if self._tfidf is None or self._tfidf_matrix is None:
            return []
        q = self._tfidf.transform([query])
        scores = cosine_similarity(q, self._tfidf_matrix)[0]
        scored_ids = [(self._ids[i], float(scores[i])) for i in range(len(scores)) if scores[i] > 0]
        scored_ids.sort(key=lambda x: x[1], reverse=True)
        return scored_ids[:k]

    def _embed_search(self, query: str, k: int) -> list[tuple[str, float]]:
        vector = self.llm.embed([query])[0]
        hits = self.store.search(vector, k=k, where={"document_id": self.analysis.document_id})
        return [(hit.id, hit.score) for hit in hits]

    def _exact_cross_references(self, query: str) -> list[str]:
        found: list[str] = []
        for match in re.finditer(r"(?:section|clause)\s+(\d+(?:\.\d+)*)", query, flags=re.I):
            needle = match.group(1)
            for clause in self.analysis.clauses:
                if needle in clause.title or needle in clause.clause_id:
                    found.append(clause.clause_id)
        for match in re.finditer(r"(schedule|annexure|amendment)\s+([A-Z0-9]+)", query, flags=re.I):
            needle = f"{match.group(1)} {match.group(2)}".lower()
            for clause in self.analysis.clauses:
                if needle in clause.title.lower():
                    found.append(clause.clause_id)
        return found

    def clause_map(self) -> list[Clause]:
        return self.analysis.clauses
