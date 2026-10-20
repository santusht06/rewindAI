# Operational Runbook: Rewind Fire TV Story Companion

**System:** Rewind AI Story Companion Service  
**Version:** 1.0.0 (RC1)  
**Owners:** Engineering & Operations Team  
**Compliance & References:** `OPS-001`..`OPS-010`, `NFR-PERF-001`, `NFR-COST-001`, `NFR-DR-001`, `AC-016`

---

## 1. Architecture & Service Topology

Rewind is an AI story companion service designed for 10-foot Fire TV experiences. It consists of:
- **Backend API Service:** FastAPI asynchronous Python application running on Uvicorn.
- **Persistence Layer:** SQLite / PostgreSQL + pgvector storing movie catalogs, subtitle chunks, embeddings, viewing sessions, and tamper-evident audit logs.
- **AI/ML Layer:** Hybrid semantic + BM25 keyword retriever with server-side pre-retrieval temporal spoiler boundary enforcement.
- **TV Client:** High-contrast OLED 10-foot Web client (`apps/tv-client/`) mounted at `/tv` with full D-pad spatial remote navigation.

---

## 2. Configuration & Secrets Management

All secrets and environment variables are strictly managed server-side (`NFR-SEC-001`):
| Variable | Default (Dev) | Production Requirement | Purpose |
| :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | `development` | `production` | Enables strict CORS and hides docs |
| `DATABASE_URL` | `sqlite+aiosqlite:///./rewind_local.db` | PostgreSQL connection string | Primary persistent store |
| `SECRET_KEY` | `dev-insecure-secret...` | 32+ character random secret | Signs single-use spoiler nonces |
| `ADMIN_API_TOKEN` | None | No production role provider configured | Local/demo-only admin shared token; admin routes fail closed in production |
| `GEMINI_API_KEY` | None | Valid Google AI Studio / Vertex key | Primary LLM Provider |
| `OPENAI_API_KEY` | None | Valid OpenAI API key | Optional fallback LLM provider |
| `RATE_LIMIT_PER_MINUTE` | `60` | `30` - `60` per viewer/IP | Protects model against abuse |

---

## 3. Health Probes & Monitoring

Rewind exposes three lightweight, privacy-preserving HTTP health probes:

### 3.1 Liveness Probe (`GET /health/live`)
- **HTTP 200 OK:** Returns `{"status": "alive", "environment": "production", "timestamp": "..."}`.
- Used by orchestrators (Kubernetes / ECS / Systemd) for container lifecycle checks.

### 3.2 Readiness Probe (`GET /health/ready`)
- **HTTP 200 OK:** Returns `{"status": "ready", "components": {"config": "ready", "persistence": "ready"}}`.
- Validates database connectivity and configuration availability before routing viewer traffic.

### 3.3 Operational Metrics Probe (`GET /health/metrics` or `GET /metrics`)
- **HTTP 200 OK:** Returns real-time latency percentiles (`p50`, `p95`, `p99`), request volume, outcome distribution, token accounting, and estimated USD cost:
```json
{
  "timestamp": "2026-10-17T13:30:00Z",
  "total_requests": 1420,
  "outcomes": {
    "answered": 1280,
    "insufficient_evidence": 85,
    "spoiler_confirmation_required": 55
  },
  "latencies_ms": {
    "p50": {"question_answering": 380.5, "retrieval": 42.1},
    "p95": {"question_answering": 890.0, "retrieval": 95.4},
    "p99": {"question_answering": 1450.2, "retrieval": 180.0}
  },
  "tokens": {
    "prompt_tokens": 124500,
    "completion_tokens": 34100,
    "total_tokens": 158600
  },
  "estimated_cost_usd": 0.01956
}
```

---

## 4. SLOs & Alerting Thresholds

