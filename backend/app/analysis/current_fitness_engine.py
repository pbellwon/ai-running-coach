from datetime import datetime, timedelta

from sqlalchemy import func

from app.db.database import SessionLocal
from app.db.models import WorkoutDB
from app.models.current_fitness import CurrentFitness


class CurrentFitnessEngine:

    def __init__(self, period_weeks: int = 8):
        self.period_weeks = period_weeks

    def build(self) -> CurrentFitness:

        db = SessionLocal()

        cutoff = datetime.utcnow() - timedelta(
            weeks=self.period_weeks
        )

        workouts = (
            db.query(WorkoutDB)
            .filter(WorkoutDB.start_time >= cutoff)
            .all()
        )

        db.close()

        running = [
            w for w in workouts
            if w.sport == "running"
        ]

        cross = [
            w for w in workouts
            if w.sport in (
                "cycling",
                "swimming",
                "walking",
                "hiking",
            )
        ]

        strength = [
            w for w in workouts
            if w.sport in (
                "training",
                "fitness_equipment",
            )
        ]

        running_distance = sum(
            w.distance_km or 0
            for w in running
        )

        running_hours = sum(
            w.duration_sec or 0
            for w in running
        ) / 3600

        cross_hours = sum(
            w.duration_sec or 0
            for w in cross
        ) / 3600

        strength_hours = sum(
            w.duration_sec or 0
            for w in strength
        ) / 3600

        longest_run = max(
            (w.distance_km or 0 for w in running),
            default=0,
        )

        running_sessions = len(running)

        running_sessions_per_week = (
            running_sessions / self.period_weeks
        )

        average_weekly_distance = (
            running_distance / self.period_weeks
        )

        active_weeks = len(
            {
                (
                    w.start_time.isocalendar()[0],
                    w.start_time.isocalendar()[1],
                )
                for w in workouts
            }
        )

        consistency = (
            active_weeks / self.period_weeks
        ) * 100

        return CurrentFitness(

            period_weeks=self.period_weeks,

            running_distance_km=round(
                running_distance,
                1,
            ),

            running_hours=round(
                running_hours,
                1,
            ),

            running_sessions=running_sessions,

            running_sessions_per_week=round(
                running_sessions_per_week,
                1,
            ),

            average_weekly_distance_km=round(
                average_weekly_distance,
                1,
            ),

            cross_training_hours=round(
                cross_hours,
                1,
            ),

            strength_hours=round(
                strength_hours,
                1,
            ),

            longest_run_km=round(
                longest_run,
                1,
            ),

            consistency=round(
                consistency,
                1,
            ),
        )