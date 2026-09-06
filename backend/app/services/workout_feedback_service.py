from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import WorkoutFeedbackDB
from app.models.workout_feedback import (
    WorkoutFeedback,
)


class WorkoutFeedbackService:
    def __init__(
        self,
        session_factory: Callable[[], Session] = SessionLocal,
    ):
        self.session_factory = session_factory

    def upsert(
        self,
        session_id: str,
        perceived_effort: float | None,
        execution_feeling: str | None,
        comment: str | None,
    ) -> WorkoutFeedback:
        now = datetime.now(
            timezone.utc
        ).replace(
            tzinfo=None
        )

        db = self.session_factory()

        try:
            existing = (
                db.query(WorkoutFeedbackDB)
                .filter(
                    WorkoutFeedbackDB.session_id
                    == session_id
                )
                .first()
            )

            if existing is None:
                existing = WorkoutFeedbackDB(
                    session_id=session_id,
                    perceived_effort=perceived_effort,
                    execution_feeling=execution_feeling,
                    comment=comment,
                    created_at=now,
                    updated_at=now,
                )

                db.add(existing)

            else:
                existing.perceived_effort = (
                    perceived_effort
                )
                existing.execution_feeling = (
                    execution_feeling
                )
                existing.comment = comment
                existing.updated_at = now

            db.commit()
            db.refresh(existing)

            return self._to_domain(
                existing
            )

        except Exception:
            db.rollback()
            raise

        finally:
            db.close()

    def get(
        self,
        session_id: str,
    ) -> WorkoutFeedback | None:
        db = self.session_factory()

        try:
            item = (
                db.query(WorkoutFeedbackDB)
                .filter(
                    WorkoutFeedbackDB.session_id
                    == session_id
                )
                .first()
            )

            if item is None:
                return None

            return self._to_domain(
                item
            )

        finally:
            db.close()

    def _to_domain(
        self,
        item: WorkoutFeedbackDB,
    ) -> WorkoutFeedback:
        return WorkoutFeedback(
            session_id=item.session_id,
            perceived_effort=item.perceived_effort,
            execution_feeling=(
                item.execution_feeling
            ),
            comment=item.comment,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )