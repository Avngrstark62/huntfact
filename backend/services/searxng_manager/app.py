import asyncio
import logging
import secrets
import time
import uuid
from dataclasses import dataclass

import aiohttp
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from config import settings
from logging_config import clear_request_id, get_logger, log_event, set_request_id, setup_logging

setup_logging()
logger = get_logger("services.searxng_manager.app")

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


def _load_auth_token_from_env() -> str:
    token = settings.searxng_manager.auth_token.strip()
    if not token:
        raise ValueError("SEARXNG_MANAGER_AUTH_TOKEN is required")
    return token


def _extract_bearer_token(authorization_header: str | None) -> str | None:
    if not authorization_header:
        return None
    scheme, _, token = authorization_header.partition(" ")
    if scheme.lower() != "bearer":
        return None
    value = token.strip()
    if not value:
        return None
    return value


@dataclass(slots=True)
class BackendInstance:
    name: str
    base_url: str


class SearxngManager:
    def __init__(
        self,
        backends: list[BackendInstance],
        upstream_timeout_seconds: float,
        health_check_interval_seconds: float,
        health_check_timeout_seconds: float,
    ) -> None:
        if not backends:
            raise ValueError("At least one backend must be configured")
        self.backends = backends
        self.upstream_timeout_seconds = upstream_timeout_seconds
        self.health_check_interval_seconds = health_check_interval_seconds
        self.health_check_timeout_seconds = health_check_timeout_seconds
        self._busy: set[int] = set()
        self._unhealthy: set[int] = set()
        self._waiting_requests = 0
        self._condition = asyncio.Condition()
        self._health_check_task: asyncio.Task | None = None
        self._session: aiohttp.ClientSession | None = None

    async def startup(self) -> None:
        timeout = aiohttp.ClientTimeout(total=self.upstream_timeout_seconds)
        self._session = aiohttp.ClientSession(
            timeout=timeout,
            auto_decompress=False,
        )
        await self._run_health_checks_once()
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        log_event(
            logger,
            level=logging.INFO,
            event="app.lifecycle.succeeded",
            status="succeeded",
            message="SearXNG manager started",
            component="services.searxng_manager",
            backend_count=len(self.backends),
            upstream_timeout_seconds=self.upstream_timeout_seconds,
            health_check_interval_seconds=self.health_check_interval_seconds,
            health_check_timeout_seconds=self.health_check_timeout_seconds,
        )

    async def shutdown(self) -> None:
        if self._health_check_task is not None:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        if self._session is not None:
            await self._session.close()
        log_event(
            logger,
            level=logging.INFO,
            event="app.lifecycle.cancelled",
            status="cancelled",
            message="SearXNG manager stopped",
            component="services.searxng_manager",
        )

    async def acquire_backend(self, excluded_backends: set[int] | None = None) -> int | None:
        excluded = excluded_backends or set()
        async with self._condition:
            self._waiting_requests += 1
            try:
                while True:
                    routable_backends = [
                        backend_index
                        for backend_index in range(len(self.backends))
                        if backend_index not in self._unhealthy and backend_index not in excluded
                    ]
                    if not routable_backends:
                        return None
                    for backend_index in routable_backends:
                        if backend_index in self._busy:
                            continue
                        self._busy.add(backend_index)
                        return backend_index
                    await self._condition.wait()
            finally:
                self._waiting_requests = max(0, self._waiting_requests - 1)

    async def release_backend(self, backend_index: int) -> None:
        async with self._condition:
            self._busy.discard(backend_index)
            self._condition.notify_all()

    async def proxy(self, request: Request, backend_index: int) -> Response:
        if self._session is None:
            raise RuntimeError("Manager session is not initialized")

        backend = self.backends[backend_index]
        upstream_url = self._build_upstream_url(backend, request)
        request_body = await request.body()
        upstream_headers = self._prepare_upstream_headers(request)

        log_event(
            logger,
            level=logging.INFO,
            event="provider.request.started",
            status="started",
            message="Forwarding request to SearXNG backend",
            component="services.searxng_manager",
            backend=backend.name,
            backend_url=backend.base_url,
            method=request.method,
            path=request.url.path,
        )

        started_at = time.perf_counter()
        try:
            async with self._session.request(
                method=request.method,
                url=upstream_url,
                data=request_body,
                headers=upstream_headers,
                allow_redirects=False,
            ) as upstream_response:
                response_body = await upstream_response.read()
                duration_ms = int((time.perf_counter() - started_at) * 1000)
                response_headers = self._prepare_downstream_headers(upstream_response.headers)
                log_event(
                    logger,
                    level=logging.INFO,
                    event="provider.request.succeeded",
                    status="succeeded",
                    message="SearXNG backend request completed",
                    component="services.searxng_manager",
                    backend=backend.name,
                    status_code=upstream_response.status,
                    duration_ms=duration_ms,
                )
                return Response(
                    content=response_body,
                    status_code=upstream_response.status,
                    headers=response_headers,
                )
        except asyncio.TimeoutError as error:
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            log_event(
                logger,
                level=logging.ERROR,
                event="provider.request.timed_out",
                status="timed_out",
                message="SearXNG backend timed out",
                component="services.searxng_manager",
                backend=backend.name,
                duration_ms=duration_ms,
                error_type=type(error).__name__,
                error_message=str(error),
            )
            await self._mark_backend_unhealthy(
                backend_index,
                reason="request_timeout",
            )
            raise HTTPException(status_code=504, detail="Upstream SearXNG timed out") from error
        except Exception as error:
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            log_event(
                logger,
                level=logging.ERROR,
                event="provider.request.failed",
                status="failed",
                message="SearXNG backend request failed",
                component="services.searxng_manager",
                backend=backend.name,
                duration_ms=duration_ms,
                error_type=type(error).__name__,
                error_message=str(error),
                exc_info=True,
            )
            await self._mark_backend_unhealthy(
                backend_index,
                reason=f"request_failed:{type(error).__name__}",
            )
            raise HTTPException(status_code=502, detail="SearXNG backend request failed") from error

    def health(self) -> dict:
        busy = len(self._busy)
        unhealthy = len(self._unhealthy)
        total = len(self.backends)
        healthy = total - unhealthy
        return {
            "status": "ok" if healthy > 0 else "degraded",
            "total_backends": total,
            "healthy_backends": healthy,
            "unhealthy_backends": unhealthy,
            "busy_backends": busy,
            "idle_backends": max(0, healthy - busy),
            "queued_requests": self._waiting_requests,
        }

    async def _run_health_checks_once(self) -> None:
        for backend_index in range(len(self.backends)):
            await self._check_backend_health(backend_index)

    async def _health_check_loop(self) -> None:
        while True:
            await asyncio.sleep(self.health_check_interval_seconds)
            await self._run_health_checks_once()

    async def _check_backend_health(self, backend_index: int) -> None:
        if self._session is None:
            return
        async with self._condition:
            if backend_index in self._busy:
                return
        backend = self.backends[backend_index]
        health_url = f"{backend.base_url}/healthz"
        timeout = aiohttp.ClientTimeout(total=self.health_check_timeout_seconds)
        try:
            async with self._session.get(
                health_url,
                allow_redirects=False,
                timeout=timeout,
            ) as response:
                if response.status == 200:
                    await self._mark_backend_healthy(backend_index)
                    return
                log_event(
                    logger,
                    level=logging.WARNING,
                    event="provider.request.failed",
                    status="failed",
                    message="Backend health check returned non-200 status",
                    component="services.searxng_manager",
                    backend=backend.name,
                    health_url=health_url,
                    status_code=response.status,
                )
                await self._mark_backend_unhealthy(
                    backend_index,
                    reason=f"health_check_status:{response.status}",
                )
        except Exception as error:
            log_event(
                logger,
                level=logging.WARNING,
                event="provider.request.failed",
                status="failed",
                message="Backend health check failed",
                component="services.searxng_manager",
                backend=backend.name,
                health_url=health_url,
                error_type=type(error).__name__,
                error_message=str(error),
            )
            await self._mark_backend_unhealthy(
                backend_index,
                reason=f"health_check_failed:{type(error).__name__}",
            )

    async def _mark_backend_unhealthy(self, backend_index: int, reason: str) -> None:
        backend = self.backends[backend_index]
        async with self._condition:
            if backend_index in self._unhealthy:
                return
            self._unhealthy.add(backend_index)
            self._condition.notify_all()
        log_event(
            logger,
            level=logging.WARNING,
            event="provider.request.failed",
            status="failed",
            message="Backend marked unhealthy",
            component="services.searxng_manager",
            backend=backend.name,
            reason=reason,
        )

    async def _mark_backend_healthy(self, backend_index: int) -> None:
        backend = self.backends[backend_index]
        async with self._condition:
            if backend_index not in self._unhealthy:
                return
            self._unhealthy.discard(backend_index)
            self._condition.notify_all()
        log_event(
            logger,
            level=logging.INFO,
            event="provider.request.succeeded",
            status="succeeded",
            message="Backend marked healthy",
            component="services.searxng_manager",
            backend=backend.name,
        )

    @staticmethod
    def _prepare_upstream_headers(request: Request) -> dict[str, str]:
        headers: dict[str, str] = {}
        for name, value in request.headers.items():
            lower_name = name.lower()
            if lower_name in HOP_BY_HOP_HEADERS:
                continue
            if lower_name == "host":
                continue
            if lower_name == "authorization":
                continue
            headers[name] = value
        return headers

    @staticmethod
    def _prepare_downstream_headers(headers: aiohttp.typedefs.LooseHeaders) -> dict[str, str]:
        downstream_headers: dict[str, str] = {}
        for name, value in headers.items():
            if name.lower() in HOP_BY_HOP_HEADERS:
                continue
            downstream_headers[name] = value
        return downstream_headers

    @staticmethod
    def _build_upstream_url(backend: BackendInstance, request: Request) -> str:
        base = backend.base_url.rstrip("/")
        query = request.url.query
        url = f"{base}{request.url.path}"
        if query:
            return f"{url}?{query}"
        return url


