"""DDGS Wrapper - DuckDuckGo Web Scraping Interface.

A simplified interface for performing web text searches using DDGS with DuckDuckGo
and multiple fallback search engines.
"""

import importlib
import logging
import threading
from typing import TYPE_CHECKING, Any, cast

__version__ = "1.0.0"
__all__ = ("search_web", "DDGS")

if TYPE_CHECKING:
    from .ddgs import DDGS

# A do-nothing logging handler
# https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library
logging.getLogger("ddgs").addHandler(logging.NullHandler())


class _ProxyMeta(type):
    _lock: threading.Lock = threading.Lock()
    _real_cls: type["DDGS"] | None = None

    @classmethod
    def _load_real(cls) -> type["DDGS"]:
        if cls._real_cls is None:
            with cls._lock:
                if cls._real_cls is None:
                    cls._real_cls = importlib.import_module(".ddgs", package=__name__).DDGS
                    globals()["DDGS"] = cls._real_cls
        return cls._real_cls

    def __call__(cls, *args: Any, **kwargs: Any) -> "DDGS":  # noqa: ANN401
        real = type(cls)._load_real()
        return real(*args, **kwargs)

    def __getattr__(cls, name: str) -> Any:  # noqa: ANN401
        return getattr(type(cls)._load_real(), name)

    def __dir__(cls) -> list[str]:
        base = set(super().__dir__())
        loaded_names = set(dir(type(cls)._load_real()))
        return sorted(base | (loaded_names - base))


class _DDGSProxy(metaclass=_ProxyMeta):
    """Proxy class for lazy-loading the real DDGS implementation."""


DDGS: type[DDGS] = cast("type[DDGS]", _DDGSProxy)  # type: ignore[no-redef]


def search_web(
    query: str,
    max_results: int | None = 10,
    region: str = "us-en",
    safesearch: str = "moderate",
    timelimit: str | None = None,
    page: int = 1,
    backend: str = "auto",
    proxy: str | None = None,
    timeout: int | None = 5,
    verify: bool | str = True,
) -> list[dict[str, Any]]:
    """Perform a web text search using DDGS.

    This is the primary interface for web scraping. It aggregates results from
    multiple search engines, starting with DuckDuckGo, and falls back to other
    engines (Bing, Google, Brave, Wikipedia, etc.) for better coverage.

    Args:
        query: The search query string (required).
        max_results: Maximum number of results to return. Defaults to 10.
        region: Region for localized search (e.g., 'us-en', 'uk-en', 'ru-ru', etc.).
            Defaults to 'us-en'.
        safesearch: Safe search setting - 'on', 'moderate', or 'off'.
            Defaults to 'moderate'.
        timelimit: Filter results by time - 'd' (day), 'w' (week), 'm' (month), 'y' (year).
            Defaults to None (no time limit).
        page: Page number for pagination (1-based). Defaults to 1.
        backend: Specify which search engine to use:
            - 'auto' (default): Uses all available engines (DuckDuckGo, Bing, Google, etc.)
            - 'duckduckgo': DuckDuckGo only
            - 'bing': Bing only
            - 'google': Google only
            - 'brave': Brave only
            - Or comma-separated list: 'duckduckgo,bing,google'
        proxy: Proxy server URL (supports http/https/socks5). Defaults to None.
        timeout: HTTP request timeout in seconds. Defaults to 5.
        verify: SSL certificate verification. Defaults to True.

    Returns:
        List of dictionaries containing search results with 'title', 'href', and 'body' keys.

    Examples:
        >>> from ddgs_wrapper import search_web
        >>> results = search_web("python programming", max_results=5)
        >>> for result in results:
        ...     print(f"{result['title']}: {result['href']}")
    """
    from .scraper import search_web as _search_web

    return _search_web(
        query,
        max_results=max_results,
        region=region,
        safesearch=safesearch,
        timelimit=timelimit,
        page=page,
        backend=backend,
        proxy=proxy,
        timeout=timeout,
        verify=verify,
    )
