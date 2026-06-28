import asyncio
import json
import signal

from pydantic import ValidationError
from logging_config import get_logger, setup_logging

from rmq.connection import rabbitmq
from rmq.consumer import start_workflow_consumer
from rmq.schemas import (
    TaskMessage,
    TaskRpcErrorResponse,
    TaskRpcSuccessResponse,
    WorkflowMessage,
    validate_task_step_result,
)
from rmq.publisher import publish_task_rpc
from services.workflow_admission.workflow_admission import clear_workflow_admission
from rmq.constants import (
    EXTRACT_AUDIO,
    TRANSCRIBE,
    TRANSLATE,
    EXTRACT_CLAIM_CLUSTERS,
    URL_FETCHER,
    WEB_SCRAPER,
    RAG_STORAGE,
    CLAIM_VERIFIER,
    SAVE_RESULT_TO_DB,
    NOTIFY,
)
from db.database import db

logger = get_logger("workflow_orchestrator")
TRANSCRIPTION_CORRECT = "TRANSCRIPTION_CORRECT"


async def _run_rpc_step(step: str, priority: int, payload: dict) -> tuple[dict | None, str | None]:
    try:
        response = await publish_task_rpc(
            TaskMessage(
                step=step,
                priority=priority,
                payload=payload,
            )
        )
    except Exception as e:
        return None, f"{step} RPC failed: {str(e)}"

    if isinstance(response, TaskRpcErrorResponse):
        return None, f"{step} failed: {response.error}"
    if not isinstance(response, TaskRpcSuccessResponse):
        return None, f"{step} failed: invalid RPC response type"
    if response.step != step:
        return None, f"{step} failed: RPC response step mismatch ({response.step})"

    try:
        validated_result = validate_task_step_result(step, response.result)
    except Exception as e:
        return None, f"{step} failed: invalid RPC result schema ({str(e)})"
    return validated_result, None


def _mark_hunt_failed(hunt_id: int | None, step: str, error: Exception) -> None:
    if not isinstance(hunt_id, int):
        return

    session = db.SessionLocal()
    try:
        db.update_hunt_status(
            session,
            hunt_id,
            "failed",
            f"step={step}; error={str(error)}",
        )
    except Exception as status_error:
        logger.error("Failed to update hunt failure status: %s", status_error, exc_info=True)
    finally:
        session.close()


def _mark_hunt_processing(hunt_id: int | None) -> None:
    if not isinstance(hunt_id, int):
        return

    session = db.SessionLocal()
    try:
        db.update_hunt_status(
            session,
            hunt_id,
            "processing",
            None,
        )
    except Exception as status_error:
        logger.error("Failed to update hunt processing status: %s", status_error, exc_info=True)
    finally:
        session.close()


def _handle_expected_workflow_failure(
    workflow_id: str | None,
    hunt_id: int | None,
    step: str,
    error_message: str,
) -> None:
    clear_workflow_admission(workflow_id)
    _mark_hunt_failed(
        hunt_id,
        step,
        RuntimeError(error_message),
    )
    logger.error(
        "Workflow failed at expected step: workflow_id=%s hunt_id=%s step=%s error=%s",
        workflow_id,
        hunt_id,
        step,
        error_message,
    )


def _handle_expected_input_failure(
    workflow_id: str | None,
    hunt_id: int | None,
    step: str,
    error_message: str,
) -> None:
    clear_workflow_admission(workflow_id)
    if isinstance(hunt_id, int):
        _mark_hunt_failed(hunt_id, step, RuntimeError(error_message))
    logger.error(
        "Workflow rejected at input validation: workflow_id=%s hunt_id=%s step=%s error=%s",
        workflow_id,
        hunt_id,
        step,
        error_message,
    )


def _transcribe_payload(extract_result: dict, service: str) -> dict:
    return {
        "audio_bytes_b64": extract_result.get("audio_bytes_b64"),
        "audio_format": extract_result.get("audio_format"),
        "transcriber_service": service,
    }


async def _run_parallel_transcription(
    extract_result: dict,
) -> tuple[dict | None, str | None, dict | None, str | None]:
    openai_transcribe_task = _run_rpc_step(
        step=TRANSCRIBE,
        priority=2,
        payload=_transcribe_payload(extract_result, "openai"),
    )
    assemblyai_transcribe_task = _run_rpc_step(
        step=TRANSCRIBE,
        priority=2,
        payload=_transcribe_payload(extract_result, "assemblyai"),
    )
    (openai_result, openai_error), (assemblyai_result, assemblyai_error) = await asyncio.gather(
        openai_transcribe_task,
        assemblyai_transcribe_task,
    )
    return openai_result, openai_error, assemblyai_result, assemblyai_error


