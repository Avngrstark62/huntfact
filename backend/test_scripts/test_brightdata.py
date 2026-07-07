from logging_config import setup_logging
setup_logging()

import sys

from services.brightdata.brightdata import fetch_html_with_brightdata
from services.web_scraper.web_scraper import _extract_markdown_from_html


DEFAULT_URL = "https://geo.brdtest.com/welcome.txt?product=unlocker&method=api"
PREVIEW_CHARS = 1200


def test_brightdata(url: str) -> None:
    print(f"Testing Bright Data HTML fetch for: {url}")
    print("\n" + "=" * 50)
    print("Running Bright Data request...")
    print("=" * 50 + "\n")

    html = fetch_html_with_brightdata(url)
    print(f"Fetched HTML length: {len(html)}\n")
    print(html[:PREVIEW_CHARS])

    markdown = _extract_markdown_from_html(html,url,1)
    print(f"\nExtracted Markdown length: {len(markdown)}\n")
    print(markdown)


if __name__ == "__main__":
    input_url = sys.argv[1].strip() if len(sys.argv) > 1 else DEFAULT_URL
    test_brightdata(input_url)
