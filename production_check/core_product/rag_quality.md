# Production Concern: RAG Quality (Tier 0)

Focus: whether retrieved evidence is relevant, sufficient, trustworthy, and correctly grounded to claims.

## Release Blockers

1. **No hard minimum evidence threshold before claim verification** (`backend/services/claim_verifier/claim_verifier.py`)  
   Verification proceeds with whatever passes distance filtering; there is no strict gate on source count/diversity/coverage before verdict generation.

2. **Distance-only retrieval filter is brittle and globally fixed** (`backend/services/claim_verifier/claim_verifier.py`)  
   `MAX_DISTANCE=0.35` is static for all claim types/domains, risking both false negatives (missing evidence) and false positives (weak matches).

3. **Source authority is model-judged, not system-enforced** (`backend/services/web_scraper/web_scraper.py`, `backend/services/claim_verifier/claim_verifier.py`)  
   High-impact source-quality decisions rely on LLM prompts without deterministic trust-domain policies.

## High Severity

4. **Retriever query generation is LLM-only with weak deterministic fallback** (`backend/services/claim_verifier/claim_verifier.py`)  
   If retrieval query generation underperforms, fallback returns raw claims, which may be poor search vectors and degrade grounding.

5. **Web query generation can over/under-cover claim space** (`backend/services/url_fetcher/url_fetcher.py`)  
   Query synthesis is prompt-driven with no coverage validator to ensure all claims are retrievable from produced queries.

6. **URL selection is single-pass and prompt-dependent** (`backend/services/web_scraper/web_scraper.py`)  
   Candidate ranking/selection lacks secondary quality checks (domain reliability, recency, contradiction diversity), so weak source sets can pass through.

7. **Scrape failures are silently dropped from context quality accounting** (`backend/services/web_scraper/web_scraper.py`, `backend/services/firecrawl/firecrawl.py`)  
   Failed URLs are skipped without explicit coverage-loss scoring, which can produce thin context while looking structurally valid.

8. **Chunking strategy may break factual coherence** (`backend/services/rag_storage/rag_storage.py`)  
   Heuristic sentence splitting/token estimates can fragment evidence context, reducing retriever precision for nuanced claims.

9. **Deduplication key is coarse (`url`, `content`)** (`backend/services/claim_verifier/claim_verifier.py`)  
   Near-duplicate evidence across pages/domains can still bias retrieval context; provenance diversity is not explicitly enforced.

## Important Gaps

10. **No recency handling or temporal relevance scoring** (URL fetcher/scraper/retriever path)  
   Retrieval quality does not explicitly prioritize up-to-date evidence for time-sensitive claims.

11. **No contradiction-seeking retrieval pass** (`backend/services/claim_verifier/claim_verifier.py`)  
   Retrieval focuses on relevance but not explicit opposing-evidence discovery, which can bias verdicts.

12. **No citation-grounding verification beyond URL allow-listing** (`backend/services/claim_verifier/claim_verifier.py`)  
   Output URLs are constrained to retrieved sources, but there is no post-check that explanation statements are truly supported by cited chunks.

13. **No evaluation loop for retrieval quality drift** (project-wide)  
   There is no production guardrail for tracking retrieval hit quality, source precision, or claim-coverage regressions over time.
