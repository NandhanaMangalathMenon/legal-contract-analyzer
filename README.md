# Contract Graph Counsel

> Upload a contract, recover its structure and long-range dependencies, surface consultancy-style risks, and ground those findings against a limited Indian Central-Law knowledge seed — without pretending to be a lawyer.

## Team

**Team Name:** To be filled by the submitting team

| Member | Contribution |
| ------ | ------------ |
| To be filled | Agent 1 — document & context analysis |
| To be filled | Agent 2 — risk & consultancy analysis |
| To be filled | Agent 3 — Indian Central-Law verification and legal knowledge |

## Problem Statement

### The Problem

A single contract sentence is rarely the whole story. Termination on page 5 may be narrowed on page 50, modified by a schedule, and rewritten by an amendment. Non-lawyers (founders, procurement, product, HR) often read the nearest clause, miss the dependency, and only learn the real meaning after a dispute. Generic “summarize this PDF” tools make that worse: they retrieve a similar-looking chunk and drop exceptions, numbers, and later overrides.

### Why We Chose This Problem

Hackathon users need a system that behaves like a junior contract-analysis team: map the document, follow cross-references, explain practical consequences, and attach legal *sources* instead of invented citations. India-focused review also needs Central Acts called out with provenance, plus an honest stop when State law or official text is missing.

## Solution

The backend runs three logical agents and a deterministic report builder:

1. **Agent 1 — Document & Context Analyst** ingests PDF/DOCX/TXT, extracts clauses, definitions, schedules, annexures, and amendments, and builds a **contract dependency graph**.
2. **Agent 2 — Contract Risk & Consultancy Analyst** retrieves a neighbourhood around each issue (definitions, exceptions, schedules, amendments, related clauses) and emits structured risks plus questions for a lawyer. It does **not** emit a 0–100 neural score.
3. **Agent 3 — India Central-Law Verifier** checks that cited clauses exist, retrieves seeded Central Law research notes, and labels support (`VERIFIED`, `PARTIALLY_SUPPORTED`, `LEGAL_SUPPORT_NOT_FOUND`, `STATE_LAW_REQUIRED`, `HUMAN_REVIEW_REQUIRED`, …). It does **not** create new risks or rename `risk_id` values.
4. **FinalReportBuilder** merges the three Pydantic objects in code (not via an LLM) into a `FinalContractReport`.

The product never says “sign it” or “don’t sign it”, and never treats “commercially unfavourable” as “illegal”.

### Key Features

- Structure-aware ingestion (pages, headings, schedules, amendments)
- Deterministic cross-reference parsing plus TF-IDF and embeddings
- Long-range dependency packages (1-hop / 2-hop graph + lexical/semantic hits)
- Consultancy-style findings: what it says, why it matters, questions, cautious review points
- Separate **contract** and **legal** vector stores
- Explainable priority scoring after Agent 2 (severity + risk factors + dependency complexity + legal uncertainty)
- CLI suitable for later REST, MCP, or agent-tool wrappers (no frontend in this milestone)

## Innovation and Differentiation

Most RAG demos chunk a PDF and summarise. This system models the contract as a **connected graph**, refuses to compress away `notwithstanding` / `subject to` / numbers, and verifies claims against a **separate** Indian Central-Law store with explicit “not found” states. Consultancy output is decision support for a conversation with a qualified lawyer, not a substitute for one.

## Technical Implementation

### Architecture

```mermaid
flowchart TD
    file[PDF_DOCX_TXT] --> a1[Agent1_DocumentContext]
    a1 --> da[DocumentAnalysis]
    da --> graph[DependencyGraph]
    da --> hybrid[HybridContractRetriever]
    da --> a2[Agent2_RiskConsultancy]
    hybrid --> a2
    graph --> a2
    a2 --> ra[RiskAnalysis]
    da --> a3[Agent3_IndiaCentralLaw]
    ra --> a3
    kb[LegalKnowledgeSeed] --> a3
    a3 --> va[VerifiedAnalysis]
    da --> report[FinalReportBuilder]
    ra --> report
    va --> report
    report --> out[FinalContractReport_JSON]
```

### Technology Stack

| Category | Technologies |
| -------- | ------------ |
| Frontend | N/A (backend-only milestone) |
| Backend | Python 3, Pydantic v2, CLI orchestrator |
| Database | In-memory `VectorStore` (swap-ready for Chroma/Qdrant/pgvector) |
| AI / ML | Pluggable `LLMClient` (`mock` default; optional Gemini). Local hashing/TF-IDF embeddings when no API key |
| Infrastructure | Local filesystem cache under `data/.cache/` |
| APIs / Services | Optional Google Gemini generate/embed |

### How It Works

1. Ingest text with page markers (or PDF/DOCX extractors; OCR is an interface, not a bundled engine).
2. Parse units and classify clause types without scoring risk.
3. Add graph edges for definitions, `Section N` references, `notwithstanding`, schedules, and amendments (amendments are **linked**, not blindly treated as total overrides).
4. Agent 2 runs rule-backed detectors on graph-aware context; optional LLM commentary does not replace structured findings.
5. Agent 3 re-checks clause IDs and searches the legal seed. Seed records are **research notes**, not official Act reprints.
6. The report builder buckets issues, copies lawyer questions, and prints limitations.