def _load_backends_from_env() -> list[BackendInstance]:
    raw_backends = settings.searxng_manager.backends.strip()
    if not raw_backends:
        raise ValueError("SEARXNG_MANAGER_BACKENDS is required")

    backends: list[BackendInstance] = []
    for index, raw in enumerate(raw_backends.split(","), start=1):
        value = raw.strip()
        if not value:
            continue
        if value.endswith("/"):
            value = value[:-1]
        if not value.startswith("http://") and not value.startswith("https://"):
            raise ValueError(f"Invalid backend URL: {value}")
        backends.append(BackendInstance(name=f"searxng-{index}", base_url=value))

    if not backends:
        raise ValueError("No valid backend URLs provided")
    return backends


def _load_timeout_from_env() -> float:
    timeout = settings.searxng_manager.timeout_seconds
    if timeout <= 0:
        raise ValueError("SEARXNG_MANAGER_TIMEOUT_SECONDS must be greater than 0")
    return timeout


def _load_health_check_interval_from_env() -> float:
    interval = settings.searxng_manager.health_check_interval_seconds
    if interval <= 0:
        raise ValueError("SEARXNG_MANAGER_HEALTH_CHECK_INTERVAL_SECONDS must be greater than 0")
    return interval


def _load_health_check_timeout_from_env() -> float:
    timeout = settings.searxng_manager.health_check_timeout_seconds
    if timeout <= 0:
        raise ValueError("SEARXNG_MANAGER_HEALTH_CHECK_TIMEOUT_SECONDS must be greater than 0")
    return timeout


