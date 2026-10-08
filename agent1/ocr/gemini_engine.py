from __future__ import annotations

import json
from pathlib import Path

from agent1.ocr.interface import OCREngine
from core.exceptions import OCRNotAvailableError
from llm.client import get_llm_client


class GeminiOCREngine(OCREngine):
    """Uses Gemini 1.5 Pro to extract text from a scanned PDF or document."""

    def __init__(self, llm=None):
        self.llm = llm or get_llm_client()

    def extract_pages(self, path: Path) -> list[str]:
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        prompt = (
            "Extract all text from the provided document accurately. "
            "Output the response as a JSON array of strings, where each string represents the text of a single page in the document. "
            "Do not summarize or invent text. Preserve original formatting, clause numbers, and schedules as closely as possible."
        )
        
        system = "You are a highly accurate OCR engine designed for legal documents."

        try:
            res = self.llm.generate_json(prompt, system=system, media_paths=[str(path)])
            if isinstance(res, list) and all(isinstance(i, str) for i in res):
                return res
            if isinstance(res, dict) and "pages" in res:
                return res["pages"]
            return [str(res)]
        except Exception as e:
            raise OCRNotAvailableError(f"Gemini OCR extraction failed: {e}")
