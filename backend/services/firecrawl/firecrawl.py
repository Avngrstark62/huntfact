from firecrawl import Firecrawl

from config import settings
from logging_config import get_logger

logger = get_logger("services.firecrawl.firecrawl")


def fetch_markdown_with_firecrawl(url: str) -> str:
    """Fetch markdown content for a URL using the Firecrawl SDK."""
    cleaned_url = url.strip()
    if not cleaned_url:
        raise ValueError("URL is required")

    if not settings.firecrawl_api_key:
        raise ValueError("Missing Firecrawl API key in config")

    app = Firecrawl(api_key=settings.firecrawl_api_key)

    try:
        response = app.scrape(cleaned_url, formats=["markdown"])
    except Exception as e:
        logger.error(f"Firecrawl scrape failed for URL '{cleaned_url}': {str(e)}", exc_info=True)
        raise RuntimeError(f"Firecrawl scrape failed for URL '{cleaned_url}'") from e

    markdown = ""
    if isinstance(response, dict):
        markdown = response.get("markdown", "")
    elif hasattr(response, "markdown"):
        markdown = getattr(response, "markdown", "")
    elif hasattr(response, "get"):
        markdown = response.get("markdown", "")

    if not isinstance(markdown, str) or not markdown.strip():
        raise RuntimeError(f"Firecrawl response missing markdown for URL '{cleaned_url}'")

    return markdown
