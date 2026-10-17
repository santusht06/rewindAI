# 04 — API Contract

## 1. General conventions
- Base path: `/api/v1` (proposal; align with existing repository conventions before implementation).
- JSON request/response unless an endpoint explicitly streams.
- Use HTTPS in deployed environments.
- Use a consistent error envelope: `code`, safe human-readable `message`, `request_id`, optional structured `details`.
- Never expose stack traces, provider secrets, SQL, internal prompts, raw tokens, or hidden infrastructure details.
- Validate all inputs server-side; enforce size limits, authentication, authorization, rate limits and timeouts.
- Dates are ISO 8601 UTC; playback positions use integer milliseconds.
- Pagination must be bounded and stable. Avoid unbounded catalog/admin responses.
- Exact schemas must be committed as OpenAPI and contract-tested.

## 2. Proposed endpoints
These are a baseline contract proposal, not proof that an existing implementation already has them.

### `GET /health/live`
Liveness only; returns service process status. Must not depend on every downstream provider.

### `GET /health/ready`
Readiness for traffic; checks essential dependencies with bounded timeouts. Returns no secrets or connection strings.

### `GET /api/v1/titles?query=&cursor=&limit=`
Lists published titles visible to the requester. `limit` has a server-enforced maximum. Response: `items[]` with `id`, `display_title`, `year` if known, `availability`, `index_status` safe for viewers, `next_cursor`.

### `GET /api/v1/titles/{title_id}`
Returns supported metadata and whether questions are available. Must not expose asset storage paths or operator-only rights records.

### `POST /api/v1/sessions`
Request: `title_id`, optional `locale`, optional progress object only if the product supports manual progress. Response: `session_id`, title summary, progress state/source, spoiler mode, required next action. Enforce title availability and user identity.

### `PATCH /api/v1/sessions/{session_id}/progress`
Request: `position_ms`, `source`, optional duration metadata. The server determines whether the source is trusted. A client cannot self-assert `verified_integration`. Response returns normalized position, source and verification status.

### `POST /api/v1/sessions/{session_id}/questions`
Request: `question`, optional client request ID, optional locale. The client MUST NOT choose a privileged spoiler policy via an unchecked request field. Response is a typed outcome:
- `answered`: `answer`, `citations[]` with valid timestamp/title/chunk display metadata, `policy_state`.
- `needs_clarification`: safe clarification question.
- `insufficient_evidence`: explicit uncertainty and suggested next step.
- `spoiler_confirmation_required`: explanation and a server-generated confirmation flow reference.
- `unsupported_title`: safe explanation.
Question size and per-user rate limits apply.

### `POST /api/v1/sessions/{session_id}/spoiler-confirmation`
Request includes a server-issued, single-use or tightly scoped confirmation token/nonce. Response updates the server-side policy state according to documented scope/expiry. Never treat a bare boolean such as `spoilers=true` as authorization.

### `DELETE /api/v1/sessions/{session_id}`
Closes or deletes the session according to product policy. Ownership is required; semantics must be explicit and idempotent where possible.

### Admin ingestion endpoints (separate permission boundary)
- `POST /api/v1/admin/ingestions` — create authorized ingestion job with asset reference, title ID and idempotency key.
- `GET /api/v1/admin/ingestions/{job_id}` — status, counts and sanitized error details.
- `POST /api/v1/admin/titles/{title_id}/publish` — publish only after validation; audit event required.
- `POST /api/v1/admin/titles/{title_id}/reindex` — stage replacement index, verify, then atomically switch active version.
- `DELETE /api/v1/admin/titles/{title_id}/content` — high-impact operation; require explicit authorization, audit and documented deletion semantics.

## 3. Error semantics
- `400` malformed request.
- `401` unauthenticated.
- `403` authenticated but unauthorized.
- `404` unknown or intentionally concealed resource.
- `409` state conflict, duplicate transition or invalid lifecycle operation.
- `413` request too large.
- `422` semantic validation error.
- `429` rate limit exceeded, include `Retry-After` when useful.
- `502/503` provider/dependency unavailable.
- `504` bounded upstream timeout.
Do not use HTTP 200 to represent an infrastructure failure. Valid domain outcomes such as insufficient evidence may be 200 with a typed outcome, if consistently documented.

## 4. Idempotency and concurrency
- Mutating endpoints that can be retried SHOULD accept an idempotency key.
- The server MUST bind a key to actor, endpoint and request fingerprint; reuse with a different payload returns conflict.
- Publish/reindex uses optimistic concurrency or a transaction/lock so two operations cannot activate conflicting versions.
- Retries must not duplicate jobs, chunks, consent grants or audit side effects.

## 5. API security
Authenticate and authorize every private endpoint. Apply request body limits, strict content types, safe CORS, CSRF protection if cookie-based auth is used, and rate limits. Never trust user ID, role, progress source, citation, title publication state or consent claims supplied by the client.

## 6. Contract examples
The exact OpenAPI schema is a required implementation artifact. Examples in this document are conceptual and must be converted into schema-validated fixtures before production. Contract changes require client compatibility tests and a versioning decision.
