# 09 — Implementation Plan

## Phase 0 — Repository and product discovery
- Inspect repository, git status, manifests, runtime, build scripts, tests, deployment and existing architecture.
- Confirm target TV runtime and official platform constraints.
- Resolve content authorization, title catalog, progress-source strategy, authentication, provider selection, budget and retention.
- Produce a current-state map, requirement gap analysis and architecture decision records.
**Exit:** no major platform/security/rights assumption is treated as fact without evidence.

## Phase 1 — Foundations
- Establish environment/config validation, secret handling, request IDs, logging redaction, migrations, health endpoints and CI.
- Define API schemas and error envelope.
- Add typed domain models and authorization boundaries.
**Exit:** clean build, tests and migrations in development/staging.

## Phase 2 — Authorized ingestion vertical slice
- Implement one supported authorized subtitle/transcript format.
- Add validation, parsing, chunking, idempotency, staging index and status reporting.
- Add retrieval smoke tests and publish/rollback behavior.
**Exit:** malformed and duplicate input tests pass; failed ingestion never publishes partial content.

## Phase 3 — Grounded question API
- Implement session ownership, progress provenance, spoiler policy and filtered retrieval.
- Add provider adapter, structured output schema and citation validation.
- Add abstention behavior and prompt-injection regression tests.
**Exit:** acceptance tests AC-003 through AC-015 pass.

## Phase 4 — TV user experience
- Implement catalog, title details/progress setup, question screen, answer/citations, errors and spoiler confirmation.
- Verify remote-only focus/navigation and target device constraints.
**Exit:** core user journey passes on supported hardware/emulator.

## Phase 5 — Reliability, privacy and operations
- Add rate limits, metrics, tracing, cost accounting, alerts, backup/restore, rights-revocation workflow and admin audit.
- Load-test agreed concurrency and latency targets.
- Run security review and dependency audit.
**Exit:** operational readiness checklist approved.

## Phase 6 — Controlled beta
- Limit catalog and users; use feature flags and gradual rollout.
- Review groundedness, spoiler reports, latency, provider cost and error rates.
- Maintain rollback capability for app, prompt, model and index versions.
**Exit:** agreed beta exit thresholds met.

## Phase 7 — Production launch
- Confirm legal/rights/privacy review, on-call ownership, incident runbooks, support process and restore test.
- Freeze risky schema/API changes during launch window.
- Release gradually and monitor.
**Exit:** launch checklist signed off.

## Required deliverables per phase
- Code and tests.
- Updated requirements/API/schema docs.
- Migrations and rollback/recovery notes.
- Metrics and failure behavior.
- Security/privacy review for changed boundaries.
- Agent report listing exact commands run, results, skipped checks and unresolved risks.

## Sequencing rules
Do not build the UI against imaginary endpoints. Define and validate API contracts first. Do not ship Q&A before spoiler and citation enforcement. Do not publish a catalog entry before a verified index exists. Do not add distributed infrastructure before a measurable need exists.
