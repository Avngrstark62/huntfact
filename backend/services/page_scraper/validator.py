from logging_config import get_logger

logger = get_logger("services.page_scraper.validator")

MAX_CONTENT_SIZE = 2 * 1024 * 1024  # 2MB


def validate_response(response: dict) -> bool:
    """
    Validate HTTP response before extraction.
    
    Checks:
    - Status code == 200
    - Content-Type contains "text/html"
    - Content length < 2MB
    """
    if response.get("status") != 200:
        return False
    
    if not response.get("content"):
        return False
    
    content_length = len(response.get("content", "").encode("utf-8"))
    if content_length > MAX_CONTENT_SIZE:
        logger.warning(f"Content exceeds max size: {content_length}")
        return False
    
    return True
