from __future__ import annotations

from datetime import date, datetime

from app.db.database import SessionLocal
from app.db.models import DailyAthleteStateDB
from app.integrations.intervals_icu_client import (
    IntervalsIcuClient,
)
from app.integrations.intervals_wellness_mapper import (
    IntervalsWellnessMapper,
)


class IntervalsWellnessSyncService:
    def __init__(
        self,
        client: IntervalsIcuClient | None = None,
        mapper: IntervalsWellnessMapper | None = None,
    ):
        self.client = client or IntervalsIcuClient()
        self.mapper = mapper or IntervalsWellnessMapper()

    def sync(
        self,
        oldest: date | datetime | str,
        newest: date | datetime | str,
    ) -> dict:
        wellness_records = self.client.get_wellness(
            oldest=oldest,
            newest=newest,
        )

        db = SessionLocal()

        created = 0
        updated = 0
        skipped = 0
        errors: list[dict] = []

        try:
            for wellness in wellness_records:
                try:
                    state = self.mapper.map(wellness)

                    state_datetime = datetime.combine(
                        state.date,
                        datetime.min.time(),
                    )

                    existing = (
                        db.query(DailyAthleteStateDB)
                        .filter(
                            DailyAthleteStateDB.date
                            == state_datetime
                        )
                        .first()
                    )

                    if existing is None:
                        db.add(
                            DailyAthleteStateDB(
                                date=state_datetime,
                                resting_hr=state.resting_hr,
                                hrv=state.hrv,
                                hrv_sdnn=state.hrv_sdnn,
                                sleep_sec=state.sleep_sec,
                                sleep_score=state.sleep_score,
                                sleep_quality=state.sleep_quality,
                                avg_sleeping_hr=(
                                    state.avg_sleeping_hr
                                ),
                                ctl=state.ctl,
                                atl=state.atl,
                                ramp_rate=state.ramp_rate,
                                weight_kg=state.weight_kg,
                                vo2max=state.vo2max,
                                steps=state.steps,
                                soreness=state.soreness,
                                fatigue=state.fatigue,
                                stress=state.stress,
                                mood=state.mood,
                                motivation=state.motivation,
                                readiness=state.readiness,
                                spo2=state.spo2,
                            )
                        )

                        created += 1

                    else:
                        self._update_existing(
                            existing=existing,
                            state=state,
                        )

                        updated += 1

                except Exception as exc:
                    skipped += 1

                    errors.append(
                        {
                            "date": wellness.get("id"),
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
            "fetched": len(wellness_records),
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "errors": errors,
        }

    def _update_existing(
        self,
        existing: DailyAthleteStateDB,
        state,
    ) -> None:
        existing.resting_hr = state.resting_hr
        existing.hrv = state.hrv
        existing.hrv_sdnn = state.hrv_sdnn

        existing.sleep_sec = state.sleep_sec
        existing.sleep_score = state.sleep_score
        existing.sleep_quality = state.sleep_quality
        existing.avg_sleeping_hr = state.avg_sleeping_hr

        existing.ctl = state.ctl
        existing.atl = state.atl
        existing.ramp_rate = state.ramp_rate

        existing.weight_kg = state.weight_kg
        existing.vo2max = state.vo2max
        existing.steps = state.steps

        existing.soreness = state.soreness
        existing.fatigue = state.fatigue
        existing.stress = state.stress
        existing.mood = state.mood
        existing.motivation = state.motivation
        existing.readiness = state.readiness

        existing.spo2 = state.spo2