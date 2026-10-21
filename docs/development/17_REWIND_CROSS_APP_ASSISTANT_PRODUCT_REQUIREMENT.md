# 17 — Rewind Cross-App AI Viewing Assistant: Corrected Core Product Requirement

**Status:** Mandatory product clarification; supersedes any conflicting wording in earlier documents.

## 1. Product definition

Rewind is a **cross-application AI viewing assistant**, inspired by the interaction pattern of Google Gemini / Google Assistant. It is not an OTT service, streaming catalog, video player, or replacement for Netflix, Amazon Prime Video, Disney+, YouTube, or other viewing applications.

The user continues watching content in the streaming app they already use. Rewind provides an assistant experience that the user can invoke while watching, ask questions about the current story, receive context-aware answers with spoiler controls, and then return to the original viewing experience.

The core product promise is:

> “Keep watching in your preferred streaming app. Invoke Rewind to ask about what is happening, understand characters and events, and return to watching—without moving your content into a Rewind-owned OTT player.”

## 2. Explicit non-goals

Unless the user later changes the product direction, do **not** build:

- A Rewind-owned OTT catalog or subscription streaming service.
- A video hosting or playback platform.
- A replacement media player for Netflix or Prime Video.
- A requirement that users select or play their movie inside a Rewind video player.
- A content library that implies Rewind owns or has rights to third-party films.

A small demo launcher or settings screen is acceptable only as a utility for configuring Rewind, choosing an integration mode, viewing supported providers, or testing the assistant. It must not become the primary viewing experience.

## 3. Primary user journey

1. The user launches Netflix (or another supported streaming provider) on a Fire TV device and starts watching a title.
2. The user pauses playback and invokes Rewind through a supported mechanism, such as an authorized system integration, supported remote/voice entry point, companion device, or other validated platform capability.
3. Rewind opens in an assistant-like experience, ideally as an overlay that preserves the current app and its playback position.
4. Rewind obtains the current title, playback position, language, and other context only through supported and authorized mechanisms. If these details cannot be accessed, the assistant must ask the user to provide/select the missing context or use another explicitly documented fallback.
5. The user asks a natural-language question, for example: “Who is this character?”, “Why did she betray him?”, or “What happened in the last scene?”
6. The backend retrieves authorized evidence, applies spoiler rules, and returns a concise, grounded answer with timestamps/citations when available.
7. The user dismisses Rewind and resumes the original streaming app, if the platform integration supports returning to it.
8. The user switches from Netflix to Prime Video or another provider. Rewind should use the same product experience and a provider-neutral integration contract; only provider-specific adapters/capabilities should vary.

## 4. Cross-provider flexibility

The architecture must not hard-code Netflix or Amazon Prime Video into core question-answering logic.

Define provider-neutral contracts such as:

- `PlaybackContextProvider`: obtains title identity, playback position, language, and context availability where authorized.
- `AssistantEntryPoint`: represents how the user invokes Rewind on a device/platform.
- `AssistantPresentationAdapter`: presents the assistant as a true overlay, side panel, foreground companion screen, or companion-device UI depending on verified platform capabilities.
- `ContentEvidenceProvider`: supplies legally obtained, authorized transcripts/subtitles/metadata and their provenance.
- `ProviderCapabilityRegistry`: records what each streaming provider and target OS actually supports.

Provider-specific adapters must implement these interfaces without leaking provider-specific behavior into domain services. Adding another streaming service should ideally require a new adapter and tests, not a rewrite of the backend or assistant UI.

Do not claim universal compatibility merely because the adapter interface exists. Each provider capability must have a status such as `VERIFIED`, `PARTIAL`, `UNAVAILABLE`, or `NOT_TESTED`, with evidence and a date/device/OS scope.

## 5. Critical platform feasibility constraint

**An ordinary third-party TV app must not be assumed to have permission to draw over, inspect, pause, or read playback state/subtitles from another app.**

Before committing to an in-app overlay implementation, the coding agent must research and test the exact target OS/device capabilities and current official platform rules. In particular, determine whether a third-party app can:

- Appear over another app without terminating or replacing it.
- Be invoked by a remote button, voice action, system shortcut, or approved integration.
- Read the active app/package identity.
- Read current title and playback position.
- Pause/resume third-party playback or preserve its state.
- Access captions/subtitles or audio/video frames from another application.
- Return the user to the previous app reliably.
- Operate under applicable app-store, privacy, DRM, and security restrictions.

Record results in a **Platform Capability and Evidence Matrix** with columns for capability, Fire OS version/device, Vega OS version/device, provider, official documentation/evidence, prototype test, result, limitation, and fallback.

Do not use hidden APIs, accessibility abuse, screen scraping, DRM circumvention, unauthorized interception, or unsupported privileged permissions to imitate system-level access.

### Fallback hierarchy

If a true cross-app overlay is not supported, do not silently build a standalone OTT app. Evaluate and document alternatives in this order:

1. An officially supported system assistant / app-to-app integration, if available and authorized.
2. A foreground assistant surface that can return to the previous app and preserve context, if supported and verified.
3. A companion phone/tablet/web assistant paired to the TV session, with user-confirmed title and playback position when automatic context is unavailable.
4. A provider-specific integration that is explicitly supported by that provider.

A fallback must be clearly labelled in product documentation and demo scripts. It must not be represented as a universal on-screen overlay if it is not one.

## 6. Demo scope and acceptance

The first demo should prove the cross-app assistant concept rather than attempt unsupported universal integration.

The demo must:

- Run on at least one explicitly selected and verified target device/OS.
- Keep the streaming provider as the place where the video is watched.
- Demonstrate a supported way to invoke the Rewind assistant.
- Ask a story question and return an evidence-grounded answer.
- Demonstrate spoiler-safe behavior or explicitly state when playback position cannot be verified.
- Return to the original viewing flow where the chosen integration permits it; otherwise demonstrate and document the approved fallback honestly.
- Clearly identify which provider/context capabilities are real, simulated, manually supplied, or not yet supported.
- Include a repeatable test/demo script and evidence (logs, test results, screenshots/video where available).

A mock provider may be used in unit/integration tests, but it does not count as proof of real Netflix or Prime Video integration. A successful backend API test does not prove that the cross-app TV experience works.

## 7. Backend-first, but platform validation from day one

Continue the requested backend-first implementation sequence, with one essential adjustment: **platform feasibility is an early blocking workstream**, not a final frontend task.

- Phase 0: audit requirements, research official platform APIs, identify target device/OS, build the capability matrix, and test the riskiest cross-app assumptions with a tiny prototype or evidence-backed spike.
- Backend phases: build provider-neutral APIs, content ingestion, retrieval, AI orchestration, authorization, spoiler policy, and observability.
- Platform proof: in parallel with backend foundation, create the smallest runnable assistant shell on the chosen OS and verify its actual entry/presentation/return capabilities. Do not implement the full UI yet.
- Frontend: begin full assistant UX after backend contracts are stable and the platform entry/presentation approach is proven or a fallback is explicitly accepted.
- End-to-end: test the real chosen invocation path and actual supported provider context; distinguish real integration from mocks/manual input.

If the essential cross-app invocation/context capabilities cannot be verified, mark the corresponding backlog items `BLOCKED` and present the evidence and options to the user before building a misleading substitute.

## 8. Required backlog additions

Create and track these tasks before full product implementation:

- `PLAT-001`: Select target Fire OS/Vega OS device and version based on actual requirements.
- `PLAT-002`: Verify app overlay/foreground presentation and lifecycle behavior.
- `PLAT-003`: Verify invocation options (remote/voice/system/companion) and permissions.
- `PLAT-004`: Verify active provider/title/playback-position availability for Netflix and Prime Video separately.
- `PLAT-005`: Verify subtitle/transcript evidence access and content rights; do not assume direct access to protected streams.
- `PLAT-006`: Prototype invoke → ask → answer → return flow on the target device.
- `PLAT-007`: Publish provider capability matrix and select MVP integration mode.
- `PLAT-008`: Add automated tests for missing/incorrect playback context and provider switching.

Every task requires acceptance criteria, test evidence, a status, and a local commit for meaningful verified changes. Do not push to any remote repository without explicit user authorization.

## 9. Definition of done for the product requirement

This requirement is verified only when:

- Rewind is positioned and implemented as a companion assistant, not an OTT service.
- The chosen target OS/device is explicitly recorded.
- The cross-app interaction model is demonstrated or an approved fallback is used and labelled honestly.
- Provider integrations are modular and capability-driven.
- Provider switching does not require rewriting core AI logic.
- The answer pipeline uses authorized evidence and enforces spoiler policy.
- Actual integration tests distinguish real provider capabilities from mocks and manual context.
- All limitations and unsupported providers are documented.

## 10. Official platform research starting points

The implementation agent must check the current official documentation for the chosen device/OS and record the exact evidence it relies on. Starting points:

- Fire TV app development: https://developer.amazon.com/docs/fire-tv/get-started-with-fire-tv.html
- Fire TV multimedia/app lifecycle requirements: https://developer.amazon.com/docs/fire-tv/multimedia-app-requirements.html
- Vega app development: https://developer.amazon.com/docs/vega/latest/build-an-app
- Vega developer guides: https://developer.amazon.com/docs/vega/0.24/dev-guides-overview

These documents describe app development and lifecycle capabilities; they do **not by themselves prove** that an ordinary third-party app can overlay or inspect Netflix/Prime Video. Verify the specific required capabilities separately.
