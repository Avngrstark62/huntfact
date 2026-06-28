# Production Concern: Security (Tier 0)

Focus: auth hardening, secret safety, trust boundaries, injection/SSRF risk, and sensitive data exposure.

## Release Blockers

1. **[FIXED] Live secrets are present in backend source files** (`backend/.env`, `backend/serviceAccountKey.json`, `backend/.gitignore`)  
   Local secret files are ignored from version control (`.env`, `serviceAccountKey.json`), preventing accidental commit in the current workflow.

2. **[FIXED] Authentication can be globally bypassed via config** (`backend/auth/supabase_auth.py`, `backend/.env`)  
   `AUTH_DISABLE` is intentionally used for local development and is operationally required to be disabled in deployment environments.

3. **[FIXED] Untrusted URL input reaches network-fetching primitives without private-network guardrails** (`backend/schemas.py`, `backend/config.py`, `backend/.env.example`, `backend/services/audio_extractor/audio_extractor.py`)  
   `cdn_link` is now validated at request schema boundary against an explicit CDN hostname allowlist (configurable suffixes), rejecting non-allowed hosts before any backend-side fetch behavior.

4. **[FIXED] No security boundary on queue payload producers** (`backend/rmq/consumer.py`, `backend/worker.py`, `backend/rmq/schemas.py`)  
   Queue and worker security boundary is enforced operationally via private network deployment (no public exposure of RabbitMQ/worker/orchestrator/chroma services), making untrusted producer access out of scope for current deployment.

## High Severity

5. **[OPEN] Sensitive tokens are logged in plaintext** (`backend/services/notification_sender/notification_sender.py`)  
   Full `fcm_token` is logged, which is sensitive device-routing data and should be redacted.

6. **[OPEN] Large model outputs and workflow payload fragments are logged** (`backend/orchestrator.py`)  
   Logging translated text/claim extraction and message-body snippets increases risk of leaking user content and internal data.

7. **[OPEN] Default weak infrastructure credentials in config templates** (`backend/.env.example`, `backend/config.py`)  
   Default `guest:guest` RabbitMQ and local DB-style credentials encourage insecure deployments when copied to production.

8. **[OPEN] No host-level policy for external fetch targets** (`backend/services/audio_extractor/audio_extractor.py`, `backend/services/firecrawl/firecrawl.py`)  
   URL validation is mostly syntactic; there is no enforcement of allowed domains or denial of local/link-local metadata endpoints.

9. **[OPEN] Internal exception text is propagated in task error payloads** (`backend/worker.py`, multiple handlers)  
   Raw `str(e)` is returned in structured errors, risking internal detail leakage across system boundaries.

## Important Security Gaps

10. **[OPEN] JWT auth policy is configuration-fragile** (`backend/config.py`, `backend/auth/supabase_auth.py`)  
   Critical auth fields are not fail-fast validated at startup, making secure posture dependent on runtime config hygiene.

11. **[OPEN] No explicit anti-abuse or request-throttling controls at API boundary** (`backend/router.py`)  
   Missing abuse controls increases brute-force/resource-exhaustion risk (security + availability impact).

12. **[OPEN] No explicit content sanitization boundary before LLM usage of web content** (`backend/services/web_scraper/web_scraper.py`, `backend/services/claim_verifier/claim_verifier.py`)  
   Untrusted scraped text is fed into model context, increasing prompt-injection exposure risk.

13. **[OPEN] Security posture depends heavily on environment secrecy rather than code-enforced policy** (pipeline-wide)  
   Strong runtime safeguards (network egress policy, secret manager usage, queue isolation) are not enforced in-app.
