import uvicorn

from config import settings
from logger import get_logger
from app import app

logger = get_logger(__name__)

if __name__ == "__main__":
    logger.info(f"Starting {settings.app_name} on {settings.host}:{settings.port}")
    logger.info(f"Debug mode: {settings.debug}")
    uvicorn.run(
        "app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
