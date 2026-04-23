from logging_config import setup_logging
setup_logging()

import asyncio
import sys
import time
import json
from rmq_redis import get_job_data
from rmq.constants import (
    EXTRACT_AUDIO, TRANSCRIBE, TRANSLATE, EXTRACT_QUESTIONS_QUERIES,
    FETCH_URLS, SELECT_URLS, FETCH_PAGES, SAVE_DATA_TO_RAG,
    ANSWER_QUESTIONS, GENERATE_RESULT, SAVE_RESULT_TO_DB, NOTIFY
)
from services.audio_extractor.handler import handle_extract_audio
from services.transcriber.handler import handle_transcribe
from services.translator.handler import handle_translate
from services.extract_questions_queries.handler import handle_extract_questions_queries
from services.fetch_urls.handler import handle_fetch_urls
from services.select_urls.handler import handle_select_urls
from services.fetch_pages.handler import handle_fetch_pages
from services.save_data_to_rag.handler import handle_save_data_to_rag
from services.answer_questions.handler import handle_answer_questions
from services.generate_result.handler import handle_generate_result
from services.save_result_to_db.handler import handle_save_result_to_db
from services.notification_sender.handler import handle_notify

HANDLERS = {
    EXTRACT_AUDIO: handle_extract_audio,
    TRANSCRIBE: handle_transcribe,
    TRANSLATE: handle_translate,
    EXTRACT_QUESTIONS_QUERIES: handle_extract_questions_queries,
    FETCH_URLS: handle_fetch_urls,
    SELECT_URLS: handle_select_urls,
    FETCH_PAGES: handle_fetch_pages,
    SAVE_DATA_TO_RAG: handle_save_data_to_rag,
    ANSWER_QUESTIONS: handle_answer_questions,
    GENERATE_RESULT: handle_generate_result,
    SAVE_RESULT_TO_DB: handle_save_result_to_db,
    NOTIFY: handle_notify,
}


async def test_handler(job_id: str, service_name: str):
    if service_name not in HANDLERS:
        print(f"Error: Unknown service '{service_name}'")
        print(f"Available services: {', '.join(HANDLERS.keys())}")
        return
    
    job_state = get_job_data(job_id)
    if job_state is None:
        print(f"Error: Job state not found in Redis for job_id: {job_id}")
        return
    
    handler = HANDLERS[service_name]
    
    start_time = time.time()
    try:
        result = await handler(job_id, job_state)
        elapsed = time.time() - start_time
        
        print(f"Status: SUCCESS | Latency: {elapsed:.2f}s")
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"Status: FAILED | Latency: {elapsed:.2f}s | Error: {str(e)}")
        raise


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} <job_id> <service_name>")
        print(f"\nAvailable services:")
        for service in HANDLERS.keys():
            print(f"  - {service}")
        sys.exit(1)
    
    job_id = sys.argv[1]
    service_name = sys.argv[2]
    
    asyncio.run(test_handler(job_id, service_name))
