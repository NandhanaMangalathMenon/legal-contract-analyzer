from __future__ import annotations

import re
from dataclasses import dataclass

from agent1.extractors.ingest import IngestedDocument, PageText
from schemas.common import ClauseType, Entity, Location, RetrievalMetadata
from schemas.document import Amendment, Annexure, Clause, Definition, Party, Schedule

CLAUSE_HEADING = re.compile(
    r"^(?:section|clause|article)\s+([\dA-Za-z]+(?:\.[\dA-Za-z]+)*)\s*[:.\-–]?\s*(.*)$",
    re.IGNORECASE,
)
NUMBERED_HEADING = re.compile(r"^(\d+(?:\.\d+){0,4})\s+([A-Z][^\n]{2,80})$")
DEFINITION_LINE = re.compile(
    r'^[“"\'"]?([A-Z][^“"\'"]{1,80})[”"\'"]?\s+(?:means|shall mean|has the meaning)\s+(.+)$',
    re.IGNORECASE,
)
SCHEDULE_HEADING = re.compile(
    r"^(schedule|annexure|annex|exhibit)\s+([A-Z0-9]+)(?:\s*[:.\-–—]\s*(.*))?$",
    re.I,
)
AMENDMENT_HEADING = re.compile(r"^(amendment(?:\s+no\.?|\s+#)?\s*([0-9]+).*)", re.I)
PARTY_LINE = re.compile(
    r"(?:between|by and between)\s+(.+?)\s+\((?:the\s+)?[\"']?([^)\"']+)[\"']?\)",
    re.IGNORECASE,
)
EXCEPTION_MARKERS = (
    "except",
    "unless",
    "provided that",
    "subject to",
    "notwithstanding",
    "save for",
    "excluding",
    "except where",
    "only if",
    "unless otherwise agreed",
)

TYPE_KEYWORDS: list[tuple[ClauseType, tuple[str, ...]]] = [
    (ClauseType.DEFINITIONS, ("means", "shall mean", "definition")),
    (ClauseType.PAYMENT, ("payment", "pay", "invoice", "consideration")),
    (ClauseType.FEES, ("fee", "fees", "charges")),
    (ClauseType.PENALTIES, ("penalty", "liquidated damages", "late fee")),
    (ClauseType.TERMINATION, ("terminat", "expire", "notice period")),
    (ClauseType.RENEWAL, ("renew", "automatic renewal", "evergreen")),
    (ClauseType.LIABILITY, ("liability", "liable", "cap on", "consequential")),
    (ClauseType.INDEMNIFICATION, ("indemnif", "hold harmless")),
    (ClauseType.CONFIDENTIALITY, ("confidential", "non-disclosure", "nda")),
    (ClauseType.INTELLECTUAL_PROPERTY, ("intellectual property", "copyright", "patent", "trademark", "assign")),
    (ClauseType.PRIVACY, ("privacy", "personal data", "personal information")),
    (ClauseType.DATA, ("data protection", "data processing", "retention")),
    (ClauseType.NON_COMPETE, ("non-compete", "non compete", "restraint of trade")),
    (ClauseType.NON_SOLICITATION, ("non-solicit", "non solicitation")),
    (ClauseType.EXCLUSIVITY, ("exclusive", "exclusivity")),
    (ClauseType.ARBITRATION, ("arbitration", "arbitral")),
    (ClauseType.DISPUTE_RESOLUTION, ("dispute", "jurisdiction", "venue", "governing court")),
    (ClauseType.GOVERNING_LAW, ("governing law", "laws of india", "indian law")),
    (ClauseType.WARRANTIES, ("warrant", "represents and warrants")),
    (ClauseType.REPRESENTATIONS, ("represents that", "representation")),
    (ClauseType.AMENDMENTS, ("amendment", "amended by")),
    (ClauseType.SCHEDULES, ("schedule",)),
    (ClauseType.ANNEXURES, ("annexure", "annex ", "exhibit")),
    (ClauseType.EXCEPTIONS, ("notwithstanding", "except as", "provided that")),
    (ClauseType.CONDITIONS, ("condition precedent", "subject to the condition")),
    (ClauseType.OBLIGATIONS, ("shall", "must", "obligation")),
]


@dataclass
class ParsedUnits:
    clauses: list[Clause]
    definitions: list[Definition]
    schedules: list[Schedule]
    annexures: list[Annexure]
    amendments: list[Amendment]
    parties: list[Party]


