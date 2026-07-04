from app.db.database import SessionLocal
from app.db.models import RecordDB
from app.analysis.data_normalizer import DataNormalizer


class EfficiencyAnalyzer:

    def analyze(self, workout_file: str):

        db = SessionLocal()

        records = (
            db.query(RecordDB)
            .filter(RecordDB.workout_file == workout_file)
            .all()
        )

        db.close()

        moving_records = []

        for record in records:
            if DataNormalizer.is_moving_record(
                speed=record.speed,
                cadence=record.cadence,
            ):
                moving_records.append(record)

        if not moving_records:
            return {
                "workout_file": workout_file,
                "records": len(records),
                "moving_records": 0,
                "error": "No moving records found",
            }

        avg_hr = self._avg([r.heart_rate for r in moving_records])
        avg_speed = self._avg([r.speed for r in moving_records])
        avg_cadence_raw = self._avg([r.cadence for r in moving_records])
        avg_altitude = self._avg([r.altitude for r in moving_records])

        normalized_cadence = DataNormalizer.normalize_running_cadence(
            avg_cadence_raw
        )

        return {
            "workout_file": workout_file,
            "records": len(records),
            "moving_records": len(moving_records),
            "moving_percentage": round(len(moving_records) / len(records) * 100, 1),

            "avg_hr": round(avg_hr or 0, 1),
            "avg_speed_mps": round(avg_speed or 0, 2),
            "avg_pace_min_per_km": round(
                DataNormalizer.pace_min_per_km(avg_speed), 2
            ) if avg_speed else None,

            "avg_cadence_raw": round(avg_cadence_raw or 0, 1),
            "avg_cadence_normalized": round(normalized_cadence or 0, 1),

            "avg_altitude": round(avg_altitude or 0, 1),
        }

    def _avg(self, values):
        clean_values = [v for v in values if v is not None]

        if not clean_values:
            return None

        return sum(clean_values) / len(clean_values)