from sqlalchemy import Column, ForeignKey, Integer, String

from db.database import Base


class HuntUser(Base):
    __tablename__ = "hunt_users"

    hunt_id = Column(Integer, ForeignKey("hunts.id"), primary_key=True, index=True)
    user_id = Column(String, primary_key=True, index=True)
