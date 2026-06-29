import logging
from hashlib import sha256

from fastapi import Depends, HTTPException, Request, status

from auth.supabase_auth import AuthenticatedUser, get_authenticated_user
from config import settings
from logging_config import get_logger, hash_user_id, log_event, sanitize_url

from .policy import (
    RateLimitPolicy,
    global_ip_policy,
    health_ip_policy,
    hunt_list_user_policy,
    hunt_read_user_policy,
    start_hunt_duplicate_policy,
    start_hunt_user_policy,
)
from .store import InMemoryRateLimitStore, RateLimitDecision

logger = get_logger("services.rate_limit")
_store = InMemoryRateLimitStore(
    cleanup_interval_seconds=settings.rate_limit.store_cleanup_interval_seconds,
    max_keys=settings.rate_limit.store_max_keys,
)


def _hash_rate_limit_key(key: str) -> str:
    return sha256(key.encode("utf-8")).hexdigest()[:16]


def _client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    return forwarded_for.split(",")[0].strip() or "unknown"


def _enforce(policy: RateLimitPolicy, key: str) -> RateLimitDecision:
    scoped_key = f"{policy.name}:{key}"
    store_key = sha256(scoped_key.encode("utf-8")).hexdigest()
    return _store.consume(
        key=store_key,
        limit=policy.limit,
        window_seconds=policy.window_seconds,
    )


def _raise_if_blocked(
    *,
    decision: RateLimitDecision,
    policy: RateLimitPolicy,
    request: Request,
    key_hash: str,
    user_id_hash: str | None = None,
    video_link: str | None = None,
) -> None:
    if decision.allowed:
        return

    request_id = getattr(request.state, "request_id", None)
    log_event(
        logger,
        level=logging.WARNING,
        event="http.request.failed",
        status="failed",
        message="Rate limit exceeded",
        component="api",
        request_id=request_id,
        path=request.url.path,
        method=request.method,
        policy_name=policy.name,
        key_hash=key_hash,
        user_id_hash=user_id_hash,
        video_link=sanitize_url(video_link),
        rate_limit=decision.limit,
        rate_limit_window_seconds=decision.window_seconds,
        retry_after_seconds=decision.retry_after_seconds,
    )
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many requests. Please try again later.",
        headers={"Retry-After": str(decision.retry_after_seconds)},
    )


async def enforce_global_ip_rate_limit(request: Request) -> None:
    policy = global_ip_policy()
    ip = _client_ip(request)
    key = ip
    decision = _enforce(policy, key)
    _raise_if_blocked(
        decision=decision,
        policy=policy,
        request=request,
        key_hash=_hash_rate_limit_key(key),
    )


async def enforce_health_ip_rate_limit(request: Request) -> None:
    policy = health_ip_policy()
    ip = _client_ip(request)
    key = ip
    decision = _enforce(policy, key)
    _raise_if_blocked(
        decision=decision,
        policy=policy,
        request=request,
        key_hash=_hash_rate_limit_key(key),
    )


async def enforce_start_hunt_user_rate_limit(
    request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> None:
    policy = start_hunt_user_policy()
    key = authenticated_user.sub
    decision = _enforce(policy, key)
    _raise_if_blocked(
        decision=decision,
        policy=policy,
        request=request,
        key_hash=_hash_rate_limit_key(key),
        user_id_hash=hash_user_id(authenticated_user.sub),
    )


async def enforce_hunt_read_user_rate_limit(
    request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> None:
    policy = hunt_read_user_policy()
    key = authenticated_user.sub
    decision = _enforce(policy, key)
    _raise_if_blocked(
        decision=decision,
        policy=policy,
        request=request,
        key_hash=_hash_rate_limit_key(key),
        user_id_hash=hash_user_id(authenticated_user.sub),
    )


async def enforce_hunt_list_user_rate_limit(
    request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> None:
    policy = hunt_list_user_policy()
    key = authenticated_user.sub
    decision = _enforce(policy, key)
    _raise_if_blocked(
        decision=decision,
        policy=policy,
        request=request,
        key_hash=_hash_rate_limit_key(key),
        user_id_hash=hash_user_id(authenticated_user.sub),
    )


def enforce_start_hunt_duplicate_rate_limit(
    *,
    request: Request,
    user_id: str,
    video_link: str,
) -> None:
    policy = start_hunt_duplicate_policy()
    key = f"{user_id}:{video_link.strip().lower()}"
    decision = _enforce(policy, key)
    _raise_if_blocked(
        decision=decision,
        policy=policy,
        request=request,
        key_hash=_hash_rate_limit_key(key),
        user_id_hash=hash_user_id(user_id),
        video_link=video_link,
    )
