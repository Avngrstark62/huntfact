"""
Extract the first audio CDN link from Instagram-style HTML payloads.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from services.reel_extractor.get_cdn_links_from_html import extract_cdn_links_from_html


def _is_audio_record(record: Dict[str, Any]) -> bool:
    content_type = str(record.get("content_type") or "").lower()
    mime_type = str(record.get("mime_type") or "").lower()
    codecs = str(record.get("codecs") or "").lower()

    if content_type == "audio":
        return True
    if mime_type.startswith("audio/"):
        return True
    if codecs.startswith(("mp4a", "opus", "vorbis", "ec-3", "ac-3")):
        return True
    return False


def extract_audio_cdn_link_from_html(html_text: str) -> Optional[str]:
    """
    Return the first CDN link identified as audio from HTML payload.
    """
    links = extract_cdn_links_from_html(html_text)
    for record in links:
        if _is_audio_record(record):
            url = record.get("url")
            if isinstance(url, str) and url:
                return url
    return None
