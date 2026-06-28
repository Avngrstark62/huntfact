"""
Extract CDN links and content types from Instagram-style HTML payloads.
"""

from __future__ import annotations

import json
from html import unescape
from html.parser import HTMLParser
from typing import Any, Dict, List
from urllib.parse import urlparse
import xml.etree.ElementTree as ET


MPD_NS = {"mpd": "urn:mpeg:dash:schema:mpd:2011"}


class _SjsScriptExtractor(HTMLParser):
    """Extract content of <script type="application/json" data-sjs> blocks."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._capture = False
        self._chunks: List[str] = []
        self.blocks: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[tuple[str, str | None]]) -> None:
        if tag.lower() != "script":
            return
        attrs_dict = {k.lower(): v for k, v in attrs}
        script_type = (attrs_dict.get("type") or "").lower()
        has_data_sjs = "data-sjs" in attrs_dict
        if script_type == "application/json" and has_data_sjs:
            self._capture = True
            self._chunks = []

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._capture:
            self.blocks.append("".join(self._chunks))
            self._capture = False
            self._chunks = []


def _is_http_url(value: str) -> bool:
    try:
        parsed = urlparse(value.strip())
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False


def _add_if_valid(records: List[Dict[str, Any]], record: Dict[str, Any]) -> None:
    url = record.get("url")
    if not isinstance(url, str):
        return
    candidate = unescape(url.strip())
    if not _is_http_url(candidate):
        return
    updated = dict(record)
    updated["url"] = candidate
    records.append(updated)


def _extract_from_mpd(manifest_xml: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    try:
        root = ET.fromstring(manifest_xml)
    except ET.ParseError:
        return records

    for adaptation in root.findall(".//mpd:AdaptationSet", MPD_NS):
        adaptation_content_type = adaptation.get("contentType")
        for rep in adaptation.findall("mpd:Representation", MPD_NS):
            base_url = rep.find("mpd:BaseURL", MPD_NS)
            if base_url is None or not base_url.text:
                continue
            _add_if_valid(
                records,
                {
                    "url": base_url.text,
                    "source": "video_dash_manifest.BaseURL",
                    "content_type": adaptation_content_type or rep.get("mimeType"),
                    "mime_type": rep.get("mimeType"),
                    "representation_id": rep.get("id"),
                    "bandwidth": rep.get("bandwidth"),
                    "width": rep.get("width"),
                    "height": rep.get("height"),
                    "codecs": rep.get("codecs"),
                },
            )
    return records


def _walk_payload(node: Any, records: List[Dict[str, Any]], path: str = "") -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            next_path = f"{path}.{key}" if path else key

            if key == "video_dash_manifest" and isinstance(value, str) and value:
                records.extend(_extract_from_mpd(value))

            if key in {"manifest_url", "progressive_url", "hls_playlist_url", "videoDashUrl"} and isinstance(value, str):
                _add_if_valid(
                    records,
                    {
                        "url": value,
                        "source": next_path,
                        "content_type": None,
                        "mime_type": None,
                        "representation_id": None,
                        "bandwidth": None,
                        "width": None,
                        "height": None,
                        "codecs": None,
                    },
                )

            if key == "video_versions" and isinstance(value, list):
                for idx, item in enumerate(value):
                    if not isinstance(item, dict):
                        continue
                    url = item.get("url")
                    if not isinstance(url, str):
                        continue
                    _add_if_valid(
                        records,
                        {
                            "url": url,
                            "source": f"{next_path}[{idx}].url",
                            "content_type": item.get("content_type"),
                            "mime_type": item.get("mime_type"),
                            "representation_id": None,
                            "bandwidth": None,
                            "width": item.get("width"),
                            "height": item.get("height"),
                            "codecs": item.get("codecs"),
                        },
                    )

            _walk_payload(value, records, next_path)
    elif isinstance(node, list):
        for idx, item in enumerate(node):
            _walk_payload(item, records, f"{path}[{idx}]")


def extract_cdn_links_from_html(html_text: str) -> List[Dict[str, Any]]:
    """
    Extract links from HTML payload and include content-type metadata when available.

    Returns list of dicts:
    - url
    - source
    - content_type
    - mime_type
    - representation_id
    - bandwidth
    - width
    - height
    - codecs
    """
    parser = _SjsScriptExtractor()
    parser.feed(html_text)
    parser.close()

    records: List[Dict[str, Any]] = []
    for block in parser.blocks:
        block = block.strip()
        if not block:
            continue
        try:
            payload = json.loads(block)
        except json.JSONDecodeError:
            continue
        _walk_payload(payload, records)

    # Deduplicate by URL while keeping first-seen metadata.
    deduped: List[Dict[str, Any]] = []
    seen_urls = set()
    for record in records:
        url = record.get("url")
        if not isinstance(url, str):
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append(record)
    return deduped
