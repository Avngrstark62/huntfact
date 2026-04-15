# Important Considerations

## A. State Consistency
Currently, Redis operations in `helpers.py` are:
- **Atomic for single commands** (SET, GET are atomic)
- **NOT atomic for sequences** (GET → modify → SET can have race conditions)

**Question for you:** Will multiple steps run in parallel, or always sequentially?
- **Sequential**: No issue, one step at a time
- **Parallel**: You might need locking mechanisms (Redis has WATCH/MULTI for transactions)

## B. Error Handling & Rollback
What happens if a step fails midway?
- Data is already modified in Redis
- No automatic rollback
- **Options:**
  1. Keep a backup of previous state before each step
  2. Design steps to be idempotent (safe to retry)
  3. Manual rollback logic

## C. TTL & Cleanup
Your `set_job_data()` has a `ttl` parameter. When should it expire?
- After job completes? (24 hours?)
- If job fails? (keep longer for debugging?)
- Manually delete when moving to DB?

## D. Job Completion & Persistence
When the job is done:
- **Option 1:** Keep in Redis with TTL (fast access if needed later)
- **Option 2:** Move final state to PostgreSQL database
- **Option 3:** Delete from Redis (state is gone unless saved to DB)
