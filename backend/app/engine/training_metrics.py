from app.models.workout import Workout


class TrainingMetricsEngine:

    def analyze(self, workout: Workout):
        intensity_score = self._calculate_intensity(workout)

        return {
            "workout_title": workout.title,
            "distance_km": workout.distance_km(),
            "duration_min": workout.duration_minutes(),
            "avg_hr": workout.avg_hr,
            "intensity_score": intensity_score,
            "load_category": self._categorize(intensity_score)
        }

    def _calculate_intensity(self, workout: Workout):
        # bardzo prosta heurystyka v1
        pace_factor = workout.avg_pace / 300  # 5:00/km jako baseline
        hr_factor = workout.avg_hr / 150

        return round((pace_factor + hr_factor) / 2, 2)

    def _categorize(self, score: float):
        if score < 0.9:
            return "easy"
        elif score < 1.2:
            return "moderate"
        else:
            return "hard"