from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from pydantic import ValidationError

from agent1.document_analyzer import DocumentContextAnalyst
from agent2.risk_analyzer import ContractRiskConsultancyAnalyst
from agent3.verifier import IndiaCentralLawVerifier
from core.config import get_settings
from core.exceptions import PipelineError, SchemaBoundaryError
from core.logging import configure_logging, pipeline_event
from llm.client import get_llm_client
from pipeline.report_builder import FinalReportBuilder
from schemas.final_report import FinalContractReport

logger = logging.getLogger(__name__)


def run_pipeline(file_path: str | Path, output_path: str | Path | None = None) -> FinalContractReport:
    configure_logging()
    path = Path(file_path)
    if not path.exists():
        raise PipelineError(f"Input file not found: {path}")
    llm = get_llm_client()
    agent1 = DocumentContextAnalyst(llm=llm)
    agent2 = ContractRiskConsultancyAnalyst(llm=llm)
    agent3 = IndiaCentralLawVerifier(llm=llm)
    builder = FinalReportBuilder()

    document = agent1.analyze(path)
    risks = agent2.analyze(document)
    verified = agent3.verify(document, risks)
    if [item.risk_id for item in verified.results] != [item.risk_id for item in risks.risks]:
        raise SchemaBoundaryError("Agent 3 changed or reordered risk identities")
    report = builder.build(document, risks, verified)

    settings = get_settings()
    destination = Path(output_path) if output_path else settings.processed_dir / f"{document.document_id}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "document_analysis": json.loads(document.model_dump_json()),
        "risk_analysis": json.loads(risks.model_dump_json()),
        "verified_analysis": json.loads(verified.model_dump_json()),
        "final_report": json.loads(report.model_dump_json()),
    }
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    pipeline_event(
        logger,
        document_id=document.document_id,
        agent="orchestrator",
        input_schema_version=document.schema_version,
        output_schema_version=report.schema_version,
        output_path=str(destination),
        human_review_triggers=report.human_review_warnings[:10],
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AI Contract Intelligence pipeline (not legal advice).")
    parser.add_argument("--file", required=True, help="Path to PDF, DOCX, or TXT contract")
    parser.add_argument("--output", default=None, help="Optional JSON output path")
    args = parser.parse_args(argv)
    try:
        report = run_pipeline(args.file, args.output)
    except (ValidationError, SchemaBoundaryError, PipelineError) as exc:
        logging.error("Pipeline failed: %s", exc)
        return 1
    try:
        print(report.model_dump_json(indent=2))
    except UnicodeEncodeError:
        print(report.model_dump_json(indent=2).encode("utf-8", "replace").decode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    raise SystemExit(main())
