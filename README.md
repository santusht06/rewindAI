# Rewind

![AI Maintained](https://img.shields.io/badge/readme-AI%20maintained-blue)

Rewind is a TV-first story companion for supported titles. Viewers can ask questions about plot, characters, and scenes while watching. The service retrieves timestamped evidence from authorized subtitle assets, applies spoiler rules on the server, and returns cited answers or abstains when evidence is insufficient.

The repository contains a FastAPI backend, a static 10-foot TV web client, subtitle ingestion and retrieval services, operational scripts, automated tests, and a detailed product/engineering requirements package.

## Project Status

The core prototype and demo flows are implemented, and the local automated suite passed 62 tests on 2026-10-19. This is not production-launch approval: production identity and admin authorization, rights-cleared catalog operations, target-device validation, load testing, and deployment sign-off remain open. See the [implementation dashboard](docs/development/IMPLEMENTATION_STATUS.md) and the maintained [project checklist](checklist.md).

## Quick Start

For the complete setup, configuration, migration, test, and troubleshooting steps, see [Getting Started](docs/GETTING_STARTED.md).

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
alembic upgrade head
pytest -q
uvicorn services.api.main:app --reload
```

After startup:

- TV client: <[http://127.0.0.1:8000/tv/](http://127.0.0.1:8000/tv/)>
- API documentation: <[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)>
- Liveness: <[http://127.0.0.1:8000/health/live](http://127.0.0.1:8000/health/live)>
- Readiness: <[http://127.0.0.1:8000/health/ready](http://127.0.0.1:8000/health/ready)>

The default local database is SQLite. Without `GEMINI_API_KEY`, the app uses deterministic mock AI providers for local development and tests. Do not expose the development service to an untrusted network; the current viewer and admin identity checks are not production authentication.

## Main Capabilities

- Browse published titles and create a viewing session with manual playback progress.
- Ingest SRT and WebVTT assets, split them into timestamped chunks, and publish an indexed content version.
- Ask title-scoped questions and receive evidence-grounded responses with scene citations or a safe abstention.
- Search authorized indexed subtitle cues for contextual translation, with source timestamps and spoiler-bounded context.
- Browse operator-curated character and relationship facts filtered by the session's reveal-time boundary.
- Enforce safe-mode retrieval boundaries before evidence reaches the model; require a server-issued, single-use confirmation for full-spoiler mode.
- Operate the client with a remote-friendly spatial D-pad navigation model.
- Monitor basic service metrics, rate-limit question requests, revoke published content, and back up/restore SQLite data.

Rewind does not currently synchronize with third-party streaming playback or obtain protected video, audio, or subtitles. Only content you are authorized to process should be ingested.

## Repository Guide

| Path | Purpose |
|---|---|
| `services/api/` | FastAPI application, API routes, domain logic, persistence, ingestion, retrieval, and AI providers |
| `apps/tv-client/` | Static television client and remote navigation code |
| `tests/` | API, persistence, ingestion, safety, client, operations, and demo tests |
| `ops/` | Packaging, backup/restore, and operational runbooks |
| `docs/development/` | Implementation status, decisions, known issues, traceability, and release documents |
| `Rewind_Complete_Project_Documentation_Package/requirements/` | Product and engineering source-of-truth requirements |

## Documentation

- [Local setup and development guide](docs/GETTING_STARTED.md)
- [Developer API reference](docs/API_REFERENCE.md)
- [Product requirements](Rewind_Complete_Project_Documentation_Package/requirements/01_PRODUCT_REQUIREMENTS.md)
- [System architecture](Rewind_Complete_Project_Documentation_Package/requirements/05_SYSTEM_ARCHITECTURE.md)
- [API contract](Rewind_Complete_Project_Documentation_Package/requirements/04_API_CONTRACT.md)
- [Security, privacy, and safety](Rewind_Complete_Project_Documentation_Package/requirements/07_SECURITY_PRIVACY_AND_SAFETY.md)
- [Acceptance criteria](Rewind_Complete_Project_Documentation_Package/requirements/08_TESTING_AND_ACCEPTANCE_CRITERIA.md)
- [Implementation status](docs/development/IMPLEMENTATION_STATUS.md)
- [Known issues and open decisions](docs/development/KNOWN_ISSUES.md)
- [Project checklist](checklist.md)