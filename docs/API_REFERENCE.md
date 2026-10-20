# API Reference

This reference describes the HTTP routes registered by the current FastAPI application. The generated schema is available at `/openapi.json` (and Swagger UI at `/docs` when not running in production). The checked-in copy is `docs/api/openapi.json`; regenerate it after changing API routes or models:

```bash
python ops/scripts/export_openapi.py
python ops/scripts/export_openapi.py --check
```

The generated OpenAPI schema includes 19 operations. `GET /metrics` is an additional hidden alias and is not included in that schema. The root path redirects to `/tv/`; `/tv/` serves the TV client, not an API resource.

## Conventions and Access

- Base URL: `http://127.0.0.1:8000`
- JSON request and response bodies use `Content-Type: application/json`.
- Application errors use the common envelope described below. Validation errors are HTTP 422.
- Every request receives an `X-Request-ID` response header. A caller may send `X-Request-ID` to supply a correlation ID.
- Session routes accept the optional `X-User-ID` header. If omitted, the service uses the fixed local identity `tv-viewer-primary`. This is not authentication; clients can choose a header value.
- Admin routes require the configured `ADMIN_API_TOKEN` in `X-Admin-Token`. The server returns 503 `ADMIN_AUTH_NOT_CONFIGURED` when no token of at least 32 characters is configured, returns 401 when the request omits the token, and returns 403 for an incorrect token. Comparisons are constant-time. This is a shared-token boundary, not per-operator identity or role-based access control; keep admin routes on a trusted network and rotate the secret through your deployment secret manager. The TV operations panel accepts the token in a password field and keeps it only in page memory; do not use that panel on a shared or untrusted device.
- The default question rate limit is 60 requests per minute, in process memory, keyed by `X-User-ID` or client IP. A rejection returns HTTP 429 with `details.retry_after_seconds`.

## Health and Documentation

| Method and path | Success | Behavior |
|---|---:|---|
| `GET /health/live` | 200 | Returns `status`, `environment`, and `timestamp`. Process liveness only. |
| `GET /health/ready` | 200 | Returns `status`, `timestamp`, and `components`. Component values are currently static; this does not test database connectivity. |
| `GET /health/metrics` | 200 | Returns in-process request/outcome counts, latency percentiles, token totals, and estimated cost. |
| `GET /metrics` | 200 | Hidden alias of `/health/metrics`; omitted from OpenAPI. |
| `GET /openapi.json` | 200 | FastAPI-generated schema. |
| `GET /docs` | 200 | Swagger UI in non-production environments. |
| `GET /redoc` | 200 | ReDoc in non-production environments. |

## Catalog

| Method and path | Parameters / body | Success | Common errors |
|---|---|---:|---|
| `GET /api/v1/titles` | Query: `query` (optional, max 100 chars), `limit` (1-50, default 20), `cursor` (optional) | 200 `TitleListResponse` | 422 |
| `GET /api/v1/titles/{title_id}` | Path: `title_id` | 200 `TitleDetailResponse` | 404, 422 |

`TitleListResponse` contains `items`, `total`, and `next_cursor`. Each item contains `id`, `display_title`, optional `year`, `duration_seconds`, `availability`, `index_status`, and `has_active_index`. The current implementation returns `total` as the number of returned items, does not apply `cursor`, and always returns `next_cursor: null`; do not assume cursor pagination is implemented.

`TitleDetailResponse` contains `id`, `display_title`, optional `year`, `duration_seconds`, `status`, `questions_available`, and `supported_locales`. Only published titles are returned by the detail endpoint.
`supported_locales` lists the currently available translation targets (`en`, `es`, `fr`, `hi`, `ja`); it does not assert that every title's source subtitles use each language.

## Viewing Sessions

| Method and path | Parameters / body | Success | Common errors |
|---|---|---:|---|
| `POST /api/v1/sessions` | Optional `X-User-ID`; `CreateSessionRequest` | 201 `SessionResponse` | 404, 422 |
| `GET /api/v1/sessions/{session_id}` | Path: `session_id`; optional `X-User-ID` | 200 `SessionResponse` | 403, 404, 422 |
| `PATCH /api/v1/sessions/{session_id}/progress` | Path: `session_id`; optional `X-User-ID`; `UpdateProgressRequest` | 200 `ProgressResponse` | 403, 404, 422 |
| `DELETE /api/v1/sessions/{session_id}` | Path: `session_id`; optional `X-User-ID` | 204, empty body | 403, 422; missing session is idempotently 204 |
| `POST /api/v1/sessions/{session_id}/safe-mode` | Path: `session_id`; optional `X-User-ID`; no body | 200 `SessionResponse` | 403, 404, 422 |
| `POST /api/v1/sessions/{session_id}/spoiler-confirmation` | Path: `session_id`; optional `X-User-ID`; `SpoilerConfirmationRequest` | 200 `SpoilerConfirmationResponse` | 403 for invalid/expired nonce, 404, 422 |

