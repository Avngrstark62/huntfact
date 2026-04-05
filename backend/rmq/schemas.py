from pydantic import BaseModel, Field
from typing import Dict, Any
from uuid import uuid4


class TaskMessage(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique job identifier")
    step: str = Field(..., description="Step name or type")
    payload: Dict[str, Any] = Field(..., description="Task payload data")
    priority: int = Field(default=5, description="Message priority")
    retry_count: int = Field(default=0, description="Retry count")
