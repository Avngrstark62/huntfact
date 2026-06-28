import time
import logging
from dataclasses import dataclass
from threading import Lock
from typing import Any

import requests
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from config import settings
from logging_config import get_logger, hash_user_id, log_event

logger = get_logger("auth.supabase")
_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthenticatedUser:
    sub: str
    email: str | None = None


class JwksCache:
    def __init__(self, ttl_seconds: int = 600) -> None:
        self._ttl_seconds = ttl_seconds
        self._jwks: dict[str, Any] | None = None
        self._expires_at = 0.0
        self._lock = Lock()

    def get_jwks(self) -> dict[str, Any]:
        now = time.time()
        if self._jwks and now < self._expires_at:
            return self._jwks

        with self._lock:
            now = time.time()
            if self._jwks and now < self._expires_at:
                return self._jwks

            if not settings.auth.supabase_jwks_url:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication is not configured",
                )

            try:
                response = requests.get(settings.auth.supabase_jwks_url, timeout=5)
                response.raise_for_status()
                payload = response.json()
            except Exception:
                log_event(
                    logger,
                    level=logging.ERROR,
                    event="auth.check.failed",
                    status="failed",
                    message="Failed to fetch Supabase JWKS",
                    component="api.auth",
                    exc_info=True,
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication token",
                )

            keys = payload.get("keys")
            if not isinstance(keys, list):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication token",
                )

            self._jwks = payload
            self._expires_at = now + self._ttl_seconds
            return self._jwks


_jwks_cache = JwksCache()


def _extract_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )
    return credentials.credentials


def _get_signing_key(token: str, jwks: dict[str, Any]) -> dict[str, Any]:
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as e:
        log_event(
            logger,
            level=logging.WARNING,
            event="auth.check.failed",
            status="failed",
            message="JWT header decode failed",
            component="api.auth",
            error_type=type(e).__name__,
            error_message=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    kid = header.get("kid")
    if not kid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication token",
    )


def _decode_claims(token: str, signing_key: dict[str, Any]) -> dict[str, Any]:
    options = {"verify_aud": bool(settings.auth.supabase_audience)}
    kwargs: dict[str, Any] = {
        "algorithms": ["ES256"],
        "issuer": settings.auth.supabase_issuer,
        "options": options,
    }
    if settings.auth.supabase_audience:
        kwargs["audience"] = settings.auth.supabase_audience

    try:
        return jwt.decode(token, signing_key, **kwargs)
    except JWTError as e:
        log_event(
            logger,
            level=logging.WARNING,
            event="auth.check.failed",
            status="failed",
            message="JWT claims decode failed",
            component="api.auth",
            error_type=type(e).__name__,
            error_message=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )


def get_authenticated_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthenticatedUser:
    request_id = getattr(request.state, "request_id", None)
    if settings.auth.disable:
        user = AuthenticatedUser(sub="disabled-auth-user")
        request.state.authenticated_user = user
        log_event(
            logger,
            level=logging.INFO,
            event="auth.check.succeeded",
            status="succeeded",
            message="Auth check bypassed because auth is disabled",
            component="api.auth",
            request_id=request_id,
            path=request.url.path,
            auth_outcome="success",
            user_id_hash=hash_user_id(user.sub),
        )
        return user
    
    try:
        log_event(
            logger,
            level=logging.INFO,
            event="auth.check.started",
            status="started",
            message="Starting auth check",
            component="api.auth",
            request_id=request_id,
            path=request.url.path,
        )
        token = _extract_token(credentials)
        jwks = _jwks_cache.get_jwks()
        signing_key = _get_signing_key(token, jwks)
        claims = _decode_claims(token, signing_key)

        subject = claims.get("sub")
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )

        user = AuthenticatedUser(sub=subject, email=claims.get("email"))
        request.state.authenticated_user = user
        log_event(
            logger,
            level=logging.INFO,
            event="auth.check.succeeded",
            status="succeeded",
            message="Auth check succeeded",
            component="api.auth",
            request_id=request_id,
            path=request.url.path,
            auth_outcome="success",
            user_id_hash=hash_user_id(user.sub),
        )
        return user
    except HTTPException as e:
        log_event(
            logger,
            level=logging.WARNING,
            event="auth.check.failed",
            status="failed",
            message="Auth check failed",
            component="api.auth",
            request_id=request_id,
            path=request.url.path,
            auth_outcome="failure",
            error_type=type(e).__name__,
            error_message=str(e.detail),
        )
        raise
