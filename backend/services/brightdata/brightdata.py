import logging
from typing import Any

import requests

from config import settings
from logging_config import get_logger, log_event, sanitize_url

logger = get_logger("services.brightdata.brightdata")


def _extract_html_from_response(response: requests.Response) -> str:
    content_type = (response.headers.get("Content-Type") or "").lower()
    if "application/json" in content_type:
        try:
            payload: Any = response.json()
        except ValueError:
            return ""

        if isinstance(payload, dict):
            for key in ("body", "raw", "html", "content", "result"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value
        return ""

    return response.text or ""


def fetch_html_with_brightdata(url: str, hunt_id: int | None = None) -> str:
    """Fetch raw HTML content for a URL using Bright Data request API."""
    cleaned_url = url.strip()
    if not cleaned_url:
        log_event(
            logger,
            level=logging.ERROR,
            event="provider.request.failed",
            status="failed",
            message="Bright Data request received empty URL",
            component="services.brightdata",
            provider="brightdata",
            operation="request",
            hunt_id=hunt_id,
        )
        raise ValueError("URL is required")

    api_key = settings.brightdata.api_key.strip()
    if not api_key:
        log_event(
            logger,
            level=logging.ERROR,
            event="provider.request.failed",
            status="failed",
            message="Bright Data API key is missing",
            component="services.brightdata",
            provider="brightdata",
            operation="request",
            hunt_id=hunt_id,
            url=sanitize_url(cleaned_url),
        )
        raise RuntimeError("BRIGHTDATA_API_KEY is required")

    zone = settings.brightdata.zone.strip()
    if not zone:
        log_event(
            logger,
            level=logging.ERROR,
            event="provider.request.failed",
            status="failed",
            message="Bright Data zone is missing",
            component="services.brightdata",
            provider="brightdata",
            operation="request",
            hunt_id=hunt_id,
            url=sanitize_url(cleaned_url),
        )
        raise RuntimeError("BRIGHTDATA_ZONE is required")

    payload = {
        "zone": zone,
        "url": cleaned_url,
        "format": settings.brightdata.response_format,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    log_event(
        logger,
        level=logging.INFO,
        event="provider.request.started",
        status="started",
        message="Starting Bright Data request",
        component="services.brightdata",
        provider="brightdata",
        operation="request",
        hunt_id=hunt_id,
        url=sanitize_url(cleaned_url),
    )
    try:
        response = requests.post(
            settings.brightdata.api_url,
            headers=headers,
            json=payload,
            timeout=settings.brightdata.timeout_seconds,
        )
    except requests.RequestException as e:
        log_event(
            logger,
            level=logging.ERROR,
            event="provider.request.failed",
            status="failed",
            message="Bright Data request failed",
            component="services.brightdata",
            provider="brightdata",
            operation="request",
            hunt_id=hunt_id,
            url=sanitize_url(cleaned_url),
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True,
        )
        raise RuntimeError(f"Bright Data request failed for URL '{cleaned_url}'") from e

    if response.status_code != 200:
        log_event(
            logger,
            level=logging.ERROR,
            event="provider.request.failed",
            status="failed",
            message="Bright Data returned non-200 response",
            component="services.brightdata",
            provider="brightdata",
            operation="request",
            hunt_id=hunt_id,
            url=sanitize_url(cleaned_url),
            http_status=response.status_code,
        )
        raise RuntimeError(
            f"Bright Data returned HTTP {response.status_code} for URL '{cleaned_url}'"
        )

    html = _extract_html_from_response(response)
    if not isinstance(html, str) or not html.strip():
        log_event(
            logger,
            level=logging.ERROR,
            event="provider.request.failed",
            status="failed",
            message="Bright Data response returned empty HTML",
            component="services.brightdata",
            provider="brightdata",
            operation="request",
            hunt_id=hunt_id,
            url=sanitize_url(cleaned_url),
        )
        raise RuntimeError(f"Bright Data response missing HTML for URL '{cleaned_url}'")

    log_event(
        logger,
        level=logging.INFO,
        event="provider.request.succeeded",
        status="succeeded",
        message="Bright Data request succeeded",
        component="services.brightdata",
        provider="brightdata",
        operation="request",
        hunt_id=hunt_id,
        url=sanitize_url(cleaned_url),
        result_summary={"html_length": len(html)},
    )
    return html
