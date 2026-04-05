from pydantic import BaseModel, Field, HttpUrl


class HealthResponse(BaseModel):
    status: str = Field(..., description="Health status: healthy or unhealthy")
    message: str = Field(..., description="Health status message")


class StartHuntRequest(BaseModel):
    video_link: HttpUrl = Field(..., description="URL of the video to analyze")


class StartHuntResponse(BaseModel):
    success: bool = Field(..., description="Whether the hunt was started successfully")
    message: str = Field(..., description="Status message")
    result: str = Field(..., description="The hunt result")
