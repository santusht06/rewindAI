# 01 — Product Requirements

## 1. Product vision
Rewind is a TV-first AI story companion that helps a viewer understand characters, relationships, plot details, clues and previously established events in a supported title without requiring the viewer to leave the viewing experience. It should feel like a contextual companion, not a generic chatbot.

## 2. Problem statement
Viewers forget details, miss connections, or want clarification while watching a long-form story. General-purpose chat may hallucinate, reveal future plot details, or lack reliable scene-level context. Rewind must ground answers in authorized, timestamped content and enforce spoiler policy independently of the LLM.

## 3. Goals
- G1: Let a viewer ask a natural-language question using a TV-friendly interaction.
- G2: Give concise, useful, evidence-grounded answers for supported titles.
- G3: Avoid revealing story events beyond the viewer's allowed progress.
- G4: Show useful evidence such as scene/time references when available.
- G5: Fail safely when title, progress, evidence, or authorization is uncertain.
- G6: Support maintainable ingestion, indexing, evaluation, monitoring and catalog operations.

## 4. Non-goals for initial release
- Replacing a streaming service or hosting full movies.
- Bypassing DRM, extracting protected media, or defeating platform restrictions.
- Guaranteeing automatic playback-position detection across all providers.
- Providing unrestricted internet answers about every title.
- Replacing subtitles, accessibility features or parental controls provided by the platform.
- Building a knowledge graph before retrieval evaluations demonstrate a measurable need.
- Training a foundation model from user conversations.
- Making claims that the system is perfectly spoiler-proof or hallucination-free.

## 5. Users and roles
- **Viewer:** chooses a supported title, sets/validates progress when needed, asks questions and reviews answers.
- **Catalog operator:** adds/removes authorized content assets and inspects ingestion status.
- **Administrator:** manages configuration, access, retention and operational health.
- **Developer/agent:** implements changes under the execution rules in document 10.

Least privilege applies. A viewer cannot trigger privileged ingestion or access another viewer's private sessions.

## 6. Core journeys
### J1 — Start a session
1. Open Rewind.
2. Choose a supported title or resume a prior session.
3. Rewind resolves title identity and content-index availability.
4. If playback position cannot be verified, user is asked to set or confirm progress.
5. Session begins in conservative spoiler mode.

### J2 — Ask a question
1. Viewer opens the question interface.
2. Viewer types or dictates a question, if voice input is supported.
3. Client submits the question and session identifier.
4. Server validates ownership, title, progress and spoiler policy.
5. Retrieval is filtered before the answer model receives evidence.
6. Server validates the generated answer and its evidence references.
7. Client renders answer, source/time references, and a useful recovery path if evidence is insufficient.

### J3 — Ask about an earlier scene
The system searches only within the permitted story range, responds with a short explanation and cites the supporting scene/time. If no reliable support is found, it says it cannot verify the answer rather than guessing.

### J4 — Request a spoiler
A spoiler-intent question must not bypass policy. If policy requires confirmation, present a clear warning and an explicit confirmation step. The server records the confirmed session policy and applies it to subsequent requests only according to the product's defined scope. No client-only flag may authorize spoilers.

### J5 — Content ingestion
An authorized operator submits an asset and metadata. The pipeline validates rights/format, parses timestamps, chunks content, embeds chunks, indexes them, and publishes only after validation succeeds. Failures remain inspectable and must not leave a partially published title.

## 7. Product principles
- Grounded over fluent: evidence wins over a plausible guess.
- Safe by default: uncertainty must not widen spoiler access.
- Explicit state: title, progress and spoiler mode are visible and auditable.
- TV-first: readable from a distance, focus state always visible, remote-only operation.
- Minimize data: collect only what is needed.
- Reversible operations: ingestion, reindexing and deletion have explicit state and recovery behavior.

## 8. Success metrics
Instrument and establish baselines before setting targets:
- Supported-question answerability and grounded-answer rate.
- Unsupported claim rate and citation correctness.
- Spoiler-policy violation rate (target: zero known violations in release tests; continue monitoring).
- Question latency percentiles and error rate.
- Ingestion success rate, time, and duplicate-chunk rate.
- Session completion and repeat-use rates.
- Accessibility and remote-navigation task completion.
Do not optimize engagement at the cost of safety, privacy, or answer quality.

## 9. Constraints and unresolved decisions
OPEN: exact Fire TV technology/runtime; authentication method; supported titles and territories; subtitle/transcript licensing; playback-position integration; voice input; language support; LLM/embedding providers; cost ceiling; retention period; analytics consent; offline behavior; target concurrency/SLOs. Resolve these before locking implementation choices.