app = FastAPI(title="SearXNG Manager", debug=False)
auth_token = _load_auth_token_from_env()

manager = SearxngManager(
    backends=_load_backends_from_env(),
    upstream_timeout_seconds=_load_timeout_from_env(),
    health_check_interval_seconds=_load_health_check_interval_from_env(),
    health_check_timeout_seconds=_load_health_check_timeout_from_env(),
)


@app.middleware("http")
async def verify_manager_auth(request: Request, call_next):
    request_token = _extract_bearer_token(request.headers.get("Authorization"))
    if request_token is not None and secrets.compare_digest(request_token, auth_token):
        return await call_next(request)

    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    set_request_id(request_id)
    try:
        log_event(
            logger,
            level=logging.WARNING,
            event="http.request.failed",
            status="unauthorized",
            message="Unauthorized request to SearXNG manager",
            component="services.searxng_manager",
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
            status_code=401,
        )
    finally:
        clear_request_id()

    return JSONResponse(
        status_code=401,
        content={"detail": "Unauthorized"},
        headers={
            "WWW-Authenticate": "Bearer",
            "X-Request-ID": request_id,
        },
    )


@app.on_event("startup")
async def on_startup() -> None:
    log_event(
        logger,
        level=logging.INFO,
        event="app.lifecycle.started",
        status="started",
        message="Starting SearXNG manager",
        component="services.searxng_manager",
    )
    await manager.startup()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await manager.shutdown()


