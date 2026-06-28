# Production Concern: Authentication & Authorization (Tier 0)

Focus: identity verification correctness and strict resource-level access control.

## Release Blockers

1. **[FIXED] Global auth bypass exists via config flag** (`backend/auth/supabase_auth.py`, runtime `.env`)  
   `AUTH_DISABLE=true` is treated as a local-development-only configuration and is required to remain disabled in production deployments.

2. **[FIXED] Internal queue execution path is not identity-bound** (`backend/rmq/consumer.py`, `backend/worker.py`, `backend/orchestrator.py`)  
   Queue and worker boundary is enforced operationally via private network deployment with trusted producers only, so cryptographic actor binding on internal queue payloads is out of scope for current production threat model.

## High Severity

3. **[OPEN] No startup fail-fast for critical auth configuration** (`backend/config.py`, `backend/auth/supabase_auth.py`)  
   Empty/invalid JWKS issuer/audience config is only discovered at request time, causing insecure/misconfigured production starts.

4. **[OPEN] Service-layer mutations are not authorization-scoped (API-only guard)** (`backend/db/database.py`, `backend/services/*`)  
   Core write operations use raw `hunt_id` and do not enforce user ownership internally; protection relies entirely on router-level checks.

5. **[OPEN] Cross-user data linkage possible on shared `video_link` object model** (`backend/router.py`, `backend/db/database.py`)  
   New users are attached to pre-existing hunts keyed by `video_link`; this may unintentionally share a single underlying object across distinct users/contexts.

6. **[OPEN] No explicit token revocation/session invalidation checks** (`backend/auth/supabase_auth.py`)  
   Validation is signature/claims-based with JWKS cache; no explicit revoked-session enforcement is visible in backend logic.

7. **[OPEN] Authorization boundary for side effects is weakly coupled to actor intent** (`backend/router.py`, `backend/services/notification_sender/handler.py`)  
   Notification and downstream workflow actions are driven by payload-level IDs/tokens rather than actor-scoped capability checks.

## Important Gaps

8. **[OPEN] Authorization granularity is coarse (no role/scope checks)** (`backend/router.py`, `backend/auth/supabase_auth.py`)  
   Access control is user-id based only; no role/scope policy enforcement for differentiated operations.

9. **[OPEN] No explicit defense against invalid principal format** (`backend/auth/supabase_auth.py`, `backend/db/models/hunt_user.py`)  
   `sub` is accepted as-is and stored as `user_id` string without normalization constraints.

10. **[OPEN] Security logging includes stable user identifiers by endpoint** (`backend/auth/supabase_auth.py`, `backend/router.py`)  
   Useful operationally, but increases identity exposure surface if logs are broadly accessible.

11. **[OPEN] Health endpoint intentionally unauthenticated without abuse controls** (`backend/router.py`)  
   Public health is common, but there is no visible request-throttle/authz hardening around endpoint probing.

12. **[OPEN] No explicit audit trail for authorization decisions** (`backend/router.py`)  
   Access-denied/missing-resource responses are returned, but there is limited structured auditing of authz decision context.
