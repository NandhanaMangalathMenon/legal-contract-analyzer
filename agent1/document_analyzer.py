from __future__ import annotations

import logging
from pathlib import Path

from pydantic import ValidationError

from agent1.clause_parser import parse_units
from agent1.dependency_graph import build_dependency_graph
from agent1.extractors.ingest import ingest_document
from agent1.ocr.interface import OCREngine
from core.exceptions import SchemaBoundaryError
from core.ids import document_id_from_path
from core.logging import pipeline_event
from llm.client import LLMClient, get_llm_client
from schemas.common import SCHEMA_VERSION, Location
from schemas.document import DocumentAnalysis, DocumentMetadata
from stores.vector_store import get_vector_store

logger = logging.getLogger(__name__)


class DocumentContextAnalyst:
    """Agent 1 — structure and relationships only. Does not decide legal risk."""

    def __init__(self, llm: LLMClient | None = None, ocr: OCREngine | None = None) -> None:
        self.llm = llm or get_llm_client()
        self.ocr = ocr

    def analyze(self, path: str | Path) -> DocumentAnalysis:
        path = Path(path)
        ingested = ingest_document(path, ocr=self.ocr)
        units = parse_units(ingested)
        purpose = _infer_purpose(ingested.full_text)
        jurisdiction = _find_jurisdiction(ingested.full_text)
        analysis = DocumentAnalysis(
            schema_version=SCHEMA_VERSION,
            document_id=document_id_from_path(path),
            filename=path.name,
            document_metadata=DocumentMetadata(
                file_type=ingested.file_type,
                page_count=len(ingested.pages) or 1,
                language="English",
                jurisdiction_text=jurisdiction,
                ocr_used=ingested.ocr_used,
                extraction_confidence=ingested.extraction_confidence,
                content_hash=ingested.content_hash,
            ),
            parties=units.parties,
            clauses=units.clauses,
            definitions=units.definitions,
            schedules=units.schedules,
            annexures=units.annexures,
            amendments=units.amendments,
            contract_purpose=purpose,
            extraction_warnings=ingested.warnings or [],
        )
        analysis.dependencies = build_dependency_graph(analysis)
        try:
            validated = DocumentAnalysis.model_validate(analysis.model_dump())
        except ValidationError as exc:
            raise SchemaBoundaryError(f"Agent 1 output failed validation: {exc}") from exc
        get_vector_store("contract_store")  # ensure store exists for downstream retrieval
        pipeline_event(
            logger,
            document_id=validated.document_id,
            agent="agent1",
            input_schema_version=SCHEMA_VERSION,
            output_schema_version=validated.schema_version,
            clause_count=len(validated.clauses),
            definition_count=len(validated.definitions),
            dependency_count=len(validated.dependencies),
            ocr_used=validated.document_metadata.ocr_used,
        )
        return validated


def _infer_purpose(text: str) -> str:
    lowered = text.lower()
    if "software" in lowered and "services" in lowered:
        return "Software or technology services agreement (inferred from document text)."
    if "sale of goods" in lowered or "purchase" in lowered:
        return "Sale or purchase related agreement (inferred from document text)."
    if "employment" in lowered:
        return "Employment-related agreement (inferred from document text)."
    return "Commercial agreement. Confirm purpose with the full recitals and a qualified lawyer."


def _find_jurisdiction(text: str) -> str | None:
    import re

    match = re.search(r"governing law[^\n.]{0,120}", text, flags=re.I)
    if match:
        return match.group(0).strip()
    if "laws of india" in text.lower() or "indian law" in text.lower():
        return "References Indian law in the document text."
    return None
