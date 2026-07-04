from app.analysis.workout_context import WorkoutContext


class CardiacDriftAnalyzer:

    def analyze(self, workout_file: str):
        context = WorkoutContext(workout_file)

        records = context.moving_records

        if len(records) < 120:
            return {
                "workout_file": workout_file,
                "error": "Not enough moving records to calculate cardiac drift",
                "moving_records": len(records),
            }

        midpoint = len(records) // 2

        first_half = records[:midpoint]
        second_half = records[midpoint:]

        first = self._segment_metrics(first_half)
        second = self._segment_metrics(second_half)

        if not first["efficiency"] or not second["efficiency"]:
            return {
                "workout_file": workout_file,
                "error": "Could not calculate efficiency",
            }

        drift = (
            (second["efficiency"] - first["efficiency"])
            / first["efficiency"]
            * 100
        )

        elevation_difference = (
            second["avg_altitude"] - first["avg_altitude"]
        )

        reliable = abs(elevation_difference) < 10

        reason = None

        if not reliable:
            reason = "Large elevation difference between halves"

        return {
            "workout_file": workout_file,
            "moving_records": len(records),

            "first_half": first,
            "second_half": second,

            "cardiac_drift_percent": round(drift, 2),

            "elevation_difference": round(elevation_difference, 1),

            "reliable": reliable,
            "reason": reason,
        }

    def _segment_metrics(self, records):

        avg_hr = self._avg([r.heart_rate for r in records])
        avg_speed = self._avg([r.speed for r in records])
        avg_altitude = self._avg([r.altitude for r in records])

        efficiency = None

        if avg_hr and avg_speed:
            efficiency = avg_speed / avg_hr

        return {
            "records": len(records),
            "avg_hr": round(avg_hr or 0, 1),
            "avg_speed_mps": round(avg_speed or 0, 2),
            "avg_altitude": round(avg_altitude or 0, 1),
            "efficiency": round(efficiency, 5) if efficiency else None,
        }

    def _avg(self, values):
        clean = [v for v in values if v is not None]

        if not clean:
            return None

        return sum(clean) / len(clean)