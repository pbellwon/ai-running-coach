import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import requests


API_URL = (
    "https://pacemind-backend-1034229547127."
    "europe-central2.run.app"
    "/admin/historical-backfill"
)

DB_PATH = Path("pace_mind.db")
CUTOFF = "2025-02-08"
BATCH_SIZE = 25


def row_to_dict(cursor, row):
    return {
        description[0]: value
        for description, value in zip(
            cursor.description,
            row,
        )
    }


def load_historical_workouts():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM workouts
        WHERE start_time < ?
        ORDER BY start_time
        """,
        (CUTOFF,),
    )

    workout_rows = cur.fetchall()

    workouts = []

    for workout_row in workout_rows:
        workout = dict(workout_row)

        laps_cur = conn.cursor()
        laps_cur.execute(
            """
            SELECT
                lap_number,
                distance_m,
                elapsed_time_sec,
                avg_hr,
                max_hr
            FROM laps
            WHERE workout_file = ?
            ORDER BY lap_number
            """,
            (workout["source_file"],),
        )

        laps = [
            dict(row)
            for row in laps_cur.fetchall()
        ]

        workouts.append(
            {
                "source_file": workout["source_file"],
                "start_time": workout["start_time"],
                "sport": workout["sport"],
                "distance_km": workout["distance_km"],
                "duration_sec": workout["duration_sec"],
                "avg_hr": workout["avg_hr"],
                "max_hr": workout["max_hr"],
                "avg_pace_sec_per_km": (
                    workout["avg_pace_sec_per_km"]
                ),
                "records_count": workout["records_count"],
                "laps_count": workout["laps_count"],
                "activity_name": workout["activity_name"],
                "description": workout["description"],
                "external_type": workout["external_type"],
                "source_platform": workout["source_platform"],
                "training_load": workout["training_load"],
                "rpe": workout["rpe"],
                "race": (
                    bool(workout["race"])
                    if workout["race"] is not None
                    else None
                ),
                "interval_summary": workout["interval_summary"],
                "declared_workout_type": (
                    workout["declared_workout_type"]
                ),
                "declared_session_role": (
                    workout["declared_session_role"]
                ),
                "laps": laps,
            }
        )

    conn.close()

    return workouts


def chunks(items, size):
    for index in range(
        0,
        len(items),
        size,
    ):
        yield items[
            index:index + size
        ]


def main():
    sync_key = os.getenv("SYNC_API_KEY")

    if not sync_key:
        raise RuntimeError(
            "SYNC_API_KEY is not set."
        )

    workouts = load_historical_workouts()

    total_laps = sum(
        len(workout["laps"])
        for workout in workouts
    )

    print(
        f"Historical workouts: {len(workouts)}"
    )
    print(
        f"Historical laps: {total_laps}"
    )
    print(
        f"Cutoff: {CUTOFF}"
    )

    created_workouts = 0
    created_laps = 0
    skipped_existing = 0
    rejected = 0

    batches = list(
        chunks(
            workouts,
            BATCH_SIZE,
        )
    )

    for batch_number, batch in enumerate(
        batches,
        start=1,
    ):
        print(
            f"Sending batch "
            f"{batch_number}/{len(batches)} "
            f"({len(batch)} workouts)"
        )

        response = requests.post(
            API_URL,
            headers={
                "X-Sync-Key": sync_key,
                "Content-Type": "application/json",
            },
            json={
                "workouts": batch
            },
            timeout=120,
        )

        if response.status_code != 200:
            print(
                "FAILED:"
            )
            print(
                response.status_code
            )
            print(
                response.text
            )
            raise RuntimeError(
                "Backfill failed."
            )

        result = response.json()

        created_workouts += (
            result["created_workouts"]
        )
        created_laps += (
            result["created_laps"]
        )
        skipped_existing += (
            result["skipped_existing"]
        )
        rejected += (
            result["rejected"]
        )

        print(
            json.dumps(
                result,
                indent=2,
            )
        )

    print("\n=== DONE ===")
    print(
        f"Created workouts: "
        f"{created_workouts}"
    )
    print(
        f"Created laps: "
        f"{created_laps}"
    )
    print(
        f"Skipped existing: "
        f"{skipped_existing}"
    )
    print(
        f"Rejected: "
        f"{rejected}"
    )


if __name__ == "__main__":
    main()