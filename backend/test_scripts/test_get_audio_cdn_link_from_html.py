import sys
from pathlib import Path

from services.reel_extractor.get_audio_cdn_link_from_html import extract_audio_cdn_link_from_html


def test_get_audio_cdn_link_from_html(html_path: str) -> None:
    file_path = Path(html_path)
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return

    html_text = file_path.read_text(encoding="utf-8", errors="replace")
    audio_url = extract_audio_cdn_link_from_html(html_text)

    print(f"Input file: {file_path}")
    if audio_url:
        print(f"Audio CDN link: {audio_url}")
    else:
        print("No audio CDN link found.")


if __name__ == "__main__":
    default_html = "newfile3.html"
    target_path = sys.argv[1] if len(sys.argv) > 1 else default_html
    test_get_audio_cdn_link_from_html(target_path)
