from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import uuid

from logging_config import get_logger
from schemas import StartHuntRequest, StartHuntResponse, HealthResponse, HuntResponse
from config import settings
from db.database import db
from rmq.publisher import publish_task, publish_workflow
from rmq.schemas import TaskMessage, WorkflowMessage
from rmq.constants import NOTIFY
from health import is_system_healthy, check_health_dependency
from auth.supabase_auth import AuthenticatedUser, get_authenticated_user

logger = get_logger("router")
router = APIRouter()
HUNT_STATUS_QUEUED = "queued"
HUNT_STATUS_PROCESSING = "processing"
HUNT_STATUS_COMPLETED = "completed"


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
async def start_hunt(
    request: StartHuntRequest,
    session: Session = Depends(db.get_db),
    _: None = Depends(check_health_dependency),
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> StartHuntResponse:
    """
    Start a new hunt with video and CDN links.
    
    - **video_link**: URL of the video to analyze
    - **cdn_link**: CDN link for the video
    
    Returns the hunt result and status.
    """
    try:
        logger.info(
            "Starting hunt for user_id=%s video=%s cdn=%s",
            authenticated_user.sub,
            request.video_link,
            request.cdn_link,
        )

        existing_hunt = db.get_hunt_by_video_link(session, str(request.video_link))
        
        job_id = str(uuid.uuid4())
        logger.info(f"Generated job_id: {job_id}")
        
        if existing_hunt and existing_hunt.result:
            logger.info(f"Hunt already exists for video: {request.video_link} and has result")
            db.add_hunt_user(session, existing_hunt.id, authenticated_user.sub)
            db.update_hunt_metadata(
                session,
                existing_hunt.id,
                thumbnail_url=str(request.thumbnail_url) if request.thumbnail_url else None,
                caption=request.caption,
                creator_handle=request.creator_handle,
                platform=request.platform,
            )

            task = TaskMessage(
                step=NOTIFY,
                priority=9,
                payload={
                    "fcm_token": request.fcm_token,
                    "hunt_id": existing_hunt.id,
                }
            )
            await publish_task(task)
            logger.info(f"Task published: {task.step}")

            return StartHuntResponse(
                success=True,
                message="Hunt started successfully",
                hunt_id=existing_hunt.id,
                status=HUNT_STATUS_COMPLETED,
                result=existing_hunt.result,
            )

        if existing_hunt:
            logger.info(f"Hunt already exists for video: {request.video_link} but no result, reprocessing")
            
            new_hunt = existing_hunt
            db.add_hunt_user(session, new_hunt.id, authenticated_user.sub)
            db.update_hunt_status(session, new_hunt.id, HUNT_STATUS_PROCESSING)
            db.update_hunt_metadata(
                session,
                new_hunt.id,
                thumbnail_url=str(request.thumbnail_url) if request.thumbnail_url else None,
                caption=request.caption,
                creator_handle=request.creator_handle,
                platform=request.platform,
            )

            await publish_workflow(
                WorkflowMessage(
                    workflow_id=job_id,
                    payload={
                        "hunt_id": new_hunt.id,
                        "fcm_token": request.fcm_token,
                        "cdn_link": str(request.cdn_link),
                    },
                )
            )
            logger.info(f"Workflow published for job_id: {job_id}")

            return StartHuntResponse(
                success=True,
                message="Hunt started successfully",
                hunt_id=new_hunt.id,
                status=HUNT_STATUS_PROCESSING,
                result=None,
            )

        new_hunt = db.create_hunt(
            session,
            str(request.video_link),
            thumbnail_url=str(request.thumbnail_url) if request.thumbnail_url else None,
            caption=request.caption,
            creator_handle=request.creator_handle,
            platform=request.platform,
        )
        logger.info(f"Created new hunt with id: {new_hunt.id}")
        db.add_hunt_user(session, new_hunt.id, authenticated_user.sub)
        db.update_hunt_status(session, new_hunt.id, HUNT_STATUS_PROCESSING)
        
        await publish_workflow(
            WorkflowMessage(
                workflow_id=job_id,
                payload={
                    "hunt_id": new_hunt.id,
                    "fcm_token": request.fcm_token,
                    "cdn_link": str(request.cdn_link),
                },
            )
        )
        logger.info(f"Workflow published for job_id: {job_id}")

        return StartHuntResponse(
            success=True,
            message="Hunt started successfully",
            hunt_id=new_hunt.id,
            status=HUNT_STATUS_PROCESSING,
            result=None,
        )
             
    except Exception as e:
        logger.error(f"Unexpected error in start_hunt: {str(e)}", exc_info=settings.debug)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal Server Error"}
        )


@router.get("/hunts/{hunt_id}", response_model=HuntResponse, tags=["hunts"])
async def get_hunt(
    hunt_id: int,
    session: Session = Depends(db.get_db),
    _: None = Depends(check_health_dependency),
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> HuntResponse:
    """
    Fetch one hunt by id.
    """
    try:
        logger.info("Fetching hunt for user_id=%s hunt_id=%s", authenticated_user.sub, hunt_id)
        hunt = db.get_hunt_for_user(session, hunt_id, authenticated_user.sub)
        if hunt is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": f"Hunt not found for hunt_id={hunt_id}"},
            )

        return HuntResponse(
            id=hunt.id,
            video_link=hunt.video_link,
            status=hunt.status,
            result=hunt.result,
            thumbnail_url=hunt.thumbnail_url,
            caption=hunt.caption,
            creator_handle=hunt.creator_handle,
            platform=hunt.platform,
            error_message=hunt.error_message,
            created_at=hunt.created_at,
            updated_at=hunt.updated_at,
            completed_at=hunt.completed_at,
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_hunt: {str(e)}", exc_info=settings.debug)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal Server Error"},
        )


@router.get("/hunts", response_model=list[HuntResponse], tags=["hunts"])
async def get_user_hunts(
    session: Session = Depends(db.get_db),
    _: None = Depends(check_health_dependency),
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> list[HuntResponse]:
    """
    Fetch all hunts associated with the authenticated user.
    """
    try:
        logger.info("Fetching hunts for user_id=%s", authenticated_user.sub)
        hunts = db.get_hunts_by_user_id(session, authenticated_user.sub)
        return [
            HuntResponse(
                id=hunt.id,
                video_link=hunt.video_link,
                status=hunt.status,
                result=hunt.result,
                thumbnail_url=hunt.thumbnail_url,
                caption=hunt.caption,
                creator_handle=hunt.creator_handle,
                platform=hunt.platform,
                error_message=hunt.error_message,
                created_at=hunt.created_at,
                updated_at=hunt.updated_at,
                completed_at=hunt.completed_at,
            )
            for hunt in hunts
        ]
    except Exception as e:
        logger.error(f"Unexpected error in get_user_hunts: {str(e)}", exc_info=settings.debug)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal Server Error"},
        )
