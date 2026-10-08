from __future__ import annotations

from pydantic import BaseModel, Field

from schemas.common import SCHEMA_VERSION, Severity
from schemas.document import Party
from schemas.risk import RiskFinding
from schemas.verification import LegalSource, VerificationResult


class PrioritizedIssue(BaseModel):
    risk_id: str
    title: str
    severity: Severity
    priority_score: int
    score_breakdown: dict[str, int] = Field(default_factory=dict)
    clause_ids: list[str] = Field(default_factory=list)
    explanation: str
    why_it_matters: str
    questions_for_lawyer: list[str] = Field(default_factory=list)
    negotiation_consideration: str | None = None
    verification: VerificationResult | None = None
    dependency_complexity: int = 0


class FinalContractReport(BaseModel):
    schema_version: str = SCHEMA_VERSION
    document_id: str
    filename: str
    executive_summary: str
    parties: list[Party] = Field(default_factory=list)
    contract_purpose: str | None = None
    major_obligations: list[str] = Field(default_factory=list)
    critical_risks: list[PrioritizedIssue] = Field(default_factory=list)
    high_risks: list[PrioritizedIssue] = Field(default_factory=list)
    medium_risks: list[PrioritizedIssue] = Field(default_factory=list)
    low_and_info_risks: list[PrioritizedIssue] = Field(default_factory=list)
    cross_clause_dependencies: list[str] = Field(default_factory=list)
    potential_contradictions: list[str] = Field(default_factory=list)
    financial_exposure: list[PrioritizedIssue] = Field(default_factory=list)
    termination_and_renewal: list[PrioritizedIssue] = Field(default_factory=list)
    liability_and_indemnity: list[PrioritizedIssue] = Field(default_factory=list)
    ip_data_confidentiality: list[PrioritizedIssue] = Field(default_factory=list)
    legal_context: list[LegalSource] = Field(default_factory=list)
    questions_for_lawyer: list[str] = Field(default_factory=list)
    suggested_review_points: list[str] = Field(default_factory=list)
    sources: list[LegalSource] = Field(default_factory=list)
    human_review_warnings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    not_legal_advice: str = (
        "This report is decision-support only. It is not legal advice, does not replace "
        "a qualified lawyer, and does not tell the user whether to sign a contract."
    )
