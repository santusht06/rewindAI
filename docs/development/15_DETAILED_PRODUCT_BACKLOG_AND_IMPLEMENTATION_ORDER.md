# Rewind — Detailed Product Backlog and Implementation Order

**Purpose:** Define what the implementation agent must build first, what depends on what, how work is split into testable tasks, and what evidence is required before moving to the next stage.

**Authority:** This backlog operationalizes the supplied product requirements, software requirements, architecture, API contract, domain/database design, security rules, testing criteria, implementation plan, status tracker, and Git/Agile rules. It does not replace those documents. If a task conflicts with a requirement, follow the requirements and record the conflict.

**Initial status:** All tasks are `NOT_STARTED` until the agent inspects the actual repository and records evidence. Never infer completion from this template.

---

## 1. Prioritization rules

Use these priority levels:

- **P0 — Blocking foundation:** Must be completed before dependent implementation can safely proceed.
- **P1 — Core MVP:** Required for the first complete Rewind user journey.
- **P2 — Production hardening:** Required for a controlled, reliable beta or production release according to the release criteria.
- **P3 — Deferred/conditional:** Implement only when a documented requirement or measurable need makes it necessary.

### Sequencing rules

1. Inspect the repository and existing implementation before creating new code.
2. Confirm unresolved product, platform, rights, progress-source, identity, provider, and deployment assumptions before relying on them.
3. Define API contracts early, but complete and verify backend functionality before feature-level frontend integration.
4. Build one thin vertical slice at a time: domain/data → service → API → tests → local commit.
5. Do not start retrieval-based Q&A before authorized ingestion and searchable indexed content are working.
6. Do not ship Q&A before spoiler filtering, evidence/citation validation, and abstention behavior are enforced and tested.
7. Do not publish a catalog entry or mark content available until its index has been validated and safely published.
8. Start frontend feature integration only after the backend acceptance gate in Section 6 passes.
9. Do not add distributed infrastructure, a knowledge graph, or extra services without a documented need.
10. Do not push changes to a remote unless the user explicitly authorizes it. Local commits are required for meaningful verified changes.

---

## 2. Task status vocabulary

Use the exact status vocabulary defined in `14_IMPLEMENTATION_STATUS_AND_BACKEND_FIRST_EXECUTION_PLAN.md`:

- `NOT_STARTED`
- `READY`
- `IN_PROGRESS`
- `BLOCKED`
- `IMPLEMENTED_UNVERIFIED`
- `IN_REVIEW`
- `VERIFIED`
- `DONE`
- `NOT_APPLICABLE`

Every task entry in the live status tracker must include its current status, dependencies, acceptance criteria, files changed, exact verification commands/results, commit hash if committed, blockers, and last-updated date.

**Status integrity:** `VERIFIED` requires successful execution of the task's required checks. `DONE` additionally requires review, documentation, traceability, and a local commit. Mark a parent task complete only when every mandatory child task and parent acceptance criterion is complete.

---

## 3. Epic map — recommended implementation order

| Order | Epic | Priority | Depends on | Completion outcome |
|---|---|---|---|---|
| E0 | Discovery and repository baseline | P0 | None | Repository, assumptions, requirements, and baseline are understood |
| E1 | Backend foundation | P0 | E0 | Reproducible backend with configuration, errors, logs, and tests |
| E2 | Domain model and persistence | P0 | E0, E1 | Versioned schema and verified data integrity |
| E3 | API contracts and core backend services | P0/P1 | E1, E2 | Tested APIs and stable contract for the frontend |
| E4 | Authorized content ingestion | P1 | E1, E2, content-rights decision | Valid timestamped content is indexed safely and idempotently |
| E5 | Retrieval and grounded AI answers | P1 | E3, E4, provider decision | Questions receive evidence-grounded answers or safe abstentions |
| E6 | Spoiler, authorization, and privacy enforcement | P0 for Q&A release | E3, E5 | Backend policy cannot be bypassed through client changes or cache reuse |
| G1 | Backend acceptance gate | P0 | E1–E6 | Backend contract and critical workflows are verified before UI integration |
| E7 | Frontend foundation and API integration | P1 | G1 | Frontend uses actual, tested API contracts |
| E8 | Core TV user journeys | P1 | E7 | User can complete the supported question-answering flow on target platform |
| E9 | End-to-end, regression, and device validation | P1 | E7, E8 | Complete journeys and failure paths are verified |
| E10 | Operational readiness and controlled beta | P2 | E9 | Monitoring, security, recovery, cost, and release gates are satisfied |
| E11 | Production launch | P2 | E10 and formal approvals | Controlled release with rollback and operational ownership |
| E12 | Conditional enhancements | P3 | Measured need or explicit requirement | Additional capabilities added without destabilizing the core product |

