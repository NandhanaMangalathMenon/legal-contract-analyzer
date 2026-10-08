from __future__ import annotations

import json
import logging
from typing import Any

from core.config import get_settings

_SENSITIVE_KEYS = {"text", "clause_text", "content", "raw_text", "prompt"}


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def pipeline_event(logger: logging.Logger, **fields: Any) -> None:
    """Structured debug log. Avoids dumping full contract text."""
    safe = {}
    for key, value in fields.items():
        if key.lower() in _SENSITIVE_KEYS:
            if isinstance(value, str):
                safe[key] = f"<redacted len={len(value)}>"
            else:
                safe[key] = "<redacted>"
        else:
            safe[key] = value
    logger.info("pipeline_event %s", json.dumps(safe, default=str))
