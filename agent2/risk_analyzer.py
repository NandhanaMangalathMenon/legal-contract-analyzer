from __future__ import annotations

import logging
import re
from pathlib import Path

from pydantic import ValidationError

from agent1.retrieval.hybrid import HybridContractRetriever
from agent2.consultancy import build_consultancy
from agent2.cross_clause import combined_exit_cluster, detect_contradictions
from agent2.dependency_analyzer import LongRangeDependencyAnalyzer
from core.exceptions import SchemaBoundaryError
from core.logging import pipeline_event
from llm.client import LLMClient, get_llm_client
from schemas.common import SCHEMA_VERSION, EvidenceItem, Location, RiskCategory, Severity
from schemas.document import Clause, DocumentAnalysis
from schemas.risk import RiskAnalysis, RiskFactors, RiskFinding
from stores.vector_store import get_vector_store

logger = logging.getLogger(__name__)
SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "system.txt").read_text(encoding="utf-8")


RULES: list[dict] = [
    {
        "id": "auto_renewal",
        "pattern": re.compile(r"automatic(?:ally)? renew|evergreen", re.I),
        "severity": Severity.HIGH,
        "category": RiskCategory.TERMINATION,
        "title": "Automatic renewal",
        "why": "Automatic renewal can extend obligations unless notice is given in time.",
        "consequence": "The user may remain bound for another term if notice windows are missed.",
        "factors": RiskFactors(financial_exposure=2, termination_difficulty=4, asymmetry=2, obligation_strength=3),
        "questions": [
            "Does the renewal notice window apply before every renewal?",
            "Is there a right to terminate during a renewed term?",
        ],
    },
    {
        "id": "termination_notice",
        "pattern": re.compile(r"terminat.+\d+\s*days|notice.{0,40}terminat", re.I),
        "severity": Severity.MEDIUM,
        "category": RiskCategory.TERMINATION,
        "title": "Termination notice mechanics",
        "why": "Notice length and who may terminate affect exit flexibility.",
        "consequence": "A long or asymmetric notice period can delay exit.",
        "factors": RiskFactors(termination_difficulty=3, asymmetry=2, obligation_strength=3),
        "questions": [
            "Is the notice period the same for both parties?",
            "Do schedules or amendments change the notice period?",
        ],
    },
    {
        "id": "early_fee",
        "pattern": re.compile(r"early termination (fee|penalty|charge)|termination fee", re.I),
        "severity": Severity.HIGH,
        "category": RiskCategory.FINANCIAL,
        "title": "Early termination fee or penalty language",
        "why": "Fees tied to exit can create financial exposure even when termination is allowed.",
        "consequence": "Leaving the contract early may trigger additional payment obligations.",
        "factors": RiskFactors(financial_exposure=4, termination_difficulty=4, obligation_strength=4),
        "questions": [
            "Is the amount a genuine pre-estimate of loss or a penalty-style figure?",
            "When exactly does the fee apply?",
        ],
    },
    {
        "id": "unlimited_liability",
        "pattern": re.compile(r"unlimited liability", re.I),
        "severity": Severity.CRITICAL,
        "category": RiskCategory.LIABILITY,
        "title": "Unlimited liability language",
        "why": "Unlimited liability can create open-ended financial exposure.",
        "consequence": "Losses may not be capped if this language controls and is enforceable on the facts.",
        "factors": RiskFactors(financial_exposure=5, asymmetry=4, obligation_strength=5),
        "questions": [
            "Does a cap elsewhere apply, or does a schedule/amendment remove it?",
            "Which losses are excluded, if any?",
        ],
    },
    {
        "id": "liability_cap",
        "pattern": re.compile(r"liability.{0,60}(cap|not exceed|capped)", re.I),
        "severity": Severity.MEDIUM,
        "category": RiskCategory.LIABILITY,
        "title": "Liability cap",
        "why": "A cap may protect one party and still leave carve-outs.",
        "consequence": "Actual exposure depends on carve-outs, indemnity, and later modifications.",
        "factors": RiskFactors(financial_exposure=3, ambiguity=2),
        "questions": ["What is excluded from the cap?", "Do indemnities sit outside the cap?"],
    },
    {
        "id": "indemnity",
        "pattern": re.compile(r"indemnif|hold harmless", re.I),
        "severity": Severity.HIGH,
        "category": RiskCategory.LIABILITY,
        "title": "Indemnification",
        "why": "Broad indemnity can shift third-party and regulatory cost.",
        "consequence": "One party may bear defence costs and damages for a wide set of claims.",
        "factors": RiskFactors(financial_exposure=4, asymmetry=3, obligation_strength=4),
        "questions": ["Is indemnity mutual?", "Are there exclusions for the indemnified party's fault?"],
    },
    {
        "id": "noncompete",
        "pattern": re.compile(r"non-compete|not compete|restraint of trade", re.I),
        "severity": Severity.HIGH,
        "category": RiskCategory.RESTRICTIONS,
        "title": "Non-compete / restraint language",
        "why": "Post-term restrictions can limit future business activity.",
        "consequence": "The restricted party may need to pause competing work in a territory or field.",
        "factors": RiskFactors(asymmetry=4, obligation_strength=4, termination_difficulty=2),
        "questions": [
            "What is the duration, geography, and scope?",
            "How might Indian Contract Act restraint-of-trade principles interact on these facts?",
        ],
    },
    {
        "id": "ip_assign",
        "pattern": re.compile(r"hereby assign|assignment of (all )?intellectual property|work made for hire|all right, title", re.I),
        "severity": Severity.HIGH,
        "category": RiskCategory.INTELLECTUAL_PROPERTY,
        "title": "IP assignment or broad transfer",
        "why": "Ownership of work product may move away from the creating party.",
        "consequence": "The assigning party may lose residual rights in created material.",
        "factors": RiskFactors(asymmetry=4, obligation_strength=4),
        "questions": ["Does the assignment include pre-existing materials?", "Are licences exclusive and perpetual?"],
    },
    {
        "id": "privacy",
        "pattern": re.compile(r"personal data|personal information|data protection|retain.{0,20}data", re.I),
        "severity": Severity.MEDIUM,
        "category": RiskCategory.PRIVACY_DATA,
        "title": "Privacy / personal data use",
        "why": "Data sharing, retention, and processing terms can create compliance and operational duties.",
        "consequence": "The handling party may need consent, security, and deletion processes.",
        "factors": RiskFactors(obligation_strength=3, ambiguity=2),
        "questions": [
            "Who is the data fiduciary vs processor on these facts?",
            "Does DPDP Act 2023 (Central) potentially apply to the processing described?",
        ],
    },
    {
        "id": "arbitration",
        "pattern": re.compile(r"arbitration|arbitral tribunal", re.I),
        "severity": Severity.MEDIUM,
        "category": RiskCategory.DISPUTES,
        "title": "Arbitration / dispute forum",
        "why": "Dispute venue and process affect cost, appeal rights, and practical enforcement.",
        "consequence": "Court litigation may be limited if a valid arbitration clause applies.",
        "factors": RiskFactors(obligation_strength=3, ambiguity=1),
        "questions": ["Is the arbitration clause mutual and certain as to seat and rules?", "Is any consumer-protection overlay relevant?"],
    },
    {
        "id": "penalty",
        "pattern": re.compile(r"penalty|liquidated damages", re.I),
        "severity": Severity.HIGH,
        "category": RiskCategory.FINANCIAL,
        "title": "Penalty or liquidated damages language",
        "why": "Stated sums on breach can be significant and may interact with Indian Contract Act provisions on compensation.",
        "consequence": "A party in breach may face a pre-agreed sum; whether it operates as described is a legal question.",
        "factors": RiskFactors(financial_exposure=4, obligation_strength=3, ambiguity=2),
        "questions": ["Is the sum linked to a genuine pre-estimate of loss?", "Are there multiple overlapping fee clauses?"],
    },
]


