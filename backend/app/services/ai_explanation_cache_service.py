from __future__ import annotations

import hashlib
import json
from datetime import (
    date,
    datetime,
    timezone,
)
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import AIExplanationDB


class AIExplanationCacheService:
    """
    Persistent PostgreSQL cache for AI-generated
    PaceMind explanations.

    Cache identity is based on the complete structured
    context sent to the LLM.

    If the context does not change, the same explanation
    can be reused without another OpenAI API request.
    """

    def __init__(
        self,
        session_factory: Callable[[], Session] = SessionLocal,
    ):
        self.session_factory = session_factory

    def build_context_hash(
        self,
        payload: dict[str, Any],
    ) -> str:
        normalized = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

        return hashlib.sha256(
            normalized.encode("utf-8")
        ).hexdigest()

    def get(
        self,
        context_hash: str,
    ) -> AIExplanationDB | None:
        db = self.session_factory()

        try:
            return (
                db.query(AIExplanationDB)
                .filter(
                    AIExplanationDB.context_hash
                    == context_hash
                )
                .first()
            )

        finally:
            db.close()

    def save(
        self,
        *,
        explanation_type: str,
        target_date: (
            date
            | datetime
            | str
        ),
        context_hash: str,
        model: str,
        explanation_text: str,
    ) -> AIExplanationDB:
        normalized_date = (
            self._normalize_date(
                target_date
            )
        )

        now = datetime.now(
            timezone.utc
        ).replace(
            tzinfo=None
        )

        db = self.session_factory()

        try:
            existing = (
                db.query(AIExplanationDB)
                .filter(
                    AIExplanationDB.context_hash
                    == context_hash
                )
                .first()
            )

            if existing is not None:
                existing.explanation_type = (
                    explanation_type
                )

                existing.target_date = (
                    normalized_date
                )

                existing.model = model

                existing.explanation_text = (
                    explanation_text
                )

                existing.updated_at = now

                db.commit()
                db.refresh(existing)

                return existing

            item = AIExplanationDB(
                explanation_type=(
                    explanation_type
                ),
                target_date=(
                    normalized_date
                ),
                context_hash=(
                    context_hash
                ),
                model=model,
                explanation_text=(
                    explanation_text
                ),
                created_at=now,
                updated_at=now,
            )

            db.add(item)
            db.commit()
            db.refresh(item)

            return item

        except Exception:
            db.rollback()
            raise

        finally:
            db.close()

    def _normalize_date(
        self,
        value: (
            date
            | datetime
            | str
        ),
    ) -> datetime:
        if isinstance(
            value,
            datetime,
        ):
            return datetime.combine(
                value.date(),
                datetime.min.time(),
            )

        if isinstance(
            value,
            date,
        ):
            return datetime.combine(
                value,
                datetime.min.time(),
            )

        if isinstance(
            value,
            str,
        ):
            normalized = (
                value.strip()
            )

            try:
                parsed = date.fromisoformat(
                    normalized
                )

            except ValueError as exc:
                raise ValueError(
                    "Date must use "
                    "YYYY-MM-DD format."
                ) from exc

            return datetime.combine(
                parsed,
                datetime.min.time(),
            )

        raise TypeError(
            "Date must be date, "
            "datetime or ISO string."
        )