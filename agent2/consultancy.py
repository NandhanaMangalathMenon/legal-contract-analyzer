from __future__ import annotations

from typing import Any
from schemas.common import Severity
from schemas.risk import ConsultancyInsight, RiskFinding


def build_consultancy(finding: RiskFinding, context: str = "", llm: Any | None = None) -> ConsultancyInsight:
    consideration = (
        "Review this provision carefully and consider asking whether it can be clarified or narrowed. "
        "This is a review consideration, not an instruction to demand a change, and not a recommendation to agree or refuse."
    )
    insight = ConsultancyInsight(
        what_the_clause_says=finding.explanation,
        why_it_matters=finding.why_it_matters,
        who_is_disadvantaged=_who(finding),
        dependency_note=(
            "Interpretation may change because of related definitions, exceptions, schedules, or amendments."
            if finding.related_clause_ids or finding.dependency_complexity
            else None
        ),
        potential_impact=_impacts(finding),
        questions_for_lawyer=finding.questions_for_lawyer,
        negotiation_consideration=consideration,
        priority=finding.severity,
    )
    if llm and context:
        prompt = f"""
        Risk Finding: {finding.title}
        Context: {context}
        
        Generate a consultancy insight JSON object containing:
        - "what_the_clause_says": string (plain English explanation)
        - "why_it_matters": string
        - "who_is_disadvantaged": string
        - "negotiation_consideration": string
        - "questions_for_lawyer": list of strings
        """
        try:
            res = llm.generate_json(prompt, system="You are Agent 2, a contract consultancy analyst. Do not give legal advice.")
            if res.get("what_the_clause_says"):
                insight.what_the_clause_says = res["what_the_clause_says"]
            if res.get("why_it_matters"):
                insight.why_it_matters = res["why_it_matters"]
            if res.get("who_is_disadvantaged"):
                insight.who_is_disadvantaged = res["who_is_disadvantaged"]
            if res.get("negotiation_consideration"):
                insight.negotiation_consideration = res["negotiation_consideration"]
            if res.get("questions_for_lawyer"):
                insight.questions_for_lawyer = res["questions_for_lawyer"]
        except Exception:
            pass
            
    return insight


def _who(finding: RiskFinding) -> str:
    if finding.risk_factors.asymmetry >= 3:
        return "The party with weaker termination, liability, or fee rights may bear a greater practical burden. Confirm with a lawyer which party that is on the facts."
    return "Burden allocation is not clearly one-sided from the extracted text alone. A lawyer should map this to the parties' roles."


def _impacts(finding: RiskFinding) -> list[str]:
    mapping = {
        "financial": "financial",
        "termination": "termination",
        "liability": "legal",
        "restrictions": "operational",
        "intellectual_property": "IP",
        "privacy_data": "data/privacy",
        "disputes": "legal",
        "ambiguity": "operational",
        "structural": "strategic",
    }
    return [mapping.get(finding.category.value, "operational")]
