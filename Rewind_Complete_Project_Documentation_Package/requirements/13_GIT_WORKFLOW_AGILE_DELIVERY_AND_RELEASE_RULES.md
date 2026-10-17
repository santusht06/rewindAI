# 13_GIT_WORKFLOW_AGILE_DELIVERY_AND_RELEASE_RULES.md

**Status:** Mandatory engineering policy  
**Applies to:** Every developer and coding agent working on Rewind  
**Priority:** This policy supplements the product, architecture, testing, and coding-agent requirements. If repository-level rules are stricter, follow the stricter rule unless the project owner explicitly approves a change.

---

## 1. Purpose

This document defines how all work must be planned, decomposed, implemented, tested, committed, reviewed, integrated, and released.

The objectives are to:

- preserve a complete, auditable history of every meaningful code change;
- make small changes that can be understood, reviewed, reverted, and tested independently;
- decompose every epic, phase, feature, and bug fix into progressively smaller deliverables;
- follow an Agile process with a visible backlog, acceptance criteria, iteration planning, daily progress tracking, reviews, and retrospectives;
- run appropriate tests from the smallest unit through end-to-end validation;
- protect `main` as a stable integration/release branch;
- **commit changes locally and to the current working branch, but never push any branch or tag to any remote until the user explicitly authorizes pushing.**

The final rule is a hard gate. Silence, urgency, a green test suite, a merge, or a request to “finish the feature” is not permission to push.

## 2. Non-negotiable Git rules

### 2.1 Commit, do not push

1. Commit each coherent, verified change locally on the designated working branch.
2. Do not run `git push`, `git push --all`, `git push --tags`, `git push origin ...`, or any equivalent remote-write operation unless the user has explicitly authorized the specific push in the current conversation.
3. Do not push implicitly through a GUI, IDE, Git integration, automation, CI workflow, GitHub CLI, hosting provider, or another tool.
4. Do not publish a branch, tag, release, pull request, or remote commit as a workaround for the no-push rule.
5. Do not assume that permission to merge locally also permits pushing.
6. If the user authorizes a push, confirm the intended remote and branch if they are not unambiguous. Push only the authorized branch/ref; do not push tags or other branches unless separately authorized.
7. After committing, report that the commit exists locally and that no push was performed.

### 2.2 Start-of-task repository inspection

Before changing files, run and inspect relevant equivalents of:

```bash
git status --short --branch
git branch --show-current
git log -5 --oneline --decorate
git remote -v
```

Also inspect project manifests, instructions, tests, build scripts, migrations, and the current diff as relevant.

- Preserve pre-existing user changes. Never overwrite, reset, clean, stash, amend, or include them without understanding their purpose and getting approval when an action could lose or alter them.
- If the working tree contains unrelated or unexplained changes, do not include them in the task's commits.
- Never use destructive Git commands such as `git reset --hard`, `git clean -fd`, or forced branch changes without explicit approval.
- Never amend, rebase, squash, or rewrite an existing commit unless explicitly requested.
- Do not change the active branch when that would risk existing work. If the correct branch is unclear, stop and ask or document the blocker.

### 2.3 Branching model

Use the repository's existing branching convention where one exists. Do not invent a new convention that conflicts with project configuration.

If no convention exists, use:

- `main`: protected, stable, releasable branch;
- `develop`: optional shared integration branch if the project needs one;
- `feature/<short-name>`: feature work;
- `fix/<short-name>`: bug fixes;
- `chore/<short-name>`: tooling, documentation, maintenance;
- `hotfix/<short-name>`: urgent production fixes.

Keep branches short-lived. Do not create a branch solely for every tiny sub-subtask if doing so adds needless overhead; use the smallest branch structure that fits the team's review and integration needs.

Never commit routine feature work directly to `main`. If the project is currently configured to work directly on `main`, inspect the state and propose a safe branch before modifying tracked files. Do not move or rewrite existing work without approval.

### 2.4 Commit boundaries

Commit after each small, coherent unit of work has passed the relevant local checks. Examples:

- a pure domain model and its unit tests;
- a migration and the tests that validate it;
- one API contract plus implementation and tests;
- one screen or interaction with its tests;
- documentation for one agreed design decision.

