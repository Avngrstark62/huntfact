import asyncio
from datetime import datetime, UTC
import json
import logging
from typing import Any, Optional
from urllib.parse import urlencode
from uuid import uuid4

import boto3
from botocore.client import BaseClient

from config import settings
from logging_config import get_logger, log_event

logger = get_logger("s3_client")


def _normalize_prefix(prefix: str) -> str:
    return prefix.strip().strip("/")


def _build_tagging(tags: dict[str, str] | None) -> str | None:
    if not tags:
        return None
    normalized = {
        str(key): str(value)
        for key, value in tags.items()
        if key is not None and value is not None
    }
    if not normalized:
        return None
    return urlencode(normalized)


class S3ClientManager:
    def __init__(self) -> None:
        self.client: Optional[BaseClient] = None
        self.is_healthy = False

    def _require_enabled(self) -> None:
        if not settings.s3.enabled:
            raise RuntimeError("S3 integration is disabled")

    def connect(self) -> BaseClient:
        self._require_enabled()
        if self.client is not None:
            return self.client

        kwargs: dict[str, Any] = {
            "service_name": "s3",
            "region_name": settings.s3.region_name,
        }
        if settings.s3.endpoint_url:
            kwargs["endpoint_url"] = settings.s3.endpoint_url
        if settings.s3.access_key_id:
            kwargs["aws_access_key_id"] = settings.s3.access_key_id
        if settings.s3.secret_access_key:
            kwargs["aws_secret_access_key"] = settings.s3.secret_access_key
        if settings.s3.session_token:
            kwargs["aws_session_token"] = settings.s3.session_token

        try:
            self.client = boto3.client(**kwargs)
            self.is_healthy = True
            log_event(
                logger,
                level=logging.INFO,
                event="provider.request.succeeded",
                status="succeeded",
                message="Connected to S3",
                component="s3_client",
                provider="s3",
                operation="connect",
                bucket_name=settings.s3.bucket_name,
                region_name=settings.s3.region_name,
            )
            return self.client
        except Exception as exc:
            self.is_healthy = False
            log_event(
                logger,
                level=logging.ERROR,
                event="provider.request.failed",
                status="failed",
                message="Failed to connect to S3",
                component="s3_client",
                provider="s3",
                operation="connect",
                error_type=type(exc).__name__,
                error_message=str(exc),
                exc_info=True,
            )
            raise

    async def ping(self) -> None:
        client = self.connect()
        try:
            await asyncio.to_thread(client.head_bucket, Bucket=settings.s3.bucket_name)
            log_event(
                logger,
                level=logging.INFO,
                event="provider.request.succeeded",
                status="succeeded",
                message="S3 bucket ping succeeded",
                component="s3_client",
                provider="s3",
                operation="head_bucket",
                bucket_name=settings.s3.bucket_name,
            )
        except Exception as e:
            log_event(
                logger,
                level=logging.ERROR,
                event="provider.request.failed",
                status="failed",
                message="S3 bucket ping failed",
                component="s3_client",
                provider="s3",
                operation="head_bucket",
                bucket_name=settings.s3.bucket_name,
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True,
            )
            raise

    def build_artifact_key(
        self,
        *,
        workflow_id: str | None,
        step: str | None,
        task_id: str | None,
        artifact_name: str,
        extension: str,
        prefix: str | None = None,
    ) -> str:
        target_prefix = _normalize_prefix(prefix or settings.s3.temp_prefix)
        workflow_part = (workflow_id or "unknown_workflow").strip()
        step_part = (step or "unknown_step").strip().lower()
        task_part = (task_id or "unknown_task").strip()
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        ext = extension.lstrip(".")
        return (
            f"{target_prefix}/{workflow_part}/{step_part}/{task_part}/"
            f"{timestamp}_{uuid4().hex}_{artifact_name}.{ext}"
        )

    async def put_bytes(
        self,
        *,
        key: str,
        body: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
        tags: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        client = self.connect()
        kwargs: dict[str, Any] = {
            "Bucket": settings.s3.bucket_name,
            "Key": key,
            "Body": body,
            "ContentType": content_type,
        }
        if metadata:
            kwargs["Metadata"] = {
                str(k): str(v)
                for k, v in metadata.items()
                if k is not None and v is not None
            }
        tagging = _build_tagging(tags)
        if tagging:
            kwargs["Tagging"] = tagging

        try:
            response = await asyncio.to_thread(client.put_object, **kwargs)
            result = {
                "bucket": settings.s3.bucket_name,
                "key": key,
                "s3_uri": f"s3://{settings.s3.bucket_name}/{key}",
                "content_type": content_type,
                "size_bytes": len(body),
                "version_id": response.get("VersionId"),
            }
            log_event(
                logger,
                level=logging.INFO,
                event="provider.request.succeeded",
                status="succeeded",
                message="S3 put object succeeded",
                component="s3_client",
                provider="s3",
                operation="put_object",
                bucket_name=settings.s3.bucket_name,
                key=key,
                result_summary={"size_bytes": len(body), "content_type": content_type},
            )
            return result
        except Exception as e:
            log_event(
                logger,
                level=logging.ERROR,
                event="provider.request.failed",
                status="failed",
                message="S3 put object failed",
                component="s3_client",
                provider="s3",
                operation="put_object",
                bucket_name=settings.s3.bucket_name,
                key=key,
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True,
            )
            raise

    async def put_json(
        self,
        *,
        key: str,
        payload: Any,
        metadata: dict[str, str] | None = None,
        tags: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        body = json.dumps(payload, default=str).encode("utf-8")
        return await self.put_bytes(
            key=key,
            body=body,
            content_type="application/json",
            metadata=metadata,
            tags=tags,
        )

    async def get_bytes(self, *, key: str) -> bytes:
        client = self.connect()
        try:
            response = await asyncio.to_thread(
                client.get_object,
                Bucket=settings.s3.bucket_name,
                Key=key,
            )
            body = await asyncio.to_thread(response["Body"].read)
            log_event(
                logger,
                level=logging.INFO,
                event="provider.request.succeeded",
                status="succeeded",
                message="S3 get object succeeded",
                component="s3_client",
                provider="s3",
                operation="get_object",
                bucket_name=settings.s3.bucket_name,
                key=key,
                result_summary={"size_bytes": len(body)},
            )
            return body
        except Exception as e:
            log_event(
                logger,
                level=logging.ERROR,
                event="provider.request.failed",
                status="failed",
                message="S3 get object failed",
                component="s3_client",
                provider="s3",
                operation="get_object",
                bucket_name=settings.s3.bucket_name,
                key=key,
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True,
            )
            raise

    async def get_json(self, *, key: str) -> Any:
        body = await self.get_bytes(key=key)
        try:
            payload = json.loads(body.decode("utf-8"))
            log_event(
                logger,
                level=logging.INFO,
                event="provider.request.succeeded",
                status="succeeded",
                message="S3 JSON decode succeeded",
                component="s3_client",
                provider="s3",
                operation="get_json",
                bucket_name=settings.s3.bucket_name,
                key=key,
            )
            return payload
        except Exception as e:
            log_event(
                logger,
                level=logging.ERROR,
                event="provider.request.failed",
                status="failed",
                message="S3 JSON decode failed",
                component="s3_client",
                provider="s3",
                operation="get_json",
                bucket_name=settings.s3.bucket_name,
                key=key,
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True,
            )
            raise

    async def delete_object(self, *, key: str) -> None:
        client = self.connect()
        try:
            await asyncio.to_thread(
                client.delete_object,
                Bucket=settings.s3.bucket_name,
                Key=key,
            )
            log_event(
                logger,
                level=logging.INFO,
                event="provider.request.succeeded",
                status="succeeded",
                message="S3 delete object succeeded",
                component="s3_client",
                provider="s3",
                operation="delete_object",
                bucket_name=settings.s3.bucket_name,
                key=key,
            )
        except Exception as e:
            log_event(
                logger,
                level=logging.ERROR,
                event="provider.request.failed",
                status="failed",
                message="S3 delete object failed",
                component="s3_client",
                provider="s3",
                operation="delete_object",
                bucket_name=settings.s3.bucket_name,
                key=key,
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True,
            )
            raise


s3_client = S3ClientManager()