`CreateSessionRequest` requires `title_id`; optional fields are `locale` (default `en`), `position_seconds` (integer, default 0), and `source` (default `manual_slider`). Client-supplied `verified_integration` and `partner_sync` sources are normalized to `manual_slider`; partner authentication is not implemented. The initial position is capped at the title duration.

`SessionResponse` contains `session_id`, `user_id`, a compact `title` (`id`, `display_title`, optional `year`), `current_position_seconds`, `progress_source`, `spoiler_mode`, `created_at`, and `updated_at`.

`UpdateProgressRequest` requires non-negative integer `position_seconds`; it optionally accepts `source` and non-negative `duration_seconds`. The server validates against the title's stored duration; the request's `duration_seconds` is not used. `ProgressResponse` contains `session_id`, `current_position_seconds`, `progress_source`, `is_verified`, `spoiler_mode`, and `updated_at`.

Progress source enum values are `verified_integration`, `manual`, `manual_slider`, `voice_cue`, `partner_sync`, and `unknown`. Client-supplied `verified_integration` and `partner_sync` values are normalized to `manual_slider`, and progress updates from the client always return `is_verified: false`. The API has no partner-authenticated progress path; partner synchronization must not be treated as verified until one is implemented.

`SpoilerConfirmationRequest` requires `confirmation_nonce` (minimum 8 characters). The nonce is returned by a question response with outcome `spoiler_confirmation_required`; confirmation consumes it once. `SpoilerConfirmationResponse` contains `session_id`, `spoiler_mode`, `status` (`confirmed`), and `updated_at`.

## Questions

| Method and path | Parameters / body | Success | Common errors |
|---|---|---:|---|
| `POST /api/v1/sessions/{session_id}/questions` | Path: `session_id`; optional `X-User-ID`; `QuestionRequest` | 200 `QuestionResponse` | 403, 404, 422, 429, 503, 504 |

`QuestionRequest` requires `question` (2-500 characters). Optional fields are `client_request_id` (max 128 characters) and `locale` (default `en`). The request intentionally has no spoiler-mode override field.

`QuestionResponse` contains `question_id`, `session_id`, `outcome`, optional `answer`, `citations`, optional `clarification_prompt`, optional `confirmation_nonce`, `policy_state`, and `created_at`. A citation contains `chunk_id`, `start_time_seconds`, `end_time_seconds`, `text`, and `relevance_score`.

Possible outcomes are `answered`, `needs_clarification`, `insufficient_evidence`, `spoiler_confirmation_required`, and `unsupported_title`. For `spoiler_confirmation_required`, post the returned nonce to the session's spoiler-confirmation route, then submit the question again if the viewer chooses to proceed. Safe mode is the default. `POST .../safe-mode` returns the session to safe mode.

Example question request:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/sessions/SESSION_ID/questions" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: local-viewer" \
  -d '{"question":"Why did Cooper leave Earth?"}'
