from agent1.document_analyzer import DocumentContextAnalyst
from agent2.risk_analyzer import ContractRiskConsultancyAnalyst


def test_sample_contract_contains_known_risk_examples(sample_txt):
    document = DocumentContextAnalyst().analyze(sample_txt)
    risks = ContractRiskConsultancyAnalyst().analyze(document)
    blob = " ".join(r.title.lower() + " " + r.explanation.lower() for r in risks.risks)
    for needle in [
        "renew",
        "termin",
        "penalty",
        "liability",
        "indemn",
        "intellectual",
        "data",
        "compete",
        "arbitr",
    ]:
        assert needle in blob
    assert document.definitions
    assert document.schedules
    assert document.amendments
    assert any("notwithstanding" in c.text.lower() for c in document.clauses)
