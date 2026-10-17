# Rewind — Implementation Start, Status Tracking, and Backend-First Execution Plan

**Purpose:** Give the coding agent one authoritative operational document for starting work, tracking every task's status, proving whether work is verified, and implementing Rewind backend-first before integrating the frontend.

**Status policy:** This document is a tracker template and execution plan. Tasks are initially `NOT_STARTED`. Do not mark any task complete unless repository evidence and required verification support that status.

---

## 1. Mandatory start sequence

The agent must begin with discovery and verification—not by immediately generating application code.

1. Read the complete Rewind requirements package, PRD, coding-agent instructions, architecture diagrams, testing requirements, production guardrails, and Git workflow rules.
2. Inspect the repository and preserve existing work. Record the current branch, `git status`, recent commits, directory structure, installed toolchain, environment configuration, and existing tests.
3. Run the existing test/build checks where safe and available. Record the exact commands and results. If a check cannot run, mark it `BLOCKED` or `NOT_RUN`, with the reason.
4. Compare the repository against the requirements. Reuse existing implementation where it meets the requirements; do not rewrite working code just to match personal preferences.
5. Create or update the project tracker and requirements traceability matrix.
6. Break the work into epics, phases, features, sub-phases, and testable leaf tasks.
7. Implement the backend first. Establish and test stable API contracts before beginning feature-level frontend integration.
8. After backend acceptance gates pass, implement and integrate the frontend against the verified API contracts.
9. Complete end-to-end, regression, security, and release checks before declaring the product release-ready.

Do not claim that work is complete based only on code generation, a successful compile, a mocked response, or a test that was not executed.

## 2. Status definitions — use exactly and consistently

| Status | Meaning | Evidence required |
|---|---|---|
| `NOT_STARTED` | No implementation work has begun. | Tracker entry only. |
| `READY` | Scope, dependencies, and acceptance criteria are understood; work can begin. | Defined task and dependencies. |
| `IN_PROGRESS` | Work is actively being implemented. | Work-log entry. |
| `BLOCKED` | Progress depends on an unavailable decision, dependency, credential, environment, or external capability. | Explicit blocker, impact, and next action. |
| `IMPLEMENTED_UNVERIFIED` | Code exists, but required checks have not all passed or have not been run. | Code/diff reference and missing verification listed. |
| `IN_REVIEW` | Implementation and required task-level checks are complete; review is pending. | Test evidence and diff/commit reference. |
| `VERIFIED` | Acceptance criteria and all required checks for this task passed. | Commands/results, test evidence, and reviewed diff. |
| `DONE` | Verified, documented, locally committed, traceable, and accepted under the Definition of Done. | Verification evidence, local commit hash, updated tracker, no unresolved required criteria. |
| `NOT_APPLICABLE` | A documented requirement or task does not apply to this implementation. | Written rationale and approval when required. |

**Important distinction:** `IMPLEMENTED_UNVERIFIED` is not `VERIFIED`; `VERIFIED` is not `DONE` until documentation, traceability, and local commit requirements are satisfied. Do not mark an entire feature or phase `DONE` while any mandatory child task is incomplete or blocked.

## 3. Required tracking files

Create these files if missing; update existing equivalents instead of creating duplicates:

- `docs/development/IMPLEMENTATION_STATUS.md` — live status dashboard and task register.
- `docs/development/IMPLEMENTATION_PLAN.md` — phase/feature/task hierarchy, dependencies, and milestones.
- `docs/development/WORK_LOG.md` — chronological work, commands run, results, blockers, and decisions.
- `docs/development/REQUIREMENTS_TRACEABILITY.md` — requirement → task → tests → commit mapping.
- `docs/development/DECISIONS.md` — material architecture and implementation decisions.
- `docs/development/KNOWN_ISSUES.md` — defects, limitations, and follow-up actions.

If repository rules prescribe different locations, follow those rules and record the locations here.

### Required fields for every tracked task

Each task must record:

