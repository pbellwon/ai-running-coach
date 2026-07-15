from app.analysis.executed_workout_structure_analyzer import ExecutedWorkoutStructureAnalyzer
from app.db.database import SessionLocal
from app.db.models import WorkoutDB
from app.models.planned_workout import PlannedWorkout
from app.models.workout_execution_comparison import WorkoutExecutionComparison


class PlanVsExecutionEngine:

    def compare(
        self,
        planned: PlannedWorkout,
        workout_file: str,
    ) -> WorkoutExecutionComparison:

        executed = self._get_executed_workout(workout_file)
        executed_structure = ExecutedWorkoutStructureAnalyzer().analyze(workout_file)

        planned_type = planned.workout_type
        executed_type = executed_structure["summary"]["detected_type"]

        warnings = list(executed_structure["summary"].get("warnings", []))

        intent_match = self._intent_match(planned_type, executed_type)

        planned_distance_km = planned.planned_distance_km
        executed_distance_km = executed.distance_km if executed else None

        distance_match = self._distance_match(
            planned_distance_km=planned_distance_km,
            executed_distance_km=executed_distance_km,
        )

        structure_match = self._structure_match(
            planned_structure=planned.structure,
            executed_segments=executed_structure["segments"],
        )

        execution_quality = self._execution_quality(
            intent_match=intent_match,
            distance_match=distance_match,
            structure_match=structure_match,
            confidence=executed_structure["summary"].get("confidence", 0),
        )

        return WorkoutExecutionComparison(
            planned_workout_type=planned_type,
            executed_workout_type=executed_type,
            intent_match=intent_match,
            planned_distance_km=planned_distance_km,
            executed_distance_km=round(executed_distance_km, 2) if executed_distance_km else None,
            distance_match=distance_match,
            structure_match=structure_match,
            execution_quality=execution_quality,
            warnings=warnings,
        )

    def _get_executed_workout(self, workout_file: str):

        db = SessionLocal()

        workout = (
            db.query(WorkoutDB)
            .filter(WorkoutDB.source_file == workout_file)
            .first()
        )

        db.close()

        return workout

    def _intent_match(self, planned_type: str, executed_type: str) -> bool:

        if planned_type == executed_type:
            return True

        if planned_type == "easy_run" and executed_type == "easy_run+strides":
            return True

        if planned_type == "easy_run+strides" and executed_type == "easy_run":
            return False

        if planned_type == "tempo_run" and executed_type in {"tempo_run", "threshold"}:
            return True

        if planned_type == "threshold" and executed_type in {"threshold", "tempo_run"}:
            return True

        return False

    def _distance_match(
        self,
        planned_distance_km: float | None,
        executed_distance_km: float | None,
    ) -> str:

        if planned_distance_km is None or executed_distance_km is None:
            return "unknown"

        diff_percent = abs(executed_distance_km - planned_distance_km) / planned_distance_km * 100

        if diff_percent <= 5:
            return "ok"

        if diff_percent <= 15:
            return "minor_difference"

        return "major_difference"

    def _structure_match(
        self,
        planned_structure: list[dict],
        executed_segments: list[dict],
    ) -> str:

        if not planned_structure or not executed_segments:
            return "unknown"

        planned_intensities = {
            segment.get("intensity")
            for segment in planned_structure
            if segment.get("intensity")
        }

        executed_intensities = {
            segment.get("intensity")
            for segment in executed_segments
            if segment.get("intensity")
        }

        if planned_intensities.issubset(executed_intensities):
            return "ok"

        if planned_intensities.intersection(executed_intensities):
            return "partial"

        return "mismatch"

    def _execution_quality(
        self,
        intent_match: bool,
        distance_match: str,
        structure_match: str,
        confidence: float,
    ) -> str:

        if confidence < 0.5:
            return "uncertain"

        if intent_match and distance_match == "ok" and structure_match in {"ok", "partial", "unknown"}:
            return "good"

        if intent_match and distance_match in {"ok", "minor_difference"}:
            return "acceptable"

        return "poor"