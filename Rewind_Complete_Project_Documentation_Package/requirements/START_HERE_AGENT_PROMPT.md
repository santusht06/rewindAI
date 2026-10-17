# Start Here — Prompt for the Coding Agent

You are working on Rewind. Treat `docs/requirements/` as the requirements source of truth. Before implementing any feature:

1. Inspect the repository, git status, instructions, manifests, runtime versions, config, migrations, API contracts, tests, deployment and existing shared components.
2. Produce a gap analysis mapping each requirement ID to current implementation status: implemented-and-tested, partially implemented, missing, contradicted, or blocked.
3. Cite repository paths and test evidence for each status. Do not guess from filenames.
4. Identify unresolved decisions and risky assumptions, especially Fire TV runtime, content rights, playback position trust, spoiler consent, auth and data retention.
5. Propose a phased implementation plan with dependency order, affected files, migrations, tests, rollback and acceptance criteria.
6. Do not start a broad rewrite. Wait for approval if the task requires destructive changes, major architecture changes, new external services, rights-sensitive actions or unresolved policy choices.
7. When approved, implement a small vertical slice and follow `10_AI_AGENT_EXECUTION_RULES.md`.
8. Never claim perfect correctness. Report actual commands and results honestly.

First task: perform repository discovery and produce the gap analysis. Do not change application code during this first audit unless explicitly instructed.
