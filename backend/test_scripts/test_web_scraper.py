from logging_config import setup_logging
setup_logging()

import asyncio
import json
import time

from services.web_scraper.handler import handle_web_scraper


DEFAULT_CLAIMS = [
    "Apollo 11 landed on the Moon in 1971.",
    "Neil Armstrong was the first human to walk on the Moon.",
]

DEFAULT_URL_FETCHER_RESULTS = {
    "results": [
        {
            "query": "apollo 11 moon landing date",
            "urls": [
                {
                    "title": "Apollo 11 - NASA",
                    "url": "https://www.nasa.gov/mission/apollo-11/",
                },
                {
                    "title": "Apollo 11 - Britannica",
                    "url": "https://www.britannica.com/event/Apollo-11",
                },
            ],
        },
        {
            "query": "neil armstrong first person on moon",
            "urls": [
                {
                    "title": "Neil Armstrong - Biography",
                    "url": "https://www.biography.com/astronaut/neil-armstrong",
                },
                {
                    "title": "Apollo 11 Mission Overview - NASA",
                    "url": "https://www.nasa.gov/history/apollo-11-mission-overview/",
                },
            ],
        },
    ]
}


async def test_web_scraper() -> None:
    print("Testing web scraper with claims:")
    for i, claim in enumerate(DEFAULT_CLAIMS, 1):
        print(f"  {i}. {claim}")

    print("\n" + "=" * 50)
    print("Running web scraper...")
    print("=" * 50 + "\n")

    start_time = time.time()
    result = await handle_web_scraper(
        {
            "claims": DEFAULT_CLAIMS,
            "url_fetcher_results": DEFAULT_URL_FETCHER_RESULTS,
        }
    )
    elapsed = time.time() - start_time

    print(f"Latency: {elapsed:.2f}s")
    print(f"Error: {result.get('error')}\n")

    context = result.get("context") or {}
    sources = context.get("sources", []) if isinstance(context, dict) else []
    print(f"Selected and scraped sources: {len(sources)}")

    print("\nRaw result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(test_web_scraper())
