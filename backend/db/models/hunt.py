from sqlalchemy import Column, DateTime, Integer, String, func
from db.database import Base


class Hunt(Base):
    __tablename__ = "hunts"

    id = Column(Integer, primary_key=True, index=True)
    video_link = Column(String, nullable=False)
    status = Column(String, nullable=False, default="queued")
    result = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    caption = Column(String, nullable=True)
    creator_handle = Column(String, nullable=True)
    platform = Column(String, nullable=False, default="instagram")
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
