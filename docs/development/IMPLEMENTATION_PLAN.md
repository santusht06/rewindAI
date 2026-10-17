# Rewind Master Implementation Plan — Agile Delivery Hierarchy

**Version:** 1.0  
**Status:** Baseline Specification & Phase 0 Discovery  
**Author:** Principal Software Architect & Lead Full-Stack Engineer  

---

## 1. Project Overview & Architectural Boundaries

**Rewind** is an AI-powered story companion designed for Fire TV. It grounds answers, recaps, character explanations, and contextual translations in authorized timestamped subtitle/transcript assets while strictly enforcing server-side spoiler controls.

### Core Architectural Rule
The server is the single source of truth for:
1. Identity & session ownership.
2. Playback progress provenance & confidence.
3. Spoiler policy evaluation & server-issued confirmation nonces.
4. Pre-LLM evidence boundary filtering (no future chunks reach model context).
5. Post-generation citation verification against retrieved chunks.
6. Cache key isolation across title, position boundary, spoiler state, and model versions.

The TV client is untrusted. LLMs are not policy engines.

---

## 2. Agile Phase Breakdown

```text
Product Goal: Rewind — Production-Grade Fire TV AI Story Companion
├── Phase 0: Discovery, Architecture Verification, and Baseline Setup (CURRENT)
├── Phase 1: Core Foundation, Configuration & Test Harness
├── Phase 2: Domain Model, Persistence & Database Migrations
├── Phase 3: Content Ingestion, Parsing & Indexing Engine (Offline Pipeline)
├── Phase 4: Retrieval-Augmented Generation & AI Orchestration (Online Pipeline)
├── Phase 5: Server-Side Spoiler Security & Safety Policy Engine
├── Phase 6: Fire TV 10-Foot User Interface & Remote D-Pad Navigation
├── Phase 7: End-to-End Integration, Adversarial Testing & Quality Evaluation
└── Phase 8: Operational Readiness, Hardening & Release Candidate
```

---

## 3. Detailed Work Breakdown Structure (WBS)

### Phase 0: Discovery, Baseline, and Architecture Verification
- **TASK-00-01:** Inspect repository reality, toolchains (Python 3.12, Node 20, uv, git), and existing files.
- **TASK-00-02:** Establish requirements traceability matrix mapping all SRS, NFR, and AC criteria.
- **TASK-00-03:** Initialize clean Git repository, establish `.gitignore`, and enforce local-commit/no-push policies.
- **TASK-00-04:** Establish baseline test harness and documentation tracking suite (`IMPLEMENTATION_PLAN.md`, `WORK_LOG.md`, `REQUIREMENTS_TRACEABILITY.md`, `DECISIONS.md`, `KNOWN_ISSUES.md`).
- **TASK-00-05:** Produce baseline report and Phase 1 actionable plan.

### Phase 1: Core Foundation, Configuration & Test Harness
- **EPIC-01: Foundational Framework & Configuration Management**
  - **STORY-01-S1: Environment & Config Validation**
    - `TASK-01-01`: Implement `Pydantic-Settings` configuration with environment validation and secret protection (`.env.example` placeholders, secret masking).
    - `TASK-01-02`: Configure structured privacy-aware logging with Request ID correlation middleware and redaction for sensitive query/credential text (`NFR-PRIV-001`, `NFR-OBS-001`).
    - `TASK-01-03`: Implement `/health/live` and `/health/ready` endpoints with dependency health probes (`SRS-ADM-003`).
    - `TASK-01-04`: Establish standardized API error envelope (`code`, `message`, `request_id`, `details`) and global exception handlers.

