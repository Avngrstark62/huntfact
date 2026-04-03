from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from config import settings
from logger import get_logger
from routes.health import router as health_router
from routes.hunt import router as hunt_router
from exceptions import AppException

logger = get_logger(__name__)


class App:
    def __init__(self):
        self.app = FastAPI(
            title=settings.app_name,
            debug=settings.debug,
        )
        self._register_middleware()
        self._register_exception_handlers()
        self._register_routes()
        logger.info(f"App initialized: {settings.app_name}")

    def _register_middleware(self):
        @self.app.middleware("http")
        async def log_requests(request: Request, call_next):
            logger.info(f"{request.method} {request.url.path}")
            try:
                response = await call_next(request)
                logger.info(f"{request.method} {request.url.path} - {response.status_code}")
                return response
            except Exception as e:
                logger.error(f"{request.method} {request.url.path} - Exception: {str(e)}", exc_info=True)
                raise

    def _register_exception_handlers(self):
        @self.app.exception_handler(AppException)
        async def app_exception_handler(request: Request, exc: AppException):
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.detail,
            )

        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "success": False,
                },
            )

    def _register_routes(self):
        self.app.include_router(health_router)
        self.app.include_router(hunt_router)

    def get_app(self) -> FastAPI:
        return self.app


app_instance = App()
app = app_instance.get_app()
