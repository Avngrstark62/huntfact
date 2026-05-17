from logging_config import setup_logging, get_logger
from config import settings
from app import app

setup_logging()
logger = get_logger("main")

if __name__ == "__main__":
    logger.info(
        f"Starting {settings.app.app_name} on {settings.app.host}:{settings.app.port}"
    )
    logger.info(f"Debug mode: {settings.app.debug}")
    import uvicorn
    uvicorn.run(
        "app:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.debug,
    )
