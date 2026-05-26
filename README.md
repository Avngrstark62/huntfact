# HuntFact

Try the first release APK: [v1.0.0](https://github.com/Avngrstark62/huntfact/releases/tag/v1.0.0)

## 1. Project Overview
HuntFact is an Android app for fact-checking short video claims (currently Instagram-first).  
You share a reel, HuntFact processes its spoken content through an asynchronous verification pipeline, and returns claim-level verdicts with explanations and source links.

## 2. User Flow
1. User shares a reel URL to HuntFact from the share sheet.
2. App validates the link, prepares a fact-check request, and sends it to the backend.
3. Backend starts an async hunt workflow and tracks status.
4. Pipeline extracts audio, transcribes, translates, extracts claims, fetches sources, and verifies claims.
5. User gets a push notification when the result is ready.
6. App shows a structured result view with verdict filters and source links.

## 3. Feature List
- Share-to-check flow from social reels (Instagram support in v1).
- Claim-level verdicts with explanation and cited web sources.
- Push notifications for hunt progress/completion.

## 4. Architecture (Including Pipeline)
HuntFact uses a distributed async architecture:
- **Android Client**: captures shared links, starts hunts, shows hunt history/results, and receives notifications.
- **API Layer**: accepts authenticated hunt requests, enforces health and user limits, and exposes hunt status endpoints.
- **Workflow Orchestrator**: drives the end-to-end pipeline, coordinates step sequencing, parallelizes cluster verification, and handles fan-in.
- **Task Workers**: execute specialized processing steps through a message queue.
- **Storage + Infra**: relational DB for hunt lifecycle/state, queue system for async tasks, vector/search support for retrieval, and notification delivery.

### Pipeline
1. Extract audio from the submitted media link.
2. Run parallel transcriptions, then consolidate/correct transcript quality.
3. Translate transcript to a normalized analysis language.
4. Extract objective factual claim clusters.
5. For each cluster: generate search intent, gather sources, scrape context, and verify claims.
6. Merge all cluster verdict tables.
7. Persist final result and update hunt status.
8. Send user notification with result availability.

## 5. Tech Stack
- **Mobile**: Kotlin, Jetpack Compose, WorkManager, Retrofit, Firebase Cloud Messaging, Supabase Auth (Google OAuth).
- **Backend/API**: Python, FastAPI, Pydantic.
- **Async + Messaging**: RabbitMQ-based orchestrator/worker pipeline.
- **Data Layer**: PostgreSQL, SQLAlchemy, Alembic, Redis.
- **Retrieval + External Intelligence**: ChromaDB, LLM APIs, transcription providers, web search/scraping services.

## 6. Known Limitations
- Verdict quality can still be brittle in edge cases; the claim verifier is not fully robust yet.
- The current system works best for objective, checkable claims.
- It does not work well when relevant evidence is not publicly available on the internet.

## 7. Upcoming Features
- Support for subjective claims using argument analysis (Toulmin model).
- Support for additional short-form platforms, including YouTube Shorts.

## 8. Contribution
We are currently setting up HuntFact for open source contributions.  
Please feel free to open issues for feature requests, bug reports, and improvement ideas.
