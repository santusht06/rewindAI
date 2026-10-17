# Rewind — Complete End-to-End Requirements (Consolidated)

> Filename retained from the supplied template. The product in this specification is Rewind. If “GoBuddy” is a separate product rather than a template filename, stop and clarify before using this file for that product.

## 1. Executive summary
Rewind is a TV-first AI story companion for supported titles. It answers plot/context questions from authorized, timestamped transcript/subtitle evidence. The core safety property is that story evidence is filtered by server-enforced progress/spoiler policy before it reaches the LLM. When context is missing, untrusted or contradictory, Rewind asks for clarification or abstains.

## 2. Scope
In scope: supported-title catalog, session/progress state, grounded Q&A, timestamped citations, spoiler control, authorized content ingestion/indexing, operational status, security/privacy, evaluation and TV-first UI.
Out of scope by default: protected media extraction, DRM bypass, unverified streaming-provider integration, unrestricted internet chatbot, full movie context in every prompt, and premature distributed architecture.

## 3. Primary users
Viewer, catalog operator, administrator and coding agent. All operations enforce least privilege.

## 4. End-to-end viewer flow
Open catalog → select supported title → confirm progress if not verifiable → ask question → authorize and validate session → apply spoiler policy → retrieve bounded permitted evidence → generate structured answer → validate citations and policy → display answer or abstention. Errors provide a clear recovery path.

## 5. Core invariants
1. No unauthorized asset is ingested or served.
2. No LLM sees future/unpermitted evidence.
3. Client input cannot grant admin rights, verified progress or spoiler consent.
4. Every citation points to real evidence retrieved for the request.
5. Unknown evidence means abstention, not invented facts.
6. Ingestion retries do not duplicate logical content.
7. Failed reindex does not replace the last good index.
8. Authorization occurs before cache access.
9. A cache key accounts for all answer-affecting policy/index/model inputs.
10. No secrets or unnecessary personal content in logs or client bundles.
11. Destructive actions require explicit authorization, audit and recovery planning.
12. The agent reports actual tests and limitations truthfully.

## 6. Architecture baseline
TV client; API; session/policy service; catalog; ingestion worker; relational database plus approved full-text/vector search; retrieval and answer orchestration; LLM/embedding adapters; operations and monitoring. Redis, queues, graph DB, separate search infrastructure and microservices are optional, justified only by evidence and scale requirements.

## 7. Ingestion
Verify rights → idempotency fingerprint → validate asset → parse timestamps → normalize/chunk → embed → stage index → validate counts/timestamps/vectors/retrieval → atomically publish → audit/metrics. Never expose partial index. Retain prior valid index for rollback unless rights are revoked.

## 8. Question answering
Validate request and session ownership → resolve trusted progress and spoiler policy → retrieve within title/index/time constraints → rerank/bound context → instruct model to treat evidence as untrusted data → generate structured response → validate outcome and citations → return grounded answer, clarification, insufficient evidence, or controlled error.

## 9. Spoiler rules
Server-side enforcement only. Unknown progress is not permission. The question itself is not consent. Consent requires explicit, server-validated confirmation with documented scope/expiry. Tests must cover indirect leaks and adversarial transcript text. Any confirmed spoiler bypass blocks release.

## 10. Database
Core entities: User, Title, ContentAsset, IngestionRun, ContentChunk, Embedding/model version, PublishedIndex, ViewingSession, Question, optional AnswerCitation and AuditEvent. Use stable IDs, foreign keys, uniqueness, constraints, migrations, transactional publication and explicit retention.

## 11. API
Proposed `/api/v1` contracts: health/live, health/ready, titles list/detail, session create, progress update, question submission, spoiler confirmation, session close/delete, and admin ingestion/status/publish/reindex/content deletion. Final OpenAPI schemas must match actual implementation. Use stable typed outcomes and error envelopes, authorization, limits and idempotency.

## 12. UI
Welcome/identity where needed; catalog; title/progress setup; question screen; answer with evidence; clarification/insufficient evidence; spoiler confirmation; settings/privacy; restricted admin operations. Remote-only navigation, focus visibility, readable text, loading/error/empty states and safe back behavior are mandatory.

## 13. Security and privacy
Use established identity, least privilege, server-side authorization, TLS, secret management, parameterized queries, upload validation, rate limits, log redaction, dependency review, backups, retention/deletion controls, rights revocation workflow and incident runbooks. Treat all transcript and LLM output as untrusted.

## 14. Non-functional requirements
Reliability through bounded timeouts/retries, idempotency and controlled failure; measurable latency/error/cost; privacy-aware observability; accessible remote-only UI; migration compatibility; tested backup/restore. Concrete SLOs, concurrency, retention and budget remain OPEN until agreed.

## 15. Testing
Unit, integration, API contract, end-to-end TV, retrieval/answer evaluation, prompt injection, spoiler regressions, authorization, ingestion failure/idempotency, concurrency, cache invalidation, load/resilience and privacy/security tests. The acceptance suite in `08_TESTING_AND_ACCEPTANCE_CRITERIA.md` is mandatory.

## 16. Coding-agent contract
Inspect repository and git status first. Discover actual stack. Plan by requirement IDs. Reuse shared components. Make small changes. Never invent APIs or claim unrun checks passed. Add tests for happy path, negative, boundary, security and regression. Run formatter/linter/types/tests/build. Review diff. Stop before destructive or policy-sensitive decisions without approval. Report implementation, files, exact verification results, limitations and follow-ups.

## 17. Production safeguards
Centralize policy, use database constraints and transactions, atomically publish index versions, authorize before cache, bound resources, monitor errors/cost/quality, test restore and rollback, and maintain runbooks. Do not add infrastructure without a demonstrated need.

## 18. Release gate
No launch until: rights/permissions reviewed; critical acceptance tests pass; no known critical/high security issue; spoiler suite passes; migration and rollback tested; target device flow verified; observability/alerts configured; backup restore proven; cost limits set; retention/deletion documented; and owners accept residual risks.

## 19. Open decisions that must be resolved
- Exact Fire TV runtime/framework and distribution path.
- Supported catalog, content source and proof of processing rights.
- Whether/how playback position can be verified.
- Authentication provider and account model.
- LLM and embedding providers, model versions and fallback.
- Database/vector search deployment.
- Consent scope/expiry and manual progress semantics.
- Supported languages and voice input.
- Data retention, deletion, analytics and privacy policy.
- Target concurrency, latency SLOs, availability, recovery objectives and cost ceiling.
- Admin operator workflow and incident ownership.

## 20. Source-of-truth map
Detailed requirements are defined in numbered documents 01–12. If this consolidated file conflicts with a detailed file, record the conflict and reconcile both; do not silently select one. Keep all files versioned together.
