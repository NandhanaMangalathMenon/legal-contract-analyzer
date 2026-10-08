from __future__ import annotations

import logging
from pathlib import Path

from pydantic import ValidationError

from agent1.dependency_graph import ContractDependencyGraph
from agent3.evidence_checker import contract_supports_finding
from agent3.legal_retriever import Agent3LegalRetriever
from core.config import get_settings
from core.exceptions import SchemaBoundaryError
from core.logging import pipeline_event
from llm.client import LLMClient, get_llm_client
from schemas.common import SCHEMA_VERSION, VerificationStatus
from schemas.document import DocumentAnalysis
from schemas.risk import RiskAnalysis, RiskFinding
from schemas.verification import VerificationResult, VerifiedAnalysis

logger = logging.getLogger(__name__)
SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "system.txt").read_text(encoding="utf-8")

TOPIC_QUERIES = {
    "financial": "penalty liquidated damages compensation Indian Contract Act section 73 74",
    "termination": "termination insolvency moratorium contract obligations",
    "liability": "liability consumer protection unfair contract consideration section 23",
    "restrictions": "restraint of trade non-compete Indian Contract Act section 27 Competition Act",
    "intellectual_property": "assignment of copyright Patents Act Trade Marks Act",
    "privacy_data": "Digital Personal Data Protection Act personal data Information Technology Act",
    "disputes": "arbitration agreement Arbitration and Conciliation Act section 7 8",
    "ambiguity": "what agreements are contracts free consent Indian Contract Act section 10",
    "structural": "amendment hierarchy contract interpretation official text required",
}


