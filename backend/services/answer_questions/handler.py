from typing import Any, Optional
from logging_config import get_logger
from services.answer_questions.answer_questions import answer_question
from rmq.schemas import TaskMessage
from rmq.constants import GENERATE_RESULT
from rmq_redis import job_repository

logger = get_logger("services.answer_questions.handler")


async def handle_answer_questions(job_id: str, payload: dict[str, Any] | None = None) -> Optional[TaskMessage]:
    """
    Answer questions using RAG-retrieved chunks.
    
    Fetches chunks from RAG for each question and sends to LLM for answering.
    """
    item_id = (payload or {}).get("item_id")
    if not item_id:
        logger.error(f"Missing item_id in ANSWER_QUESTIONS payload for job_id: {job_id}")
        raise RuntimeError(f"Missing item_id in payload for job_id={job_id}")

    logger.info(f"Starting per-item question answering for job_id: {job_id}, item_id: {item_id}")
    failed_item = False
    try:
        base_item = job_repository.get_item_base(job_id, item_id)
        if not base_item:
            logger.error(f"Item not found for job_id: {job_id}, item_id: {item_id}")
            job_repository.set_item_answer(job_id, item_id, None)
            failed_item = True
        else:
            question = base_item.get("question") or ""
            query = base_item.get("query") or ""
            answer = await answer_question(job_id, question, query)
            job_repository.set_item_answer(job_id, item_id, answer)
            if answer is None:
                failed_item = True
            logger.info(f"Per-item question answering completed for job_id: {job_id}, item_id: {item_id}")
    except Exception as e:
        logger.error(f"Error answering question for job_id: {job_id}, item_id: {item_id}: {str(e)}", exc_info=True)
        job_repository.set_item_answer(job_id, item_id, None)
        failed_item = True

    counted, done, total = job_repository.mark_qa_item_completed(job_id, item_id)
    if failed_item and counted:
        job_repository.increment_qa_failed(job_id)
    logger.info(
        f"Updated QA barrier for job_id: {job_id}, item_id: {item_id}, counted: {counted}, progress: {done}/{total}"
    )

    if total > 0 and done == total:
        lock_acquired = job_repository.try_acquire_generate_lock(job_id)
        logger.info(
            f"QA fan-in reached for job_id: {job_id}, lock_acquired: {lock_acquired}, done: {done}, total: {total}"
        )
        if lock_acquired:
            return TaskMessage(
                job_id=job_id,
                step=GENERATE_RESULT,
                priority=10,
                payload={},
            )
    return None
