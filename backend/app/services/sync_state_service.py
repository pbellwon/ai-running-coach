from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.db.database import SessionLocal
from app.db.models import SyncStateDB


class SyncStateService:
    def can_run(
        self,
        sync_name: str,
        cooldown_minutes: int,
    ) -> tuple[bool, int]:
        db = SessionLocal()

        try:
            state = (
                db.query(SyncStateDB)
                .filter(
                    SyncStateDB.sync_name == sync_name
                )
                .first()
            )

            if state is None:
                return True, 0

            now = datetime.now(
                timezone.utc
            ).replace(
                tzinfo=None
            )

            cooldown = timedelta(
                minutes=cooldown_minutes
            )

            next_allowed_at = (
                state.last_success_at
                + cooldown
            )

            if now >= next_allowed_at:
                return True, 0

            remaining = (
                next_allowed_at - now
            )

            remaining_seconds = max(
                1,
                int(
                    remaining.total_seconds()
                ),
            )

            return (
                False,
                remaining_seconds,
            )

        finally:
            db.close()

    def mark_success(
        self,
        sync_name: str,
    ) -> None:
        db = SessionLocal()

        try:
            state = (
                db.query(SyncStateDB)
                .filter(
                    SyncStateDB.sync_name == sync_name
                )
                .first()
            )

            now = datetime.now(
                timezone.utc
            ).replace(
                tzinfo=None
            )

            if state is None:
                state = SyncStateDB(
                    sync_name=sync_name,
                    last_success_at=now,
                )

                db.add(state)

            else:
                state.last_success_at = now

            db.commit()

        finally:
            db.close()