from __future__ import annotations

from pydantic import BaseModel, Field

from schemas.common import SCHEMA_VERSION, EvidenceItem, VerificationStatus


class LegalSource(BaseModel):
    source_id: str
    document_name: str
    section: str | None = None
    title: str | None = None
    excerpt: str
    authority: str
    source: str
    source_url: str | None = None
    version_date: str | None = None
    score: float | None = None


class VerificationResult(BaseModel):
    risk_id: str
    verification_status: VerificationStatus
    contract_supported: bool
    confidence: float = Field(ge=0.0, le=1.0)
    contract_evidence: list[EvidenceItem] = Field(default_factory=list)
    legal_sources: list[LegalSource] = Field(default_factory=list)
    reasoning: str
    what_the_contract_says: str | None = None
    what_the_law_says: str | None = None
    what_the_system_inferred: str | None = None
    requires_human_review: bool = False
    human_review_reasons: list[str] = Field(default_factory=list)


class VerifiedAnalysis(BaseModel):
    schema_version: str = SCHEMA_VERSION
    document_id: str
    results: list[VerificationResult] = Field(default_factory=list)
    jurisdiction_scope: str = "INDIAN_CENTRAL_LAW"
    coverage_disclaimer: str = (
        "Legal knowledge is a limited, non-exhaustive seed of Indian Central Law "
        "summaries for decision support. It is not official statutory text and is not legal advice."
    )
