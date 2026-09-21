
from __future__ import annotations

import argparse
from math import isclose

from dotenv import load_dotenv

load_dotenv()

from app.db.database import SessionLocal
from app.db.models import LapDB
from app.integrations.intervals_icu_client import (
    IntervalsIcuClient,
)
from app.integrations.intervals_lap_mapper import (
    IntervalsLapMapper,
)


ACTIVITY_ID = "i187362334"
WORKOUT_FILE = f"intervals_icu:{ACTIVITY_ID}"
EXPECTED_LAPS = 23


def backfill(*, apply: bool) -> None:
    activity = (
        IntervalsIcuClient()
        .get_activity_with_intervals(ACTIVITY_ID)
    )

    intervals = activity.get("icu_intervals") or []

    source_laps = IntervalsLapMapper().map(
        workout_file=WORKOUT_FILE,
        intervals=intervals,
    )

    if len(source_laps) != EXPECTED_LAPS:
        raise RuntimeError(
            f"Unexpected source lap count: "
            f"{len(source_laps)}; "
            f"expected {EXPECTED_LAPS}. "
            "No changes made."
        )

    for lap in source_laps:
        moving = lap.moving_time_sec
        elapsed = lap.elapsed_time_sec

        if (
            moving is None
            or not (0 < moving <= elapsed)
        ):
            raise RuntimeError(
                f"Missing or invalid moving time "
                f"for lap {lap.lap_number}. "
                "No changes made."
            )

    db = SessionLocal()

    try:
        existing_laps = (
            db.query(LapDB)
            .filter(
                LapDB.workout_file == WORKOUT_FILE
            )
            .order_by(LapDB.lap_number.asc())
            .all()
        )

        if len(existing_laps) != EXPECTED_LAPS:
            raise RuntimeError(
                f"Unexpected database lap count: "
                f"{len(existing_laps)}; "
                f"expected {EXPECTED_LAPS}. "
                "No changes made."
            )

        for existing, source in zip(
            existing_laps,
            source_laps,
        ):
            if existing.lap_number != source.lap_number:
                raise RuntimeError(
                    f"Lap number mismatch at "
                    f"{source.lap_number}. "
                    "No changes made."
                )

            if (
                existing.distance_m is None
                or source.distance_m is None
                or not isclose(
                    existing.distance_m,
                    source.distance_m,
                    rel_tol=0,
                    abs_tol=1.0,
                )
            ):
                raise RuntimeError(
                    f"Distance mismatch at "
                    f"lap {source.lap_number}. "
                    "No changes made."
                )

            if (
                existing.elapsed_time_sec is None
                or not isclose(
                    existing.elapsed_time_sec,
                    source.elapsed_time_sec,
                    rel_tol=0,
                    abs_tol=1.0,
                )
            ):
                raise RuntimeError(
                    f"Elapsed time mismatch at "
                    f"lap {source.lap_number}. "
                    "No changes made."
                )

        print(
            "Validation OK:",
            len(existing_laps),
            "matching laps.",
        )

        print(
            "Database records will be preserved. "
            "Only moving_time_sec will be updated."
        )

        for existing, source in zip(
            existing_laps,
            source_laps,
        ):
            if source.lap_number in (4, 5):
                print(
                    f"Lap {source.lap_number}: "
                    f"elapsed={existing.elapsed_time_sec}, "
                    f"moving={source.moving_time_sec}"
                )

        if not apply:
            print(
                "DRY RUN: no database changes made."
            )
            return

        for existing, source in zip(
            existing_laps,
            source_laps,
        ):
            existing.moving_time_sec = (
                source.moving_time_sec
            )

        db.commit()

        print(
            "UPDATE COMPLETED:",
            len(existing_laps),
            "laps.",
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write validated moving times to the database.",
    )

    args = parser.parse_args()

    backfill(apply=args.apply)