### Phase 2: Domain Model, Persistence & Database Migrations
- **EPIC-02: Data Models, Migrations & Session Contracts**
  - **STORY-02-S1: Domain Entities & Database Schema**
    - `TASK-02-01`: Define SQLAlchemy 2.0 / PostgreSQL domain entities: `Movie`, `ContentVersion`, `SubtitleChunk`, `StoryFact`, `ViewingSession`, `Question`, `AnswerSource`, `AuditEvent`.
    - `TASK-02-02`: Configure database migrations (Alembic) with reversible upgrade/downgrade scripts and data integrity constraints.
    - `TASK-02-03`: Implement repository and transaction boundary layer with support for both PostgreSQL+pgvector in production and lightweight SQLite/in-memory for isolated deterministic unit tests.
  - **STORY-02-S2: Session & Catalog API Handlers**
    - `TASK-02-04`: Implement Title Catalog endpoints (`GET /api/v1/titles`, `GET /api/v1/titles/{id}`) validating publication status (`SRS-CAT-001` - `003`).
    - `TASK-02-05`: Implement Session endpoints (`POST /api/v1/sessions`, `PATCH /api/v1/sessions/{id}/progress`, `DELETE /api/v1/sessions/{id}`) with ownership validation and progress provenance (`SRS-SES-001` - `004`).

### Phase 3: Content Ingestion & Subtitle Processing Pipeline
- **EPIC-03: Subtitle Parsing, Chunking & Index Management**
  - **STORY-03-S1: Asset Ingestion & Parser**
    - `TASK-03-01`: Implement SRT and WebVTT parsers with timestamp validation (`start_ms >= 0`, `end_ms >= start_ms`), encoding normalization, and syntax quarantine (`SRS-ING-001`, `SRS-ING-003`, `AC-019`).
    - `TASK-03-02`: Implement semantic/temporal chunking with boundary constraints, speaker tagging, and SHA256 content deduplication (`SRS-ING-002`, `AC-012`).
  - **STORY-03-S2: Staged Indexing & Versioning**
    - `TASK-03-03`: Implement embedding adapter interface (Gemini / OpenAI / Mock deterministic vector provider).
    - `TASK-03-04`: Implement Staged Indexing: write chunks to draft content version, verify index completeness, and atomically publish or rollback (`SRS-ING-004`, `SRS-ING-005`, `AC-013`, `AC-018`).
    - `TASK-03-05`: Implement Admin Ingestion endpoints with audit events (`POST /api/v1/admin/ingestions`, `POST /api/v1/admin/titles/{id}/publish`) (`SRS-ADM-001`, `SRS-ADM-002`).

### Phase 4: Retrieval & AI Orchestration (RAG Pipeline)
- **EPIC-04: Grounded Q&A, Context Construction & Provider Adapters**
  - **STORY-04-S1: Hybrid Retrieval & Pre-Filter Engine**
    - `TASK-04-01`: Implement retrieval query parser with lexical keyword search and vector similarity search.
    - `TASK-04-02`: Apply mandatory title isolation, active version verification, and temporal playback boundary filter (`SRS-QA-002`, `AC-004`).
    - `TASK-04-03`: Implement context builder with strict token budget enforcement and prompt injection hardening (treating transcript dialogue strictly as data) (`SRS-QA-003`, `AC-008`).
  - **STORY-04-S2: LLM Adapter & Output Validation**
    - `TASK-04-04`: Implement model provider adapter with bounded timeouts, retries, and token accounting (`NFR-REL-001`, `NFR-REL-002`, `NFR-COST-001`, `AC-015`).
    - `TASK-04-05`: Implement structured output schema parser and citation validator: verify every cited chunk ID exists in the retrieved set (`SRS-QA-004`, `SRS-QA-007`, `AC-005`, `AC-007`).
    - `TASK-04-06`: Implement domain outcome router (`answered`, `needs_clarification`, `insufficient_evidence`, `spoiler_confirmation_required`, `unsupported_title`) (`SRS-QA-006`, `AC-006`).

