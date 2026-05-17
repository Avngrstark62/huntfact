from sqlalchemy import Column, Integer, String

from db.database import Base


class UserHuntLimit(Base):
    __tablename__ = "user_hunt_limits"

    user_id = Column(String, primary_key=True, index=True)
    hunts_limit = Column(Integer, nullable=False, default=30)
