# Requirements Traceability Matrix (RTM) — Rewind

**Version:** 1.0  
**Project:** Rewind — Fire TV AI Story Companion  
**Status:** Phase 0 Baseline  

This matrix maps every functional requirement (SRS), non-functional requirement (NFR), and acceptance scenario (AC) from the authoritative specification package to Agile epics, implementation tasks, target test suites, and verification status.

---

## 1. Functional Requirements (SRS)

| Req ID | Category | Requirement Summary | Agile Epic / Task | Target Test Suite | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SRS-CAT-001** | Catalog | List only titles marked published & available to user | EPIC-02 / TASK-02-01 | `test_catalog_published_filter` | BACKLOG |
| **SRS-CAT-002** | Catalog | Stable internal ID distinct from display name | EPIC-01 / TASK-01-02 | `test_title_entity_invariants` | BACKLOG |
| **SRS-CAT-003** | Catalog | Distinguish unsupported title, unready index, & transient error | EPIC-02 / TASK-02-02 | `test_catalog_status_distinction` | BACKLOG |
| **SRS-SES-001** | Sessions | Every question associated with valid session & title | EPIC-04 / TASK-04-01 | `test_question_session_binding` | BACKLOG |
| **SRS-SES-002** | Sessions | Backend validates session ownership on private operations | EPIC-02 / TASK-02-03 | `test_session_ownership_idor` | BACKLOG |
| **SRS-SES-003** | Sessions | Record progress source (`verified`, `manual`, `unknown`) & timestamp | EPIC-02 / TASK-02-04 | `test_session_progress_provenance` | BACKLOG |
| **SRS-SES-004** | Sessions | Unknown or stale progress NOT treated as verified | EPIC-02 / TASK-02-04 | `test_unknown_progress_enforcement` | BACKLOG |
| **SRS-QA-001** | Q&A | Questions size-limited & validated server-side | EPIC-04 / TASK-04-01 | `test_question_validation_limits` | BACKLOG |
| **SRS-QA-002** | Q&A | Retrieval applies title, publication, auth & spoiler filters BEFORE LLM | EPIC-04 / TASK-04-02 | `test_retrieval_pre_filter_invariants` | BACKLOG |
| **SRS-QA-003** | Q&A | Bounded token/chunk budget; never full transcript into LLM | EPIC-04 / TASK-04-03 | `test_context_builder_budget_cap` | BACKLOG |
| **SRS-QA-004** | Q&A | Answer generation uses only permitted evidence for plot claims | EPIC-04 / TASK-04-04 | `test_grounded_answer_generation` | BACKLOG |
| **SRS-QA-005** | Q&A | Plot claims map to evidence chunks / timestamps | EPIC-04 / TASK-04-04 | `test_citation_mapping` | BACKLOG |
| **SRS-QA-006** | Q&A | Abstain or clarify if evidence is absent, contradictory, or future | EPIC-04 / TASK-04-05 | `test_qa_abstention_behavior` | BACKLOG |
| **SRS-QA-007** | Q&A | Validate citations against retrieved set; reject hallucinations | EPIC-04 / TASK-04-05 | `test_citation_validation_defense` | BACKLOG |
| **SRS-QA-008** | Q&A | Client distinguishes grounded answer, clarification, error, unready | EPIC-06 / TASK-06-03 | `test_client_response_contracts` | BACKLOG |
| **SRS-QA-009** | Q&A | LLM output treated as untrusted; schema-validated before rendering | EPIC-04 / TASK-04-04 | `test_llm_output_schema_validation` | BACKLOG |
| **SRS-SPO-001** | Spoilers | Policy enforced server-side, not in client or LLM prompt | EPIC-05 / TASK-05-01 | `test_server_side_spoiler_gate` | BACKLOG |
| **SRS-SPO-002** | Spoilers | Retrieval filters strictly by trusted playback boundary | EPIC-05 / TASK-05-01 | `test_spoiler_boundary_filtering` | BACKLOG |
| **SRS-SPO-003** | Spoilers | Unknown progress requires confirmation; no auto-sync assumption | EPIC-05 / TASK-05-02 | `test_unknown_progress_clarification` | BACKLOG |
| **SRS-SPO-004** | Spoilers | Spoiler confirmation explicit, scoped, server-validated nonce | EPIC-05 / TASK-05-03 | `test_spoiler_confirmation_flow` | BACKLOG |
| **SRS-SPO-005** | Spoilers | Question asking future events does not grant consent | EPIC-05 / TASK-05-03 | `test_adversarial_question_spoiler_bypass` | BACKLOG |
| **SRS-SPO-006** | Spoilers | Adversarial tests: recap, indirect twists, prompt injection | EPIC-05 / TASK-05-04 | `test_adversarial_spoiler_suite` | BACKLOG |
| **SRS-ING-001** | Ingestion | Only authorized subtitle/transcript assets ingested | EPIC-03 / TASK-03-01 | `test_asset_authorization_check` | BACKLOG |
| **SRS-ING-002** | Ingestion | Idempotent for same source/version/fingerprint | EPIC-03 / TASK-03-02 | `test_ingestion_idempotency` | BACKLOG |
| **SRS-ING-003** | Ingestion | Invalid timestamps, empty files, bad encoding fail explicitly | EPIC-03 / TASK-03-01 | `test_ingestion_malformed_inputs` | BACKLOG |
| **SRS-ING-004** | Ingestion | Staged indexing; incomplete indexes never visible as published | EPIC-03 / TASK-03-03 | `test_staged_indexing_isolation` | BACKLOG |
| **SRS-ING-005** | Ingestion | Atomic version switch with rollback path to previous index | EPIC-03 / TASK-03-03 | `test_atomic_index_switch_rollback` | BACKLOG |
| **SRS-ING-006** | Ingestion | Content deletion tombstones chunks, embeddings, caches | EPIC-03 / TASK-03-04 | `test_content_unpublish_purge` | BACKLOG |
| **SRS-ING-007** | Ingestion | Audit runs with source checksum, chunk count, model/parser ver | EPIC-03 / TASK-03-02 | `test_ingestion_audit_metrics` | BACKLOG |
| **SRS-ADM-001** | Admin | Administrative operations require separate authorization | EPIC-02 / TASK-02-05 | `test_admin_auth_boundary` | BACKLOG |
| **SRS-ADM-002** | Admin | High-impact actions (publish, reindex, purge) audited | EPIC-02 / TASK-02-05 | `test_admin_audit_logging` | BACKLOG |
| **SRS-ADM-003** | Admin | Health/readiness checks without leaking credentials/secrets | EPIC-01 / TASK-01-03 | `test_health_and_readiness_probes` | BACKLOG |

