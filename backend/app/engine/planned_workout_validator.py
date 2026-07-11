from app.models.planned_workout import PlannedWorkout


class PlannedWorkoutValidator:

    def validate(self, workout: PlannedWorkout) -> dict:

        warnings = []

        if workout.workout_type == "unknown":
            warnings.append("Workout intent could not be classified.")

        if workout.planned_distance_km is None and workout.planned_duration_min is None:
            warnings.append("Planned workout should have distance or duration.")

        if workout.workout_type in {"long_run", "long_run+progression"}:
            if workout.planned_distance_km is None:
                warnings.append("Long run should have planned distance.")

        if workout.workout_type in {"threshold", "threshold+vo2max", "vo2max"}:
            if not workout.structure:
                warnings.append("Quality workout should have planned structure.")

        if workout.workout_type == "easy_run" and workout.priority == "key":
            warnings.append("Easy run should usually not be marked as key workout.")

        return {
            "valid": len(warnings) == 0,
            "warnings": warnings,
        }