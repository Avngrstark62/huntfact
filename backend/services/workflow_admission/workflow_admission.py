import hashlib

from sqlalchemy.orm import Session

from logging_config import get_logger
from db.database import db
from rmq.publisher import publish_workflow
from rmq.schemas import WorkflowMessage

logger = get_logger("services.workflow_admission.workflow_admission")


def generate_workflow_id(video_link: str) -> str:
    return hashlib.sha256(video_link.encode("utf-8")).hexdigest()


async def admit_and_publish_workflow(
    *,
    session: Session,
    hunt_id: int,
    video_link: str,
    cdn_link: str,
    fcm_token: str,
) -> tuple[bool, str]:
    workflow_id = generate_workflow_id(video_link)
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
        logger.info(
            "Workflow already admitted for video_link=%s workflow_id=%s hunt_id=%s",
            video_link,
            workflow_id,
            hunt_id,
        )
        return True, "Hunt is already processing"

    try:
        await publish_workflow(
            WorkflowMessage(
                workflow_id=workflow_id,
                payload={
                    "workflow_id": workflow_id,
                    "hunt_id": hunt_id,
                    "video_link": video_link,
                    "cdn_link": cdn_link,
                    "fcm_token": fcm_token,
                },
            )
        )
    except Exception:
        db.delete_workflow_admission(session, workflow_id)
        raise

    logger.info(
        "Workflow admitted and published: workflow_id=%s hunt_id=%s",
        workflow_id,
        hunt_id,
    )
    return True, "Hunt started successfully"


def clear_workflow_admission(workflow_id: str | None) -> None:
    if not isinstance(workflow_id, str) or not workflow_id.strip():
        return

    session = db.SessionLocal()
    try:
        db.delete_workflow_admission(session, workflow_id.strip())
    except Exception as delete_error:
        logger.error(
            "Failed to clear workflow admission row: workflow_id=%s error=%s",
            workflow_id,
            str(delete_error),
            exc_info=True,
        )
    finally:
        session.close()
