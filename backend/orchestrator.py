import asyncio
import json
import signal

from logging_config import get_logger, setup_logging

from rmq.connection import rabbitmq
from rmq.consumer import start_workflow_consumer
from rmq.schemas import WorkflowMessage, TaskMessage
from rmq.publisher import publish_task_rpc
from rmq.constants import (
    EXTRACT_AUDIO,
    TRANSCRIBE,
    TRANSLATE,
    EXTRACT_CLAIM_CLUSTERS,
    URL_FETCHER,
    WEB_SCRAPER,
    CLAIM_VERIFIER,
    SAVE_RESULT_TO_DB,
    NOTIFY,
)
from db.database import db

logger = get_logger("workflow_orchestrator")


async def _run_cluster_verification_loop(cluster: list) -> dict:
    """Run URL fetcher -> web scraper -> claim verifier for one cluster."""
    url_fetcher_response = await publish_task_rpc(
        TaskMessage(
            step=URL_FETCHER,
            priority=5,
            payload={"claims": cluster},
        )
    )
    if url_fetcher_response.get("status") != "success":
        raise RuntimeError(f"URL_FETCHER failed: {url_fetcher_response}")
    url_fetcher_result = url_fetcher_response.get("result") or {}

    web_scraper_response = await publish_task_rpc(
        TaskMessage(
            step=WEB_SCRAPER,
            priority=6,
            payload={
                "claims": cluster,
                "url_fetcher_results": url_fetcher_result,
            },
        )
    )
    if web_scraper_response.get("status") != "success":
        raise RuntimeError(f"WEB_SCRAPER failed: {web_scraper_response}")
    web_scraper_result = web_scraper_response.get("result") or {}

    claim_verifier_response = await publish_task_rpc(
        TaskMessage(
            step=CLAIM_VERIFIER,
            priority=7,
            payload={
                "claims": cluster,
                "context": web_scraper_result.get("context"),
            },
        )
    )
    if claim_verifier_response.get("status") != "success":
        raise RuntimeError(f"CLAIM_VERIFIER failed: {claim_verifier_response}")
    claim_verifier_result = claim_verifier_response.get("result") or {}
    return claim_verifier_result.get("table") or {"rows": []}


def _merge_cluster_tables(cluster_tables: list[dict]) -> dict:
    """Merge per-cluster claim verifier tables into one table."""
    merged_rows = []
    for table in cluster_tables:
        if not isinstance(table, dict):
            continue
        rows = table.get("rows")
        if isinstance(rows, list):
            merged_rows.extend(rows)
    return {"rows": merged_rows}

