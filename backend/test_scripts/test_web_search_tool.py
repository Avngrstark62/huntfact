import asyncio
from agents.tools.web_search_tool import web_search

async def test():
    print("[TEST] Starting test_web_search_tool")
    print("[TEST] This will test if web_search() works independently")
    
    try:
        print("[TEST] Calling web_search() with test query")
        result = web_search(query='1990 Muslim community fertility rate 4.5')
        print(f"[TEST] Got result successfully!")
        print(f"[TEST] Number of results: {len(result)}")
        if result:
            print(f"[TEST] First result: {result[0]}")
        else:
            print(f"[TEST] No results returned")
        return result
    except Exception as e:
        print(f"[TEST] Error occurred: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("[TEST] Starting asyncio.run()")
    asyncio.run(test())
    print("[TEST] Test completed")
