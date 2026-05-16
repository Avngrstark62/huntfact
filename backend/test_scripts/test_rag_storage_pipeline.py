from logging_config import setup_logging

setup_logging()

import asyncio
import json
import time

from services.rag_storage.handler import handle_rag_storage
from services.web_scraper.handler import handle_web_scraper


DEFAULT_CLAIMS = [
    "Apollo 11 landed on the Moon in 1969.",
    "Neil Armstrong was the first person to walk on the Moon.",
]

DEFAULT_URL_FETCHER_RESULTS = {
    "results": [
        {
            "query": "apollo 11 mission official details",
            "urls": [
                {
                    "title": "Apollo 11 Mission - NASA",
                    "url": "https://www.nasa.gov/mission/apollo-11/",
                },
                {
                    "title": "Apollo 11 - Britannica",
                    "url": "https://www.britannica.com/event/Apollo-11",
                },
            ],
        },
        {
            "query": "neil armstrong first moonwalk source",
            "urls": [
                {
                    "title": "Neil Armstrong Biography",
                    "url": "https://www.biography.com/astronaut/neil-armstrong",
                },
                {
                    "title": "Apollo 11 Overview - NASA History",
                    "url": "https://www.nasa.gov/history/apollo-11-mission-overview/",
                },
            ],
        },
    ]
}


async def test_rag_storage_pipeline() -> None:
    print("Testing web_scraper -> rag_storage pipeline")
    print("\nClaims:")
    for idx, claim in enumerate(DEFAULT_CLAIMS, 1):
        print(f"  {idx}. {claim}")

    print("\n" + "=" * 60)
    print("Step 1: Running web scraper (fetches markdown live)")
    print("=" * 60)

    web_start = time.time()
    web_result = await handle_web_scraper(
        {
            "claims": DEFAULT_CLAIMS,
            "url_fetcher_results": DEFAULT_URL_FETCHER_RESULTS,
        }
    )
    web_elapsed = time.time() - web_start

    print(f"Web scraper latency: {web_elapsed:.2f}s")
    print(f"Web scraper error: {web_result.get('error')}")

    if web_result.get("error"):
        print("\nWeb scraper failed. Raw response:")
        print(json.dumps(web_result, indent=2, ensure_ascii=False))
        return

    context = web_result.get("context") or {}
    sources = context.get("sources", []) if isinstance(context, dict) else []
    print(f"Web scraper sources fetched: {len(sources)}")

    if not sources:
        print("\nNo sources returned by web scraper, skipping rag storage call.")
        return

    print("\n" + "=" * 60)
    print("Step 2: Running rag storage")
    print("=" * 60)

    rag_start = time.time()
    rag_result = await handle_rag_storage(
        {
            "context": context,
            "collection_name": "collection_5",
        }
    )
    rag_elapsed = time.time() - rag_start

    print(f"RAG storage latency: {rag_elapsed:.2f}s")
    print(f"RAG storage error: {rag_result.get('error')}")

    rag_reference = rag_result.get("rag_reference") or {}
    print(
        "RAG reference: "
        f"collection={rag_reference.get('collection_name')} "
        f"sources={rag_reference.get('source_count')} "
        f"chunks={rag_reference.get('chunk_count')}"
    )

    print("\nFinal web scraper response:")
    print(json.dumps(web_result, indent=2, ensure_ascii=False))
    print("\nFinal rag storage response:")
    print(json.dumps(rag_result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(test_rag_storage_pipeline())
