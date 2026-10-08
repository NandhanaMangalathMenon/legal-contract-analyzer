from __future__ import annotations

from schemas.common import EvidenceItem
from schemas.document import DocumentAnalysis
from schemas.risk import RiskFinding


def contract_supports_finding(document: DocumentAnalysis, finding: RiskFinding) -> tuple[bool, list[EvidenceItem], list[str]]:
    """Deterministic check that cited clause IDs exist and contain overlapping evidence text."""
    units: dict[str, str] = {}
    for clause in document.clauses:
        units[clause.clause_id] = clause.text
    for definition in document.definitions:
        units[definition.definition_id] = definition.text
    for schedule in document.schedules:
        units[schedule.schedule_id] = schedule.text
    for annexure in document.annexures:
        units[annexure.annexure_id] = annexure.text
    for amendment in document.amendments:
        units[amendment.amendment_id] = amendment.text

    missing = [cid for cid in finding.clause_ids if cid not in units]
    evidence: list[EvidenceItem] = []
    for cid in finding.clause_ids:
        if cid in units:
            evidence.append(
                EvidenceItem(
                    source_kind="contract",
                    source_id=cid,
                    excerpt=units[cid][:500],
                )
            )
    supported = not missing and bool(finding.clause_ids)
    notes = [f"Missing contract unit: {item}" for item in missing]
    if finding.contradiction_ids:
        notes.append("Contradiction cluster present; human review of hierarchy is warranted.")
    return supported, evidence, notes
