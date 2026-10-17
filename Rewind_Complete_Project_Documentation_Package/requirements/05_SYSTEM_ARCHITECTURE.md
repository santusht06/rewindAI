# 05 — System Architecture

## 1. Architectural approach
Use clear boundaries and a small number of components. Start with a modular backend and separate asynchronous ingestion worker if scale/reliability needs justify it. Do not introduce microservices, queues, Redis, a graph database or multiple model providers merely because they are common patterns; add them only for a documented requirement.

## 2. Logical components
1. **TV client:** catalog browsing, session UI, remote navigation, question entry, progress selection, answer/citation display.
2. **API layer:** authentication, schema validation, rate limits, request IDs, response contracts.
3. **Session/policy service:** title/session ownership, progress trust, spoiler state and consent.
4. **Catalog service:** published titles and index availability.
5. **Retrieval service:** hybrid search, metadata filters, bounded results, deduplication and ranking.
6. **Answer orchestrator:** builds a constrained prompt, invokes model adapter, validates output and citations, returns typed outcomes.
7. **Ingestion worker:** validates authorized assets, parses timestamps, chunks, embeds, indexes, verifies and stages publication.
8. **Persistence:** relational data, content metadata, vectors/full-text index, audit records.
9. **Provider adapters:** LLM and embedding interfaces with timeouts, retries and model/version telemetry.
10. **Operations/admin:** ingestion status, health, audit review, safe reindex/publish and incident response.

## 3. Ingestion flow
1. Authenticate the operator and verify rights/authorization metadata.
2. Create idempotent ingestion run; calculate source/config fingerprints.
3. Validate file type, size, encoding, locale and timestamp format.
4. Parse captions/transcript into timestamped segments; reject malformed or suspicious inputs.
5. Normalize whitespace while preserving meaningful text and timestamps.
6. Chunk by semantic/temporal boundaries within configured size limits. Do not split timestamps from their text.
7. Generate embeddings with explicit model/version/dimension.
8. Write to a staging index version, not the currently published index.
9. Validate counts, timestamp ranges, empty chunks, duplicate hashes, vector dimensions and retrieval smoke tests.
10. Atomically publish the new version; retain the previous version for rollback according to policy.
11. Emit metrics and sanitized audit events. Failed runs must remain diagnosable and never appear published.

## 4. Online question flow
1. Authenticate request and validate request size.
2. Resolve session and verify ownership, title publication and index version.
3. Resolve trusted progress and spoiler policy; if unknown, return a safe clarification path.
4. Normalize question and classify intent only as an aid, not as an authorization decision.
5. Retrieve from the active index using mandatory title/index/time/spoiler filters.
6. Optionally rerank bounded candidates; enforce evidence/token budgets.
7. Build prompt with explicit instructions that retrieved text is untrusted evidence, never executable instructions.
8. Call LLM with timeout, bounded retry policy and model/version metadata.
9. Parse structured output. Validate outcome, citations, source IDs, timestamps and policy compliance.
10. If validation fails, retry only under a bounded, justified policy or abstain.
11. Return typed response and emit privacy-aware telemetry.

## 5. Retrieval and evidence
- Prefer hybrid lexical + vector retrieval when evaluation demonstrates benefit.
- Apply security and spoiler filters before the LLM sees evidence; post-filtering alone is insufficient.
- Enforce per-title and active-index filters.
- Use deterministic ranking tie-breakers for reproducibility.
- Remove near-duplicate chunks where appropriate, but do not discard evidence needed to understand dialogue continuity.
- Do not claim a citation proves more than the chunk contains.
- If evidence conflicts, disclose uncertainty or ask a clarifying question.

## 6. Spoiler model
A spoiler policy is a server-side authorization rule over eligible evidence, not merely a prompt instruction. Evidence must be bounded by a trusted progress position or a clearly declared manual-progress setting. Consider timestamp uncertainty and scenes that span the boundary; use a conservative margin or require confirmation. Consent must be explicit, scoped, auditable and not inferred from the question itself. Define whether consent applies to one question, a session, or a period before implementation.

## 7. LLM adapter
- Keep provider-specific code behind an interface.
- Set request timeout, output token limit, and bounded retries.
- Avoid automatic retries for non-idempotent side effects.
- Validate structured output with a schema.
- Version prompts and record the version used.
- Do not send unnecessary personal data or full transcript context.
- Treat model output as untrusted; never execute generated code or tool calls unless explicitly designed and independently authorized.

## 8. Cache and real-time correctness
Cache only if measurements justify it. Cache keys must include all factors affecting correctness: user/session scope as applicable, title, index version, progress boundary, spoiler state, locale, normalized question, retrieval configuration, model and prompt version. Check authorization before cache access. Invalidate on publish/unpublish, rights changes, progress/policy changes where relevant, and deletion. Never return stale cached answers when policy or evidence changed.

## 9. Deployment topology
A reasonable initial deployment is a TV client, HTTPS API, relational database with full-text/vector capability, a worker process, object storage for authorized source assets if needed, and managed secrets/monitoring. Redis, a task broker, distributed tracing backend and separate search engine are optional decisions based on measured requirements. Separate development, staging and production credentials/data.

## 10. External platform integration
Playback position, subtitles, launch/deep links and identity integration must be verified against official APIs, platform policies and device constraints. Do not reverse-engineer protected streams or bypass DRM. If integration is unavailable, provide manual progress selection and clearly label its limitations.

## 11. Architecture decision records
Record material decisions: selected TV framework, auth, database/vector index, model providers, chunking/retrieval design, content-rights workflow, progress trust model, spoiler consent scope, hosting/SLO, retention, cost budget and backup/recovery objectives.