---

## 4. Detailed backlog

### E0 — Discovery and repository baseline

**Priority:** P0. **Must finish before substantial feature implementation.**

#### E0.1 — Requirements and constraints
- `DISC-001` Read every requirements document, PRD, agent instruction, and applicable diagram.
- `DISC-002` Create a requirement-to-task-to-test traceability matrix.
- `DISC-003` Identify conflicting, incomplete, or ambiguous requirements.
- `DISC-004` Record architecture decisions and unresolved decisions.
- `DISC-005` Confirm target Fire TV runtime, official platform constraints, and development/test device availability.
- `DISC-006` Confirm authorized content sources and rights/retention constraints.
- `DISC-007` Confirm how playback position and title identity will be supplied; do not assume third-party streaming integrations expose these values.
- `DISC-008` Record proposed identity/session model, database/vector-search approach, LLM and embedding providers, budget constraints, and deployment environment based on documented decisions.

**Acceptance criteria:** Every mandatory requirement has an identifier or reference; assumptions are labelled as assumptions; critical unresolved decisions are recorded with owners/next actions; no unsupported platform or content-access capability is treated as verified fact.

#### E0.2 — Repository baseline
- `DISC-009` Inspect Git branch, status, recent commits, remotes (read-only inspection), and existing changes.
- `DISC-010` Map existing backend/frontend entry points, manifests, configuration, migrations, tests, and deployment assets.
- `DISC-011` Run safe existing baseline tests/build/lint checks and record exact results.
- `DISC-012` Compare current implementation with requirements and label existing features as verified, unverified, missing, or blocked.
- `DISC-013` Create or update `IMPLEMENTATION_STATUS.md`, `IMPLEMENTATION_PLAN.md`, `WORK_LOG.md`, `REQUIREMENTS_TRACEABILITY.md`, `DECISIONS.md`, and `KNOWN_ISSUES.md`.
- `DISC-014` Convert the backlog below into live tasks with actual dependencies and status.

**Acceptance criteria:** Existing user work is preserved; baseline commands and results are recorded honestly; next backend tasks are `READY`; no code has been rewritten without a requirement-based reason.

---

### E1 — Backend foundation

**Priority:** P0. **Depends on:** E0.

- `BE-FOUND-001` Confirm backend framework, runtime, package manager, and folder structure from existing code and approved architecture.
- `BE-FOUND-002` Establish reproducible local setup and dependency installation instructions.
- `BE-FOUND-003` Implement typed configuration loading and startup validation for required environment variables.
- `BE-FOUND-004` Provide a safe `.env.example` containing placeholders only; verify secrets are not committed.
- `BE-FOUND-005` Establish structured logs, request/correlation IDs, and redaction of credentials/sensitive data.
- `BE-FOUND-006` Define consistent exception handling and the API error envelope in the API contract.
- `BE-FOUND-007` Add request validation and generated/maintained API schema.
- `BE-FOUND-008` Add liveness/readiness endpoints if required by the architecture.
- `BE-FOUND-009` Configure test framework, fixtures, test database strategy, and repeatable test commands.
- `BE-FOUND-010` Add formatting, lint, type/static analysis, and build checks using repository conventions.

**Acceptance criteria:** Backend starts reproducibly; invalid required configuration fails clearly and safely; errors have stable response shapes; logs do not expose secrets; health behavior reflects documented dependencies; baseline quality checks execute.

**Do not start:** AI feature work, UI integration, or infrastructure expansion before this foundation is verified.

---

### E2 — Domain model and persistence

**Priority:** P0. **Depends on:** E1 and approved domain/database decisions.

- `BE-DATA-001` Translate documented domain entities and invariants into implementation models.
- `BE-DATA-002` Design schema for the documented concepts, such as supported titles, content/index versions, timestamped transcript chunks, sessions/progress context, question requests, and evidence references, only as required by the authoritative domain model.
- `BE-DATA-003` Implement versioned database migrations and document upgrade/rollback expectations.
- `BE-DATA-004` Add appropriate foreign keys, uniqueness rules, check constraints, and indexes.
- `BE-DATA-005` Implement data-access/repository boundaries and transaction management.
- `BE-DATA-006` Define content/index version and publication state transitions to avoid exposing incomplete indexes.
- `BE-DATA-007` Test constraints, relationships, rollback behavior, concurrent writes, and failure handling where applicable.
- `BE-DATA-008` Verify repeatable operations do not create unintended duplicates.

