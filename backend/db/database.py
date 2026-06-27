from datetime import datetime, timezone, timedelta

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from config import settings
from typing import Generator

Base = declarative_base()
DEFAULT_USER_HUNTS_LIMIT = 30


class Database:
    def __init__(self):
        self.engine = create_engine(
            settings.database.url,
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

    def get_or_create_hunt(
        self,
        session: Session,
        video_link: str,
        thumbnail_url: str | None = None,
        caption: str | None = None,
        creator_handle: str | None = None,
        platform: str = "instagram",
    ):
        from db.models.hunt import Hunt

        existing_hunt = self.get_hunt_by_video_link(session, video_link)
        if existing_hunt is not None:
            return existing_hunt

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
        except IntegrityError:
            session.rollback()
            existing_hunt = self.get_hunt_by_video_link(session, video_link)
            if existing_hunt is None:
                raise
            return existing_hunt
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

    def create_workflow_admission(
        self,
        session: Session,
        workflow_id: str,
        video_link: str,
        hunt_id: int,
    ) -> bool:
        from db.models.workflow_admission import WorkflowAdmission

        row = WorkflowAdmission(
            workflow_id=workflow_id,
            video_link=video_link,
            hunt_id=hunt_id,
        )
        session.add(row)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            return False
        except:
            session.rollback()
            raise
        return True

    def delete_workflow_admission(self, session: Session, workflow_id: str) -> bool:
        from db.models.workflow_admission import WorkflowAdmission

        deleted_rows = (
            session.query(WorkflowAdmission)
            .filter(WorkflowAdmission.workflow_id == workflow_id)
            .delete(synchronize_session=False)
        )
        try:
            session.commit()
        except:
            session.rollback()
            raise
        return deleted_rows > 0

    def clear_workflow_admission_if_hunt_failed(
        self,
        session: Session,
        workflow_id: str,
        hunt_id: int,
    ) -> bool:
        from db.models.hunt import Hunt
        from db.models.workflow_admission import WorkflowAdmission

        hunt = session.query(Hunt).filter(Hunt.id == hunt_id).first()
        if hunt is None or hunt.status != "failed":
            return False

        deleted_rows = (
            session.query(WorkflowAdmission)
            .filter(WorkflowAdmission.workflow_id == workflow_id)
            .delete(synchronize_session=False)
        )
        try:
            session.commit()
        except:
            session.rollback()
            raise
        return deleted_rows > 0

    def mark_stale_processing_hunts_failed(
        self,
        session: Session,
        stale_minutes: int = 5,
    ) -> list[int]:
        from db.models.hunt import Hunt

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_minutes)
        stale_hunts = (
            session.query(Hunt)
            .filter(Hunt.status == "processing", Hunt.updated_at < cutoff)
            .all()
        )
        stale_ids: list[int] = []
        for hunt in stale_hunts:
            stale_ids.append(hunt.id)
            hunt.status = "failed"
            hunt.error_message = f"Marked failed by cleanup after {stale_minutes} minutes in processing"
            hunt.completed_at = None

        if stale_hunts:
            try:
                session.commit()
            except:
                session.rollback()
                raise
        return stale_ids

    def delete_workflow_admissions_for_failed_hunts(self, session: Session) -> int:
        from db.models.hunt import Hunt
        from db.models.workflow_admission import WorkflowAdmission

        failed_admissions = (
            session.query(WorkflowAdmission.workflow_id)
            .join(Hunt, WorkflowAdmission.hunt_id == Hunt.id)
            .filter(Hunt.status == "failed")
            .all()
        )
        workflow_ids = [row[0] for row in failed_admissions]
        if not workflow_ids:
            return 0

        deleted_rows = (
            session.query(WorkflowAdmission)
            .filter(WorkflowAdmission.workflow_id.in_(workflow_ids))
            .delete(synchronize_session=False)
        )
        try:
            session.commit()
        except:
            session.rollback()
            raise
        return int(deleted_rows or 0)

    def update_hunt_result(
        self,
        session: Session,
        hunt_id: int,
        result: str,
        title: str,
        summary: str,
        trust_score: int,
    ):
        from db.models.hunt import Hunt

        hunt = session.query(Hunt).filter(Hunt.id == hunt_id).first()
        if hunt:
            hunt.result = result
            hunt.title = title
            hunt.summary = summary
            hunt.trust_score = trust_score
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

    def get_or_create_user_hunts_limit(
        self,
        session: Session,
        user_id: str,
    ) -> int:
        from db.models.user_hunt_limit import UserHuntLimit

        row = session.query(UserHuntLimit).filter(UserHuntLimit.user_id == user_id).first()
        if row:
            return row.hunts_limit

        row = UserHuntLimit(
            user_id=user_id,
            hunts_limit=DEFAULT_USER_HUNTS_LIMIT,
        )
        session.add(row)
        try:
            session.commit()
        except:
            session.rollback()
            row = session.query(UserHuntLimit).filter(UserHuntLimit.user_id == user_id).first()
            if row is None:
                raise
            return row.hunts_limit
        session.refresh(row)
        return row.hunts_limit

    def get_active_hunts_count_by_user_id(self, session: Session, user_id: str) -> int:
        from db.models.hunt import Hunt
        from db.models.hunt_user import HuntUser

        return (
            session.query(Hunt.id)
            .join(HuntUser, Hunt.id == HuntUser.hunt_id)
            .filter(
                HuntUser.user_id == user_id,
                Hunt.status.in_(["queued", "starting", "processing", "completed"]),
            )
            .count()
        )


# ✅ singleton instance
db = Database()
