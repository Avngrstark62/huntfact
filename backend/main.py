from logging_config import setup_logging, get_logger
from config import settings
from app import app

setup_logging()
logger = get_logger("main")

if __name__ == "__main__":
    logger.info(f"Starting {settings.app_name} on {settings.host}:{settings.port}")
    logger.info(f"Debug mode: {settings.debug}")
    import uvicorn
    uvicorn.run(
        "app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
