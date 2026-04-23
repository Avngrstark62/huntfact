from datetime import datetime, timezone
from typing import Any, Iterator, Optional

from logging_config import get_logger
from rmq.constants import (
    ANSWER_QUESTIONS,
    EXTRACT_AUDIO,
    EXTRACT_QUESTIONS_QUERIES,
    FETCH_PAGES,
    FETCH_URLS,
    GENERATE_RESULT,
    NOTIFY,
    SAVE_DATA_TO_RAG,
    SAVE_RESULT_TO_DB,
    SELECT_URLS,
    TRANSCRIBE,
    TRANSLATE,
)

from . import codec
from .client import redis_client
from .keys import (
    job_audio_key,
    job_audio_meta_key,
    job_item_answer_key,
    job_item_base_key,
    job_item_selected_key,
    job_item_urls_key,
    job_items_index_key,
    job_keys_registry_key,
    job_meta_key,
    job_page_key,
    job_pages_index_key,
    job_result_key,
    job_steps_key,
    job_utterances_en_key,
    job_utterances_key,
)

logger = get_logger("redis.repository")

BASE_TTL_SECONDS = 86400
SHORT_TTL_SECONDS = 7200
PIPELINE_STEPS = [
    EXTRACT_AUDIO,
    TRANSCRIBE,
    TRANSLATE,
    EXTRACT_QUESTIONS_QUERIES,
    FETCH_URLS,
    SELECT_URLS,
    FETCH_PAGES,
    SAVE_DATA_TO_RAG,
    ANSWER_QUESTIONS,
    GENERATE_RESULT,
    SAVE_RESULT_TO_DB,
    NOTIFY,
]


