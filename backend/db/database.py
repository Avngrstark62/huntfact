from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from config import settings
from typing import Generator

Base = declarative_base()


class Database:
    def __init__(self):
        self.engine = create_engine(
            settings.database_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,  # important
        )

        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )
        
        self.is_healthy = False

    # dependency
    def get_db(self) -> Generator[Session, None, None]:
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    # -------- CRUD methods --------

    def create_hunt(self, session: Session, video_link: str):
        from db.models.hunt import Hunt

        hunt = Hunt(video_link=video_link)
        session.add(hunt)
        try:
            session.commit()
        except:
            session.rollback()
            raise

        session.refresh(hunt)
        return hunt

    def get_hunt(self, session: Session, hunt_id: int):
        from db.models.hunt import Hunt

        return session.query(Hunt).filter(Hunt.id == hunt_id).first()


# ✅ singleton instance
db = Database()