Do not create one huge commit for an entire phase. Do not create meaningless commits merely to satisfy a numeric quota. Each commit must represent a clear, reviewable state.

A commit must not knowingly contain failing tests, broken builds, temporary debug code, secrets, unrelated formatting, generated junk, or unrelated user changes. If a baseline test is already failing, record the failure and prove whether the change affects it before deciding whether a commit is safe.

### 2.5 Commit message format

Prefer Conventional Commits unless the repository already defines another standard:

```text
<type>(<scope>): <imperative summary>

Why:
- Explain the problem or requirement addressed.

Validation:
- List the relevant checks run and their outcomes.

Work item:
- EPIC-123 / STORY-123 / TASK-123
```

Allowed types include `feat`, `fix`, `refactor`, `test`, `docs`, `build`, `ci`, `perf`, and `chore`.

Examples:

```text
feat(retrieval): add timestamp-filtered transcript search
fix(spoilers): exclude future chunks in safe mode
test(api): cover invalid playback positions
docs(architecture): define ingestion failure recovery
```

Keep the summary specific and concise. Never claim tests passed if they were not run. A commit message can refer to a work item, but must not include secrets or private user data.

## 3. Required Agile hierarchy

Every meaningful project deliverable must be represented in a traceable hierarchy. Use the repository's issue tracker if available; otherwise maintain a Markdown backlog and progress log.

```text
Product Goal
└── Release / Milestone
    └── Epic
        └── Phase / Iteration objective
            └── Feature / User Story
                └── Sub-phase / Task
                    └── Sub-sub-phase / Implementation step
                        └── Verifiable change
                            └── Tests and evidence
                                └── Local commit(s)
```

The hierarchy is not permission to create bureaucracy. Split work until each leaf task is small enough to implement, review, test, and describe clearly—typically hours rather than multiple days. If a task is still too large or has multiple independent outcomes, split it further.

### 3.1 Every level needs an explicit outcome

Each release, epic, phase, feature, sub-phase, and sub-sub-phase must specify, where applicable:

- stable ID and title;
- problem and user/business value;
- scope and explicit non-goals;
- dependencies and blockers;
- acceptance criteria written as observable outcomes;
- design/API/data implications;
- security, privacy, spoiler-policy, and compatibility implications;
- test cases and required test level;
- definition of done;
- owner/status;
- related commits and evidence.

Do not mark work complete because code was written. It is complete only when the agreed acceptance criteria and verification requirements are met.

### 3.2 Example hierarchy

```text
RELEASE R0.1 — Reliable content ingestion
└── EPIC ING-01 — Ingest authorized subtitle assets
    └── PHASE 1 — Input validation
        └── STORY ING-01-S1 — Reject unsupported or malformed assets
            ├── TASK ING-01-S1-T1 — Define supported formats and size limits
            │   ├── STEP 1.1.1 — Add configuration and schema
            │   ├── STEP 1.1.2 — Add valid-input tests
            │   └── STEP 1.1.3 — Add invalid/boundary-input tests
            ├── TASK ING-01-S1-T2 — Implement parser validation
            │   ├── STEP 1.2.1 — Implement pure validation logic
            │   ├── STEP 1.2.2 — Map validation failures to stable errors
            │   └── STEP 1.2.3 — Add regression tests
            └── STORY VERIFICATION
                ├── Unit tests
                ├── Integration tests
                ├── Security and resource-limit tests
                └── Commit locally after checks pass
```

## 4. Agile operating cadence

Use Scrum-style iteration planning with Kanban visibility for work in progress. Adapt iteration length to the project, but keep the process explicit and lightweight.

### 4.1 Backlog refinement

Before a story is selected:

1. clarify the user problem and intended behavior;
2. confirm it is in scope and identify non-goals;
3. break it into tasks and smaller steps;
4. write testable acceptance criteria;
5. identify dependencies, schema/API changes, security concerns, and rollback needs;
6. estimate relative size or effort;
7. identify unknowns and resolve high-risk questions early;
8. link it to the requirement and design documents.

If a requirement is ambiguous or contradictory, do not silently invent product behavior. Record the question and request a decision when it materially affects architecture, privacy, security, data, user experience, or scope.

### 4.2 Iteration planning

At the beginning of each iteration:

