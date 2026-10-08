from agent1.document_analyzer import DocumentContextAnalyst


def test_agent1_extracts_structure_and_dependencies(sample_txt):
    analysis = DocumentContextAnalyst().analyze(sample_txt)
    assert analysis.schema_version == "1.0"
    assert analysis.clauses
    assert any(item.term.lower() == "confidential information" for item in analysis.definitions)
    assert analysis.schedules
    assert analysis.amendments
    relations = {edge.relation.value for edge in analysis.dependencies}
    assert "DEFINED_BY" in relations or "REFERENCES" in relations
    assert any(c.type.value == "termination" for c in analysis.clauses)
    titles = " ".join(c.title.lower() for c in analysis.clauses)
    assert "schedule" in titles or analysis.schedules
    assert analysis.document_metadata.page_count >= 1
