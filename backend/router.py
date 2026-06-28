import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from logging_config import get_logger, hash_user_id, log_event, sanitize_url
from schemas import (
    ErrorResponse,
    HealthResponse,
    HuntResponse,
    StartHuntRequest,
    StartHuntResponse,
)
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
COMMON_ERROR_RESPONSES = {
    422: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["health"],
    responses={
        **COMMON_ERROR_RESPONSES,
        503: {"model": ErrorResponse},
    },
)
def get_health() -> HealthResponse:
    """
    Health check endpoint.
    
    Returns the current server health status and database connectivity.
    """
    if not is_system_healthy():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database or RabbitMQ connection failed",
        )
    
    return HealthResponse(
        status="healthy",
        message="Server is running"
    )


@router.post(
    "/start-hunt",
    response_model=StartHuntResponse,
    tags=["hunts"],
    responses={
        **COMMON_ERROR_RESPONSES,
        429: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def start_hunt(
    request: StartHuntRequest,
    http_request: Request,
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
        request_id = getattr(http_request.state, "request_id", None)
        user_id_hash = hash_user_id(authenticated_user.sub)
        log_event(
            logger,
            level=logging.INFO,
            event="workflow.admission.started",
            status="started",
            message="Starting hunt admission",
            component="api",
            request_id=request_id,
            user_id_hash=user_id_hash,
            platform=request.platform,
            has_thumbnail=bool(request.thumbnail_url),
            has_caption=bool(request.caption),
            has_creator_handle=bool(request.creator_handle),
            video_link=sanitize_url(str(request.video_link)),
            cdn_link=sanitize_url(str(request.cdn_link)),
        )

        hunt_limit_error = enforce_user_hunt_limit(session, authenticated_user.sub)
        if hunt_limit_error is not None:
            raise hunt_limit_error

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

        log_event(
            logger,
            level=logging.INFO,
            event="db.write.succeeded",
            status="succeeded",
            message="Created or reused hunt",
            component="api",
            request_id=request_id,
            hunt_id=existing_hunt.id,
            user_id_hash=user_id_hash,
        )
        if existing_hunt.status == HUNT_STATUS_COMPLETED:
            await publish_notify_best_effort(
                existing_hunt.id,
                request.fcm_token,
                context={
                    "request_id": request_id,
                    "user_id_hash": user_id_hash,
                    "hunt_id": existing_hunt.id,
                },
            )
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
                context={
                    "request_id": request_id,
                    "user_id_hash": user_id_hash,
                    "hunt_id": existing_hunt.id,
                },
            )
        except Exception as publish_error:
            log_event(
                logger,
                level=logging.ERROR,
                event="workflow.admission.failed",
                status="failed",
                message="Workflow publish failed",
                component="api",
                request_id=request_id,
                hunt_id=existing_hunt.id,
                error_type=type(publish_error).__name__,
                error_message=str(publish_error),
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
             
    except HTTPException:
        raise
    except Exception as e:
        request_id = getattr(http_request.state, "request_id", None)
        log_event(
            logger,
            level=logging.ERROR,
            event="workflow.admission.failed",
            status="failed",
            message="Unexpected error in start_hunt",
            component="api",
            request_id=request_id,
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=settings.app.debug,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.get(
    "/hunts/{hunt_id}",
    response_model=HuntResponse,
    tags=["hunts"],
    responses={
        **COMMON_ERROR_RESPONSES,
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def get_hunt(
    hunt_id: int,
    http_request: Request,
    session: Session = Depends(db.get_db),
    _: None = Depends(check_health_dependency),
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> HuntResponse:
    """
    Fetch one hunt by id.
    """
    try:
        log_event(
            logger,
            level=logging.INFO,
            event="db.query.started",
            status="started",
            message="Fetching hunt",
            component="api",
            request_id=getattr(http_request.state, "request_id", None),
            hunt_id=hunt_id,
            user_id_hash=hash_user_id(authenticated_user.sub),
        )
        hunt = db.get_hunt_for_user(session, hunt_id, authenticated_user.sub)
        if hunt is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hunt not found for hunt_id={hunt_id}",
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
    except HTTPException:
        raise
    except Exception as e:
        log_event(
            logger,
            level=logging.ERROR,
            event="db.query.failed",
            status="failed",
            message="Unexpected error in get_hunt",
            component="api",
            request_id=getattr(http_request.state, "request_id", None),
            hunt_id=hunt_id,
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=settings.app.debug,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.get(
    "/hunts",
    response_model=list[HuntResponse],
    tags=["hunts"],
    responses={
        **COMMON_ERROR_RESPONSES,
        503: {"model": ErrorResponse},
    },
)
async def get_user_hunts(
    http_request: Request,
    session: Session = Depends(db.get_db),
    _: None = Depends(check_health_dependency),
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> list[HuntResponse]:
    """
    Fetch all hunts associated with the authenticated user.
    """
    try:
        log_event(
            logger,
            level=logging.INFO,
            event="db.query.started",
            status="started",
            message="Fetching hunts for user",
            component="api",
            request_id=getattr(http_request.state, "request_id", None),
            user_id_hash=hash_user_id(authenticated_user.sub),
        )
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
    except HTTPException:
        raise
    except Exception as e:
        log_event(
            logger,
            level=logging.ERROR,
            event="db.query.failed",
            status="failed",
            message="Unexpected error in get_user_hunts",
            component="api",
            request_id=getattr(http_request.state, "request_id", None),
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=settings.app.debug,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )
