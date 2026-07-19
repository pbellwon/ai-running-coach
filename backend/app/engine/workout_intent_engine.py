from app.models.workout_intent import WorkoutIntent


class WorkoutIntentEngine:

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
            "off",
            "mobility",
            "race",
            "unknown",
        ]

    def classify(self, workout_type: str) -> WorkoutIntent:

        workout_type = self._normalize_workout_type(workout_type)

        if workout_type == "easy_run":
            return WorkoutIntent(
                workout_type="easy_run",
                primary_capability="aerobic_endurance",
                secondary_capabilities=[
                    "recovery",
                    "running_economy",
                    "neuromuscular",
                ],
                modifiers=[],
                components=[
                    {
                        "type": "easy_run",
                        "priority": "primary",
                    }
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

        if workout_type == "easy_run+strides":
            return WorkoutIntent(
                workout_type="easy_run+strides",
                primary_capability="aerobic_endurance",
                secondary_capabilities=[
                    "recovery",
                    "running_economy",
                    "neuromuscular",
                ],
                modifiers=["strides"],
                components=[
                    {
                        "type": "easy_run",
                        "priority": "primary",
                    },
                    {
                        "type": "strides",
                        "priority": "secondary",
                    },
                ],
                expected_intensity="low_with_neuromuscular",
                expected_load="low_to_moderate",
                success_metrics=[
                    "heart_rate",
                    "pace_stability",
                    "stride_quality",
                    "cadence",
                ],
                description="Easy run with strides focused on aerobic development and neuromuscular quality.",
            )

        if workout_type == "easy_run+hills":
            return WorkoutIntent(
                workout_type="easy_run+hills",
                primary_capability="aerobic_endurance",
                secondary_capabilities=[
                    "neuromuscular",
                    "strength_endurance",
                    "running_economy",
                ],
                modifiers=["hills"],
                components=[
                    {
                        "type": "easy_run",
                        "priority": "primary",
                    },
                    {
                        "type": "hill_sprints",
                        "priority": "secondary",
                    },
                ],
                expected_intensity="low_with_neuromuscular",
                expected_load="moderate",
                success_metrics=[
                    "heart_rate",
                    "hill_power",
                    "stride_quality",
                    "recovery",
                ],
                description="Easy run with hill sprints focused on aerobic work and neuromuscular power.",
            )

        if workout_type == "long_run":
            return WorkoutIntent(
                workout_type="long_run",
                primary_capability="aerobic_endurance",
                secondary_capabilities=[
                    "durability",
                    "fatigue_resistance",
                ],
                modifiers=[],
                components=[
                    {
                        "type": "long_run",
                        "priority": "primary",
                    }
                ],
                expected_intensity="low",
                expected_load="moderate_to_high",
                success_metrics=[
                    "duration",
                    "heart_rate",
                    "cardiac_drift",
                    "pace_stability",
                ],
                description="Long run focused on aerobic endurance and durability.",
            )

        if workout_type == "long_run+progression":
            return WorkoutIntent(
                workout_type="long_run+progression",
                primary_capability="aerobic_endurance",
                secondary_capabilities=[
                    "durability",
                    "fatigue_resistance",
                    "threshold",
                ],
                modifiers=["progression"],
                components=[
                    {
                        "type": "long_run",
                        "priority": "primary",
                    },
                    {
                        "type": "progression",
                        "priority": "secondary",
                    },
                ],
                expected_intensity="low_to_moderate",
                expected_load="high",
                success_metrics=[
                    "duration",
                    "heart_rate",
                    "cardiac_drift",
                    "progression_control",
                ],
                description="Long run with progression focused on aerobic endurance and fatigue resistance.",
            )

        if workout_type == "tempo_run":
            return WorkoutIntent(
                workout_type="tempo_run",
                primary_capability="aerobic_power",
                secondary_capabilities=[
                    "threshold",
                    "running_economy",
                ],
                modifiers=[],
                components=[
                    {
                        "type": "tempo_run",
                        "priority": "primary",
                    }
                ],
                expected_intensity="moderate",
                expected_load="moderate_to_high",
                success_metrics=[
                    "pace",
                    "heart_rate",
                    "pace_stability",
                    "cardiac_drift",
                ],
                description="Tempo run focused on controlled moderate intensity below threshold.",
            )

        if workout_type == "threshold":
            return WorkoutIntent(
                workout_type="threshold",
                primary_capability="threshold",
                secondary_capabilities=[
                    "running_economy",
                ],
                modifiers=[],
                components=[
                    {
                        "type": "threshold",
                        "priority": "primary",
                    }
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

        if workout_type == "threshold+vo2max":
            return WorkoutIntent(
                workout_type="threshold+vo2max",
                primary_capability="threshold",
                secondary_capabilities=[
                    "vo2max",
                    "running_economy",
                    "neuromuscular",
                ],
                modifiers=["mixed_quality"],
                components=[
                    {
                        "type": "threshold",
                        "priority": "primary",
                    },
                    {
                        "type": "vo2max",
                        "priority": "secondary",
                    },
                ],
                expected_intensity="high",
                expected_load="high",
                success_metrics=[
                    "threshold_pace",
                    "interval_pace",
                    "heart_rate",
                    "recovery",
                    "pace_stability",
                ],
                description="Mixed threshold and VO2max session.",
            )

        if workout_type == "vo2max":
            return WorkoutIntent(
                workout_type="vo2max",
                primary_capability="vo2max",
                secondary_capabilities=[
                    "running_economy",
                    "anaerobic_capacity",
                ],
                modifiers=[],
                components=[
                    {
                        "type": "vo2max",
                        "priority": "primary",
                    }
                ],
                expected_intensity="high",
                expected_load="high",
                success_metrics=[
                    "interval_pace",
                    "heart_rate",
                    "recovery",
                    "repeatability",
                ],
                description="VO2max interval session focused on high aerobic power.",
            )

        if workout_type == "strength":
            return WorkoutIntent(
                workout_type="strength",
                primary_capability="strength",
                secondary_capabilities=[
                    "injury_resilience",
                    "running_economy",
                ],
                modifiers=[],
                components=[
                    {
                        "type": "strength",
                        "priority": "primary",
                    }
                ],
                expected_intensity="variable",
                expected_load="moderate",
                success_metrics=[
                    "completion",
                    "soreness",
                    "next_day_readiness",
                ],
                description="Strength session focused on durability and injury resilience.",
            )

        if workout_type == "off":
            return WorkoutIntent(
                workout_type="off",
                primary_capability="recovery",
                secondary_capabilities=[],
                modifiers=[],
                components=[
                    {
                        "type": "rest",
                        "priority": "primary",
                    }
                ],
                expected_intensity="none",
                expected_load="none",
                success_metrics=[
                    "recovery",
                    "readiness",
                ],
                description="Rest day.",
            )

        if workout_type == "mobility":
            return WorkoutIntent(
                workout_type="mobility",
                primary_capability="mobility",
                secondary_capabilities=[
                    "recovery",
                    "injury_resilience",
                ],
                modifiers=[],
                components=[
                    {
                        "type": "mobility",
                        "priority": "primary",
                    }
                ],
                expected_intensity="low",
                expected_load="low",
                success_metrics=[
                    "completion",
                    "range_of_motion",
                    "soreness",
                ],
                description="Mobility session focused on recovery and movement quality.",
            )

        if workout_type == "race":
            return WorkoutIntent(
                workout_type="race",
                primary_capability="race_performance",
                secondary_capabilities=[
                    "threshold",
                    "vo2max",
                    "durability",
                ],
                modifiers=["race"],
                components=[
                    {
                        "type": "race",
                        "priority": "primary",
                    }
                ],
                expected_intensity="maximal",
                expected_load="high",
                success_metrics=[
                    "finish_time",
                    "pace_execution",
                    "heart_rate",
                    "race_fade",
                ],
                description="Race effort.",
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

    def classify_from_description(self, description: str) -> WorkoutIntent:

        text = description.lower().strip()

        if self._contains_any(
            text,
            [
                "off",
                "rest",
                "odpoczynek",
                "wolne",
            ],
        ):
            return self.classify("off")

        if self._contains_any(
            text,
            [
                "strength",
                "siła",
                "sila",
                "trening siłowy",
                "trening silowy",
                "lekka siła",
                "lekka sila",
                "siłownia",
                "silownia",
            ],
        ):
            return self.classify("strength")

        if self._contains_any(
            text,
            [
                "mobility",
                "hip mobility",
                "mobilność",
                "mobilnosc",
                "rozciąganie",
                "rozciaganie",
            ],
        ):
            return self.classify("mobility")

        if self._contains_any(
            text,
            [
                "race",
                "bieg ",
                "10k",
                "5k",
                "parkrun",
                "półmaraton",
                "polmaraton",
                "maraton",
                "warszawa",
                "praska",
            ],
        ):
            if self._contains_any(text, ["easy", " e ", "recovery"]):
                pass
            else:
                return self.classify("race")

        has_easy = self._contains_any(
            text,
            [
                "easy",
                " e",
                " e ",
                "spokojny",
                "luźno",
                "luzno",
                "regeneracyjny",
                "recovery",
                "ultra easy",
            ],
        )

        has_long = self._contains_any(
            text,
            [
                "long",
                "długi",
                "dlugi",
                "wybieganie",
                "bieg długi",
                "bieg dlugi",
            ],
        )

        has_strides = self._contains_any(
            text,
            [
                "strides",
                "stride",
                "rytmy",
                "rytmów",
                "rytmow",
                "przebieżki",
                "przebiezki",
                " st",
                "6st",
                "4st",
                "100m r",
                "150m r",
            ],
        )

        has_hills = self._contains_any(
            text,
            [
                "hill",
                "hills",
                "podbiegi",
                "podbieg",
                "górki",
                "gorki",
                " h ",
            ],
        )

        has_progression = self._contains_any(
            text,
            [
                "progression",
                "bnp",
                "fast finish",
                "ostatnie",
                "narastająco",
                "narastajaco",
                "steady",
            ],
        )

        has_threshold = self._contains_any(
            text,
            [
                "threshold",
                "prog",
                "progu",
                "próg",
                "progowy",
                "treshold",
                " t ",
                " t/",
                " t)",
                "tempo 4:00",
                "tempo 4:02",
                "@3:56",
                "@3:55",
                "@3:54",
                "@3:52",
                "@4:00",
                "@4:02",
                "3x3",
                "4x2",
                "2x3",
                "3×3",
                "4×2",
                "2×3",
            ],
        )

        has_tempo = self._contains_any(
            text,
            [
                "tempo",
                "steady",
                "ii zakres",
                "ciągłego progu",
                "ciaglego progu",
                "ciągły próg",
                "ciagly prog",
            ],
        )

        has_vo2max = self._contains_any(
            text,
            [
                "vo2",
                "vo2max",
                "interwał",
                "interwal",
                "interwały",
                "interwaly",
                " i ",
                " i/",
                " i)",
                "1200m",
                "1000m",
                "1 km i",
                "800m",
                "400m",
                "3:42",
                "3:40",
                "3:38",
            ],
        )

        if has_threshold and has_vo2max:
            return self.classify("threshold+vo2max")

        if has_threshold:
            return self.classify("threshold")

        if has_tempo:
            return self.classify("tempo_run")

        if has_vo2max:
            return self.classify("vo2max")

        if has_long and has_progression:
            return self.classify("long_run+progression")

        if has_long:
            return self.classify("long_run")

        if has_easy and has_hills:
            return self.classify("easy_run+hills")

        if has_easy and has_strides:
            return self.classify("easy_run+strides")

        if has_easy:
            return self.classify("easy_run")

        return self.classify("unknown")

    def _normalize_workout_type(self, workout_type: str) -> str:

        if workout_type is None:
            return "unknown"

        workout_type = workout_type.strip().lower()
        workout_type = workout_type.replace(" ", "_")
        workout_type = workout_type.replace("%2b", "+")
        workout_type = workout_type.replace("_strides", "+strides")
        workout_type = workout_type.replace("_hills", "+hills")
        workout_type = workout_type.replace("_progression", "+progression")

        return workout_type

    def _contains_any(self, text: str, patterns: list[str]) -> bool:

        return any(pattern in text for pattern in patterns)