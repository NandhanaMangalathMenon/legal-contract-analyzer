from __future__ import annotations

from pydantic import BaseModel, Field

from schemas.common import (
    SCHEMA_VERSION,
    ClauseType,
    DependencyRelation,
    Entity,
    Location,
    RetrievalMetadata,
)


class DocumentMetadata(BaseModel):
    file_type: str
    page_count: int = 0
    language: str = "English"
    jurisdiction_text: str | None = None
    ocr_used: bool = False
    extraction_confidence: float = 1.0
    content_hash: str | None = None


class Party(BaseModel):
    name: str
    role: str | None = None
    aliases: list[str] = Field(default_factory=list)


class Clause(BaseModel):
    clause_id: str
    title: str
    type: ClauseType = ClauseType.MISCELLANEOUS
    text: str
    location: Location = Field(default_factory=Location)
    entities: list[Entity] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    exceptions: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    defined_terms: list[str] = Field(default_factory=list)
    retrieval: RetrievalMetadata = Field(default_factory=RetrievalMetadata)
    parent_id: str | None = None
    component_kind: str = "clause"


class Definition(BaseModel):
    definition_id: str
    term: str
    text: str
    location: Location = Field(default_factory=Location)
    clause_id: str | None = None


class Schedule(BaseModel):
    schedule_id: str
    title: str
    text: str
    location: Location = Field(default_factory=Location)
    modifies: list[str] = Field(default_factory=list)


class Annexure(BaseModel):
    annexure_id: str
    title: str
    text: str
    location: Location = Field(default_factory=Location)
    modifies: list[str] = Field(default_factory=list)


class Amendment(BaseModel):
    amendment_id: str
    title: str
    text: str
    date: str | None = None
    parties: list[str] = Field(default_factory=list)
    modified_clause_ids: list[str] = Field(default_factory=list)
    replacement_text: str | None = None
    supersedes_previous: bool | None = None
    location: Location = Field(default_factory=Location)


class DependencyEdge(BaseModel):
    source_id: str
    target_id: str
    relation: DependencyRelation
    evidence: str | None = None
    deterministic: bool = True


class DocumentAnalysis(BaseModel):
    schema_version: str = SCHEMA_VERSION
    document_id: str
    filename: str
    document_metadata: DocumentMetadata
    parties: list[Party] = Field(default_factory=list)
    clauses: list[Clause] = Field(default_factory=list)
    definitions: list[Definition] = Field(default_factory=list)
    schedules: list[Schedule] = Field(default_factory=list)
    annexures: list[Annexure] = Field(default_factory=list)
    amendments: list[Amendment] = Field(default_factory=list)
    dependencies: list[DependencyEdge] = Field(default_factory=list)
    contract_purpose: str | None = None
    extraction_warnings: list[str] = Field(default_factory=list)