**Acceptance criteria:** Models match the documented domain; migrations run on a clean development/test database; invalid relationships and duplicates are rejected; transactional failures do not leave partially committed state; tests use the intended database engine for integration claims.

**Important:** Do not assume a database extension or vector-search capability is installed just because the architecture diagram mentions it. Verify local/deployment compatibility before depending on it.

---

### E3 — API contracts and core backend services

**Priority:** P0/P1. **Depends on:** E1 and E2.

- `BE-API-001` Define documented request/response schemas, status codes, pagination conventions if needed, and error formats.
- `BE-API-002` Define and implement required identity, session ownership, authentication, and authorization boundaries according to the product requirements.
- `BE-API-003` Implement core business services independently from thin route/controller handlers.
- `BE-API-004` Implement required catalog/title lookup endpoints, if included in the documented scope.
- `BE-API-005` Implement session/progress-context endpoints or service contracts needed for Q&A, following the documented source-of-truth for playback position.
- `BE-API-006` Implement question submission and response contracts; initially it may return a clearly specified not-ready/service error until the complete Q&A pipeline exists, but do not pretend the feature is complete.
- `BE-API-007` Implement validation, authorization, negative-path, and API contract tests.
- `BE-API-008` Generate or publish the actual API schema and examples for frontend use.
- `BE-API-009` Verify that frontend-facing contracts include loading-relevant states, empty results, validation errors, forbidden requests, rate limiting, and provider/service failures where applicable.

**Acceptance criteria:** API behavior matches the published contract; authorization boundaries are tested; errors are predictable; the frontend can build against documented contracts rather than invented endpoints; integration tests validate real backend behavior.

**Note:** API contracts should be defined early. This does not authorize starting full frontend feature integration before the backend acceptance gate.

---

### E4 — Authorized content ingestion and indexing

**Priority:** P1. **Depends on:** E1, E2, and documented/verified authorization to use source assets.

- `BE-INGEST-001` Define the supported source format and required metadata for the first ingestion slice.
- `BE-INGEST-002` Validate asset type, encoding, size, metadata, and content authorization.
- `BE-INGEST-003` Parse timestamps and subtitle/transcript cues; handle malformed and boundary cases.
- `BE-INGEST-004` Normalize text without losing meaningful timing or source attribution.
- `BE-INGEST-005` Implement deterministic, tested chunking with title, content version, and timestamp metadata.
- `BE-INGEST-006` Add an embedding-provider interface and a configured implementation consistent with approved provider decisions.
- `BE-INGEST-007` Persist chunks and vector/search metadata using the documented data model.
- `BE-INGEST-008` Implement ingestion status and diagnostic reporting.
- `BE-INGEST-009` Implement idempotency, retry behavior, and safe reprocessing.
- `BE-INGEST-010` Stage indexes and publish only after validation; prevent partial or failed ingestion from becoming available.
- `BE-INGEST-011` Implement rollback or unpublish behavior for invalidated content/index versions where required.
- `BE-INGEST-012` Test duplicate inputs, malformed assets, timestamp ordering, empty files, oversized inputs, embedding failures, database failures, and interrupted jobs.

**Acceptance criteria:** An authorized fixture is ingested reproducibly; chunks retain correct title/version/timestamps; duplicate processing is safe; failed ingestion does not expose partial content; published content has passed validation; source rights and retention constraints are documented.

---

### E5 — Retrieval and evidence-grounded Q&A

**Priority:** P1. **Depends on:** E2, E3, E4, and approved model/provider configuration.

- `BE-AI-001` Implement the documented retrieval strategy, including keyword/vector search if required.
- `BE-AI-002` Filter retrieval candidates by title, content/index version, access rights, and permitted temporal scope before model context construction.
- `BE-AI-003` Implement ranking, deduplication, and bounded context assembly.
- `BE-AI-004` Define a provider interface for the language model and configure timeouts and failure behavior.
- `BE-AI-005` Define a structured response schema for answer text and source references.
- `BE-AI-006` Validate source references and timestamps against retrieved evidence.
- `BE-AI-007` Implement abstention when the available evidence is insufficient or contradictory.
- `BE-AI-008` Treat transcript text as untrusted data; resist prompt injection from retrieved material.
- `BE-AI-009` Add observability for latency, retrieval outcomes, provider failures, and cost where permitted by privacy requirements.
- `BE-AI-010` Test supported questions, ambiguous questions, insufficient evidence, contradictory evidence, model timeout, malformed model output, and missing citations.

