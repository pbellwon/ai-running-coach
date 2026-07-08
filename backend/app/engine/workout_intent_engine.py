from app.models.workout_intent import WorkoutIntent


class WorkoutIntentEngine:

    def classify(self, workout_type: str) -> WorkoutIntent:

        workout_type = workout_type.strip().lower()
        workout_type = workout_type.replace(" ", "_")

        if workout_type == "threshold+vo2max":
            return WorkoutIntent(
                workout_type="threshold+vo2max",
                primary_capability="threshold",
                secondary_capabilities=[
                    "vo2max",
                    "running_economy",
                ],
                modifiers=[],
                components=[
                    {"type": "threshold", "priority": "primary"},
                    {"type": "vo2max", "priority": "secondary"},
                ],
                expected_intensity="high",
                expected_load="high",
                success_metrics=[
                    "threshold_pace",
                    "interval_pace",
                    "heart_rate_response",
                    "recovery_between_reps",
                    "pace_stability",
                ],
                description="Combined threshold and VO2max session with sustained work plus faster repetitions.",
            )

        if workout_type == "easy_run+hills":
            return WorkoutIntent(
                workout_type="easy_run+hills",
                primary_capability="aerobic_endurance",
                secondary_capabilities=[
                    "strength",
                    "running_economy",
                    "neuromuscular",
                ],
                modifiers=[
                    "hills",
                ],
                components=[
                    {"type": "easy_run", "priority": "primary"},
                    {"type": "hills", "priority": "secondary"},
                ],
                expected_intensity="low_to_moderate",
                expected_load="moderate",
                success_metrics=[
                    "heart_rate",
                    "pace_stability",
                    "hill_effort_control",
                    "recovery",
                ],
                description="Easy aerobic run with hill work adding strength and running economy stimulus.",
            )

        if workout_type == "long_run+progression":
            return WorkoutIntent(
                workout_type="long_run+progression",
                primary_capability="aerobic_endurance",
                secondary_capabilities=[
                    "durability",
                    "aerobic_strength",
                    "threshold",
                ],
                modifiers=[
                    "progression",
                ],
                components=[
                    {"type": "long_run", "priority": "primary"},
                    {"type": "progression", "priority": "secondary"},
                ],
                expected_intensity="moderate_to_high",
                expected_load="high",
                success_metrics=[
                    "duration",
                    "heart_rate",
                    "pace_progression",
                    "cardiac_drift",
                    "fatigue_resistance",
                ],
                description="Long run with faster progression finish to develop endurance and fatigue resistance.",
            )

        modifiers = []

        if "+strides" in workout_type:
            workout_type = workout_type.replace("+strides", "")
            modifiers.append("strides")

        if workout_type == "easy_run":
            return WorkoutIntent(
                workout_type="easy_run",
                primary_capability="aerobic_endurance",
                secondary_capabilities=[
                    "recovery",
                    "running_economy",
                    "neuromuscular",
                ],
                modifiers=modifiers,
                components=[
                    {"type": "easy_run", "priority": "primary"},
                ],
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
                secondary_capabilities=[
                    "durability",
                ],
                modifiers=modifiers,
                components=[
                    {"type": "long_run", "priority": "primary"},
                ],
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

        if workout_type == "tempo_run":
            return WorkoutIntent(
                workout_type="tempo_run",
                primary_capability="aerobic_strength",
                secondary_capabilities=[
                    "running_economy",
                    "aerobic_endurance",
                ],
                modifiers=modifiers,
                components=[
                    {"type": "tempo_run", "priority": "primary"},
                ],
                expected_intensity="moderate",
                expected_load="moderate",
                success_metrics=[
                    "pace",
                    "heart_rate",
                    "pace_stability",
                ],
                description="Controlled moderate-effort run between easy and threshold intensity.",
            )

        if workout_type == "threshold":
            return WorkoutIntent(
                workout_type="threshold",
                primary_capability="threshold",
                secondary_capabilities=[
                    "running_economy",
                ],
                modifiers=modifiers,
                components=[
                    {"type": "threshold", "priority": "primary"},
                ],
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
                secondary_capabilities=[
                    "speed_endurance",
                ],
                modifiers=modifiers,
                components=[
                    {"type": "vo2max", "priority": "primary"},
                ],
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
                secondary_capabilities=[
                    "injury_resilience",
                ],
                modifiers=modifiers,
                components=[
                    {"type": "strength", "priority": "primary"},
                ],
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
            secondary_capabilities=[],
            modifiers=[],
            components=[],
            expected_intensity="unknown",
            expected_load="unknown",
            success_metrics=[],
            description="Unknown workout type.",
        )

    def supported_types(self) -> list[str]:

        return [
            "easy_run",
            "easy_run+strides",
            "easy_run+hills",
            "long_run",
            "long_run+progression",
            "tempo_run",
            "threshold",
            "threshold+vo2max",
            "vo2max",
            "strength",
        ]