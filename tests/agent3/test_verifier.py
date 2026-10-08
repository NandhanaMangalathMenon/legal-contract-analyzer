from agent1.document_analyzer import DocumentContextAnalyst
from agent2.risk_analyzer import ContractRiskConsultancyAnalyst
from agent3.verifier import IndiaCentralLawVerifier
from schemas.common import VerificationStatus


def test_agent3_preserves_risk_ids_and_does_not_invent_sources(sample_txt):
    document = DocumentContextAnalyst().analyze(sample_txt)
    risks = ContractRiskConsultancyAnalyst().analyze(document)
    verified = IndiaCentralLawVerifier().verify(document, risks)
    assert [item.risk_id for item in verified.results] == [item.risk_id for item in risks.risks]
    allowed = {status.value for status in VerificationStatus}
    for item in verified.results:
        assert item.verification_status.value in allowed
        assert item.what_the_contract_says
        assert item.what_the_law_says
        assert item.what_the_system_inferred
        for source in item.legal_sources:
            assert source.source_url
            assert "research note" in source.excerpt.lower() or source.authority == "central_act_summary"
