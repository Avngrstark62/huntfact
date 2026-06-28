from sqlalchemy import Column, DateTime, Integer, String, func

from db.database import Base


class WorkflowAdmission(Base):
    __tablename__ = "workflow_admissions"

    workflow_id = Column(String, primary_key=True, index=True)
    video_link = Column(String, nullable=False, index=True)
    hunt_id = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