---

## 2. Non-Functional Requirements (NFR)

| Req ID | Category | Requirement Summary | Agile Epic / Task | Target Test Suite | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **NFR-REL-001** | Reliability | LLM failure returns controlled fallback; no fake success | EPIC-04 / TASK-04-06 | `test_rag_and_spoiler_controls.py` | `VERIFIED` |
| **NFR-REL-002** | Reliability | Bounded timeouts, retries, cancellation for external calls | EPIC-04 / TASK-04-06 | `test_rag_and_spoiler_controls.py` | `VERIFIED` |
| **NFR-REL-003** | Reliability | Retried writes idempotent via idempotency keys | EPIC-02 / TASK-02-04 | `test_domain_and_persistence.py` | `VERIFIED` |
| **NFR-SEC-001** | Security | Secrets stored server-side; never shipped in TV client | EPIC-01 / TASK-01-01 | `test_config.py` | `VERIFIED` |
| **NFR-SEC-002** | Security | Parameterized SQL / safe ORM queries; no raw injection | EPIC-01 / TASK-01-02 | `test_domain_and_persistence.py` | `VERIFIED` |
| **NFR-SEC-003** | Security | Strict authorization checked at every trust boundary | EPIC-02 / TASK-02-03 | `test_api_v1_endpoints.py` | `VERIFIED` |
| **NFR-PRIV-001**| Privacy | Logs exclude credentials, raw tokens, unnecessary text | EPIC-01 / TASK-01-01 | `test_logging.py` | `VERIFIED` |
| **NFR-PERF-001**| Performance | Latency p50/p95/p99 measured and instrumented | EPIC-07 / TASK-07-02 | `test_performance_benchmarks` | BACKLOG |
| **NFR-SCALE-001**| Scalability | Stateless API server instances | EPIC-01 / TASK-01-03 | `test_stateless_api_concurrency` | BACKLOG |
| **NFR-OBS-001** | Observability | Correlation/Request ID on every request, trace, log | EPIC-01 / TASK-01-01 | `test_health_and_errors.py` | `VERIFIED` |
| **NFR-ACC-001** | Accessibility | Remote-only D-pad navigation; visible focus; 10-ft UI | EPIC-06 / TASK-06-01 | `test_tv_client.py` | `VERIFIED` |
| **NFR-MAINT-001**| Maintainability| Versioned API (`/api/v1`) & reversible database migrations | EPIC-01 / TASK-01-02 | `test_domain_and_persistence.py` | `VERIFIED` |
| **NFR-DR-001**  | DR | Documented recovery, backup, and index rebuild workflows | EPIC-07 / TASK-07-03 | `test_disaster_recovery_plan` | BACKLOG |
| **NFR-COST-001**| Cost | Token usage & embedding costs tracked per request | EPIC-04 / TASK-04-06 | `services/api/ai/provider.py` | `VERIFIED` |

