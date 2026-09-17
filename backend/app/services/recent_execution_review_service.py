from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Callable

from sqlalchemy.orm import Session

from app.analysis.executed_workout_structure_analyzer import (
    ExecutedWorkoutStructureAnalyzer,
)
from app.db.database import SessionLocal
from app.db.models import WorkoutDB
from app.engine.existing_plan_importer import (
    ExistingPlanImporter,
)
from app.engine.workout_execution_review_engine import (
    WorkoutExecutionReviewEngine,
)
from app.integrations.google_sheets_plan_source import (
    GoogleSheetsPlanSource,
)
from app.models.executed_session import (
    ExecutedSession,
)
from app.services.composite_session_builder import (
    CompositeSessionBuilder,
)
from app.services.workout_feedback_service import (
    WorkoutFeedbackService,
)


class RecentExecutionReviewService:
    """
    Builds execution reviews for the most recent logical sessions.

    Flow:
    WorkoutDB
    -> CompositeSessionBuilder
    -> plan matching
    -> athlete feedback
    -> executed workout structure
    -> WorkoutExecutionReviewEngine

    The result is designed to be consumed directly by the API
    and the recent-workouts UI.
    """

    DEFAULT_LIMIT = 3
    MIN_RAW_ACTIVITY_CANDIDATES = 36
    RAW_ACTIVITY_MULTIPLIER = 12

    def __init__(
        self,
        session_factory: Callable[[], Session] = SessionLocal,
        plan_source=None,
        plan_importer=None,
        session_builder=None,
        feedback_service=None,
        review_engine=None,
        structure_analyzer=None,
    ):
        self.session_factory = session_factory

        self.plan_source = (
            plan_source
            if plan_source is not None
            else GoogleSheetsPlanSource()
        )

        self.plan_importer = (
            plan_importer
            if plan_importer is not None
            else ExistingPlanImporter()
        )

        self.session_builder = (
            session_builder
            if session_builder is not None
            else CompositeSessionBuilder()
        )

        self.feedback_service = (
            feedback_service
            if feedback_service is not None
            else WorkoutFeedbackService(
                session_factory=session_factory
            )
        )

        self.review_engine = (
            review_engine
            if review_engine is not None
            else WorkoutExecutionReviewEngine()
        )

        self.structure_analyzer = (
            structure_analyzer
            if structure_analyzer is not None
            else ExecutedWorkoutStructureAnalyzer()
        )

    def build(
        self,
        target_date: date | datetime | str | None = None,
        limit: int = DEFAULT_LIMIT,
    ) -> list[dict]:
        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero."
            )

        resolved_date = self._normalize_date(
            target_date
        )

        workouts = self._get_recent_executed_workouts(
            target_date=resolved_date,
            limit=limit,
        )

        sessions = self.session_builder.build(
            workouts
        )

        recent_sessions = sorted(
            sessions,
            key=lambda item: item.start_time,
            reverse=True,
        )[:limit]

        if not recent_sessions:
            return []

        session_start_date = min(
            session.start_time.date()
            for session in recent_sessions
        )

        session_end_date = max(
            session.start_time.date()
            for session in recent_sessions
        )

        planned_workouts = (
            self._get_planned_workouts(
                range_start=session_start_date,
                range_end=session_end_date,
            )
        )

        return [
            self._build_review(
                session=session,
                planned_workouts=planned_workouts,
            )
            for session in recent_sessions
        ]

    def _build_review(
        self,
        session: ExecutedSession,
        planned_workouts: list,
    ) -> dict:
        planned_workout = self._match_plan(
            session=session,
            planned_workouts=planned_workouts,
        )

        feedback = self.feedback_service.get(
            session_id=session.session_id
        )

        execution_structure = (
            self._build_execution_structure(
                session
            )
        )

        review = self.review_engine.review(
            session=session,
            planned_workout=planned_workout,
            feedback=feedback,
            execution_structure=execution_structure,
        )

        return {
            "session_id": (
                session.session_id
            ),
            "date": (
                session.start_time
                .date()
                .isoformat()
            ),
            "start_time": (
                session.start_time.isoformat()
            ),
            "sport_family": (
                session.sport_family
            ),
            "workout_type": (
                session.workout_type
            ),
            "distance_km": (
                session.total_distance_km
            ),
            "duration_min": (
                session.total_duration_min
            ),
            "activities_count": (
                session.activities_count
            ),
            "source_files": (
                session.source_files
            ),
            "planned_workout": (
                self._serialize_plan(
                    planned_workout
                )
            ),
            "execution_structure": (
                execution_structure
            ),
            "review": {
                "status": review.status,
                "confidence": (
                    review.confidence
                ),
                "planned_workout_type": (
                    review
                    .planned_workout_type
                ),
                "executed_workout_type": (
                    review
                    .executed_workout_type
                ),
                "planned_distance_km": (
                    review
                    .planned_distance_km
                ),
                "executed_distance_km": (
                    review
                    .executed_distance_km
                ),
                "planned_duration_min": (
                    review
                    .planned_duration_min
                ),
                "executed_duration_min": (
                    review
                    .executed_duration_min
                ),
                "athlete_feedback": (
                    review.athlete_feedback
                ),
                "evidence": (
                    review.evidence
                ),
                "warnings": (
                    review.warnings
                ),
            },
        }

    def _build_execution_structure(
        self,
        session: ExecutedSession,
    ) -> dict | None:
        if (
            session.sport_family
            != "running"
        ):
            return None

        source_files = (
            session.source_files
            or []
        )

        if not source_files:
            return None

        structures = []

        for workout_file in source_files:
            structure = (
                self.structure_analyzer
                .analyze(
                    workout_file
                )
            )

            structures.append(
                structure
            )

        if len(structures) == 1:
            return structures[0]

        return (
            self._merge_execution_structures(
                structures
            )
        )

    def _merge_execution_structures(
        self,
        structures: list[dict],
    ) -> dict:
        segments = []

        warnings = []

        laps_count = 0

        fast_finishes = []

        detected_types = []

        confidences = []

        for structure in structures:
            segments.extend(
                structure.get(
                    "segments",
                    []
                )
            )

            summary = (
                structure.get(
                    "summary"
                )
                or {}
            )

            laps_count += (
                summary.get(
                    "laps_count",
                    0
                )
                or 0
            )

            warnings.extend(
                summary.get(
                    "warnings",
                    []
                )
                or []
            )

            detected_type = (
                summary.get(
                    "detected_type"
                )
            )

            if detected_type:
                detected_types.append(
                    detected_type
                )

            confidence = (
                summary.get(
                    "confidence"
                )
            )

            if confidence is not None:
                confidences.append(
                    confidence
                )

            fast_finish = (
                summary.get(
                    "fast_finish"
                )
                or {}
            )

            if fast_finish.get(
                "detected"
            ):
                fast_finishes.append(
                    fast_finish
                )

        best_fast_finish = (
            fast_finishes[-1]
            if fast_finishes
            else {
                "detected": False
            }
        )

        detected_type = (
            detected_types[-1]
            if detected_types
            else "unknown"
        )

        confidence = (
            max(confidences)
            if confidences
            else 0.2
        )

        return {
            "workout_file": None,
            "source_files": [
                structure.get(
                    "workout_file"
                )
                for structure in structures
                if structure.get(
                    "workout_file"
                )
            ],
            "segments": segments,
            "summary": {
                "laps_count": (
                    laps_count
                ),
                "detected_type": (
                    detected_type
                ),
                "confidence": (
                    confidence
                ),
                "classification_method": (
                    "merged_lap_pattern"
                ),
                "fast_finish": (
                    best_fast_finish
                ),
                "warnings": (
                    list(
                        dict.fromkeys(
                            warnings
                        )
                    )
                ),
            },
        }

    def _match_plan(
        self,
        session: ExecutedSession,
        planned_workouts: list,
    ):
        candidates = [
            workout
            for workout in planned_workouts
            if (
                workout.planned_date
                == session.start_time.date()
            )
        ]

        if not candidates:
            return None

        if len(candidates) == 1:
            return candidates[0]

        return max(
            candidates,
            key=lambda workout: self._plan_match_score(
                session=session,
                planned_workout=workout,
            ),
        )

    def _plan_match_score(
        self,
        session: ExecutedSession,
        planned_workout,
    ) -> int:
        planned_type = (
            planned_workout.workout_type
        )

        executed_type = (
            session.workout_type
        )

        if planned_type == executed_type:
            return 100

        compatible_pairs = {
            ("easy_run", "easy_run+strides"),
            ("tempo_run", "threshold"),
            ("threshold", "tempo_run"),
            ("long_run", "easy_run"),
            ("long_run", "easy_run+strides"),
            ("long_run+progression", "easy_run"),
            ("long_run+progression", "tempo_run"),
        }

        if (
            planned_type,
            executed_type,
        ) in compatible_pairs:
            return 80

        text = (
            f"{planned_workout.title} "
            f"{planned_workout.description}"
        ).lower()

        if (
            executed_type
            in {
                "bike",
                "cycling",
                "elliptical",
                "cross_training",
                "cross_train",
            }
            and any(
                marker in text
                for marker in {
                    "cross train",
                    "cross-training",
                    "cross training",
                    "bike",
                    "cycling",
                    "rower",
                    "elliptical",
                }
            )
        ):
            return 75

        return 0

    def _get_planned_workouts(
        self,
        range_start: date,
        range_end: date,
    ) -> list:
        rows = (
            self.plan_source.fetch_rows()
        )

        workouts = (
            self.plan_importer.import_rows(
                rows
            )
        )

        return [
            workout
            for workout in workouts
            if (
                range_start
                <= workout.planned_date
                <= range_end
            )
        ]

    def _get_recent_executed_workouts(
        self,
        target_date: date,
        limit: int,
    ) -> list[WorkoutDB]:
        end_datetime = datetime.combine(
            target_date
            + timedelta(days=1),
            datetime.min.time(),
        )

        candidate_limit = max(
            self.MIN_RAW_ACTIVITY_CANDIDATES,
            limit
            * self.RAW_ACTIVITY_MULTIPLIER,
        )

        db = self.session_factory()

        try:
            workouts = (
                db.query(WorkoutDB)
                .filter(
                    WorkoutDB.start_time
                    < end_datetime
                )
                .order_by(
                    WorkoutDB.start_time.desc()
                )
                .limit(
                    candidate_limit
                )
                .all()
            )

            return list(
                reversed(
                    workouts
                )
            )

        finally:
            db.close()

    def _serialize_plan(
        self,
        planned_workout,
    ) -> dict | None:
        if planned_workout is None:
            return None

        return {
            "date": (
                planned_workout
                .planned_date
                .isoformat()
            ),
            "title": (
                planned_workout.title
            ),
            "workout_type": (
                planned_workout.workout_type
            ),
            "planned_distance_km": (
                planned_workout
                .planned_distance_km
            ),
            "planned_duration_min": (
                planned_workout
                .planned_duration_min
            ),
            "priority": (
                planned_workout.priority
            ),
        }

    def _normalize_date(
        self,
        value: date | datetime | str | None,
    ) -> date:
        if value is None:
            return date.today()

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

        return date.fromisoformat(
            value
        )