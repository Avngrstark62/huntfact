from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, Field, HttpUrl, field_validator

from config import settings
from result_schema import FactCheckRow


class HealthResponse(BaseModel):
    status: str = Field(..., description="Health status: healthy or unhealthy")
    message: str = Field(..., description="Health status message")


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error description for the client")
    code: str | None = Field(None, description="Optional application error code")


class StartHuntRequest(BaseModel):
    video_link: HttpUrl = Field(..., description="URL of the video to analyze")
    cdn_link: HttpUrl = Field(..., description="CDN link for the video")
    fcm_token: str = Field(..., description="Firebase Cloud Messaging token for notifications")
    thumbnail_url: HttpUrl | None = Field(None, description="Thumbnail URL for reel preview")
    caption: str | None = Field(None, description="Caption text for the shared reel")
    creator_handle: str | None = Field(None, description="Creator handle for the shared reel")
    platform: str = Field("instagram", description="Source platform for the shared media")

    @field_validator("cdn_link")
    @classmethod
    def validate_cdn_link_against_allowlist(cls, value: HttpUrl) -> HttpUrl:
        parsed = urlparse(str(value))
        host = (parsed.hostname or "").strip().lower()
        if not host:
            raise ValueError("cdn_link must include a valid hostname")

        allowed_suffixes = [
            suffix.strip().lower()
            for suffix in settings.security.allowed_cdn_host_suffixes
            if isinstance(suffix, str) and suffix.strip()
        ]
        if not allowed_suffixes:
            raise ValueError("CDN host allowlist is not configured")

        host_allowed = any(
            host == suffix or host.endswith(f".{suffix}")
            for suffix in allowed_suffixes
        )
        if not host_allowed:
            raise ValueError("cdn_link host is not allowed")

        return value


class StartHuntResponse(BaseModel):
    success: bool = Field(..., description="Whether the hunt was started successfully")
    message: str = Field(..., description="Status message")
    hunt_id: int = Field(..., description="The hunt id for status tracking")


class HuntResponse(BaseModel):
    id: int = Field(..., description="Hunt id")
    video_link: str = Field(..., description="Video link for this hunt")
    status: str = Field(..., description="Current hunt status")
    result: list[FactCheckRow] | None = Field(
        None,
        description="Fact-check result rows",
    )
    title: str | None = Field(None, description="Short title for the hunt summary")
    summary: str | None = Field(None, description="One-paragraph summary for the hunt")
    trust_score: int | None = Field(None, description="Overall trust score from 0 to 100")
    thumbnail_url: str | None = Field(None, description="Thumbnail URL for reel preview")
    caption: str | None = Field(None, description="Caption text for the shared reel")
    creator_handle: str | None = Field(None, description="Creator handle for the shared reel")
    platform: str = Field(..., description="Source platform for the shared media")
    error_message: str | None = Field(None, description="Error details for failed hunts")
    created_at: datetime | None = Field(None, description="Hunt creation timestamp")
    updated_at: datetime | None = Field(None, description="Hunt updated timestamp")
    completed_at: datetime | None = Field(None, description="Hunt completion timestamp")
