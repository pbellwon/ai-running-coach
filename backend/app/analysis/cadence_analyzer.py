from app.analysis.workout_context import WorkoutContext
from app.analysis.data_normalizer import DataNormalizer


class CadenceAnalyzer:

    def analyze(self, workout_file: str):

        context = WorkoutContext(workout_file)

        cadences = []

        for record in context.moving_records:
            if not DataNormalizer.is_running_record(record.speed, record.cadence):
                continue

            cadence = DataNormalizer.normalize_running_cadence(record.cadence)

            if cadence:
                cadences.append(cadence)

        if len(cadences) < 30:
            return {
                "workout_file": workout_file,
                "error": "Not enough cadence data",
                "records": len(cadences),
            }

        avg = self._avg(cadences)
        std = self._std(cadences, avg)

        return {
            "workout_file": workout_file,
            "records": len(cadences),
            "avg_cadence": round(avg, 1),
            "min_cadence": round(min(cadences), 1),
            "max_cadence": round(max(cadences), 1),
            "cadence_std": round(std, 1),
            "cadence_stability": self._classify(std),
        }

    def _avg(self, values):
        return sum(values) / len(values)

    def _std(self, values, avg):
        variance = sum((v - avg) ** 2 for v in values) / len(values)
        return variance ** 0.5

    def _classify(self, std):

        if std < 2:
            return "excellent"

        if std < 4:
            return "good"

        if std < 7:
            return "variable"

        return "unstable"