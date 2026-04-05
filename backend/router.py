import logging
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from schemas import StartHuntRequest, StartHuntResponse, HealthResponse
from config import settings
from db.database import db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
def get_health() -> HealthResponse:
    """
    Health check endpoint.
    
    Returns the current server health status and database connectivity.
    """
    if not db.is_healthy:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "message": "Database connection failed"
            }
        )
    
    return HealthResponse(
        status="healthy",
        message="Server is running"
    )


@router.post("/start-hunt", response_model=StartHuntResponse, tags=["hunts"])
def start_hunt(request: StartHuntRequest) -> StartHuntResponse:
    """
    Start a new hunt with a video link.
    
    - **video_link**: URL of the video to analyze
    
    Returns the hunt result and status.
    """
    try:
        logger.info(f"Starting hunt with video: {request.video_link}")
        
        result = StartHuntResponse(
            success=True,
            message="Hunt started successfully",
            result="this fact is true",
        )
        logger.info("Hunt started successfully")
        return result
    except Exception as e:
        logger.error(f"Unexpected error in start_hunt: {str(e)}", exc_info=settings.debug)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal Server Error"}
        )
