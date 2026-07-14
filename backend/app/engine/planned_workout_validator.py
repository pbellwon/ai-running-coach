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

        structure_distance_km = self._structure_distance_km(workout.structure)

        if workout.planned_distance_km is not None and structure_distance_km > 0:
            if structure_distance_km > workout.planned_distance_km:
                warnings.append("Structured distance exceeds planned workout distance.")

            if structure_distance_km < workout.planned_distance_km * 0.5:
                warnings.append("Structured distance is much lower than planned workout distance.")

        if workout.priority == "key" and not self._has_main_segment(workout.structure):
            warnings.append("Key workout should have a main segment.")

        return {
            "valid": len(warnings) == 0,
            "warnings": warnings,
            "structure_distance_km": round(structure_distance_km, 2),
        }

    def _structure_distance_km(self, structure: list[dict]) -> float:

        total = 0.0

        for segment in structure:
            if "distance_km" in segment and segment["distance_km"] is not None:
                repetitions = segment.get("repetitions", 1)
                total += float(segment["distance_km"]) * repetitions

            if "distance_m" in segment and segment["distance_m"] is not None:
                repetitions = segment.get("repetitions", 1)
                total += float(segment["distance_m"]) * repetitions / 1000

        return total

    def _has_main_segment(self, structure: list[dict]) -> bool:

        return any(
            segment.get("segment") == "main"
            for segment in structure
        )