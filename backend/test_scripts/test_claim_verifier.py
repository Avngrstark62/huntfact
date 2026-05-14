from logging_config import setup_logging
setup_logging()

import asyncio
import json
import time

from services.claim_verifier.handler import handle_claim_verifier


DEFAULT_CLAIMS = [
    "Apollo 11 landed on the Moon in 1971.",
    "Apollo 11 landed on Mars.",
]

DEFAULT_CONTEXT = {
    "sources": [
        {
            "source_id": 1,
            "url": "https://www.nasa.gov/mission/apollo-11/",
            "title": "Apollo 11 Mission",
            "query": "apollo 11 moon landing date",
            "content": (
                "Apollo 11 was the spaceflight that first landed humans on the Moon. "
                "Neil Armstrong and Buzz Aldrin landed on July 20, 1969."
            ),
        },
        {
            "source_id": 2,
            "url": "https://www.britannica.com/event/Apollo-11",
            "title": "Apollo 11 | Britannica",
            "query": "apollo 11 mission overview",
            "content": (
                "Apollo 11, launched July 16, 1969, achieved the first crewed lunar landing. "
                "No mission detail indicates a Mars landing."
            ),
        },
    ]
}


async def test_claim_verifier() -> None:
    print("Testing claim verifier with claims:")
    for i, claim in enumerate(DEFAULT_CLAIMS, 1):
        print(f"  {i}. {claim}")

    print("\n" + "=" * 50)
    print("Running claim verifier...")
    print("=" * 50 + "\n")

    start_time = time.time()
    result = await handle_claim_verifier(
        {
            "claims": DEFAULT_CLAIMS,
            "context": DEFAULT_CONTEXT,
        }
    )
    elapsed = time.time() - start_time

    print(f"Latency: {elapsed:.2f}s")
    print(f"Error: {result.get('error')}\n")

    table = result.get("table") or {}
    rows = table.get("rows", []) if isinstance(table, dict) else []
    print(f"Rows returned: {len(rows)}")

    print("\nRaw result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(test_claim_verifier())