class IndiaCentralLawVerifier:
    """Agent 3 — verifies Agent 2 findings against contract evidence and retrieved Central Law notes."""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or get_llm_client()
        self.retriever = Agent3LegalRetriever(self.llm)

    def verify(self, document: DocumentAnalysis, risks: RiskAnalysis) -> VerifiedAnalysis:
        if risks.document_id != document.document_id:
            raise SchemaBoundaryError("RiskAnalysis.document_id does not match DocumentAnalysis.document_id")
        graph = ContractDependencyGraph(document)
        settings = get_settings()
        results: list[VerificationResult] = []
        for finding in risks.risks:
            results.append(self._verify_one(document, finding, graph, settings.human_review_confidence_threshold))
        analysis = VerifiedAnalysis(
            schema_version=SCHEMA_VERSION,
            document_id=document.document_id,
            results=results,
        )
        try:
            validated = VerifiedAnalysis.model_validate(analysis.model_dump())
        except ValidationError as exc:
            raise SchemaBoundaryError(f"Agent 3 output failed validation: {exc}") from exc
        pipeline_event(
            logger,
            document_id=validated.document_id,
            agent="agent3",
            input_schema_version=risks.schema_version,
            output_schema_version=validated.schema_version,
            retrieved_legal_source_ids=[
                src.source_id for item in validated.results for src in item.legal_sources
            ],
            verification_statuses=[item.verification_status.value for item in validated.results],
        )
        return validated

    def _verify_one(
        self,
        document: DocumentAnalysis,
        finding: RiskFinding,
        graph: ContractDependencyGraph,
        threshold: float,
    ) -> VerificationResult:
        supported, evidence, notes = contract_supports_finding(document, finding)
        query = TOPIC_QUERIES.get(finding.category.value, finding.title)
        legal_sources = self.retriever.search(query + " " + finding.title, k=4)
        human_reasons: list[str] = list(notes)
        status = VerificationStatus.LEGAL_SUPPORT_NOT_FOUND
        confidence = 0.35
        contract_ok = supported

        if not supported:
            status = VerificationStatus.UNSUPPORTED
            confidence = 0.2
            human_reasons.append("Cited contract units could not all be located.")
        elif legal_sources:
            status = VerificationStatus.PARTIALLY_SUPPORTED
            confidence = 0.62
            # Seed notes are summaries, never full official text.
            human_reasons.append(
                "Legal hits are research notes pointing to India Code; they are not a complete official extract."
            )
            if finding.category.value in {"restrictions", "disputes", "privacy_data", "intellectual_property"}:
                status = VerificationStatus.PARTIALLY_SUPPORTED
                confidence = 0.58
            if finding.dependency_complexity >= 6 or finding.contradiction_ids:
                status = VerificationStatus.HUMAN_REVIEW_REQUIRED
                human_reasons.append("High dependency complexity or contradiction cluster.")
                confidence = min(confidence, 0.5)
            if document.document_metadata.ocr_used or document.document_metadata.extraction_confidence < 0.7:
                status = VerificationStatus.HUMAN_REVIEW_REQUIRED
                human_reasons.append("Document extraction confidence is reduced.")
        else:
            status = VerificationStatus.LEGAL_SUPPORT_NOT_FOUND
            human_reasons.append("No seeded Central Law note matched this topic.")

        if "state" in (document.document_metadata.jurisdiction_text or "").lower() and "india" not in (
            document.document_metadata.jurisdiction_text or ""
        ).lower():
            status = VerificationStatus.STATE_LAW_REQUIRED
            human_reasons.append("Document jurisdiction text may implicate State law; not guessed.")

        if finding.risk_factors.financial_exposure >= 5:
            human_reasons.append("Significant financial-exposure factor; professional review is warranted.")
            status = VerificationStatus.HUMAN_REVIEW_REQUIRED

        if confidence < threshold and status not in {
            VerificationStatus.UNSUPPORTED,
            VerificationStatus.STATE_LAW_REQUIRED,
        }:
            status = VerificationStatus.HUMAN_REVIEW_REQUIRED
            human_reasons.append("Confidence below configured threshold.")

        related = graph.neighbors(finding.clause_ids[0], hops=2) if finding.clause_ids else []
        contract_context = "\n".join(f"[{item.source_id}] {item.excerpt}" for item in evidence)
        legal_context = "\n".join(f"[{item.source_id}] {item.document_name} Section {item.section}: {item.excerpt}" for item in legal_sources)
        
        prompt = f"""
        Risk ID: {finding.risk_id}
        Title: {finding.title}
        Finding explanation: {finding.explanation}
        Finding why it matters: {finding.why_it_matters}
        
        Contract Evidence:
        {contract_context}
        
        Legal Sources:
        {legal_context}
        
        Pre-computed status: {status.value} (If unsupported or state law required, keep this or downgrade to human review).
        
        Analyze the risk finding against the contract evidence and the legal sources. Output a JSON object with:
        - "verification_status": string (VERIFIED, PARTIALLY_SUPPORTED, UNSUPPORTED, CONTRADICTED, LEGAL_SUPPORT_NOT_FOUND, STATE_LAW_REQUIRED, HUMAN_REVIEW_REQUIRED)
        - "reasoning": string (explain why)
        - "what_the_contract_says": string
        - "what_the_law_says": string
        - "what_the_system_inferred": string
        """
        
        try:
            llm_res = self.llm.generate_json(prompt, system=SYSTEM_PROMPT)
            llm_status = VerificationStatus(llm_res.get("verification_status", status.value))
            reasoning = llm_res.get("reasoning", "LLM verification failed.")
            wtcs = llm_res.get("what_the_contract_says", finding.explanation)
            wtls = llm_res.get("what_the_law_says", "LEGAL_SUPPORT_NOT_FOUND")
            wtsi = llm_res.get("what_the_system_inferred", finding.why_it_matters)
            if llm_status == VerificationStatus.UNSUPPORTED or llm_status == VerificationStatus.LEGAL_SUPPORT_NOT_FOUND:
                confidence = min(confidence, 0.4)
        except Exception as e:
            logger.warning(f"Agent 3 LLM verification failed for {finding.risk_id}: {e}")
            llm_status = status
            reasoning = (
                f"Contract support={'yes' if contract_ok else 'no'}. "
                f"Retrieved {len(legal_sources)} Central Law research note(s). "
                "Commercial unfavourability is not treated as illegality. "
                + " ".join(human_reasons)
            )
            wtcs = finding.explanation
            wtls = legal_sources[0].excerpt if legal_sources else "LEGAL_SUPPORT_NOT_FOUND in the seeded knowledge base."
            wtsi = finding.why_it_matters

        if llm_status in {VerificationStatus.HUMAN_REVIEW_REQUIRED, VerificationStatus.STATE_LAW_REQUIRED}:
            requires_human = True
        else:
            requires_human = status in {
                VerificationStatus.HUMAN_REVIEW_REQUIRED,
                VerificationStatus.STATE_LAW_REQUIRED,
                VerificationStatus.CONTRADICTED,
                VerificationStatus.LEGAL_SUPPORT_NOT_FOUND,
            } or bool(finding.contradiction_ids)

        return VerificationResult(
            risk_id=finding.risk_id,
            verification_status=llm_status,
            contract_supported=contract_ok,
            confidence=confidence,
            contract_evidence=evidence,
            legal_sources=legal_sources,
            reasoning=reasoning,
            what_the_contract_says=wtcs,
            what_the_law_says=wtls,
            what_the_system_inferred=wtsi,
            requires_human_review=requires_human,
            human_review_reasons=human_reasons,
        )
