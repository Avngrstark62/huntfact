"""
Reel extractor v2:
- Accepts reel URL
- Fetches reel HTML page
- Extracts audio CDN URL from embedded HTML payload
"""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

import requests

from services.reel_extractor.get_audio_cdn_link_from_html import extract_audio_cdn_link_from_html


def _extract_shortcode_from_url(url: str) -> Optional[str]:
    """
    Extract shortcode from Instagram URL.

    Supports:
    - https://www.instagram.com/reel/{shortcode}/
    - https://www.instagram.com/reels/{shortcode}/
    - https://www.instagram.com/p/{shortcode}/
    """
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    match = re.match(r"^(?:reels?|p)/([a-zA-Z0-9_-]+)", path)
    if match:
        return match.group(1)
    return None


def get_reel_audio_cdn_link(reel_url: str) -> Optional[str]:
    """
    Get first audio CDN link from reel HTML.

    Args:
        reel_url: Instagram reel URL

    Returns:
        Audio CDN URL as plain string, or None if unavailable.
    """
    shortcode = _extract_shortcode_from_url(reel_url)
    if not shortcode:
        print(f"Could not extract shortcode from URL: {reel_url}")
        return None

    url = f"https://www.instagram.com/reel/{shortcode}/?l=1"
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "en-US,en;q=0.9,hi;q=0.8,ja;q=0.7",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "sec-fetch-user": "?1",
        "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36",
        # "cache-control": "no-cache",
        # "cookie": "csrftoken=_2tj7yoTzC-jqiwm6bojoF; datr=WCVBas493yRPa8G7QLBnU8vU; ig_did=C28334A1-1D51-486E-9E21-E845BF929BB8; wd=432x834; dpr=2.5; mid=akElWAABAAETqfY7pHAyVshmzarp; ps_l=1; ps_n=1",
        # "dpr": "2.5",
        # "pragma": "no-cache",
        # "priority": "u=0, i",
        # "sec-ch-prefers-color-scheme": "light",
        # "sec-ch-ua": '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
        # "sec-ch-ua-full-version-list": '"Not)A;Brand";v="99.0.0.0", "Google Chrome";v="127.0.6533.103", "Chromium";v="127.0.6533.103"',
        # "sec-ch-ua-mobile": "?1",
        # "sec-ch-ua-model": '"moto g54 5G"',
        # "sec-ch-ua-platform": '"Android"',
        # "sec-ch-ua-platform-version": '"15.0.0"',
        # "upgrade-insecure-requests": "1",
        # "viewport-width": "980",
    }

    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Failed to fetch reel HTML: {exc}")
        return None

    html_text = response.text
    if not html_text:
        print("Received empty HTML response.")
        return None

    audio_cdn_link = extract_audio_cdn_link_from_html(html_text)
    if not audio_cdn_link:
        print("Audio CDN link not found in HTML.")
        return None

    return audio_cdn_link


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python reel_extractor_2.py <reel_url>")
        raise SystemExit(1)

    result = get_reel_audio_cdn_link(sys.argv[1])
    if result:
        print(result)
    else:
        print("Failed to extract audio CDN link.")
