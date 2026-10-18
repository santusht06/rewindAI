# 16 — Mandatory Fire TV / Fire OS / Vega OS Demo Requirement

## 1. Requirement status

**Priority: P0 — Core product acceptance requirement.**

Rewind must deliver a working, demo-ready television application that runs on **Fire OS or Vega OS**. A backend API, browser-only mockup, desktop web application, architecture diagram, or simulator screenshot alone does not satisfy this requirement.

The project may use React Native, web technologies, Android Kotlin/Java, or another suitable framework, provided the chosen implementation is demonstrably compatible with the selected target platform and the project’s distribution/demo constraints.

## 2. Required outcome

The release candidate must include:

- An installable/runnable app or an explicitly documented and reproducible demo deployment on the selected supported platform.
- A television-first interface usable with a remote control or the platform’s standard input method.
- A working primary Rewind user journey connected to the real backend, not only hard-coded mock data.
- Clear loading, empty, error, retry, and offline/provider-failure states.
- A repeatable demo script, setup instructions, test evidence, and known-limitations list.
- Evidence of testing on the actual target platform or a clearly identified target-compatible environment. If physical hardware is unavailable, emulator/simulator validation must be labelled as such and physical-device validation must remain open.

## 3. Choose the platform early; verify rather than assume

During Phase 0, evaluate Fire OS and Vega OS against the required demo environment, framework compatibility, input/focus APIs, packaging, installation, networking, and available test hardware. Verify current platform requirements from official documentation before locking the stack.

Record an Architecture Decision Record (ADR) containing:

1. Chosen target: Fire OS or Vega OS (or an explicitly justified dual-target plan).
2. Framework and language.
3. Why it is compatible with the target and best for the demo timeline.
4. Packaging, build, install, and run procedure.
5. Remote-control/focus-navigation strategy.
6. Device/emulator test strategy and known limitations.
7. Any features or APIs that differ between the selected platform and the alternative.

Do not claim Vega OS compatibility merely because an app uses web technologies, and do not assume an Android APK will run unchanged on every Fire OS or Vega OS target. Verify compatibility for the actual target and document evidence.

## 4. Priority category alignment

The challenge lists these categories: **AI-enhanced viewing, sports, fitness, family entertainment, multi-modal UX, and computer vision**. The product backlog must explicitly map Rewind’s proposed features to these categories and identify which category or categories the demo is intended to demonstrate.

Rewind’s story-aware, evidence-grounded AI companion most naturally aligns with **AI-enhanced viewing**. Multi-modal UX may be considered only if a concrete, working interaction is planned and tested. Do not claim sports, fitness, family-entertainment, or computer-vision coverage unless actual requirements and implemented demo features support those claims.

Before major implementation, create a short category-fit statement with:

- Primary category and rationale.
- Secondary category, if applicable, and implemented evidence.
- Exact user-visible demo feature.
- Acceptance criteria and verification method.

Do not add unrelated features simply to claim multiple categories. Prioritize one compelling, reliable core demo.

## 5. Demo MVP user journey

The MVP journey must be refined against the existing product requirements. At minimum, define and verify the following journey where supported by the chosen platform and authorized content sources:

1. Launch Rewind on the target TV platform.
2. Navigate the interface using the remote/control method.
3. Open a supported demo title or clearly labelled sample story.
4. Ask a question about the story.
5. Send the request to the backend and retrieve relevant timestamped evidence.
6. Display an answer grounded in that evidence, with citation/timestamp UI where required.
7. Demonstrate spoiler-safe behavior for a question that crosses the allowed story boundary.
8. Show a safe, understandable response when evidence is insufficient or the backend/provider is unavailable.

Use authorized sample content or fixtures for the demo. Do not imply integration with third-party streaming services or live playback-position access unless that integration has been verified and authorized. If live playback integration is unavailable, expose playback position through a clearly labelled demo control or supported test fixture rather than pretending to read it from another app.

## 6. Backend-first delivery without postponing platform risk

The implementation sequence remains backend-first for core service correctness, but the target-platform risk must be checked at the start and a minimal TV shell must be built early enough to prove the selected platform can run the app.

Required sequence:

### Gate A — Phase 0 platform feasibility

- Confirm the actual target OS/version/device class.
- Verify official framework/build/package requirements.
- Identify available hardware or emulator.
- Create the platform ADR and category-fit statement.
- Define the end-to-end demo acceptance criteria.

**Gate A must pass before committing to a platform-specific frontend architecture.**

### Gate B — Backend foundation and core services

Implement database, API contracts, authorized content ingestion, retrieval, AI orchestration, and backend-enforced spoiler rules according to the detailed backlog. Test the backend independently and publish an OpenAPI/API contract for the client.

### Gate C — Minimal target-platform proof of execution

Create the smallest runnable app shell on the selected target. Verify startup, rendering, remote/focus navigation, network reachability, and packaging/install flow. This proof is an early risk-reduction task; it does not mean full frontend implementation must precede backend development.

### Gate D — Backend acceptance

The required backend tests and core workflows must pass. Record actual commands, outputs, and unresolved limitations. Do not start full feature integration against invented endpoints.

### Gate E — Frontend implementation and integration

Build the full TV user journey against the verified API contract. Use real backend integration for the core path; mocks may be used only in isolated UI tests or clearly labelled fallback/demo modes.

### Gate F — End-to-end demo acceptance

Run the complete journey on the chosen platform or clearly distinguish emulator verification from physical-device verification. Confirm remote navigation, answer rendering, citations/timestamps, spoiler restrictions, failure states, and repeatable setup.

## 7. Status tracking and evidence

Add the following fields to the project status tracker for each platform/demo task:

- `target_platform`
- `target_os_version_or_device_class`
- `build_command`
- `install_or_launch_procedure`
- `test_environment` (`physical_device`, `emulator`, `simulator`, or `not_available`)
- `verification_status`
- `evidence_or_log_reference`
- `known_platform_limitations`

Use these statuses consistently:

- `NOT_STARTED`
- `IN_PROGRESS`
- `BLOCKED`
- `IMPLEMENTED_UNVERIFIED`
- `VERIFIED`
- `DONE`

`DONE` requires a successful repeatable build/run procedure, completed acceptance criteria, recorded evidence, updated docs, and a local commit. A successful web build alone cannot mark the TV platform requirement done.

## 8. Required backlog items

Create and track these items explicitly:

- `PLAT-001`: Confirm Fire OS vs Vega OS target and demo constraints.
- `PLAT-002`: Verify framework compatibility and packaging against official platform documentation.
- `PLAT-003`: Record platform ADR and category-fit statement.
- `PLAT-004`: Create a minimal runnable target-platform shell.
- `PLAT-005`: Verify remote/focus navigation and backend connectivity.
- `DEMO-001`: Define the end-to-end demo script and acceptance checklist.
- `DEMO-002`: Prepare authorized sample content and reproducible demo data.
- `DEMO-003`: Integrate the core AI story-question flow with the backend.
- `DEMO-004`: Verify citations/timestamps, spoiler boundaries, and insufficient-evidence behavior.
- `DEMO-005`: Verify failure/retry states and document provider/network dependencies.
- `DEMO-006`: Record build, launch, and target-environment test evidence.
- `DEMO-007`: Complete final demo rehearsal and list any unverified device-specific behavior.

Each item must have an owner/agent, dependencies, acceptance criteria, tests, status, and local commit reference in the project tracker.

## 9. Non-negotiable acceptance rule

The project cannot be called demo-ready until Rewind can be launched on the selected Fire OS or Vega OS target, the main story-question journey works end to end against the backend, spoiler rules are enforced server-side, and the test evidence and known limitations are documented. Never claim platform compatibility or physical-device testing that has not actually been verified.
