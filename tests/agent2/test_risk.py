from agent1.document_analyzer import DocumentContextAnalyst
from agent2.risk_analyzer import ContractRiskConsultancyAnalyst


def test_agent2_finds_cross_clause_and_consultancy(sample_txt):
    document = DocumentContextAnalyst().analyze(sample_txt)
    risks = ContractRiskConsultancyAnalyst().analyze(document)
    assert risks.document_id == document.document_id
    assert all(item.risk_id.startswith("R-") for item in risks.risks)
    titles = " ".join(item.title.lower() for item in risks.risks)
    assert "renew" in titles or "termination" in titles
    assert risks.contradictions or any(item.contradiction_ids for item in risks.risks)
    clustered = [item for item in risks.risks if len(item.clause_ids) > 1]
    assert clustered
    assert all(item.consultancy is not None for item in risks.risks)
    assert all("sign" not in (item.consultancy.negotiation_consideration or "").lower() for item in risks.risks)
