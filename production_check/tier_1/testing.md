# Production Concern: Testing (Tier 1)

Focus: ability to catch backend regressions before deployment.

## Major Testing Issues

1. **No automated test framework integrated for CI-style pass/fail gating** (`backend/pyproject.toml`, `backend/test_scripts/*.py`)  
   Current coverage is script-based manual execution; there is no `pytest`/unittest suite enforcing pre-release regression checks.

2. **Critical API and workflow paths lack deterministic assertions** (`backend/test_scripts/*.py`, `backend/router.py`, `backend/orchestrator.py`)  
   Test scripts mostly print outputs and latencies instead of asserting contracts/behavior, so regressions can pass unnoticed.

3. **Core failure-path behavior is largely untested** (`backend/test_scripts/*.py`)  
   There is little evidence of systematic tests for provider outages, malformed queue payloads, timeout cases, partial step failures, and retry/recovery outcomes.

4. **Heavy dependence on live external services in test scripts** (`backend/test_scripts/test_url_fetcher.py`, `backend/test_scripts/test_web_scraper.py`, `backend/test_scripts/test_transcriber.py`, `backend/test_scripts/test_translator.py`)  
   Live-network/manual tests are slow and flaky, reducing repeatability and making frequent pre-deploy validation unlikely.

## Important Testing Gaps

5. **No contract tests for response schema stability** (`backend/schemas.py`, `backend/router.py`)  
   There is no automated check that API success/error payload shapes remain stable for clients across backend changes.

6. **No end-to-end automated regression test for full async pipeline** (`backend/orchestrator.py`, `backend/worker.py`, `backend/test_scripts/test_rag_storage_pipeline.py`)  
   Existing pipeline script is diagnostic, not a strict pass/fail E2E test with expected-state verification.

7. **No evidence of coverage for data integrity and state transitions** (`backend/db/database.py`, `backend/router.py`, `backend/orchestrator.py`)  
   Important transitions (`queued`→`processing`→`completed/failed`) and DB persistence invariants are not backed by repeatable automated tests.
