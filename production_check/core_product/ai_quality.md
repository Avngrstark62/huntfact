# Production Concern: AI Quality (Tier 0)

Focus: factual correctness, calibration, and user-trust quality of AI-generated outputs.

## Release Blockers

1. **No final quality gate before marking hunts completed** (`backend/orchestrator.py`, `backend/services/save_result_to_db/save_result_to_db.py`)  
   Pipeline accepts structurally valid outputs even when evidence quality is weak, then persists and serves them as final results.

2. **Verification verdict is derived from model-generated latent scores without robustness checks** (`backend/services/claim_verifier/claim_verifier.py`)  
   `support_strength`/`contradiction_strength`/`completeness`/`source_quality` are trusted directly from LLM output and converted into verdict/confidence with no independent calibration validation.

3. **Fallback no-evidence paths can still produce user-facing result objects with weak epistemic signaling** (`backend/orchestrator.py`, `backend/services/save_result_to_db/save_result_to_db.py`)  
   “no verdict/unverified” pathways are handled, but there is no hard policy to stop low-evidence runs from being treated as normal successful completions.

## High Severity

4. **Prompt-only safeguards against hallucination/prompt injection** (`backend/services/claim_verifier/claim_verifier.py`, `backend/services/claim_extractor/claim_extractor.py`, `backend/services/web_scraper/web_scraper.py`)  
   Quality relies heavily on instructions (“use only provided sources”) without stronger adversarial controls or consistency checks.

5. **RAG quality bottlenecks can degrade AI correctness silently** (`backend/services/claim_verifier/claim_verifier.py`)  
   Hard caps (`MAX_QUERIES=10`, `MAX_CHUNKS_PER_QUERY=5`, `MAX_DISTANCE=0.35`) may under-retrieve for complex claims, yet downstream still returns confident-looking outputs.

6. **No cross-model/cross-pass consistency checks for critical claims** (pipeline-wide)  
   Final verification depends on a single reasoning pass; there is no contradiction/self-consistency re-check for high-impact claims.

7. **Trust score is simplistic mean of confidences and may misrepresent reliability** (`backend/services/save_result_to_db/save_result_to_db.py`)  
   Aggregation ignores claim importance/evidence breadth, so a polished but weakly grounded run can appear trustworthy.

8. **Metadata generation can soften/reshape low-quality outputs** (`backend/services/save_result_to_db/save_result_to_db.py`)  
   Title/summary generation is another LLM step and can produce persuasive framing even when underlying evidence quality is poor.

## Important Gaps

9. **No per-claim minimum evidence threshold before strong verdicts** (`backend/services/claim_verifier/claim_verifier.py`)  
   Verdict mapping uses score formulas but lacks explicit hard guardrails like minimum source count/diversity for “true/false”-style outcomes.

10. **No confidence calibration benchmark loop in runtime path** (project-wide)  
   Confidence values are generated/derived but not calibrated against a held benchmark in production decisioning.

11. **Translation/transcription uncertainty is not propagated into final claim confidence** (`backend/orchestrator.py`, transcription/translation services, claim verifier)  
   Upstream ASR/translation ambiguity is not explicitly carried as uncertainty penalties into final verdict confidence.

12. **No user-facing quality disclaimers by evidence strength tier** (API response design)  
   Responses include `trust_score` and table rows, but there is no standardized quality band/message that clearly distinguishes high-certainty vs weak-evidence outcomes.
