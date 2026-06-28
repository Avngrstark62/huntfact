from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from logging_config import get_logger
from schemas import StartHuntRequest, StartHuntResponse, HealthResponse, HuntResponse
from config import settings
from db.database import db
from services.notification_sender.notify_publish import publish_notify_best_effort
from services.workflow_admission.workflow_admission import admit_and_publish_workflow
from services.hunt_limits.hunt_limits import enforce_user_hunt_limit
from health import is_system_healthy, check_health_dependency
from auth.supabase_auth import AuthenticatedUser, get_authenticated_user

logger = get_logger("router")
router = APIRouter()
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
    
    Returns whether workflow publish was accepted.
    """
    try:
        logger.info(
            "Starting hunt for user_id=%s video=%s cdn=%s",
            authenticated_user.sub,
            request.video_link,
            request.cdn_link,
        )

        hunt_limit_response = enforce_user_hunt_limit(session, authenticated_user.sub)
        if hunt_limit_response is not None:
            return hunt_limit_response

        video_link = str(request.video_link)
        try:
            existing_hunt = db.get_or_create_hunt_in_txn(
                session,
                video_link,
                thumbnail_url=str(request.thumbnail_url) if request.thumbnail_url else None,
                caption=request.caption,
                creator_handle=request.creator_handle,
                platform=request.platform,
            )
            db.add_hunt_user_in_txn(session, existing_hunt.id, authenticated_user.sub)
            session.commit()
        except Exception:
            session.rollback()
            raise

        logger.info("Created or reused hunt with id: %s", existing_hunt.id)
        if existing_hunt.status == HUNT_STATUS_COMPLETED:
            await publish_notify_best_effort(existing_hunt.id, request.fcm_token)
            return StartHuntResponse(
                success=True,
                message="Hunt started successfully",
                hunt_id=existing_hunt.id,
            )

        try:
            admission_success, admission_message = await admit_and_publish_workflow(
                session=session,
                hunt_id=existing_hunt.id,
                video_link=video_link,
                cdn_link=str(request.cdn_link),
                fcm_token=request.fcm_token,
            )
        except Exception as publish_error:
            logger.error(
                "Workflow publish failed for hunt_id=%s: %s",
                existing_hunt.id,
                str(publish_error),
                exc_info=True,
            )
            return StartHuntResponse(
                success=False,
                message="Hunt failed to queue workflow",
                hunt_id=existing_hunt.id,
            )

        return StartHuntResponse(
            success=admission_success,
            message=admission_message,
            hunt_id=existing_hunt.id,
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
