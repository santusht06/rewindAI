# 12 — Code Organization and Style Standards

## 1. First rule: repository evidence wins
The structure below is a logical reference, not permission to restructure an existing working repository blindly. The agent MUST inspect the current repository and adapt these boundaries to its actual stack. Avoid a mass rename or framework migration unless explicitly requested.

## 2. Suggested logical structure
```text
/
  docs/
    requirements/                 # this document set
    adr/                          # architecture decision records
  apps/
    tv-client/                    # actual TV app/runtime, if monorepo
  services/
    api/
      api/                        # routing/controllers and request schemas
      domain/                     # entities, policies, domain outcomes
      application/                # use cases/orchestration
      infrastructure/             # DB, cache, model providers, external adapters
      migrations/
      tests/
    ingestion-worker/
  packages/
    contracts/                    # shared/generated API contracts where supported
  evals/
    datasets/
    reports/
  ops/
    deployment/
    monitoring/
    runbooks/
  scripts/
  .env.example                    # placeholders only
  README.md
```
Do not create every directory just to match this diagram. Start with the minimum coherent structure needed.

## 3. Layer boundaries
- **Presentation:** rendering, focus/navigation, input validation for usability. No authoritative access or spoiler decisions.
- **API/controller:** transport parsing, authentication context, request/response mapping.
- **Application/use case:** orchestrates business actions and transactions.
- **Domain:** progress policy, spoiler rules, lifecycle transitions and invariants.
- **Infrastructure:** database, vector search, model providers, object storage, external APIs.
- **Worker:** asynchronous ingestion with explicit job states and idempotency.
Keep dependencies directed inward: domain logic should not depend on UI frameworks or provider SDKs.

## 4. Naming and style
- Use the repository's formatter, linter and idioms.
- Prefer descriptive names over abbreviations.
- Avoid boolean names that conceal state; use explicit enums for multi-state workflows.
- Keep functions cohesive and bounded.
- Avoid giant controllers, giant prompt builders, global mutable state and hidden side effects.
- Use typed request/response schemas and explicit domain errors.
- Keep comments focused on why, invariants and non-obvious constraints; do not narrate obvious code.
- Never commit generated secrets, local databases, build outputs or real user data.
- Keep configuration and defaults documented and validated.

## 5. Error handling
- Use typed domain errors mapped centrally to stable API responses.
- Log errors once at the appropriate boundary with correlation ID.
- Preserve exception causes for diagnostics without exposing them to users.
- Never silently convert errors into empty success results.
- Catch only exceptions the current layer can meaningfully handle.

## 6. Tests and fixtures
- Mirror source structure for tests where appropriate.
- Use deterministic fixtures and synthetic content.
- Keep regression tests for every discovered defect.
- Do not rely on live model/provider calls for every unit test; use contract-tested adapters and controlled integration tests.
- Maintain a separate evaluation suite for answer quality and spoiler behavior.
- Tests must assert behavior, not implementation details unless those details are contractual.

## 7. API/schema style
- Keep OpenAPI or equivalent contract checked into version control.
- Use explicit enums and structured errors.
- Generate clients/types where stable and supported.
- Avoid untyped dictionaries at trust boundaries.
- Document deprecation and compatibility before breaking changes.

## 8. Pull request/change hygiene
- One coherent purpose per change.
- Explain requirement IDs and behavior changes.
- Include migration and rollout notes.
- Include test commands and results.
- Review the full diff for accidental generated files, secrets, duplicate code and unrelated formatting.
- Update documentation in the same change when contracts or behavior change.
