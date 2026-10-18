from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import AdaptationDecisionRecordDB
from app.models.adaptation_decision_record import (
    AdaptationDecisionRecord,
    AdaptationResponse,
)


class AdaptationDecisionService:
    def __init__(
        self,
        session_factory: Callable[[], Session] = SessionLocal,
    ):
        self.session_factory = session_factory

    def save(
        self,
        target_date: str,
        original_workout_type: str,
        proposed_workout_type: str | None,
        proposal_decision: str,
        athlete_response: AdaptationResponse,
    ) -> AdaptationDecisionRecord:
        now = datetime.now(
            timezone.utc
        ).replace(
            tzinfo=None
        )

        db = self.session_factory()

        try:
            item = AdaptationDecisionRecordDB(
                target_date=target_date,
                original_workout_type=original_workout_type,
                proposed_workout_type=proposed_workout_type,
                proposal_decision=proposal_decision,
                athlete_response=athlete_response,
                created_at=now,
            )

            db.add(item)
            db.commit()
            db.refresh(item)

            return AdaptationDecisionRecord(
                target_date=item.target_date,
                original_workout_type=item.original_workout_type,
                proposed_workout_type=item.proposed_workout_type,
                proposal_decision=item.proposal_decision,
                athlete_response=item.athlete_response,
                created_at=item.created_at,
            )

        except Exception:
            db.rollback()
            raise

        finally:
            db.close()