from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
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
HUNT_STATUS_FAILED = "failed"


def _require_hunt_metadata(hunt) -> None:
    if not hunt.title or not hunt.summary or hunt.trust_score is None:
        raise RuntimeError(
            f"Hunt metadata missing for hunt_id={hunt.id}. "
            "title/summary/trust_score must be set before serving this response."
        )


def _is_completed(hunt) -> bool:
    return hunt.status == HUNT_STATUS_COMPLETED


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
        async def _publish_hunt_workflow(hunt_id: int) -> None:
            job_id = str(uuid.uuid4())
            logger.info("Generated job_id: %s", job_id)
            await publish_workflow(
                WorkflowMessage(
                    workflow_id=job_id,
                    payload={
                        "hunt_id": hunt_id,
                        "fcm_token": request.fcm_token,
                        "cdn_link": str(request.cdn_link),
                    },
                )
            )
            logger.info("Workflow published for job_id: %s", job_id)

        logger.info(
            "Starting hunt for user_id=%s video=%s cdn=%s",
            authenticated_user.sub,
            request.video_link,
            request.cdn_link,
        )

        user_hunts_limit = db.get_or_create_user_hunts_limit(session, authenticated_user.sub)
        active_hunts_count = db.get_active_hunts_count_by_user_id(session, authenticated_user.sub)
        if active_hunts_count >= user_hunts_limit:
            logger.info(
                "Hunt limit reached for user_id=%s active_hunts=%s hunts_limit=%s",
                authenticated_user.sub,
                active_hunts_count,
                user_hunts_limit,
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": (
                        f"Hunt limit reached. You have {active_hunts_count} hunts in "
                        f"queued/processing/completed states with a limit of {user_hunts_limit}."
                    )
                },
            )

        video_link = str(request.video_link)
        existing_hunt = db.get_hunt_by_video_link(session, video_link)

        if existing_hunt is None:
            try:
                existing_hunt = db.create_hunt(
                    session,
                    video_link,
                    thumbnail_url=str(request.thumbnail_url) if request.thumbnail_url else None,
                    caption=request.caption,
                    creator_handle=request.creator_handle,
                    platform=request.platform,
                )
                logger.info("Created new hunt with id: %s", existing_hunt.id)
            except IntegrityError:
                logger.info("Concurrent hunt create detected for video=%s", video_link)
                existing_hunt = db.get_hunt_by_video_link(session, video_link)
                if existing_hunt is None:
                    raise

        db.add_hunt_user(session, existing_hunt.id, authenticated_user.sub)
        db.update_hunt_metadata(
            session,
            existing_hunt.id,
            thumbnail_url=str(request.thumbnail_url) if request.thumbnail_url else None,
            caption=request.caption,
            creator_handle=request.creator_handle,
            platform=request.platform,
        )

        if existing_hunt.status == HUNT_STATUS_COMPLETED and existing_hunt.result:
            logger.info("Returning completed hunt for video=%s", request.video_link)
            task = TaskMessage(
                step=NOTIFY,
                priority=10,
                payload={
                    "fcm_token": request.fcm_token,
                    "hunt_id": existing_hunt.id,
                },
            )
            await publish_task(task)
            logger.info("Task published: %s", task.step)
            _require_hunt_metadata(existing_hunt)

            return StartHuntResponse(
                success=True,
                message="Hunt started successfully",
                hunt_id=existing_hunt.id,
                status=HUNT_STATUS_COMPLETED,
                result=existing_hunt.result,
                title=existing_hunt.title,
                summary=existing_hunt.summary,
                trust_score=existing_hunt.trust_score,
            )

        if existing_hunt.status == HUNT_STATUS_QUEUED:
            existing_hunt, transitioned = db.transition_hunt_to_processing(
                session,
                existing_hunt.id,
            )
            if existing_hunt is None:
                raise RuntimeError("Hunt disappeared while transitioning to processing")
            if transitioned:
                logger.info("Queued hunt moved to processing for hunt_id=%s", existing_hunt.id)
                await _publish_hunt_workflow(existing_hunt.id)
            else:
                logger.info("Queued hunt already being processed for hunt_id=%s", existing_hunt.id)
            return StartHuntResponse(
                success=True,
                message="Hunt started successfully",
                hunt_id=existing_hunt.id,
                status=HUNT_STATUS_PROCESSING,
                result=None,
                title=existing_hunt.title,
                summary=existing_hunt.summary,
                trust_score=existing_hunt.trust_score,
            )

        if existing_hunt.status == HUNT_STATUS_PROCESSING:
            logger.info("Hunt already processing for hunt_id=%s", existing_hunt.id)
            return StartHuntResponse(
                success=True,
                message="Hunt started successfully",
                hunt_id=existing_hunt.id,
                status=HUNT_STATUS_PROCESSING,
                result=None,
                title=existing_hunt.title,
                summary=existing_hunt.summary,
                trust_score=existing_hunt.trust_score,
            )

        if existing_hunt.status == HUNT_STATUS_FAILED:
            existing_hunt, transitioned = db.transition_hunt_to_processing(
                session,
                existing_hunt.id,
                clear_result=True,
            )
            if existing_hunt is None:
                raise RuntimeError("Hunt disappeared while retrying failed status")
            if transitioned:
                logger.info("Retrying failed hunt for hunt_id=%s", existing_hunt.id)
                await _publish_hunt_workflow(existing_hunt.id)
            else:
                logger.info("Failed hunt already transitioned for hunt_id=%s", existing_hunt.id)
            return StartHuntResponse(
                success=True,
                message="Hunt started successfully",
                hunt_id=existing_hunt.id,
                status=HUNT_STATUS_PROCESSING,
                result=None,
                title=existing_hunt.title,
                summary=existing_hunt.summary,
                trust_score=existing_hunt.trust_score,
            )

        logger.info(
            "Unknown hunt status=%s for hunt_id=%s, treating as processing",
            existing_hunt.status,
            existing_hunt.id,
        )
        existing_hunt, transitioned = db.transition_hunt_to_processing(
            session,
            existing_hunt.id,
        )
        if existing_hunt is None:
            raise RuntimeError("Hunt disappeared while handling unknown status")
        if transitioned:
            await _publish_hunt_workflow(existing_hunt.id)

        return StartHuntResponse(
            success=True,
            message="Hunt started successfully",
            hunt_id=existing_hunt.id,
            status=HUNT_STATUS_PROCESSING,
            result=None,
            title=existing_hunt.title,
            summary=existing_hunt.summary,
            trust_score=existing_hunt.trust_score,
        )
             
    except Exception as e:
        logger.error(f"Unexpected error in start_hunt: {str(e)}", exc_info=settings.app.debug)
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
        if _is_completed(hunt):
            _require_hunt_metadata(hunt)

        return HuntResponse(
            id=hunt.id,
            video_link=hunt.video_link,
            status=hunt.status,
            result=hunt.result,
            title=hunt.title,
            summary=hunt.summary,
            trust_score=hunt.trust_score,
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
        logger.error(f"Unexpected error in get_hunt: {str(e)}", exc_info=settings.app.debug)
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
        responses: list[HuntResponse] = []
        for hunt in hunts:
            if _is_completed(hunt):
                _require_hunt_metadata(hunt)
            responses.append(HuntResponse(
                id=hunt.id,
                video_link=hunt.video_link,
                status=hunt.status,
                result=hunt.result,
                title=hunt.title,
                summary=hunt.summary,
                trust_score=hunt.trust_score,
                thumbnail_url=hunt.thumbnail_url,
                caption=hunt.caption,
                creator_handle=hunt.creator_handle,
                platform=hunt.platform,
                error_message=hunt.error_message,
                created_at=hunt.created_at,
                updated_at=hunt.updated_at,
                completed_at=hunt.completed_at,
            ))
        return responses
    except Exception as e:
        logger.error(f"Unexpected error in get_user_hunts: {str(e)}", exc_info=settings.app.debug)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal Server Error"},
        )
