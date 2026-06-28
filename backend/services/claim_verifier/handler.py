from typing import Any, Optional
import logging

from logging_config import get_logger, log_event
from services.claim_verifier.claim_verifier import verify_claims_with_context

logger = get_logger("services.claim_verifier.handler")


async def handle_claim_verifier(payload: dict[str, Any] | None = None) -> Optional[dict]:
    trace_context = ((payload or {}).get("context") if isinstance(payload, dict) else {}) or {}
    trace_context = trace_context if isinstance(trace_context, dict) else {}
    log_event(
        logger,
        level=logging.INFO,
        event="task.started",
        status="started",
        message="Starting claim verifier service",
        component="services.claim_verifier.handler",
        workflow_id=trace_context.get("workflow_id"),
        hunt_id=trace_context.get("hunt_id"),
        request_id=trace_context.get("request_id"),
        task_id=trace_context.get("task_id"),
        step=trace_context.get("step"),
    )

    body = payload or {}
    claims = body.get("claims")
    if not isinstance(claims, list):
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="No claims list found in payload",
            component="services.claim_verifier.handler",
            workflow_id=trace_context.get("workflow_id"),
            hunt_id=trace_context.get("hunt_id"),
            request_id=trace_context.get("request_id"),
            task_id=trace_context.get("task_id"),
        )
        return {"table": None, "error": "No claims list found in payload"}

    rag_collection_name = body.get("rag_collection_name")
    if not isinstance(rag_collection_name, str):
        rag_reference = body.get("rag_reference")
        if isinstance(rag_reference, dict):
            maybe_collection_name = rag_reference.get("collection_name")
            if isinstance(maybe_collection_name, str):
                rag_collection_name = maybe_collection_name

    if not isinstance(rag_collection_name, str) or not rag_collection_name.strip():
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="No rag_collection_name found in payload",
            component="services.claim_verifier.handler",
            workflow_id=trace_context.get("workflow_id"),
            hunt_id=trace_context.get("hunt_id"),
            request_id=trace_context.get("request_id"),
            task_id=trace_context.get("task_id"),
        )
        return {"table": None, "error": "No rag_collection_name found in payload"}

    try:
        table = await verify_claims_with_context(claims, rag_collection_name.strip())
        log_event(
            logger,
            level=logging.INFO,
            event="task.succeeded",
            status="succeeded",
            message="Claim verifier service completed",
            component="services.claim_verifier.handler",
            workflow_id=trace_context.get("workflow_id"),
            hunt_id=trace_context.get("hunt_id"),
            request_id=trace_context.get("request_id"),
            task_id=trace_context.get("task_id"),
            result_summary={"row_count": len((table or {}).get("rows") or [])},
        )
        return {"table": table, "error": None}
    except Exception as e:
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="Claim verifier service failed",
            component="services.claim_verifier.handler",
            workflow_id=trace_context.get("workflow_id"),
            hunt_id=trace_context.get("hunt_id"),
            request_id=trace_context.get("request_id"),
            task_id=trace_context.get("task_id"),
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True,
        )
        return {"table": None, "error": str(e)}
