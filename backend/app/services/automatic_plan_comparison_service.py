from __future__ import annotations

from app.db.database import SessionLocal
from app.db.models import WorkoutDB
from app.engine.existing_plan_importer import ExistingPlanImporter
from app.engine.plan_vs_execution_engine import PlanVsExecutionEngine
from app.integrations.google_sheets_plan_source import GoogleSheetsPlanSource
from app.services.plan_matcher import PlanMatcher


class AutomaticPlanComparisonService:
    """
    Automatically matches an executed workout with the planned workout
    scheduled for the same calendar date and compares execution with plan.
    """

    def compare(self, workout_file: str) -> dict:
        executed_workout = self._get_executed_workout(workout_file)

        if executed_workout is None:
            return {
                "workout_file": workout_file,
                "status": "executed_workout_not_found",
                "matched": False,
                "executed_date": None,
                "planned_workout": None,
                "comparison": None,
            }

        if executed_workout.start_time is None:
            return {
                "workout_file": workout_file,
                "status": "executed_workout_date_missing",
                "matched": False,
                "executed_date": None,
                "planned_workout": None,
                "comparison": None,
            }

        executed_date = executed_workout.start_time.date()

        plan_source = GoogleSheetsPlanSource()
        importer = ExistingPlanImporter()
        matcher = PlanMatcher()

        rows = plan_source.fetch_rows()
        planned_workouts = importer.import_rows(rows)

        planned_workout = matcher.match_by_date(
            executed_date=executed_date,
            planned_workouts=planned_workouts,
        )

        if planned_workout is None:
            return {
                "workout_file": workout_file,
                "status": "planned_workout_not_found",
                "matched": False,
                "executed_date": executed_date.isoformat(),
                "planned_workout": None,
                "comparison": None,
            }

        comparison = PlanVsExecutionEngine().compare(
            planned=planned_workout,
            workout_file=workout_file,
        )

        return {
            "workout_file": workout_file,
            "status": "compared",
            "matched": True,
            "executed_date": executed_date.isoformat(),
            "planned_workout": planned_workout,
            "comparison": comparison,
        }

    def _get_executed_workout(
        self,
        workout_file: str,
    ) -> WorkoutDB | None:
        db = SessionLocal()

        try:
            return (
                db.query(WorkoutDB)
                .filter(WorkoutDB.source_file == workout_file)
                .first()
            )
        finally:
            db.close()