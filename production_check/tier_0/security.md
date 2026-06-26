# Production Concern: Security (Tier 0)

Focus: auth hardening, secret safety, trust boundaries, injection/SSRF risk, and sensitive data exposure.

## Release Blockers

1. **Live secrets are present in backend source files** (`backend/.env`, `backend/serviceAccountKey.json`)  
   API keys and private credentials in repo are immediate compromise risk and must be rotated/removed before launch.

2. **Authentication can be globally bypassed via config** (`backend/auth/supabase_auth.py`, `backend/.env`)  
   `AUTH_DISABLE=true` fully bypasses auth checks and enables unauthorized access to protected endpoints.

3. **Untrusted URL input reaches network-fetching primitives without private-network guardrails** (`backend/schemas.py`, `backend/services/audio_extractor/audio_extractor.py`, `backend/orchestrator.py`)  
   User-controlled `cdn_link`/URL-derived inputs can trigger backend-side fetch behavior (FFmpeg/network) without SSRF protections (private IP/blocklist/allowlist).

4. **No security boundary on queue payload producers** (`backend/rmq/consumer.py`, `backend/worker.py`, `backend/rmq/schemas.py`)  
   Worker executes task payloads from queue without message authenticity checks/signing; if queue is reachable, attacker-crafted jobs can trigger internal actions.

## High Severity

5. **Sensitive tokens are logged in plaintext** (`backend/services/notification_sender/notification_sender.py`)  
   Full `fcm_token` is logged, which is sensitive device-routing data and should be redacted.

6. **Large model outputs and workflow payload fragments are logged** (`backend/orchestrator.py`)  
   Logging translated text/claim extraction and message-body snippets increases risk of leaking user content and internal data.

7. **Default weak infrastructure credentials in config templates** (`backend/.env.example`, `backend/config.py`)  
   Default `guest:guest` RabbitMQ and local DB-style credentials encourage insecure deployments when copied to production.

8. **No host-level policy for external fetch targets** (`backend/services/audio_extractor/audio_extractor.py`, `backend/services/firecrawl/firecrawl.py`)  
   URL validation is mostly syntactic; there is no enforcement of allowed domains or denial of local/link-local metadata endpoints.

9. **Internal exception text is propagated in task error payloads** (`backend/worker.py`, multiple handlers)  
   Raw `str(e)` is returned in structured errors, risking internal detail leakage across system boundaries.

## Important Security Gaps

10. **JWT auth policy is configuration-fragile** (`backend/config.py`, `backend/auth/supabase_auth.py`)  
   Critical auth fields are not fail-fast validated at startup, making secure posture dependent on runtime config hygiene.

11. **No explicit anti-abuse or request-throttling controls at API boundary** (`backend/router.py`)  
   Missing abuse controls increases brute-force/resource-exhaustion risk (security + availability impact).

12. **No explicit content sanitization boundary before LLM usage of web content** (`backend/services/web_scraper/web_scraper.py`, `backend/services/claim_verifier/claim_verifier.py`)  
   Untrusted scraped text is fed into model context, increasing prompt-injection exposure risk.

13. **Security posture depends heavily on environment secrecy rather than code-enforced policy** (pipeline-wide)  
   Strong runtime safeguards (network egress policy, secret manager usage, queue isolation) are not enforced in-app.