def _build_no_verdict_table_for_cluster(cluster: list, explanation: str) -> dict:
    rows = []
    for claim in cluster:
        if not isinstance(claim, str):
            continue
        value = claim.strip()
        if not value:
            continue
        rows.append(
            {
                "claim": value,
                "verdict": "unverified",
                "confidence": 50,
                "sources": [],
                "explanation": explanation,
            }
        )
    return {"rows": rows}


async def _run_cluster_verification_loop(cluster: list) -> dict:
    """Run URL fetcher -> web scraper -> rag storage -> claim verifier for one cluster."""
    url_fetcher_result, url_fetcher_error = await _run_rpc_step(
        step=URL_FETCHER,
        priority=6,
        payload={"claims": cluster},
    )
    if url_fetcher_error:
        raise RuntimeError(url_fetcher_error)

    web_scraper_result, web_scraper_error = await _run_rpc_step(
        step=WEB_SCRAPER,
        priority=7,
        payload={
            "claims": cluster,
            "url_fetcher_results": url_fetcher_result,
        },
    )
    if web_scraper_error:
        raise RuntimeError(web_scraper_error)
    context = web_scraper_result.get("context") or {}
    context_sources = context.get("sources") if isinstance(context, dict) else None
    if not isinstance(context_sources, list) or not context_sources:
        logger.warning(
            "No context sources for cluster, returning fallback no-verdict rows: claims=%s",
            len(cluster),
        )
        return _build_no_verdict_table_for_cluster(
            cluster,
            "No sufficient web sources were found to verify this claim cluster.",
        )

    rag_storage_result, rag_storage_error = await _run_rpc_step(
        step=RAG_STORAGE,
        priority=8,
        payload={"context": context},
    )
    if rag_storage_error:
        raise RuntimeError(rag_storage_error)

    claim_verifier_result, claim_verifier_error = await _run_rpc_step(
        step=CLAIM_VERIFIER,
        priority=9,
        payload={
            "claims": cluster,
            "rag_reference": rag_storage_result.get("rag_reference"),
        },
    )
    if claim_verifier_error:
        raise RuntimeError(claim_verifier_error)
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


async def _run_cluster_fanout_and_merge(workflow_id: str, clusters: list) -> dict:
    valid_clusters = [cluster for cluster in clusters if isinstance(cluster, list) and cluster]
    logger.info(
        "Starting cluster fanout: workflow_id=%s clusters=%s",
        workflow_id,
        len(valid_clusters),
    )

    loop_tasks = [_run_cluster_verification_loop(cluster) for cluster in valid_clusters]
    cluster_results = await asyncio.gather(*loop_tasks, return_exceptions=True)
    cluster_tables = []

    for idx, result in enumerate(cluster_results):
        if isinstance(result, Exception):
            logger.error(
                "Cluster verification failed, using fallback table: workflow_id=%s cluster_index=%s error=%s",
                workflow_id,
                idx,
                str(result),
                exc_info=True,
            )
            cluster = valid_clusters[idx] if idx < len(valid_clusters) else []
            cluster_tables.append(
                _build_no_verdict_table_for_cluster(
                    cluster,
                    "Verification could not be completed for this claim cluster due to a processing error.",
                )
            )
            continue
        cluster_tables.append(result)

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
    return merged_table

