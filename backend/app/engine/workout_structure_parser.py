import re


class WorkoutStructureParser:

    def parse(self, description: str) -> list[dict]:

        if not description:
            return []

        text = description.lower().strip()

        segments = []

        segments.extend(self._find_easy_km_blocks(text))
        segments.extend(self._find_long_run(text))
        segments.extend(self._find_continuous_threshold(text))
        segments.extend(self._find_threshold_blocks(text))
        segments.extend(self._find_tempo_time_blocks(text))
        segments.extend(self._find_fast_blocks(text))
        segments.extend(self._find_strides(text))
        segments.extend(self._find_hills(text))
        segments.extend(self._find_progression(text))
        segments.extend(self._find_strength(text))
        segments.extend(self._find_mobility(text))
        segments.extend(self._find_off(text))
        segments.extend(self._find_race(text))

        segments = self._deduplicate_segments(segments)

        return self._sort_segments(segments)

    def _find_easy_km_blocks(self, text: str) -> list[dict]:

        segments = []

        patterns = [
            r"(\d+(?:[\.,]\d+)?)\s*km\s*easy\b",
            r"(\d+(?:[\.,]\d+)?)\s*km\s*e\b",
            r"\beasy\s*(\d+(?:[\.,]\d+)?)\s*km",
            r"\be\s*(\d+(?:[\.,]\d+)?)\s*km",
        ]

        matches = []

        for pattern in patterns:
            for match in re.finditer(pattern, text):
                distance_km = self._to_float(match.group(1))
                matches.append((match.start(), distance_km))

        matches = sorted(matches, key=lambda item: item[0])

        for index, (_, distance_km) in enumerate(matches):
            segment_name = "main"

            if len(matches) > 1:
                if index == 0:
                    segment_name = "warmup"
                elif index == len(matches) - 1:
                    segment_name = "cooldown"
                else:
                    segment_name = "easy"

            segments.append(
                {
                    "segment": segment_name,
                    "description": f"{distance_km:g} km easy",
                    "distance_km": distance_km,
                    "intensity": "easy",
                }
            )

        return segments

    def _find_long_run(self, text: str) -> list[dict]:

        patterns = [
            r"long\s*run\s*(\d+(?:[\.,]\d+)?)\s*km",
            r"long\s*(\d+(?:[\.,]\d+)?)\s*km",
            r"(\d+(?:[\.,]\d+)?)\s*km\s*long",
            r"(\d+(?:[\.,]\d+)?)\s*km\s*e.*long",
            r"(\d+(?:[\.,]\d+)?)\s*km\s*spokojny\s*tlen",
            r"(\d+(?:[\.,]\d+)?)\s*km\s*e\.",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                distance_km = self._to_float(match.group(1))

                return [
                    {
                        "segment": "main",
                        "description": f"Long run {distance_km:g} km",
                        "distance_km": distance_km,
                        "intensity": "easy",
                    }
                ]

        return []

    def _find_continuous_threshold(self, text: str) -> list[dict]:

        segments = []

        patterns = [
            r"(\d+(?:[\.,]\d+)?)\s*km\s*threshold",
            r"(\d+(?:[\.,]\d+)?)\s*km\s*tempo",
            r"(\d+(?:[\.,]\d+)?)\s*km\s*progu",
            r"(\d+(?:[\.,]\d+)?)\s*km\s*prog",
            r"(\d+(?:[\.,]\d+)?)\s*km\s*ciągłego\s*progu",
            r"(\d+(?:[\.,]\d+)?)\s*km\s*ciaglego\s*progu",
            r"(\d+(?:[\.,]\d+)?)\s*km\s*@\s*\d",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text):
                distance_km = self._to_float(match.group(1))

                segments.append(
                    {
                        "segment": "main",
                        "description": f"{distance_km:g} km threshold",
                        "distance_km": distance_km,
                        "intensity": "threshold",
                    }
                )

        return segments

    def _find_threshold_blocks(self, text: str) -> list[dict]:

        segments = []

        patterns = [
            r"(\d+)\s*x\s*(\d+(?:[\.,]\d+)?)\s*km\s*(?:threshold|tempo|t|prog|progu)?",
            r"(\d+)\s*×\s*(\d+(?:[\.,]\d+)?)\s*km\s*(?:threshold|tempo|t|prog|progu)?",
            r"(\d+)\s*x\s*(\d+(?:[\.,]\d+)?)\s*mi\s*(?:threshold|tempo|t|prog|progu)?",
            r"(\d+)\s*×\s*(\d+(?:[\.,]\d+)?)\s*mi\s*(?:threshold|tempo|t|prog|progu)?",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text):
                repetitions = int(match.group(1))
                distance = self._to_float(match.group(2))

                unit = "mi" if "mi" in match.group(0) else "km"
                distance_km = distance * 1.60934 if unit == "mi" else distance

                if distance_km < 1:
                    continue

                intensity = "threshold"

                if self._contains_any(match.group(0), ["vo2"]):
                    intensity = "vo2max"

                segments.append(
                    {
                        "segment": "main",
                        "description": f"{repetitions} x {distance:g} {unit} {intensity}",
                        "repetitions": repetitions,
                        "distance_km": round(distance_km, 3),
                        "intensity": intensity,
                    }
                )

        return segments

    def _find_tempo_time_blocks(self, text: str) -> list[dict]:

        segments = []

        patterns = [
            r"(\d+)\s*x\s*(\d+)\s*min\s*(?:t|tempo|threshold)?",
            r"(\d+)\s*×\s*(\d+)\s*min\s*(?:t|tempo|threshold)?",
            r"(\d+)\s*x\s*(\d+)'\s*(?:t|tempo|threshold)?",
            r"(\d+)\s*×\s*(\d+)'\s*(?:t|tempo|threshold)?",
            r"(\d+)\s*min\s*(?:t|tempo|threshold)",
            r"(\d+)'\s*(?:t|tempo|threshold)",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text):

                if len(match.groups()) == 2:
                    repetitions = int(match.group(1))
                    duration_min = int(match.group(2))
                else:
                    repetitions = 1
                    duration_min = int(match.group(1))

                segments.append(
                    {
                        "segment": "main",
                        "description": f"{repetitions} x {duration_min} min threshold",
                        "repetitions": repetitions,
                        "duration_min": duration_min,
                        "intensity": "threshold",
                    }
                )

        return segments

    def _find_fast_blocks(self, text: str) -> list[dict]:

        segments = []

        patterns = [
            r"(\d+)\s*x\s*(\d+)\s*m\b",
            r"(\d+)\s*×\s*(\d+)\s*m\b",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text):
                repetitions = int(match.group(1))
                distance_m = int(match.group(2))

                if distance_m < 50 or distance_m >= 1000:
                    continue

                intensity = "vo2max"

                if self._contains_any(
                    text,
                    [
                        "stride",
                        "strides",
                        "rytmy",
                        "rytmów",
                        "rytmow",
                        "przebieżki",
                        "przebiezki",
                        " st",
                    ],
                ):
                    intensity = "strides"

                segments.append(
                    {
                        "segment": "secondary",
                        "description": f"{repetitions} x {distance_m} m {intensity}",
                        "repetitions": repetitions,
                        "distance_m": distance_m,
                        "intensity": intensity,
                    }
                )

        return segments

    def _find_strides(self, text: str) -> list[dict]:

        segments = []

        patterns = [
            r"(\d+)\s*x\s*(\d+)\s*s\s*(?:strides|stride|rytmy|rytmów|rytmow)",
            r"(\d+)\s*×\s*(\d+)\s*s\s*(?:strides|stride|rytmy|rytmów|rytmow)",
            r"(\d+)\s*x\s*(\d+)\"\s*(?:strides|stride|rytmy|rytmów|rytmow)",
            r"(\d+)\s*×\s*(\d+)\"\s*(?:strides|stride|rytmy|rytmów|rytmow)",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text):
                repetitions = int(match.group(1))
                duration_sec = int(match.group(2))

                segments.append(
                    {
                        "segment": "secondary",
                        "description": f"{repetitions} x {duration_sec} sec strides",
                        "repetitions": repetitions,
                        "duration_sec": duration_sec,
                        "intensity": "strides",
                    }
                )

        return segments

    def _find_hills(self, text: str) -> list[dict]:

        segments = []

        patterns = [
            r"(\d+)\s*x\s*(\d+)\s*s\s*(?:hill|hills|podbieg|podbiegi)",
            r"(\d+)\s*×\s*(\d+)\s*s\s*(?:hill|hills|podbieg|podbiegi)",
            r"(\d+)\s*x\s*(\d+)\"\s*(?:hill|hills|podbieg|podbiegi)",
            r"(\d+)\s*×\s*(\d+)\"\s*(?:hill|hills|podbieg|podbiegi)",
            r"(\d+)\s*x\s*(\d+)\s*m\s*(?:hill|hills|podbieg|podbiegi)",
            r"(\d+)\s*×\s*(\d+)\s*m\s*(?:hill|hills|podbieg|podbiegi)",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text):
                repetitions = int(match.group(1))
                value = int(match.group(2))
                is_distance = "m" in match.group(0)

                segment = {
                    "segment": "secondary",
                    "description": f"{repetitions} x {value}{'m' if is_distance else 'sec'} hills",
                    "repetitions": repetitions,
                    "intensity": "hills",
                }

                if is_distance:
                    segment["distance_m"] = value
                else:
                    segment["duration_sec"] = value

                segments.append(segment)

        return segments

    def _find_progression(self, text: str) -> list[dict]:

        if not self._contains_any(
            text,
            [
                "progression",
                "bnp",
                "fast finish",
                "ostatnie",
                "steady",
                "->",
                "→",
            ],
        ):
            return []

        return [
            {
                "segment": "finish",
                "description": "Progression / fast finish",
                "intensity": "progression",
            }
        ]

    def _find_strength(self, text: str) -> list[dict]:

        if not self._contains_any(
            text,
            [
                "strength",
                "siła",
                "sila",
                "siłownia",
                "silownia",
                "trening siłowy",
                "trening silowy",
            ],
        ):
            return []

        duration_min = 45

        match = re.search(r"(\d+)\s*min", text)

        if match:
            duration_min = int(match.group(1))

        if "lekka" in text:
            duration_min = min(duration_min, 30)

        return [
            {
                "segment": "main",
                "description": f"Strength {duration_min} min",
                "duration_min": duration_min,
                "intensity": "strength",
            }
        ]

    def _find_mobility(self, text: str) -> list[dict]:

        if not self._contains_any(
            text,
            [
                "mobility",
                "mobilność",
                "mobilnosc",
                "hip mobility",
                "rozciąganie",
                "rozciaganie",
            ],
        ):
            return []

        duration_min = 20

        match = re.search(r"(\d+)\s*min", text)

        if match:
            duration_min = int(match.group(1))

        return [
            {
                "segment": "main",
                "description": f"Mobility {duration_min} min",
                "duration_min": duration_min,
                "intensity": "mobility",
            }
        ]

    def _find_off(self, text: str) -> list[dict]:

        if text not in {"off", "rest"}:
            return []

        return [
            {
                "segment": "main",
                "description": "Off",
                "intensity": "off",
            }
        ]

    def _find_race(self, text: str) -> list[dict]:

        race_keywords = [
            "race",
            "zawody",
            "start",
            "atak",
            "bieg niepodległości",
            "bieg niepodleglosci",
            "bieg urodzinowy",
            "nocny swietojanski",
            "nocny świętojański",
            "challenge",
            "praska",
            "warszawa",
            "city trail",
            "parkrun test",
        ]

        if not self._contains_any(text, race_keywords):
            return []

        distance_km = None

        if "10k" in text or "10 km" in text:
            distance_km = 10

        if "5k" in text or "5 km" in text:
            distance_km = 5

        if "parkrun" in text:
            distance_km = 5

        if "półmaraton" in text or "polmaraton" in text or "21k" in text:
            distance_km = 21.1

        segment = {
            "segment": "main",
            "description": "Race",
            "intensity": "race",
        }

        if distance_km:
            segment["distance_km"] = distance_km

        return [segment]

    def _deduplicate_segments(self, segments: list[dict]) -> list[dict]:

        unique_segments = []
        seen = set()

        for segment in segments:
            key = (
                segment.get("segment"),
                segment.get("distance_km"),
                segment.get("distance_m"),
                segment.get("duration_min"),
                segment.get("duration_sec"),
                segment.get("intensity"),
                segment.get("repetitions"),
            )

            if key in seen:
                continue

            seen.add(key)
            unique_segments.append(segment)

        return unique_segments

    def _sort_segments(self, segments: list[dict]) -> list[dict]:

        segment_order = {
            "warmup": 10,
            "main": 20,
            "easy": 25,
            "secondary": 30,
            "finish": 40,
            "cooldown": 50,
        }

        intensity_order = {
            "off": 0,
            "mobility": 5,
            "strength": 10,
            "easy": 20,
            "tempo": 30,
            "threshold": 40,
            "vo2max": 50,
            "hills": 60,
            "strides": 70,
            "progression": 80,
            "race": 90,
        }

        def sort_key(segment: dict):

            segment_name = segment.get("segment", "")
            intensity = segment.get("intensity", "")

            return (
                segment_order.get(segment_name, 999),
                intensity_order.get(intensity, 999),
            )

        return sorted(segments, key=sort_key)

    def _to_float(self, value: str) -> float:

        return float(value.replace(",", "."))

    def _contains_any(self, text: str, patterns: list[str]) -> bool:

        return any(pattern in text for pattern in patterns)