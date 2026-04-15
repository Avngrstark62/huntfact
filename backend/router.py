from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from logging_config import get_logger
from schemas import StartHuntRequest, StartHuntResponse, HealthResponse
from config import settings
from db.database import db
from rmq.publisher import publish_task
from rmq.schemas import TaskMessage
from rmq.constants import EXTRACT_AUDIO, NOTIFY
from health import is_system_healthy, check_health_dependency
from redis import set_job_data

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
async def start_hunt(request: StartHuntRequest, session: Session = Depends(db.get_db), _: None = Depends(check_health_dependency)) -> StartHuntResponse:
    """
    Start a new hunt with video and CDN links.
    
    - **video_link**: URL of the video to analyze
    - **cdn_link**: CDN link for the video
    
    Returns the hunt result and status.
    """
    try:
        logger.info(f"Starting hunt with video: {request.video_link}, cdn: {request.cdn_link}")

        existing_hunt = db.get_hunt_by_video_link(session, str(request.video_link))
        
        if existing_hunt:
            logger.info(f"Hunt already exists for video: {request.video_link}")

            job_id = str(existing_hunt.id)
            job_state = {
                "result": existing_hunt.result
            }

            set_job_data(job_id, job_state, ttl=86400)
            logger.info(f"Initialized job state in Redis for hunt: {job_id}")

            task = TaskMessage(
                job_id=str(existing_hunt.id),
                step=NOTIFY,
                priority=4,
                payload={}
            )
        else:
            new_hunt = db.create_hunt(session, str(request.video_link))
            logger.info(f"Created new hunt with id: {new_hunt.id}")
            
            job_id = str(new_hunt.id)
            job_state = {
                "cdn_link": str(request.cdn_link),
                "audio_bytes": None,
                "utterances": [],
                "items": []
            }
            
            set_job_data(job_id, job_state, ttl=86400)
            logger.info(f"Initialized job state in Redis for hunt: {job_id}")
            
            task = TaskMessage(
                job_id=job_id,
                step=EXTRACT_AUDIO,
                priority=1,
                payload={}
            )
        
        await publish_task(task)
        logger.info(f"Task published: {task.step}")
        
        return StartHuntResponse(
            success=True,
            message="Hunt started successfully",
            result="Processing",
        )
            
    except Exception as e:
        logger.error(f"Unexpected error in start_hunt: {str(e)}", exc_info=settings.debug)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal Server Error"}
        )