async def handle_workflow_message(msg: dict) -> None:
    workflow_id = None
    hunt_id = None
    current_step = "WORKFLOW_INIT"
    payload = {}

    try:
        current_step = "VALIDATE_WORKFLOW_MESSAGE"
        try:
            workflow = WorkflowMessage.model_validate(msg)
        except ValidationError as validation_error:
            _handle_expected_input_failure(
                workflow_id=None,
                hunt_id=None,
                step=current_step,
                error_message=f"Invalid workflow message: {str(validation_error)}",
            )
            return

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
            _handle_expected_input_failure(
                workflow_id=workflow_id,
                hunt_id=None,
                step=current_step,
                error_message=f"Invalid hunt_id in workflow payload: {hunt_id}",
            )
            return

        _mark_hunt_processing(hunt_id)

        current_step = EXTRACT_AUDIO
        extract_result, extract_error = await _run_rpc_step(
            step=EXTRACT_AUDIO,
            priority=1,
            payload={"cdn_link": cdn_link},
        )
        if extract_error:
            _handle_expected_workflow_failure(workflow_id, hunt_id, current_step, extract_error)
            return

        logger.info("EXTRACT_AUDIO completed")

        current_step = TRANSCRIBE
        (
            openai_transcribe_result,
            openai_transcribe_error,
            assemblyai_transcribe_result,
            assemblyai_transcribe_error,
        ) = await _run_parallel_transcription(extract_result)
        if openai_transcribe_error:
            _handle_expected_workflow_failure(
                workflow_id,
                hunt_id,
                f"{current_step}_OPENAI",
                openai_transcribe_error,
            )
            return
        if assemblyai_transcribe_error:
            _handle_expected_workflow_failure(
                workflow_id,
                hunt_id,
                f"{current_step}_ASSEMBLYAI",
                assemblyai_transcribe_error,
            )
            return
        logger.info(
            "Parallel TRANSCRIBE completed: openai_chars=%s assemblyai_chars=%s",
            len(openai_transcribe_result.get("transcript_text") or ""),
            len(assemblyai_transcribe_result.get("transcript_text") or ""),
        )

        current_step = TRANSCRIPTION_CORRECT
        correction_result, correction_error = await _run_rpc_step(
            step=TRANSCRIPTION_CORRECT,
            priority=3,
            payload={
                "transcripts": [
                    openai_transcribe_result.get("transcript_text"),
                    assemblyai_transcribe_result.get("transcript_text"),
                ],
            },
        )
        if correction_error:
            _handle_expected_workflow_failure(workflow_id, hunt_id, current_step, correction_error)
            return
        logger.info(
            "TRANSCRIPTION_CORRECT completed: corrected_chars=%s",
            len(correction_result.get("corrected_transcript") or ""),
        )

        current_step = TRANSLATE
        translate_result, translate_error = await _run_rpc_step(
            step=TRANSLATE,
            priority=4,
            payload={
                "transcript_text": correction_result.get("corrected_transcript"),
            },
        )
        if translate_error:
            _handle_expected_workflow_failure(workflow_id, hunt_id, current_step, translate_error)
            return
        logger.info(f"TRANSLATE completed: {translate_result}")

        current_step = EXTRACT_CLAIM_CLUSTERS
        claim_extract_result, claim_extract_error = await _run_rpc_step(
            step=EXTRACT_CLAIM_CLUSTERS,
            priority=5,
            payload={
                "content": translate_result.get("translated_text"),
            },
        )
        if claim_extract_error:
            _handle_expected_workflow_failure(workflow_id, hunt_id, current_step, claim_extract_error)
            return
        logger.info(f"EXTRACT_CLAIM_CLUSTERS completed: {claim_extract_result}")

        clusters = claim_extract_result.get("clusters") or []
        if not isinstance(clusters, list):
            _handle_expected_workflow_failure(
                workflow_id,
                hunt_id,
                current_step,
                "EXTRACT_CLAIM_CLUSTERS returned invalid clusters format",
            )
            return
        merged_table = await _run_cluster_fanout_and_merge(workflow_id, clusters)

        current_step = SAVE_RESULT_TO_DB
        _, save_error = await _run_rpc_step(
            step=SAVE_RESULT_TO_DB,
            priority=10,
            payload={
                "hunt_id": hunt_id,
                "table": merged_table,
            },
        )
        if save_error:
            _handle_expected_workflow_failure(workflow_id, hunt_id, current_step, save_error)
            return

        logger.info(
            "Workflow completed at SAVE_RESULT_TO_DB: workflow_id=%s hunt_id=%s transcript_chars=%s translated_chars=%s clusters=%s merged_rows=%s",
            workflow_id,
            hunt_id,
            len(correction_result.get("corrected_transcript") or ""),
            len(translate_result.get("translated_text") or ""),
            len(claim_extract_result.get("clusters") or []),
            len(merged_table.get("rows") or []),
        )
    except Exception as e:
        logger.error(
            "Unexpected workflow exception: workflow_id=%s hunt_id=%s step=%s error=%s body=%s",
            workflow_id,
            hunt_id,
            current_step,
            str(e),
            json.dumps(msg)[:500],
            exc_info=True,
        )
        return

    current_step = NOTIFY
    notify_status = "sent"
    try:
        _, notify_error = await _run_rpc_step(
            step=NOTIFY,
            priority=11,
            payload={
                "hunt_id": hunt_id,
                "fcm_token": payload.get("fcm_token"),
            },
        )
        if notify_error:
            raise RuntimeError(notify_error)
    except Exception as e:
        notify_status = "failed"
        logger.error(
            "Workflow completed but notification failed: workflow_id=%s hunt_id=%s error=%s",
            workflow_id,
            hunt_id,
            str(e),
            exc_info=True,
        )

    logger.info(
        "Workflow processing finished: workflow_id=%s hunt_id=%s completion=completed notify_status=%s",
        workflow_id,
        hunt_id,
        notify_status,
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
