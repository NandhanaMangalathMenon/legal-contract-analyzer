from __future__ import annotations

import re
from collections import defaultdict, deque

from schemas.common import DependencyRelation
from schemas.document import DependencyEdge, DocumentAnalysis

XREF_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"as defined in (?:section|clause)\s+([\dA-Za-z.]+)", re.I), "definition"),
    (re.compile(r"subject to (?:section|clause)\s+([\dA-Za-z.]+)", re.I), "condition"),
    (re.compile(r"notwithstanding (?:section|clause)\s+([\dA-Za-z.]+)", re.I), "exception"),
    (re.compile(r"except as (?:provided|set forth) in (?:section|clause|schedule)\s+([\dA-Za-z.]+)", re.I), "exception"),
    (re.compile(r"as set forth in (annexure|schedule|exhibit)\s+([A-Z0-9]+)", re.I), "schedule"),
    (re.compile(r"except as provided in (schedule)\s+([A-Z0-9]+)", re.I), "schedule"),
    (re.compile(r"pursuant to (amendment(?:\s+no\.?)?\s*[0-9]+)", re.I), "amendment"),
    (re.compile(r"under the terms described above", re.I), "above"),
    (re.compile(r"(?:section|clause)\s+([\dA-Za-z.]+)", re.I), "generic"),
]


class ContractDependencyGraph:
    def __init__(self, analysis: DocumentAnalysis | None = None) -> None:
        self.edges: list[DependencyEdge] = []
        self._adj: dict[str, list[DependencyEdge]] = defaultdict(list)
        self._rev: dict[str, list[DependencyEdge]] = defaultdict(list)
        if analysis:
            for edge in analysis.dependencies:
                self.add_edge(edge)

    def add_edge(self, edge: DependencyEdge) -> None:
        self.edges.append(edge)
        self._adj[edge.source_id].append(edge)
        self._rev[edge.target_id].append(edge)

    def neighbors(self, node_id: str, hops: int = 1) -> list[str]:
        seen = {node_id}
        queue = deque([(node_id, 0)])
        ordered: list[str] = []
        while queue:
            current, depth = queue.popleft()
            if depth >= hops:
                continue
            for edge in self._adj[current] + self._rev[current]:
                nxt = edge.target_id if edge.source_id == current else edge.source_id
                if nxt not in seen:
                    seen.add(nxt)
                    ordered.append(nxt)
                    queue.append((nxt, depth + 1))
        return ordered

    def edges_for(self, node_id: str) -> list[DependencyEdge]:
        return list(self._adj[node_id]) + list(self._rev[node_id])

    def complexity(self, node_id: str) -> int:
        related = self.neighbors(node_id, hops=2)
        local = self.edges_for(node_id)
        mods = sum(1 for e in local if e.relation in {DependencyRelation.MODIFIED_BY, DependencyRelation.OVERRIDDEN_BY})
        defs = sum(1 for e in local if e.relation == DependencyRelation.DEFINED_BY)
        excs = sum(1 for e in local if e.relation in {DependencyRelation.EXCEPTED_BY, DependencyRelation.LIMITED_BY})
        return min(20, len(related) + mods + defs + excs)


