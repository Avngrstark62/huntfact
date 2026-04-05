from fastapi import FastAPI

from logging_config import setup_logging, get_logger
from config import settings
from router import router
from db.database import db, Base
from rmq.connection import rabbitmq

setup_logging()
logger = get_logger("app")

class App:
    def __init__(self):
        self.app = FastAPI(
            title=settings.app_name,
            debug=settings.debug,
        )
        self._register_startup_shutdown()
        self._register_routes()

    def _register_startup_shutdown(self):
        @self.app.on_event("startup")
        async def startup_event():
            try:
                Base.metadata.create_all(bind=db.engine)
                db.is_healthy = True
                logger.info("Database initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize database: {str(e)}", exc_info=True)
                db.is_healthy = False
            
            try:
                await rabbitmq.connect()
                channel = await rabbitmq.get_channel()
                await channel.declare_queue(
                    settings.queue_name,
                    durable=True,
                    arguments={"x-max-priority": settings.max_priority}
                )
                rabbitmq.is_healthy = True
                logger.info("RabbitMQ connection established successfully")
                logger.info(f"Queue '{settings.queue_name}' declared successfully")
            except Exception as e:
                logger.error(f"Failed to initialize RabbitMQ: {str(e)}", exc_info=True)
                rabbitmq.is_healthy = False

        @self.app.on_event("shutdown")
        async def shutdown_event():
            try:
                db.engine.dispose()
                logger.info("Database connections closed")
            except Exception as e:
                logger.error(f"Error closing database: {str(e)}", exc_info=True)
            
            try:
                await rabbitmq.close()
                logger.info("RabbitMQ connection closed")
            except Exception as e:
                logger.error(f"Error closing RabbitMQ: {str(e)}", exc_info=True)

    def _register_routes(self):
        self.app.include_router(router)

    def get_app(self) -> FastAPI:
        return self.app


app_instance = App()
app = app_instance.get_app()