| Metric | Target SLO | Warning Alert | Critical Alert (SEV-2) |
| :--- | :--- | :--- | :--- |
| **Q&A Latency (p95)** | < 2500ms | > 2000ms for 5m | > 3500ms for 5m |
| **Retrieval Latency (p95)** | < 150ms | > 250ms for 5m | > 500ms for 5m |
| **HTTP 5xx Error Rate** | < 0.1% | > 0.5% for 3m | > 2.0% for 3m |
| **Rate Limit 429 Rate** | < 1.0% | > 3.0% for 5m | > 10.0% (possible DoS) |
| **Daily Cost Burn** | < $5.00/day | > $10.00 in 24h | > $25.00 in 24h |

---

## 5. Database Backup, Disaster Recovery & Integrity (`OPS-005`, `NFR-DR-001`)

Rewind includes an automated disaster recovery script: `ops/scripts/backup_restore.py`.

### 5.1 Creating a Verified Point-in-Time Backup
Run during scheduled daily cron or before major catalog changes:
```bash
python ops/scripts/backup_restore.py backup --db-path rewind_local.db --out-dir ops/backups
```
This performs:
1. Online, lock-safe atomic snapshot using SQLite Online Backup API.
2. Structural integrity validation via `PRAGMA integrity_check`.
3. Cryptographic SHA-256 calculation stored in `.json` manifest alongside table counts.

### 5.2 Restoring from Backup
```bash
python ops/scripts/backup_restore.py restore --backup-path ops/backups/rewind_backup_YYYYMMDD_HHMMSS.db --target-path rewind_local.db
```
The restore procedure:
1. Validates the backup SHA-256 against the recorded manifest.
2. Checks SQLite structural integrity on the source backup.
3. Atomically restores into a temporary file and validates before replacing the active database.

### 5.3 Database and Migration Scope

`ops/scripts/backup_restore.py` operates on SQLite files only. It is not a PostgreSQL
backup or restore tool. Before beta/production deployment, select the actual database
service and use its supported, tested backup and point-in-time recovery mechanism.
Do not treat a SQLite rehearsal as evidence for PostgreSQL recovery.

### 5.4 Deployment, Migration, and Rollback Rehearsal

The hosting platform, production database, identity provider, and deployment mechanism
have not been selected. The following is a release sequence to rehearse in the chosen
non-production environment; it is not evidence that a deployment has occurred:

1. Confirm the reviewed application artifact, environment configuration, operator access,
   and database-specific backup/restore procedure.
2. Capture and verify a pre-deployment backup using the target database's supported
   tooling. Record the artifact/revision, backup identifier, and verification result.
3. Run `alembic upgrade head` as a single controlled migration step before routing
   traffic to the new application version. Record the prior and resulting revisions.
4. Deploy the application artifact and verify `/health/live`, `/health/ready`, viewer
   authorization, and an approved end-to-end smoke journey before enabling traffic.
5. If smoke checks fail, stop or drain traffic and roll back the application artifact.
   Run an Alembic downgrade only after confirming the migration is compatible and the
   downgrade will not discard required data. If a database restore is required, use
   the verified target-database recovery procedure during a controlled maintenance
   window; do not overwrite a live database while application workers are active.
6. Repeat readiness and smoke checks, then record the incident/change identifier,
   migration revision, backup/recovery point, operator, timestamps, and results.

Do not mark the beta/production checklist item complete until this sequence has been
rehearsed against the selected target using non-production data and the evidence is
recorded. Local SQLite migration and backup tests do not substitute for that rehearsal.

---

## 6. Content Rights Revocation & Instant Unpublishing (`OPS-006`, `AC-016`)

If a studio or content owner issues a rights withdrawal or takedown request:

1. **Local/demo only until production admin identity is implemented**, invoke the Admin Unpublish API:
```bash
curl -X POST "http://localhost:8000/api/v1/admin/titles/{title_id}/unpublish" \
  -H "X-Admin-Token: $ADMIN_SECRET_TOKEN"
```
2. **Behavioral Invariants Enforced:**
   - The movie status is immediately transitioned to `draft`.
   - All content versions for this title are set to `is_active = False`.
   - Subtitle indexing is instantly disabled for this title.
   - Any ongoing or future user questions return `unsupported_title` safe response.
   - A permanent, tamper-evident audit record (`AuditAction.UNPUBLISH`) is committed to the database.
