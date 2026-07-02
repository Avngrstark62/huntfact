from datetime import datetime, timezone, timedelta

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from config import settings
from typing import Any, Generator
import logging

from logging_config import get_logger, log_event, sanitize_url

Base = declarative_base()
DEFAULT_USER_HUNTS_LIMIT = 30
logger = get_logger("db.database")


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

    def get_or_create_hunt_in_txn(
        self,
        session: Session,
        video_link: str,
        thumbnail_url: str | None = None,
        caption: str | None = None,
        creator_handle: str | None = None,
        platform: str = "instagram",
    ):
        """
        Transaction-friendly version of get_or_create_hunt.
        Uses savepoint semantics and does not commit the outer transaction.
        """
        from db.models.hunt import Hunt

        log_event(
            logger,
            level=logging.INFO,
            event="db.write.started",
            status="started",
            message="Creating or reusing hunt in transaction",
            component="db",
            video_link=sanitize_url(video_link),
        )
        existing_hunt = self.get_hunt_by_video_link(session, video_link)
        if existing_hunt is not None:
            log_event(
                logger,
                level=logging.INFO,
                event="db.write.succeeded",
                status="skipped",
                message="Reused existing hunt in transaction",
                component="db",
                hunt_id=existing_hunt.id,
                video_link=sanitize_url(video_link),
            )
            return existing_hunt

        try:
            with session.begin_nested():
                hunt = Hunt(
                    video_link=video_link,
                    status="queued",
                    thumbnail_url=thumbnail_url,
                    caption=caption,
                    creator_handle=creator_handle,
                    platform=platform,
                )
                session.add(hunt)
                session.flush()
                session.refresh(hunt)
                log_event(
                    logger,
                    level=logging.INFO,
                    event="db.write.succeeded",
                    status="succeeded",
                    message="Created new hunt in transaction",
                    component="db",
                    hunt_id=hunt.id,
                    video_link=sanitize_url(video_link),
                )
                return hunt
        except IntegrityError:
            # Concurrent request may have created the same video_link.
            existing_hunt = self.get_hunt_by_video_link(session, video_link)
            if existing_hunt is None:
                raise
            log_event(
                logger,
                level=logging.WARNING,
                event="db.write.failed",
                status="skipped",
                message="Reused hunt after integrity conflict in transaction",
                component="db",
                hunt_id=existing_hunt.id,
                video_link=sanitize_url(video_link),
            )
            return existing_hunt

    def get_hunt(self, session: Session, hunt_id: int):
        from db.models.hunt import Hunt

        return session.query(Hunt).filter(Hunt.id == hunt_id).first()

    def get_hunt_for_user(self, session: Session, hunt_id: int, user_id: str):
        from db.models.hunt import Hunt
        from db.models.hunt_user import HuntUser

        log_event(
            logger,
            level=logging.INFO,
            event="db.query.started",
            status="started",
            message="Querying hunt for user",
            component="db",
            hunt_id=hunt_id,
        )
        hunt = (
            session.query(Hunt)
            .join(HuntUser, Hunt.id == HuntUser.hunt_id)
            .filter(Hunt.id == hunt_id, HuntUser.user_id == user_id)
            .first()
        )
        log_event(
            logger,
            level=logging.INFO,
            event="db.query.succeeded",
            status="succeeded" if hunt is not None else "skipped",
            message="Queried hunt for user",
            component="db",
            hunt_id=hunt_id,
        )
        return hunt

    def get_hunt_by_video_link(self, session: Session, video_link: str):
        from db.models.hunt import Hunt
        log_event(
            logger,
            level=logging.INFO,
            event="db.query.started",
            status="started",
            message="Querying hunt by video_link",
            component="db",
            video_link=sanitize_url(video_link),
        )
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
        log_event(
            logger,
            level=logging.INFO,
            event="db.write.started",
            status="started",
            message="Creating workflow admission",
            component="db",
            workflow_id=workflow_id,
            hunt_id=hunt_id,
            video_link=sanitize_url(video_link),
        )
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            log_event(
                logger,
                level=logging.WARNING,
                event="db.write.failed",
                status="skipped",
                message="Workflow admission already exists",
                component="db",
                workflow_id=workflow_id,
                hunt_id=hunt_id,
            )
            return False
        except:
            session.rollback()
            log_event(
                logger,
                level=logging.ERROR,
                event="db.write.failed",
                status="failed",
                message="Creating workflow admission failed",
                component="db",
                workflow_id=workflow_id,
                hunt_id=hunt_id,
                exc_info=True,
            )
            raise
        log_event(
            logger,
            level=logging.INFO,
            event="db.write.succeeded",
            status="succeeded",
            message="Workflow admission created",
            component="db",
            workflow_id=workflow_id,
            hunt_id=hunt_id,
        )
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
            log_event(
                logger,
                level=logging.INFO,
                event="db.write.succeeded",
                status="skipped",
                message="Skipped clearing workflow admission because hunt is not failed",
                component="db",
                workflow_id=workflow_id,
                hunt_id=hunt_id,
            )
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
            log_event(
                logger,
                level=logging.ERROR,
                event="db.write.failed",
                status="failed",
                message="Clearing workflow admission for failed hunt failed",
                component="db",
                workflow_id=workflow_id,
                hunt_id=hunt_id,
                exc_info=True,
            )
            raise
        log_event(
            logger,
            level=logging.INFO,
            event="db.write.succeeded",
            status="succeeded" if deleted_rows > 0 else "skipped",
            message="Cleared workflow admission for failed hunt",
            component="db",
            workflow_id=workflow_id,
            hunt_id=hunt_id,
        )
        return deleted_rows > 0

    def mark_stale_processing_hunts_failed(
        self,
        session: Session,
        stale_minutes: int = 5,
    ) -> list[int]:
        from db.models.hunt import Hunt

        log_event(
            logger,
            level=logging.INFO,
            event="db.write.started",
            status="started",
            message="Marking stale processing hunts as failed",
            component="db",
            stale_minutes=stale_minutes,
        )
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
                log_event(
                    logger,
                    level=logging.ERROR,
                    event="db.write.failed",
                    status="failed",
                    message="Marking stale processing hunts failed commit failed",
                    component="db",
                    stale_minutes=stale_minutes,
                    exc_info=True,
                )
                raise
        log_event(
            logger,
            level=logging.INFO,
            event="db.write.succeeded",
            status="succeeded" if stale_hunts else "skipped",
            message="Marked stale processing hunts as failed",
            component="db",
            stale_minutes=stale_minutes,
            result_summary={"hunt_count": len(stale_ids)},
        )
        return stale_ids

    def mark_stale_queued_hunts_failed(
        self,
        session: Session,
        stale_minutes: int = 30,
    ) -> list[int]:
        from db.models.hunt import Hunt

        log_event(
            logger,
            level=logging.INFO,
            event="db.write.started",
            status="started",
            message="Marking stale queued hunts as failed",
            component="db",
            stale_minutes=stale_minutes,
        )
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_minutes)
        stale_hunts = (
            session.query(Hunt)
            .filter(Hunt.status == "queued", Hunt.updated_at < cutoff)
            .all()
        )
        stale_ids: list[int] = []
        for hunt in stale_hunts:
            stale_ids.append(hunt.id)
            hunt.status = "failed"
            hunt.error_message = f"Marked failed by cleanup after {stale_minutes} minutes in queued"
            hunt.completed_at = None

        if stale_hunts:
            try:
                session.commit()
            except:
                session.rollback()
                log_event(
                    logger,
                    level=logging.ERROR,
                    event="db.write.failed",
                    status="failed",
                    message="Marking stale queued hunts failed commit failed",
                    component="db",
                    stale_minutes=stale_minutes,
                    exc_info=True,
                )
                raise
        log_event(
            logger,
            level=logging.INFO,
            event="db.write.succeeded",
            status="succeeded" if stale_hunts else "skipped",
            message="Marked stale queued hunts as failed",
            component="db",
            stale_minutes=stale_minutes,
            result_summary={"hunt_count": len(stale_ids)},
        )
        return stale_ids

    def delete_workflow_admissions_for_failed_hunts(self, session: Session) -> int:
        from db.models.hunt import Hunt
        from db.models.workflow_admission import WorkflowAdmission

        log_event(
            logger,
            level=logging.INFO,
            event="db.write.started",
            status="started",
            message="Deleting workflow admissions for failed hunts",
            component="db",
        )
        failed_admissions = (
            session.query(WorkflowAdmission.workflow_id)
            .join(Hunt, WorkflowAdmission.hunt_id == Hunt.id)
            .filter(Hunt.status == "failed")
            .all()
        )
        workflow_ids = [row[0] for row in failed_admissions]
        if not workflow_ids:
            log_event(
                logger,
                level=logging.INFO,
                event="db.write.succeeded",
                status="skipped",
                message="No workflow admissions to delete for failed hunts",
                component="db",
            )
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
            log_event(
                logger,
                level=logging.ERROR,
                event="db.write.failed",
                status="failed",
                message="Deleting workflow admissions for failed hunts failed",
                component="db",
                exc_info=True,
            )
            raise
        log_event(
            logger,
            level=logging.INFO,
            event="db.write.succeeded",
            status="succeeded",
            message="Deleted workflow admissions for failed hunts",
            component="db",
            result_summary={"deleted_count": int(deleted_rows or 0)},
        )
        return int(deleted_rows or 0)

    def update_hunt_result(
        self,
        session: Session,
        hunt_id: int,
        result: Any,
        title: str,
        summary: str,
        trust_score: int,
    ):
        from db.models.hunt import Hunt

        hunt = session.query(Hunt).filter(Hunt.id == hunt_id).first()
        if hunt:
            log_event(
                logger,
                level=logging.INFO,
                event="db.write.started",
                status="started",
                message="Updating hunt result",
                component="db",
                hunt_id=hunt_id,
            )
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
                log_event(
                    logger,
                    level=logging.ERROR,
                    event="db.write.failed",
                    status="failed",
                    message="Updating hunt result failed",
                    component="db",
                    hunt_id=hunt_id,
                    exc_info=True,
                )
                raise
            session.refresh(hunt)
            log_event(
                logger,
                level=logging.INFO,
                event="db.write.succeeded",
                status="succeeded",
                message="Updated hunt result",
                component="db",
                hunt_id=hunt_id,
            )
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
            log_event(
                logger,
                level=logging.ERROR,
                event="db.write.failed",
                status="failed",
                message="Cannot update hunt status because hunt was not found",
                component="db",
                hunt_id=hunt_id,
                status_value=status_value,
            )
            raise RuntimeError(f"Hunt not found for hunt_id={hunt_id}")

        hunt.status = status_value
        hunt.error_message = error_message
        if status_value != "completed":
            hunt.completed_at = None

        try:
            session.commit()
        except:
            session.rollback()
            log_event(
                logger,
                level=logging.ERROR,
                event="db.write.failed",
                status="failed",
                message="Updating hunt status failed",
                component="db",
                hunt_id=hunt_id,
                status_value=status_value,
                exc_info=True,
            )
            raise
        session.refresh(hunt)
        log_event(
            logger,
            level=logging.INFO,
            event="db.write.succeeded",
            status="succeeded",
            message="Updated hunt status",
            component="db",
            hunt_id=hunt_id,
            status_value=status_value,
        )
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

    def add_hunt_user_in_txn(self, session: Session, hunt_id: int, user_id: str):
        """
        Transaction-friendly version of add_hunt_user.
        Uses savepoint semantics and does not commit the outer transaction.
        """
        from db.models.hunt_user import HuntUser

        existing = (
            session.query(HuntUser)
            .filter(HuntUser.hunt_id == hunt_id, HuntUser.user_id == user_id)
            .first()
        )
        if existing:
            log_event(
                logger,
                level=logging.INFO,
                event="db.write.succeeded",
                status="skipped",
                message="Hunt-user mapping already exists in transaction",
                component="db",
                hunt_id=hunt_id,
            )
            return existing

        try:
            with session.begin_nested():
                hunt_user = HuntUser(hunt_id=hunt_id, user_id=user_id)
                session.add(hunt_user)
                session.flush()
                session.refresh(hunt_user)
                log_event(
                    logger,
                    level=logging.INFO,
                    event="db.write.succeeded",
                    status="succeeded",
                    message="Created hunt-user mapping in transaction",
                    component="db",
                    hunt_id=hunt_id,
                )
                return hunt_user
        except IntegrityError:
            existing = (
                session.query(HuntUser)
                .filter(HuntUser.hunt_id == hunt_id, HuntUser.user_id == user_id)
                .first()
            )
            if existing is None:
                raise
            log_event(
                logger,
                level=logging.WARNING,
                event="db.write.failed",
                status="skipped",
                message="Reused hunt-user mapping after integrity conflict in transaction",
                component="db",
                hunt_id=hunt_id,
            )
            return existing

    def get_users_by_hunt_id(self, session: Session, hunt_id: int):
        from db.models.hunt_user import HuntUser

        rows = session.query(HuntUser).filter(HuntUser.hunt_id == hunt_id).all()
        return [row.user_id for row in rows]

    def get_hunts_by_user_id(self, session: Session, user_id: str):
        from db.models.hunt import Hunt
        from db.models.hunt_user import HuntUser

        log_event(
            logger,
            level=logging.INFO,
            event="db.query.started",
            status="started",
            message="Querying hunts by user id",
            component="db",
        )
        hunts = (
            session.query(Hunt)
            .join(HuntUser, Hunt.id == HuntUser.hunt_id)
            .filter(HuntUser.user_id == user_id)
            .order_by(Hunt.updated_at.desc())
            .all()
        )
        log_event(
            logger,
            level=logging.INFO,
            event="db.query.succeeded",
            status="succeeded",
            message="Queried hunts by user id",
            component="db",
            result_summary={"hunt_count": len(hunts)},
        )
        return hunts

    def get_or_create_user_hunts_limit(
        self,
        session: Session,
        user_id: str,
    ) -> int:
        from db.models.user_hunt_limit import UserHuntLimit

        log_event(
            logger,
            level=logging.INFO,
            event="db.query.started",
            status="started",
            message="Resolving user hunts limit",
            component="db",
        )
        row = session.query(UserHuntLimit).filter(UserHuntLimit.user_id == user_id).first()
        if row:
            log_event(
                logger,
                level=logging.INFO,
                event="db.query.succeeded",
                status="succeeded",
                message="Resolved existing user hunts limit",
                component="db",
                result_summary={"hunts_limit": row.hunts_limit},
            )
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
                log_event(
                    logger,
                    level=logging.ERROR,
                    event="db.write.failed",
                    status="failed",
                    message="Failed to create user hunts limit",
                    component="db",
                    exc_info=True,
                )
                raise
            log_event(
                logger,
                level=logging.WARNING,
                event="db.write.failed",
                status="skipped",
                message="Resolved existing user hunts limit after create conflict",
                component="db",
                result_summary={"hunts_limit": row.hunts_limit},
            )
            return row.hunts_limit
        session.refresh(row)
        log_event(
            logger,
            level=logging.INFO,
            event="db.write.succeeded",
            status="succeeded",
            message="Created default user hunts limit",
            component="db",
            result_summary={"hunts_limit": row.hunts_limit},
        )
        return row.hunts_limit

    def get_active_hunts_count_by_user_id(self, session: Session, user_id: str) -> int:
        from db.models.hunt import Hunt
        from db.models.hunt_user import HuntUser

        log_event(
            logger,
            level=logging.INFO,
            event="db.query.started",
            status="started",
            message="Counting active hunts by user id",
            component="db",
        )
        count = (
            session.query(Hunt.id)
            .join(HuntUser, Hunt.id == HuntUser.hunt_id)
            .filter(
                HuntUser.user_id == user_id,
                Hunt.status.in_(["queued", "starting", "processing", "completed"]),
            )
            .count()
        )
        log_event(
            logger,
            level=logging.INFO,
            event="db.query.succeeded",
            status="succeeded",
            message="Counted active hunts by user id",
            component="db",
            result_summary={"active_hunts_count": count},
        )
        return count


# ✅ singleton instance
db = Database()
