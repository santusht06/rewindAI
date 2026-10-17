# Rewind — Complete Project Documentation Package

This package consolidates the Rewind project documentation created across the planning workflow, including the latest Git/Agile delivery rules.

## Contents

- `requirements/` — Product requirements, software requirements, architecture, domain/database model, API contract, UX/screen requirements, security/privacy/safety, testing and acceptance criteria, implementation plan, AI-agent execution rules, production engineering guardrails, code organization standards, consolidated requirements, start-here prompt, and Git/Agile delivery/release rules.
- `production_prd/` — Production PRD in Markdown and DOCX, plus coding-agent instructions.
- `system_design_diagrams/` — Mermaid source files for use cases, system context, architecture, ingestion, online Q&A, sequence, spoiler control, translation, database ERD, deployment, and testing.

## Suggested use

1. Read `requirements/00_README.md`.
2. Give the coding agent `requirements/START_HERE_AGENT_PROMPT.md` and the entire `requirements/` directory as source-of-truth requirements.
3. Read `requirements/13_GIT_WORKFLOW_AGILE_DELIVERY_AND_RELEASE_RULES.md` before implementation. It requires local commits for verified changes and prohibits pushing to any remote until the user explicitly authorizes it.
4. Use the Mermaid files as source diagrams; render them with a Mermaid-compatible viewer when needed.
5. Reconcile the documentation with the actual repository before coding. Do not assume that documentation alone guarantees correctness or that every external integration is available.

## Documentation precedence

Treat the project-specific requirements and safety rules as the baseline. If documents conflict, stop and report the exact conflict for resolution rather than silently choosing a behavior. Never expose secrets, invent unverified integrations, or claim tests passed without running them.