def parse_units(ingested: IngestedDocument) -> ParsedUnits:
    blocks = _collect_blocks(ingested.pages)
    clauses: list[Clause] = []
    definitions: list[Definition] = []
    schedules: list[Schedule] = []
    annexures: list[Annexure] = []
    amendments: list[Amendment] = []
    clause_counter = 0
    def_counter = 0
    sch_counter = 0
    ann_counter = 0
    amd_counter = 0

    for block in blocks:
        heading = block["heading"]
        body = block["text"]
        page = block["page"]
        kind = block["kind"]
        location = Location(page=page, heading=heading, section=heading)

        if kind == "schedule":
            sch_counter += 1
            schedule_id = f"SCH-{sch_counter:03d}"
            schedules.append(
                Schedule(
                    schedule_id=schedule_id,
                    title=heading,
                    text=body,
                    location=location,
                    modifies=_detect_modified_refs(body),
                )
            )
            clauses.append(_as_clause(schedule_id, heading, body, location, ClauseType.SCHEDULES, "schedule"))
            continue
        if kind == "annexure":
            ann_counter += 1
            annexure_id = f"ANN-{ann_counter:03d}"
            annexures.append(
                Annexure(
                    annexure_id=annexure_id,
                    title=heading,
                    text=body,
                    location=location,
                    modifies=_detect_modified_refs(body),
                )
            )
            clauses.append(_as_clause(annexure_id, heading, body, location, ClauseType.ANNEXURES, "annexure"))
            continue
        if kind == "amendment":
            amd_counter += 1
            amendment_id = f"AMD-{amd_counter:03d}"
            date = _find_date(body)
            amendments.append(
                Amendment(
                    amendment_id=amendment_id,
                    title=heading,
                    text=body,
                    date=date,
                    modified_clause_ids=_detect_modified_refs(body),
                    replacement_text=_replacement_snippet(body),
                    supersedes_previous=None,
                    location=location,
                )
            )
            clauses.append(_as_clause(amendment_id, heading, body, location, ClauseType.AMENDMENTS, "amendment"))
            continue

        clause_counter += 1
        clause_id = f"C-{clause_counter:03d}"
        clause_type = classify_clause(heading, body)
        exceptions = extract_exception_phrases(body)
        conditions = extract_condition_phrases(body)
        defined_terms = extract_defined_terms_used(body)
        entities = extract_entities(body)
        clauses.append(
            Clause(
                clause_id=clause_id,
                title=heading or f"Clause {clause_counter}",
                type=clause_type,
                text=body,
                location=location,
                entities=entities,
                exceptions=exceptions,
                conditions=conditions,
                defined_terms=defined_terms,
                retrieval=RetrievalMetadata(source="clause_parser", method="deterministic"),
                component_kind="clause",
            )
        )
        for term, meaning in extract_definitions(body):
            def_counter += 1
            def_id = f"DEF-{def_counter:03d}"
            definitions.append(
                Definition(
                    definition_id=def_id,
                    term=term,
                    text=meaning,
                    location=location,
                    clause_id=clause_id,
                )
            )

    parties = extract_parties(ingested.full_text)
    return ParsedUnits(
        clauses=clauses,
        definitions=definitions,
        schedules=schedules,
        annexures=annexures,
        amendments=amendments,
        parties=parties,
    )


def _as_clause(
    unit_id: str,
    heading: str,
    body: str,
    location: Location,
    clause_type: ClauseType,
    kind: str,
) -> Clause:
    return Clause(
        clause_id=unit_id,
        title=heading,
        type=clause_type,
        text=body,
        location=location,
        exceptions=extract_exception_phrases(body),
        conditions=extract_condition_phrases(body),
        defined_terms=extract_defined_terms_used(body),
        retrieval=RetrievalMetadata(source="clause_parser", method="deterministic"),
        component_kind=kind,
    )


