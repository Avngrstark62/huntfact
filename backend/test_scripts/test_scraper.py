import asyncio
import sys
from services.page_scraper import scrape_page


async def main():
    """Test script for page scraper service."""
    
    # Example URLs
    urls = [
        "https://daily.dev"
    ]
    
    # Allow passing URLs as command line arguments
    if len(sys.argv) > 1:
        urls = sys.argv[1:]
    
    print(f"Scraping {len(urls)} URL(s)...\n")
    
    for url in urls:
        print(f"Processing: {url}")
        result = await scrape_page(url)
        if result:
            print(result)
        # print(f"  Success: {result['success']}")
        # if result['title']:
        #     print(f"  Title: {result['title'][:60]}...")
        # if result['content']:
        #     print(f"  Content: {result['content'][:100]}...")
        print()


if __name__ == "__main__":
    asyncio.run(main())
