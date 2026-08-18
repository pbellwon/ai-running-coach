from __future__ import annotations

import sqlite3


DATABASE_PATH = "pace_mind.db"

COLUMNS = {
    "activity_name": "TEXT",
    "description": "TEXT",
    "external_type": "TEXT",
    "source_platform": "TEXT",
    "training_load": "REAL",
    "rpe": "REAL",
    "race": "BOOLEAN",
    "interval_summary": "TEXT",
    "declared_workout_type": "TEXT",
    "declared_session_role": "TEXT",
}


def main() -> None:
    connection = sqlite3.connect(DATABASE_PATH)

    try:
        existing_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(workouts)"
            ).fetchall()
        }

        added_columns: list[str] = []

        for column_name, column_type in COLUMNS.items():
            if column_name in existing_columns:
                continue

            connection.execute(
                f"ALTER TABLE workouts "
                f"ADD COLUMN {column_name} {column_type}"
            )

            added_columns.append(column_name)

        connection.commit()

        print(
            "Added columns:",
            added_columns or "none",
        )

    finally:
        connection.close()


if __name__ == "__main__":
    main()