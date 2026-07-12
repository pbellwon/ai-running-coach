from statistics import mean

from app.db.database import SessionLocal
from app.db.models import LapDB


class ExecutedWorkoutStructureAnalyzer:

    def analyze(self, workout_file: str) -> dict:

        db = SessionLocal()

        laps = (
            db.query(LapDB)
            .filter(LapDB.workout_file == workout_file)
            .order_by(LapDB.lap_number.asc())
            .all()
        )

        db.close()

        if not laps:
            return {
                "workout_file": workout_file,
                "segments": [],
                "summary": {
                    "laps_count": 0,
                    "detected_type": "unknown",
                },
            }

        easy_laps = []
        fast_laps = []
        recovery_laps = []

        for lap in laps:
            distance_m = lap.distance_m or 0
            duration_sec = lap.elapsed_time_sec or 0

            if distance_m <= 0 or duration_sec <= 0:
                continue

            pace_sec_per_km = duration_sec / (distance_m / 1000)

            if 70 <= distance_m <= 150 and 10 <= duration_sec <= 35:
                fast_laps.append(lap)

            elif 70 <= distance_m <= 200 and pace_sec_per_km >= 420:
                recovery_laps.append(lap)

            elif distance_m >= 1000 and pace_sec_per_km >= 270:
                easy_laps.append(lap)

        segments = []

        if easy_laps:
            segments.append(
                {
                    "segment": "easy_block",
                    "laps": len(easy_laps),
                    "distance_km": round(sum((lap.distance_m or 0) for lap in easy_laps) / 1000, 2),
                    "duration_min": round(sum((lap.elapsed_time_sec or 0) for lap in easy_laps) / 60, 1),
                    "avg_hr": round(mean([lap.avg_hr for lap in easy_laps if lap.avg_hr]), 1)
                    if any(lap.avg_hr for lap in easy_laps)
                    else None,
                }
            )

        if fast_laps:
            segments.append(
                {
                    "segment": "strides",
                    "repetitions": len(fast_laps),
                    "avg_distance_m": round(mean([lap.distance_m for lap in fast_laps if lap.distance_m]), 1),
                    "avg_duration_sec": round(mean([lap.elapsed_time_sec for lap in fast_laps if lap.elapsed_time_sec]), 1),
                    "avg_pace_sec_per_km": round(
                        mean([
                            lap.elapsed_time_sec / (lap.distance_m / 1000)
                            for lap in fast_laps
                            if lap.distance_m and lap.elapsed_time_sec
                        ]),
                        1,
                    ),
                    "intensity": "strides",
                }
            )

        if recovery_laps:
            segments.append(
                {
                    "segment": "recoveries",
                    "repetitions": len(recovery_laps),
                    "avg_distance_m": round(mean([lap.distance_m for lap in recovery_laps if lap.distance_m]), 1),
                    "avg_duration_sec": round(mean([lap.elapsed_time_sec for lap in recovery_laps if lap.elapsed_time_sec]), 1),
                }
            )

        detected_type = "unknown"

        if easy_laps and fast_laps:
            detected_type = "easy_run+strides"
        elif easy_laps:
            detected_type = "easy_run"
        elif fast_laps:
            detected_type = "fast_reps"

        return {
            "workout_file": workout_file,
            "segments": segments,
            "summary": {
                "laps_count": len(laps),
                "detected_type": detected_type,
            },
        }