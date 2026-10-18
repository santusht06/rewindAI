# Rewind Project Checklist

Living project checklist for implemented features, verified changes, and remaining work. The status dashboard and requirements documents remain the detailed source of truth; this file is a concise working index. Check an item only after recording current evidence.

**Last reviewed:** 2026-10-18

## Recent Changes

- [x] Fix editable installation by limiting setuptools discovery to `services`.
- [x] Replace the obsolete `requirements.txt` install instructions with the `pyproject.toml` workflow.
- [x] Verify editable install, test suite, and API startup from the project virtual environment.

## Implemented Features

### Backend and API

- [x] FastAPI application, configuration, structured logging, request IDs, and safe error responses.
- [x] Liveness, readiness, and operational metrics endpoints.
- [x] Versioned API for title catalog, sessions/progress, questions, spoiler confirmation, and admin actions.
- [x] SQLAlchemy persistence, Alembic migrations, repositories, and relational integrity rules.
- [x] SRT/WebVTT parsing, timestamp validation, subtitle chunking, embeddings, staged indexing, and publication.
- [x] Idempotent ingestion, title unpublishing, and content-version deactivation.
- [x] Hybrid retrieval and grounded answers with citation validation and safe abstention.
- [x] Server-side temporal spoiler filtering, single-use confirmation nonces, session ownership checks, and prompt-injection defenses.
- [x] Rate limiting, privacy-aware telemetry, and SQLite backup/restore utilities.

### TV Client and Demo

- [x] Static TV client integrated at `/tv/` with catalog, title/progress, question/answer, clarification, spoiler modal, settings, and admin screens.
- [x] D-pad/spatial focus navigation and desktop remote simulation.
- [x] Fire TV/Vega-oriented manifest/configuration and app packaging utility.
- [x] Demo script and automated demo-flow coverage.

### Engineering Evidence

- [x] Automated API, persistence, ingestion, RAG/spoiler, operational, TV-client, and demo tests exist.
- [x] Project requirements and implementation status are documented under `docs/` and `Rewind_Complete_Project_Documentation_Package/`.

## Work To Do

### Setup and Release

- [ ] Verify a fresh editable install using `pip install -e ".[dev]"` and record the result here.
- [ ] Keep the test suite passing and triage static-check debt: baseline `ruff check .` 130 findings and `mypy services` 117 errors across 12 files (2026-10-18); establish clean gates.
- [ ] Complete E11 production-launch sign-off; the status dashboard currently marks E11 `NOT_STARTED`.
- [ ] Verify deployment, migration, backup/restore, and rollback procedures in the intended beta/production environment.
- [ ] Replace the fallback viewer identity and development admin check with production-grade authentication/authorization; test unauthorized access paths.
- [ ] Make readiness probes verify required dependencies such as database connectivity.
- [ ] Validate progress provenance server-side; do not mark caller-supplied `partner_sync` as verified without partner authentication.
- [ ] Keep `docs/api/openapi.json` synchronized with the runtime schema using `ops/scripts/export_openapi.py --check`.

### Product and Platform Decisions

- [ ] Select and configure the production LLM and embedding providers; Gemini is wired, while the configured OpenAI key is not currently connected to a provider implementation.
- [ ] Confirm content licensing and rights for every title/transcript used beyond authorized demo fixtures.
- [ ] Run load testing and verify the documented Q&A latency targets (p50 < 1.5s, p95 < 3.0s).
- [ ] Verify packaging, navigation, backend reachability, and lifecycle behavior on the selected Fire OS/Vega OS device or emulator; label physical-device testing separately.
- [ ] Decide hosting, production persistence, authentication, data retention, supported catalog, budget, and service-level targets.
- [ ] Keep playback progress manual unless an authorized and technically verified third-party playback integration is available.

### Optional Capability Follow-ups

- [ ] Evaluate direct TV voice input; current documented fallback is remote-friendly presets and text entry.
- [ ] Evaluate additional subtitle formats only if required by the authorized content catalog; current parser supports SRT and WebVTT.

## Open Constraints

- The requirements explicitly do not assume access to third-party streaming playback position, protected video/audio, or subtitles.
- Real provider credentials and authorized production content are environment/product decisions, not bundled defaults.
- The release-readiness report documents a controlled-beta target, but production launch remains a separate gate.

## Change Log

| Date | Change | Verification |
|---|---|---|
| 2026-10-18 | Added explicit setuptools build backend and restricted package discovery to `services`; updated README install/run instructions; created this checklist. | `pip install -e '.[dev]'` succeeded; `pytest -q` passed (55 tests); Uvicorn started and `/health/live` returned `status: alive`. |
| 2026-10-18 | Expanded README, added local setup/API guide, documented identity/admin/readiness limitations, and clarified beta/production and platform/spoiler evidence. | Documentation review and `git diff --check`; setup and migration commands were verified in the local environment. |
| 2026-10-18 | Recorded the current lint and type-check baseline as open engineering work. | `ruff check .`: 130 findings; `mypy services`: 117 errors across 12 files. |
| 2026-10-18 | Added a route-by-route API reference and OpenAPI export/check utility; refreshed the checked-in schema and documented the progress-provenance caveat. | `python ops/scripts/export_openapi.py --check` passed; `pytest -q tests/test_api_v1_endpoints.py` passed (6 tests); `ruff check ops/scripts/export_openapi.py` passed. |
| 2026-10-18 | Replaced permissive admin placeholder with a configured shared token, minimum-length enforcement, and constant-time comparison; admin integration tests cover unconfigured/short token, missing, invalid, and valid credentials. | `pytest -q` passed (57 tests); affected suites passed; TV-client tests, JavaScript syntax, import-order check, and `git diff --check` passed. |