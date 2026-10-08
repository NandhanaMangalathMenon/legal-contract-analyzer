from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from core.exceptions import OCRNotAvailableError


class OCREngine(ABC):
    """Designed for scanned PDFs. Concrete engines (Tesseract, Cloud OCR) plug in later."""

    @abstractmethod
    def extract_pages(self, path: Path) -> list[str]:
        raise NotImplementedError


class StubOCREngine(OCREngine):
    def extract_pages(self, path: Path) -> list[str]:
        raise OCRNotAvailableError(
            f"OCR is not configured. Scanned PDF cannot be read: {path.name}. "
            "Provide a text-based PDF/DOCX/TXT or implement OCREngine."
        )
