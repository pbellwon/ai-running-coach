from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

from app.db.database import SessionLocal
from app.db.models import WorkoutDB
from app.engine.existing_plan_importer import ExistingPlanImporter
from app.integrations.google_sheets_plan_source import (
    GoogleSheetsPlanSource,
)
from app.models.executed_session import ExecutedSession
from app.services.composite_session_builder import (
    CompositeSessionBuilder,
)
from app.services.training_distribution_analyzer import (
    TrainingDistributionAnalyzer,
)
from app.services.workout_type_matcher import (
    WorkoutTypeMatcher,
)


class WeeklyReviewService:
    """
    Builds a weekly review using logical executed sessions.

    Individual recorded activities may be grouped into one logical
    session, for example:
    - warm-up + race + cooldown
    - warm-up + intervals + cooldown

    Matching is one-to-one between planned workouts and logical
    executed sessions.

    The review contains:
    - plan execution and type compliance
    - missed and unplanned sessions
    - training on planned off days
    - planned and executed distance information
    - executed training distribution
    """

    def review(
        self,
        week_start: date | datetime | str,
    ) -> dict:
        normalized_week_start = self._normalize_date(
            week_start
        )

        if normalized_week_start.weekday() != 0:
            raise ValueError(
                "week_start must be a Monday. "
                f"Received: "
                f"{normalized_week_start.isoformat()}."
            )

        week_end = (
            normalized_week_start
            + timedelta(days=6)
        )

        planned_workouts = (
            self._get_planned_workouts(
                week_start=normalized_week_start,
                week_end=week_end,
            )
        )

        executed_workouts = (
            self._get_executed_workouts(
                week_start=normalized_week_start,
                week_end=week_end,
            )
        )

        executed_sessions = (
            CompositeSessionBuilder().build(
                executed_workouts
            )
        )

        planned_by_date: dict[
            date,
            list,
        ] = defaultdict(list)

        sessions_by_date: dict[
            date,
            list[ExecutedSession],
        ] = defaultdict(list)

        for planned_workout in planned_workouts:
            planned_by_date[
                planned_workout.planned_date
            ].append(planned_workout)

        for executed_session in executed_sessions:
            sessions_by_date[
                executed_session.start_time.date()
            ].append(executed_session)

        matcher = WorkoutTypeMatcher()

        days = []

        paired_count = 0
        type_matched_count = 0
        type_mismatch_count = 0
        missed_count = 0
        unplanned_count = 0
        off_days_count = 0
        trained_on_off_day_count = 0

        planned_distance_km = 0.0
        executed_distance_km = 0.0
        planned_distance_entries_count = 0

        # Used by TrainingDistributionAnalyzer.
        #
        # Example:
        # executed workout_type = easy_run
        # matched planned type = long_run
        #
        # Physiologically it was an easy run,
        # but its role in the week was a long run.
        planned_type_by_session_id: dict[
            str,
            str,
        ] = {}

        for day_offset in range(7):
            current_date = (
                normalized_week_start
                + timedelta(days=day_offset)
            )

            day_planned = planned_by_date.get(
                current_date,
                [],
            )

            day_sessions = sessions_by_date.get(
                current_date,
                [],
            )

            training_plans = [
                workout
                for workout in day_planned
                if workout.workout_type != "off"
            ]

            off_plans = [
                workout
                for workout in day_planned
                if workout.workout_type == "off"
            ]

            off_days_count += len(off_plans)

            if (
                off_plans
                and not training_plans
                and day_sessions
            ):
                trained_on_off_day_count += 1

            executed_types = (
                self._build_session_type_map(
                    day_sessions
                )
            )

            match_result = matcher.match_day(
                planned_workouts=training_plans,
                executed_workouts=day_sessions,
                executed_types=executed_types,
            )

            matches = match_result["matches"]

            # Preserve the role of the matched
            # planned workout for distribution analysis.
            for match in matches:
                planned_type_by_session_id[
                    match.executed_workout.session_id
                ] = match.planned_type

            unmatched_planned = match_result[
                "unmatched_planned"
            ]

            unmatched_sessions = match_result[
                "unmatched_executed"
            ]

            day_paired_count = len(matches)

            day_type_matched_count = sum(
                1
                for match in matches
                if match.type_match
            )

            day_type_mismatch_count = sum(
                1
                for match in matches
                if not match.type_match
            )

            day_missed_count = len(
                unmatched_planned
            )

            day_unplanned_count = len(
                unmatched_sessions
            )

            paired_count += day_paired_count

            type_matched_count += (
                day_type_matched_count
            )

            type_mismatch_count += (
                day_type_mismatch_count
            )

            missed_count += day_missed_count
            unplanned_count += day_unplanned_count

            planned_match_map = {
                id(match.planned_workout): match
                for match in matches
            }

            session_match_map = {
                id(match.executed_workout): match
                for match in matches
            }

            planned_entries = []

            for planned_workout in day_planned:
                if (
                    planned_workout.planned_distance_km
                    is not None
                ):
                    planned_distance_km += (
                        planned_workout
                        .planned_distance_km
                    )

                    planned_distance_entries_count += 1

                if (
                    planned_workout.workout_type
                    == "off"
                ):
                    match_status = "off"
                    matched_executed_type = None
                    matched_session_id = None
                    type_match = None
                    match_score = None

                else:
                    match = planned_match_map.get(
                        id(planned_workout)
                    )

                    if match is None:
                        match_status = "missed"
                        matched_executed_type = None
                        matched_session_id = None
                        type_match = False
                        match_score = None

                    elif match.type_match:
                        match_status = (
                            "type_matched"
                        )

                        matched_executed_type = (
                            match.executed_type
                        )

                        matched_session_id = (
                            match
                            .executed_workout
                            .session_id
                        )

                        type_match = True
                        match_score = (
                            match.match_score
                        )

                    else:
                        match_status = (
                            "type_mismatch"
                        )

                        matched_executed_type = (
                            match.executed_type
                        )

                        matched_session_id = (
                            match
                            .executed_workout
                            .session_id
                        )

                        type_match = False
                        match_score = (
                            match.match_score
                        )

                planned_entries.append(
                    {
                        "title": (
                            planned_workout.title
                        ),
                        "description": (
                            planned_workout.description
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
                        "match_status": (
                            match_status
                        ),
                        "matched_session_id": (
                            matched_session_id
                        ),
                        "matched_executed_type": (
                            matched_executed_type
                        ),
                        "type_match": (
                            type_match
                        ),
                        "match_score": (
                            match_score
                        ),
                    }
                )

            executed_session_entries = []

            for executed_session in day_sessions:
                if (
                    executed_session
                    .total_distance_km
                    is not None
                ):
                    executed_distance_km += (
                        executed_session
                        .total_distance_km
                    )

                match = session_match_map.get(
                    id(executed_session)
                )

                if match is None:
                    matched_to_plan = False
                    matched_planned_title = None
                    matched_planned_type = None
                    type_match = False
                    match_score = None

                else:
                    matched_to_plan = True

                    matched_planned_title = (
                        match.planned_workout.title
                    )

                    matched_planned_type = (
                        match.planned_type
                    )

                    type_match = (
                        match.type_match
                    )

                    match_score = (
                        match.match_score
                    )

                executed_session_entries.append(
                    self._serialize_session(
                        session=executed_session,
                        matched_to_plan=(
                            matched_to_plan
                        ),
                        matched_planned_title=(
                            matched_planned_title
                        ),
                        matched_planned_type=(
                            matched_planned_type
                        ),
                        type_match=(
                            type_match
                        ),
                        match_score=(
                            match_score
                        ),
                    )
                )

            day_status = (
                self._determine_day_status(
                    training_plans_count=len(
                        training_plans
                    ),
                    off_plans_count=len(
                        off_plans
                    ),
                    executed_sessions_count=len(
                        day_sessions
                    ),
                    paired_count=(
                        day_paired_count
                    ),
                    type_matched_count=(
                        day_type_matched_count
                    ),
                    type_mismatch_count=(
                        day_type_mismatch_count
                    ),
                    missed_count=(
                        day_missed_count
                    ),
                    unplanned_count=(
                        day_unplanned_count
                    ),
                )
            )

            days.append(
                {
                    "date": (
                        current_date.isoformat()
                    ),
                    "day": (
                        current_date.strftime(
                            "%A"
                        )
                    ),
                    "status": (
                        day_status
                    ),
                    "planned_workouts": (
                        planned_entries
                    ),
                    "executed_sessions": (
                        executed_session_entries
                    ),
                }
            )

        planned_training_count = sum(
            1
            for workout in planned_workouts
            if workout.workout_type != "off"
        )

        execution_rate = (
            paired_count
            / planned_training_count
            * 100
            if planned_training_count
            else 0.0
        )

        type_compliance_rate = (
            type_matched_count
            / planned_training_count
            * 100
            if planned_training_count
            else 0.0
        )

        paired_type_compliance_rate = (
            type_matched_count
            / paired_count
            * 100
            if paired_count
            else 0.0
        )

        planned_distance_complete = (
            planned_distance_entries_count
            == planned_training_count
        )

        distance_difference_km = (
            executed_distance_km
            - planned_distance_km
            if planned_distance_complete
            else None
        )

        # Training distribution is calculated only after
        # plan-to-session matching, because some session roles
        # such as long_run are plan-aware.
        training_distribution = (
            TrainingDistributionAnalyzer().analyze(
                sessions=executed_sessions,
                planned_type_by_session_id=(
                    planned_type_by_session_id
                ),
            )
        )

        return {
            "week_start": (
                normalized_week_start.isoformat()
            ),
            "week_end": (
                week_end.isoformat()
            ),
            "summary": {
                "planned_entries_count": len(
                    planned_workouts
                ),
                "planned_training_count": (
                    planned_training_count
                ),

                # Raw activity files stored in WorkoutDB.
                "executed_source_activities_count": (
                    len(executed_workouts)
                ),

                # Logical sessions after grouping.
                "executed_sessions_count": (
                    len(executed_sessions)
                ),

                # Temporary API compatibility field.
                "executed_workouts_count": (
                    len(executed_sessions)
                ),

                "matched_workouts_count": (
                    paired_count
                ),
                "paired_workouts_count": (
                    paired_count
                ),
                "type_matched_workouts_count": (
                    type_matched_count
                ),
                "type_mismatch_workouts_count": (
                    type_mismatch_count
                ),
                "missed_workouts_count": (
                    missed_count
                ),
                "unplanned_workouts_count": (
                    unplanned_count
                ),
                "off_days_count": (
                    off_days_count
                ),
                "trained_on_off_day_count": (
                    trained_on_off_day_count
                ),
                "planned_distance_km": round(
                    planned_distance_km,
                    2,
                ),
                "planned_distance_entries_count": (
                    planned_distance_entries_count
                ),
                "planned_distance_complete": (
                    planned_distance_complete
                ),
                "executed_distance_km": round(
                    executed_distance_km,
                    2,
                ),
                "distance_difference_km": (
                    round(
                        distance_difference_km,
                        2,
                    )
                    if distance_difference_km
                    is not None
                    else None
                ),
                "execution_rate_percent": round(
                    execution_rate,
                    1,
                ),
                "type_compliance_rate_percent": (
                    round(
                        type_compliance_rate,
                        1,
                    )
                ),
                "paired_type_compliance_rate_percent": (
                    round(
                        paired_type_compliance_rate,
                        1,
                    )
                ),
            },
            "training_distribution": (
                training_distribution
            ),
            "days": days,
        }

    def _build_session_type_map(
        self,
        sessions: list[ExecutedSession],
    ) -> dict[str, dict]:
        return {
            session.session_id: {
                "workout_type": (
                    session.workout_type
                ),
                "confidence": (
                    session.confidence
                ),
                "classification_method": (
                    session.classification_method
                ),
                "warnings": (
                    session.warnings
                ),
            }
            for session in sessions
        }

    def _serialize_session(
        self,
        session: ExecutedSession,
        matched_to_plan: bool,
        matched_planned_title: str | None,
        matched_planned_type: str | None,
        type_match: bool,
        match_score: int | None,
    ) -> dict:
        return {
            "session_id": (
                session.session_id
            ),
            "start_time": (
                session.start_time.isoformat()
            ),
            "end_time": (
                session.end_time.isoformat()
            ),
            "sport_family": (
                session.sport_family
            ),
            "workout_type": (
                session.workout_type
            ),
            "classification_confidence": (
                session.confidence
            ),
            "classification_method": (
                session.classification_method
            ),
            "classification_warnings": (
                session.warnings
            ),
            "activities_count": (
                session.activities_count
            ),
            "source_files": (
                session.source_files
            ),
            "total_distance_km": (
                session.total_distance_km
            ),
            "total_duration_min": (
                session.total_duration_min
            ),
            "matched_to_plan": (
                matched_to_plan
            ),
            "matched_planned_title": (
                matched_planned_title
            ),
            "matched_planned_type": (
                matched_planned_type
            ),
            "type_match": (
                type_match
            ),
            "match_score": (
                match_score
            ),
            "components": [
                {
                    "workout_file": (
                        component.workout_file
                    ),
                    "role": (
                        component.role
                    ),
                    "start_time": (
                        component
                        .start_time
                        .isoformat()
                    ),
                    "end_time": (
                        component
                        .end_time
                        .isoformat()
                    ),
                    "sport": (
                        component.sport
                    ),
                    "distance_km": (
                        component.distance_km
                    ),
                    "duration_min": (
                        component.duration_min
                    ),
                    "workout_type": (
                        component.workout_type
                    ),
                    "confidence": (
                        component.confidence
                    ),
                    "classification_method": (
                        component
                        .classification_method
                    ),
                    "warnings": (
                        component.warnings
                    ),
                }
                for component
                in session.components
            ],
        }

    def _get_planned_workouts(
        self,
        week_start: date,
        week_end: date,
    ) -> list:
        rows = (
            GoogleSheetsPlanSource()
            .fetch_rows()
        )

        workouts = (
            ExistingPlanImporter()
            .import_rows(rows)
        )

        return [
            workout
            for workout in workouts
            if (
                week_start
                <= workout.planned_date
                <= week_end
            )
        ]

    def _get_executed_workouts(
        self,
        week_start: date,
        week_end: date,
    ) -> list[WorkoutDB]:
        range_start = datetime.combine(
            week_start,
            datetime.min.time(),
        )

        range_end = datetime.combine(
            week_end + timedelta(days=1),
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

    def _determine_day_status(
        self,
        training_plans_count: int,
        off_plans_count: int,
        executed_sessions_count: int,
        paired_count: int,
        type_matched_count: int,
        type_mismatch_count: int,
        missed_count: int,
        unplanned_count: int,
    ) -> str:
        if (
            training_plans_count == 0
            and off_plans_count == 0
            and executed_sessions_count == 0
        ):
            return "empty"

        if (
            off_plans_count > 0
            and training_plans_count == 0
            and executed_sessions_count == 0
        ):
            return "off_completed"

        if (
            off_plans_count > 0
            and training_plans_count == 0
            and executed_sessions_count > 0
        ):
            return "trained_on_off_day"

        if (
            training_plans_count == 0
            and executed_sessions_count > 0
        ):
            return "unplanned_execution"

        if (
            missed_count > 0
            and paired_count == 0
        ):
            return "missed"

        if missed_count > 0:
            return "partially_executed"

        if type_mismatch_count > 0:
            return "executed_type_mismatch"

        if unplanned_count > 0:
            return (
                "executed_with_extra_workout"
            )

        if (
            paired_count > 0
            and type_matched_count
            == paired_count
        ):
            return "executed_as_planned"

        return "executed"

    def _normalize_date(
        self,
        value: date | datetime | str,
    ) -> date:
        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        if isinstance(value, str):
            normalized_value = value.strip()

            if not normalized_value:
                raise ValueError(
                    "week_start cannot be empty."
                )

            try:
                return date.fromisoformat(
                    normalized_value
                )

            except ValueError as exc:
                raise ValueError(
                    "week_start must use "
                    "YYYY-MM-DD format."
                ) from exc

        raise TypeError(
            "week_start must be a date, "
            "datetime or ISO string."
        )