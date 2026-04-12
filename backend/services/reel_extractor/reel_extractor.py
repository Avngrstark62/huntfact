"""
Minimal Instagram Reel CDN URL extractor.
Stateless, browser-like extraction without login.
"""

import json
import re
import time
from typing import Optional
from urllib.parse import urlparse

import requests


def _get_browser_headers() -> dict:
    """
    Construct browser-like headers mimicking Chrome on Linux.
    Based on Instaloader's _default_http_header() pattern.
    """
    return {
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,en;q=0.8',
        'Content-Length': '0',
        'Host': 'www.instagram.com',
        'Origin': 'https://www.instagram.com',
        'Referer': 'https://www.instagram.com/',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        'X-Instagram-AJAX': '1',
        'X-Requested-With': 'XMLHttpRequest',
    }


def _extract_shortcode_from_url(url: str) -> Optional[str]:
    """
    Extract shortcode from Instagram URL.
    
    Supports:
    - https://www.instagram.com/reel/{shortcode}/
    - https://www.instagram.com/reels/{shortcode}/
    - https://www.instagram.com/p/{shortcode}/
    """
    parsed = urlparse(url)
    path = parsed.path.strip('/')
    
    # Match /reel/{shortcode}, /reels/{shortcode}, or /p/{shortcode}
    match = re.match(r'^(?:reels?|p)/([a-zA-Z0-9_-]+)', path)
    if match:
        return match.group(1)
    
    return None


def _extract_csrf_token(html: str) -> Optional[str]:
    """
    Extract CSRF token from HTML response.
    Looks for csrftoken in <script> tags or meta content.
    """
    # Try to find in script content: {"csrf_token":"..."}
    match = re.search(r'"csrf_token":"([a-zA-Z0-9]+)"', html)
    if match:
        return match.group(1)
    
    # Try meta tag: <meta name="csrf-token" content="...">
    match = re.search(r'<meta[^>]*name="csrf-token"[^>]*content="([^"]*)"', html)
    if match:
        return match.group(1)
    
    return None


def get_reel_video_url(reel_url: str) -> Optional[str]:
    """
    Extract direct CDN video URL from Instagram reel link.
    
    Args:
        reel_url: Full Instagram reel URL (e.g., https://www.instagram.com/reel/ABC123/)
    
    Returns:
        CDN video URL (mp4) or None if extraction fails
    
    Flow:
    1. Extract shortcode from URL
    2. GET reel page to establish context and get CSRF token
    3. POST GraphQL query to fetch metadata
    4. Parse response and extract video_url
    """
    
    # Step 1: Extract shortcode
    shortcode = _extract_shortcode_from_url(reel_url)
    if not shortcode:
        print(f"❌ [Step 1] Failed to extract shortcode from URL: {reel_url}", file=__import__('sys').stderr)
        return None
    print(f"✓ [Step 1] Extracted shortcode: {shortcode}")
    
    try:
        # Step 2: Browse reel page (anti-bot evasion)
        session = requests.Session()
        headers = _get_browser_headers()
        
        page_url = f'https://www.instagram.com/reel/{shortcode}/'
        try:
            resp = session.get(page_url, headers=headers, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"❌ [Step 2] Failed to fetch reel page: {e}", file=__import__('sys').stderr)
            return None
        print(f"✓ [Step 2] Fetched reel page (status: {resp.status_code})")
        
        # Extract CSRF token from HTML
        csrf_token = _extract_csrf_token(resp.text)
        if not csrf_token:
            # Try to get from cookies as fallback
            csrf_token = session.cookies.get('csrftoken', '')
        
        if not csrf_token:
            print(f"❌ [Step 2] Failed to extract CSRF token from response", file=__import__('sys').stderr)
            return None
        print(f"✓ [Step 2] Extracted CSRF token")
        
        # Step 3: Simulate human reading time (anti-bot)
        time.sleep(0.2)
        
        # Step 4: GraphQL query (doc_id method - POST-based)
        graphql_headers = headers.copy()
        if 'Connection' in graphql_headers:
            del graphql_headers['Connection']
        if 'Content-Length' in graphql_headers:
            del graphql_headers['Content-Length']
        graphql_headers.update({
            'authority': 'www.instagram.com',
            'scheme': 'https',
            'accept': '*/*',
            'X-CSRFToken': csrf_token,
            'Referer': page_url,
        })
        
        # GraphQL variables and doc_id
        variables = json.dumps({'shortcode': shortcode}, separators=(',', ':'))
        doc_id = '8845758582119845'  # doc_id for shortcode media queries
        # doc_id = '34473019679012509'
        # doc_id = '33328371206806736'
        # doc_id = '26636510599312486'
        # doc_id = '25945596851746603'
        # doc_id = '34648316151419259'
        # doc_id = '9859601450795492'
        # doc_id = '9859601450795492'
        # doc_id = '27116338451299930'
        # doc_id = '24869955132672973'
        # doc_id = '25776299125399759'
        
        graphql_url = 'https://www.instagram.com/graphql/query'
        try:
            graphql_resp = session.post(
                graphql_url,
                headers=graphql_headers,
                data={
                    'variables': variables,
                    'doc_id': doc_id,
                    'server_timestamps': 'true'
                },
                timeout=10
            )
            graphql_resp.raise_for_status()
        except requests.RequestException as e:
            print(f"❌ [Step 4] GraphQL request failed: {e}", file=__import__('sys').stderr)
            return None
        print(f"✓ [Step 4] GraphQL query successful (status: {graphql_resp.status_code})")
        
        # Step 5: Parse response and extract video_url
        try:
            response_json = graphql_resp.json()
        except json.JSONDecodeError as e:
            print(f"❌ [Step 5] Failed to parse GraphQL response as JSON: {e}", file=__import__('sys').stderr)
            return None
        
        data_field = response_json.get('data')
        if data_field is None:
            print(f"❌ [Step 5] 'data' field is None in response", file=__import__('sys').stderr)
            return None
        
        if not isinstance(data_field, dict):
            print(f"❌ [Step 5] 'data' field is not a dict: {type(data_field)}", file=__import__('sys').stderr)
            return None
        
        media_data = data_field.get('xdt_shortcode_media')
        
        if not media_data:
            print(f"❌ [Step 5] 'xdt_shortcode_media' is null or unavailable", file=__import__('sys').stderr)
            return None
        
        # Extract video_url from metadata
        video_url = media_data.get('video_url')
        
        if video_url:
            print(f"✓ [Step 5] Extracted video URL")
            return video_url
        
        # Check if it's a video but URL is missing
        if media_data.get('is_video'):
            print(f"❌ [Step 5] Media is video but video_url field is missing", file=__import__('sys').stderr)
            return None
        
        print(f"❌ [Step 5] Media is not a video (is_video: {media_data.get('is_video')})", file=__import__('sys').stderr)
        return None
    
    except Exception as e:
        print(f"❌ [Unknown] Unexpected error: {e}", file=__import__('sys').stderr)
        return None


if __name__ == '__main__':
    # Test example
    import sys
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
        result = get_reel_video_url(url)
        if result:
            print(f"✓ Video URL: {result}")
        else:
            print("✗ Failed to extract video URL")
    else:
        print("Usage: python reel_extractor.py <reel_url>")
        print("Example: python reel_extractor.py https://www.instagram.com/reel/ABC123xyz/")
