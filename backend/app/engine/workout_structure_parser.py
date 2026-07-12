import re


class WorkoutStructureParser:

    def parse(self, description: str) -> list[dict]:

        text = description.strip().lower()

        structure = []

        threshold_blocks = self._find_threshold_blocks(text)
        fast_blocks = self._find_fast_blocks(text)

        for block in threshold_blocks:
            structure.append(block)

        for block in fast_blocks:
            structure.append(block)

        return structure

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
                        "intensity": "vo2max",
                    }
                )

        return blocks