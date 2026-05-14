from logging_config import setup_logging
setup_logging()

import sys

from services.firecrawl.firecrawl import fetch_markdown_with_firecrawl


DEFAULT_URL = "https://example.com"


def test_firecrawl(url: str) -> None:
    print(f"Testing Firecrawl markdown fetch for: {url}")
    print("\n" + "=" * 50)
    print("Running Firecrawl...")
    print("=" * 50 + "\n")

    markdown = fetch_markdown_with_firecrawl(url)
    print(markdown)


if __name__ == "__main__":
    input_url = sys.argv[1].strip() if len(sys.argv) > 1 else DEFAULT_URL
    test_firecrawl(input_url)