async def handle_workflow_message(msg: dict) -> None:
    try:
        workflow = WorkflowMessage.model_validate(msg)
        workflow_id = workflow.workflow_id
        payload = workflow.payload
        cdn_link = payload.get("cdn_link")
        hunt_id = payload.get("hunt_id")
        logger.info(
            "Received workflow message: workflow_id=%s cdn_link=%s hunt_id=%s",
            workflow_id,
            cdn_link,
            hunt_id,
        )

        if not isinstance(hunt_id, int):
            raise RuntimeError(f"Invalid hunt_id in workflow payload: {hunt_id}")

        extract_response = await publish_task_rpc(
            TaskMessage(
                step=EXTRACT_AUDIO,
                priority=1,
                payload={"cdn_link": cdn_link},
            )
        )
        if extract_response.get("status") != "success":
            raise RuntimeError(f"EXTRACT_AUDIO failed: {extract_response}")
        extract_result = extract_response.get("result") or {}

        logger.info("EXTRACT_AUDIO completed")

        transcribe_response = await publish_task_rpc(
            TaskMessage(
                step=TRANSCRIBE,
                priority=2,
                payload={
                    "audio_bytes_b64": extract_result.get("audio_bytes_b64"),
                    "audio_format": extract_result.get("audio_format"),
                },
            )
        )
        if transcribe_response.get("status") != "success":
            raise RuntimeError(f"TRANSCRIBE failed: {transcribe_response}")
        transcribe_result = transcribe_response.get("result") or {}

        logger.info(f"TRANSCRIBE completed: {transcribe_result}")

        translate_response = await publish_task_rpc(
            TaskMessage(
                step=TRANSLATE,
                priority=3,
                payload={
                    "transcript_text": transcribe_result.get("transcript_text"),
                },
            )
        )
        if translate_response.get("status") != "success":
            raise RuntimeError(f"TRANSLATE failed: {translate_response}")
        translate_result = translate_response.get("result") or {}
        logger.info(f"TRANSLATE completed: {translate_result}")

        claim_extract_response = await publish_task_rpc(
            TaskMessage(
                step=EXTRACT_CLAIM_CLUSTERS,
                priority=4,
                payload={
                    "content": translate_result.get("translated_text"),
                },
            )
        )
        if claim_extract_response.get("status") != "success":
            raise RuntimeError(f"EXTRACT_CLAIM_CLUSTERS failed: {claim_extract_response}")
        claim_extract_result = claim_extract_response.get("result") or {}
        logger.info(f"EXTRACT_CLAIM_CLUSTERS completed: {claim_extract_result}")

        clusters = claim_extract_result.get("clusters") or []
        if not isinstance(clusters, list):
            raise RuntimeError("EXTRACT_CLAIM_CLUSTERS returned invalid clusters format")
        valid_clusters = [cluster for cluster in clusters if isinstance(cluster, list) and cluster]

        logger.info(
            "Starting cluster fanout: workflow_id=%s clusters=%s",
            workflow_id,
            len(valid_clusters),
        )

        loop_tasks = [_run_cluster_verification_loop(cluster) for cluster in valid_clusters]
        cluster_tables = await asyncio.gather(*loop_tasks)
        logger.info(
            "Cluster fanout completed: workflow_id=%s clusters=%s",
            workflow_id,
            cluster_tables,
        )
        merged_table = _merge_cluster_tables(cluster_tables)
        logger.info(
            "Cluster fan-in completed: workflow_id=%s rows=%s",
            workflow_id,
            len(merged_table.get("rows") or []),
        )

        save_result_response = await publish_task_rpc(
            TaskMessage(
                step=SAVE_RESULT_TO_DB,
                priority=8,
                payload={
                    "hunt_id": hunt_id,
                    "table": merged_table,
                },
            )
        )
        if save_result_response.get("status") != "success":
            raise RuntimeError(f"SAVE_RESULT_TO_DB failed: {save_result_response}")

        notify_response = await publish_task_rpc(
            TaskMessage(
                step=NOTIFY,
                priority=9,
                payload={
                    "hunt_id": hunt_id,
                    "fcm_token": payload.get("fcm_token"),
                },
            )
        )
        if notify_response.get("status") != "success":
            raise RuntimeError(f"NOTIFY failed: {notify_response}")

        logger.info(
            "Workflow RPC chain completed: workflow_id=%s transcript_chars=%s translated_chars=%s clusters=%s merged_rows=%s",
            workflow_id,
            len(transcribe_result.get("transcript_text") or ""),
            len(translate_result.get("translated_text") or ""),
            len(claim_extract_result.get("clusters") or []),
            len(merged_table.get("rows") or []),
        )

    except Exception as e:
        hunt_id = (msg or {}).get("payload", {}).get("hunt_id")
        if isinstance(hunt_id, int):
            session = db.SessionLocal()
            try:
                db.update_hunt_status(session, hunt_id, "failed", str(e))
            except Exception as status_error:
                logger.error("Failed to update hunt failure status: %s", status_error, exc_info=True)
            finally:
                session.close()
        logger.error(
            "Workflow execution failed: %s body=%s",
            e,
            json.dumps(msg)[:500],
            exc_info=True,
        )


async def main() -> None:
    setup_logging()
    logger.info("Starting workflow orchestrator...")

    loop = asyncio.get_event_loop()
    consumer_task = None

    def handle_shutdown(signum, frame) -> None:
        logger.info("Received signal %s, shutting down workflow orchestrator...", signum)
        if consumer_task and not consumer_task.done():
            consumer_task.cancel()

    loop.add_signal_handler(signal.SIGTERM, handle_shutdown, signal.SIGTERM, None)
    loop.add_signal_handler(signal.SIGINT, handle_shutdown, signal.SIGINT, None)

    try:
        consumer_task = asyncio.create_task(
            start_workflow_consumer(handle_workflow_message)
        )
        await consumer_task
    except asyncio.CancelledError:
        logger.info("Workflow consumer cancelled")
    finally:
        logger.info("Closing RabbitMQ connection...")
        try:
            await rabbitmq.close()
        except Exception as e:
            logger.error("Error closing RabbitMQ: %s", e, exc_info=True)
        logger.info("Workflow orchestrator stopped")


if __name__ == "__main__":
    asyncio.run(main())
