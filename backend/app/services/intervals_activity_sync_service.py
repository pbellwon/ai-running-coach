from __future__ import annotations

from datetime import date, datetime

from app.db.database import SessionLocal
from app.db.models import (
    LapDB,
    WorkoutDB,
)
from app.integrations.intervals_activity_mapper import (
    IntervalsActivityMapper,
)
from app.integrations.intervals_icu_client import (
    IntervalsIcuClient,
)
from app.integrations.intervals_lap_mapper import (
    IntervalsLapMapper,
)


class IntervalsActivitySyncService:
    """
    Synchronizes Intervals.icu activities into WorkoutDB
    and detected activity intervals into LapDB.

    Existing activities are identified by:

        source_file = intervals_icu:<activity_id>

    Lap rows use the same source_file value in:

        LapDB.workout_file

    Sync is idempotent:
    - WorkoutDB rows are updated;
    - LapDB rows for the activity are replaced.
    """

    def __init__(
        self,
        client: IntervalsIcuClient | None = None,
        mapper: IntervalsActivityMapper | None = None,
        lap_mapper: IntervalsLapMapper | None = None,
        session_factory=SessionLocal,
    ):
        self.client = (
            client
            or IntervalsIcuClient()
        )

        self.mapper = (
            mapper
            or IntervalsActivityMapper()
        )

        self.lap_mapper = (
            lap_mapper
            or IntervalsLapMapper()
        )

        self.session_factory = (
            session_factory
        )

    def sync(
        self,
        oldest: date | datetime | str,
        newest: date | datetime | str,
    ) -> dict:
        activities = (
            self.client.get_activities(
                oldest=oldest,
                newest=newest,
            )
        )

        db = self.session_factory()

        created = 0
        updated = 0
        skipped = 0

        laps_created = 0
        laps_replaced = 0

        errors: list[dict] = []

        try:
            for activity in activities:
                try:
                    activity_id = (
                        activity.get("id")
                    )

                    if not activity_id:
                        skipped += 1

                        errors.append(
                            {
                                "activity_id": None,
                                "error": (
                                    "Missing activity id"
                                ),
                            }
                        )

                        continue

                    mapped = (
                        self.mapper.map(
                            activity
                        )
                    )

                    existing = (
                        db.query(WorkoutDB)
                        .filter(
                            WorkoutDB.source_file
                            == mapped.source_file
                        )
                        .first()
                    )

                    if existing is None:
                        db.add(
                            mapped
                        )

                        created += 1

                    else:
                        self._update_existing(
                            existing=existing,
                            incoming=mapped,
                        )

                        updated += 1

                    lap_result = (
                        self._sync_laps(
                            db=db,
                            activity_id=str(
                                activity_id
                            ),
                            workout_file=(
                                mapped.source_file
                            ),
                        )
                    )

                    laps_created += (
                        lap_result[
                            "created"
                        ]
                    )

                    laps_replaced += (
                        lap_result[
                            "replaced"
                        ]
                    )

                except Exception as exc:
                    skipped += 1

                    errors.append(
                        {
                            "activity_id": (
                                activity.get(
                                    "id"
                                )
                            ),
                            "error": str(
                                exc
                            ),
                        }
                    )

            db.commit()

        except Exception:
            db.rollback()
            raise

        finally:
            db.close()

        return {
            "source": "intervals_icu",
            "oldest": str(oldest),
            "newest": str(newest),
            "fetched": len(
                activities
            ),
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "laps_created": (
                laps_created
            ),
            "laps_replaced": (
                laps_replaced
            ),
            "errors": errors,
        }

    def _sync_laps(
        self,
        *,
        db,
        activity_id: str,
        workout_file: str,
    ) -> dict:
        activity = (
            self.client
            .get_activity_with_intervals(
                activity_id
            )
        )

        intervals = (
            activity.get(
                "icu_intervals"
            )
            or []
        )

        laps = (
            self.lap_mapper.map(
                workout_file=(
                    workout_file
                ),
                intervals=intervals,
            )
        )

        existing_count = (
            db.query(LapDB)
            .filter(
                LapDB.workout_file
                == workout_file
            )
            .count()
        )

        if existing_count:
            (
                db.query(LapDB)
                .filter(
                    LapDB.workout_file
                    == workout_file
                )
                .delete(
                    synchronize_session=False
                )
            )

        for lap in laps:
            db.add(
                lap
            )

        return {
            "created": len(
                laps
            ),
            "replaced": (
                existing_count
            ),
        }

    def _update_existing(
        self,
        existing: WorkoutDB,
        incoming: WorkoutDB,
    ) -> None:
        existing.start_time = (
            incoming.start_time
        )

        existing.sport = (
            incoming.sport
        )

        existing.distance_km = (
            incoming.distance_km
        )

        existing.duration_sec = (
            incoming.duration_sec
        )

        existing.avg_hr = (
            incoming.avg_hr
        )

        existing.max_hr = (
            incoming.max_hr
        )

        existing.avg_pace_sec_per_km = (
            incoming.avg_pace_sec_per_km
        )

        existing.records_count = (
            incoming.records_count
        )

        existing.laps_count = (
            incoming.laps_count
        )

        existing.activity_name = (
            incoming.activity_name
        )

        existing.description = (
            incoming.description
        )

        existing.external_type = (
            incoming.external_type
        )

        existing.source_platform = (
            incoming.source_platform
        )

        existing.training_load = (
            incoming.training_load
        )

        existing.rpe = (
            incoming.rpe
        )

        existing.race = (
            incoming.race
        )

        existing.interval_summary = (
            incoming.interval_summary
        )

        existing.declared_workout_type = (
            incoming.declared_workout_type
        )

        existing.declared_session_role = (
            incoming.declared_session_role
        )