from logging_config import setup_logging
setup_logging()

import asyncio
import json
import time

from services.save_result_to_db.handler import handle_save_result_to_db


DEFAULT_PAYLOAD = {
    "hunt_id": 1,
    "table": {
        "rows": [
            {
                "claim": "Apollo 11 landed on the Moon in 1969.",
                "verdict": "true",
                "sources": [
                    "https://www.nasa.gov/mission/apollo-11/",
                    "https://www.britannica.com/event/Apollo-11",
                ],
                "explanation": (
                    "Both cited sources describe Apollo 11 as the first crewed lunar landing mission "
                    "and place the landing in July 1969. The NASA mission page and Britannica overview "
                    "provide consistent dates and mission details, supporting the claim directly."
                ),
            },
            {
                "claim": "Apollo 11 landed on Mars.",
                "verdict": "false",
                "sources": [
                    "https://www.nasa.gov/mission/apollo-11/",
                ],
                "explanation": (
                    "The provided mission source explicitly states Apollo 11 landed on the Moon and "
                    "contains no indication of a Mars landing. This directly contradicts the claim."
                ),
            },
        ]
    },
}


async def test_save_result_to_db() -> None:
    print("Testing save_result_to_db with payload:")
    print(json.dumps(DEFAULT_PAYLOAD, indent=2, ensure_ascii=False))

    print("\n" + "=" * 50)
    print("Running save_result_to_db...")
    print("=" * 50 + "\n")

    start_time = time.time()
    result = await handle_save_result_to_db(DEFAULT_PAYLOAD)
    elapsed = time.time() - start_time

    print(f"Latency: {elapsed:.2f}s")
    print(f"Error: {result.get('error')}\n")

    print("Raw result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(test_save_result_to_db())
