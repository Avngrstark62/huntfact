from logging_config import setup_logging
setup_logging()

import asyncio
import json
import sys
import time

from services.url_fetcher.handler import handle_url_fetcher


DEFAULT_CLAIMS = [
    'Asharam, who is serving a life sentence for the rape of a minor girl and a woman, arrived at Ram Janm Bhoomi in Ayodhya on March 12.',
    'Champat Rai is the President of the Vishva Hindu Parishad and the secretary of Ram Janm Bhoomi.',
    'Asharam was welcomed with flower garlands at the Ram Janm Bhoomi temple in Uttar Pradesh.',
    'Asaram, also received a similar welcome at Kashi Vishwanath Temple.',
    'Asaram will visit Mathura, where a similar welcome with flowers is expected.'
]


async def test_url_fetcher(claims: list[str]) -> None:
    print("Testing URL fetcher with claims:")
    for i, claim in enumerate(claims, 1):
        print(f"  {i}. {claim}")

    print("\n" + "=" * 50)
    print("Running URL fetcher...")
    print("=" * 50 + "\n")

    start_time = time.time()
    result = await handle_url_fetcher({"claims": claims})
    elapsed = time.time() - start_time

    print(f"Latency: {elapsed:.2f}s")
    print(f"Error: {result.get('error')}\n")

    query_results = result.get("results") or []
    print(f"Total generated queries: {len(query_results)}\n")

    for entry in query_results:
        query = entry.get("query", "")
        urls = entry.get("urls", [])
        print(f"Query: {query}")
        print(f"Results found: {len(urls)}")
        for i, url in enumerate(urls, 1):
            print(f"  [{i}] {url.get('title', 'N/A')}")
            print(f"      URL: {url.get('href', 'N/A')}")
            print(f"      Snippet: {url.get('body', 'N/A')[:120]}...")
        print()

    print("Raw result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    input_claims = [arg.strip() for arg in sys.argv[1:] if arg.strip()]
    claims_to_test = input_claims if input_claims else DEFAULT_CLAIMS
    asyncio.run(test_url_fetcher(claims_to_test))
