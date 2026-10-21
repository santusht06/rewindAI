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
- **Consequences:** In safe mode, future subtitle chunks excluded by the server-side retrieval boundary are not available as evidence to the model. This is a strong defense for indexed transcript evidence, not a guarantee against every possible spoiler source, implementation defect, or information disclosed elsewhere in the product.

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

---

## ADR-005: Fire OS vs Vega OS Target Selection & Dual-Target Deployment Strategy

- **Status:** APPROVED
- **Date:** 2026-10-18
- **Context:** Rewind must deliver a demo-ready application that runs on Amazon television platforms (Fire OS or Vega OS). Amazon is transitioning from Fire OS (Android AOSP fork) to Vega OS (Linux microkernel runtime executing web technologies and React Native, dropping Android/AOSP). The application must run reliably without platform lock-in.
- **Alternatives Evaluated:**
  1. *Native Android APK (Kotlin/Java):* Compatible only with legacy Fire OS (Fire TV Stick 4K Gen 1/2, Fire TV Cube). Completely incompatible with new Vega OS devices because Vega OS does not include the Android ART runtime.
  2. *Vega OS C++ Native / React Native only:* Limits testing to internal Amazon hardware not generally accessible outside developer programs, breaking standard local verification.
  3. *Universal W3C 10-Foot Television Web Application (`HTML5 / Modern CSS / Vanilla JS / W3C Spatial Navigation`):* 
     - Supported natively on **Fire OS** via Amazon Web App Tester, Amazon Hosted Web Apps, and standard Chromium-based System WebView APK wrapper.
     - Supported natively on **Vega OS**, which uses modern Web Standards / Chromium engine as its primary first-party application execution environment.
     - Allows zero-dependency testing on any television browser, emulator, or desktop simulator while guaranteeing 100% binary/runtime compatibility across both Fire OS and Vega OS.
- **Decision:** Adopt the **Universal 10-Foot Television Web Application** architecture with explicit dual-target packaging:
  - For **Vega OS:** Packaged as a standard W3C Web App with `manifest.json` configured for TV landscape fullscreen execution.
  - For **Fire OS:** Packaged with `amazon-webapp-config.json` for immediate testing on Amazon Web App Tester and Amazon Hosted Web Apps.
  - For **Evaluation / Demo Rehearsal:** Delivered directly from FastAPI at `/tv/` with an interactive on-screen Fire TV Remote simulator overlay.
- **Consequences:** A shared web client and target-specific packaging reduce duplicated UI work. Manifests and desktop/browser tests do not establish compatibility with every Fire OS/Vega OS version or device. Verify launch, focus/remote behavior, lifecycle, networking, and packaging on the selected target and record the exact environment.

### Platform Validation Caveat

The ADR records the intended dual-target design, not certification or verified physical-device compatibility. Platform compatibility remains open until supported target environments and test evidence are recorded in the implementation tracker.

---

## ADR-006: Cross-App AI Viewing Assistant Interaction Model and Feasibility Fallback Architecture

- **Status:** APPROVED
- **Date:** 2026-10-21
- **Reference:** `17_REWIND_CROSS_APP_ASSISTANT_PRODUCT_REQUIREMENT.md`
- **Context:** Rewind must operate as a cross-application AI viewing assistant (inspired by Google Gemini / Google Assistant overlay patterns) rather than an OTT video player, streaming catalog, or video hosting platform. The user continues watching content in their existing streaming app (e.g., Netflix, Amazon Prime Video, Disney+, YouTube). Rewind is invoked to understand plot, dialogue, characters, and scene context without moving content into a Rewind-owned player.
- **Critical Feasibility Realities:**
  - Modern TV operating systems (Fire OS / Android AOSP and Vega OS Linux) strictly sandbox third-party applications.
  - An ordinary third-party TV app **cannot** draw floating overlays over protected DRM video surfaces (Widevine L1), read active package/window state, inspect video frames, or tap into another app's internal playback position or subtitle stream without system-level platform privileges.
  - Screen scraping, accessibility service abuse, and hidden private APIs are explicitly prohibited by app-store guidelines, DRM security policies, and architectural boundaries.