### Phase 5: Server-Side Spoiler & Safety Enforcement Engine
- **EPIC-05: Spoiler Policy Engine & Cache Isolation**
  - **STORY-05-S1: Playback Position & Policy Gate**
    - `TASK-05-01`: Implement server-side spoiler policy evaluator: enforce `safe_mode` as default, validate trusted vs manual progress, reject unconfirmed full spoilers (`SRS-SPO-001`, `SRS-SPO-002`, `AC-003`, `AC-004`).
    - `TASK-05-02`: Implement single-use cryptographic confirmation nonces for explicit spoiler consent (`POST /api/v1/sessions/{id}/spoiler-confirmation`) (`SRS-SPO-004`, `AC-009`, `AC-010`).
    - `TASK-05-03`: Implement multi-dimensional cache key generator ensuring isolation across title, index version, playback timestamp boundary, spoiler state, and model prompt version (`SRS-SPO-001`, `AC-014`).
    - `TASK-05-04`: Build dedicated adversarial spoiler regression test suite covering future twist questions, character name queries, recap spoofing, and consent forgery (`SRS-SPO-006`).

### Phase 6: Fire TV 10-Foot User Interface & Remote D-Pad Navigation
- **EPIC-06: TV Client Experience & Remote Navigation**
  - **STORY-06-S1: 10-Foot Layout & Focus Management**
    - `TASK-06-01`: Build TV-first responsive web client (React/HTML5/Vanilla CSS) supporting Fire TV display resolutions (1080p/4K) and 10-foot viewing distances.
    - `TASK-06-02`: Implement complete remote-control D-pad navigation (`ArrowUp`, `ArrowDown`, `ArrowLeft`, `ArrowRight`, `Enter`, `Back/Escape`) with visible high-contrast focus rings and focus trapping (`NFR-ACC-001`, `AC-017`).
    - `TASK-06-03`: Implement TV screens: Catalog Browser, Title Detail / Manual Position Slider, Question Prompt Input, Answer View with Timestamp References, and Modal Spoiler Warning Dialog.
    - `TASK-06-04`: Connect TV client to backend API with robust loading skeletons, offline states, and graceful error messages.

### Phase 7: End-to-End Integration, Evaluation & Adversarial Test Suites
- **EPIC-07: Full Journey Validation & Golden Dataset Evaluation**
  - **STORY-07-S1: System Integration & Scenarios AC-001 to AC-020**
    - `TASK-07-01`: Implement automated end-to-end test suite exercising user journeys: title select -> manual progress -> ask question -> retrieve grounded answer -> spoiler confirmation.
    - `TASK-07-02`: Build golden evaluation dataset with synthetic movie transcripts and validated Q&A pairs to benchmark groundedness, citation precision, and spoiler containment.
    - `TASK-07-03`: Execute full regression suite covering AC-001 through AC-020.

### Phase 8: Operational Readiness, Hardening & Release Candidate
- **EPIC-08: DevOps, Security Review & Release Verification**
  - **STORY-08-S1: Production Hardening**
    - `TASK-08-01`: Containerization (Dockerfile, docker-compose for local development with PostgreSQL + pgvector).
    - `TASK-08-02`: Security audit: secret scanning, dependency vulnerability scan, IDOR checks, CORS and CSP headers.
    - `TASK-08-03`: Operational runbooks: database backup/restore verification, rights-revocation unpublish procedure (`AC-016`), and release checklist sign-off.

---

## 4. Phase Exit Criteria & Gating

- **Phase 0 Exit:** Traceability matrix complete, repo audit baseline recorded, git repo clean, tracking documents established.
- **Phase 1 Exit:** Config validation, logging redaction, health checks, error envelopes passing all unit tests.
- **Phase 2 Exit:** Domain models and migrations verified with automated schema tests.
- **Phase 3 Exit:** SRT/VTT parsing, chunking, idempotency, and staging index tests passing (`AC-012`, `AC-013`, `AC-019`).
- **Phase 4 Exit:** RAG pipeline, context builder, model adapters, and citation validation passing (`AC-005`, `AC-006`, `AC-007`).
- **Phase 5 Exit:** Spoiler policy, nonces, cache isolation, and adversarial suites passing 100% (`AC-003`, `AC-004`, `AC-009`, `AC-010`, `AC-014`).
- **Phase 6 Exit:** TV client remote navigation and focus order verified (`AC-017`).
- **Phase 7 Exit:** AC-001 through AC-020 end-to-end verified.
- **Phase 8 Exit:** Full release checklist approved. Local commit created on `main`. No unauthorized remote push.
