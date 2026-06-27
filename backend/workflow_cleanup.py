import asyncio
import signal

from db.database import db
from logging_config import get_logger, setup_logging

logger = get_logger("workflow_cleanup")
STALE_PROCESSING_MINUTES = 5
CLEANUP_INTERVAL_SECONDS = 30


def _run_cleanup_cycle() -> tuple[list[int], int]:
    session = db.SessionLocal()
    try:
        stale_hunt_ids = db.mark_stale_processing_hunts_failed(
            session,
            stale_minutes=STALE_PROCESSING_MINUTES,
        )
        deleted_admissions = db.delete_workflow_admissions_for_failed_hunts(session)
        return stale_hunt_ids, deleted_admissions
    finally:
        session.close()


async def main() -> None:
    setup_logging()
    logger.info("Starting workflow cleanup process...")

    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def handle_shutdown(signum, frame) -> None:
        logger.info("Received signal %s, stopping workflow cleanup...", signum)
        stop_event.set()

    loop.add_signal_handler(signal.SIGTERM, handle_shutdown, signal.SIGTERM, None)
    loop.add_signal_handler(signal.SIGINT, handle_shutdown, signal.SIGINT, None)

    while not stop_event.is_set():
        try:
            stale_hunt_ids, deleted_admissions = _run_cleanup_cycle()
            if stale_hunt_ids or deleted_admissions:
                logger.info(
                    "Cleanup cycle completed: stale_hunts_marked_failed=%s admissions_deleted=%s",
                    stale_hunt_ids,
                    deleted_admissions,
                )
        except Exception as e:
            logger.error("Workflow cleanup cycle failed: %s", str(e), exc_info=True)
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)

    logger.info("Workflow cleanup process stopped")


if __name__ == "__main__":
    asyncio.run(main())
