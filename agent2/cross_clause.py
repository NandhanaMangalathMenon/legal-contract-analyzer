from __future__ import annotations

import re
from dataclasses import dataclass

from schemas.document import Clause, DocumentAnalysis

NOTICE_RE = re.compile(r"(\d+)\s*days['’]?\s*notice", re.I)
LIABILITY_UNLIMITED = re.compile(r"unlimited liability|liability shall be unlimited", re.I)
LIABILITY_CAP = re.compile(r"capped at|liability.{0,40}not exceed|maximum liability", re.I)


@dataclass
class Contradiction:
    description: str
    clause_ids: list[str]


def detect_contradictions(analysis: DocumentAnalysis) -> list[Contradiction]:
    found: list[Contradiction] = []
    notices: list[tuple[str, int, str]] = []
    for clause in analysis.clauses:
        for match in NOTICE_RE.finditer(clause.text):
            notices.append((clause.clause_id, int(match.group(1)), match.group(0)))
    unique_days = {item[1] for item in notices}
    if len(unique_days) > 1:
        ids = [item[0] for item in notices]
        found.append(
            Contradiction(
                description="Notice periods differ across clauses: "
                + "; ".join(f"{cid} ({text})" for cid, _days, text in notices),
                clause_ids=ids,
            )
        )

    caps: list[str] = []
    unlimited: list[str] = []
    for clause in analysis.clauses:
        if LIABILITY_CAP.search(clause.text):
            caps.append(clause.clause_id)
        if LIABILITY_UNLIMITED.search(clause.text):
            unlimited.append(clause.clause_id)
    if caps and unlimited:
        found.append(
            Contradiction(
                description="Liability appears capped in some provisions and unlimited in others.",
                clause_ids=caps + unlimited,
            )
        )

    saturday_def = [
        d for d in analysis.definitions if "business day" in d.term.lower() and "saturday" in d.text.lower()
    ]
    saturday_use = [
        c for c in analysis.clauses if "including saturday" in c.text.lower() or "includes saturday" in c.text.lower()
    ]
    if saturday_def and saturday_use:
        found.append(
            Contradiction(
                description="Business Day definition may conflict with a schedule or clause that includes Saturday.",
                clause_ids=[saturday_def[0].definition_id] + [c.clause_id for c in saturday_use],
            )
        )
    return found


def combined_exit_cluster(clauses: list[Clause]) -> list[str]:
    renewal = [c.clause_id for c in clauses if "renew" in c.text.lower()]
    notice = [c.clause_id for c in clauses if NOTICE_RE.search(c.text)]
    penalty = [c.clause_id for c in clauses if re.search(r"early termination|termination fee|penalty", c.text, re.I)]
    if renewal and notice:
        return sorted(set(renewal + notice + penalty))
    return []
