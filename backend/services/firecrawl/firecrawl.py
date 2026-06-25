from firecrawl import Firecrawl

from config import settings
from logging_config import get_logger

logger = get_logger("services.firecrawl.firecrawl")


def fetch_markdown_with_firecrawl(url: str) -> str:
    """Fetch markdown content for a URL using the Firecrawl SDK."""
    cleaned_url = url.strip()
    if not cleaned_url:
        raise ValueError("URL is required")

    app = Firecrawl(api_url=settings.firecrawl.api_url)

    response = None

    try:
        response = app.scrape(cleaned_url, formats=["markdown"])
        logger.info(f"Firecrawl scrape succeeded for URL '{cleaned_url}'")
    except Exception as e:
        logger.info(f"Firecrawl scrape failed for URL '{cleaned_url}'")
        return ""
        # raise RuntimeError(f"Firecrawl scrape failed for URL '{cleaned_url}'") from e

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
