# Incident Response Playbook: Rewind Fire TV Story Companion

**System:** Rewind AI Story Companion Service  
**Version:** 1.0.0 (RC1)  
**Owners:** Security, AI Safety, & DevOps On-Call Team  
**Compliance & References:** `OPS-008`, `BE-SAFE-001`..`BE-SAFE-010`, `AC-009`, `AC-016`

---

## 1. Incident Classification & Severity Matrix

| Severity | Definition | Target Response | Target Resolution | Examples |
| :--- | :--- | :--- | :--- | :--- |
| **SEV-1 (Critical)** | Core safety invariant violated or total service outage | < 15 minutes | < 2 hours | Spoiler content served in SAFE mode (`AC-004`), authentication bypass, complete database corruption |
| **SEV-2 (High)** | Major degradation affecting user experience | < 30 minutes | < 6 hours | Model provider 503/timeout (> 5%), p95 latency > 3500ms, rate limiter misfire |
| **SEV-3 (Medium)** | Minor or isolated operational failure | < 2 hours | < 24 hours | Subtitle asset parsing error during admin ingestion, telemetry aggregation delay |

---

## 2. On-Call Roles & Escalation Path

- **Incident Commander (IC):** Coordinates triage, directs containment, and manages status communication.
- **Lead Investigator (Safety/Backend):** Inspects server audit logs, validates query parameters, and verifies spoiler boundaries.
- **Operations Engineer:** Manages service restarts, traffic routing, backups, and provider failover.

---

## 3. SEV-1 Playbook: Potential Spoiler Policy Breach (`AC-004`, `SRS-SPO-001`)

If a viewer reports receiving dialogue or plot details occurring after their playback position:

### Step 1: Immediate Containment (Stop the Bleed)
1. Force all active viewing sessions back to `SAFE` mode:
   ```sql
   UPDATE viewing_sessions 
   SET spoiler_mode = 'safe', full_spoilers_confirmed = 0, spoiler_confirmation_nonce = NULL;
   ```
2. If isolated to a specific title, immediately unpublish the title index:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/admin/titles/{title_id}/unpublish" -H "X-Admin-Token: $ADMIN_TOKEN"
   ```

### Step 2: Investigation & Evidence Collection
1. Fetch the request ID from the user report or client logs:
   ```bash
   grep "req_abc123" /var/log/rewind/app.log
   ```
2. Inspect the audit log record in `audit_events`:
   ```sql
   SELECT * FROM audit_events WHERE target_id = 'question_id_here';
   ```
3. Check the maximum temporal boundary passed to `SubtitleRetriever`:
   - Verify `max_boundary_seconds <= session.current_position_seconds`.
   - Verify no future chunks were passed into `candidates` list.

### Step 3: Resolution & Verification
1. Run adversarial spoiler regression suite:
   ```bash
   pytest tests/test_rag_and_spoiler_controls.py -v
   ```
2. Confirm zero future chunk leakage before restoring title to published state.

---

## 4. SEV-2 Playbook: Model Provider Outage or High Latency

If Gemini / OpenAI returns 5xx or response times exceed 3000ms:

1. **Verify Provider Status:**
   - Check Google AI Studio or OpenAI status dashboards.
   - Inspect `/health/metrics` to isolate `model_inference` vs `retrieval` latency.
2. **Enable Provider Fallback:**
   - If Gemini is failing and `OPENAI_API_KEY` is configured, switch `MODEL_PROVIDER=openai` in `.env` and restart worker.
   - If all external providers are down, the service will gracefully fall back to the safe abstention response:
     `"No relevant dialogue or scene details have occurred yet up to your current playback position."`
3. **Protect Downstream with Rate Limiting:**
   - Lower `RATE_LIMIT_PER_MINUTE` to 20 to protect queue from cascading retry storms.

---

## 5. SEV-1 / SEV-2 Playbook: Copyright Revocation / Takedown Request (`AC-016`)

Upon receiving an authorized takedown notice:
1. Identify the internal `movie_id` associated with the rights claim.
2. Issue the immediate unpublish request:
   ```bash
   python -c "
   import asyncio
   from services.api.infrastructure.database import async_session_factory
   from services.api.infrastructure.repositories import MovieRepository, ContentVersionRepository
   from services.api.domain.models import MovieStatus

   async def revoke():
       async with async_session_factory() as session:
           m_repo = MovieRepository(session)
           v_repo = ContentVersionRepository(session)
           await v_repo.deactivate_all_versions('TARGET_MOVIE_ID')
           await m_repo.update_status('TARGET_MOVIE_ID', MovieStatus.DRAFT)
           await session.commit()
   asyncio.run(revoke())
   "
   ```
3. Verify `GET /api/v1/titles` no longer lists the title as available.

---

## 6. Post-Mortem & Root Cause Analysis (RCA) Requirements

Every SEV-1 and SEV-2 requires an RCA within 48 hours containing:
- **Timeline:** Timestamped log of detection, notification, containment, and resolution.
- **Root Cause:** Deep technical analysis (5 Whys).
- **Corrective Actions:** Code fixes, added unit/integration tests, or architectural safeguards.
