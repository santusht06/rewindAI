# 02 — Software Requirements Specification (SRS)

## 1. System boundary
Rewind consists of a TV client, backend API, identity/session services, title catalog, authorized-content ingestion/indexing pipeline, retrieval/answer orchestration, persistence, model-provider adapters, and operations/administration tooling. External streaming applications are outside the system boundary unless a specific supported integration is proven and authorized.

## 2. Functional requirements
### Catalog and sessions
- SRS-CAT-001: The system MUST list only titles marked published and available to the current user/region.
- SRS-CAT-002: Each title MUST have a stable internal ID distinct from its display name and external identifiers.
- SRS-CAT-003: The system MUST distinguish unsupported title, supported title with unavailable index, and transient catalog failure.
- SRS-SES-001: Every question MUST be associated with a valid session and a title.
- SRS-SES-002: The backend MUST validate session ownership on every private operation.
- SRS-SES-003: Session progress MUST record its source (verified integration, user-confirmed manual progress, or unknown), value, and update time.
- SRS-SES-004: Unknown or stale progress MUST NOT be treated as a verified playback position.
### Question and answer
- SRS-QA-001: Questions MUST be size-limited and validated server-side.
- SRS-QA-002: Retrieval MUST apply title, publication, authorization and spoiler filters before evidence is sent to the LLM.
- SRS-QA-003: The system MUST retrieve a bounded number/token budget of relevant chunks; it MUST NOT send the entire movie/transcript by default.
- SRS-QA-004: Answer generation MUST use only permitted evidence for plot-specific claims.
- SRS-QA-005: Each material plot claim SHOULD map to one or more evidence chunks/time ranges.
- SRS-QA-006: If evidence is absent, contradictory, malformed or outside the permitted range, the system MUST abstain or ask a clarifying question.
- SRS-QA-007: The server MUST validate source IDs against the actual retrieved set and MUST reject fabricated references.
- SRS-QA-008: The client MUST distinguish a grounded answer, clarification request, unsupported question, and service failure.
- SRS-QA-009: LLM output MUST be treated as untrusted data and schema-validated before rendering.
### Spoiler control
- SRS-SPO-001: Spoiler policy MUST be enforced on the server, not solely in client code or prompts.
- SRS-SPO-002: Retrieval filters MUST use a trusted progress boundary where one exists.
- SRS-SPO-003: If progress is unknown, the system MUST ask the user to set/confirm progress or clearly use a manual mode; it MUST NOT imply automatic synchronization.
- SRS-SPO-004: Spoiler confirmation MUST be explicit, scoped, expiring or otherwise governed by a documented policy, and validated server-side.
- SRS-SPO-005: A question asking for future events MUST NOT itself count as spoiler consent.
- SRS-SPO-006: Tests MUST include indirect, ambiguous, character-name, recap, “who is…” and prompt-injection attempts.
### Ingestion and catalog operations
- SRS-ING-001: Only authorized assets may be ingested.
- SRS-ING-002: Ingestion MUST be idempotent for the same source/version/configuration.
- SRS-ING-003: Invalid timestamps, empty assets, unsupported formats and permission failures MUST produce explicit errors.
- SRS-ING-004: Ingestion MUST be staged; incomplete indexing MUST NOT be visible as published.
- SRS-ING-005: Reindexing MUST preserve a rollback path to the last valid index until the replacement is verified.
- SRS-ING-006: Deletion MUST remove or tombstone dependent chunks, embeddings and caches according to retention policy.
- SRS-ING-007: Each ingestion run MUST record source checksum, parser/embedding version, counts, status and errors without exposing secrets.
### Administration
- SRS-ADM-001: Administrative operations MUST require separate authorization.
- SRS-ADM-002: High-impact operations (publish, purge, rights revocation, index replacement) MUST be audited.
- SRS-ADM-003: The system MUST provide health/readiness checks without exposing sensitive configuration.

## 3. Non-functional requirements
- NFR-REL-001: Failures in the LLM provider MUST return a controlled error or safe fallback; no fabricated success.
- NFR-REL-002: External calls MUST have bounded timeouts, bounded retries, and cancellation where supported.
- NFR-REL-003: Retried write operations MUST be idempotent or use an idempotency key.
- NFR-SEC-001: Secrets MUST be stored server-side in an approved secret store/environment and never shipped in the TV client.
- NFR-SEC-002: All database access MUST use parameterized queries or safe ORM operations.
- NFR-SEC-003: Authorization MUST be checked at every trust boundary.
- NFR-PRIV-001: Logs MUST exclude credentials, raw tokens and unnecessary user question content.
- NFR-PERF-001: Latency and concurrency targets are OPEN and must be agreed before production; measure p50/p95/p99.
- NFR-SCALE-001: Stateless API replicas SHOULD be possible unless a documented constraint prevents it.
- NFR-OBS-001: Every request MUST have a correlation/trace identifier; logs, metrics and traces MUST be privacy-aware.
- NFR-ACC-001: All core flows MUST be operable by remote control without a touch screen.
- NFR-MAINT-001: Public API and database schema changes MUST have versioning/compatibility notes.
- NFR-DR-001: Backup, restore and recovery objectives are OPEN and must be tested before production.
- NFR-COST-001: Token, embedding and provider spend SHOULD be measurable by request/title/environment.

## 4. State and error behavior
Use typed states instead of overloaded booleans. Ingestion states: `queued`, `validating`, `processing`, `indexing`, `verifying`, `published`, `failed`, `cancelled`. Question outcomes: `answered`, `needs_clarification`, `insufficient_evidence`, `spoiler_confirmation_required`, `unsupported_title`, `rate_limited`, `temporarily_unavailable`. Keep transport errors distinct from valid domain outcomes.

## 5. Consistency requirements
- A question sees one coherent published index version.
- Title progress and spoiler policy are evaluated for each request.
- A cache hit is valid only if its key includes all answer-affecting inputs: title/index version, normalized question, progress boundary, spoiler policy, locale, model/prompt version and relevant user/session scope.
- Cache must never bypass authorization or spoiler filtering.
- Duplicate ingestion jobs must not create duplicate published chunks.
- If a required invariant cannot be maintained, fail closed and surface an actionable error.
