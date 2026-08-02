from __future__ import annotations

from datetime import date, datetime

from app.db.database import SessionLocal
from app.db.models import WorkoutDB
from app.integrations.intervals_activity_mapper import (
    IntervalsActivityMapper,
)
from app.integrations.intervals_icu_client import (
    IntervalsIcuClient,
)


class IntervalsActivitySyncService:
    """
    Synchronizes Intervals.icu activities into WorkoutDB.

    Existing Intervals activities are identified by source_file:

        intervals_icu:<activity_id>

    Sync is idempotent:
    repeated syncs update existing records instead of inserting duplicates.
    """

    def __init__(
        self,
        client: IntervalsIcuClient | None = None,
        mapper: IntervalsActivityMapper | None = None,
    ):
        self.client = client or IntervalsIcuClient()
        self.mapper = mapper or IntervalsActivityMapper()

    def sync(
        self,
        oldest: date | datetime | str,
        newest: date | datetime | str,
    ) -> dict:
        activities = self.client.get_activities(
            oldest=oldest,
            newest=newest,
        )

        db = SessionLocal()

        created = 0
        updated = 0
        skipped = 0
        errors: list[dict] = []

        try:
            for activity in activities:
                try:
                    activity_id = activity.get("id")

                    if not activity_id:
                        skipped += 1
                        errors.append(
                            {
                                "activity_id": None,
                                "error": "Missing activity id",
                            }
                        )
                        continue

                    mapped = self.mapper.map(activity)

                    existing = (
                        db.query(WorkoutDB)
                        .filter(
                            WorkoutDB.source_file
                            == mapped.source_file
                        )
                        .first()
                    )

                    if existing is None:
                        db.add(mapped)
                        created += 1
                    else:
                        self._update_existing(
                            existing=existing,
                            incoming=mapped,
                        )
                        updated += 1

                except Exception as exc:
                    skipped += 1

                    errors.append(
                        {
                            "activity_id": (
                                activity.get("id")
                            ),
                            "error": str(exc),
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
            "fetched": len(activities),
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "errors": errors,
        }

    def _update_existing(
        self,
        existing: WorkoutDB,
        incoming: WorkoutDB,
    ) -> None:
        existing.start_time = incoming.start_time
        existing.sport = incoming.sport
        existing.distance_km = incoming.distance_km
        existing.duration_sec = incoming.duration_sec
        existing.avg_hr = incoming.avg_hr
        existing.max_hr = incoming.max_hr
        existing.avg_pace_sec_per_km = (
            incoming.avg_pace_sec_per_km
        )
        existing.records_count = incoming.records_count
        existing.laps_count = incoming.laps_count