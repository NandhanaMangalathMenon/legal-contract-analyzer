from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.0"


class ClauseType(str, Enum):
    PAYMENT = "payment"
    FEES = "fees"
    TERMINATION = "termination"
    RENEWAL = "renewal"
    LIABILITY = "liability"
    INDEMNIFICATION = "indemnification"
    CONFIDENTIALITY = "confidentiality"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    PRIVACY = "privacy"
    DATA = "data"
    NON_COMPETE = "non_compete"
    NON_SOLICITATION = "non_solicitation"
    EXCLUSIVITY = "exclusivity"
    DISPUTE_RESOLUTION = "dispute_resolution"
    ARBITRATION = "arbitration"
    GOVERNING_LAW = "governing_law"
    OBLIGATIONS = "obligations"
    PENALTIES = "penalties"
    WARRANTIES = "warranties"
    REPRESENTATIONS = "representations"
    DEFINITIONS = "definitions"
    EXCEPTIONS = "exceptions"
    CONDITIONS = "conditions"
    SCHEDULES = "schedules"
    ANNEXURES = "annexures"
    AMENDMENTS = "amendments"
    MISCELLANEOUS = "miscellaneous"


class DependencyRelation(str, Enum):
    REFERENCES = "REFERENCES"
    DEFINED_BY = "DEFINED_BY"
    MODIFIED_BY = "MODIFIED_BY"
    OVERRIDES = "OVERRIDES"
    OVERRIDDEN_BY = "OVERRIDDEN_BY"
    EXCEPTED_BY = "EXCEPTED_BY"
    LIMITED_BY = "LIMITED_BY"
    CONDITIONED_BY = "CONDITIONED_BY"
    RELATED_TO = "RELATED_TO"
    INCORPORATES = "INCORPORATES"


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class RiskCategory(str, Enum):
    FINANCIAL = "financial"
    TERMINATION = "termination"
    LIABILITY = "liability"
    RESTRICTIONS = "restrictions"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    PRIVACY_DATA = "privacy_data"
    DISPUTES = "disputes"
    AMBIGUITY = "ambiguity"
    STRUCTURAL = "structural"


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    LEGAL_SUPPORT_NOT_FOUND = "LEGAL_SUPPORT_NOT_FOUND"
    STATE_LAW_REQUIRED = "STATE_LAW_REQUIRED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"


class Location(BaseModel):
    page: int | None = None
    heading: str | None = None
    section: str | None = None
    subsection: str | None = None
    start_offset: int | None = None
    end_offset: int | None = None


class Entity(BaseModel):
    name: str
    entity_type: str = "unknown"
    role: str | None = None


class RetrievalMetadata(BaseModel):
    source: str = "parser"
    score: float | None = None
    method: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class EvidenceItem(BaseModel):
    source_kind: str
    source_id: str
    excerpt: str
    location: Location | None = None
    score: float | None = None
