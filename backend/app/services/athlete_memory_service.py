from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import AthleteMemoryDB
from app.models.athlete_memory import (
    AthleteMemory,
)


class AthleteMemoryService:
    def __init__(
        self,
        session_factory: Callable[[], Session] = SessionLocal,
    ):
        self.session_factory = session_factory

    def create(
        self,
        category: str,
        memory_text: str,
        source: str,
        confidence: float | None,
    ) -> AthleteMemory:
        now = datetime.now(
            timezone.utc
        ).replace(
            tzinfo=None
        )

        db = self.session_factory()

        try:
            item = AthleteMemoryDB(
                category=category,
                memory_text=memory_text,
                source=source,
                confidence=confidence,
                is_active=True,
                created_at=now,
                updated_at=now,
            )

            db.add(item)
            db.commit()
            db.refresh(item)

            return self._to_domain(item)

        except Exception:
            db.rollback()
            raise

        finally:
            db.close()

    def update(
        self,
        memory_id: int,
        category: str,
        memory_text: str,
        source: str,
        confidence: float | None,
    ) -> AthleteMemory | None:
        now = datetime.now(
            timezone.utc
        ).replace(
            tzinfo=None
        )

        db = self.session_factory()

        try:
            item = (
                db.query(AthleteMemoryDB)
                .filter(
                    AthleteMemoryDB.id
                    == memory_id
                )
                .first()
            )

            if item is None:
                return None

            item.category = category
            item.memory_text = memory_text
            item.source = source
            item.confidence = confidence
            item.updated_at = now

            db.commit()
            db.refresh(item)

            return self._to_domain(item)

        except Exception:
            db.rollback()
            raise

        finally:
            db.close()

    def list_active(
        self,
    ) -> list[AthleteMemory]:
        db = self.session_factory()

        try:
            items = (
                db.query(AthleteMemoryDB)
                .filter(
                    AthleteMemoryDB.is_active.is_(True)
                )
                .order_by(
                    AthleteMemoryDB.id.asc()
                )
                .all()
            )

            return [
                self._to_domain(item)
                for item in items
            ]

        finally:
            db.close()

    def deactivate(
        self,
        memory_id: int,
    ) -> AthleteMemory | None:
        now = datetime.now(
            timezone.utc
        ).replace(
            tzinfo=None
        )

        db = self.session_factory()

        try:
            item = (
                db.query(AthleteMemoryDB)
                .filter(
                    AthleteMemoryDB.id
                    == memory_id
                )
                .first()
            )

            if item is None:
                return None

            item.is_active = False
            item.updated_at = now

            db.commit()
            db.refresh(item)

            return self._to_domain(item)

        except Exception:
            db.rollback()
            raise

        finally:
            db.close()

    def _to_domain(
        self,
        item: AthleteMemoryDB,
    ) -> AthleteMemory:
        return AthleteMemory(
            id=item.id,
            category=item.category,
            memory_text=item.memory_text,
            source=item.source,
            confidence=item.confidence,
            is_active=item.is_active,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )