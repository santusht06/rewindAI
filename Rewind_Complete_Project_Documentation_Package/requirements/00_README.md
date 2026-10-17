# Rewind — Complete Product & Engineering Requirements
**Document set:** 1.0  
**Status:** Baseline specification; decisions explicitly marked `OPEN` require confirmation before production implementation.

## Purpose
This repository is the authoritative, version-controlled requirements set for Rewind, an AI story companion designed initially for a TV/Fire TV experience. It explains what the product must do, how components are expected to behave, and how an implementation agent must prove that its changes work.

## Document index
1. `01_PRODUCT_REQUIREMENTS.md` — product scope, users, goals and journeys.
2. `02_SOFTWARE_REQUIREMENTS_SPECIFICATION.md` — functional/non-functional requirements and system behavior.
3. `03_DOMAIN_MODEL_AND_DATABASE.md` — entities, invariants, relationships and persistence.
4. `04_API_CONTRACT.md` — API conventions, endpoint contracts and error semantics.
5. `05_SYSTEM_ARCHITECTURE.md` — boundaries, data flow, ingestion and runtime Q&A.
6. `06_UX_AND_SCREEN_REQUIREMENTS.md` — TV-first screens, remote navigation and accessibility.
7. `07_SECURITY_PRIVACY_AND_SAFETY.md` — identity, authorization, data handling, AI safety and content rights.
8. `08_TESTING_AND_ACCEPTANCE_CRITERIA.md` — test layers, acceptance scenarios and release gates.
9. `09_IMPLEMENTATION_PLAN.md` — phased implementation and dependency order.
10. `10_AI_AGENT_EXECUTION_RULES.md` — mandatory rules for the coding agent.
11. `11_PRODUCTION_ENGINEERING_GUARDRAILS.md` — consistency, reliability, observability and operations.
12. `12_CODE_ORGANIZATION_AND_STYLE_STANDARDS.md` — repository layout and coding conventions.
13. `GoBuddy_COMPLETE_REQUIREMENTS.md` — consolidated requirements. The legacy GoBuddy filename is retained from the requested template; the product described here is **Rewind**. Rename only if the intended product name is actually GoBuddy.

## Normative language
- **MUST / MUST NOT** = mandatory release requirement.
- **SHOULD / SHOULD NOT** = strong recommendation; deviations need a documented reason.
- **MAY** = optional.
- A requirement is not implemented merely because code exists. It must have an observable test or other reviewable evidence.

## Product assumptions and open decisions
- The first target is a Fire TV / TV interface. Confirm the exact native runtime and distribution constraints by inspecting the real repository and current platform documentation.
- The service uses a backend API and a content index. PostgreSQL with vector search is a candidate baseline, not a license to add dependencies before inspecting the repository.
- Content is indexed only from material the operator is authorized to process and store. Do not scrape or redistribute copyrighted subtitle/transcript content without permission.
- Do not assume streaming providers expose playback position, subtitles, or deep links to third-party apps. Every integration needs documented, authorized technical proof.
- LLM and embedding provider, hosting, authentication provider, data retention, supported catalog, budget, and service-level targets are `OPEN`.
- Default spoiler mode is conservative: answer only from content known to have been reached by the user, when trustworthy playback position is available. If position is unavailable or unreliable, ask the user to set/confirm the current point or use a clearly disclosed manual progress mode. Never silently assume a position.
- A coding agent MUST distinguish confirmed product decisions from proposals and MUST surface blockers instead of inventing requirements.

## Change control
Each requirement should have a stable ID. A change that affects API, schema, spoiler behavior, privacy, supported platform, or stored data requires:
1. impact analysis;
2. migration/backward-compatibility assessment;
3. tests and rollback strategy;
4. updates to all affected documents;
5. explicit approval for destructive data changes or external side effects.

## Definition of ready
A task is ready when its user-visible outcome, edge cases, access rules, error behavior, acceptance criteria, and dependencies are understood. If a security, privacy, rights, or spoiler-policy decision is unresolved, the agent must ask or implement the safe default without expanding scope.

## Definition of done
- Acceptance criteria are mapped to tests or reviewable evidence.
- Formatting, lint, type checks, unit/integration tests and build have been run where available.
- Relevant regression and security tests pass.
- Migrations are reversible or have a documented recovery plan.
- No secrets, user data, or sensitive transcript text leak into logs.
- Documentation and configuration examples are updated.
- The agent reports exact commands and results, including skipped or failed checks. It never claims “bug-free.”