---

## 3. Acceptance Criteria Scenarios (AC)

| AC ID | Title | Summary | Target Implementation | Test Case | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AC-001** | Supported Title | Published title with active index reports questions available | Catalog & Session API | `test_api_v1_endpoints.py` | `VERIFIED` |
| **AC-002** | Unsupported Title | Unsupported title explains limitation; does NOT invoke LLM | Catalog & Session API | `test_api_v1_endpoints.py` | `VERIFIED` |
| **AC-003** | Unknown Progress | Unknown progress requests confirmation; no silent full access | Session & Spoiler Engine | `test_api_v1_endpoints.py` | `VERIFIED` |
| **AC-004** | Future Evidence | Retrieval strictly excludes evidence beyond position boundary | Spoiler Filter & Retrieval | `test_rag_and_spoiler_controls.py` | `VERIFIED` |
| **AC-005** | Grounded Answer | Permitted evidence produces grounded answer with chunk citations | RAG Orchestrator | `test_rag_and_spoiler_controls.py` | `VERIFIED` |
| **AC-006** | Insufficient Evidence | Insufficient evidence returns abstention/clarification | RAG Orchestrator | `test_rag_and_spoiler_controls.py` | `VERIFIED` |
| **AC-007** | Fake Citation | Model-hallucinated chunk ID is rejected by server | Answer Validator | `test_rag_and_spoiler_controls.py` | `VERIFIED` |
| **AC-008** | Prompt Injection | Malicious instruction in subtitle treated as data, not instruction | Prompt Builder & Guard | `test_rag_and_spoiler_controls.py` | `VERIFIED` |
| **AC-009** | Spoiler Confirmation | Spoiler question triggers warning & server-side confirmation | Spoiler Policy Engine | `test_rag_and_spoiler_controls.py` | `VERIFIED` |
| **AC-010** | Forged Consent | Client flag `spoilers=true` without server nonce is rejected | Spoiler Policy Engine | `test_api_v1_endpoints.py` | `VERIFIED` |
| **AC-011** | Cross-User Access | User B cannot access User A's session or questions | Auth & Session Security | `test_api_v1_endpoints.py` | `VERIFIED` |
| **AC-012** | Idempotent Ingestion | Re-submitting same asset does not duplicate chunks | Ingestion Worker | `test_ingestion_pipeline.py` | `VERIFIED` |
| **AC-013** | Failed Reindex | Staging index failure leaves last good index active | Index Manager | `test_ingestion_pipeline.py` | `VERIFIED` |
| **AC-014** | Cache Policy Correctness | Stricter policy/progress cannot hit full-spoiler cached answer | Cache Key Generator | `test_ac014_cache_policy_isolation` | BACKLOG |
| **AC-015** | Provider Outage | LLM timeout returns controlled retryable error, no hallucination | LLM Adapter | `test_rag_and_spoiler_controls.py` | `VERIFIED` |
| **AC-016** | Rights Revocation | Revoking authorization unpublishes title and invalidates cache | Rights / Admin Service | `test_api_v1_endpoints.py` | `VERIFIED` |
| **AC-017** | Remote-Only TV Use | TV remote D-pad allows complete journey from title to answer | TV Web / Client App | `test_tv_client.py` & `test_e2e_user_journeys.py` | `VERIFIED` |
| **AC-018** | Concurrent Publish | Concurrent index publishes resolve to exactly one active index | Index Manager | `test_ingestion_pipeline.py` | `VERIFIED` |
| **AC-019** | Malformed Timestamps | Reversed/corrupt timestamps rejected at ingestion | Ingestion Parser | `test_ingestion_pipeline.py` | `VERIFIED` |
| **AC-020** | Logging Privacy | Secrets & sensitive question text redacted from logs | Logging Middleware | `test_logging.py` | `VERIFIED` |
