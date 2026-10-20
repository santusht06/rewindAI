# Getting Started

This guide sets up Rewind for local development. It does not configure production credentials, authorize content, or validate a Fire TV/Vega OS device.

## Requirements

- Python 3.11 or newer. The project metadata accepts Python 3.11+, while Ruff and the engineering decision record target Python 3.12; Python 3.12 is the recommended development baseline.
- Git and a shell.
- Network access for the initial Python package installation.

Node.js is not needed for the current static TV client. No streaming-service account or AI API key is required for local tests.

## Install

Run from the repository root:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

The editable install uses the dependencies declared in `pyproject.toml`. The `dev` extra includes pytest, pytest-asyncio, coverage, Ruff, and mypy. A separate `requirements.txt` is not maintained.

If your shell does not activate the environment with `. .venv/bin/activate`, use the appropriate activation command for that shell, or call executables directly from `.venv/bin/`.

## Configure and Migrate

The defaults are suitable for local development: SQLite at `./rewind_local.db`, safe spoiler mode, and deterministic mock model/embedding providers. To make the configuration explicit, copy the example file:

```bash
cp .env.example .env
```

Edit `.env` only when needed. `GEMINI_API_KEY` switches the current model and embedding provider to Gemini. Without it, deterministic local providers are selected. `OPENAI_API_KEY` is present in configuration but there is no OpenAI provider wired into the current provider factory. Never commit real credentials. The default `SECRET_KEY` is development-only and must be replaced before any production deployment.

To use admin ingestion/publication routes locally, set `ADMIN_API_TOKEN` to a unique secret of at least 32 characters. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Admin routes fail closed if this setting is missing or too short. The shared token is a local/demo guard, not a substitute for production operator identity, role-based authorization, or a secret manager.

Apply the database migrations:

```bash
alembic upgrade head
```

The migration command creates the local SQLite database if it does not exist. Back up or point `DATABASE_URL` at a disposable database before testing schema changes against existing data.

## Test and Run

Run the complete automated suite:

```bash
pytest -q
```

Run focused quality checks when making changes:

```bash
ruff check .
mypy services
```

**Last verified (2026-10-20):** `ruff check .` and `mypy services` pass locally. The CI workflow runs those checks with the tests, OpenAPI snapshot check, and a disposable SQLite migration upgrade/downgrade cycle. Run these commands before submitting changes; local success does not mean the GitHub workflow has run for an unpushed branch.

Start the development API:

```bash
uvicorn services.api.main:app --reload
```

Useful local URLs:

| URL | Purpose |
|---|---|
| `http://127.0.0.1:8000/tv/` | TV client |
| `http://127.0.0.1:8000/docs` | Interactive API docs |
| `http://127.0.0.1:8000/health/live` | Process liveness response |
| `http://127.0.0.1:8000/health/ready` | Readiness response with database connectivity check |
| `http://127.0.0.1:8000/health/metrics` | In-process operational metrics |

The readiness endpoint runs a bounded `SELECT 1` against the configured database. It returns HTTP 503 and marks persistence unavailable when that check fails or times out. Liveness remains independent of database health.

## API Surface

See the [developer API reference](API_REFERENCE.md) for all routes, request/response fields, headers, status codes, examples, and known implementation caveats. FastAPI serves the live schema at `/openapi.json` and Swagger UI at `/docs`; regenerate the checked-in snapshot with `python ops/scripts/export_openapi.py` after API changes.

The product-level contract is in the [API requirements](../Rewind_Complete_Project_Documentation_Package/requirements/04_API_CONTRACT.md).

## Important Limitations

- Playback progress is manual. The app does not connect to Prime Video, Netflix, or other third-party playback systems.
- Only SRT and WebVTT subtitle assets are currently supported. Process only material you have permission to ingest and store.
- Viewer identity and admin authorization are local/demo-only. Production requests to viewer and admin routes fail closed with HTTP 503 until an identity provider and operator role model are selected and implemented. Do not expose the service to untrusted networks.
- Browser and automated tests do not prove compatibility on a physical Fire TV or Vega OS device. Record target-device or emulator results separately.
- The project is not approved for production launch. Track remaining work in the [implementation dashboard](development/IMPLEMENTATION_STATUS.md), [known issues](development/KNOWN_ISSUES.md), and [project checklist](../checklist.md).

## Troubleshooting

**`pip install -e ".[dev]"` fails:** Confirm you are at the repository root and that the active environment uses Python 3.11 or newer. The package finder is explicitly configured in `pyproject.toml` to include the `services` package.

**Imports fail when running tests:** Activate `.venv` in the current shell, then run `python -m pytest -q` to ensure pytest uses that environment.

**A title list is empty:** The catalog lists published titles with an active content index. An authorized subtitle asset must be ingested and its version published before it is available for Q&A. Follow the demo guide for the reproducible local journey.

**Gemini calls fail:** Check that `GEMINI_API_KEY` is set in the environment or `.env`. Leaving it unset selects the deterministic mock providers; it does not silently fall back after a configured Gemini request fails.

## Next References

- [Demo rehearsal guide](demo/DEMO_SCRIPT_AND_REHEARSAL_GUIDE.md)
- [Operational runbook](../ops/runbooks/OPERATIONAL_RUNBOOK.md)
- [Incident response](../ops/runbooks/INCIDENT_RESPONSE.md)
- [Product and engineering requirements index](../Rewind_Complete_Project_Documentation_Package/requirements/00_README.md)