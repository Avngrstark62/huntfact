import json
import sys
from pathlib import Path

from services.reel_extractor.get_cdn_links_from_html import extract_cdn_links_from_html


def test_get_cdn_links_from_html(html_path: str) -> None:
    file_path = Path(html_path)
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return

    html_text = file_path.read_text(encoding="utf-8", errors="replace")
    links = extract_cdn_links_from_html(html_text)

    print(f"Input file: {file_path}")
    print(f"Total links found: {len(links)}")
    print("=" * 80)

    for idx, item in enumerate(links, 1):
        print(f"[{idx}]")
        print(f"  content_type: {item.get('content_type')}")
        print(f"  mime_type: {item.get('mime_type')}")
        print(f"  representation_id: {item.get('representation_id')}")
        print(f"  bandwidth: {item.get('bandwidth')}")
        print(f"  width: {item.get('width')}")
        print(f"  height: {item.get('height')}")
        print(f"  codecs: {item.get('codecs')}")
        print(f"  source: {item.get('source')}")
        print(f"  url: {item.get('url')}")
        print("-" * 80)

    print("Raw JSON:")
    print(json.dumps(links, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    default_html = "newfile3.html"
    target_path = sys.argv[1] if len(sys.argv) > 1 else default_html
    test_get_cdn_links_from_html(target_path)