def build_dependency_graph(analysis: DocumentAnalysis) -> list[DependencyEdge]:
    graph = ContractDependencyGraph()
    id_by_heading = _index_headings(analysis)
    term_to_def = {item.term.lower(): item.definition_id for item in analysis.definitions}

    for clause in analysis.clauses:
        text = clause.text
        for pattern, kind in XREF_PATTERNS:
            for match in pattern.finditer(text):
                target = _resolve_target(match, kind, analysis, id_by_heading)
                if not target or target == clause.clause_id:
                    continue
                relation = _relation_for(kind, match.group(0))
                graph.add_edge(
                    DependencyEdge(
                        source_id=clause.clause_id,
                        target_id=target,
                        relation=relation,
                        evidence=match.group(0)[:240],
                        deterministic=True,
                    )
                )
                if target not in clause.references:
                    clause.references.append(target)

        for definition in analysis.definitions:
            if definition.term and re.search(rf"\b{re.escape(definition.term)}\b", text):
                if definition.clause_id == clause.clause_id:
                    continue
                graph.add_edge(
                    DependencyEdge(
                        source_id=clause.clause_id,
                        target_id=definition.definition_id,
                        relation=DependencyRelation.DEFINED_BY,
                        evidence=definition.term,
                        deterministic=True,
                    )
                )

        lower = text.lower()
        if any(token in lower for token in ("notwithstanding", "except", "subject to", "provided that")):
            for other in analysis.clauses:
                if other.clause_id == clause.clause_id:
                    continue
                if other.clause_id in clause.references:
                    graph.add_edge(
                        DependencyEdge(
                            source_id=clause.clause_id,
                            target_id=other.clause_id,
                            relation=DependencyRelation.EXCEPTED_BY
                            if "notwithstanding" in lower or "except" in lower
                            else DependencyRelation.CONDITIONED_BY,
                            evidence="exception/condition language with cross-reference",
                            deterministic=True,
                        )
                    )

    for schedule in analysis.schedules:
        for clause in analysis.clauses:
            if clause.component_kind == "schedule":
                continue
            if any(token in clause.text.lower() for token in ("schedule", schedule.title.lower().split(":")[0].lower())):
                graph.add_edge(
                    DependencyEdge(
                        source_id=clause.clause_id,
                        target_id=schedule.schedule_id,
                        relation=DependencyRelation.MODIFIED_BY
                        if "modif" in schedule.text.lower()
                        else DependencyRelation.INCORPORATES,
                        evidence=schedule.title,
                        deterministic=False,
                    )
                )
        for ref in schedule.modifies:
            target = id_by_heading.get(ref.lower())
            if target:
                graph.add_edge(
                    DependencyEdge(
                        source_id=schedule.schedule_id,
                        target_id=target,
                        relation=DependencyRelation.MODIFIED_BY,
                        evidence=ref,
                        deterministic=True,
                    )
                )

    for annexure in analysis.annexures:
        for ref in annexure.modifies:
            target = id_by_heading.get(ref.lower())
            if target:
                graph.add_edge(
                    DependencyEdge(
                        source_id=annexure.annexure_id,
                        target_id=target,
                        relation=DependencyRelation.INCORPORATES,
                        evidence=ref,
                        deterministic=True,
                    )
                )

    for amendment in analysis.amendments:
        for ref in amendment.modified_clause_ids:
            target = id_by_heading.get(ref.lower()) or _fuzzy_section(analysis, ref)
            if target:
                graph.add_edge(
                    DependencyEdge(
                        source_id=amendment.amendment_id,
                        target_id=target,
                        relation=DependencyRelation.OVERRIDDEN_BY,
                        evidence=ref,
                        deterministic=True,
                    )
                )
                graph.add_edge(
                    DependencyEdge(
                        source_id=target,
                        target_id=amendment.amendment_id,
                        relation=DependencyRelation.OVERRIDDEN_BY,
                        evidence=amendment.title,
                        deterministic=True,
                    )
                )

    # Unique edges
    unique: dict[tuple[str, str, str], DependencyEdge] = {}
    for edge in graph.edges:
        unique[(edge.source_id, edge.target_id, edge.relation.value)] = edge
    _ = term_to_def
    return list(unique.values())


def _index_headings(analysis: DocumentAnalysis) -> dict[str, str]:
    index: dict[str, str] = {}
    for clause in analysis.clauses:
        index[clause.title.lower()] = clause.clause_id
        numbers = re.findall(r"(?:section|clause)\s+([\dA-Za-z.]+)", clause.title, flags=re.I)
        for number in numbers:
            index[f"section {number}".lower()] = clause.clause_id
            index[f"clause {number}".lower()] = clause.clause_id
        numbers = re.findall(r"^(\d+(?:\.\d+)*)", clause.title)
        for number in numbers:
            index[f"section {number}".lower()] = clause.clause_id
    for schedule in analysis.schedules:
        index[schedule.title.lower()] = schedule.schedule_id
        m = re.search(r"schedule\s+([A-Z0-9]+)", schedule.title, re.I)
        if m:
            index[f"schedule {m.group(1)}".lower()] = schedule.schedule_id
    for annexure in analysis.annexures:
        index[annexure.title.lower()] = annexure.annexure_id
    for amendment in analysis.amendments:
        index[amendment.title.lower()] = amendment.amendment_id
        m = re.search(r"amendment(?:\s+no\.?)?\s*([0-9]+)", amendment.title, re.I)
        if m:
            index[f"amendment no. {m.group(1)}".lower()] = amendment.amendment_id
            index[f"amendment {m.group(1)}".lower()] = amendment.amendment_id
    for definition in analysis.definitions:
        index[definition.term.lower()] = definition.definition_id
    return index


def _resolve_target(match: re.Match[str], kind: str, analysis: DocumentAnalysis, index: dict[str, str]) -> str | None:
    if kind == "above":
        return None
    if kind in {"schedule"}:
        label = f"{match.group(1)} {match.group(2)}".lower()
        return index.get(label)
    if kind == "amendment":
        return index.get(match.group(1).lower()) or index.get(f"amendment {match.group(1)}".lower())
    number = match.group(1)
    return index.get(f"section {number}".lower()) or index.get(f"clause {number}".lower())


def _relation_for(kind: str, evidence: str) -> DependencyRelation:
    lower = evidence.lower()
    if "notwithstanding" in lower or "except" in lower:
        return DependencyRelation.EXCEPTED_BY
    if "subject to" in lower:
        return DependencyRelation.CONDITIONED_BY
    if kind == "definition" or "defined" in lower:
        return DependencyRelation.DEFINED_BY
    if kind == "schedule":
        return DependencyRelation.INCORPORATES
    if kind == "amendment":
        return DependencyRelation.OVERRIDDEN_BY
    return DependencyRelation.REFERENCES


def _fuzzy_section(analysis: DocumentAnalysis, ref: str) -> str | None:
    number = re.search(r"(\d+(?:\.\d+)*)", ref)
    if not number:
        return None
    needle = number.group(1)
    for clause in analysis.clauses:
        if needle in clause.title:
            return clause.clause_id
    return None
