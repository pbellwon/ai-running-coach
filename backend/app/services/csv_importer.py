import csv
from pathlib import Path
from datetime import datetime
from app.models.workout import Workout


class CSVWorkoutImporter:
    def __init__(self, file_path: str):
        self.file_path = Path(__file__).resolve().parent.parent.parent / file_path

    def load_workouts(self):
        workouts = []

        with open(self.file_path, mode="r") as file:
            reader = csv.DictReader(file)

            for row in reader:
                workouts.append(
                    Workout(
                        date=datetime.strptime(row["date"], "%Y-%m-%d").date(),
                        sport=row["sport"],
                        title=row["title"],
                        duration_seconds=int(row["duration_seconds"]),
                        distance_meters=float(row["distance_meters"]),
                        avg_hr=int(row["avg_hr"]),
                        max_hr=int(row["max_hr"]),
                        avg_pace=float(row["avg_pace"]),
                    )
                )

        return workouts