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

| **LIM-03** | Viewer Identity | `X-User-ID` is accepted as the viewer identity and falls back to a fixed local viewer ID; it is not authenticated identity. | Keep local/demo use isolated. Implement and verify a production identity provider and authorization policy before exposing the API to untrusted clients. |
| **LIM-04** | Admin Authorization | The current admin dependency is a development placeholder and does not establish a secure operator identity or role boundary. | Do not expose admin routes to untrusted networks. Replace the placeholder with authenticated, role-based authorization and add adversarial tests before beta/production exposure. |
| **LIM-05** | Readiness Probe | `/health/ready` currently returns static component statuses rather than checking database connectivity or other runtime dependencies. | Do not use it as a production readiness gate until dependency probes are implemented and tested. |
| **LIM-06** | Static Quality Checks | Workspace baseline on 2026-10-18: `ruff check .` reported 130 findings; `mypy services` reported 117 errors across 12 files. | Triage findings, resolve them in focused changes, and establish clean lint/type-check release gates. Re-run with recorded tool versions because counts may change. |
| **LIM-07** | Progress Provenance | The progress update handler normalizes `verified_integration` but treats a client-supplied `partner_sync` source as verified. | Do not trust caller-supplied `partner_sync` or `is_verified` until partner authentication and server-side source validation are implemented and tested. |
| **LIM-08** | OpenAPI Snapshot | The checked-in schema can drift from runtime routes and response descriptions. | Run `python ops/scripts/export_openapi.py` after API changes and `python ops/scripts/export_openapi.py --check` in verification. |

## Release Evidence Caveat

The release report dated 2026-10-17 records a controlled-beta readiness assessment. The implementation dashboard separately marks E11 production launch as `NOT_STARTED`, and this repository has not established production-grade viewer/admin authentication or physical-device validation. Treat beta readiness as a historical assessment, not proof of production approval or platform certification. Use the current test run and target-environment evidence when making release decisions.
