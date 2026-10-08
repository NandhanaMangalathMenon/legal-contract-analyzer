from __future__ import annotations

from pydantic import BaseModel, Field

from schemas.common import SCHEMA_VERSION, EvidenceItem, RiskCategory, Severity


class RiskFactors(BaseModel):
    financial_exposure: int = Field(ge=0, le=5, default=0)
    termination_difficulty: int = Field(ge=0, le=5, default=0)
    asymmetry: int = Field(ge=0, le=5, default=0)
    ambiguity: int = Field(ge=0, le=5, default=0)
    obligation_strength: int = Field(ge=0, le=5, default=0)


class ConsultancyInsight(BaseModel):
    what_the_clause_says: str
    why_it_matters: str
    who_is_disadvantaged: str | None = None
    dependency_note: str | None = None
    potential_impact: list[str] = Field(default_factory=list)
    questions_for_lawyer: list[str] = Field(default_factory=list)
    negotiation_consideration: str | None = None
    priority: Severity


class RiskFinding(BaseModel):
    risk_id: str
    severity: Severity
    category: RiskCategory
    title: str
    clause_ids: list[str]
    explanation: str
    why_it_matters: str
    potential_consequence: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    questions_for_lawyer: list[str] = Field(default_factory=list)
    risk_factors: RiskFactors = Field(default_factory=RiskFactors)
    consultancy: ConsultancyInsight | None = None
    related_clause_ids: list[str] = Field(default_factory=list)
    dependency_complexity: int = 0
    contradiction_ids: list[str] = Field(default_factory=list)


class RiskAnalysis(BaseModel):
    schema_version: str = SCHEMA_VERSION
    document_id: str
    risks: list[RiskFinding] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    major_obligations: list[str] = Field(default_factory=list)
    analysis_warnings: list[str] = Field(default_factory=list)