def _collect_blocks(pages: list[PageText]) -> list[dict]:
    blocks: list[dict] = []
    current: dict | None = None
    for page in pages:
        for raw_line in page.text.splitlines():
            line = raw_line.strip()
            if not line:
                if current:
                    current["text"] += "\n"
                continue
            heading_info = _match_heading(line)
            if heading_info:
                if current and current["text"].strip():
                    blocks.append(current)
                current = {
                    "heading": heading_info["heading"],
                    "kind": heading_info["kind"],
                    "page": page.page,
                    "text": line + "\n",
                }
            else:
                if current is None:
                    current = {
                        "heading": f"Page {page.page} preamble",
                        "kind": "clause",
                        "page": page.page,
                        "text": line + "\n",
                    }
                else:
                    current["text"] += line + "\n"
        if current:
            current["text"] += "\n"
    if current and current["text"].strip():
        blocks.append(current)
    if not blocks:
        joined = "\n".join(p.text for p in pages).strip()
        blocks.append({"heading": "Full document", "kind": "clause", "page": 1, "text": joined})
    return blocks


def _match_heading(line: str) -> dict | None:
    sched = SCHEDULE_HEADING.match(line)
    if sched:
        kind_raw = sched.group(1).lower()
        kind = "schedule" if kind_raw == "schedule" else "annexure"
        label = line.strip()
        return {"heading": label, "kind": kind}
    amd = AMENDMENT_HEADING.match(line)
    if amd:
        return {"heading": line.strip(), "kind": "amendment"}
    clause = CLAUSE_HEADING.match(line)
    if clause:
        number, rest = clause.group(1), clause.group(2)
        return {"heading": f"Section {number} {rest}".strip(), "kind": "clause"}
    numbered = NUMBERED_HEADING.match(line)
    if numbered:
        return {"heading": line.strip(), "kind": "clause"}
    if line.isupper() and 8 <= len(line) <= 80:
        return {"heading": line.title(), "kind": "clause"}
    return None


def classify_clause(heading: str, body: str) -> ClauseType:
    blob = f"{heading}\n{body}".lower()
    for clause_type, keywords in TYPE_KEYWORDS:
        if any(keyword in blob for keyword in keywords):
            return clause_type
    return ClauseType.MISCELLANEOUS


def extract_exception_phrases(text: str) -> list[str]:
    phrases: list[str] = []
    for sentence in re.split(r"(?<=[.;])\s+", text):
        lower = sentence.lower()
        if any(marker in lower for marker in EXCEPTION_MARKERS):
            phrases.append(sentence.strip())
    return phrases


def extract_condition_phrases(text: str) -> list[str]:
    phrases: list[str] = []
    for sentence in re.split(r"(?<=[.;])\s+", text):
        lower = sentence.lower()
        if any(token in lower for token in ("if ", "only if", "provided that", "subject to", "conditional")):
            phrases.append(sentence.strip())
    return phrases


def extract_definitions(text: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for line in text.splitlines():
        match = DEFINITION_LINE.match(line.strip())
        if match:
            found.append((match.group(1).strip(), match.group(2).strip()))
    inline = re.findall(
        r'["“]([A-Z][^"”]{1,60})["”]\s+(?:means|shall mean)\s+([^.]+)',
        text,
    )
    for term, meaning in inline:
        found.append((term.strip(), meaning.strip()))
    return found


def extract_defined_terms_used(text: str) -> list[str]:
    return sorted(set(re.findall(r'\b([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3})\b', text)))


def extract_entities(text: str) -> list[Entity]:
    entities: list[Entity] = []
    for name in ("Party A", "Party B", "Receiving Party", "Disclosing Party", "Customer", "Vendor"):
        if name.lower() in text.lower():
            entities.append(Entity(name=name, entity_type="party"))
    return entities


def extract_parties(text: str) -> list[Party]:
    parties: list[Party] = []
    for match in PARTY_LINE.finditer(text):
        parties.append(Party(name=match.group(1).strip(" ,"), role=match.group(2).strip()))
    if not parties:
        if "party a" in text.lower():
            parties.append(Party(name="Party A", role="Party A"))
        if "party b" in text.lower():
            parties.append(Party(name="Party B", role="Party B"))
    return parties


def _detect_modified_refs(text: str) -> list[str]:
    refs = re.findall(r"(?:section|clause|article)\s+(\d+(?:\.\d+)*)", text, flags=re.I)
    return [f"Section {item}" for item in refs]


def _replacement_snippet(text: str) -> str | None:
    match = re.search(r"(?:shall be replaced with|is hereby amended to read as follows)[:\s]+(.+)", text, re.I | re.S)
    if match:
        return match.group(1).strip()[:500]
    return None


def _find_date(text: str) -> str | None:
    match = re.search(r"\b(\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b", text, re.I)
    if match:
        return match.group(1)
    match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    return match.group(1) if match else None