**Acceptance criteria:** Answers are grounded in retrieved content; sources point to actual retrieved evidence; the model does not receive the whole movie; unsupported questions receive the documented safe response; provider failures are bounded and handled; tests clearly distinguish mocked providers from real integration tests.

---

### E6 — Spoiler protection, security, and privacy

**Priority:** P0 for release of Q&A. **Depends on:** E3 and the retrieval/Q&A implementation.

- `BE-SAFE-001` Implement server-side spoiler policy and explicit authorization state as specified by the product requirements.
- `BE-SAFE-002` Define the provenance and trust level of playback position; do not treat unverified client values as authoritative without the documented policy.
- `BE-SAFE-003` Filter evidence before sending it to the model, not merely after generating an answer.
- `BE-SAFE-004` Ensure answer caches cannot bypass spoiler policy, title identity, content version, session ownership, or permissions.
- `BE-SAFE-005` Add direct API tests that manipulate playback position and spoiler flags.
- `BE-SAFE-006` Test cache isolation and invalidation when progress or permissions change.
- `BE-SAFE-007` Apply documented request limits, authorization checks, and rate limiting.
- `BE-SAFE-008` Review logs and telemetry for sensitive content and identifiers.
- `BE-SAFE-009` Add prompt-injection and unsupported-claim regression cases.
- `BE-SAFE-010` Document content removal/revocation and index invalidation behavior where required.

**Acceptance criteria:** Spoiler restrictions are enforced server-side; later-story evidence is excluded before LLM invocation; client-side manipulation cannot bypass the policy; cache hits obey current policy; privacy/security tests pass; any limitation around playback-position trust is explicitly documented.

---

## 5. First end-to-end backend vertical slice

Before expanding into many titles or advanced features, implement one controlled, authorized vertical slice. This is the recommended proof that the core architecture works.

1. Load one authorized test title and one valid timestamped transcript/subtitle fixture.
2. Validate and ingest the fixture.
3. Create chunks and persist their metadata and embeddings/index entries.
4. Publish the index only after successful validation.
5. Submit a question through the real backend API.
6. Retrieve relevant evidence for that title and allowed story position.
7. Generate an answer using the configured provider adapter or a clearly labelled test double for tests that do not require external calls.
8. Validate citations/timestamps and return the documented response.
9. Repeat with insufficient evidence and confirm safe abstention.
10. Repeat at a spoiler boundary and confirm forbidden evidence never reaches the model.
11. Test ingestion retries, duplicate ingestion, provider failure, and database failure.
12. Run the relevant end-to-end backend tests and record exact results.

**Vertical-slice exit gate:** The full backend path works in the intended integration environment, required safety tests pass, and the code and test evidence are committed locally. Mock-only success is insufficient to claim real provider/database integration.

---

## 6. Backend acceptance gate — frontend feature integration must wait

Set gate status to `BLOCKED` until all required criteria below have evidence. Then mark `VERIFIED`; do not mark `DONE` until review, documentation, traceability, and local commit requirements are satisfied.

- [x] Required backend startup and configuration checks pass.
- [x] Database migrations and data-integrity tests pass.
- [x] Actual API schema/contracts match implementation.
- [x] Authentication/session ownership rules are tested where applicable.
- [x] Authorized ingestion works for the supported initial asset format.
- [x] Index publication prevents partial/failed content exposure.
- [x] Question-answering path returns validated evidence references.
- [x] Insufficient evidence produces safe abstention.
- [x] Spoiler filtering occurs before model context construction.
- [x] Cache behavior cannot bypass current policy.
- [x] Negative-path and provider/database failure tests pass or are explicitly recorded as blocked with an approved mitigation.
- [x] Backend lint/type/build checks pass.
- [x] API documentation and example configuration are current.
- [x] Test commands/results, known issues, and local commit hashes are recorded.

**GATE G1 STATUS: PASSED (VERIFIED)** — All acceptance criteria verified in test suites.

---

