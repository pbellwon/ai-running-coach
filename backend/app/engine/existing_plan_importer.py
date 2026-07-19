from datetime import date

from app.engine.planned_workout_engine import PlannedWorkoutEngine
from app.models.planned_workout import PlannedWorkout


class ExistingPlanImporter:

    REQUIRED_COLUMNS = {
        "date",
        "title",
        "description",
        "planned_distance_km",
        "planned_duration_min",
        "priority",
    }

    def __init__(self):
        self.planned_workout_engine = PlannedWorkoutEngine()

    def import_rows(self, rows: list[dict]) -> list[PlannedWorkout]:

        workouts = []

        for row in rows:
            if self._is_empty_row(row):
                continue

            self._validate_row(row)

            workout = self._row_to_planned_workout(row)
            workouts.append(workout)

        return workouts

    def _row_to_planned_workout(self, row: dict) -> PlannedWorkout:

        planned_date = self._parse_date(row.get("date"))

        title = self._clean_string(row.get("title")) or "Untitled workout"

        description = self._clean_string(row.get("description"))

        if not description:
            description = title

        planned_distance_km = self._parse_float(row.get("planned_distance_km"))

        planned_duration_min = self._parse_int(row.get("planned_duration_min"))

        priority = self._clean_string(row.get("priority")) or "normal"

        return self.planned_workout_engine.build(
            planned_date=planned_date,
            title=title,
            description=description,
            planned_distance_km=planned_distance_km,
            planned_duration_min=planned_duration_min,
            priority=priority,
        )

    def _validate_row(self, row: dict):

        missing_columns = self.REQUIRED_COLUMNS - set(row.keys())

        if missing_columns:
            raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

        if not self._clean_string(row.get("date")):
            raise ValueError("Missing required value: date")

    def _is_empty_row(self, row: dict) -> bool:

        values = [self._clean_string(value) for value in row.values()]
        return all(value == "" for value in values)

    def _parse_date(self, value) -> date:

        value = self._clean_string(value)

        if not value:
            raise ValueError("Date cannot be empty")

        return date.fromisoformat(value)

    def _parse_float(self, value) -> float | None:

        value = self._clean_string(value)

        if not value:
            return None

        value = value.replace(",", ".")

        return float(value)

    def _parse_int(self, value) -> int | None:

        value = self._clean_string(value)

        if not value:
            return None

        value = value.replace(",", ".")

        return int(float(value))

    def _clean_string(self, value) -> str:

        if value is None:
            return ""

        return str(value).strip()