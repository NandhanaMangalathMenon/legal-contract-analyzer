# common/validation.py

import json
from pathlib import Path
from typing import Any, Dict

from jsonschema import (
    Draft202012Validator,
    ValidationError
)


# =============================================================
# Schema directory
# =============================================================

SCHEMA_DIR = (
    Path(__file__).resolve().parent.parent
    / "schemas"
)


# =============================================================
# Load schema
# =============================================================

def load_schema(
    schema_filename: str
) -> Dict[str, Any]:

    schema_path = (
        SCHEMA_DIR
        / schema_filename
    )

    if not schema_path.exists():

        raise FileNotFoundError(
            f"Schema not found: {schema_path}"
        )

    try:

        with open(
            schema_path,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except json.JSONDecodeError as e:

        raise ValueError(
            f"Invalid JSON schema: {schema_path}"
        ) from e


# =============================================================
# Validate generic JSON
# =============================================================

def validate_json(
    data: Dict[str, Any],
    schema_filename: str
) -> bool:
    """
    Validate data against a JSON schema.

    Returns True if valid.

    Raises ValueError if invalid.
    """

    schema = load_schema(
        schema_filename
    )

    validator = Draft202012Validator(
        schema
    )

    errors = sorted(
        validator.iter_errors(data),
        key=lambda error: list(
            error.path
        )
    )

    if errors:

        error_messages = []

        for error in errors:

            path = ".".join(
                str(part)
                for part in error.path
            )

            if not path:
                path = "<root>"

            error_messages.append(
                f"{path}: {error.message}"
            )

        message = (
            "JSON schema validation failed:\n"
            + "\n".join(error_messages)
        )

        raise ValueError(
            message
        )

    return True


# =============================================================
# DocumentAnalysis
# =============================================================

def validate_document_analysis(
    data: Dict[str, Any]
) -> bool:

    return validate_json(
        data,
        "document_schema.json"
    )


# =============================================================
# RiskAnalysis
# =============================================================

def validate_risk_analysis(
    data: Dict[str, Any]
) -> bool:

    return validate_json(
        data,
        "risk_schema.json"
    )


# =============================================================
# VerifiedAnalysis
# =============================================================

def validate_verified_analysis(
    data: Dict[str, Any]
) -> bool:

    return validate_json(
        data,
        "verification_schema.json"
    )
