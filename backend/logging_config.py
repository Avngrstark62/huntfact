import json
import logging
import os
import re
import sys
import traceback
from contextvars import ContextVar
from datetime import datetime, UTC
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from config import settings

_REQUEST_ID: ContextVar[str | None] = ContextVar("request_id", default=None)
_BUILTIN_LOG_RECORD_FIELDS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
    "asctime",
}
_ALLOWED_EVENTS = {
    "app.lifecycle.started",
    "app.lifecycle.succeeded",
    "app.lifecycle.failed",
    "app.lifecycle.cancelled",
    "http.request.received",
    "http.request.completed",
    "http.request.failed",
    "auth.check.started",
    "auth.check.succeeded",
    "auth.check.failed",
    "workflow.admission.started",
    "workflow.admission.succeeded",
    "workflow.admission.failed",
    "workflow.started",
    "workflow.completed",
    "workflow.failed",
    "workflow.cancelled",
    "task.publish.started",
    "task.publish.succeeded",
    "task.publish.failed",
    "task.started",
    "task.succeeded",
    "task.failed",
    "task.retrying",
    "task.timed_out",
    "task.cancelled",
    "rmq.connection.started",
    "rmq.connection.succeeded",
    "rmq.connection.failed",
    "rmq.consume.started",
    "rmq.message.received",
    "rmq.message.acked",
    "rmq.message.rejected",
    "rmq.message.quarantined",
    "rmq.publish.started",
    "rmq.publish.succeeded",
    "rmq.publish.failed",
    "rmq.rpc.reply.received",
    "rmq.rpc.reply.failed",
    "db.query.started",
    "db.query.succeeded",
    "db.query.failed",
    "db.write.started",
    "db.write.succeeded",
    "db.write.failed",
    "provider.request.started",
    "provider.request.succeeded",
    "provider.request.failed",
    "provider.request.timed_out",
}


def set_request_id(request_id: str | None) -> None:
    _REQUEST_ID.set(request_id)


def get_request_id() -> str | None:
    return _REQUEST_ID.get()


def clear_request_id() -> None:
    _REQUEST_ID.set(None)


def hash_user_id(user_id: str | None) -> str | None:
    value = (user_id or "").strip()
    if not value:
        return None
    return sha256(value.encode("utf-8")).hexdigest()[:16]


def sanitize_url(url: str | None) -> str | None:
    value = (url or "").strip()
    if not value:
        return None
    try:
        parsed = urlsplit(value)
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    except Exception:
        return None


def _normalize_status(status: str) -> str:
    allowed = {
        "started",
        "succeeded",
        "failed",
        "retrying",
        "timed_out",
        "cancelled",
        "quarantined",
        "skipped",
    }
    return status if status in allowed else "started"


def _default_component(logger: logging.Logger) -> str:
    prefix = "huntfact."
    if logger.name.startswith(prefix):
        return logger.name[len(prefix):]
    return logger.name


def _normalize_event(event: str) -> str:
    if event in _ALLOWED_EVENTS:
        return event
    return "log.message"


def _sanitize_filename_component(value: str | None, fallback: str = "service") -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9._-]+", "-", (value or "").strip().lower())
    sanitized = sanitized.strip("._-")
    return sanitized or fallback


def _resolve_process_label() -> str:
    script_name = Path(sys.argv[0] or "").stem
    if script_name and script_name.lower() not in {"python", "python3"}:
        return _sanitize_filename_component(script_name)
    return _sanitize_filename_component(settings.logging.service_name)


def _build_json_log_path() -> Path:
    log_dir = Path(settings.logging.log_dir or "logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"{_resolve_process_label()}-{os.getpid()}.jsonl"


class JsonFormatter(logging.Formatter):
    def __init__(self, include_source: bool = False) -> None:
        super().__init__()
        self._include_source = include_source

    def format(self, record: logging.LogRecord) -> str:
        request_id = getattr(record, "request_id", None) or get_request_id()
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "service": getattr(record, "service", settings.logging.service_name),
            "component": getattr(record, "component", _default_component(logging.getLogger(record.name))),
            "event": _normalize_event(getattr(record, "event", "log.message")),
            "status": _normalize_status(getattr(record, "status", "started")),
            "message": record.getMessage(),
            "logger": record.name,
        }
        if request_id:
            payload["request_id"] = request_id

        for key, value in record.__dict__.items():
            if key in _BUILTIN_LOG_RECORD_FIELDS or key in payload:
                continue
            if value is not None:
                payload[key] = value

        if record.exc_info:
            payload["stacktrace"] = "".join(traceback.format_exception(*record.exc_info))
            if "error_type" not in payload and record.exc_info[0] is not None:
                payload["error_type"] = record.exc_info[0].__name__
            if "error_message" not in payload and record.exc_info[1] is not None:
                payload["error_message"] = str(record.exc_info[1])

        if self._include_source:
            payload["source"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }

        return json.dumps(payload, default=str, ensure_ascii=True)


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("huntfact")
    if logger.handlers:
        return logger

    handler = logging.StreamHandler()
    log_format = (settings.logging.format or "text").lower().strip()
    if log_format == "json":
        formatter: logging.Formatter = JsonFormatter(include_source=settings.logging.include_source)
    else:
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    file_handler = logging.FileHandler(_build_json_log_path(), encoding="utf-8")
    file_handler.setFormatter(JsonFormatter(include_source=settings.logging.include_source))
    logger.addHandler(file_handler)
    logger.setLevel(getattr(logging, (settings.logging.level or "INFO").upper(), logging.INFO))
    logger.propagate = False
    return logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"huntfact.{name}")


def log_event(
    logger: logging.Logger,
    *,
    level: int,
    event: str,
    status: str,
    message: str,
    component: str | None = None,
    exc_info: bool = False,
    **fields: Any,
) -> None:
    extra_fields = {
        "service": settings.logging.service_name,
        "component": component or _default_component(logger),
        "event": _normalize_event(event),
        "status": _normalize_status(status),
    }
    request_id = fields.get("request_id") or get_request_id()
    if request_id:
        extra_fields["request_id"] = request_id
    for key, value in fields.items():
        if value is not None:
            extra_fields[key] = value
    logger.log(level, message, extra=extra_fields, exc_info=exc_info)
