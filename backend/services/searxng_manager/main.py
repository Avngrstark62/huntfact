import logging

import uvicorn

from logging_config import get_logger, log_event, setup_logging
from services.searxng_manager.app import app

setup_logging()
logger = get_logger("services.searxng_manager.main")


if __name__ == "__main__":
    log_event(
        logger,
        level=logging.INFO,
        event="app.lifecycle.started",
        status="started",
        message="Starting SearXNG manager server",
        component="services.searxng_manager",
    )
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8090,
        reload=False,
    )
