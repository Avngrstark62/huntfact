from datetime import datetime, timezone

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

    def create_hunt(
        self,
        session: Session,
        video_link: str,
        thumbnail_url: str | None = None,
        caption: str | None = None,
        creator_handle: str | None = None,
        platform: str = "instagram",
    ):
        from db.models.hunt import Hunt

        hunt = Hunt(
            video_link=video_link,
            status="queued",
            thumbnail_url=thumbnail_url,
            caption=caption,
            creator_handle=creator_handle,
            platform=platform,
        )
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

    def get_hunt_for_user(self, session: Session, hunt_id: int, user_id: str):
        from db.models.hunt import Hunt
        from db.models.hunt_user import HuntUser

        return (
            session.query(Hunt)
            .join(HuntUser, Hunt.id == HuntUser.hunt_id)
            .filter(Hunt.id == hunt_id, HuntUser.user_id == user_id)
            .first()
        )

    def get_hunt_by_video_link(self, session: Session, video_link: str):
        from db.models.hunt import Hunt

        return session.query(Hunt).filter(Hunt.video_link == video_link).first()

    def update_hunt_result(self, session: Session, hunt_id: int, result: str):
        from db.models.hunt import Hunt

        hunt = session.query(Hunt).filter(Hunt.id == hunt_id).first()
        if hunt:
            hunt.result = result
            hunt.status = "completed"
            hunt.error_message = None
            hunt.completed_at = datetime.now(timezone.utc)
            try:
                session.commit()
            except:
                session.rollback()
                raise
            session.refresh(hunt)
            return hunt
        return None

    def update_hunt_status(
        self,
        session: Session,
        hunt_id: int,
        status_value: str,
        error_message: str | None = None,
    ):
        from db.models.hunt import Hunt

        hunt = session.query(Hunt).filter(Hunt.id == hunt_id).first()
        if hunt is None:
            return None

        hunt.status = status_value
        hunt.error_message = error_message
        if status_value != "completed":
            hunt.completed_at = None

        try:
            session.commit()
        except:
            session.rollback()
            raise
        session.refresh(hunt)
        return hunt

    def update_hunt_metadata(
        self,
        session: Session,
        hunt_id: int,
        thumbnail_url: str | None = None,
        caption: str | None = None,
        creator_handle: str | None = None,
        platform: str | None = None,
    ):
        from db.models.hunt import Hunt

        hunt = session.query(Hunt).filter(Hunt.id == hunt_id).first()
        if hunt is None:
            return None

        if thumbnail_url:
            hunt.thumbnail_url = thumbnail_url
        if caption:
            hunt.caption = caption
        if creator_handle:
            hunt.creator_handle = creator_handle
        if platform:
            hunt.platform = platform

        try:
            session.commit()
        except:
            session.rollback()
            raise
        session.refresh(hunt)
        return hunt

    def add_hunt_user(self, session: Session, hunt_id: int, user_id: str):
        from db.models.hunt_user import HuntUser

        existing = (
            session.query(HuntUser)
            .filter(HuntUser.hunt_id == hunt_id, HuntUser.user_id == user_id)
            .first()
        )
        if existing:
            return existing

        hunt_user = HuntUser(hunt_id=hunt_id, user_id=user_id)
        session.add(hunt_user)
        try:
            session.commit()
        except:
            session.rollback()
            raise
        session.refresh(hunt_user)
        return hunt_user

    def get_users_by_hunt_id(self, session: Session, hunt_id: int):
        from db.models.hunt_user import HuntUser

        rows = session.query(HuntUser).filter(HuntUser.hunt_id == hunt_id).all()
        return [row.user_id for row in rows]

    def get_hunts_by_user_id(self, session: Session, user_id: str):
        from db.models.hunt import Hunt
        from db.models.hunt_user import HuntUser

        return (
            session.query(Hunt)
            .join(HuntUser, Hunt.id == HuntUser.hunt_id)
            .filter(HuntUser.user_id == user_id)
            .order_by(Hunt.updated_at.desc())
            .all()
        )


# ✅ singleton instance
db = Database()
