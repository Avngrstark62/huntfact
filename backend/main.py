import logging
import uvicorn

from config import settings
from app import app

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info(f"Starting {settings.app_name} on {settings.host}:{settings.port}")
    logger.info(f"Debug mode: {settings.debug}")
    uvicorn.run(
        "app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