- **Alternatives Evaluated:**
  1. *Standalone OTT Streaming Player (Rejected):* Building a custom video player and content catalog where movies are uploaded and played. Directly rejected by product requirements; Rewind is not an OTT service.
  2. *Unverified "Magic" Overlay via Unsupported Hacks (Rejected):* Attempting accessibility or window manager abuse to draw over Netflix. Brittle, breaks DRM, violates platform security, and fails completely on Vega OS.
  3. *Provider-Neutral Modular Assistant Architecture with Honest Fallback Hierarchy (Selected):*
     - Decouple the assistant from any specific streaming service using abstract contracts: `PlaybackContextProvider`, `AssistantEntryPoint`, `AssistantPresentationAdapter`, `ContentEvidenceProvider`, and `ProviderCapabilityRegistry`.
     - Implement an explicit **Fallback Hierarchy**:
       1. System assistant / app-to-app integration (where authorized and supported).
       2. Foreground assistant surface with seamless resume to previous app.
       3. Companion device/web assistant paired to TV session with confirmed playback timestamp.
       4. Provider-specific integration (where officially supported by provider APIs).
     - Label all provider capabilities transparently as `VERIFIED`, `PARTIAL`, `UNAVAILABLE`, or `NOT_TESTED`.
- **Decision:** Adopt the **Provider-Neutral Modular Assistant Architecture with Honest Fallback Hierarchy**.
- **Consequences:**
  - The TV client is structured as an assistant shell / companion side panel, not a movie playback destination.
  - Adding a new streaming provider requires only implementing the provider adapter, without modifying core RAG, spoiler controls, or AI orchestration.
  - When automatic playback synchronization is unavailable due to OS sandboxing, the assistant transparently prompts the user for manual timestamp confirmation, maintaining 100% spoiler safety.

---

# 2. Priority Category-Fit Statement (Challenge Alignment)

**Document Reference:** `16_FIRE_TV_VEGA_OS_DEMO_CORE_REQUIREMENT.md`  
**Evaluation Categories:** *AI-enhanced viewing, sports, fitness, family entertainment, multi-modal UX, computer vision.*

### Primary Category: AI-Enhanced Viewing
- **Rationale:** Rewind is fundamentally designed to transform passive media consumption into an interactive, grounded, story-aware companion experience. By synchronizing strictly to the viewer's current playback position, it answers questions ("Who is that?", "Why did they betray them?", "What happened previously?") with mathematical certainty that later plot twists remain concealed.
- **Exact User-Visible Demo Feature:** The 10-foot **Companion Console** (`S4`) and **Grounded Answer Screen** (`S5`), showing verbatim subtitle quotes, speaker labels, and clickable scene jump timestamps [MM:SS] matching the viewer's current timeline.
- **Acceptance Criteria & Verification:** Answers must cite verified timestamped subtitle cues; attempts to query future plot events in `safe` mode must trigger server-side spoiler protection without leaking information (`AC-004`, `SRS-SPO-001`..`006`).

### Secondary Category: Multi-Modal UX
- **Rationale:** Traditional TV interfaces require clumsy onscreen keyboard hunting. Rewind unifies remote D-pad directional navigation, an OLED vanguard double-bezel visual hierarchy, digital clock position synchronization, and auditory story dialogue into a cohesive 10-foot interaction model.
- **Exact User-Visible Demo Feature:** The **Spatial D-Pad Remote Engine** with on-screen Remote Simulator (`apps/tv-client/js/remote.js`), electric-indigo focus rings (`#818cf8`), single-press question presets ("Explain Current Scene", "Catch Me Up", "Who is on Screen?"), and modal focus trapping.
- **Acceptance Criteria & Verification:** The interface is 100% navigable with Arrow keys (`Up/Down/Left/Right`), `OK/Enter`, and `Back/Escape` without mouse, touch, or external hardware dependencies.

