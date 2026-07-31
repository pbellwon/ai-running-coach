from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.db.models import WorkoutDB
from app.models.executed_session import (
    ExecutedSession,
    ExecutedSessionComponent,
)
from app.services.executed_workout_type_resolver import (
    ExecutedWorkoutTypeResolver,
)


class CompositeSessionBuilder:
    """
    Converts individual recorded workouts into logical training sessions.

    Running activities may be grouped when they:
    - happen on the same calendar date;
    - are separated by no more than the configured time gap;
    - belong to the same running session.

    Non-running activities are kept as separate sessions because a strength
    workout and an easy bike ride on the same day are usually separate
    training stimuli.
    """

    DEFAULT_RUNNING_GAP_MINUTES = 45

    QUALITY_TYPES = {
        "race",
        "vo2max",
        "intervals",
        "threshold",
        "tempo_run",
        "tempo",
    }

    EASY_TYPES = {
        "easy_run",
        "easy_run+strides",
        "easy_run+hills",
        "recovery_run",
        "unknown",
    }

    def __init__(
        self,
        running_gap_minutes: int = DEFAULT_RUNNING_GAP_MINUTES,
        resolver: ExecutedWorkoutTypeResolver | None = None,
    ):
        if running_gap_minutes < 0:
            raise ValueError(
                "running_gap_minutes cannot be negative."
            )

        self.running_gap = timedelta(
            minutes=running_gap_minutes
        )

        self.resolver = (
            resolver
            if resolver is not None
            else ExecutedWorkoutTypeResolver()
        )

    def build(
        self,
        workouts: list[WorkoutDB],
    ) -> list[ExecutedSession]:
        valid_workouts = [
            workout
            for workout in workouts
            if workout.start_time is not None
        ]

        ordered_workouts = sorted(
            valid_workouts,
            key=lambda workout: workout.start_time,
        )

        components = [
            self._build_component(workout)
            for workout in ordered_workouts
        ]

        groups = self._group_components(components)

        sessions = [
            self._build_session(
                components=group,
                session_index=index,
            )
            for index, group in enumerate(groups, start=1)
        ]

        return sessions

    def _build_component(
        self,
        workout: WorkoutDB,
    ) -> ExecutedSessionComponent:
        type_result = self.resolver.resolve(workout)

        start_time = workout.start_time

        duration_sec = workout.duration_sec or 0

        end_time = start_time + timedelta(
            seconds=duration_sec
        )

        duration_min = (
            round(duration_sec / 60, 1)
            if workout.duration_sec is not None
            else None
        )

        distance_km = (
            round(workout.distance_km, 2)
            if workout.distance_km is not None
            else None
        )

        return ExecutedSessionComponent(
            workout=workout,
            workout_file=workout.source_file or "",
            start_time=start_time,
            end_time=end_time,
            sport=self._normalize_sport(workout.sport),
            distance_km=distance_km,
            duration_min=duration_min,
            workout_type=type_result.get(
                "workout_type",
                "unknown",
            ),
            confidence=float(
                type_result.get("confidence", 0)
            ),
            classification_method=type_result.get(
                "classification_method",
                "unknown",
            ),
            warnings=list(
                type_result.get("warnings", [])
            ),
        )

    def _group_components(
        self,
        components: list[ExecutedSessionComponent],
    ) -> list[list[ExecutedSessionComponent]]:
        groups: list[list[ExecutedSessionComponent]] = []

        for component in components:
            if not groups:
                groups.append([component])
                continue

            current_group = groups[-1]
            previous_component = current_group[-1]

            if self._should_join_group(
                previous_component=previous_component,
                current_component=component,
                current_group=current_group,
            ):
                current_group.append(component)
            else:
                groups.append([component])

        return groups

    def _should_join_group(
        self,
        previous_component: ExecutedSessionComponent,
        current_component: ExecutedSessionComponent,
        current_group: list[ExecutedSessionComponent],
    ) -> bool:
        if previous_component.start_time.date() != (
            current_component.start_time.date()
        ):
            return False

        if previous_component.sport != "running":
            return False

        if current_component.sport != "running":
            return False

        gap = (
            current_component.start_time
            - previous_component.end_time
        )

        if gap < timedelta(0):
            gap = timedelta(0)

        if gap > self.running_gap:
            return False

        return self._looks_like_same_running_session(
            current_group=current_group,
            candidate=current_component,
        )

    def _looks_like_same_running_session(
        self,
        current_group: list[ExecutedSessionComponent],
        candidate: ExecutedSessionComponent,
    ) -> bool:
        """
        Conservative grouping rule.

        A nearby running activity joins the session when:
        - either activity is easy/supporting;
        - or the existing group already contains a quality component;
        - or the candidate itself is a quality component.

        Two long independent easy runs are not automatically grouped.
        """

        existing_types = {
            component.workout_type
            for component in current_group
        }

        candidate_type = candidate.workout_type

        existing_has_quality = bool(
            existing_types.intersection(self.QUALITY_TYPES)
        )

        candidate_is_quality = (
            candidate_type in self.QUALITY_TYPES
        )

        existing_has_support = bool(
            existing_types.intersection(self.EASY_TYPES)
        )

        candidate_is_support = (
            candidate_type in self.EASY_TYPES
        )

        if existing_has_quality or candidate_is_quality:
            return True

        if existing_has_support and candidate_is_support:
            total_existing_duration = sum(
                component.duration_min or 0
                for component in current_group
            )

            candidate_duration = candidate.duration_min or 0

            # Prevent two substantial easy runs from being merged simply
            # because they happened close together.
            if (
                total_existing_duration >= 40
                and candidate_duration >= 40
            ):
                return False

            return True

        return False

    def _build_session(
        self,
        components: list[ExecutedSessionComponent],
        session_index: int,
    ) -> ExecutedSession:
        if not components:
            raise ValueError(
                "Cannot build a session without components."
            )

        self._assign_component_roles(components)

        session_type = self._resolve_session_type(
            components
        )

        confidence = self._resolve_session_confidence(
            components=components,
            session_type=session_type,
        )

        classification_method = (
            "composite_session"
            if len(components) > 1
            else components[0].classification_method
        )

        warnings = self._collect_warnings(
            components=components,
        )

        if len(components) > 1:
            warnings.append(
                "Logical session composed of multiple recorded activities."
            )

        total_distance_km = self._sum_optional_values(
            component.distance_km
            for component in components
        )

        total_duration_min = self._sum_optional_values(
            component.duration_min
            for component in components
        )

        start_time = min(
            component.start_time
            for component in components
        )

        end_time = max(
            component.end_time
            for component in components
        )

        session_id = (
            f"{start_time.date().isoformat()}"
            f"-session-{session_index}"
        )

        return ExecutedSession(
            session_id=session_id,
            start_time=start_time,
            end_time=end_time,
            sport_family=self._resolve_sport_family(
                components
            ),
            workout_type=session_type,
            confidence=confidence,
            classification_method=classification_method,
            components=components,
            total_distance_km=total_distance_km,
            total_duration_min=total_duration_min,
            warnings=warnings,
        )

    def _assign_component_roles(
        self,
        components: list[ExecutedSessionComponent],
    ) -> None:
        if len(components) == 1:
            components[0].role = "main"
            return

        main_index = self._select_main_component_index(
            components
        )

        for index, component in enumerate(components):
            if index == main_index:
                component.role = "main"
            elif index < main_index:
                component.role = "warmup"
            else:
                component.role = "cooldown"

    def _select_main_component_index(
        self,
        components: list[ExecutedSessionComponent],
    ) -> int:
        quality_candidates = [
            (
                index,
                component,
            )
            for index, component in enumerate(components)
            if component.workout_type in self.QUALITY_TYPES
        ]

        if quality_candidates:
            return max(
                quality_candidates,
                key=lambda item: self._main_component_score(
                    item[1]
                ),
            )[0]

        return max(
            range(len(components)),
            key=lambda index: self._main_component_score(
                components[index]
            ),
        )

    def _main_component_score(
        self,
        component: ExecutedSessionComponent,
    ) -> tuple:
        quality_priority = (
            1
            if component.workout_type in self.QUALITY_TYPES
            else 0
        )

        distance = component.distance_km or 0
        duration = component.duration_min or 0
        confidence = component.confidence

        return (
            quality_priority,
            confidence,
            distance,
            duration,
        )

    def _resolve_session_type(
        self,
        components: list[ExecutedSessionComponent],
    ) -> str:
        main_component = next(
            (
                component
                for component in components
                if component.role == "main"
            ),
            components[0],
        )

        return main_component.workout_type

    def _resolve_session_confidence(
        self,
        components: list[ExecutedSessionComponent],
        session_type: str,
    ) -> float:
        relevant_components = [
            component
            for component in components
            if component.workout_type == session_type
            or component.role == "main"
        ]

        if not relevant_components:
            return 0.0

        confidence = max(
            component.confidence
            for component in relevant_components
        )

        if len(components) > 1:
            confidence = min(
                confidence + 0.05,
                1.0,
            )

        return round(confidence, 2)

    def _resolve_sport_family(
        self,
        components: list[ExecutedSessionComponent],
    ) -> str:
        sports = {
            component.sport
            for component in components
        }

        if len(sports) == 1:
            return next(iter(sports))

        return "mixed"

    def _collect_warnings(
        self,
        components: list[ExecutedSessionComponent],
    ) -> list[str]:
        warnings: list[str] = []

        for component in components:
            for warning in component.warnings:
                if warning not in warnings:
                    warnings.append(warning)

        return warnings

    def _sum_optional_values(
        self,
        values: Any,
    ) -> float | None:
        filtered_values = [
            value
            for value in values
            if value is not None
        ]

        if not filtered_values:
            return None

        return round(
            sum(filtered_values),
            2,
        )

    def _normalize_sport(
        self,
        value: str | None,
    ) -> str:
        if value is None:
            return "unknown"

        return value.strip().lower()