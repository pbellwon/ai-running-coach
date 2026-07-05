from sqlalchemy import func
from sqlalchemy import extract
from app.db.database import SessionLocal
from app.db.models import WorkoutDB
from app.analysis.sport_classifier import SportClassifier


class StatisticsEngine:

    def overview(self):
        db = SessionLocal()

        total_workouts = db.query(WorkoutDB).count()

        total_distance = (
            db.query(func.sum(WorkoutDB.distance_km)).scalar() or 0
        )

        first_workout = (
            db.query(func.min(WorkoutDB.start_time)).scalar()
        )

        last_workout = (
            db.query(func.max(WorkoutDB.start_time)).scalar()
        )

        average_distance = (
            db.query(func.avg(WorkoutDB.distance_km)).scalar() or 0
        )

        by_sport_rows = (
            db.query(
                WorkoutDB.sport,
                func.count(WorkoutDB.id),
                func.sum(WorkoutDB.distance_km),
            )
         .group_by(WorkoutDB.sport)
            .all()
        )

        by_sport = [
            {
                "sport": row[0],
                "workouts": row[1],
                "distance_km": round(row[2] or 0, 1),
            }
            for row in by_sport_rows
        ]

        db.close()

        return {
            "total_workouts": total_workouts,
            "total_distance_km": round(total_distance, 1),
            "average_distance_km": round(average_distance, 2),
            "first_workout": first_workout,
            "last_workout": last_workout,
            "by_sport": by_sport
        }
    
    def training_load_overview(self):
        db = SessionLocal()
        classifier = SportClassifier()

        rows = (
            db.query(
                WorkoutDB.sport,
                func.count(WorkoutDB.id),
                func.sum(WorkoutDB.distance_km),
                func.sum(WorkoutDB.duration_sec),
            )
            .group_by(WorkoutDB.sport)
            .all()
        )

        categories = {}

        for sport, workouts, distance, duration in rows:
            category = classifier.classify(sport)

            if category not in categories:
                categories[category] = {
                    "workouts": 0,
                    "distance_km": 0,
                    "duration_hours": 0,
                    "sports": [],
                }

            categories[category]["workouts"] += workouts
            categories[category]["distance_km"] += distance or 0
            categories[category]["duration_hours"] += (duration or 0) / 3600
            categories[category]["sports"].append(sport)

        db.close()

        return {
            category: {
                "workouts": data["workouts"],
                "distance_km": round(data["distance_km"], 1),
                "duration_hours": round(data["duration_hours"], 1),
                "sports": data["sports"],
            }
            for category, data in categories.items()
        }
    
    def weekly_overview(self):
        db = SessionLocal()

        rows = (
            db.query(
                extract("year", WorkoutDB.start_time).label("year"),
                extract("week", WorkoutDB.start_time).label("week"),
                WorkoutDB.sport,
                func.count(WorkoutDB.id),
                func.sum(WorkoutDB.distance_km),
                func.sum(WorkoutDB.duration_sec),
            )
            .group_by("year", "week", WorkoutDB.sport)
            .order_by("year", "week")
            .all()
        )

        weeks = {}

        for year, week, sport, workouts, distance, duration in rows:

            key = f"{int(year)}-W{int(week):02d}"

            if key not in weeks:
                weeks[key] = {
                    "year": int(year),
                    "week": int(week),

                    "total_workouts": 0,
                    "total_distance_km": 0,
                    "total_duration_hours": 0,

                    "running_distance_km": 0,
                    "running_duration_hours": 0,

                    "cross_training_hours": 0,
                    "strength_hours": 0,

                    "sports": {},
                }

            distance = distance or 0
            duration_hours = (duration or 0) / 3600

            weeks[key]["total_workouts"] += workouts
            weeks[key]["total_distance_km"] += distance
            weeks[key]["total_duration_hours"] += duration_hours

            if sport == "running":
                weeks[key]["running_distance_km"] += distance
                weeks[key]["running_duration_hours"] += duration_hours

            elif sport in {
                "cycling",
                "swimming",
                "walking",
                "hiking",
            }:
                weeks[key]["cross_training_hours"] += duration_hours

            elif sport in {
                "training",
                "fitness_equipment",
            }:
                weeks[key]["strength_hours"] += duration_hours

            weeks[key]["sports"][sport] = {
                "workouts": workouts,
                "distance_km": round(distance, 1),
                "duration_hours": round(duration_hours, 1),
            }

        db.close()

        return [
            {
                "year": week_data["year"],
                "week": week_data["week"],

                "total_workouts": week_data["total_workouts"],
                "total_distance_km": round(week_data["total_distance_km"], 1),
                "total_duration_hours": round(week_data["total_duration_hours"], 1),

                "running_distance_km": round(week_data["running_distance_km"], 1),
                "running_duration_hours": round(week_data["running_duration_hours"], 1),

                "cross_training_hours": round(week_data["cross_training_hours"], 1),
                "strength_hours": round(week_data["strength_hours"], 1),

                "sports": week_data["sports"],
            }
            for week_data in weeks.values()
        ]
    
    def total_workouts(self):
        db = SessionLocal()
        value = db.query(func.count(WorkoutDB.id)).scalar()
        db.close()
        return value or 0

    def total_distance_km(self):
        db = SessionLocal()
        value = db.query(func.sum(WorkoutDB.distance_km)).scalar()
        db.close()
        return round(value or 0, 1)

    def running_workouts(self):
        db = SessionLocal()
        value = (
            db.query(func.count(WorkoutDB.id))
            .filter(WorkoutDB.sport == "running")
            .scalar()
        )
        db.close()
        return value or 0

    def running_distance_km(self):
        db = SessionLocal()
        value = (
            db.query(func.sum(WorkoutDB.distance_km))
            .filter(WorkoutDB.sport == "running")
            .scalar()
        )
        db.close()
        return round(value or 0, 1)

    def longest_run_km(self):
        db = SessionLocal()
        value = (
            db.query(func.max(WorkoutDB.distance_km))
            .filter(WorkoutDB.sport == "running")
            .scalar()
        )
        db.close()
        return round(value or 0, 1)

    def average_long_run_km(self):
        db = SessionLocal()
        value = (
            db.query(func.avg(WorkoutDB.distance_km))
            .filter(
                WorkoutDB.sport == "running",
                WorkoutDB.distance_km >= 18,
            )
            .scalar()
        )
        db.close()
        return round(value or 0, 1)

    def training_days_per_week(self):
        db = SessionLocal()

        total_workouts = db.query(func.count(WorkoutDB.id)).scalar() or 0

        first = db.query(func.min(WorkoutDB.start_time)).scalar()
        last = db.query(func.max(WorkoutDB.start_time)).scalar()

        db.close()

        if not first or not last:
            return 0

        weeks = max((last - first).days / 7, 1)

        return round(total_workouts / weeks, 1)
    
    def running_hours(self):
        db = SessionLocal()
        value = (
            db.query(func.sum(WorkoutDB.duration_sec))
            .filter(WorkoutDB.sport == "running")
            .scalar()
        )
        db.close()
        return round((value or 0) / 3600, 1)

    def cross_training_hours(self):
        db = SessionLocal()
        value = (
            db.query(func.sum(WorkoutDB.duration_sec))
            .filter(
                WorkoutDB.sport.in_([
                    "cycling",
                    "swimming",
                    "hiking",
                    "walking",
                ])
            )
            .scalar()
        )
        db.close()
        return round((value or 0) / 3600, 1)

    def strength_hours(self):
        db = SessionLocal()
        value = (
            db.query(func.sum(WorkoutDB.duration_sec))
            .filter(
                WorkoutDB.sport.in_([
                    "training",
                    "fitness_equipment",
                ])
            )
            .scalar()
        )
        db.close()
        return round((value or 0) / 3600, 1)