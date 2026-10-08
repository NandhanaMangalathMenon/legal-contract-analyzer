from __future__ import annotations

import hashlib
import re
from pathlib import Path


def document_id_from_path(path: Path) -> str:
    digest = hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()[:10].upper()
    return f"DOC-{digest}"


def document_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def stable_unit_id(prefix: str, index: int, parent: str | None = None) -> str:
    if parent:
        return f"{parent}.{index}"
    return f"{prefix}-{index:03d}"


def slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", value.strip()).strip("-")
    return cleaned.upper()[:40] or "UNIT"
