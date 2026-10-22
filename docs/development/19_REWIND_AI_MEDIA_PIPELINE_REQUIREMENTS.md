# Rewind AI Media Pipeline — Technical Requirements

**Document ID:** REWIND-REQ-019 | **Status:** Proposed baseline

## 1. Processing model
Media processing is asynchronous. The API creates a durable job and returns a job ID; workers process stages and persist state. Do not make upload requests wait for a full transcode/index. Recommended initial components: FastAPI, PostgreSQL, FFmpeg/FFprobe, MinIO or Cloudinary behind `MediaStorageProvider`, and replaceable STT/embedding/LLM/TTS adapters. Add Redis/Celery when task queue needs justify it; a simple worker is acceptable for the first slice.

## 2. Job stages
Suggested path: `UPLOADED → INSPECTING → MEDIA_PROCESSING → TRANSCRIPT_EXTRACTING → TRANSCRIPT_NORMALIZING → CHUNKING → EMBEDDING → INDEXING → READY`. Playback validation and AI indexing may proceed in parallel after inspection. `READY` requires both playback and AI-readiness checks. Failures persist stage-specific error code, safe message, attempts, and retryability. Only backend logic can change job status.

## 3. Media processing
- Inspect actual streams with FFprobe; never trust extension alone.
- Validate duration, size, dimensions, codecs, and supported streams.
- Generate HLS or another format proven compatible with the target player.
- Store versioned output prefixes; verify manifest references and segment availability.
- Keep source assets immutable; safely clean incomplete temporary outputs.
- Avoid unnecessary renditions for a demo; choose based on target-device compatibility and compute.
- Process only media the operator is authorized to use.

## 4. Transcript rules
Source preference: usable embedded subtitle → supplied SRT/VTT → configured STT from extracted audio. Preserve timestamp provenance, source type, language, provider/model metadata, and transcript version. Normalize stable segment ID, movie ID, start/end milliseconds, text, language, source type, and optional speaker/confidence. Reject invalid intervals. Do not claim speaker identity without diarization evidence.

## 5. Chunking and indexing
Create contextual windows from adjacent dialogue segments, respect embedding input limits, and retain exact time ranges and source segment IDs. Record embedding model/version. Use deterministic IDs/upserts. Prevent stale transcript versions from mixing with current vectors. Index text with PostgreSQL full-text search and vectors with pgvector. Filter by movie and spoiler boundary before generation. Reranking is optional until retrieval evaluation justifies it.

## 6. Runtime query contract
Request: `movie_id`, `question` or audio reference, `playback_position_ms`, `spoiler_mode`, optional `conversation_id` and `locale`.

Response: `answer`, optional `recognized_question`, `evidence[]` (chunk ID, start/end ms, short quote), optional spoken-audio reference, `insufficient_evidence`, and safe error/trace ID. Do not return the full transcript by default; bound LLM context.

## 7. Security
Treat subtitles as untrusted content and block transcript-based prompt injection. Limit upload size, processing time, transcript size, concurrency, and provider spend. Authorize movie/conversation access. Keep API keys server-side. Use time-limited private media URLs. Avoid logging secrets, authorization headers, raw audio, or unnecessary personal data.

## 8. Tests
Unit: timestamp normalization, chunk boundaries, transcript version isolation, spoiler filtering, idempotency, provider error mapping. Integration: storage, FFprobe/FFmpeg worker, PostgreSQL/pgvector, hybrid retrieval, fake provider contracts. E2E: upload→ready→play→ask→grounded answer; no-subtitle STT path; spoiler restriction; worker retry; provider outage.

## 9. Diagram references
Study `18_REWIND_OTT_DEMO_END_TO_END_ARCHITECTURE.mmd`, `19_REWIND_MEDIA_INGESTION_AND_INDEXING.mmd`, and `21_REWIND_SPOILER_BOUNDARY_AND_RETRIEVAL.mmd` under `system_design_diagrams/` before implementation.
