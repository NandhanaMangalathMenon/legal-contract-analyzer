from agent1.document_analyzer import DocumentContextAnalyst
from agent1.retrieval.hybrid import HybridContractRetriever
from llm.client import get_llm_client
from stores.vector_store import get_vector_store


def test_hybrid_retriever_uses_graph_and_exact_refs(sample_txt):
    document = DocumentContextAnalyst().analyze(sample_txt)
    retriever = HybridContractRetriever(document, get_llm_client(), get_vector_store("contract_store"))
    target = next(c for c in document.clauses if "terminat" in c.text.lower())
    ranked = retriever.retrieve("notwithstanding Section 5 termination", target_id=target.clause_id, k=8)
    methods = {item.method for item in ranked}
    assert "dependency_graph" in methods or "exact_xref" in methods
    assert ranked
