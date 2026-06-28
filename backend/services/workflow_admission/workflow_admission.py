import asyncio
import hashlib
import logging

from sqlalchemy.orm import Session

from config import settings
from logging_config import get_logger, log_event, sanitize_url
from db.database import db
from rmq.publisher import publish_workflow
from rmq.schemas import WorkflowMessage

logger = get_logger("services.workflow_admission.workflow_admission")


def generate_workflow_id(video_link: str) -> str:
    return hashlib.sha256(video_link.encode("utf-8")).hexdigest()


class _WorkflowAdmissionAttemptError(Exception):
    def __init__(self, *, workflow_id: str, admission_created_by_this_call: bool):
        super().__init__("Workflow admission attempt failed")
        self.workflow_id = workflow_id
        self.admission_created_by_this_call = admission_created_by_this_call


def _retry_settings() -> tuple[int, float]:
    retry_count = max(1, settings.workflow_admission.retry_count)
    base_delay_seconds = max(0.0, settings.workflow_admission.retry_base_delay_ms / 1000.0)
    return retry_count, base_delay_seconds


async def _admit_and_publish_workflow_once(
    *,
    session: Session,
    hunt_id: int,
    video_link: str,
    cdn_link: str,
    fcm_token: str,
    context: dict | None = None,
) -> tuple[bool, str]:
    workflow_id = generate_workflow_id(video_link)
    workflow_message = WorkflowMessage(
        workflow_id=workflow_id,
        payload={
            "workflow_id": workflow_id,
            "hunt_id": hunt_id,
            "video_link": video_link,
            "cdn_link": cdn_link,
            "fcm_token": fcm_token,
            "context": {
                **(context or {}),
                "workflow_id": workflow_id,
                "hunt_id": hunt_id,
            },
        },
    )
    admitted = db.create_workflow_admission(
        session=session,
        workflow_id=workflow_id,
        video_link=video_link,
        hunt_id=hunt_id,
    )
    if not admitted:
        db.clear_workflow_admission_if_hunt_failed(
            session=session,
            workflow_id=workflow_id,
            hunt_id=hunt_id,
        )
        log_event(
            logger,
            level=logging.INFO,
            event="workflow.admission.succeeded",
            status="skipped",
            message="Workflow already admitted",
            workflow_id=workflow_id,
            hunt_id=hunt_id,
            video_link=sanitize_url(video_link),
        )
        return True, "Hunt is already processing."

    try:
        await publish_workflow(workflow_message)
    except Exception as publish_error:
        raise _WorkflowAdmissionAttemptError(
            workflow_id=workflow_id,
            admission_created_by_this_call=True,
        ) from publish_error

    log_event(
        logger,
        level=logging.INFO,
        event="workflow.admission.succeeded",
        status="succeeded",
        message="Workflow admitted and published",
        workflow_id=workflow_id,
        hunt_id=hunt_id,
    )
    return True, "Hunt started successfully"


async def admit_and_publish_workflow(
    *,
    session: Session,
    hunt_id: int,
    video_link: str,
    cdn_link: str,
    fcm_token: str,
    context: dict | None = None,
) -> tuple[bool, str]:
    retry_count, base_delay_seconds = _retry_settings()
    workflow_id = generate_workflow_id(video_link)
    last_error: Exception | None = None
    admission_created_by_this_call = False

    for attempt in range(1, retry_count + 1):
        try:
            return await _admit_and_publish_workflow_once(
                session=session,
                hunt_id=hunt_id,
                video_link=video_link,
                cdn_link=cdn_link,
                fcm_token=fcm_token,
                context=context,
            )
        except _WorkflowAdmissionAttemptError as attempt_error:
            last_error = attempt_error.__cause__ or attempt_error
            admission_created_by_this_call = (
                admission_created_by_this_call
                or attempt_error.admission_created_by_this_call
            )
        except Exception as workflow_error:
            last_error = workflow_error
            try:
                session.rollback()
            except Exception:
                pass

        if attempt >= retry_count:
            if admission_created_by_this_call:
                db.delete_workflow_admission(session, workflow_id)
            log_event(
                logger,
                level=logging.ERROR,
                event="workflow.admission.failed",
                status="failed",
                message="Workflow admission/publish failed after retries",
                workflow_id=workflow_id,
                hunt_id=hunt_id,
                attempt=retry_count,
                max_attempts=retry_count,
                error_type=type(last_error).__name__ if last_error is not None else None,
                error_message=str(last_error) if last_error is not None else "unknown error",
                exc_info=True,
            )
            return False, "Hunt failed previously. Please try again."

        delay_seconds = base_delay_seconds * (2 ** (attempt - 1))
        log_event(
            logger,
            level=logging.WARNING,
            event="workflow.admission.failed",
            status="retrying",
            message="Workflow admission/publish attempt failed; retrying",
            workflow_id=workflow_id,
            hunt_id=hunt_id,
            attempt=attempt,
            max_attempts=retry_count,
            delay_seconds=delay_seconds,
            error_type=type(last_error).__name__ if last_error is not None else None,
            error_message=str(last_error) if last_error is not None else "unknown error",
        )
        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)

    return False, "Hunt failed previously. Please try again."


def clear_workflow_admission(workflow_id: str | None) -> None:
    if not isinstance(workflow_id, str) or not workflow_id.strip():
        return

    session = db.SessionLocal()
    try:
        db.delete_workflow_admission(session, workflow_id.strip())
    except Exception as delete_error:
        log_event(
            logger,
            level=logging.ERROR,
            event="workflow.admission.failed",
            status="failed",
            message="Failed to clear workflow admission row",
            workflow_id=workflow_id,
            error_type=type(delete_error).__name__,
            error_message=str(delete_error),
            exc_info=True,
        )
    finally:
        session.close()
