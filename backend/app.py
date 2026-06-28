from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import aio_pika

from logging_config import setup_logging, get_logger
from config import settings
from router import router
from db.database import db, Base
import db.models as db_models  # noqa: F401
from rmq.connection import rabbitmq
from firebase_config import initialize_firebase
from chroma_client import chroma_client

setup_logging()
logger = get_logger("app")

class App:
    def __init__(self):
        self.app = FastAPI(
            title=settings.app.name,
            debug=settings.app.debug,
        )
        self._register_exception_handlers()
        self._register_startup_shutdown()
        self._register_routes()

    def _register_exception_handlers(self):
        @self.app.exception_handler(RequestValidationError)
        async def validation_exception_handler(request: Request, exc: RequestValidationError):
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "detail": "Request validation failed",
                    "code": "VALIDATION_ERROR",
                },
            )

        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "detail": detail,
                    "code": "HTTP_ERROR",
                },
            )

        @self.app.exception_handler(Exception)
        async def unhandled_exception_handler(request: Request, exc: Exception):
            logger.error("Unhandled exception: %s", str(exc), exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "Internal Server Error",
                    "code": "INTERNAL_ERROR",
                },
            )

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
                dlx = await channel.declare_exchange(
                    settings.rabbitmq.dead_letter_exchange_name,
                    aio_pika.ExchangeType.DIRECT,
                    durable=True,
                )
                task_dlq = await channel.declare_queue(
                    settings.rabbitmq.task_dead_letter_queue_name,
                    durable=True,
                )
                workflow_dlq = await channel.declare_queue(
                    settings.rabbitmq.workflow_dead_letter_queue_name,
                    durable=True,
                )
                await task_dlq.bind(
                    dlx,
                    routing_key=settings.rabbitmq.task_dead_letter_routing_key,
                )
                await workflow_dlq.bind(
                    dlx,
                    routing_key=settings.rabbitmq.workflow_dead_letter_routing_key,
                )
                await channel.declare_queue(
                    settings.rabbitmq.task_queue_name,
                    durable=True,
                    arguments={
                        "x-max-priority": settings.rabbitmq.max_priority,
                        "x-dead-letter-exchange": settings.rabbitmq.dead_letter_exchange_name,
                        "x-dead-letter-routing-key": settings.rabbitmq.task_dead_letter_routing_key,
                    },
                )
                await channel.declare_queue(
                    settings.rabbitmq.workflow_queue_name,
                    durable=True,
                    arguments={
                        "x-dead-letter-exchange": settings.rabbitmq.dead_letter_exchange_name,
                        "x-dead-letter-routing-key": settings.rabbitmq.workflow_dead_letter_routing_key,
                    },
                )
                rabbitmq.is_healthy = True
                logger.info("RabbitMQ connection established successfully")
                logger.info(f"Queue '{settings.rabbitmq.task_queue_name}' declared successfully")
                logger.info(f"Queue '{settings.rabbitmq.workflow_queue_name}' declared successfully")
            except Exception as e:
                logger.error(f"Failed to initialize RabbitMQ: {str(e)}", exc_info=True)
                rabbitmq.is_healthy = False
            
            try:
                initialize_firebase()
                logger.info("Firebase initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Firebase: {str(e)}", exc_info=True)
            
            try:
                chroma_client.connect()
                logger.info("ChromaDB connection established successfully")
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB: {str(e)}", exc_info=True)
                chroma_client.is_healthy = False

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
            
            try:
                chroma_client.disconnect()
                logger.info("ChromaDB connection closed")
            except Exception as e:
                logger.error(f"Error closing ChromaDB: {str(e)}", exc_info=True)

    def _register_routes(self):
        self.app.include_router(router)

    def get_app(self) -> FastAPI:
        return self.app


app_instance = App()
app = app_instance.get_app()
