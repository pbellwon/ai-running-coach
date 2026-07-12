import re


class WorkoutStructureParser:

    def parse(self, description: str) -> list[dict]:

        text = description.strip().lower()

        structure = []

        structure.extend(self._find_long_run(text))
        structure.extend(self._find_easy_distance(text))
        structure.extend(self._find_threshold_blocks(text))
        structure.extend(self._find_fast_blocks(text))
        structure.extend(self._find_strides(text))
        structure.extend(self._find_hills(text))
        structure.extend(self._find_progression(text))

        return structure

    def _find_long_run(self, text: str) -> list[dict]:

        blocks = []

        pattern = r"(?:long run|long|długi|dlugi|wybieganie)\s*(\d+(?:\.\d+)?)\s*km"

        matches = re.findall(pattern, text)

        for distance_km in matches:
            distance_km = float(distance_km)

            blocks.append(
                {
                    "segment": "main",
                    "description": f"Long run {distance_km:g} km",
                    "distance_km": distance_km,
                    "intensity": "easy_to_moderate",
                }
            )

        return blocks

    def _find_easy_distance(self, text: str) -> list[dict]:

        blocks = []

        pattern = r"(?:easy|easy run|spokojny|luźny|luzny|luźno|luzno)\s*(\d+(?:\.\d+)?)\s*km"

        matches = re.findall(pattern, text)

        for distance_km in matches:
            distance_km = float(distance_km)

            blocks.append(
                {
                    "segment": "main",
                    "description": f"Easy {distance_km:g} km",
                    "distance_km": distance_km,
                    "intensity": "easy",
                }
            )

        return blocks

    def _find_threshold_blocks(self, text: str) -> list[dict]:

        blocks = []

        pattern_km = r"(\d+)\s*x\s*(\d+(?:\.\d+)?)\s*km"

        matches = re.findall(pattern_km, text)

        for repetitions, distance_km in matches:
            distance_km = float(distance_km)

            if distance_km >= 1:
                blocks.append(
                    {
                        "segment": "main",
                        "description": f"{repetitions} x {distance_km:g} km threshold",
                        "repetitions": int(repetitions),
                        "distance_km": distance_km,
                        "intensity": "threshold",
                    }
                )

        return blocks

    def _find_fast_blocks(self, text: str) -> list[dict]:

        blocks = []

        pattern_m = r"(\d+)\s*x\s*(\d+)\s*m?"

        matches = re.findall(pattern_m, text)

        for repetitions, distance_m in matches:
            distance_m = int(distance_m)

            if 50 <= distance_m < 1000:
                blocks.append(
                    {
                        "segment": "secondary",
                        "description": f"{repetitions} x {distance_m} m fast",
                        "repetitions": int(repetitions),
                        "distance_m": distance_m,
                        "intensity": "strides" if "strides" in text or "rytmy" in text or "przebieżki" in text or "przebiezki" in text else "vo2max",
                    }
                )

        return blocks

    def _find_strides(self, text: str) -> list[dict]:

        blocks = []

        pattern = r"(\d+)\s*x\s*(\d+)\s*s\s*(?:strides|rytmy|przebieżki|przebiezki)?"

        matches = re.findall(pattern, text)

        for repetitions, duration_sec in matches:
            duration_sec = int(duration_sec)

            if duration_sec <= 40:
                blocks.append(
                    {
                        "segment": "secondary",
                        "description": f"{repetitions} x {duration_sec} s strides",
                        "repetitions": int(repetitions),
                        "duration_sec": duration_sec,
                        "intensity": "strides",
                    }
                )

        return blocks

    def _find_hills(self, text: str) -> list[dict]:

        blocks = []

        pattern = r"(\d+)\s*x\s*(\d+)\s*s\s*(?:hills|hill|podbiegi|górki|gorki)"

        matches = re.findall(pattern, text)

        for repetitions, duration_sec in matches:
            duration_sec = int(duration_sec)

            blocks.append(
                {
                    "segment": "secondary",
                    "description": f"{repetitions} x {duration_sec} s hills",
                    "repetitions": int(repetitions),
                    "duration_sec": duration_sec,
                    "intensity": "hills",
                }
            )

        return blocks

    def _find_progression(self, text: str) -> list[dict]:

        keywords = [
            "progression",
            "fast finish",
            "szybka końcówka",
            "szybka koncowka",
            "narastająco",
            "narastajaco",
        ]

        if any(keyword in text for keyword in keywords):
            return [
                {
                    "segment": "finish",
                    "description": "Fast finish / progression",
                    "intensity": "progression",
                }
            ]

        return []