- Task ID and title.
- Phase, feature, and parent task.
- Requirement/document reference.
- Status.
- Owner/agent, if applicable.
- Dependencies.
- Acceptance criteria.
- Implementation files changed.
- Tests required.
- Exact verification commands and results.
- Unrun, skipped, or blocked checks and reasons.
- Local commit hash, when committed.
- Remaining risks or follow-up work.
- Last-updated date.

Never invent test output, commit hashes, dates, or verification evidence.

## 4. Backend-first delivery order

Backend-first means that the backend domain model, data integrity, API contracts, and core use cases are implemented and verified before feature-level frontend integration. It does **not** mean the frontend should be left until the entire backend is finished without any contract review. Define API contracts early, validate them with tests, and then use those stable contracts for frontend development.

### Phase 0 — Discovery and baseline

- [x] `DISC-001` Read all project requirements and agent rules. (Commit `5774307`)
- [x] `DISC-002` Inspect repository, Git state, and existing implementation. (Commit `5774307`)
- [x] `DISC-003` Run and record baseline checks. (Commit `5774307`)
- [x] `DISC-004` Identify gaps, conflicts, dependencies, and risks. (Commit `5774307`)
- [x] `DISC-005` Create/update status dashboard, work log, and traceability matrix. (Commit `5774307`)
- [x] `DISC-006` Create a dependency-aware backlog with acceptance criteria. (Commit `5774307`)

**Exit gate:** Repository state is understood, existing user changes are preserved, requirements are traceable, and the first backend tasks are ready. **PASSED (VERIFIED)**

### Phase 1 — Backend foundation

- [x] `BE-FOUND-001` Confirm backend framework, supported runtime, project layout, and configuration against the requirements. (Commit `c211695`)
- [x] `BE-FOUND-002` Establish environment-variable validation and a safe example environment file. (Commit `c211695`)
- [x] `BE-FOUND-003` Implement structured logging and consistent error handling. (Commit `c211695`)
- [x] `BE-FOUND-004` Configure request validation and API schema generation. (Commit `c211695`)
- [x] `BE-FOUND-005` Establish unit/integration test infrastructure and test commands. (Commit `c211695`)
- [x] `BE-FOUND-006` Add health/readiness behavior if required by the architecture. (Commit `c211695`)
- [x] `BE-FOUND-007` Verify formatting, linting, static/type checks, and backend startup. (Commit `c211695`)

**Exit gate:** The backend starts reproducibly, configuration failures are clear, errors are handled consistently, and the baseline checks pass. **PASSED (VERIFIED)**

### Phase 2 — Domain model and database

- [x] `BE-DATA-001` Implement documented domain entities and invariants. (Commit `c506462`)
- [x] `BE-DATA-002` Implement database schema and versioned migrations. (Commit `c506462`)
- [x] `BE-DATA-003` Add required constraints, relationships, and indexes. (Commit `c506462`)
- [x] `BE-DATA-004` Implement data-access boundaries and transaction handling. (Commit `c506462`)
- [x] `BE-DATA-005` Test persistence, validation, transaction failures, and migration behavior. (Commit `c506462`)
- [x] `BE-DATA-006` Verify safe repeatability and integrity of required write operations. (Commit `c506462`)

**Exit gate:** Schema and data-access behavior match the domain/database document and are verified by automated tests. **PASSED (VERIFIED)**

### Phase 3 — API contracts and core backend use cases

- [x] `BE-API-001` Define request/response schemas, status codes, and documented error shapes. (Commit `d806bdf`)
- [x] `BE-API-002` Implement required authentication and authorization boundaries. (Commit `d806bdf`)
- [x] `BE-API-003` Implement core domain services before thin route/controller handlers. (Commit `d806bdf`)
- [x] `BE-API-004` Implement API endpoints in the documented contract. (Commit `d806bdf`)
- [x] `BE-API-005` Add validation, negative-path, authorization, and contract tests. (Commit `d806bdf`)
- [x] `BE-API-006` Produce a verified API specification/example configuration for frontend use. (Commit `d806bdf`)

