from pydantic import BaseModel, Field
from typing import Dict, Any


class TaskMessage(BaseModel):
    job_id: str = Field(..., description="Unique job identifier")
    step: str = Field(..., description="Step name or type")
    payload: Dict[str, Any] = Field(..., description="Task payload data")
    priority: int = Field(default=5, description="Message priority")
    retry_count: int = Field(default=0, description="Retry count")