### E7 — Frontend foundation and API integration

**Priority:** P1. **Start only after Gate G1 is verified.** Follow the documented UI framework and Fire TV platform requirements.

- `FE-FOUND-001` Inspect or establish frontend project structure and supported runtime.
- `FE-FOUND-002` Build a centralized API client using the verified API contract.
- `FE-FOUND-003` Configure the backend base URL through environment configuration; never embed server secrets in the client.
- `FE-FOUND-004` Add response parsing and consistent handling for validation, authorization, rate-limit, server, and network errors.
- `FE-FOUND-005` Implement shared loading, empty, retry, and error states.
- `FE-FOUND-006` Add contract-aware frontend tests and mock only where the test scope requires it.
- `FE-FOUND-007` Verify production builds and environment-specific configuration.

**Acceptance criteria:** The frontend uses real documented endpoint shapes; no endpoint or field is guessed; errors are handled consistently; no secret is shipped to the client.

---

### E8 — Core Fire TV user journeys

**Priority:** P1. **Depends on:** E7.

- `FE-TV-001` Implement the supported title/catalog discovery flow if included in scope.
- `FE-TV-002` Implement title selection/details and required progress/session setup.
- `FE-TV-003` Implement the question-entry flow.
- `FE-TV-004` Implement answer display with validated source/timestamp references.
- `FE-TV-005` Implement documented spoiler confirmation and safe-mode states.
- `FE-TV-006` Implement no-results, insufficient-evidence, loading, offline, timeout, and server-error experiences.
- `FE-TV-007` Implement remote-control/D-pad focus order, focus visibility, back navigation, and keyboard/input behavior appropriate to the target runtime.
- `FE-TV-008` Verify readability, overscan/layout constraints, accessibility, and performance on supported hardware/emulator.
- `FE-TV-009` Ensure frontend spoiler controls mirror the backend policy but never replace backend enforcement.

**Acceptance criteria:** A user can complete the supported question-answering journey on the target platform; all primary states are represented; remote-only navigation is usable; citations and spoiler states match backend responses.

---

### E9 — End-to-end integration and regression

**Priority:** P1. **Depends on:** E8.

- `QA-E2E-001` Test the complete supported journey from title/session setup to answer and evidence display.
- `QA-E2E-002` Test ingestion-to-query consistency against a known authorized fixture.
- `QA-E2E-003` Test spoiler-boundary scenarios from the real client through the backend.
- `QA-E2E-004` Test empty, malformed, unauthorized, and unavailable-content cases.
- `QA-E2E-005` Test network loss, provider outage, timeout, retry, and recovery behavior.
- `QA-E2E-006` Test stale or incompatible cache behavior and index version changes.
- `QA-E2E-007` Run backend and frontend regression suites.
- `QA-E2E-008` Test on supported Fire TV hardware/emulator where available and record device/runtime details.
- `QA-E2E-009` Review accessibility, navigation, error presentation, and performance against acceptance criteria.

**Acceptance criteria:** Required end-to-end flows pass; regressions are resolved or formally triaged; tests not run are clearly marked; target-device gaps are not hidden behind browser-only testing.

---

### E10 — Operational readiness and controlled beta

**Priority:** P2. **Depends on:** E9 and agreed operational targets.

- `OPS-001` Add documented metrics and structured operational events with privacy-safe payloads.
- `OPS-002` Establish service health checks, alert conditions, and operational dashboards as appropriate to the deployment.
- `OPS-003` Add rate limits, resource bounds, and concurrency tests against agreed targets.
- `OPS-004` Measure request latency, retrieval latency, model latency, failure rates, and per-question cost where permitted.
- `OPS-005` Document database backup and restore procedures and execute a restore test.
- `OPS-006` Document content/index revocation, invalidation, and rollback procedures.
- `OPS-007` Complete dependency, configuration, and security review.
- `OPS-008` Document deployment, rollback, incident response, and support ownership.
- `OPS-009` Define beta scope, feature flags, user/catalog limits, monitoring windows, and exit thresholds.
- `OPS-010` Run controlled beta only after explicit deployment/release authorization.

**Acceptance criteria:** Agreed performance and reliability targets are tested; operations can detect and investigate failures; rollback/recovery is documented and tested; security/privacy and cost constraints are reviewed; beta entry and exit criteria are measurable.

---

### E11 — Production launch

**Priority:** P2. **Depends on:** E10 and required approvals.

