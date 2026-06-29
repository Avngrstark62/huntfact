import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import aio_pika

from logging_config import (
    clear_request_id,
    get_logger,
    hash_user_id,
    log_event,
    set_request_id,
    setup_logging,
)
from config import settings
from router import router
from db.database import db, Base
import db.models as db_models  # noqa: F401
from rmq.connection import rabbitmq
from firebase_config import initialize_firebase
from chroma_client import chroma_client
from services.rate_limit import enforce_global_ip_rate_limit

setup_logging()
logger = get_logger("app")

class App:
    def __init__(self):
        self.app = FastAPI(
            title=settings.app.name,
            debug=settings.app.debug,
        )
        self._register_middleware()
        self._register_exception_handlers()
        self._register_startup_shutdown()
        self._register_routes()

    def _register_middleware(self):
        @self.app.middleware("http")
        async def request_logging_middleware(request: Request, call_next):
            request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
            request.state.request_id = request_id
            set_request_id(request_id)
            started_at = time.perf_counter()
            auth_user = getattr(request.state, "authenticated_user", None)

            log_event(
                logger,
                level=logging.INFO,
                event="http.request.received",
                status="started",
                message="HTTP request received",
                component="api",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                client_ip=request.client.host if request.client else None,
                user_id_hash=hash_user_id(getattr(auth_user, "sub", None)) if auth_user else None,
            )

            try:
                await enforce_global_ip_rate_limit(request)
                response = await call_next(request)
                duration_ms = int((time.perf_counter() - started_at) * 1000)
                response.headers["X-Request-ID"] = request_id
                log_event(
                    logger,
                    level=logging.INFO,
                    event="http.request.completed",
                    status="succeeded",
                    message="HTTP request completed",
                    component="api",
                    request_id=request_id,
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                )
                return response
            except HTTPException as exc:
                duration_ms = int((time.perf_counter() - started_at) * 1000)
                log_event(
                    logger,
                    level=logging.WARNING,
                    event="http.request.failed",
                    status="failed",
                    message="HTTP request rejected",
                    component="api",
                    request_id=request_id,
                    method=request.method,
                    path=request.url.path,
                    status_code=exc.status_code,
                    duration_ms=duration_ms,
                    error_type=type(exc).__name__,
                    error_message=str(exc.detail),
                )
                raise
            except Exception as exc:
                duration_ms = int((time.perf_counter() - started_at) * 1000)
                log_event(
                    logger,
                    level=logging.ERROR,
                    event="http.request.failed",
                    status="failed",
                    message="HTTP request failed",
                    component="api",
                    request_id=request_id,
                    method=request.method,
                    path=request.url.path,
                    duration_ms=duration_ms,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                    exc_info=True,
                )
                raise
            finally:
                clear_request_id()

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
            log_event(
                logger,
                level=logging.ERROR,
                event="app.lifecycle.failed",
                status="failed",
                message="Unhandled exception",
                component="api",
                request_id=getattr(request.state, "request_id", None),
                error_type=type(exc).__name__,
                error_message=str(exc),
                exc_info=True,
            )
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
                log_event(
                    logger,
                    level=logging.INFO,
                    event="app.lifecycle.succeeded",
                    status="succeeded",
                    message="Database initialized",
                    component="app",
                )
            except Exception as e:
                log_event(
                    logger,
                    level=logging.ERROR,
                    event="app.lifecycle.failed",
                    status="failed",
                    message="Failed to initialize database",
                    component="app",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    exc_info=True,
                )
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
                log_event(
                    logger,
                    level=logging.INFO,
                    event="app.lifecycle.succeeded",
                    status="succeeded",
                    message="RabbitMQ initialized and queues declared",
                    component="app",
                    task_queue=settings.rabbitmq.task_queue_name,
                    workflow_queue=settings.rabbitmq.workflow_queue_name,
                )
            except Exception as e:
                log_event(
                    logger,
                    level=logging.ERROR,
                    event="app.lifecycle.failed",
                    status="failed",
                    message="Failed to initialize RabbitMQ",
                    component="app",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    exc_info=True,
                )
                rabbitmq.is_healthy = False
            
            try:
                initialize_firebase()
                log_event(
                    logger,
                    level=logging.INFO,
                    event="app.lifecycle.succeeded",
                    status="succeeded",
                    message="Firebase initialized",
                    component="app",
                )
            except Exception as e:
                log_event(
                    logger,
                    level=logging.ERROR,
                    event="app.lifecycle.failed",
                    status="failed",
                    message="Failed to initialize Firebase",
                    component="app",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    exc_info=True,
                )
            
            try:
                chroma_client.connect()
                log_event(
                    logger,
                    level=logging.INFO,
                    event="app.lifecycle.succeeded",
                    status="succeeded",
                    message="ChromaDB connected",
                    component="app",
                )
            except Exception as e:
                log_event(
                    logger,
                    level=logging.ERROR,
                    event="app.lifecycle.failed",
                    status="failed",
                    message="Failed to initialize ChromaDB",
                    component="app",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    exc_info=True,
                )
                chroma_client.is_healthy = False

        @self.app.on_event("shutdown")
        async def shutdown_event():
            try:
                db.engine.dispose()
                log_event(
                    logger,
                    level=logging.INFO,
                    event="app.lifecycle.cancelled",
                    status="cancelled",
                    message="Database connections closed",
                    component="app",
                )
            except Exception as e:
                log_event(
                    logger,
                    level=logging.ERROR,
                    event="app.lifecycle.failed",
                    status="failed",
                    message="Error closing database",
                    component="app",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    exc_info=True,
                )
            
            try:
                await rabbitmq.close()
                log_event(
                    logger,
                    level=logging.INFO,
                    event="app.lifecycle.cancelled",
                    status="cancelled",
                    message="RabbitMQ connection closed",
                    component="app",
                )
            except Exception as e:
                log_event(
                    logger,
                    level=logging.ERROR,
                    event="app.lifecycle.failed",
                    status="failed",
                    message="Error closing RabbitMQ",
                    component="app",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    exc_info=True,
                )
            
            try:
                chroma_client.disconnect()
                log_event(
                    logger,
                    level=logging.INFO,
                    event="app.lifecycle.cancelled",
                    status="cancelled",
                    message="ChromaDB connection closed",
                    component="app",
                )
            except Exception as e:
                log_event(
                    logger,
                    level=logging.ERROR,
                    event="app.lifecycle.failed",
                    status="failed",
                    message="Error closing ChromaDB",
                    component="app",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    exc_info=True,
                )

    def _register_routes(self):
        self.app.include_router(router)

    def get_app(self) -> FastAPI:
        return self.app


app_instance = App()
app = app_instance.get_app()
