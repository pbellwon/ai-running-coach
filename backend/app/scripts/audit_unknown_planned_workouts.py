from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
import re

from app.engine.existing_plan_importer import ExistingPlanImporter
from app.integrations.google_sheets_plan_source import GoogleSheetsPlanSource


AUDIT_START_DATE = date(2025, 11, 1)


def normalize_description(value: str) -> str:
    text = value.lower().strip()

    text = text.replace("’", "'")
    text = text.replace("“", '"')
    text = text.replace("”", '"')
    text = text.replace("×", "x")

    text = re.sub(r"\s+", " ", text)

    return text


def main() -> None:
    source = GoogleSheetsPlanSource()
    importer = ExistingPlanImporter()

    rows = source.fetch_rows()
    workouts = importer.import_rows(rows)

    audited_workouts = [
        workout
        for workout in workouts
        if workout.planned_date >= AUDIT_START_DATE
    ]

    unknown_workouts = [
        workout
        for workout in audited_workouts
        if workout.workout_type == "unknown"
    ]

    recognized_count = len(audited_workouts) - len(unknown_workouts)

    unknown_percent = (
        len(unknown_workouts) / len(audited_workouts) * 100
        if audited_workouts
        else 0
    )

    print()
    print("PACE MIND — PLANNED WORKOUT PARSER AUDIT")
    print("=" * 60)
    print(f"Audit start date:       {AUDIT_START_DATE.isoformat()}")
    print(f"Total workouts:         {len(audited_workouts)}")
    print(f"Recognized workouts:    {recognized_count}")
    print(f"Unknown workouts:       {len(unknown_workouts)}")
    print(f"Unknown percentage:     {unknown_percent:.2f}%")
    print()

    if not unknown_workouts:
        print("No unknown workouts found.")
        return

    grouped_workouts: dict[str, list] = defaultdict(list)

    for workout in unknown_workouts:
        normalized = normalize_description(
            workout.description or workout.title or ""
        )
        grouped_workouts[normalized].append(workout)

    pattern_counts = Counter(
        {
            description: len(group)
            for description, group in grouped_workouts.items()
        }
    )

    print("MOST COMMON UNKNOWN DESCRIPTIONS")
    print("=" * 60)

    for index, (description, count) in enumerate(
        pattern_counts.most_common(),
        start=1,
    ):
        examples = grouped_workouts[description]
        dates = ", ".join(
            workout.planned_date.isoformat()
            for workout in examples[:5]
        )

        print(f"{index}. Count: {count}")
        print(f"   Description: {description}")
        print(f"   Example dates: {dates}")

        if len(examples) > 5:
            print(f"   Additional occurrences: {len(examples) - 5}")

        print()

    print("ALL UNKNOWN WORKOUTS")
    print("=" * 60)

    for workout in unknown_workouts:
        print(
            f"{workout.planned_date.isoformat()} | "
            f"{workout.title} | "
            f"{workout.description}"
        )


if __name__ == "__main__":
    main()