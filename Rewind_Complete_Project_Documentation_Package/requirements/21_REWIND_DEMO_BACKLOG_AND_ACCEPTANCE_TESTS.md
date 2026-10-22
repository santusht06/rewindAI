# Rewind OTT Demo — Phased Backlog & Acceptance Tests

**Document ID:** REWIND-REQ-021

## Phase 0 — Feasibility
- [ ] Read requirements and all diagram references.
- [ ] Record target device and OS/runtime.
- [ ] Verify build/launch, remote navigation, microphone, and player support.
- [ ] Choose storage provider and record decision.
- [ ] Record risks and update status tracker.
**Exit:** no platform assumption is silently treated as verified.

## Phase 1 — Backend foundation
- [ ] Configure FastAPI, settings, migrations, PostgreSQL.
- [ ] Add models for movie, asset, job, transcript segment, chunk, playback session, conversation.
- [ ] Authorize admin operations.
- [ ] Add health checks, structured logs, request IDs, provider interfaces.
**Exit:** migrations and unit/integration tests pass.

## Phase 2 — Upload and playback
- [ ] Implement authorized upload to MinIO or Cloudinary.
- [ ] Persist asset metadata and validate source.
- [ ] Run FFprobe and package a compatible playback format.
- [ ] Validate manifest/segments.
- [ ] Implement catalog/playback APIs and playback position reporting.
**Exit:** a permitted test movie plays end to end.

## Phase 3 — Transcript and indexing
- [ ] Extract embedded subtitle or ingest SRT/VTT.
- [ ] Add STT fallback.
- [ ] Normalize timestamped transcript versions.
- [ ] Chunk, embed, store vectors, enable full-text search.
- [ ] Add idempotency, retries, and readiness validation.
**Exit:** test queries retrieve relevant chunks with timestamps.

## Phase 4 — Text Q&A and spoiler safety
- [ ] Implement hybrid retrieval scoped by movie.
- [ ] Filter spoiler boundary before LLM context construction.
- [ ] Generate bounded evidence-grounded answers.
- [ ] Add insufficient-evidence behavior.
- [ ] Test hostile subtitle prompt injection, cross-movie isolation, and cache policy.
**Exit:** answers are grounded and future evidence is excluded in current-position mode.

## Phase 5 — Voice
- [ ] Implement push-to-talk and STT adapter.
- [ ] Display recognized text with retry/cancel.
- [ ] Reuse the same Q&A path.
- [ ] Add TTS, stop-speaking, provider failure, and text fallback.
- [ ] Verify client contains no provider secrets.
**Exit:** voice question → transcript → grounded answer → spoken response works on target.

## Phase 6 — UX and device verification
- [ ] Build catalog/player/assistant/listening/thinking/speaking/error states.
- [ ] Verify D-pad focus and playback pause/resume.
- [ ] Test slow network, long title, empty transcript, provider timeout, unavailable mic.
- [ ] Record target device/OS and update diagrams to match real behavior.
**Exit:** repeatable demo with documented limitations.

## Acceptance test matrix
| ID | Scenario | Expected result |
|---|---|---|
| AT-01 | Valid authorized upload | Asset/job created |
| AT-02 | Corrupt/unsupported video | Safe failure; never READY |
| AT-03 | Embedded subtitles | Extracted with timestamps |
| AT-04 | No subtitles | STT path or clear failure |
| AT-05 | Retry job | No duplicate/mixed chunks |
| AT-06 | Movie ready | Player starts/seeks correctly |
| AT-07 | Supported story question | Answer includes evidence timestamps |
| AT-08 | No supporting evidence | Abstain or clarify |
| AT-09 | Future plot question in current-position mode | Future evidence excluded before LLM |
| AT-10 | Instruction-like subtitle text | Cannot change assistant policy |
| AT-11 | STT available | Recognized question is shown and answered |
| AT-12 | TTS fails | Text answer remains usable |
| AT-13 | Cross-movie chunk access | No data leakage |
| AT-14 | Unsupported platform capability | Marked partial/unavailable; no fake success |
| AT-15 | Worker restarts | Job recoverable and retryable |

For every phase, record environment/date, actual commands or manual steps, test results, redacted logs, useful screenshots, limitations, and commit hash. Never mark work complete based only on generated code.
