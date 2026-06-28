# Production Concern: Database Integrity (Tier 0)

Focus: atomic writes, consistent state transitions, constraint enforcement, and prevention of corrupted/partial records.

## Release Blockers

1. **[FIXED] Multi-step `start-hunt` DB mutations are not atomic** (`backend/router.py`, `backend/db/database.py`)  
   Hunt creation and user-link insertion now run in one transactional unit in `start_hunt`, with rollback on failure before commit, preventing partial DB state for the core start-hunt write path.

2. **[FIXED] Workflow publish is outside DB transaction boundary** (`backend/router.py`, `backend/services/workflow_admission/workflow_admission.py`, `backend/orchestrator.py`)  
   Router no longer marks hunts as `processing` before workflow consumption; status transition to `processing` now occurs in orchestrator execution path, reducing publish-time stuck-state inconsistency from API write flow.

## High Severity

3. **[OPEN] Status transition rules are not constrained at DB level** (`backend/db/models/hunt.py`, `backend/db/database.py`)  
   `status` is free-text with no enum/check constraint, allowing invalid or impossible lifecycle states to be persisted.

4. **[OPEN] No DB-level integrity constraints for result quality fields** (`backend/db/models/hunt.py`)  
   `trust_score` has no range constraint (0-100), and completed-record metadata (`title`, `summary`, `trust_score`) is not enforced for completed hunts.

5. **[OPEN] `result` is stored as raw string without JSON validity guarantee** (`backend/db/models/hunt.py`, `backend/services/save_result_to_db/save_result_to_db.py`)  
   Invalid or malformed JSON strings can be persisted and later break consumers expecting valid structured result payloads.

6. **[OPEN] Failure update can overwrite successful terminal state semantics** (`backend/orchestrator.py`, `backend/db/database.py`)  
   Global exception path updates hunt to `failed` by `hunt_id` without strict transition checks, risking conflicting status/result combinations.

7. **[OPEN] No explicit transactional lock/serialization for per-hunt write flows** (`backend/db/database.py`)  
   Concurrent updates rely on optimistic patterns but lack row-level locking strategy for critical state writes.

8. **[OPEN] Schema-management strategy can drift integrity guarantees** (`backend/app.py`, Alembic files)  
   Runtime `Base.metadata.create_all(...)` combined with Alembic migrations can produce environment drift and mismatched constraints.

9. **[NEW] `workflow_admissions.hunt_id` is not foreign-key constrained to `hunts.id`** (`backend/db/models/workflow_admission.py`, `backend/alembic/versions/d4e7f21c8a9b_add_workflow_admissions_table.py`)  
   Admission rows can become orphaned from hunts because referential linkage is not enforced at DB level.

## Important Integrity Gaps

10. **[OPEN] No DB check constraints on string-domain fields** (`backend/db/models/hunt.py`)  
   `platform` and `status` accept arbitrary values, weakening consistency and downstream assumptions.

11. **[OPEN] Cross-entity consistency is application-enforced, not DB-enforced** (`backend/db/models/hunt_user.py`, external auth identity model)  
   `hunt_users.user_id` has no FK to an internal users table (if one exists later), so referential consistency depends entirely on app logic.

12. **[OPEN] Write methods commit immediately, preventing grouped rollback semantics** (`backend/db/database.py`)  
   Database API methods each call `session.commit()`, making it hard to guarantee all-or-nothing behavior across related operations.

13. **[OPEN] No explicit migration-level backfill constraints for legacy rows** (Alembic + current model expectations)  
   App expects metadata for completed hunts, but DB model/migrations do not enforce it, allowing legacy partial records to persist.

14. **[NEW] `workflow_admissions` can store internally inconsistent linkage fields** (`backend/db/models/workflow_admission.py`, `backend/services/workflow_admission/workflow_admission.py`)  
   Both `hunt_id` and `video_link` are stored, but DB has no constraint ensuring the `video_link` matches the referenced hunt record, allowing contradictory admission rows under bad writes.
