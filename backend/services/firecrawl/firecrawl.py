from firecrawl import Firecrawl
import logging

from config import settings
from logging_config import get_logger, log_event, sanitize_url

logger = get_logger("services.firecrawl.firecrawl")


def fetch_markdown_with_firecrawl(url: str, hunt_id: int | None = None) -> str:
    """Fetch markdown content for a URL using the Firecrawl SDK."""
    cleaned_url = url.strip()
    if not cleaned_url:
        log_event(
            logger,
            level=logging.ERROR,
            event="provider.request.failed",
            status="failed",
            message="Firecrawl scrape received empty URL",
            component="services.firecrawl",
            provider="firecrawl",
            operation="scrape",
            hunt_id=hunt_id,
        )
        raise ValueError("URL is required")

    app = Firecrawl(api_url=settings.firecrawl.api_url)

    response = None

    log_event(
        logger,
        level=logging.INFO,
        event="provider.request.started",
        status="started",
        message="Starting Firecrawl scrape",
        component="services.firecrawl",
        provider="firecrawl",
        operation="scrape",
        hunt_id=hunt_id,
        url=sanitize_url(cleaned_url),
    )
    try:
        response = app.scrape(cleaned_url, formats=["markdown"])
        log_event(
            logger,
            level=logging.INFO,
            event="provider.request.succeeded",
            status="succeeded",
            message="Firecrawl scrape succeeded",
            component="services.firecrawl",
            provider="firecrawl",
            operation="scrape",
            hunt_id=hunt_id,
            url=sanitize_url(cleaned_url),
        )
    except Exception as e:
        log_event(
            logger,
            level=logging.ERROR,
            event="provider.request.failed",
            status="failed",
            message="Firecrawl scrape failed",
            component="services.firecrawl",
            provider="firecrawl",
            operation="scrape",
            hunt_id=hunt_id,
            url=sanitize_url(cleaned_url),
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True,
        )
        raise RuntimeError(f"Firecrawl scrape failed for URL '{cleaned_url}'") from e

    markdown = ""
    if isinstance(response, dict):
        markdown = response.get("markdown", "")
    elif hasattr(response, "markdown"):
        markdown = getattr(response, "markdown", "")
    elif hasattr(response, "get"):
        markdown = response.get("markdown", "")

    if not isinstance(markdown, str) or not markdown.strip():
        log_event(
            logger,
            level=logging.ERROR,
            event="provider.request.failed",
            status="failed",
            message="Firecrawl scrape returned empty markdown",
            component="services.firecrawl",
            provider="firecrawl",
            operation="scrape",
            hunt_id=hunt_id,
            url=sanitize_url(cleaned_url),
        )
        raise RuntimeError(f"Firecrawl response missing markdown for URL '{cleaned_url}'")

    return markdown
