from __future__ import annotations

from dataclasses import (
    asdict,
    is_dataclass,
)
from datetime import (
    date,
    datetime,
)
from enum import Enum
from typing import Any

from app.models.coach_context import (
    CoachContext,
)
from app.services.athlete_memory_service import (
    AthleteMemoryService,
)
from app.services.current_goal_service import (
    CurrentGoalService,
)
from app.services.goal_progress_service import (
    GoalProgressService,
)
from app.services.pacemind_today_service import (
    PaceMindTodayService,
)


class CoachContextService:
    """
    Builds the structured context used by AI-facing
    PaceMind services.

    Responsibilities:
    - reuse deterministic PaceMind services;
    - load the athlete's current primary goal;
    - collect today's state;
    - collect goal progress;
    - collect active athlete memory;
    - normalize everything into JSON-safe structures.

    This service does NOT:
    - call an LLM;
    - make training decisions;
    - modify the training plan.
    """

    SCHEMA_VERSION = "1.0"

    def __init__(
        self,
        today_service=None,
        goal_progress_service=None,
        athlete_memory_service=None,
        current_goal_service=None,
    ):
        self.today_service = (
            today_service
            if today_service is not None
            else PaceMindTodayService()
        )

        self.goal_progress_service = (
            goal_progress_service
            if goal_progress_service
            is not None
            else GoalProgressService()
        )

        self.athlete_memory_service = (
            athlete_memory_service
            if athlete_memory_service
            is not None
            else AthleteMemoryService()
        )

        self.current_goal_service = (
            current_goal_service
            if current_goal_service
            is not None
            else CurrentGoalService()
        )

    def build(
        self,
        target_date: (
            date
            | datetime
            | str
        ),
    ) -> CoachContext:
        normalized_date = (
            self._normalize_date(
                target_date
            )
        )

        target_date_iso = (
            normalized_date.isoformat()
        )

        goal = (
            self.current_goal_service
            .get()
        )

        today = (
            self.today_service.build(
                target_date_iso
            )
        )

        goal_progress = (
            self.goal_progress_service
            .build(
                goal=goal,
                target_date=(
                    normalized_date
                ),
            )
        )

        athlete_memory = (
            self.athlete_memory_service
            .list_active()
        )

        return CoachContext(
            schema_version=(
                self.SCHEMA_VERSION
            ),
            target_date=(
                target_date_iso
            ),
            goal=self._serialize(
                goal
            ),
            today=self._serialize(
                today
            ),
            goal_progress=(
                self._serialize(
                    goal_progress
                )
            ),
            athlete_memory=[
                self._serialize(item)
                for item
                in athlete_memory
            ],
        )

    def _normalize_date(
        self,
        value: (
            date
            | datetime
            | str
        ),
    ) -> date:
        if isinstance(
            value,
            datetime,
        ):
            return value.date()

        if isinstance(
            value,
            date,
        ):
            return value

        if isinstance(
            value,
            str,
        ):
            normalized = (
                value.strip()
            )

            try:
                return (
                    date.fromisoformat(
                        normalized
                    )
                )

            except ValueError as exc:
                raise ValueError(
                    "Date must use "
                    "YYYY-MM-DD format."
                ) from exc

        raise TypeError(
            "Date must be date, "
            "datetime or ISO string."
        )

    def _serialize(
        self,
        value: Any,
    ) -> Any:
        if value is None:
            return None

        if is_dataclass(value):
            return self._serialize(
                asdict(value)
            )

        if isinstance(
            value,
            Enum,
        ):
            return self._serialize(
                value.value
            )

        if isinstance(
            value,
            datetime,
        ):
            return value.isoformat()

        if isinstance(
            value,
            date,
        ):
            return value.isoformat()

        if isinstance(
            value,
            dict,
        ):
            return {
                str(key): (
                    self._serialize(
                        item
                    )
                )
                for key, item
                in value.items()
            }

        if isinstance(
            value,
            (
                list,
                tuple,
                set,
            ),
        ):
            return [
                self._serialize(item)
                for item in value
            ]

        if isinstance(
            value,
            (
                str,
                int,
                float,
                bool,
            ),
        ):
            return value

        if hasattr(
            value,
            "__dict__",
        ):
            return {
                key: (
                    self._serialize(
                        item
                    )
                )
                for key, item
                in vars(value).items()
                if not key.startswith(
                    "_"
                )
            }

        return str(value)