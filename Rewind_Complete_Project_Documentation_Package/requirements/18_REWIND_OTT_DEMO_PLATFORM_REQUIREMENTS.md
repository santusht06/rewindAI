# Rewind OTT Demonstration Platform — Product & Functional Requirements

**Document ID:** REWIND-REQ-018 | **Status:** Proposed baseline

## 1. Product definition
Rewind is an AI viewing assistant demonstrated through a small OTT-style host application. The host lets an administrator upload a movie, processes and serves it, and provides a player in which viewers ask story questions using text or voice. This demo host proves the assistant end to end; it does not change the long-term goal: assist viewers alongside existing streaming services, not replace Netflix, Prime Video, Disney+, or other providers.

## 2. Goals
1. Upload a demonstration movie to object storage.
2. Inspect and package video for playback.
3. Extract existing subtitles or generate timestamped transcript where needed.
4. Create contextual text chunks and embeddings for retrieval.
5. Play the movie and pass current playback position to Rewind.
6. Answer natural-language questions with supporting timestamps.
7. Support replaceable STT and TTS integrations.
8. Enforce spoiler boundaries server-side.
9. Make processing states, errors, and capability limitations visible.

## 3. Non-goals
- Netflix-scale global delivery, petabyte storage, or millions of concurrent viewers.
- Billing, subscriptions, advertising, large-scale recommendations, or a commercial catalog.
- DRM circumvention, protected-screen scraping, or undocumented APIs.
- Claiming the demo proves overlays over Netflix/Prime Video.
- Claiming subtitle RAG can reliably answer visual-only questions.
- Requiring Kafka, Cassandra, Kubernetes, or a large microservice fleet for the first demo.

## 4. User journeys
**Admin:** create movie metadata → upload permitted video → start processing → inspect status/errors → publish only after playback and AI index are ready.

**Viewer:** browse catalog → play movie → pause/invoke assistant → ask by text or voice → see answer and timestamps → optionally hear answer → dismiss and resume at the previous position.

## 5. Functional requirements
### FR-01 Catalog
List published movies with title, duration, language, poster/placeholder, and clear loading, empty, and error states.

### FR-02 Upload and assets
Use backend-authorized uploads. Store binaries in object storage, not PostgreSQL. Persist provider/object key, size, checksum where practical, duration, media type, and status. Use short-lived signed URLs or provider SDKs. Validate actual media metadata and treat uploads as untrusted input.

### FR-03 Media processing
Use FFprobe to inspect streams and FFmpeg or a managed service to package playback assets. HLS is the preferred initial format only if supported by the chosen player/target. Validate manifest and segments before declaring playback ready. Version outputs and hide provider-specific details behind an adapter.

### FR-04 Subtitle/transcript ingestion
Prefer usable embedded subtitles, then supplied SRT/VTT, then STT from extracted audio. Normalize segments to text plus start/end milliseconds and preserve language and provenance (`embedded_subtitle`, `uploaded_subtitle`, `generated_transcript`). STT is not visual scene understanding.

### FR-05 Chunking and indexing
Chunk around dialogue boundaries/contextual windows. Store movie ID, transcript version, time range, language, source, stable chunk ID, text, and embedding. Use PostgreSQL + pgvector plus full-text search. Make retries idempotent and never mix transcript versions.

### FR-06 Playback context
Each assistant request carries movie ID, current playback position, spoiler mode, and conversation/session ID. Validate ownership and bounds. Treat reported position as potentially stale. Never assume other OTT providers expose position or subtitles.

### FR-07 Q&A
Scope retrieval to the selected movie; enforce spoiler policy before sending evidence to the LLM. Use hybrid retrieval and optional reranking. Send bounded evidence, return answer plus timestamps/chunk references, and abstain or clarify when evidence is insufficient. Retrieved transcript content is untrusted and cannot override agent instructions.

### FR-08 Spoilers
Support `CURRENT_POSITION_ONLY` and `ALLOW_FULL_MOVIE`. In current-position mode, exclude future chunks before generation. Apply the same boundary to vector search, keyword search, cached answers, summaries, and conversation memory. Include boundary and mode in cache keys. Fail closed if a safe boundary cannot be established.

### FR-09 Voice
Use push-to-talk initially. STT converts audio to text; display the recognized question and allow retry/cancel; reuse the same Q&A pipeline; TTS speaks the answer when enabled. Handle permissions, timeout, cancellation, provider failure, and text fallback. Keep provider secrets on the backend.

### FR-10 Observability
Expose job stage, attempts, timestamps, last safe error, and retryability. Log IDs, not secrets or raw audio by default. Add health/readiness checks for API, database, queue, storage, and configured providers.

### FR-11 Security/privacy
Authorize all admin operations; enforce upload and processing limits; use least-privilege storage permissions and short-lived URLs; rate-limit expensive AI endpoints; keep secrets out of frontend bundles; define retention/deletion for media, transcripts, audio, and questions.

## 6. Initial entities
`Movie`, `MediaAsset`, `ProcessingJob`, `TranscriptSegment`, `KnowledgeChunk`, `PlaybackSession`, `Conversation`, `ConversationMessage`, and `ProviderCapability`. Store references and metadata rather than media binaries in relational tables.

## 7. Acceptance criteria
1. Admin uploads an authorized test movie and sees status.
2. Playback assets validate and play in the demo client.
3. Timestamped transcript and searchable chunks are created.
4. Text questions return evidence-backed answers and timestamps.
5. Current-position mode does not expose future plot evidence.
6. Voice question works when STT is configured; TTS speaks when enabled.
7. Provider failures are visible and recoverable.
8. Tests cover movie isolation, spoiler filtering, idempotency, retries, and provider failure.
9. Documentation distinguishes real integrations from mocks/manual context/unverified platform assumptions.

## 8. Mandatory diagrams
Read before implementation:
- `../system_design_diagrams/18_REWIND_OTT_DEMO_END_TO_END_ARCHITECTURE.mmd`
- `../system_design_diagrams/19_REWIND_MEDIA_INGESTION_AND_INDEXING.mmd`
- `../system_design_diagrams/20_REWIND_AI_QUERY_AND_VOICE_SEQUENCE.mmd`
- `../system_design_diagrams/21_REWIND_SPOILER_BOUNDARY_AND_RETRIEVAL.mmd`

These documents extend the existing requirements. `17_REWIND_CROSS_APP_ASSISTANT_PRODUCT_REQUIREMENT.md` remains authoritative for the cross-app product goal and platform limitations.