class ContractRiskConsultancyAnalyst:
    """Agent 2 — risk and consultancy reasoning over the full structured contract."""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or get_llm_client()

    def analyze(self, document: DocumentAnalysis) -> RiskAnalysis:
        retriever = HybridContractRetriever(document, self.llm, get_vector_store("contract_store"))
        long_range = LongRangeDependencyAnalyzer(document, retriever)
        findings: list[RiskFinding] = []
        counter = 0
        used_clauses: set[str] = set()

        for clause in document.clauses:
            package = long_range.package_for(clause)
            for rule in RULES:
                if not rule["pattern"].search(clause.text):
                    continue
                counter += 1
                risk_id = f"R-{counter:03d}"
                evidence = [
                    EvidenceItem(
                        source_kind="contract",
                        source_id=clause.clause_id,
                        excerpt=clause.text[:500],
                        location=clause.location,
                    )
                ]
                related = package.related_ids
                finding = RiskFinding(
                    risk_id=risk_id,
                    severity=rule["severity"],
                    category=rule["category"],
                    title=rule["title"],
                    clause_ids=[clause.clause_id],
                    explanation=f"{clause.clause_id} ({clause.title}): {clause.text.strip()[:600]}",
                    why_it_matters=rule["why"],
                    potential_consequence=rule["consequence"],
                    evidence=evidence,
                    questions_for_lawyer=list(rule["questions"]),
                    risk_factors=rule["factors"],
                    related_clause_ids=related,
                    dependency_complexity=package.dependency_complexity,
                )
                finding.consultancy = build_consultancy(finding, context=package.compressed_context, llm=self.llm)
                findings.append(finding)
                used_clauses.add(clause.clause_id)

        contradictions = detect_contradictions(document)
        contradiction_notes: list[str] = []
        for item in contradictions:
            counter += 1
            risk_id = f"R-{counter:03d}"
            contradiction_notes.append(item.description)
            finding = RiskFinding(
                risk_id=risk_id,
                severity=Severity.HIGH,
                category=RiskCategory.STRUCTURAL,
                title="Potential cross-clause contradiction",
                clause_ids=item.clause_ids,
                explanation=item.description,
                why_it_matters="Contradictory notice, liability, or definition language can make rights uncertain until hierarchy is resolved.",
                potential_consequence="A party may rely on the more favourable sentence while the other sentence still exists in the document.",
                evidence=[
                    EvidenceItem(source_kind="contract", source_id=cid, excerpt=item.description)
                    for cid in item.clause_ids
                ],
                questions_for_lawyer=[
                    "Which provision controls if they cannot be read together?",
                    "Do later amendments or schedules resolve the conflict?",
                ],
                risk_factors=RiskFactors(ambiguity=5, obligation_strength=3, asymmetry=2),
                related_clause_ids=item.clause_ids,
                contradiction_ids=item.clause_ids,
                dependency_complexity=len(item.clause_ids),
            )
            finding.consultancy = build_consultancy(finding, context="Contradictory clauses", llm=self.llm)
            findings.append(finding)

        exit_ids = combined_exit_cluster(document.clauses)
        if exit_ids:
            counter += 1
            finding = RiskFinding(
                risk_id=f"R-{counter:03d}",
                severity=Severity.HIGH,
                category=RiskCategory.TERMINATION,
                title="Combined exit risk (renewal + notice + possible fees)",
                clause_ids=exit_ids,
                explanation=(
                    "Renewal, notice, and fee provisions were found in different places. "
                    "Individually they may appear routine; together they can make exit harder."
                ),
                why_it_matters="Long-range interaction between renewal, notice, and fees can reduce practical ability to leave.",
                potential_consequence="Operational lock-in and possible extra cost on exit.",
                evidence=[
                    EvidenceItem(
                        source_kind="contract",
                        source_id=cid,
                        excerpt=next(c.text for c in document.clauses if c.clause_id == cid)[:400],
                    )
                    for cid in exit_ids
                ],
                questions_for_lawyer=[
                    "How do automatic renewal, notice, and fees operate together?",
                    "Does Schedule or Amendment language change the exit path?",
                ],
                risk_factors=RiskFactors(financial_exposure=3, termination_difficulty=5, ambiguity=3, obligation_strength=3),
                related_clause_ids=exit_ids,
                dependency_complexity=len(exit_ids),
            )
            finding.consultancy = build_consultancy(finding, context="Combined exit cluster", llm=self.llm)
            findings.append(finding)

        undefined = _undefined_terms(document)
        if undefined:
            counter += 1
            finding = RiskFinding(
                risk_id=f"R-{counter:03d}",
                severity=Severity.LOW,
                category=RiskCategory.AMBIGUITY,
                title="Capitalised terms without a matching definition unit",
                clause_ids=[document.clauses[0].clause_id] if document.clauses else [],
                explanation="Some capitalised phrases were not linked to a parsed definition: " + ", ".join(undefined[:12]),
                why_it_matters="Undefined terms can shift meaning if a later schedule or industry usage is applied.",
                potential_consequence="Ambiguous duties or rights.",
                questions_for_lawyer=["Should these terms be defined or mapped to existing definitions?"],
                risk_factors=RiskFactors(ambiguity=3),
            )
            finding.consultancy = build_consultancy(finding, context="Undefined terms", llm=self.llm)
            findings.append(finding)

        # Optional LLM commentary is additive and never replaces structured findings.
        if document.clauses:
            self.llm.generate(
                f"Review this evidence package for missed interactions. Do not invent law.\n{document.clauses[0].text[:1500]}",
                system=SYSTEM_PROMPT,
            )

        obligations = [
            f"{c.clause_id}: {c.title}"
            for c in document.clauses
            if c.type.value in {"obligations", "payment", "confidentiality", "termination"} or "shall" in c.text.lower()
        ][:20]

        analysis = RiskAnalysis(
            schema_version=SCHEMA_VERSION,
            document_id=document.document_id,
            risks=findings,
            contradictions=contradiction_notes,
            major_obligations=obligations or ["No obvious 'shall' obligations were parsed; review the source document."],
        )
        try:
            validated = RiskAnalysis.model_validate(analysis.model_dump())
        except ValidationError as exc:
            raise SchemaBoundaryError(f"Agent 2 output failed validation: {exc}") from exc
        pipeline_event(
            logger,
            document_id=validated.document_id,
            agent="agent2",
            input_schema_version=document.schema_version,
            output_schema_version=validated.schema_version,
            retrieved_clause_ids=sorted(used_clauses),
            risk_count=len(validated.risks),
        )
        return validated


def _undefined_terms(document: DocumentAnalysis) -> list[str]:
    defined = {d.term.lower() for d in document.definitions}
    skip = {
        "the",
        "this",
        "party",
        "agreement",
        "section",
        "schedule",
        "page",
        "india",
        "clause",
        "either",
        "notwithstanding",
    }
    candidates: list[str] = []
    for clause in document.clauses:
        for term in re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", clause.text):
            if term.lower() in defined or term.lower().split()[0].lower() in skip:
                continue
            if term not in candidates:
                candidates.append(term)
    return candidates
