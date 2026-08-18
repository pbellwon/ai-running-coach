from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta

from app.db.database import SessionLocal
from app.db.models import WorkoutDB
from app.models.executed_session import ExecutedSession
from app.models.training_context import (
    LastTrainingSession,
    TrainingContext,
)
from app.services.composite_session_builder import (
    CompositeSessionBuilder,
)


class TrainingContextService:
    """
    Builds recent training context for a selected date.

    Raw WorkoutDB activities are converted into logical sessions
    before they are summarized.

    Main window:
    - seven calendar days, including target_date.

    Short-term window:
    - final 48 hours of the main window.

    Session role such as long_run is kept separate from
    workout_type.

    Example:
        workout_type = easy_run
        session_role = long_run

    This allows a long easy run to be counted both as:
    - an easy physiological session
    - a long run in the weekly structure
    """

    WINDOW_DAYS = 7
    RECENT_HOURS = 48

    EASY_TYPES = {
        "easy_run",
        "recovery_run",
        "easy_run+strides",
        "easy_run+hills",
    }

    QUALITY_TYPES = {
        "tempo",
        "tempo_run",
        "threshold",
        "intervals",
        "vo2max",
        "race",
    }

    LONG_RUN_TYPES = {
        "long_run",
    }

    RUNNING_TYPES = (
        EASY_TYPES
        | QUALITY_TYPES
        | LONG_RUN_TYPES
    )

    STRENGTH_TYPES = {
        "strength",
    }

    CYCLING_TYPES = {
        "bike",
        "cycling",
        "indoor_cycling",
        "virtual_ride",
        "low_intensity_cross_training",
    }

    def build(
        self,
        target_date: date | datetime | str,
    ) -> TrainingContext:
        normalized_date = self._normalize_date(
            target_date
        )

        window_start = (
            normalized_date
            - timedelta(
                days=self.WINDOW_DAYS - 1
            )
        )

        workouts = self._get_workouts(
            window_start=window_start,
            window_end=normalized_date,
        )

        declared_role_by_source_file = (
            self._build_declared_role_map(
                workouts
            )
        )

        sessions = (
            CompositeSessionBuilder().build(
                workouts
            )
        )

        return self.summarize(
            target_date=normalized_date,
            sessions=sessions,
            source_activities_count=len(
                workouts
            ),
            declared_role_by_source_file=(
                declared_role_by_source_file
            ),
        )

    def summarize(
        self,
        target_date: date | datetime | str,
        sessions: list[ExecutedSession],
        source_activities_count: int,
        declared_role_by_source_file: (
            dict[str, str] | None
        ) = None,
    ) -> TrainingContext:
        normalized_date = self._normalize_date(
            target_date
        )

        declared_role_by_source_file = (
            declared_role_by_source_file
            or {}
        )

        window_end = datetime.combine(
            normalized_date
            + timedelta(days=1),
            datetime.min.time(),
        )

        recent_cutoff = (
            window_end
            - timedelta(
                hours=self.RECENT_HOURS
            )
        )

        sorted_sessions = sorted(
            sessions,
            key=lambda session: (
                session.start_time
            ),
        )

        running_sessions = [
            session
            for session in sorted_sessions
            if self._is_running_session(
                session
            )
        ]

        easy_sessions = [
            session
            for session in running_sessions
            if (
                session.workout_type
                in self.EASY_TYPES
            )
        ]

        quality_sessions = [
            session
            for session in running_sessions
            if (
                session.workout_type
                in self.QUALITY_TYPES
            )
        ]

        long_run_sessions = [
            session
            for session in running_sessions
            if self._is_long_run_session(
                session=session,
                declared_role_by_source_file=(
                    declared_role_by_source_file
                ),
            )
        ]

        strength_sessions = [
            session
            for session in sorted_sessions
            if self._is_strength_session(
                session
            )
        ]

        cycling_sessions = [
            session
            for session in sorted_sessions
            if self._is_cycling_session(
                session
            )
        ]

        known_session_ids = {
            session.session_id
            for session in (
                running_sessions
                + strength_sessions
                + cycling_sessions
            )
        }

        other_sessions = [
            session
            for session in sorted_sessions
            if (
                session.session_id
                not in known_session_ids
            )
        ]

        recent_sessions = [
            session
            for session in sorted_sessions
            if (
                recent_cutoff
                <= session.start_time
                < window_end
            )
        ]

        recent_quality_sessions = [
            session
            for session in recent_sessions
            if (
                session.workout_type
                in self.QUALITY_TYPES
            )
        ]

        recent_strength_sessions = [
            session
            for session in recent_sessions
            if self._is_strength_session(
                session
            )
        ]

        type_counts = Counter(
            session.workout_type
            for session in sorted_sessions
        )

        last_session = (
            self._build_last_session(
                sessions=sorted_sessions,
                window_end=window_end,
            )
        )

        return TrainingContext(
            target_date=normalized_date,
            window_days=self.WINDOW_DAYS,

            source_activities_count=(
                source_activities_count
            ),
            logical_sessions_count=len(
                sorted_sessions
            ),

            total_training_min=(
                self._sum_duration(
                    sorted_sessions
                )
            ),
            running_distance_km=(
                self._sum_distance(
                    running_sessions
                )
            ),
            running_duration_min=(
                self._sum_duration(
                    running_sessions
                )
            ),

            running_sessions=len(
                running_sessions
            ),
            easy_sessions=len(
                easy_sessions
            ),
            quality_sessions=len(
                quality_sessions
            ),
            long_run_sessions=len(
                long_run_sessions
            ),
            strength_sessions=len(
                strength_sessions
            ),
            cycling_sessions=len(
                cycling_sessions
            ),
            other_sessions=len(
                other_sessions
            ),

            recent_48h_sessions=len(
                recent_sessions
            ),
            recent_48h_training_min=(
                self._sum_duration(
                    recent_sessions
                )
            ),
            recent_48h_quality_sessions=len(
                recent_quality_sessions
            ),
            recent_48h_strength_sessions=len(
                recent_strength_sessions
            ),

            type_counts=dict(
                sorted(
                    type_counts.items()
                )
            ),

            last_session=last_session,
        )

    def _build_declared_role_map(
        self,
        workouts: list[WorkoutDB],
    ) -> dict[str, str]:
        result: dict[str, str] = {}

        for workout in workouts:
            source_file = getattr(
                workout,
                "source_file",
                None,
            )

            session_role = getattr(
                workout,
                "declared_session_role",
                None,
            )

            if (
                source_file
                and session_role
            ):
                result[source_file] = (
                    session_role
                )

        return result

    def _is_long_run_session(
        self,
        session: ExecutedSession,
        declared_role_by_source_file: (
            dict[str, str]
        ),
    ) -> bool:
        # Compatibility with sessions that may already
        # have long_run as their workout_type.
        if (
            session.workout_type
            in self.LONG_RUN_TYPES
        ):
            return True

        # Current Intervals.icu approach:
        # workout_type and session_role are independent.
        for source_file in session.source_files:
            role = (
                declared_role_by_source_file.get(
                    source_file
                )
            )

            if role == "long_run":
                return True

        return False

    def _get_workouts(
        self,
        window_start: date,
        window_end: date,
    ) -> list[WorkoutDB]:
        range_start = datetime.combine(
            window_start,
            datetime.min.time(),
        )

        range_end = datetime.combine(
            window_end
            + timedelta(days=1),
            datetime.min.time(),
        )

        db = SessionLocal()

        try:
            return (
                db.query(WorkoutDB)
                .filter(
                    WorkoutDB.start_time
                    >= range_start
                )
                .filter(
                    WorkoutDB.start_time
                    < range_end
                )
                .order_by(
                    WorkoutDB.start_time.asc()
                )
                .all()
            )

        finally:
            db.close()

    def _build_last_session(
        self,
        sessions: list[
            ExecutedSession
        ],
        window_end: datetime,
    ) -> LastTrainingSession | None:
        if not sessions:
            return None

        session = sessions[-1]

        hours_before_window_end = (
            window_end
            - session.end_time
        ).total_seconds() / 3600

        return LastTrainingSession(
            session_id=(
                session.session_id
            ),
            start_time=(
                session.start_time
            ),
            sport_family=(
                session.sport_family
            ),
            workout_type=(
                session.workout_type
            ),
            distance_km=(
                session.total_distance_km
            ),
            duration_min=(
                session.total_duration_min
            ),
            hours_before_window_end=round(
                hours_before_window_end,
                1,
            ),
        )

    def _is_running_session(
        self,
        session: ExecutedSession,
    ) -> bool:
        if (
            session.sport_family
            == "running"
        ):
            return True

        return (
            session.workout_type
            in self.RUNNING_TYPES
        )

    def _is_strength_session(
        self,
        session: ExecutedSession,
    ) -> bool:
        if (
            session.workout_type
            in self.STRENGTH_TYPES
        ):
            return True

        return (
            session.sport_family
            == "training"
        )

    def _is_cycling_session(
        self,
        session: ExecutedSession,
    ) -> bool:
        if (
            session.workout_type
            in self.CYCLING_TYPES
        ):
            return True

        return (
            session.sport_family
            == "cycling"
        )

    def _sum_distance(
        self,
        sessions: list[
            ExecutedSession
        ],
    ) -> float:
        return round(
            sum(
                (
                    session.total_distance_km
                    or 0
                )
                for session in sessions
            ),
            2,
        )

    def _sum_duration(
        self,
        sessions: list[
            ExecutedSession
        ],
    ) -> float:
        return round(
            sum(
                (
                    session.total_duration_min
                    or 0
                )
                for session in sessions
            ),
            1,
        )

    def _normalize_date(
        self,
        value: date | datetime | str,
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
            normalized = value.strip()

            try:
                return date.fromisoformat(
                    normalized
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