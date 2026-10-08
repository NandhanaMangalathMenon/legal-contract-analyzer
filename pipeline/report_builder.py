from __future__ import annotations

from core.scoring import explainable_priority_score
from schemas.common import RiskCategory, SCHEMA_VERSION, Severity
from schemas.document import DocumentAnalysis
from schemas.final_report import FinalContractReport, PrioritizedIssue
from schemas.risk import RiskAnalysis, RiskFinding
from schemas.verification import VerifiedAnalysis, VerificationResult

LIMITATIONS = [
    "This system is not a lawyer and does not provide legal advice.",
    "It does not tell the user whether to sign a contract.",
    "Indian Central Law coverage is a limited seed of research notes, not official complete Act text.",
    "State law, foreign law, and unincorporated documents are out of scope unless later added.",
    "OCR quality, missing schedules, and unclear amendment hierarchy can change meaning.",
    "Commercial unfavourability is not treated as illegality or unenforceability.",
    "Facts outside the uploaded document (course of dealing, side letters, oral variations) are not analysed.",
]


class FinalReportBuilder:
    """Deterministic merge of the three agent outputs. No LLM recombination."""

    def build(
        self,
        document: DocumentAnalysis,
        risks: RiskAnalysis,
        verified: VerifiedAnalysis,
    ) -> FinalContractReport:
        by_risk = {item.risk_id: item for item in verified.results}
        issues = [_to_issue(finding, by_risk.get(finding.risk_id)) for finding in risks.risks]
        issues.sort(key=lambda item: (-item.priority_score, item.risk_id))

        def bucket(severity: Severity) -> list[PrioritizedIssue]:
            return [item for item in issues if item.severity == severity]

        questions: list[str] = []
        review_points: list[str] = []
        human: list[str] = []
        for issue in issues:
            for question in issue.questions_for_lawyer:
                if question not in questions:
                    questions.append(question)
            if issue.negotiation_consideration and issue.negotiation_consideration not in review_points:
                review_points.append(issue.negotiation_consideration)
            if issue.verification and issue.verification.requires_human_review:
                human.append(f"{issue.risk_id}: " + "; ".join(issue.verification.human_review_reasons[:3]))

        sources = []
        seen_src = set()
        for result in verified.results:
            for src in result.legal_sources:
                if src.source_id not in seen_src:
                    seen_src.add(src.source_id)
                    sources.append(src)

        deps = []
        for edge in document.dependencies[:40]:
            deps.append(f"{edge.source_id} -{edge.relation.value}-> {edge.target_id}")

        summary = _executive_summary(document, issues, human)
        return FinalContractReport(
            schema_version=SCHEMA_VERSION,
            document_id=document.document_id,
            filename=document.filename,
            executive_summary=summary,
            parties=document.parties,
            contract_purpose=document.contract_purpose,
            major_obligations=risks.major_obligations,
            critical_risks=bucket(Severity.CRITICAL),
            high_risks=bucket(Severity.HIGH),
            medium_risks=bucket(Severity.MEDIUM),
            low_and_info_risks=[i for i in issues if i.severity in {Severity.LOW, Severity.INFO}],
            cross_clause_dependencies=deps,
            potential_contradictions=risks.contradictions,
            financial_exposure=_by_category(issues, {RiskCategory.FINANCIAL}),
            termination_and_renewal=_by_category(issues, {RiskCategory.TERMINATION}),
            liability_and_indemnity=_by_category(issues, {RiskCategory.LIABILITY}),
            ip_data_confidentiality=_by_category(
                issues,
                {RiskCategory.INTELLECTUAL_PROPERTY, RiskCategory.PRIVACY_DATA, RiskCategory.RESTRICTIONS},
            ),
            legal_context=sources[:15],
            questions_for_lawyer=questions[:30],
            suggested_review_points=review_points[:20],
            sources=sources,
            human_review_warnings=human,
            limitations=LIMITATIONS,
        )


def _to_issue(finding: RiskFinding, verification: VerificationResult | None) -> PrioritizedIssue:
    legal_uncertainty = 0
    if verification:
        if verification.verification_status.value in {"LEGAL_SUPPORT_NOT_FOUND", "STATE_LAW_REQUIRED", "HUMAN_REVIEW_REQUIRED"}:
            legal_uncertainty = 6
        elif verification.verification_status.value == "PARTIALLY_SUPPORTED":
            legal_uncertainty = 3
    score, parts = explainable_priority_score(finding, finding.dependency_complexity)
    parts = dict(parts)
    parts["legal_uncertainty"] = legal_uncertainty
    return PrioritizedIssue(
        risk_id=finding.risk_id,
        title=finding.title,
        severity=finding.severity,
        priority_score=score + legal_uncertainty,
        score_breakdown=parts,
        clause_ids=finding.clause_ids,
        explanation=finding.explanation,
        why_it_matters=finding.why_it_matters,
        questions_for_lawyer=finding.questions_for_lawyer,
        negotiation_consideration=finding.consultancy.negotiation_consideration if finding.consultancy else None,
        verification=verification,
        dependency_complexity=finding.dependency_complexity,
    )


def _category_guess(issue: PrioritizedIssue) -> str:
    title = issue.title.lower()
    if "termin" in title or "renew" in title or "exit" in title:
        return RiskCategory.TERMINATION.value
    if "liab" in title or "indemn" in title:
        return RiskCategory.LIABILITY.value
    if "fee" in title or "penalty" in title or "financial" in title:
        return RiskCategory.FINANCIAL.value
    if "ip" in title or "copyright" in title or "assign" in title:
        return RiskCategory.INTELLECTUAL_PROPERTY.value
    if "privacy" in title or "data" in title:
        return RiskCategory.PRIVACY_DATA.value
    if "compete" in title or "solicit" in title:
        return RiskCategory.RESTRICTIONS.value
    return "other"


def _by_category(issues: list[PrioritizedIssue], categories: set[RiskCategory]) -> list[PrioritizedIssue]:
    wanted = {c.value for c in categories}
    return [issue for issue in issues if _category_guess(issue) in wanted]


def _executive_summary(document: DocumentAnalysis, issues: list[PrioritizedIssue], human: list[str]) -> str:
    top = issues[:5]
    lines = [
        f"Document {document.filename} was analysed as a connected contract structure, not as isolated sentences.",
        f"Parsed {len(document.clauses)} units, {len(document.definitions)} definitions, "
        f"{len(document.schedules)} schedules, {len(document.amendments)} amendments, "
        f"and {len(document.dependencies)} dependency edges.",
        "This is decision-support only. It is not a recommendation to sign or refuse the contract.",
    ]
    if top:
        lines.append("Highest ranked issues: " + "; ".join(f"{i.risk_id} {i.title}" for i in top) + ".")
    if human:
        lines.append("Human review flags were raised. A qualified lawyer should review those items.")
    return " ".join(lines)