- state one iteration goal;
- select only work that fits available capacity;
- verify dependencies and acceptance criteria;
- identify the tasks, tests, and documentation needed;
- establish a demonstrable outcome;
- record the starting status and known risks.

Do not promise that every planned item will finish. Do not start more work than can reasonably be verified.

### 4.3 Daily progress tracking

For each active story, record:

- completed since the last update;
- next smallest actionable task;
- current blocker or uncertainty;
- test/build status;
- local commit hashes;
- whether any integration is waiting for review.

Keep `docs/engineering/WORK_LOG.md` and `docs/engineering/DECISIONS.md` if no equivalent files exist. Do not duplicate an established issue tracker unnecessarily. Update progress after each meaningful sub-phase, not just at the end of a large feature.

### 4.4 Review and retrospective

At the end of an iteration:

- demonstrate working behavior against acceptance criteria;
- review test results, known defects, risks, and incomplete work;
- verify documentation and traceability;
- record what should improve in the next iteration;
- carry unfinished work back to the backlog with updated status.

A retrospective action must have an owner and a concrete follow-up task.

## 5. Definition of Ready

A story may start only when:

- the desired outcome is clear;
- acceptance criteria are testable;
- dependencies and likely impacted modules are known;
- product decisions needed for implementation are resolved;
- security/privacy and data implications have been considered;
- the work can be split into small tasks;
- the required test and verification approach is understood.

If a story cannot meet these conditions, create a discovery/spike task rather than guessing.

## 6. Definition of Done

A story is done only when all applicable checks pass:

- implementation matches the approved requirement and acceptance criteria;
- no unrelated files or changes are included;
- unit tests pass;
- integration tests pass;
- API/contract tests pass where applicable;
- end-to-end tests pass for affected user journeys;
- regression tests cover the defect or prior failure;
- security, authorization, spoiler, privacy, boundary, and failure-path tests pass where applicable;
- lint, formatting, type checking, build, and static analysis pass as configured;
- migrations are tested and rollback/forward recovery is documented;
- observability and actionable error handling are in place;
- user/developer documentation is updated;
- code review or self-review is complete;
- changes are committed locally with traceable commit messages;
- the working tree is understood and no unintended files are included;
- no push has occurred unless explicitly authorized by the user.

If a check cannot run, mark the item **NOT VERIFIED**, explain why, and do not falsely claim full completion. A release-critical check cannot be waived by the coding agent itself.

## 7. Testing strategy: left to right, unit to end-to-end

Testing must be designed while decomposing the story, not added as an afterthought.

### 7.1 Test pyramid

1. **Static checks:** formatting, lint, type checks, dependency/security scans where configured.
2. **Unit tests:** pure logic, boundaries, validation, state transitions, policy decisions.
3. **Component tests:** one service/module with controlled dependencies.
4. **Integration tests:** database, migrations, Redis/cache, embedding provider adapters, queues, and external boundaries.
5. **Contract tests:** request/response schemas, error semantics, compatibility and versioning.
6. **End-to-end tests:** complete user journeys through realistic application boundaries.
7. **Non-functional tests:** load, latency, resource limits, resilience, security, accessibility and supported-device behavior.
8. **Release smoke tests:** critical flows on the exact candidate build/configuration.

Use deterministic fakes for unit tests and real test infrastructure for integration tests where feasible. A fake must not be presented as proof that a real third-party integration works.

### 7.2 Rewind critical test areas

At minimum, cover:

- authorized content ingestion, malformed input, duplicate ingestion and interrupted ingestion;
- timestamp parsing, chunk boundaries and media-position mapping;
- retrieval relevance, evidence ranking, source identity and citation integrity;
- safe-mode exclusion of future transcript chunks before context reaches the LLM;
- explicit spoiler-confirmation state, session boundaries and policy changes;
- cache-key separation across title, position, policy, locale and relevant context;
- prompt injection inside transcript text;
- unsupported questions and insufficient evidence;
- provider timeouts, rate limits, malformed model output and cancellation;
- database failures, migrations, transaction rollback and reindex recovery;
- authentication, authorization, rate limiting and input limits;
- Fire TV remote navigation, focus order, back behavior, loading/error/empty states;
- end-to-end asking a question and showing a grounded answer with valid source timestamps.

Never rely solely on an LLM prompt to enforce authorization or spoiler rules. Enforce them in deterministic server-side code and test them directly.

