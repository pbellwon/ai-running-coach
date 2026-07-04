from app.db.database import SessionLocal
from app.db.models import RecordDB


class TrainingLoadEngine:
    """
    MVP training load based on heart-rate zones from record-level FIT data.
    Later we will replace this with a more advanced TRIMP-style model.
    """

    def __init__(self):

        self.hr_max = 187

        self.hr_zones = {
            "z1": (0, round(self.hr_max * 0.70)),
            "z2": (round(self.hr_max * 0.70) + 1, round(self.hr_max * 0.80)),
            "z3": (round(self.hr_max * 0.80) + 1, round(self.hr_max * 0.87)),
            "z4": (round(self.hr_max * 0.87) + 1, round(self.hr_max * 0.94)),
            "z5": (round(self.hr_max * 0.94) + 1, self.hr_max + 20),
        }

        self.zone_weights = {
            "z1": 1,
            "z2": 2,
            "z3": 3,
            "z4": 5,
            "z5": 8,
        }

    def analyze_workout(self, workout_file: str):
        db = SessionLocal()

        records = (
            db.query(RecordDB)
            .filter(RecordDB.workout_file == workout_file)
            .filter(RecordDB.heart_rate.isnot(None))
            .all()
        )

        db.close()

        if not records:
            return {
                "workout_file": workout_file,
                "records": 0,
                "training_load": 0,
                "zones": {},
            }

        zone_seconds = {
            "z1": 0,
            "z2": 0,
            "z3": 0,
            "z4": 0,
            "z5": 0,
        }

        for record in records:
            zone = self._get_hr_zone(record.heart_rate)
            zone_seconds[zone] += 1

        training_load = 0

        for zone, seconds in zone_seconds.items():
            minutes = seconds / 60
            training_load += minutes * self.zone_weights[zone]

        total_seconds = sum(zone_seconds.values())

        zones = {
            zone: {
                "seconds": seconds,
                "minutes": round(seconds / 60, 1),
                "percentage": round((seconds / total_seconds) * 100, 1)
                if total_seconds > 0
                else 0,
            }
            for zone, seconds in zone_seconds.items()
        }

        return {
            "workout_file": workout_file,
            "records": len(records),
            "duration_minutes": round(total_seconds / 60, 1),
            "training_load": round(training_load, 1),
            "zones": zones,
        }

    def _get_hr_zone(self, heart_rate: float) -> str:
        for zone, (low, high) in self.hr_zones.items():
            if low <= heart_rate <= high:
                return zone

        return "z1"