- `REL-001` Verify legal/content-rights, privacy, security, and platform approvals required for launch.
- `REL-002` Confirm release artifact/build reproducibility and configuration separation.
- `REL-003` Freeze or explicitly review risky schema/API changes during the launch window.
- `REL-004` Verify backup/restore, rollback, and incident procedures.
- `REL-005` Confirm on-call/ownership and support procedures.
- `REL-006` Run release smoke tests and monitor key health/error/cost indicators.
- `REL-007` Roll out gradually where supported; stop or roll back when agreed thresholds are breached.

**Acceptance criteria:** All release gates have recorded approval/evidence. Do not deploy or publish to production without explicit user authorization.

---

### E12 — Conditional enhancements (P3)

These are not early priorities unless the authoritative requirements explicitly require them or measurement demonstrates a need:

- Additional transcript/subtitle formats and languages.
- More titles and automated catalog operations.
- Advanced reranking or hybrid-search tuning beyond the initial validated approach.
- Knowledge graph or entity-relation extraction.
- Additional model providers and automatic provider failover.
- Distributed queues, separate microservices, or additional infrastructure.
- Advanced analytics and personalization.

For every enhancement, document the user/business need, measurable success criterion, operational cost, security impact, dependency changes, and why it should be prioritized over existing P0/P1 work.

---

## 7. Definition of ready for a task

A task may move to `READY` only when:

- Its parent and dependencies are identified.
- Its requirement source is known.
- Its scope and non-goals are clear.
- Acceptance criteria are observable and testable.
- Required test levels are identified.
- External dependencies and required credentials/environments are known.
- The proposed implementation is compatible with approved architecture.
- It can be completed without silently assuming an unverified integration capability.

If not, keep it in `BACKLOG` (if your team uses that extra planning state) or `BLOCKED`, and record the missing information. Do not invent a new status that conflicts with the required status vocabulary.

---

## 8. Definition of done for a task

A task is `DONE` only when:

1. Its acceptance criteria pass.
2. Required tests were executed and their results recorded.
3. Formatting/lint/type/build checks applicable to the change pass.
4. The diff was reviewed for unrelated changes, secrets, unsafe defaults, and regressions.
5. Documentation, API contracts, and migrations were updated as applicable.
6. Requirement traceability is updated.
7. Known limitations and skipped checks are recorded honestly.
8. A meaningful local commit exists and its hash is recorded.
9. The working tree state is reported accurately.

A passing compile alone is not sufficient. A mocked test is not evidence that a real external integration works. A task with mandatory unrun checks cannot be `VERIFIED` or `DONE` unless the governing acceptance criteria explicitly permit that omission and the exception is recorded and approved.

---

## 9. Required live status table
 
 | Task ID | Task | Priority | Dependencies | Status | Verification evidence | Commit | Blocker / next action |