### 7.3 Regression discipline

Whenever a defect is found:

1. write a failing regression test that reproduces it, where practical;
2. confirm the test fails for the intended reason;
3. implement the smallest safe fix;
4. run the regression test;
5. run the relevant surrounding suite and end-to-end flow;
6. document the root cause and prevention;
7. commit the fix locally.

Do not delete, skip, weaken, or rewrite a test simply to make a build green. If a test is incorrect, explain the evidence and update it deliberately.

## 8. Local commit workflow for each sub-phase

For each small task or sub-phase:

1. Read the current task and acceptance criteria.
2. Inspect `git status`, current branch, and relevant code.
3. Make one coherent change.
4. Add/update tests and documentation.
5. Run the smallest relevant test first.
6. Run the affected component/integration tests.
7. Run lint/type/build checks relevant to the change.
8. Inspect `git diff --check`, `git diff`, and `git status`.
9. Ensure no secrets, generated artifacts, unrelated files, or pre-existing user changes are staged.
10. Stage explicit paths rather than blindly staging everything.
11. Commit with a descriptive message.
12. Record the commit hash, checks, outcome, and remaining work in the work log.
13. Continue to the next leaf task only when dependencies and checks allow it.
14. **Do not push.**

Example commands (adapt to the repository; inspect results before executing):

```bash
git status --short --branch
git diff --check
git diff
git add path/to/intentional-file path/to/intentional-test
git diff --cached --check
git diff --cached
git commit -m "fix(spoilers): exclude future chunks in safe mode"
git status --short --branch
git log -1 --oneline
```

Never run `git add .` or `git add -A` without first inspecting every changed/untracked file and confirming that all of them belong in the commit. Explicit path staging is preferred.

## 9. Main-branch integration policy

`main` must remain stable and releasable.

1. Implement work on the agreed feature/fix/chore branch.
2. Complete the story's tests and review.
3. Complete cross-feature integration tests.
4. Run the full required regression suite and production build.
5. Run end-to-end tests for all affected critical journeys.
6. Review migrations, environment/configuration changes, observability, security and rollback.
7. Prepare an integration report with commits, test evidence, known limitations and risk.
8. Integrate into `main` only through the repository's approved merge method and only when the user/project owner has authorized that integration, unless an existing explicit project policy already delegates this authority.
9. Never force-push or rewrite `main`.
10. After local integration, verify `main` and the working tree, record the resulting commit, and **do not push** without explicit user authorization.

### 9.1 Local merge versus remote pull request

A local merge is not a remote merge. Do not create or update a remote pull request, because doing so generally requires publishing a branch. If the project requires a pull request for review, prepare the branch and a local review summary, then wait for explicit permission to push/open the remote PR.

### 9.2 When the user says “merge into main”

Treat that as permission to perform the requested merge locally only, unless the user explicitly also says to push. Do not infer remote permission.

### 9.3 Before integrating

Confirm:

- all required checks passed on the exact commits to integrate;
- no unexpected working-tree changes exist;
- commits are traceable to accepted work items;
- the merge base and target are understood;
- migrations and configuration remain compatible;
- rollback/recovery steps exist for risky changes;
- the user has authorized local integration if required by project policy.

If any critical check fails, do not merge. Report the failure and propose a fix.

## 10. Phase and feature completion reports

At the end of each sub-phase, report:

- hierarchy ID and title;
- files changed;
- behavior delivered;
- tests run and exact results;
- checks not run and why;
- local commit hash(es);
- outstanding defects, assumptions or blockers;
- next sub-phase;
- Git status;
- explicit statement: **“No push performed.”**

At the end of each feature, additionally report acceptance criteria individually as `PASS`, `FAIL`, or `NOT VERIFIED`.

At the end of each phase, provide an integration report and confirm whether all dependent stories are complete. Do not describe an incomplete phase as complete.

## 11. Change tracking and traceability

Maintain a traceability chain:

```text
Requirement ID
  → Epic / Story / Task ID
  → Acceptance criterion
  → Test case(s)
  → Implementation file(s)
  → Local commit hash(es)
  → Verification result
```

Use stable identifiers. Do not silently renumber existing items. For every behavior change, update the relevant requirement or decision record if it changes documented behavior.

