# Production Concern: Database Integrity (Tier 0)

Focus: atomic writes, consistent state transitions, constraint enforcement, and prevention of corrupted/partial records.

## Release Blockers

1. **Multi-step `start-hunt` DB mutations are not atomic** (`backend/router.py`, `backend/db/database.py`)  
   Hunt creation, user-link insertion, metadata updates, and status transitions are committed in separate DB operations; mid-flow failures can leave partial state.

2. **Workflow publish is outside DB transaction boundary** (`backend/router.py`)  
   Hunt may be committed as `processing` even when workflow publish fails, creating stuck/inconsistent records.

3. **Status transition rules are not constrained at DB level** (`backend/db/models/hunt.py`, `backend/db/database.py`)  
   `status` is free-text with no enum/check constraint, allowing invalid or impossible lifecycle states to be persisted.

## High Severity

4. **No DB-level integrity constraints for result quality fields** (`backend/db/models/hunt.py`)  
   `trust_score` has no range constraint (0-100), and completed-record metadata (`title`, `summary`, `trust_score`) is not enforced for completed hunts.

5. **`result` is stored as raw string without JSON validity guarantee** (`backend/db/models/hunt.py`, `backend/services/save_result_to_db/save_result_to_db.py`)  
   Invalid or malformed JSON strings can be persisted and later break consumers expecting valid structured result payloads.

6. **Failure update can overwrite successful terminal state semantics** (`backend/orchestrator.py`, `backend/db/database.py`)  
   Global exception path updates hunt to `failed` by `hunt_id` without strict transition checks, risking conflicting status/result combinations.

7. **No explicit transactional lock/serialization for per-hunt write flows** (`backend/db/database.py`)  
   Concurrent updates rely on optimistic patterns but lack row-level locking strategy for critical state writes.

8. **Schema-management strategy can drift integrity guarantees** (`backend/app.py`, Alembic files)  
   Runtime `Base.metadata.create_all(...)` combined with Alembic migrations can produce environment drift and mismatched constraints.

## Important Integrity Gaps

9. **No DB check constraints on string-domain fields** (`backend/db/models/hunt.py`)  
   `platform` and `status` accept arbitrary values, weakening consistency and downstream assumptions.

10. **Cross-entity consistency is application-enforced, not DB-enforced** (`backend/db/models/hunt_user.py`, external auth identity model)  
   `hunt_users.user_id` has no FK to an internal users table (if one exists later), so referential consistency depends entirely on app logic.

11. **Write methods commit immediately, preventing grouped rollback semantics** (`backend/db/database.py`)  
   Database API methods each call `session.commit()`, making it hard to guarantee all-or-nothing behavior across related operations.

12. **No explicit migration-level backfill constraints for legacy rows** (Alembic + current model expectations)  
   App expects metadata for completed hunts, but DB model/migrations do not enforce it, allowing legacy partial records to persist.
