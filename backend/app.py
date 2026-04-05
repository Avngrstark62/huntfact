import logging
from fastapi import FastAPI

from config import settings
from router import router
from db.database import db, Base

logger = logging.getLogger(__name__)


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

    def _register_routes(self):
        self.app.include_router(router)

    def get_app(self) -> FastAPI:
        return self.app


app_instance = App()
app = app_instance.get_app()