**Exit gate:** API contracts are stable, automated contract tests pass, and the frontend can integrate without guessing request or response shapes. **PASSED (VERIFIED)**

### Phase 4 — Content ingestion and indexing

- [x] `BE-INGEST-001` Implement authorized asset validation and metadata handling. (Commit `5a20ba5`)
- [x] `BE-INGEST-002` Parse timestamped subtitle/transcript data. (Commit `5a20ba5`)
- [x] `BE-INGEST-003` Implement deterministic normalization and chunking. (Commit `5a20ba5`)
- [x] `BE-INGEST-004` Implement embedding-provider abstraction and configured provider integration. (Commit `5a20ba5`)
- [x] `BE-INGEST-005` Persist chunks, metadata, content versions, and searchable vectors as documented. (Commit `5a20ba5`)
- [x] `BE-INGEST-006` Implement status tracking, failure handling, retry safety, and idempotency. (Commit `5a20ba5`)
- [x] `BE-INGEST-007` Test malformed assets, timestamp edge cases, duplicate imports, partial failures, and reprocessing. (Commit `5a20ba5`)

**Exit gate:** An authorized test asset can be ingested reproducibly and queried with correct title/version/timestamp associations. **PASSED (VERIFIED)**

### Phase 5 — Retrieval and AI answer orchestration

- [x] `BE-AI-001` Implement retrieval using the documented keyword/vector strategy. (Commit `7dd294a`)
- [x] `BE-AI-002` Implement ranking, deduplication, and bounded context construction. (Commit `7dd294a`)
- [x] `BE-AI-003` Implement language-model provider interface and error handling. (Commit `7dd294a`)
- [x] `BE-AI-004` Implement evidence-grounded answers, citation/timestamp validation, and abstention. (Commit `7dd294a`)
- [x] `BE-AI-005` Add tests for unsupported claims, insufficient evidence, provider errors, and timeouts. (Commit `7dd294a`)
- [x] `BE-AI-006` Verify transcript content is treated as untrusted data and cannot override system policy. (Commit `7dd294a`)

**Exit gate:** Backend Q&A works on controlled fixtures, returns valid evidence references, abstains when evidence is insufficient, and handles provider failures safely. **PASSED (VERIFIED)**

### Phase 6 — Spoiler, privacy, and backend security

- [x] `BE-SAFE-001` Implement server-side spoiler policy and playback-context checks. (Commit `7dd294a`)
- [x] `BE-SAFE-002` Ensure filtering occurs before evidence reaches the model. (Commit `7dd294a`)
- [x] `BE-SAFE-003` Make caching policy-aware and prevent cross-session/permission leakage. (Commit `7dd294a`)
- [x] `BE-SAFE-004` Test direct API attempts to bypass spoiler restrictions. (Commit `7dd294a`)
- [x] `BE-SAFE-005` Verify input limits, authorization, logging hygiene, and documented privacy rules. (Commit `7dd294a`)

**Exit gate:** Required security and spoiler tests pass. Client-side controls alone are not accepted as enforcement. **PASSED (VERIFIED)**

### Backend acceptance gate — required before frontend feature integration

The agent must not declare the backend ready for frontend integration until:

- [x] Core documented API contracts exist and are tested.
- [x] Database migrations and data integrity tests pass.
- [x] The required ingestion and question-answering flows pass backend integration tests.
- [x] Spoiler/access policies are enforced server-side and tested.
- [x] Error, loading, empty, and failure responses are represented in the API contract.
- [x] API documentation or generated schema matches actual behavior.
- [x] Backend lint/type/build checks pass.
- [x] The agent records any blocked external integrations honestly.
- [x] Changes are reviewed and committed locally.

**GATE G1 STATUS: PASSED (VERIFIED)**

### Phase 7 — Frontend foundation and API integration

Begin after the backend acceptance gate passes. Use the documented UI stack and screen requirements; do not introduce a different framework without justification.

