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
