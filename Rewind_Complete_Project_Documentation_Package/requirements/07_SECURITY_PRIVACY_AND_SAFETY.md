# 07 — Security, Privacy and Safety

## 1. Threat model
Protect accounts/sessions, authorized content, questions and answers, administrative actions, API credentials, model-provider credentials, and system integrity. Threats include unauthorized access, session IDOR, prompt injection through transcripts, spoiler bypass, malicious ingestion files, rate abuse, cache leakage, provider outages, data leakage in logs, dependency compromise and unauthorized content processing.

## 2. Identity and authorization
- Use an established identity solution where appropriate; do not invent cryptography.
- Validate token signature, issuer, audience, expiry and relevant claims.
- Authorize each session/title/admin action on the server.
- Use least privilege and separate viewer/admin roles.
- Rotate/revoke credentials and keep secrets out of source control, images and client bundles.
- If cookie auth is used, implement secure cookie attributes and CSRF protection as applicable.
- Do not expose whether a private resource exists when that would create an enumeration risk.

## 3. Content rights and governance
- Ingest only assets with documented authorization and permitted processing/storage scope.
- Track rights state and provenance; unpublish or delete content when authorization expires or is revoked.
- Do not bypass DRM, scrape protected playback streams, or redistribute source captions.
- Define retention, deletion, backup and audit requirements before production.
- Limit admin access to raw source assets and transcripts.

## 4. AI safety and prompt injection
- Retrieved transcript text is untrusted data, not instructions.
- Never allow transcript content to change system policy, authorize spoilers, request secrets, or trigger tools.
- Keep policy enforcement outside the LLM.
- Filter unauthorized/future evidence before prompt construction.
- Schema-validate outputs and verify citation IDs against retrieved evidence.
- Do not execute model-generated SQL, shell commands, code or arbitrary URLs.
- Use adversarial tests for instructions embedded in dialogue, quoted text, character names and metadata.
- When uncertain, abstain rather than infer unsupported plot details.

## 5. Spoiler safety
- The server owns spoiler policy.
- Unknown progress is not equivalent to zero, current time, or full access.
- A user question requesting a future event is not confirmation.
- Confirmation flow must be deliberate, scoped, auditable and server-validated.
- Test indirect leaks: “is this character trustworthy?”, “who is the masked person?”, summaries, hints, comparisons and answers that imply a future death/reveal.
- Be transparent that no design can guarantee perfect prevention; treat any confirmed leak as a release-blocking defect.

## 6. Data privacy
- Minimize collection and retention of raw questions, answers, voice data and viewing history.
- Do not store audio unless explicitly required, consented to and protected.
- Redact secrets and personal data from logs.
- Apply access controls to analytics and audit events.
- Document data export/deletion behavior and its limits, including backups and legal retention.
- Use synthetic or sanitized data in development and tests.
- Do not use user content for model training unless a separate, explicit and lawful policy allows it.

## 7. API and infrastructure controls
- TLS in deployed environments.
- Strict request size/type validation and rate limits.
- Parameterized queries, safe ORM usage, output encoding and secure headers where applicable.
- Validate upload types by content and size, not filename alone; isolate parsers and scan assets where appropriate.
- Restrict egress from workers where feasible.
- Patch dependencies; generate and review a software bill of materials where appropriate.
- Separate environments and accounts.
- Backups encrypted and restore-tested.
- Admin operations require audit and, for destructive actions, explicit confirmation.

## 8. Incident response
Maintain runbooks for suspected spoiler leak, credential exposure, unauthorized content, data breach, provider outage, corrupted index and runaway cost. Include containment, disable/rollback procedure, evidence preservation, notification/escalation requirements and post-incident review. Legal notification obligations depend on jurisdiction and must be reviewed by qualified counsel.

## 9. Security release gate
No production release with known critical/high exploitable findings, secrets in repository/client bundle, broken ownership checks, unbounded expensive endpoints, untested destructive migrations, or known spoiler-policy bypass.