Recommended files if equivalent project systems do not exist:

```text
docs/
├── requirements/
├── architecture/
├── decisions/
└── engineering/
    ├── WORK_LOG.md
    ├── DECISIONS.md
    ├── RELEASE_CHECKLIST.md
    └── TEST_EVIDENCE.md
```

Keep the work log concise and append-only where practical. Never store secrets, tokens, private credentials or sensitive production data in documentation, tests, logs or commits.

## 12. Dependency, migration and configuration changes

For dependency changes:

- explain why the dependency is needed;
- check maintenance, license, compatibility and security posture as appropriate;
- pin or constrain versions according to repository conventions;
- update lockfiles;
- run the relevant test/build suite;
- do not add a package to avoid understanding an existing abstraction.

For database changes:

- use versioned migrations;
- test fresh-database and upgrade-from-supported-version paths;
- consider backward compatibility and expand/contract migrations for live systems;
- define rollback or forward-recovery strategy;
- never run destructive production operations without explicit approval.

For configuration changes:

- update example environment files and docs;
- do not commit real credentials;
- validate required values at startup;
- define safe defaults and failure behavior.

## 13. Handling failed tests and existing failures

- Capture the failing command and relevant error.
- Determine whether it is caused by the current change, a pre-existing failure, or environment limitations.
- Do not mask a failure by swallowing exceptions or weakening assertions.
- If the failure is pre-existing, record a baseline and run targeted tests to assess impact.
- Do not merge a change that introduces a failure in a required check.
- If the environment prevents a required test, mark it `NOT VERIFIED` and identify the needed environment.
- A passing subset is not equivalent to a passing full suite.

## 14. AI coding-agent conduct

The coding agent must:

- act as an implementation assistant, not an autonomous release authority;
- follow the approved backlog and do only the current task's scope;
- stop and ask when a decision could materially change product behavior, security, data integrity, cost, or architecture;
- never claim tests, builds, commits, merges or pushes happened unless verified;
- never create fake test evidence;
- never bypass hooks or CI checks to force completion;
- never expose secrets or include them in commit messages;
- never push unless the user explicitly authorizes the exact push;
- never integrate into `main` while critical checks are failing;
- keep all uncommitted user changes intact;
- prefer reversible, small changes and provide a truthful summary.

If the user asks for a broad feature, first produce the epic/phase/story/task/sub-task breakdown and proposed acceptance criteria. Do not begin a large implementation before the plan is reviewed when scope or architecture is uncertain.

## 15. Release checklist

A release candidate is ready for review only if:

- [ ] all included stories meet their acceptance criteria;
- [ ] required unit, component, integration, contract and end-to-end tests pass;
- [ ] security/privacy/spoiler regressions pass;
- [ ] lint, type checks and production build pass;
- [ ] migrations and recovery plans are reviewed;
- [ ] logs, metrics and error handling are adequate;
- [ ] supported-device smoke tests pass where applicable;
- [ ] release notes and known limitations are accurate;
- [ ] commits and work items are traceable;
- [ ] no unrelated or secret files are included;
- [ ] local integration into `main` is authorized and verified if applicable;
- [ ] user explicitly authorized any remote push (otherwise no push is performed).

Passing this checklist means the candidate is ready for the designated review/release decision. It does not authorize the agent to deploy or publish automatically.

## 16. Required final status format

```text
Work item:
Hierarchy:
Branch:
Summary:
Files changed:
Acceptance criteria:
- AC-1: PASS / FAIL / NOT VERIFIED — evidence
- AC-2: PASS / FAIL / NOT VERIFIED — evidence

Tests and checks:
- <command>: PASS / FAIL / NOT RUN — reason

Commits created locally:
- <hash> <subject>

Integration:
- Local main merge: YES / NO / NOT AUTHORIZED
- Remote push: NOT PERFORMED / AUTHORIZED AND PERFORMED

Working tree:
Known issues / risks:
Next smallest task:
```

## 17. Absolute final rule

**Commit every meaningful, verified change locally. Track it against the Agile backlog. Test every leaf task, run end-to-end and regression tests for the complete feature, and integrate into `main` only after the required checks and authorization. Never push to any remote until the user explicitly tells you to push.**

If unsure whether an operation publishes data to a remote, do not execute it. Ask first.
