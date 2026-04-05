from sqlalchemy import Column, Integer, String
from db.database import Base

class Hunt(Base):
    __tablename__ = "hunts"

    id = Column(Integer, primary_key=True, index=True)
    video_link = Column(String, nullable=False)
    result = Column(String, nullable=True)
