import trafilatura
from bs4 import BeautifulSoup
from logging_config import get_logger

logger = get_logger("services.page_scraper.extractor")


def extract_content(html: str) -> dict:
    """
    Extract main content from HTML.
    
    Uses trafilatura as primary tool, falls back to BeautifulSoup.
    
    Returns:
        {
            "title": str | None,
            "text": str | None
        }
    """
    try:
        extracted = trafilatura.extract(html, include_comments=False)
        
        if extracted:
            title = trafilatura.extract_metadata(html).title if trafilatura.extract_metadata(html) else None
            return {
                "title": title,
                "text": extracted.strip()
            }
    except Exception as e:
        logger.warning(f"Trafilatura extraction failed: {str(e)}")
    
    return _fallback_extract(html)


def _fallback_extract(html: str) -> dict:
    """
    Fallback extraction using BeautifulSoup.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove unwanted tags
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        
        # Extract title
        title = None
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)
        
        # Extract main content
        main_content = soup.find("main") or soup.find("article") or soup.find("body")
        if main_content:
            text = main_content.get_text(separator=" ", strip=True)
            # Clean up whitespace
            text = " ".join(text.split())
            
            if text:
                return {
                    "title": title,
                    "text": text
                }
    except Exception as e:
        logger.warning(f"BeautifulSoup fallback failed: {str(e)}")
    
    return {
        "title": None,
        "text": None
    }