### Technical Decisions

- Three logical agents, many ordinary modules (retriever, graph, parser, scorer). No extra “autonomous agents”.
- Pydantic validation at every agent boundary (`SchemaBoundaryError` if invalid).
- Deterministic parsing for explicit cross-references; embeddings only as a complement.
- Model temperature / penalties come from environment variables, not scattered literals.
- Legal seed cites India Code as the place to read official text; the app does not invent case names or holdings.

## Implementation During the Hackathon

Built during Hacktoberfest Hack Day — Coimbatore 2026 as a backend pipeline: shared schemas, LLM/VectorStore abstractions, Agents 1–3, hybrid retrieval, a Central Law seed for 14 priority Acts, deterministic aggregation, sample contract, and tests.

### Team Contributions

- **Developer 1 (branch `agent1-document-context`):** `agent1/`
- **Developer 2 (branch `agent2-risk-consultancy`):** `agent2/`
- **Developer 3 (branch `agent3-legal-verification`):** `agent3/`, `legal_knowledge/`
- **Shared:** `schemas/`, `llm/`, `pipeline/`, `stores/`, `core/`

## Working Application

**Live Application:** N/A (CLI backend; no hosted UI in this repository)

Run the orchestrator locally against `data/sample_contracts/sample_contract.txt` or the generated PDF (see Setup).

## Demo Video

**Demo Video:** To be added by the team

## Open Source and AI Usage

### AI / Models

- **Optional Gemini (`GEMINI_API_KEY`, `GEMINI_MODEL`):** generation and embeddings when `LLM_PROVIDER=gemini`.
- **Mock / local hashing embedder:** default so the pipeline is reproducible without secrets. Mock generation does not perform legal reasoning; deterministic modules do.

### Open Source Components

- **Pydantic / pydantic-settings:** schema contracts and configuration
- **pypdf / python-docx:** document ingestion
- **scikit-learn / numpy:** TF-IDF and cosine ranking
- **httpx:** Gemini HTTP client
- **fpdf2:** sample PDF generation
- **pytest:** tests
- **India Code (https://www.indiacode.nic.in/):** pointed to as the official source for Central Acts; this repo does not copy full Act text

## Setup and Usage

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
git clone <repository-url>
cd legal-contract-analyzer
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

On Unix: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && cp .env.example .env`

### Environment Variables

See `.env.example`. Important variables:

```env
LLM_PROVIDER=mock
GEMINI_API_KEY=
MODEL_TEMPERATURE=0.2
MODEL_FREQUENCY_PENALTY=0.0
MODEL_PRESENCE_PENALTY=0.0
VECTOR_STORE_BACKEND=memory
HUMAN_REVIEW_CONFIDENCE_THRESHOLD=0.55
```

Never put real API keys in git.

### Running the Project

```bash
python -m pipeline.orchestrator --file data/sample_contracts/sample_contract.txt
```

Generate the sample PDF:

```bash
python data/sample_contracts/build_sample_pdf.py
python -m pipeline.orchestrator --file data/sample_contracts/sample_contract.pdf
```

JSON for the run is written under `data/processed/` (gitignored).

### Usage

1. Point `--file` at a PDF, DOCX, or TXT contract.
2. Read `FinalContractReport` sections: obligations, risks by severity, dependencies, legal context, questions, limitations.
3. Take questions to a **qualified lawyer**. Do not treat the JSON as a sign/no-sign decision.

### Tests

```bash
pytest
```

## Challenges and Learnings

- Naive RAG drops later “notwithstanding” clauses; explicit graphs plus exception preservation matter more than a larger context window.
- Official legal text cannot be fabricated for a demo. A small, labelled seed with `LEGAL_SUPPORT_NOT_FOUND` is safer than hallucinated citations.
- Amendment “newest wins” is a legal conclusion, not a parsing rule — the graph records `OVERRIDDEN_BY` and leaves hierarchy to Agent 2/3 and humans.
- Keeping three output schemas joinable by `risk_id` is an integration requirement, not a formatting preference.

## Credits and License

### Credits

Hacktoberfest Hack Day — Coimbatore 2026 (INIT CLUB × iDEA CLUB / MLH). India Code and the listed Central Acts remain the authoritative legal sources. Sample contract is synthetic evaluation data, not a real client document.

### License

MIT — see `LICENSE`.

## Devpost Submission

**Devpost Project:** To be added by the team

## Submission Checklist

- [x] Project title and description added
- [ ] All team members listed
- [x] Problem clearly explained
- [x] Reason for choosing the problem explained
- [x] Solution and key features documented
- [x] Innovation and differentiation explained
- [x] Architecture included
- [x] Technical implementation documented
- [x] Work completed during the hackathon documented
- [x] Team contributions documented (roles; names TBD)
- [x] Working application is functional (CLI)
- [ ] Live application link added where applicable
- [ ] Demo video added
- [x] AI and open-source components documented
- [x] Setup and usage instructions tested
- [x] Challenges and learnings documented
- [ ] Devpost submission completed
- [ ] Devpost link added
- [x] Credits added
- [x] License added
- [x] Repository is organized and complete
