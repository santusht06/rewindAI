# Architectural Decision Records (ADRs) — Rewind

**Version:** 1.0  
**Project:** Rewind — Fire TV AI Story Companion  
**Status:** Active  

This document logs significant architectural and implementation decisions, their context, evaluated alternatives, and consequences.

---

## ADR-001: Backend Technology Stack Selection

- **Status:** APPROVED
- **Date:** 2026-10-17
- **Context:** Rewind requires an API layer with high async I/O performance, strong static typing, native integration with AI/LLM SDKs and vector search, robust validation schemas, and automated OpenAPI documentation generation.
- **Alternatives Considered:**
  1. *Node.js / TypeScript (Express or NestJS):* Strong async performance and frontend ecosystem overlap, but AI/ML libraries, text chunking, and evaluation tools are predominantly Python-native.
  2. *Go (Gin/Chi):* High performance and low memory footprint, but less idiomatic for complex LLM prompt construction, structured schema generation, and rapid RAG iteration.
  3. *Python 3.12 / FastAPI + Pydantic v2:* Native async support, high performance via Starlette/Uvicorn, first-class Pydantic v2 schema validation, native AI ecosystem compatibility, and built-in OpenAPI contract generation.
- **Decision:** Use **Python 3.12 / FastAPI + Pydantic v2** as the primary backend stack.
- **Consequences:** Backend developers and coding agents must adhere strictly to PEP 8, full type annotations (`mypy`), async def endpoints, and Pydantic validation at all boundaries.

---

## ADR-002: Persistence Strategy & Vector Search Architecture

- **Status:** APPROVED
- **Date:** 2026-10-17
- **Context:** Rewind requires relational persistence for movies, viewing sessions, question logs, and audit trails, as well as vector and full-text search for subtitle chunks.
- **Alternatives Considered:**
  1. *Dedicated Vector DB (Pinecone, Qdrant, Milvus) + Relational DB:* Increases infrastructure operational complexity, introduces two sources of truth, requires distributed transactions for atomic publish/rollback.
  2. *PostgreSQL with `pgvector` + Full-Text Search (tsvector):* Single unified datastore, transactional guarantees across content version publishing, relational foreign keys protecting chunks and sessions, supported across major cloud providers (RDS, Supabase, Neon). In development/testing, an abstracted repository pattern allows running tests with an in-memory/SQLite equivalent without requiring external Docker services.
- **Decision:** Use **PostgreSQL with `pgvector` and tsvector full-text search** as the production target, managed via SQLAlchemy 2.0 and Alembic migrations. Provide a deterministic in-memory/test adapter for unit and integration testing.
- **Consequences:** Eliminates distributed state inconsistency; atomic publish and rollback operations can be executed inside a single PostgreSQL database transaction.

---

## ADR-003: Server-Side Enforcement of Spoiler Boundaries

- **Status:** APPROVED
- **Date:** 2026-10-17
- **Context:** The system must guarantee that future plot twists and events are never revealed to a viewer who is currently at an earlier playback position, unless explicit server-authorized consent is given.
- **Alternatives Considered:**
  1. *Prompt Engineering Only (telling LLM "don't reveal spoilers"):* Known to fail under adversarial prompting, indirect questions ("who is X really?"), or prompt injection attacks in subtitles.
  2. *Client-side filtering / UI hiding:* Untrusted client can be bypassed by inspecting network payloads or tampering with requests.
  3. *Deterministic Pre-Retrieval Server-Side Filtering:* The retrieval query includes an absolute timestamp ceiling (`end_time_seconds <= current_position_seconds + margin`). Future subtitle chunks are never retrieved from the database, meaning they never enter the LLM prompt context.
- **Decision:** Implement **Pre-Retrieval Server-Side Boundary Filtering** as the primary defense. Post-generation schema validation and citation verification act as secondary defense in depth. Full spoiler mode requires an explicit server-generated, single-use confirmation token.
- **Consequences:** Mathematically impossible for the LLM to reveal future dialogue or transcript details because the evidence does not exist in its prompt context.

---

## ADR-004: Fire TV User Experience & Navigation Architecture

- **Status:** APPROVED
- **Date:** 2026-10-17
- **Context:** Rewind must be operable on Fire TV devices from a 10-foot distance using only a standard D-pad directional remote (Up, Down, Left, Right, Select/Enter, Back).
- **Alternatives Considered:**
  1. *Native Android Java/Kotlin App:* High device-specific fidelity, but slower iteration and requires Android SDK toolchain installation on every development host.
  2. *Fire TV Web App / Progressive Web App (10-Foot UI):* Supported natively by Fire TV Web App Runtime (W3C standards), standard HTML5/CSS/JavaScript with spatial navigation, testable on any browser or TV emulator, full remote key code support (`KeyCode 38, 40, 37, 39, 13, 27`).
- **Decision:** Implement a **10-foot TV Web Client** with dedicated spatial navigation, high-contrast focus rings, remote key event handlers, and remote-accessible keyboard/dial input.
- **Consequences:** Ensures full compliance with Amazon Fire TV 10-foot UX guidelines and enables rapid automated browser-based and E2E testing.
