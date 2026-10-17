# 11 — Production Engineering Guardrails

## 1. Shared-component discipline
Before creating a UI component, API client, repository, service, validator, logger, cache or provider adapter, search for an existing one. Extend the existing abstraction if it remains cohesive. Extract a shared component only when at least two real call sites share stable behavior or a clear domain boundary warrants it. Avoid both copy-paste duplication and premature generic frameworks.

## 2. Single source of truth
- Define API schemas once where the stack allows generation of server/client types.
- Centralize spoiler policy, progress trust and citation validation.
- Use one canonical title identity and one active-index pointer.
- Keep environment-specific values in validated configuration.
- Avoid duplicated business rules in frontend and backend; frontend may improve UX but backend decides authority.

## 3. Transactions and concurrency
- Use database constraints as a final defense, not only application checks.
- Publish/reindex with atomic state transitions.
- Use row/version locking or optimistic concurrency for conflicting operations.
- Define transaction boundaries; never hold DB transactions open during slow model calls.
- Use an outbox only if reliable event publication is required and the actual architecture justifies it.
- Queue jobs must have deduplication, bounded retries, dead-letter/failed state and operator recovery.

## 4. Cache correctness
- Cache only after measuring need.
- Authorize before cache lookup.
- Include index version, progress, spoiler policy, locale and prompt/model version in answer cache identity.
- Invalidate on title unpublish, rights revocation, index swap and policy changes.
- Set TTLs intentionally; do not treat TTL as a substitute for invalidation.
- Cache failures must degrade safely to the source of truth.

## 5. Reliability
- Define timeouts at every network boundary.
- Retry only transient errors, with capped exponential backoff and jitter; do not retry indefinitely.
- Use circuit breaking/bulkheads only when justified and correctly configured.
- Bound request sizes, result counts, token budgets and worker concurrency.
- Support cancellation and idempotency for expensive operations.
- Return stable domain outcomes and actionable errors.
- No unbounded loops, unbounded queues or unbounded pagination.

## 6. Observability
Every request/job should have correlation ID, component, operation, outcome, duration and relevant version metadata. Metrics: request rate, latency, error class, provider latency/failures, token/cost use, retrieval counts, abstention rate, ingestion duration/failure, queue age and active index version. Avoid high-cardinality labels and sensitive payloads. Add alerts with actionable runbooks.

## 7. Configuration and secrets
Validate required config at startup; fail early with a safe message. Keep example config secret-free. Use separate credentials per environment and least privilege. Rotate secrets. Never log complete environment variables. Do not embed LLM keys in a TV application.

## 8. Data lifecycle
Define retention and deletion semantics for sessions, questions, answers, source assets, chunks, vectors, logs and backups. Deletion must invalidate caches and search indexes. Rights revocation must prevent new retrieval immediately, even if physical cleanup is asynchronous. Document eventual cleanup and verify it.

## 9. Dependency and supply-chain controls
Pin compatible dependencies through the project lockfile. Review new dependency purpose, license, maintenance, security advisories and transitive impact. Run dependency and secret scans where available. Do not upgrade broad dependency sets as an unrelated side effect.

## 10. Release and rollback
Use staged deployments, health checks, backward-compatible migrations, feature flags for risky features, versioned prompts/indexes and rollback plans. A rollback must not reactivate content whose rights were revoked. Never rollback security policy to a weaker state simply to restore availability.

## 11. Production readiness checklist
- [ ] Auth and ownership checks verified.
- [ ] Spoiler regression suite passed.
- [ ] Ingestion idempotency and failed-run recovery tested.
- [ ] Citation validation tested.
- [ ] Cache invalidation tested.
- [ ] Rate limits, timeouts and request/token limits set.
- [ ] Secrets and sensitive logs reviewed.
- [ ] Backups and restore tested.
- [ ] Alerts and runbooks available.
- [ ] Cost budgets/alerts configured.
- [ ] Rights, retention and deletion behavior reviewed.
- [ ] Supported TV hardware/device flow tested.
