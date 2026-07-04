from app.db.database import SessionLocal
from app.db.models import RecordDB
from app.analysis.data_normalizer import DataNormalizer


class WorkoutContext:
    def __init__(self, workout_file: str):
        self.workout_file = workout_file
        self.records = self._load_records()
        self.moving_records = self._moving_records()

    def _load_records(self):
        db = SessionLocal()

        records = (
            db.query(RecordDB)
            .filter(RecordDB.workout_file == self.workout_file)
            .all()
        )

        db.close()

        return records

    def _moving_records(self):
        return [
            record
            for record in self.records
            if DataNormalizer.is_moving_record(
                speed=record.speed,
                cadence=record.cadence,
            )
        ]

    def avg(self, values):
        clean = [v for v in values if v is not None]

        if not clean:
            return None

        return sum(clean) / len(clean)

    @property
    def avg_hr(self):
        return self.avg([r.heart_rate for r in self.moving_records])

    @property
    def avg_speed(self):
        return self.avg([r.speed for r in self.moving_records])

    @property
    def avg_pace_min_per_km(self):
        return DataNormalizer.pace_min_per_km(self.avg_speed)

    @property
    def avg_cadence_raw(self):
        return self.avg([r.cadence for r in self.moving_records])

    @property
    def avg_cadence_normalized(self):
        return DataNormalizer.normalize_running_cadence(
            self.avg_cadence_raw
        )

    @property
    def avg_altitude(self):
        return self.avg([r.altitude for r in self.moving_records])

    @property
    def moving_percentage(self):
        if not self.records:
            return 0

        return len(self.moving_records) / len(self.records) * 100