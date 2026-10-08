# common/file_parser.py

from pathlib import Path
from typing import List, Dict

from docx import Document
from pypdf import PdfReader


# =============================================================
# PDF
# =============================================================

def parse_pdf(
    file_path: str
) -> List[Dict[str, object]]:
    """
    Extract machine-readable text from a PDF.

    Images and scanned text are ignored.
    OCR is intentionally NOT performed.
    """

    path = Path(file_path)

    reader = PdfReader(
        str(path)
    )

    pages = []

    for page_number, page in enumerate(
        reader.pages,
        start=1
    ):

        try:
            text = page.extract_text() or ""

        except Exception:
            text = ""

        text = text.strip()

        pages.append(
            {
                "page": page_number,
                "text": text
            }
        )

    # ---------------------------------------------------------
    # Detect image-only PDF
    # ---------------------------------------------------------

    has_text = any(
        page["text"]
        for page in pages
    )

    if not has_text:

        raise ValueError(
            "PDF contains no machine-readable text. "
            "OCR is disabled."
        )

    return pages


# =============================================================
# DOCX
# =============================================================

def parse_docx(
    file_path: str
) -> List[Dict[str, object]]:
    """
    Extract text from a DOCX file.

    DOCX does not reliably expose page boundaries
    through python-docx, so the entire document is
    treated as one logical page.
    """

    document = Document(
        file_path
    )

    paragraphs = []

    for paragraph in document.paragraphs:

        text = paragraph.text.strip()

        if text:
            paragraphs.append(text)

    full_text = "\n".join(
        paragraphs
    )

    if not full_text.strip():

        raise ValueError(
            "DOCX contains no machine-readable text."
        )

    return [
        {
            "page": 1,
            "text": full_text
        }
    ]


# =============================================================
# TXT
# =============================================================

def parse_txt(
    file_path: str
) -> List[Dict[str, object]]:
    """
    Extract text from a TXT file.

    TXT files do not have real page numbers,
    so the complete file is treated as page 1.
    """

    path = Path(file_path)

    try:

        text = path.read_text(
            encoding="utf-8"
        )

    except UnicodeDecodeError:

        # Try a common fallback
        text = path.read_text(
            encoding="latin-1"
        )

    text = text.strip()

    if not text:

        raise ValueError(
            "TXT file contains no text."
        )

    return [
        {
            "page": 1,
            "text": text
        }
    ]


# =============================================================
# Main parser
# =============================================================

def parse_document(
    file_path: str
) -> List[Dict[str, object]]:
    """
    Automatically detect file type and extract text.

    Supported:

        .pdf
        .docx
        .txt

    Returns:

        [
            {
                "page": 1,
                "text": "..."
            },
            ...
        ]
    """

    path = Path(file_path)

    if not path.exists():

        raise FileNotFoundError(
            f"File does not exist: {file_path}"
        )

    if not path.is_file():

        raise ValueError(
            f"Path is not a file: {file_path}"
        )

    extension = (
        path.suffix.lower()
    )

    # ---------------------------------------------------------
    # PDF
    # ---------------------------------------------------------

    if extension == ".pdf":

        return parse_pdf(
            str(path)
        )

    # ---------------------------------------------------------
    # DOCX
    # ---------------------------------------------------------

    if extension == ".docx":

        return parse_docx(
            str(path)
        )

    # ---------------------------------------------------------
    # TXT
    # ---------------------------------------------------------

    if extension == ".txt":

        return parse_txt(
            str(path)
        )

    # ---------------------------------------------------------
    # Unsupported
    # ---------------------------------------------------------

    raise ValueError(
        "Unsupported file type: "
        f"{extension}. "
        "Supported formats are PDF, DOCX and TXT."
    )
