import json
from pathlib import Path

from pipeline.orchestrator import run_pipeline
from schemas.final_report import FinalContractReport


def test_end_to_end_txt_pipeline(sample_txt, tmp_path):
    output = tmp_path / "report.json"
    report = run_pipeline(sample_txt, output)
    assert isinstance(report, FinalContractReport)
    assert "not legal advice" in report.not_legal_advice.lower()
    assert "sign" not in report.executive_summary.lower() or "not a recommendation to sign" in report.executive_summary.lower()
    assert report.critical_risks or report.high_risks
    assert report.questions_for_lawyer
    assert report.limitations
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["document_analysis"]["schema_version"] == "1.0"
    assert payload["risk_analysis"]["schema_version"] == "1.0"
    assert payload["verified_analysis"]["schema_version"] == "1.0"
    assert payload["final_report"]["document_id"] == report.document_id
    risk_ids = [r["risk_id"] for r in payload["risk_analysis"]["risks"]]
    verified_ids = [r["risk_id"] for r in payload["verified_analysis"]["results"]]
    assert risk_ids == verified_ids


def test_pdf_pipeline_when_sample_exists(tmp_path):
    from data.sample_contracts.build_sample_pdf import build

    pdf_path = build()
    assert Path(pdf_path).exists()
    report = run_pipeline(pdf_path, tmp_path / "pdf.json")
    assert report.filename.endswith(".pdf")
    assert report.document_id
