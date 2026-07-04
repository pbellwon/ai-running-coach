from app.analysis.workout_context import WorkoutContext


class EfficiencyAnalyzer:

    def analyze(self, workout_file: str):
        context = WorkoutContext(workout_file)

        if not context.moving_records:
            return {
                "workout_file": workout_file,
                "records": len(context.records),
                "moving_records": 0,
                "error": "No moving records found",
            }

        return {
            "workout_file": workout_file,
            "records": len(context.records),
            "moving_records": len(context.moving_records),
            "moving_percentage": round(context.moving_percentage, 1),

            "avg_hr": round(context.avg_hr or 0, 1),
            "avg_speed_mps": round(context.avg_speed or 0, 2),
            "avg_pace_min_per_km": round(context.avg_pace_min_per_km or 0, 2),

            "avg_cadence_raw": round(context.avg_cadence_raw or 0, 1),
            "avg_cadence_normalized": round(context.avg_cadence_normalized or 0, 1),

            "avg_altitude": round(context.avg_altitude or 0, 1),
        }