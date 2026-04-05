from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse

from logging_config import get_logger
from schemas import StartHuntRequest, StartHuntResponse, HealthResponse
from config import settings
from rmq.connection import rabbitmq
from health import is_system_healthy, check_health_dependency

logger = get_logger("router")
router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
def get_health() -> HealthResponse:
    """
    Health check endpoint.
    
    Returns the current server health status and database connectivity.
    """
    if not is_system_healthy():
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "message": "Database or RabbitMQ connection failed"
            }
        )
    
    return HealthResponse(
        status="healthy",
        message="Server is running"
    )


@router.post("/start-hunt", response_model=StartHuntResponse, tags=["hunts"])
def start_hunt(request: StartHuntRequest, _: None = Depends(check_health_dependency)) -> StartHuntResponse:
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

