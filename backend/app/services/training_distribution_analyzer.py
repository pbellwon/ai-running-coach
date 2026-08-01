from __future__ import annotations

from collections import Counter

from app.models.executed_session import ExecutedSession


class TrainingDistributionAnalyzer:
    """
    Summarizes executed training distribution.

    Two concepts are intentionally separated:

    - workout_type:
      physiological/executed character of the session
      e.g. easy_run, tempo_run, vo2max

    - session_role:
      role of the session in the training week
      e.g. long_run

    session_role can be inferred from the matched planned workout.
    """

    EASY_TYPES = {
        "easy_run",
        "recovery_run",
        "easy_run+strides",
        "easy_run+hills",
    }

    QUALITY_TYPES = {
        "tempo_run",
        "tempo",
        "threshold",
        "vo2max",
        "intervals",
        "race",
    }

    LONG_RUN_TYPES = {
        "long_run",
    }

    STRENGTH_TYPES = {
        "strength",
    }

    CROSS_TRAINING_TYPES = {
        "bike",
        "swimming",
        "cross_training",
        "low_intensity_cross_training",
        "other_endurance",
    }

    MOBILITY_TYPES = {
        "mobility",
    }

    RUNNING_TYPES = (
        EASY_TYPES
        | QUALITY_TYPES
        | LONG_RUN_TYPES
    )

    def analyze(
        self,
        sessions: list[ExecutedSession],
        planned_type_by_session_id: dict[str, str] | None = None,
    ) -> dict:
        planned_type_by_session_id = (
            planned_type_by_session_id or {}
        )

        type_counts = Counter(
            session.workout_type
            for session in sessions
        )

        running_sessions = [
            session
            for session in sessions
            if self._is_running_session(session)
        ]

        easy_sessions = [
            session
            for session in running_sessions
            if session.workout_type in self.EASY_TYPES
        ]

        quality_sessions = [
            session
            for session in running_sessions
            if session.workout_type in self.QUALITY_TYPES
        ]

        long_run_sessions = [
            session
            for session in running_sessions
            if self._is_long_run(
                session=session,
                planned_type_by_session_id=(
                    planned_type_by_session_id
                ),
            )
        ]

        strength_sessions = [
            session
            for session in sessions
            if session.workout_type in self.STRENGTH_TYPES
        ]

        cross_training_sessions = [
            session
            for session in sessions
            if session.workout_type
            in self.CROSS_TRAINING_TYPES
        ]

        mobility_sessions = [
            session
            for session in sessions
            if session.workout_type in self.MOBILITY_TYPES
        ]

        unknown_sessions = [
            session
            for session in sessions
            if session.workout_type == "unknown"
        ]

        running_distance_km = self._sum_distance(
            running_sessions
        )

        easy_session_distance_km = self._sum_distance(
            easy_sessions
        )

        quality_session_distance_km = self._sum_distance(
            quality_sessions
        )

        quality_component_distance_km = round(
            sum(
                self._quality_component_distance(session)
                for session in quality_sessions
            ),
            2,
        )

        long_run_distance_km = self._sum_distance(
            long_run_sessions
        )

        running_duration_min = self._sum_duration(
            running_sessions
        )

        strength_duration_min = self._sum_duration(
            strength_sessions
        )

        cross_training_duration_min = self._sum_duration(
            cross_training_sessions
        )

        total_training_duration_min = self._sum_duration(
            sessions
        )

        category_counts = {
            "easy": len(easy_sessions),
            "quality": len(quality_sessions),
            "long_run": len(long_run_sessions),
            "strength": len(strength_sessions),
            "cross_training": len(
                cross_training_sessions
            ),
            "mobility": len(mobility_sessions),
            "unknown": len(unknown_sessions),
        }

        return {
            "session_counts": {
                "total": len(sessions),
                "running": len(running_sessions),
                "easy": len(easy_sessions),
                "quality": len(quality_sessions),
                "long_run": len(long_run_sessions),
                "strength": len(strength_sessions),
                "cross_training": len(
                    cross_training_sessions
                ),
                "mobility": len(mobility_sessions),
                "unknown": len(unknown_sessions),
            },
            "type_counts": dict(
                sorted(type_counts.items())
            ),
            "category_counts": category_counts,
            "distance": {
                "running_total_km": running_distance_km,

                # Full distance of sessions classified as easy.
                "easy_session_km": (
                    easy_session_distance_km
                ),

                # Full distance of quality sessions,
                # including warm-up/cooldown when part
                # of a composite session.
                "quality_session_km": (
                    quality_session_distance_km
                ),

                # Actual quality component only.
                "quality_component_km": (
                    quality_component_distance_km
                ),

                # Full distance of sessions whose role
                # in the plan was long_run.
                "long_run_km": long_run_distance_km,

                "long_run_share_percent": (
                    self._percentage(
                        long_run_distance_km,
                        running_distance_km,
                    )
                ),
            },
            "duration": {
                "total_training_min": (
                    total_training_duration_min
                ),
                "running_min": running_duration_min,
                "strength_min": strength_duration_min,
                "cross_training_min": (
                    cross_training_duration_min
                ),
                "running_share_percent": (
                    self._percentage(
                        running_duration_min,
                        total_training_duration_min,
                    )
                ),
            },
            "ratios": {
                "easy_to_quality_session_ratio": (
                    self._safe_ratio(
                        len(easy_sessions),
                        len(quality_sessions),
                    )
                ),
                "quality_session_share_percent": (
                    self._percentage(
                        len(quality_sessions),
                        len(running_sessions),
                    )
                ),
            },
        }

    def _is_long_run(
        self,
        session: ExecutedSession,
        planned_type_by_session_id: dict[str, str],
    ) -> bool:
        if session.workout_type in self.LONG_RUN_TYPES:
            return True

        planned_type = planned_type_by_session_id.get(
            session.session_id
        )

        return planned_type in self.LONG_RUN_TYPES

    def _quality_component_distance(
        self,
        session: ExecutedSession,
    ) -> float:
        """
        For a composite quality session, count only components
        that actually represent quality work.

        For a single-activity quality session, the whole session
        is considered the quality component.
        """

        if not session.components:
            return session.total_distance_km or 0

        if len(session.components) == 1:
            return session.total_distance_km or 0

        quality_components = [
            component
            for component in session.components
            if (
                component.role == "main"
                and component.workout_type
                in self.QUALITY_TYPES
            )
        ]

        if not quality_components:
            return session.total_distance_km or 0

        return sum(
            component.distance_km or 0
            for component in quality_components
        )

    def _is_running_session(
        self,
        session: ExecutedSession,
    ) -> bool:
        if session.sport_family == "running":
            return True

        return session.workout_type in self.RUNNING_TYPES

    def _sum_distance(
        self,
        sessions: list[ExecutedSession],
    ) -> float:
        return round(
            sum(
                session.total_distance_km or 0
                for session in sessions
            ),
            2,
        )

    def _sum_duration(
        self,
        sessions: list[ExecutedSession],
    ) -> float:
        return round(
            sum(
                session.total_duration_min or 0
                for session in sessions
            ),
            1,
        )

    def _percentage(
        self,
        numerator: float,
        denominator: float,
    ) -> float | None:
        if denominator <= 0:
            return None

        return round(
            numerator / denominator * 100,
            1,
        )

    def _safe_ratio(
        self,
        numerator: float,
        denominator: float,
    ) -> float | None:
        if denominator <= 0:
            return None

        return round(
            numerator / denominator,
            2,
        )