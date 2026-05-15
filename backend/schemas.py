from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class HealthResponse(BaseModel):
    status: str = Field(..., description="Health status: healthy or unhealthy")
    message: str = Field(..., description="Health status message")


class StartHuntRequest(BaseModel):
    video_link: HttpUrl = Field(..., description="URL of the video to analyze")
    cdn_link: HttpUrl = Field(..., description="CDN link for the video")
    fcm_token: str = Field(..., description="Firebase Cloud Messaging token for notifications")
    thumbnail_url: HttpUrl | None = Field(None, description="Thumbnail URL for reel preview")
    caption: str | None = Field(None, description="Caption text for the shared reel")
    creator_handle: str | None = Field(None, description="Creator handle for the shared reel")
    platform: str = Field("instagram", description="Source platform for the shared media")


class StartHuntResponse(BaseModel):
    success: bool = Field(..., description="Whether the hunt was started successfully")
    message: str = Field(..., description="Status message")
    hunt_id: int = Field(..., description="The hunt id for status tracking")
    status: str = Field(..., description="Current hunt status")
    result: str | None = Field(None, description="The hunt result")


class HuntResponse(BaseModel):
    id: int = Field(..., description="Hunt id")
    video_link: str = Field(..., description="Video link for this hunt")
    status: str = Field(..., description="Current hunt status")
    result: str | None = Field(None, description="Fact-check result JSON string")
    thumbnail_url: str | None = Field(None, description="Thumbnail URL for reel preview")
    caption: str | None = Field(None, description="Caption text for the shared reel")
    creator_handle: str | None = Field(None, description="Creator handle for the shared reel")
    platform: str = Field(..., description="Source platform for the shared media")
    error_message: str | None = Field(None, description="Error details for failed hunts")
    created_at: datetime | None = Field(None, description="Hunt creation timestamp")
    updated_at: datetime | None = Field(None, description="Hunt updated timestamp")
    completed_at: datetime | None = Field(None, description="Hunt completion timestamp")
