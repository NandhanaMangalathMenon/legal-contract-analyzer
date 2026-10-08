import pytest
from pydantic import ValidationError

from schemas.common import SCHEMA_VERSION, Severity
from schemas.document import DocumentAnalysis, DocumentMetadata
from schemas.risk import RiskAnalysis, RiskFinding, RiskFactors
from schemas.verification import VerificationResult, VerifiedAnalysis, VerificationStatus


def test_document_analysis_requires_metadata():
    with pytest.raises(ValidationError):
        DocumentAnalysis(document_id="DOC-1", filename="x.txt")


def test_risk_factors_bounded():
    with pytest.raises(ValidationError):
        RiskFactors(financial_exposure=9)


def test_agent3_cannot_drop_schema_version():
    finding = RiskFinding(
        risk_id="R-001",
        severity=Severity.LOW,
        category="ambiguity",
        title="t",
        clause_ids=["C-001"],
        explanation="e",
        why_it_matters="w",
        potential_consequence="p",
    )
    analysis = RiskAnalysis(document_id="DOC-1", risks=[finding])
    assert analysis.schema_version == SCHEMA_VERSION
    verified = VerifiedAnalysis(
        document_id="DOC-1",
        results=[
            VerificationResult(
                risk_id="R-001",
                verification_status=VerificationStatus.LEGAL_SUPPORT_NOT_FOUND,
                contract_supported=True,
                confidence=0.4,
                reasoning="seed empty",
            )
        ],
    )
    assert verified.results[0].risk_id == "R-001"
