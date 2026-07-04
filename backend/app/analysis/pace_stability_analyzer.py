from app.analysis.workout_context import WorkoutContext
from app.analysis.data_normalizer import DataNormalizer


class PaceStabilityAnalyzer:

    def analyze(self, workout_file: str):
        context = WorkoutContext(workout_file)
        records = context.moving_records

        paces = [
            DataNormalizer.pace_min_per_km(r.speed)
            for r in records
            if r.speed and r.speed > 0
        ]

        if len(paces) < 60:
            return {
                "workout_file": workout_file,
                "error": "Not enough pace data",
                "records": len(records),
            }

        avg_pace = self._avg(paces)
        pace_std = self._std(paces, avg_pace)

        stability_index = pace_std / avg_pace if avg_pace else None

        return {
            "workout_file": workout_file,
            "records": len(records),
            "avg_pace_min_per_km": round(avg_pace, 2),
            "pace_std": round(pace_std, 2),
            "pace_variability_percent": round(stability_index * 100, 1),
            "stability": self._classify(stability_index),
        }

    def _avg(self, values):
        return sum(values) / len(values)

    def _std(self, values, avg):
        variance = sum((v - avg) ** 2 for v in values) / len(values)
        return variance ** 0.5

    def _classify(self, stability_index):
        if stability_index is None:
            return "unknown"

        if stability_index < 0.05:
            return "very_stable"

        if stability_index < 0.10:
            return "stable"

        if stability_index < 0.18:
            return "variable"

        return "highly_variable"