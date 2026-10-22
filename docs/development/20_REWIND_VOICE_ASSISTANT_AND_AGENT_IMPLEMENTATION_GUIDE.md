# Rewind Voice Assistant & Coding-Agent Implementation Guide

**Document ID:** REWIND-REQ-020 | **Audience:** Coding agents and engineers

## 1. Mandatory agent instructions
Before coding, the agent MUST:
1. Read root `README.md`, the existing master agent prompt, and Git/Agile rules.
2. Read requirements 17, 18, 19, 20, and 21.
3. Open and study every diagram listed in Section 8.
4. Compare diagrams with the actual repository and record discrepancies.
5. Produce a Phase 0 feasibility report and task/status plan before implementation.
6. Record target runtime/device and mark unknown capabilities `NOT_TESTED`; Android compatibility alone does not prove Fire TV/Vega OS support.
7. Implement one vertical slice at a time and attach test evidence.

Diagrams are required explanatory references for component boundaries and data flow. Requirement 17 controls cross-app product constraints if any diagram conflicts. If implementation proves a diagram wrong, update it with the reason in the same change.

## 2. Product boundary and adapters
The OTT player is a demo host, not the enduring product. Keep provider-specific behavior behind interfaces: `MediaStorageProvider`, `MediaProcessingProvider`, `SubtitleProvider`, `SpeechToTextProvider`, `EmbeddingProvider`, `RetrievalProvider`, `LLMProvider`, `TextToSpeechProvider`, `PlaybackContextProvider`, and `AssistantPresentationAdapter`. Mocks are permitted for tests/UI development but must be labelled and never presented as verified integration.

## 3. Recommended vertical slice
1. Create movie record.
2. Upload a short authorized test video.
3. Inspect and package playable output.
4. Extract subtitles or ingest SRT.
5. Normalize and store timestamped segments.
6. Create chunks and embeddings.
7. Query by text and return evidence with timestamps.
8. Pass real current playback position.
9. Enforce server-side spoiler filtering.
10. Add STT/TTS after text Q&A is stable.
11. Test remote navigation and platform assumptions on actual device.

## 4. Voice behavior
Initial release uses push-to-talk: activate microphone → listening state → STT → show recognized text → allow retry/cancel → reuse Q&A pipeline → display answer/evidence → optionally play TTS → stop speech/resume playback. Provide text fallback. Do not claim full-duplex low-latency conversation until implemented and tested.

## 5. Suggested API groups
- `/admin/movies`, `/admin/uploads`, `/admin/jobs/{job_id}`
- `/catalog/movies`
- `/playback/sessions`
- `/assistant/query`, optional `/assistant/voice-query`
- `/assistant/conversations/{id}`
- `/health/live`, `/health/ready`

Adapt route names to the repository but document and test contracts.

## 6. UI expectations
Use React Native + Expo only after target runtime/dependency compatibility is verified. Standard web shadcn/ui components do not run directly in React Native; consider React Native Reusables and NativeWind if compatible. Build visible loading/listening/thinking/speaking/error/retry states and clear D-pad focus. Do not assume DOM, hover, or touch. Keep assistant UI independent of the playback surface.

## 7. Definition of done
A task is complete only when acceptance criteria pass, relevant tests run, failure/loading states are covered, docs/diagrams match implementation, status tracker is updated, and changes are committed locally according to project rules. Never claim unrun tests passed. Never push/publish remotely without explicit user authorization. Avoid destructive commands without permission.

## 8. Mandatory diagram references — study before implementation
1. `system_design_diagrams/18_REWIND_OTT_DEMO_END_TO_END_ARCHITECTURE.mmd` — overall client/API/media/AI topology.
2. `system_design_diagrams/19_REWIND_MEDIA_INGESTION_AND_INDEXING.mmd` — asynchronous media workflow and readiness gates.
3. `system_design_diagrams/20_REWIND_AI_QUERY_AND_VOICE_SEQUENCE.mmd` — runtime STT, retrieval, LLM, evidence, TTS sequence.
4. `system_design_diagrams/21_REWIND_SPOILER_BOUNDARY_AND_RETRIEVAL.mmd` — server-side spoiler boundary.
Also inspect existing system design diagrams, especially the cross-app capability verification diagram and overview. Preserve the distinction between the OTT demo player and cross-app assistant goal.

## 9. Phase 0 feasibility gate
Verify app build/launch, remote navigation, player format, playback position, microphone capture/permissions, assistant presentation, and (if relevant) official cross-app APIs. Record status `VERIFIED`, `PARTIAL`, `UNAVAILABLE`, or `NOT_TESTED`, plus device/OS, steps, evidence, and date. Do not use hidden APIs, unauthorized screen scraping, or DRM circumvention.
