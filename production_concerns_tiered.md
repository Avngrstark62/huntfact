# Tier 0 — Must Have (Launch Blockers 🚨)



**If any of these are bad, don't launch.**



| Category                       | Why                                                            |

| ------------------------------ | -------------------------------------------------------------- |

| Functional correctness         | The core fact-check must work correctly.                       |

| Error handling                 | Users should never see crashes or stack traces.                |

| Reliability                    | External APIs will fail. Your system must recover gracefully.  |

| Security                       | A vulnerability can permanently damage trust.                  |

| Privacy                        | Never leak user or internal data.                              |

| Authentication & Authorization | Users should only access what they're allowed to.              |

| AI quality                     | Hallucinating or giving wrong fact-checks defeats the product. |

| RAG quality                    | Bad retrieval = bad answers regardless of model quality.       |

| Output validation              | Never trust LLM output blindly.                                |

| Observability (logging)        | If something breaks, you must know why.                        |

| Timeouts                       | Every external call must eventually stop waiting.              |

| Retry strategy                 | Temporary failures should recover automatically.               |

| Rate limiting                  | Protect against abuse and accidental overload.                 |

| Cost protection                | Prevent a single user from generating huge bills.              |

| Database integrity             | Never corrupt or partially save important data.                |



**These are the "people uninstall your app or your company loses money" issues.**



---



# Tier 1 — Very Important (Should Have Before Launch)



**The product works without these, but users will notice problems.**



| Category                  | Why                                              |

| ------------------------- | ------------------------------------------------ |

| Performance               | Nobody likes waiting 30+ seconds.                |

| Edge cases                | Real users do weird things.                      |

| Input validation          | Prevent bad requests from entering the pipeline. |

| Web search quality        | Better sources → better answers.                 |

| Scraping robustness       | Websites change constantly.                      |

| Confidence estimation     | Know when the AI isn't sure.                     |

| Source attribution        | Users need evidence, not just answers.           |

| User experience           | Good loading/errors increase trust.              |

| Monitoring                | Detect problems before users complain.           |

| Notifications reliability | Avoid duplicate or missing notifications.        |

| Caching                   | Reduces latency and cost.                        |

| Background jobs           | Ensure async tasks don't disappear.              |

| Testing                   | Catch obvious regressions before deployment.     |

| Deployment & Rollback     | Quickly recover from bad releases.               |

| Dependency handling       | Third-party APIs will eventually fail.           |

| Quotas & Limits           | Stay within provider constraints.                |



---



# Tier 2 — Important (Can Improve After Launch)



**Not launch blockers, but they'll become important as usage grows.**



| Category                  | Why                                                |

| ------------------------- | -------------------------------------------------- |

| Scalability               | Needed when user count grows.                      |

| Resource optimization     | Better CPU/RAM efficiency.                         |

| Analytics                 | Understand user behavior.                          |

| Feature flags             | Safely enable/disable features.                    |

| API versioning            | Important once clients depend on your API.         |

| Configuration management  | Easier deployments.                                |

| Regression testing        | Prevent future updates from breaking old behavior. |

| Maintainability           | Makes development faster later.                    |

| Embedding/index freshness | Improves long-term RAG quality.                    |

| Data consistency checks   | Prevent subtle data issues.                        |



---



# Tier 3 — Nice to Have (Later)



**These matter once the product has traction.**



| Category                | Why                                                     |

| ----------------------- | ------------------------------------------------------- |

| Disaster recovery       | Critical at scale, less urgent on day one.              |

| Compliance (GDPR, etc.) | Depends on users and regions served.                    |

| Incident playbooks      | Useful once you have an on-call process.                |

| Documentation           | Helps team growth.                                      |

| Business metrics        | Useful for optimization, not launch.                    |

| User feedback loop      | Great for improving quality over time.                  |

| AI evaluation benchmark | Becomes increasingly valuable as prompts/models evolve. |
