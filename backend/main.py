import logging

from logging_config import setup_logging, get_logger
from logging_config import log_event
from config import settings
from app import app

setup_logging()
logger = get_logger("main")

if __name__ == "__main__":
    log_event(
        logger,
        level=logging.INFO,
        event="app.lifecycle.started",
        status="started",
        message="Starting API server",
        component="main",
        app_name=settings.app.name,
        host=settings.app.host,
        port=settings.app.port,
    )
    log_event(
        logger,
        level=logging.INFO,
        event="app.lifecycle.started",
        status="started",
        message="API debug mode configuration",
        component="main",
        debug_mode=settings.app.debug,
    )
    import uvicorn
    uvicorn.run(
        "app:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.debug,
    )
