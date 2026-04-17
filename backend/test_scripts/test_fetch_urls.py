from logging_config import setup_logging
setup_logging()

import asyncio
import json
import time
from services.fetch_urls.fetch_urls import fetch_urls_for_queries

async def test_fetch_urls():
    queries = [
        "Muslim community percentage in India 1990",
        "India child mortality rate 1990",
        "India maternal mortality ratio 1999-2000",
    ]
    
    print("Test queries:")
    for i, q in enumerate(queries, 1):
        print(f"  {i}. {q}")
    
    print("\n" + "="*50)
    print("Fetching URLs...")
    print("="*50 + "\n")
    
    start_time = time.time()
    try:
        results = await fetch_urls_for_queries(queries)
        elapsed = time.time() - start_time
        
        print(f"Latency: {elapsed:.2f}s\n")
        
        for result in results:
            print(f"Query: {result['query']}")
            print(f"URLs found: {len(result['urls'])}\n")
            
            for i, url in enumerate(result['urls'], 1):
                print(f"  [{i}] {url.get('title', 'N/A')}")
                print(f"      URL: {url.get('href', 'N/A')}")
                print(f"      Snippet: {url.get('body', 'N/A')[:100]}...")
                print()

        print(results)
    
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"Latency: {elapsed:.2f}s")
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_fetch_urls())
