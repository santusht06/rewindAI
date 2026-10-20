# Known Issues and Defect Tracking — Rewind

**Version:** 1.0  
**Project:** Rewind — Fire TV AI Story Companion  
**Status:** Active  

This document logs known limitations, open decisions, environmental constraints, and follow-up items.

---

## Open Product Decisions

| ID | Topic | Current Baseline / Safe Default | Status | Impact / Notes |
| :--- | :--- | :--- | :--- | :--- |
| **OPEN-01** | Third-Party Streaming Integration | Safe default: Manual playback position slider / progress entry. Do not assume third-party streaming apps (Prime Video, Netflix) expose live playback hooks. | DOCUMENTED | Automatic progress sync requires verified platform API access. |
| **OPEN-02** | External LLM Provider Selection | Safe default: Modular provider adapter supporting Google Gemini, OpenAI, and a Mock Provider for zero-cost deterministic tests. | DOCUMENTED | Production deployment requires setting `GEMINI_API_KEY` or `OPENAI_API_KEY`. |
| **OPEN-03** | Subtitle Licensing & Catalog Rights | Safe default: Only authorized or public domain / creative commons sample transcripts are processed. | DOCUMENTED | Commercial release requires verified content rights documentation. |
| **OPEN-04** | Target Latency SLO | Initial engineering baseline: p50 < 1.5s, p95 < 3.0s for grounded Q&A. | PENDING LOAD TEST | To be verified under Phase 7/8 performance benchmarks. |

---

## Active Limitations

| ID | Component | Limitation Summary | Mitigation / Workaround |
| :--- | :--- | :--- | :--- |
| **LIM-01** | Subtitle Formats | Initial parser supports SRT and WebVTT (.srt, .vtt). Binary subtitle formats (.sub, bitmap PGS) are not supported. | Plain-text subtitle formats cover >95% of standard web/streaming assets. |
| **LIM-02** | TV Voice Input | Direct microphone voice dictation on TV requires Alexa Voice Service or Web Speech API integration. | Provide onscreen remote-navigable quick question presets and virtual keyboard as the primary accessible fallback. |

| **LIM-03** | Viewer Identity | `X-User-ID` and a fixed fallback are supported only outside production. Production viewer routes fail closed with HTTP 503; an identity provider and verified claims are not yet implemented. | Select the identity provider/protocol, then implement and test server-side token validation and viewer ownership authorization before enabling production access. |
| **LIM-04** | Admin Authorization | The shared `ADMIN_API_TOKEN` (minimum 32 characters) is local/demo-only. Admin routes fail closed in production; individual operator identity and roles are not implemented. | Select operator identity, role claims, and secret-management policy; then implement and test production authorization and rotation. |
| **LIM-05** | Readiness Probe | `/health/ready` checks database connectivity with a bounded `SELECT 1`; other external dependencies are not checked. | Verify the database probe in the intended deployment environment and add probes for any additional dependencies required by the chosen production architecture. |
| **LIM-06** | Static Quality Checks | Current Ruff and mypy checks pass locally; `.github/workflows/quality.yml` is configured to enforce them. Historic 2026-10-18 counts are stale. | Preserve the CI gates and record tool versions when updating the supported Python baseline. |
| **LIM-07** | Progress Provenance | No partner-authenticated synchronization endpoint is implemented. Client-supplied `verified_integration` and `partner_sync` sources are normalized to `manual_slider`; client updates always report `is_verified: false`. | Keep partner progress unverified until partner authentication and server-side source validation are implemented. Regression-tested in `test_api_v1_endpoints.py`. |
| **LIM-08** | OpenAPI Snapshot | The checked-in schema can drift from runtime routes and response descriptions. | Run `python ops/scripts/export_openapi.py` after API changes and `python ops/scripts/export_openapi.py --check` in verification. |

## Release Evidence Caveat

The release report dated 2026-10-17 records a controlled-beta readiness assessment. The implementation dashboard separately marks E11 production launch as `NOT_STARTED`; viewer identity and admin-role decisions, target deployment environment, production authentication, and physical-device validation remain open. Production routes fail closed until auth is selected and implemented. Treat the beta assessment as historical, not proof of current beta readiness, production approval, or platform certification. Use current test and target-environment evidence for release decisions.