```

## Subtitle Translation and Character Cards

These viewer routes require the session's `X-User-ID` and use the same story boundary as Q&A: safe mode is limited to the server-stored current playback position, while full-title access requires the existing single-use spoiler confirmation. There is no separate “selected point” spoiler mode because the current client only reports manually chosen progress; a user-selected boundary would currently duplicate that control and would not provide independently verified playback state.

SRT/WebVTT ingestion preserves individual cues as well as the existing larger retrieval chunks. Translation accepts only a cue ID from the active authorized index; it never accepts arbitrary viewer-provided dialogue.

| Method and path | Parameters / body | Success | Common errors |
|---|---|---:|---|
| `GET /api/v1/sessions/{session_id}/subtitle-lines` | Path: `session_id`; query: `query` (2-120 characters); optional `X-User-ID` | 200 `SubtitleLineSearchResponse` | 403, 404, 422 |
| `POST /api/v1/sessions/{session_id}/translations` | Path: `session_id`; optional `X-User-ID`; `TranslationRequest` | 200 `TranslationResponse` | 403, 404, 422, 503, 504 |
| `GET /api/v1/sessions/{session_id}/characters` | Path: `session_id`; optional `X-User-ID` | 200 `CharacterCardsResponse` | 403, 404, 422 |
| `POST /api/v1/admin/titles/{title_id}/character-facts` | Path: `title_id`; `X-Admin-Token`; `CharacterFactCreateRequest` | 201 `CharacterFactResponse` | 401, 403, 404, 422, 503 |

`SubtitleLineSearchResponse.items` contains cue IDs, start/end timestamps, and cue text from the active index, already filtered by the spoiler boundary. `TranslationRequest` requires `cue_id` and `target_locale` (`en`, `es`, `fr`, `hi`, or `ja`); `explain_context` defaults to `true`. The response contains the original cue, translation when available, optional contextual explanation, and a timestamped cue citation. If the provider cannot translate reliably, the endpoint returns `outcome: insufficient_evidence`, no translation, and an explanatory message. The local deterministic mock supports identity translation when source and target locales match and explicitly abstains otherwise; configure the server-side Gemini provider for model translation.

`CharacterCardsResponse.items` contains only verified, curated facts whose first-known timestamp is at or before the active spoiler boundary. Cards are grouped by character name and include optional relationship text. Facts are entered by an authorized operator against the currently active subtitle version; publishing a replacement index does not carry old-version facts forward automatically. For film titles, the reveal boundary is a timestamp; episode-aware bounds are not implemented.

Example operator request for a curated character fact:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/admin/titles/TITLE_ID/character-facts" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: $ADMIN_API_TOKEN" \
  -d '{"character_name":"Cooper","fact":"Cooper is Murph’s father.","relationship":"Father of Murph.","first_known_at_seconds":20}'
```

## Content Administration

These routes mutate the catalog, content index, and curated metadata. Admin requests require the configured shared token. This does not provide individual operator identity or role-based access control; protect the token and keep admin routes on a trusted network.

| Method and path | Parameters / body | Success | Common errors |
|---|---|---:|---|
| `POST /api/v1/admin/titles/{title_id}/ingest` | Path: `title_id`; required `X-Admin-Token`; `IngestionRequest` | 201 `IngestionResponse` | 401, 403, 404, 413, 422, 503 |
| `POST /api/v1/admin/titles/{title_id}/publish-version/{version_id}` | Path: `title_id`, `version_id`; required `X-Admin-Token`; no body | 200 JSON object | 401, 403, 404, 422, 503 |
| `POST /api/v1/admin/titles/{title_id}/unpublish` | Path: `title_id`; required `X-Admin-Token`; no body | 200 JSON object | 401, 403, 404, 422, 503 |
| `POST /api/v1/admin/titles/{title_id}/character-facts` | Path: `title_id`; `X-Admin-Token`; `CharacterFactCreateRequest` | 201 `CharacterFactResponse` | 401, 403, 404, 422, 503 |

`IngestionRequest` requires `raw_content` (at least 10 characters); it optionally accepts `source_type` (default `srt`) and `auto_publish` (default `false`). The supported parser formats are SRT and WebVTT. Only ingest content you are authorized to process and store.

`IngestionResponse` contains `movie_id`, `content_version_id`, `version_number`, `source_checksum`, `cue_count`, `chunk_count`, `duration_seconds`, `is_active`, `processing_status`, and `elapsed_milliseconds`. Publishing returns `movie_id`, `active_version_id`, `version_number`, and `status`. Unpublishing returns `movie_id`, `status`, and `message`.

## Error Responses

Application and validation errors use this envelope:

```json
{
  "code": "NOT_FOUND",
  "message": "A safe human-readable description",
  "request_id": "req_example",
  "details": null
}
```

Known application status/code pairs include 400 `BAD_REQUEST`, 401 `UNAUTHENTICATED`, 403 `FORBIDDEN`, 404 `NOT_FOUND`, 409 `STATE_CONFLICT`, 413 `PAYLOAD_TOO_LARGE`, 422 `VALIDATION_ERROR`, 429 `RATE_LIMIT_EXCEEDED`, 503 `ADMIN_AUTH_NOT_CONFIGURED` or `PROVIDER_UNAVAILABLE`, and 504 `GATEWAY_TIMEOUT`. Unexpected exceptions return 500 `INTERNAL_SERVER_ERROR`. Per-operation application-error responses are not fully declared in the generated OpenAPI schema; use this section and the implementation for those cases.

## Keeping the Contract in Sync

After changing a route, schema, or response, regenerate the checked-in schema and verify it is current:

```bash
python ops/scripts/export_openapi.py
python ops/scripts/export_openapi.py --check
```

The API tests are in `tests/test_api_v1_endpoints.py`; the human-readable product contract is in `Rewind_Complete_Project_Documentation_Package/requirements/04_API_CONTRACT.md`.