class RedisJobRepository:
    def __init__(self) -> None:
        self.client = None

    def _client(self):
        if self.client is None:
            self.client = redis_client.connect()
        return self.client

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _refresh_ttl(self, redis_key: str, ttl: int) -> None:
        self._client().expire(redis_key, ttl)

    def _register_key(self, job_id: str, redis_key: str, ttl: int) -> None:
        registry_key = job_keys_registry_key(job_id)
        self._client().sadd(registry_key, redis_key)
        self._refresh_ttl(registry_key, BASE_TTL_SECONDS)
        self._refresh_ttl(redis_key, ttl)

    def _set_json(self, job_id: str, redis_key: str, value: Any, ttl: int, nx: bool = False) -> bool:
        payload = codec.dumps(value)
        written = bool(self._client().set(redis_key, payload, nx=nx))
        if written or not nx:
            self._register_key(job_id, redis_key, ttl)
        return written

    def _get_json(self, redis_key: str) -> Any:
        return codec.loads(self._client().get(redis_key))

    def init_job(self, job_id: str, meta: dict, ttl: int = BASE_TTL_SECONDS) -> None:
        now = self._now()
        meta_payload = {
            "status": "queued",
            "current_step": "",
            "created_at": now,
            "updated_at": now,
            **meta,
        }

        meta_key = job_meta_key(job_id)
        steps_key = job_steps_key(job_id)
        self._client().hset(meta_key, mapping={k: str(v) for k, v in meta_payload.items() if v is not None})
        self._register_key(job_id, meta_key, ttl)

        step_states = {step: "pending" for step in PIPELINE_STEPS}
        self._client().hset(steps_key, mapping=step_states)
        self._register_key(job_id, steps_key, ttl)

    def set_step_state(self, job_id: str, step: str, state: str) -> None:
        steps_key = job_steps_key(job_id)
        self._client().hset(steps_key, step, state)
        self._register_key(job_id, steps_key, BASE_TTL_SECONDS)

    def get_step_state(self, job_id: str, step: str) -> Optional[str]:
        return self._client().hget(job_steps_key(job_id), step)

    def set_job_status(
        self,
        job_id: str,
        status: str,
        current_step: Optional[str] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        fields: dict[str, Optional[str]] = {"status": status, "updated_at": self._now()}
        if current_step is not None:
            fields["current_step"] = current_step
        fields["error_code"] = error_code
        fields["error_message"] = error_message
        self.set_meta_fields(job_id, fields)

    def set_meta_fields(self, job_id: str, fields: dict) -> None:
        meta_key = job_meta_key(job_id)
        values_to_set = {k: str(v) for k, v in fields.items() if v is not None}
        values_to_clear = [k for k, v in fields.items() if v is None]
        if values_to_set:
            self._client().hset(meta_key, mapping=values_to_set)
        if values_to_clear:
            self._client().hdel(meta_key, *values_to_clear)
        self._register_key(job_id, meta_key, BASE_TTL_SECONDS)

    def get_meta_fields(self, job_id: str, fields: list[str]) -> dict:
        meta_key = job_meta_key(job_id)
        values = self._client().hmget(meta_key, fields)
        return {field: value for field, value in zip(fields, values)}

    def job_exists(self, job_id: str) -> bool:
        return self._client().exists(job_meta_key(job_id)) > 0

    def delete_job(self, job_id: str) -> None:
        registry_key = job_keys_registry_key(job_id)
        job_keys = self._client().smembers(registry_key)
        if job_keys:
            self._client().delete(*job_keys)
        self._client().delete(registry_key)

    def register_job_key(self, job_id: str, redis_key: str) -> None:
        self._register_key(job_id, redis_key, BASE_TTL_SECONDS)

    def iter_job_keys(self, job_id: str) -> Iterator[str]:
        for redis_key in self._client().smembers(job_keys_registry_key(job_id)):
            yield redis_key

    def set_utterances(self, job_id: str, utterances: Any) -> None:
        self._set_json(job_id, job_utterances_key(job_id), utterances, BASE_TTL_SECONDS)

    def get_utterances(self, job_id: str) -> Any:
        return self._get_json(job_utterances_key(job_id))

    def set_utterances_en(self, job_id: str, utterances_en: Any) -> None:
        self._set_json(job_id, job_utterances_en_key(job_id), utterances_en, BASE_TTL_SECONDS)

    def get_utterances_en(self, job_id: str) -> Any:
        return self._get_json(job_utterances_en_key(job_id))

    def set_result(self, job_id: str, result: Any) -> None:
        self._set_json(job_id, job_result_key(job_id), result, BASE_TTL_SECONDS)

    def get_result(self, job_id: str) -> Any:
        return self._get_json(job_result_key(job_id))

    def set_items_base(self, job_id: str, items: list[dict]) -> None:
        index_key = job_items_index_key(job_id)
        self._client().delete(index_key)
        item_ids = [f"item_{index}" for index, _ in enumerate(items)]
        if item_ids:
            self._client().rpush(index_key, *item_ids)
            self._register_key(job_id, index_key, BASE_TTL_SECONDS)

        for item_id, item in zip(item_ids, items):
            payload = {
                "question": item.get("question"),
                "query": item.get("query"),
            }
            self._set_json(job_id, job_item_base_key(job_id, item_id), payload, BASE_TTL_SECONDS, nx=True)

    def get_item_base(self, job_id: str, item_id: str) -> Any:
        return self._get_json(job_item_base_key(job_id, item_id))

    def set_item_urls(self, job_id: str, item_id: str, urls: list) -> None:
        self._set_json(
            job_id,
            job_item_urls_key(job_id, item_id),
            {"urls": urls},
            BASE_TTL_SECONDS,
            nx=True,
        )

    def get_item_urls(self, job_id: str, item_id: str) -> Any:
        payload = self._get_json(job_item_urls_key(job_id, item_id))
        if payload is None:
            return None
        return payload.get("urls", [])

    def set_item_selected_urls(self, job_id: str, item_id: str, selected_urls: list) -> None:
        self._set_json(
            job_id,
            job_item_selected_key(job_id, item_id),
            {"selected_urls": selected_urls},
            BASE_TTL_SECONDS,
            nx=True,
        )

    def get_item_selected_urls(self, job_id: str, item_id: str) -> Any:
        payload = self._get_json(job_item_selected_key(job_id, item_id))
        if payload is None:
            return None
        return payload.get("selected_urls", [])

    def set_item_answer(self, job_id: str, item_id: str, answer: Any) -> None:
        self._set_json(
            job_id,
            job_item_answer_key(job_id, item_id),
            {"answer": answer},
            BASE_TTL_SECONDS,
            nx=True,
        )

    def get_item_answer(self, job_id: str, item_id: str) -> Any:
        payload = self._get_json(job_item_answer_key(job_id, item_id))
        if payload is None:
            return None
        return payload.get("answer")

    def iter_item_ids(self, job_id: str) -> Iterator[str]:
        item_ids = self._client().lrange(job_items_index_key(job_id), 0, -1)
        for item_id in item_ids:
            yield item_id

    def get_composed_items(self, job_id: str) -> list[dict]:
        items: list[dict] = []
        for item_id in self.iter_item_ids(job_id):
            item: dict[str, Any] = {"item_id": item_id}
            base = self.get_item_base(job_id, item_id) or {}
            urls = self.get_item_urls(job_id, item_id)
            selected_urls = self.get_item_selected_urls(job_id, item_id)
            answer = self.get_item_answer(job_id, item_id)

            item.update(base)
            if urls is not None:
                item["urls"] = urls
            if selected_urls is not None:
                item["selected_urls"] = selected_urls
            if answer is not None:
                item["answer"] = answer
            items.append(item)
        return items

    def set_audio(self, job_id: str, audio_b64: Optional[str], fmt: Optional[str], error: Optional[str] = None) -> None:
        audio_key = job_audio_key(job_id)
        if audio_b64 is not None:
            self._client().set(audio_key, audio_b64)
            self._register_key(job_id, audio_key, SHORT_TTL_SECONDS)

        meta_key = job_audio_meta_key(job_id)
        meta_payload = {}
        if fmt is not None:
            meta_payload["format"] = fmt
        if error is not None:
            meta_payload["error"] = error
        if meta_payload:
            self._client().hset(meta_key, mapping=meta_payload)
            self._register_key(job_id, meta_key, SHORT_TTL_SECONDS)

    def get_audio(self, job_id: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
        audio_b64 = self._client().get(job_audio_key(job_id))
        audio_meta = self._client().hgetall(job_audio_meta_key(job_id))
        return (
            audio_b64,
            audio_meta.get("format"),
            audio_meta.get("error"),
        )

    def delete_audio(self, job_id: str) -> None:
        self._client().delete(job_audio_key(job_id), job_audio_meta_key(job_id))

    def set_pages(self, job_id: str, pages_data: list[dict]) -> None:
        index_key = job_pages_index_key(job_id)
        self._client().delete(index_key)
        page_ids = [f"p{index}" for index, _ in enumerate(pages_data)]
        if page_ids:
            self._client().sadd(index_key, *page_ids)
            self._register_key(job_id, index_key, SHORT_TTL_SECONDS)

        for page_id, page in zip(page_ids, pages_data):
            payload = {
                "url": page.get("url"),
                "scraped_content": page.get("scraped_content"),
            }
            self._set_json(job_id, job_page_key(job_id, page_id), payload, SHORT_TTL_SECONDS, nx=True)

    def iter_pages(self, job_id: str) -> Iterator[dict]:
        page_ids = sorted(self._client().smembers(job_pages_index_key(job_id)))
        for page_id in page_ids:
            page = self._get_json(job_page_key(job_id, page_id))
            if page is not None:
                yield page

    def delete_pages(self, job_id: str) -> None:
        index_key = job_pages_index_key(job_id)
        page_ids = self._client().smembers(index_key)
        page_keys = [job_page_key(job_id, page_id) for page_id in page_ids]
        if page_keys:
            self._client().delete(*page_keys)
        self._client().delete(index_key)


job_repository = RedisJobRepository()
