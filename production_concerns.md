| Category                       | What to look for                          | Example                                    |
| ------------------------------ | ----------------------------------------- | ------------------------------------------ |
| **1. Functional correctness**  | Does every feature work?                  | Wrong fact-check result                    |
| **2. Edge cases**              | Empty, huge, malformed, unexpected inputs | Empty article crashes pipeline             |
| **3. Validation**              | Input validation everywhere               | Invalid URL accepted                       |
| **4. Error handling**          | Graceful failures                         | LLM timeout returns 500                    |
| **5. Reliability**             | Retries, fallbacks, circuit breakers      | Search API fails → fallback model          |
| **6. Availability**            | Backend stays online                      | One dependency down shouldn't kill service |
| **7. Scalability**             | Many concurrent users                     | 100 requests/sec                           |
| **8. Performance**             | Latency optimization                      | 30s response feels broken                  |
| **9. Resource usage**          | CPU, RAM, DB connections                  | Memory leak                                |
| **10. Cost**                   | Token usage, search cost, scraping cost   | User generates $2 request                  |
| **11. Security**               | Auth, secrets, injection, SSRF            | Prompt injection via webpage               |
| **12. Privacy**                | PII handling                              | User data sent to logs                     |
| **13. Authorization**          | Proper permissions                        | User accesses others' data                 |
| **14. Rate limiting**          | Abuse protection                          | Bot sends 10k requests                     |
| **15. Database integrity**     | Transactions, consistency                 | Half-written records                       |
| **16. Data corruption**        | Invalid state                             | Duplicate fact-checks                      |
| **17. Idempotency**            | Safe retries                              | Same notification sent twice               |
| **18. Race conditions**        | Concurrent requests                       | Two workers update same row                |
| **19. Background jobs**        | Retry, dead-letter queue                  | Failed notification lost                   |
| **20. Caching**                | Correct invalidation                      | Old fact-check served                      |
| **21. RAG quality**            | Retrieval relevance                       | Wrong chunk retrieved                      |
| **22. Embedding/index health** | Freshness                                 | New documents never indexed                |
| **23. Web search quality**     | Good source selection                     | Spam website ranked first                  |
| **24. Scraping robustness**    | Site changes                              | HTML parser breaks                         |
| **25. LLM quality**            | Hallucination, refusals                   | Makes up facts                             |
| **26. Prompt robustness**      | Injection resistance                      | Website overrides system prompt            |
| **27. Output validation**      | Verify model output                       | Invalid JSON                               |
| **28. Confidence estimation**  | Know when uncertain                       | Says "true" with no evidence               |
| **29. Source attribution**     | Citations correct                         | Citation doesn't support claim             |
| **30. User experience**        | Helpful failures                          | "Something went wrong" vs useful message   |
| **31. Observability**          | Logs, metrics, traces                     | Can't debug failures                       |
| **32. Monitoring**             | Live dashboards                           | Latency spike unnoticed                    |
| **33. Alerting**               | Automatic alerts                          | DB down but nobody knows                   |
| **34. Analytics**              | User behavior                             | Where users abandon requests               |
| **35. Testing**                | Unit/integration/E2E                      | Entire pipeline tested                     |
| **36. Regression testing**     | Old bugs stay fixed                       | Prompt update breaks old case              |
| **37. Deployment**             | Safe releases                             | Blue-green/canary                          |
| **38. Rollback**               | Instant recovery                          | Bad deploy reversible                      |
| **39. Configuration**          | Env vars correct                          | Wrong API key in prod                      |
| **40. Dependency management**  | External services                         | Provider API changes                       |
| **41. API compatibility**      | Versioning                                | Clients break after update                 |
| **42. Notifications**          | Reliable delivery                         | Duplicate FCM notifications                |
| **43. Timeouts**               | Every network call                        | Scraper hangs forever                      |
| **44. Retry strategy**         | Smart retries                             | Infinite retry storm                       |
| **45. Quotas & limits**        | Provider limits                           | OpenAI rate limit exceeded                 |
| **46. Disaster recovery**      | Backup & restore                          | DB corruption                              |
| **47. Compliance**             | GDPR, ToS                                 | Illegal scraping                           |
| **48. Abuse prevention**       | Spam, scraping abuse                      | Free API exploited                         |
| **49. Documentation**          | Runbooks, API docs                        | On-call can't fix outage                   |
| **50. Maintainability**        | Code organization                         | Impossible to modify                       |
| **51. Feature flags**          | Disable bad features                      | Turn off web search instantly              |
| **52. Incident readiness**     | Postmortems, playbooks                    | Know exactly what to do                    |
| **53. AI evaluation**          | Golden dataset                            | 500 benchmark claims before release        |
| **54. User feedback loop**     | Learn from failures                       | "Report incorrect fact-check"              |
| **55. Business metrics**       | Success rate                              | % users getting useful answers             |
