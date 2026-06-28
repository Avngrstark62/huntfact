import asyncio
import logging
import signal

from config import settings
from db.database import db
from logging_config import get_logger, log_event, setup_logging

logger = get_logger("workflow_cleanup")
STALE_PROCESSING_MINUTES = settings.workflow_cleanup.processing_stale_minutes
STALE_QUEUED_MINUTES = settings.workflow_cleanup.queued_stale_minutes
CLEANUP_INTERVAL_SECONDS = settings.workflow_cleanup.interval_seconds


def _run_cleanup_cycle() -> tuple[list[int], list[int], int]:
    session = db.SessionLocal()
    try:
        stale_processing_hunt_ids = db.mark_stale_processing_hunts_failed(
            session,
            stale_minutes=STALE_PROCESSING_MINUTES,
        )
        stale_queued_hunt_ids = db.mark_stale_queued_hunts_failed(
            session,
            stale_minutes=STALE_QUEUED_MINUTES,
        )
        deleted_admissions = db.delete_workflow_admissions_for_failed_hunts(session)
        return stale_processing_hunt_ids, stale_queued_hunt_ids, deleted_admissions
    finally:
        session.close()


async def main() -> None:
    setup_logging()
    log_event(
        logger,
        level=logging.INFO,
        event="app.lifecycle.started",
        status="started",
        message="Starting workflow cleanup process",
        component="workflow_cleanup",
    )

    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def handle_shutdown(signum, frame) -> None:
        log_event(
            logger,
            level=logging.INFO,
            event="app.lifecycle.cancelled",
            status="cancelled",
            message="Stopping workflow cleanup due to signal",
            component="workflow_cleanup",
            signal=signum,
        )
        stop_event.set()

    loop.add_signal_handler(signal.SIGTERM, handle_shutdown, signal.SIGTERM, None)
    loop.add_signal_handler(signal.SIGINT, handle_shutdown, signal.SIGINT, None)

    while not stop_event.is_set():
        try:
            stale_processing_hunt_ids, stale_queued_hunt_ids, deleted_admissions = _run_cleanup_cycle()
            if stale_processing_hunt_ids or stale_queued_hunt_ids or deleted_admissions:
                log_event(
                    logger,
                    level=logging.INFO,
                    event="app.lifecycle.succeeded",
                    status="succeeded",
                    message="Workflow cleanup cycle completed",
                    component="workflow_cleanup",
                    stale_processing_hunts=stale_processing_hunt_ids,
                    stale_queued_hunts=stale_queued_hunt_ids,
                    admissions_deleted=deleted_admissions,
                )
        except Exception as e:
            log_event(
                logger,
                level=logging.ERROR,
                event="app.lifecycle.failed",
                status="failed",
                message="Workflow cleanup cycle failed",
                component="workflow_cleanup",
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True,
            )
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)

    log_event(
        logger,
        level=logging.INFO,
        event="app.lifecycle.succeeded",
        status="cancelled",
        message="Workflow cleanup process stopped",
        component="workflow_cleanup",
    )


if __name__ == "__main__":
    asyncio.run(main())