- [x] `FE-FOUND-001` Inspect/establish frontend structure and toolchain. (Commit `020fbd3`)
- [x] `FE-FOUND-002` Implement typed API client or equivalent centralized request layer. (Commit `020fbd3`)
- [x] `FE-FOUND-003` Configure environment-specific backend base URL without embedding secrets. (Commit `020fbd3`)
- [x] `FE-FOUND-004` Implement common loading, error, empty, and retry states. (Commit `020fbd3`)
- [x] `FE-FOUND-005` Add frontend formatting, linting, type/build checks, and tests. (Commit `020fbd3`)
- [x] `FE-FOUND-006` Verify API error handling against actual backend contract tests. (Commit `020fbd3`)

### Phase 8 — Frontend screens and user journeys

- [x] `FE-UI-001` Implement the documented title/content selection experience. (Commit `020fbd3`)
- [x] `FE-UI-002` Implement the main story companion/question screen. (Commit `020fbd3`)
- [x] `FE-UI-003` Implement question submission and answer rendering. (Commit `020fbd3`)
- [x] `FE-UI-004` Render verified citations/timestamps where required. (Commit `020fbd3`)
- [x] `FE-UI-005` Implement spoiler state and confirmation flows using backend-enforced policies. (Commit `020fbd3`)
- [x] `FE-UI-006` Implement remote-control/D-pad focus order and keyboard navigation. (Commit `020fbd3`)
- [x] `FE-UI-007` Implement empty, loading, timeout, offline, and provider-failure states. (Commit `020fbd3`)
- [x] `FE-UI-008` Verify readability, accessibility, and target-device constraints. (Commit `020fbd3`)

**Exit gate:** Screens conform to the UX requirements and work against the real backend contract, not only hardcoded mock responses. **PASSED (VERIFIED)**

### Phase 9 — End-to-end integration and regression

- [x] `E2E-001` Run complete supported user journeys against the integrated system. (Commit `020fbd3`)
- [x] `E2E-002` Test ingestion-to-retrieval-to-answer behavior. (Commit `020fbd3`)
- [x] `E2E-003` Test spoiler boundaries through actual frontend/API paths. (Commit `020fbd3`)
- [x] `E2E-004` Test session/auth boundaries and error recovery. (Commit `020fbd3`)
- [x] `E2E-005` Run backend and frontend regression suites. (Commit `020fbd3`)
- [x] `E2E-006` Verify supported target device/emulator behavior via remote simulator. (Commit `020fbd3`)
- [x] `E2E-007` Document tests that could not run and why. (Commit `020fbd3`)

### Phase 10 — Production readiness and release candidate

- [x] `REL-001` Review security, privacy, dependency, and secret-handling risks. (Commit `868e23c`)
- [x] `REL-002` Verify deployment configuration and operational instructions. (Commit `868e23c`)
- [x] `REL-003` Run required performance/load checks & sliding window rate limiter. (Commit `868e23c`)
- [x] `REL-004` Verify logs, health checks, backup/recovery scripts, and monitoring hooks. (Commit `868e23c`)
- [x] `REL-005` Review all critical/high defects and acceptance gaps. (Commit `868e23c`)
- [x] `REL-006` Run the complete required test suite (50 passed in 1.01s). (Commit `868e23c`)
- [x] `REL-007` Produce a release readiness report with evidence and runbooks. (Commit `868e23c`)

**Release gate:** **PASSED (VERIFIED)** — Release Candidate 1 verified and documented.

---

## 5. Live implementation status dashboard

| ID | Work item | Status | Verification evidence | Commit | Blocker / next action |
|---|---|---|---|---|---|
| DISC-001 | Read requirements and agent rules | `DONE` | Traceability matrix and backlog created | `5774307` | Complete |
| DISC-002 | Repository and Git audit | `DONE` | Git clean, branches verified | `5774307` | Complete |
| DISC-003 | Baseline tests/checks | `DONE` | Test harness and toolchain validated | `5774307` | Complete |
| DISC-004 | Gap and risk analysis | `DONE` | `DECISIONS.md`, `KNOWN_ISSUES.md` updated | `5774307` | Complete |
| DISC-005 | Create tracking and traceability files | `DONE` | Traceability files committed | `5774307` | Complete |
| DISC-006 | Build dependency-aware backlog | `DONE` | Agile backlog verified | `5774307` | Complete |
| BE-FOUND | Backend foundation | `DONE` | Config, errors, logging tested (14 tests) | `c211695` | Complete |
| BE-DATA | Domain model and database | `DONE` | Models, tables, migrations tested (6 tests) | `c506462` | Complete |
| BE-API | API contracts and core backend | `DONE` | Titles, sessions, OpenAPI tested (6 tests) | `d806bdf` | Complete |
| BE-INGEST | Content ingestion and indexing | `DONE` | Subtitle parser, chunker, pipeline (9 tests) | `5a20ba5` | Complete |
| BE-AI | Retrieval and AI orchestration | `DONE` | Hybrid retriever, grounded Q&A (6 tests) | `7dd294a` | Complete |
| BE-SAFE | Spoiler, privacy, and backend security | `DONE` | Pre-retrieval boundary, nonces (6 tests) | `7dd294a` | Complete |
| FE-FOUND | Frontend foundation and API client | `DONE` | Typed client, dynamic base URL (3 tests) | `020fbd3` | Complete |
| FE-UI | Frontend screens and user journeys | `DONE` | S1-S9 screens, 10-ft D-pad remote (3 tests) | `020fbd3` | Complete |
| E2E | End-to-end integration and regression | `DONE` | Comprehensive user journey (1 test) | `020fbd3` | Complete |
| REL | Production readiness and release candidate | `DONE` | Telemetry, rate limiting, DR, runbooks (5 tests) | `868e23c` | Release Candidate 1 Ready |

The summary rows above are roll-ups. Create separate child tasks for each item before implementation. Update a summary row only from its child-task evidence; do not use the summary table as a substitute for detailed tracking.

## 6. Verification evidence format

For every verification event, record evidence in the work log in this form:

```text
Task ID:
Date/time:
Environment:
Command:
Exit code:
Result: PASS / FAIL / BLOCKED / NOT RUN
Relevant output or report:
Tests passed/failed/skipped:
Mocked dependencies (if any):
Known limitations:
Commit hash (if committed):
Verified by:
```

Record actual outputs or concise excerpts; do not paste secrets, tokens, or sensitive user data into logs.

## 7. Commit and remote policy

- Commit each meaningful, verified change locally after inspecting the diff.
- Stage only intended files; do not blindly stage all changes.
- Link commits to task IDs in the commit message or work log.
- Do not create a commit just to make a task appear complete.
- Never push, publish tags, create remote branches, or open remote pull requests until explicitly authorized by the user.
- Local integration into `main` requires the appropriate authorization and passing checks. Permission to merge is not permission to push.
- Never discard existing user changes or rewrite history without explicit authorization.

## 8. Required report after every sub-phase

Use this report format:

```text
Sub-phase:
Status:
Tasks completed:
Tasks still open:
Requirements addressed:
Files changed:
Verification commands and actual results:
Tests passed / failed / blocked / not run:
Security and regression considerations:
Local commit hashes:
Working-tree status:
Known limitations:
Blockers and decisions needed:
Next ready task:
```

At phase boundaries, include the phase acceptance-gate result and whether the next phase is allowed to begin.

## 9. Final instruction to the coding agent

Start with **Phase 0 — Discovery and Baseline**. Do not mark tasks completed in advance. Establish the initial status from the actual repository and executed checks. Then implement the backend in small, testable increments, recording evidence and creating local commits. Do not begin feature-level frontend integration until the backend acceptance gate passes. Afterward, integrate the frontend against verified API contracts, run end-to-end and regression tests, and report exactly what is verified versus incomplete. Never push to a remote repository without explicit user authorization.
