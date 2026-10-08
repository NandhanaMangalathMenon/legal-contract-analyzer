from __future__ import annotations

from dataclasses import dataclass, field

from agent1.dependency_graph import ContractDependencyGraph
from agent1.retrieval.hybrid import HybridContractRetriever, RankedPassage
from core.config import get_settings
from schemas.document import Clause, Definition, DocumentAnalysis


@dataclass
class EvidencePackage:
    target_id: str
    target_text: str
    related_ids: list[str]
    definitions: list[Definition]
    passages: list[RankedPassage]
    compressed_context: str
    dependency_complexity: int
    graph_depth: int


class LongRangeDependencyAnalyzer:
    def __init__(self, analysis: DocumentAnalysis, retriever: HybridContractRetriever) -> None:
        self.analysis = analysis
        self.retriever = retriever
        self.graph = ContractDependencyGraph(analysis)
        self._clauses = {c.clause_id: c for c in analysis.clauses}
        self._defs = {d.definition_id: d for d in analysis.definitions}

    def package_for(self, clause: Clause) -> EvidencePackage:
        settings = get_settings()
        hop1 = self.graph.neighbors(clause.clause_id, hops=1)
        hop2 = [n for n in self.graph.neighbors(clause.clause_id, hops=2) if n not in hop1]
        related = (hop1 + hop2)[: settings.max_context_clauses]
        semantic = self.retriever.retrieve(clause.text, target_id=clause.clause_id, k=6)
        definitions = [
            self._defs[item]
            for item in related
            if item in self._defs
        ]
        for edge_target in related:
            # definitions linked from DEFINED_BY
            pass
        for definition in self.analysis.definitions:
            if definition.term and definition.term.lower() in clause.text.lower():
                if definition not in definitions:
                    definitions.append(definition)
        passages = semantic
        complexity = self.graph.complexity(clause.clause_id)
        compressed = compress_legal_context(clause, related, self._clauses, definitions, passages)
        return EvidencePackage(
            target_id=clause.clause_id,
            target_text=clause.text,
            related_ids=related,
            definitions=definitions,
            passages=passages,
            compressed_context=compressed,
            dependency_complexity=complexity,
            graph_depth=2 if hop2 else 1 if hop1 else 0,
        )


PRESERVE_MARKERS = (
    "unless",
    "except",
    "subject to",
    "provided that",
    "notwithstanding",
    "only if",
    "within",
    "before",
    "after",
    "save for",
    "excluding",
)


def compress_legal_context(
    clause: Clause,
    related_ids: list[str],
    clauses: dict[str, Clause],
    definitions: list[Definition],
    passages: list[RankedPassage],
) -> str:
    """Structure-aware compression. Never drops exception/condition markers or numbers."""
    parts = [
        f"GLOBAL MAP TARGET: {clause.clause_id} {clause.title} [{clause.type.value}]",
        f"PRIMARY TEXT:\n{clause.text.strip()}",
    ]
    if clause.exceptions:
        parts.append("EXCEPTIONS (preserved exactly):\n- " + "\n- ".join(clause.exceptions))
    if clause.conditions:
        parts.append("CONDITIONS (preserved exactly):\n- " + "\n- ".join(clause.conditions))
    if definitions:
        parts.append(
            "DEFINITIONS:\n"
            + "\n".join(f"- {item.definition_id} {item.term}: {item.text}" for item in definitions)
        )
    neighborhood = []
    for unit_id in related_ids:
        other = clauses.get(unit_id)
        if other:
            neighborhood.append(f"- {other.clause_id} {other.title}: {_preserve_sentence(other.text)}")
    if neighborhood:
        parts.append("DEPENDENCY NEIGHBORHOOD:\n" + "\n".join(neighborhood))
    extra = []
    for passage in passages[:6]:
        if passage.unit_id in {clause.clause_id, *related_ids}:
            continue
        extra.append(f"- {passage.unit_id} ({passage.method}): {_preserve_sentence(passage.text)}")
    if extra:
        parts.append("RELATED PASSAGES:\n" + "\n".join(extra))
    return "\n\n".join(parts)


def _preserve_sentence(text: str) -> str:
    sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
    kept: list[str] = []
    for sentence in sentences:
        lower = sentence.lower()
        if any(marker in lower for marker in PRESERVE_MARKERS):
            kept.append(sentence)
            continue
        if any(ch.isdigit() for ch in sentence):
            kept.append(sentence)
            continue
        if len(kept) < 2:
            kept.append(sentence)
    return ". ".join(kept)[:1200]
