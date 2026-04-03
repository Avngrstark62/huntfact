from pydantic import BaseModel, validator, Field

from logger import get_logger
from exceptions import ValidationException

logger = get_logger(__name__)


class StartHuntRequest(BaseModel):
    video_link: str = Field(..., description="URL of the video to analyze")

    @validator("video_link")
    def validate_video_link(cls, v):
        if not v or not v.strip():
            raise ValueError("video_link cannot be empty")
        if not v.startswith(("http://", "https://")):
            raise ValueError("video_link must be a valid URL")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "video_link": "https://example.com/video.mp4"
            }
        }


class StartHuntResponse(BaseModel):
    success: bool = Field(..., description="Whether the hunt was started successfully")
    message: str = Field(..., description="Status message")
    result: str = Field(..., description="The hunt result")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Hunt started successfully",
                "result": "this fact is true"
            }
        }