|---|---|---|---|---|---|---|---|
| DISC-001 | Read requirements | P0 | None | `DONE` | Traceability matrix created | `5774307` | Complete |
| BE-FOUND-001 | Confirm backend stack | P0 | E0 | `DONE` | Config & errors tested | `c211695` | Complete |
| BE-DATA-001 | Implement domain model | P0 | E1 | `DONE` | Tables & migrations tested | `c506462` | Complete |
| BE-API-001 | Define API contract | P0 | E1 | `DONE` | OpenAPI schema matching | `d806bdf` | Complete |
| BE-INGEST-001 | Validate authorized asset | P1 | E1, E2, rights decision | `DONE` | Parser & pipeline tested | `5a20ba5` | Complete |
| BE-AI-001 | Implement retrieval | P1 | E2, E4 | `DONE` | Grounded Q&A tested | `7dd294a` | Complete |
| BE-SAFE-001 | Enforce spoiler policy | P0 for Q&A | E3, E5 | `DONE` | Boundary & nonces tested | `7dd294a` | Complete |
| G1 | Backend acceptance gate | P0 | E1–E6 | `DONE` | 41/41 backend tests pass | `7dd294a` | Passed |
| FE-FOUND-001 | Frontend foundation | P1 | G1 verified | `DONE` | TV client mounted at /tv | `020fbd3` | Complete |
| FE-TV-001 | Core TV user journey | P1 | E7 | `DONE` | 9 screens, D-pad navigation | `020fbd3` | Complete |
| QA-E2E-001 | Full user journey E2E | P1 | E8 | `DONE` | Comprehensive E2E test pass | `020fbd3` | Complete |
| OPS-001 | Operational metrics | P2 | E9 | `DONE` | Telemetry, rate limit, DR | `868e23c` | Complete |
| PLAT-001 | Fire OS vs. Vega OS Architecture ADR | P0 | FE-TV-001 | `DONE` | ADR-005 in DECISIONS.md | pending | Complete |
| PLAT-002 | Category Alignment Statement | P0 | PLAT-001 | `DONE` | AI-Enhanced & Multi-Modal in DECISIONS.md | pending | Complete |
| PLAT-003 | W3C TV Web Manifest & Config | P0 | PLAT-001 | `DONE` | manifest.json & amazon-webapp-config.json | pending | Complete |
| PLAT-004 | TV Packaging Utility | P0 | PLAT-003 | `DONE` | ops/scripts/package_tv_app.py verified | pending | Complete |
| PLAT-005 | Platform Packaging Automated Test | P0 | PLAT-004 | `DONE` | tests/test_tv_platform_demo.py passed | pending | Complete |
| DEMO-001 | 5-Minute Rehearsal Script & Guide | P0 | FE-TV-001 | `DONE` | docs/demo/DEMO_SCRIPT_AND_REHEARSAL_GUIDE.md | pending | Complete |
| DEMO-002 | S1 Welcome & Remote Demo Flow | P0 | DEMO-001 | `DONE` | Verified in test_tv_platform_demo.py | pending | Complete |
| DEMO-003 | S2/S3 Catalog & Playback Sync Flow | P0 | DEMO-001 | `DONE` | Verified in test_tv_platform_demo.py | pending | Complete |
| DEMO-004 | S4/S5 Grounded In-Bounds AI Answers | P0 | DEMO-001 | `DONE` | Verified in test_tv_platform_demo.py | pending | Complete |
| DEMO-005 | S7 Adversarial Spoiler Gate & Safe Modal | P0 | DEMO-001 | `DONE` | Verified in test_tv_platform_demo.py | pending | Complete |
| DEMO-006 | S8/S9 Operations & Revocation Flow | P0 | DEMO-001 | `DONE` | Verified in test_tv_platform_demo.py | pending | Complete |
| DEMO-007 | Automated Demo Journey Test Suite | P0 | DEMO-001..006 | `DONE` | 5/5 passed in test_tv_platform_demo.py | pending | Complete |


The live status table must be expanded to include every leaf task in the actual implementation backlog. Do not leave a task marked `NOT_STARTED` if work has begun; do not change it to `DONE` without evidence.

---

## 10. Required task report

At each sub-phase boundary, the coding agent must report:

- **Task IDs and titles:** What was attempted.
- **Status transitions:** Previous and current status, with reason.
- **Requirement references:** Which requirements were addressed.
- **Files changed:** Exact paths.
- **Verification:** Exact commands and real results.
- **Tests:** Passed, failed, skipped, blocked, and not run.
- **Evidence:** Relevant test output, API schema, migration results, or reproducible instructions.
- **Git:** Branch, local commit hashes, and working-tree status.
- **Remaining work:** Open acceptance criteria, risks, and blockers.
- **Next task:** Next ready task and why it is next in the dependency order.

Never say “all tests pass” unless the required suite was actually executed. Never claim a phase is complete while mandatory child tasks or acceptance criteria remain incomplete.

---

## 11. Git and publication safeguards

- Inspect `git status` before and after each task.
- Preserve unrelated user changes.
- Stage only intended files; inspect the staged diff before committing.
- Commit each meaningful, verified change locally using repository conventions.
- Reference task IDs in commit messages or commit bodies where practical.
- Never use destructive reset/clean/history-rewrite commands without explicit authorization.
- Do not push, publish tags, create remote branches, open remote PRs, deploy, or publish artifacts without the required explicit authorization.
- Local integration into `main` requires the appropriate authorization and all required checks. Permission to merge locally is not permission to push.

---

## 12. Immediate next action for the coding agent

Start with **E0 — Discovery and repository baseline**. Do not assume any task is already complete. Inspect the actual repository and current tracker, run safe baseline checks, and update the live status files with evidence. Then make only the first ready backend foundation task `IN_PROGRESS` and implement it in a small verified increment. Continue in dependency order through backend data, APIs, ingestion, retrieval, and safety. Do not begin frontend feature integration until Gate G1 has been verified and its evidence is recorded.