@app.get("/healthz")
async def healthz(request: Request) -> JSONResponse:
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    set_request_id(request_id)
    try:
        log_event(
            logger,
            level=logging.INFO,
            event="http.request.received",
            status="started",
            message="Health check request received",
            component="services.searxng_manager",
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )
        payload = manager.health()
        log_event(
            logger,
            level=logging.INFO,
            event="http.request.completed",
            status="succeeded",
            message="Health check completed",
            component="services.searxng_manager",
            method=request.method,
            path=request.url.path,
            status_code=200,
            result_summary=payload,
        )
        return JSONResponse(status_code=200, content=payload, headers={"X-Request-ID": request_id})
    finally:
        clear_request_id()


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def proxy_request(path: str, request: Request) -> Response:
    _ = path
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    set_request_id(request_id)
    started_at = time.perf_counter()
    try:
        log_event(
            logger,
            level=logging.INFO,
            event="http.request.received",
            status="started",
            message="Manager request received",
            component="services.searxng_manager",
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )
        attempted_backends: set[int] = set()
        last_http_error: HTTPException | None = None

        for attempt in range(1, 3):
            backend_index = await manager.acquire_backend(excluded_backends=attempted_backends)
            if backend_index is None:
                if attempt == 1:
                    raise HTTPException(status_code=503, detail="No healthy SearXNG backends available")
                break

            attempted_backends.add(backend_index)
            queue_wait_ms = int((time.perf_counter() - started_at) * 1000)
            log_event(
                logger,
                level=logging.INFO,
                event="http.request.received",
                status="started",
                message="Assigned request to backend",
                component="services.searxng_manager",
                path=request.url.path,
                method=request.method,
                backend=manager.backends[backend_index].name,
                queue_wait_ms=queue_wait_ms,
                attempt=attempt,
            )

            try:
                response = await manager.proxy(request, backend_index)
                response.headers["X-Request-ID"] = request_id
                duration_ms = int((time.perf_counter() - started_at) * 1000)
                log_event(
                    logger,
                    level=logging.INFO,
                    event="http.request.completed",
                    status="succeeded",
                    message="Manager request completed",
                    component="services.searxng_manager",
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    backend=manager.backends[backend_index].name,
                    attempts_used=attempt,
                )
                return response
            except HTTPException as error:
                last_http_error = error
                if attempt < 2:
                    log_event(
                        logger,
                        level=logging.WARNING,
                        event="http.request.failed",
                        status="retrying",
                        message="Backend request failed; retrying on different backend",
                        component="services.searxng_manager",
                        method=request.method,
                        path=request.url.path,
                        backend=manager.backends[backend_index].name,
                        status_code=error.status_code,
                        attempt=attempt,
                    )
                    continue
                raise
            finally:
                await manager.release_backend(backend_index)
                log_event(
                    logger,
                    level=logging.INFO,
                    event="http.request.completed",
                    status="succeeded",
                    message="Backend slot released",
                    component="services.searxng_manager",
                    backend=manager.backends[backend_index].name,
                )

        if last_http_error is not None:
            raise last_http_error
        raise HTTPException(status_code=503, detail="No healthy SearXNG backends available")
    except HTTPException as error:
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        log_event(
            logger,
            level=logging.ERROR,
            event="http.request.failed",
            status="failed",
            message="Manager request failed",
            component="services.searxng_manager",
            method=request.method,
            path=request.url.path,
            status_code=error.status_code,
            duration_ms=duration_ms,
            error_type=type(error).__name__,
            error_message=str(error.detail),
        )
        return JSONResponse(
            status_code=error.status_code,
            content={"detail": error.detail},
            headers={"X-Request-ID": request_id},
        )
    except Exception as error:
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        log_event(
            logger,
            level=logging.ERROR,
            event="http.request.failed",
            status="failed",
            message="Manager request crashed",
            component="services.searxng_manager",
            method=request.method,
            path=request.url.path,
            duration_ms=duration_ms,
            error_type=type(error).__name__,
            error_message=str(error),
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"},
            headers={"X-Request-ID": request_id},
        )
    finally:
        clear_request_id()
