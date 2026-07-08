from app.models.workout_intent import WorkoutIntent


class WorkoutIntentEngine:

    def classify(self, workout_type: str) -> WorkoutIntent:

        if workout_type == "easy_run":
            return WorkoutIntent(
                workout_type="easy_run",
                primary_capability="aerobic_endurance",
                secondary_capability="recovery",
                expected_intensity="low",
                expected_load="low_to_moderate",
                success_metrics=[
                    "heart_rate",
                    "pace_stability",
                    "cardiac_drift",
                ],
                description="Easy run focused on aerobic development and recovery.",
            )

        if workout_type == "long_run":
            return WorkoutIntent(
                workout_type="long_run",
                primary_capability="aerobic_endurance",
                secondary_capability="durability",
                expected_intensity="low_to_moderate",
                expected_load="moderate_to_high",
                success_metrics=[
                    "duration",
                    "heart_rate",
                    "cardiac_drift",
                    "fueling",
                ],
                description="Long run focused on aerobic endurance and fatigue resistance.",
            )

        if workout_type == "threshold":
            return WorkoutIntent(
                workout_type="threshold",
                primary_capability="threshold",
                secondary_capability="running_economy",
                expected_intensity="moderate_to_high",
                expected_load="high",
                success_metrics=[
                    "pace",
                    "heart_rate",
                    "pace_stability",
                    "cardiac_drift",
                ],
                description="Threshold session focused on improving sustainable race effort.",
            )

        if workout_type == "vo2max":
            return WorkoutIntent(
                workout_type="vo2max",
                primary_capability="vo2max",
                secondary_capability="speed_endurance",
                expected_intensity="high",
                expected_load="high",
                success_metrics=[
                    "interval_pace",
                    "heart_rate_response",
                    "recovery_between_reps",
                ],
                description="High-intensity interval session focused on VO2max development.",
            )

        if workout_type == "strength":
            return WorkoutIntent(
                workout_type="strength",
                primary_capability="strength",
                secondary_capability="injury_resilience",
                expected_intensity="moderate",
                expected_load="moderate",
                success_metrics=[
                    "completion",
                    "soreness",
                    "recovery",
                ],
                description="Strength session focused on durability and injury prevention.",
            )

        return WorkoutIntent(
            workout_type="unknown",
            primary_capability="unknown",
            secondary_capability=None,
            expected_intensity="unknown",
            expected_load="unknown",
            success_metrics=[],
            description="Unknown workout type.",
        )
    
    def supported_types(self) -> list[str]:

        return [
            "easy_run",
            "long_run",
            "threshold",
            "vo2max",
            "strength",
        ]