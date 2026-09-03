import os

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from app.models.athlete import Athlete, AthleteProfile, AthletePhysiology
from app.db.database import Base, SessionLocal, engine
from app.db.models import LapDB, WorkoutDB
from app.db import models
from app.services.fit_importer import FITImporter
from app.analysis.statistics_engine import StatisticsEngine
from app.analysis.training_load_engine import TrainingLoadEngine
from app.analysis.efficiency_analyzer import EfficiencyAnalyzer
from app.analysis.cardiac_drift_analyzer import CardiacDriftAnalyzer
from app.analysis.pace_stability_analyzer import PaceStabilityAnalyzer
from app.analysis.cadence_analyzer import CadenceAnalyzer
from datetime import date, datetime, timedelta
from app.models.goal import Goal
from app.engine.goal_engine import GoalEngine
from app.engine.athlete_gap_analyzer import AthleteGapAnalyzer
from app.engine.goal_feasibility import GoalFeasibility
from app.engine.athlete_profile_builder import AthleteProfileBuilder
from dataclasses import asdict
from app.engine.capability_engine import CapabilityEngine
from app.analysis.current_fitness_engine import CurrentFitnessEngine
from app.engine.workout_intent_engine import WorkoutIntentEngine
from app.engine.planned_workout_engine import PlannedWorkoutEngine
from app.engine.planned_workout_validator import PlannedWorkoutValidator
from app.engine.workout_structure_parser import WorkoutStructureParser
from app.analysis.executed_workout_structure_analyzer import ExecutedWorkoutStructureAnalyzer
from app.engine.plan_vs_execution_engine import PlanVsExecutionEngine
from app.engine.adaptive_feedback_engine import AdaptiveFeedbackEngine
from app.engine.existing_plan_importer import ExistingPlanImporter
from app.integrations.google_sheets_plan_source import GoogleSheetsPlanSource
from app.services.plan_matcher import PlanMatcher
from app.services.automatic_plan_comparison_service import (
    AutomaticPlanComparisonService,
)
from app.services.weekly_review_service import WeeklyReviewService
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(".env", override=True)
from app.integrations.intervals_icu_client import (
    IntervalsIcuClient,
)
from app.services.intervals_activity_sync_service import (
    IntervalsActivitySyncService,
)
from app.services.intervals_wellness_sync_service import (
    IntervalsWellnessSyncService,
)
from app.services.recovery_snapshot_service import (
    RecoverySnapshotService,
)
from app.services.recovery_trend_service import (
    RecoveryTrendService,
)
from app.services.training_context_service import (
    TrainingContextService,
)
from app.services.training_decision_engine import (
    TrainingDecisionEngine,
)
from app.services.today_recommendation_service import (
    TodayRecommendationService,
)
from app.services.pacemind_today_service import (
    PaceMindTodayService,
)
from app.services.sync_state_service import (
    SyncStateService,
)
from app.services.goal_progress_service import (
    GoalProgressService,
)


class HistoricalLapPayload(BaseModel):
    lap_number: int
    distance_m: float | None = None
    elapsed_time_sec: float | None = None
    avg_hr: float | None = None
    max_hr: float | None = None


class HistoricalWorkoutPayload(BaseModel):
    source_file: str
    start_time: datetime

    sport: str | None = None
    distance_km: float | None = None
    duration_sec: float | None = None
    avg_hr: float | None = None
    max_hr: float | None = None
    avg_pace_sec_per_km: float | None = None

    records_count: int | None = None
    laps_count: int | None = None

    activity_name: str | None = None
    description: str | None = None
    external_type: str | None = None
    source_platform: str | None = None

    training_load: float | None = None
    rpe: float | None = None
    race: bool | None = None

    interval_summary: str | None = None
    declared_workout_type: str | None = None
    declared_session_role: str | None = None

    laps: list[HistoricalLapPayload] = Field(
        default_factory=list
    )


class HistoricalBackfillPayload(BaseModel):
    workouts: list[HistoricalWorkoutPayload] = Field(
        default_factory=list
    )


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "https://pacemind-503211.web.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {"message": "Welcome to PaceMind API 🚀"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/athlete")
def get_athlete():
    athlete = Athlete(
        id="1",
        profile=AthleteProfile(
            first_name="Paweł",
            age=39,
            height_cm=192,
            weight_kg=77.8
        ),
        physiology=AthletePhysiology(
            vo2max=55
        )
    )

    return athlete

from pathlib import Path
from fitparse import FitFile
import gzip


@app.get("/fit/test")
def test_fit():

    folder = Path("data/imports/trainingpeaks_fit")

    file = next(folder.glob("*.FIT.gz"))

    with gzip.open(file, "rb") as gz:
        fit = FitFile(gz)

        messages = list(fit.get_messages("session"))

    return {
        "file": file.name,
        "sessions": len(messages)
    }


@app.get("/fit/decode-one")
def decode_one_fit():
    importer = FITImporter("data/imports/trainingpeaks_fit")
    return importer.decode_one_file()

@app.get("/stats/overview")
def stats_overview():
    engine = StatisticsEngine()
    return engine.overview()

@app.get("/stats/training-load-overview")
def training_load_overview():
    engine = StatisticsEngine()
    return engine.training_load_overview()

@app.get("/stats/weekly")
def weekly_stats():
    engine = StatisticsEngine()
    return engine.weekly_overview()

@app.get("/load/workout")
def workout_load(workout_file: str):
    engine = TrainingLoadEngine()
    return engine.analyze_workout(workout_file)

@app.get("/analysis/efficiency")
def efficiency_analysis(workout_file: str):
    analyzer = EfficiencyAnalyzer()
    return analyzer.analyze(workout_file)

@app.get("/debug/record")
def debug_record(workout_file: str):
    from app.db.database import SessionLocal
    from app.db.models import RecordDB

    db = SessionLocal()

    record = (
        db.query(RecordDB)
        .filter(RecordDB.workout_file == workout_file)
        .first()
    )

    db.close()

    return record.__dict__ if record else {"error": "not found"}

@app.get("/debug/fit-record")
def debug_fit_record(workout_file: str):
    from pathlib import Path
    from app.services.fit_importer import FITImporter

    importer = FITImporter("data/imports/trainingpeaks_fit")
    file = Path("data/imports/trainingpeaks_fit") / workout_file

    decoded = importer.decode_file(file)

    return decoded["first_record"]

@app.get("/debug/fit-records")
def debug_fit_records(workout_file: str):
    from pathlib import Path
    from app.services.fit_importer import FITImporter

    importer = FITImporter("data/imports/trainingpeaks_fit")
    file = Path("data/imports/trainingpeaks_fit") / workout_file

    decoded = importer.decode_file(file)

    return decoded["records"][:10]

@app.get("/analysis/cardiac-drift")
def cardiac_drift(workout_file: str):
    analyzer = CardiacDriftAnalyzer()
    return analyzer.analyze(workout_file)

@app.get("/analysis/pace-stability")
def pace_stability(workout_file: str):
    analyzer = PaceStabilityAnalyzer()
    return analyzer.analyze(workout_file)

@app.get("/analysis/cadence")
def cadence_analysis(workout_file: str):
    analyzer = CadenceAnalyzer()
    return analyzer.analyze(workout_file)

@app.get("/goal/test")
def goal_test():
    goal = Goal(
        goal_type="race_time",
        distance_km=10,
        target_time_sec=2320,  # 38:40
        target_date=date(2026, 10, 1),
        priority="A",
        notes="Break 39 minutes for 10K and target around 38:40.",
    )

    engine = GoalEngine()

    return engine.evaluate(goal)

@app.get("/goal/progress")
def goal_progress(
    target_date: str | None = None,
):
    resolved_date = (
        target_date
        or date.today().isoformat()
    )

    goal = Goal(
        goal_type="race_time",
        distance_km=10,
        target_time_sec=2310,
        target_date=date(
            2026,
            10,
            1,
        ),
        priority="A",
        notes=(
            "Target 38:30 for 10K."
        ),
    )

    progress = (
        GoalProgressService()
        .build(
            goal=goal,
            target_date=resolved_date,
        )
    )

    return asdict(progress)

@app.get("/goal/gap-test")
def goal_gap_test():

    goal = Goal(
        goal_type="race_time",
        distance_km=10,
        target_time_sec=2320,
        target_date=date(2026, 10, 1),
        priority="A",
    )

    athlete = {
        "weekly_distance_km": 42,
        "long_run_km": 14,
        "threshold_pace": None,
        "easy_pace": 5.15,
    }

    analyzer = AthleteGapAnalyzer()

    return analyzer.analyze(goal, athlete)

@app.get("/goal/feasibility")
def goal_feasibility():

    goal = Goal(
        goal_type="race_time",
        distance_km=10,
        target_time_sec=2320,
        target_date=date(2026, 10, 1),
        priority="A",
    )

    engine = GoalEngine()
    summary = engine.evaluate(goal)

    feasibility = GoalFeasibility()

    return feasibility.evaluate(summary)

@app.get("/athlete/profile")
def athlete_profile():

    profile = AthleteProfileBuilder().build()

    return asdict(profile)

@app.get("/athlete/gaps")
def athlete_gaps():

    goal = Goal(
        goal_type="race_time",
        distance_km=10,
        target_time_sec=2320,
        target_date=date(2026, 10, 1),
        priority="A",
    )

    athlete = AthleteProfileBuilder().build()
    current = CurrentFitnessEngine().build()

    capabilities = CapabilityEngine().analyze(
        athlete=athlete,
        current=current,
    )

    gaps = AthleteGapAnalyzer().analyze(
        goal=goal,
        capabilities=capabilities,
    )

    return [
        {
            "area": gap.area,
            "current_score": gap.current_score,
            "target_score": gap.target_score,
            "gap": gap.gap,
            "reason": gap.reason,
        }
        for gap in gaps
    ]

@app.get("/athlete/current-fitness")
def athlete_current_fitness():

    fitness = CurrentFitnessEngine().build()

    return asdict(fitness)

@app.get("/athlete/capabilities")
def athlete_capabilities():

    athlete = AthleteProfileBuilder().build()
    current = CurrentFitnessEngine().build()

    capabilities = CapabilityEngine().analyze(
        athlete=athlete,
        current=current,
    )

    return [
        {
            "area": capability.area,
            "score": capability.score,
            "confidence": capability.confidence,
            "evidence": capability.evidence,
        }
        for capability in capabilities
    ]

@app.get("/workout/intent-test")
def workout_intent_test(workout_type: str = "threshold"):

    intent = WorkoutIntentEngine().classify(workout_type)

    return asdict(intent)

@app.get("/workout/intents")
def workout_intents():

    return {
        "supported_workout_types": WorkoutIntentEngine().supported_types()
    }

@app.get("/workout/intent-from-description")
def workout_intent_from_description(description: str):

    intent = WorkoutIntentEngine().classify_from_description(description)

    return asdict(intent)

@app.get("/plan/workout-test")
def planned_workout_test():

    workout = PlannedWorkoutEngine().build_test_workout()

    return asdict(workout)


@app.get("/plan/build-workout")
def build_planned_workout(
    planned_date: date,
    title: str,
    description: str,
    planned_distance_km: float | None = None,
    planned_duration_min: int | None = None,
    priority: str = "normal",
):

    workout = PlannedWorkoutEngine().build(
        planned_date=planned_date,
        title=title,
        description=description,
        planned_distance_km=planned_distance_km,
        planned_duration_min=planned_duration_min,
        priority=priority,
    )

    return asdict(workout)

@app.get("/plan/validate-workout")
def validate_planned_workout(
    planned_date: date,
    title: str,
    description: str,
    planned_distance_km: float | None = None,
    planned_duration_min: int | None = None,
    priority: str = "normal",
):

    workout = PlannedWorkoutEngine().build(
        planned_date=planned_date,
        title=title,
        description=description,
        planned_distance_km=planned_distance_km,
        planned_duration_min=planned_duration_min,
        priority=priority,
    )

    validation = PlannedWorkoutValidator().validate(workout)

    return {
        "workout": asdict(workout),
        "validation": validation,
    }

@app.get("/workout/structure-test")
def workout_structure_test(description: str):

    return {
        "description": description,
        "structure": WorkoutStructureParser().parse(description),
    }

@app.get("/analysis/executed-structure")
def executed_workout_structure(workout_file: str):

    return ExecutedWorkoutStructureAnalyzer().analyze(workout_file)

@app.get("/plan/compare-workout")
def compare_planned_workout(
    planned_date: date,
    title: str,
    description: str,
    workout_file: str,
    planned_distance_km: float | None = None,
    planned_duration_min: int | None = None,
    priority: str = "normal",
):

    planned = PlannedWorkoutEngine().build(
        planned_date=planned_date,
        title=title,
        description=description,
        planned_distance_km=planned_distance_km,
        planned_duration_min=planned_duration_min,
        priority=priority,
    )

    comparison = PlanVsExecutionEngine().compare(
        planned=planned,
        workout_file=workout_file,
    )

    return asdict(comparison)

@app.get("/plan/compare-workout-debug")
def compare_planned_workout_debug(
    planned_date: date,
    title: str,
    description: str,
    workout_file: str,
    planned_distance_km: float | None = None,
    planned_duration_min: int | None = None,
    priority: str = "normal",
):

    planned = PlannedWorkoutEngine().build(
        planned_date=planned_date,
        title=title,
        description=description,
        planned_distance_km=planned_distance_km,
        planned_duration_min=planned_duration_min,
        priority=priority,
    )

    executed_structure = ExecutedWorkoutStructureAnalyzer().analyze(workout_file)

    comparison = PlanVsExecutionEngine().compare(
        planned=planned,
        workout_file=workout_file,
    )

    return {
        "planned": asdict(planned),
        "executed_structure": executed_structure,
        "comparison": asdict(comparison),
    }

@app.get("/coach/adaptive-feedback")
def adaptive_feedback(
    planned_date: date,
    title: str,
    description: str,
    workout_file: str,
    planned_distance_km: float | None = None,
    planned_duration_min: int | None = None,
    priority: str = "normal",
):

    planned = PlannedWorkoutEngine().build(
        planned_date=planned_date,
        title=title,
        description=description,
        planned_distance_km=planned_distance_km,
        planned_duration_min=planned_duration_min,
        priority=priority,
    )

    comparison = PlanVsExecutionEngine().compare(
        planned=planned,
        workout_file=workout_file,
    )

    feedback = AdaptiveFeedbackEngine().generate(comparison)

    return {
        "comparison": asdict(comparison),
        "feedback": asdict(feedback),
    }

@app.get("/plan/import-test")
def import_existing_plan_test():

    rows = [
        {
            "date": "2026-07-20",
            "day": "pn",
            "title": "Strength",
            "description": "strength 45min",
            "planned_distance_km": "",
            "planned_duration_min": "45",
            "priority": "normal",
            "notes": "Siła",
        },
        {
            "date": "2026-07-22",
            "day": "śr",
            "title": "Easy Run",
            "description": "easy 10km",
            "planned_distance_km": "10",
            "planned_duration_min": "",
            "priority": "normal",
            "notes": "10 km E",
        },
        {
            "date": "2026-07-30",
            "day": "czw",
            "title": "Threshold",
            "description": "3km easy + 6km threshold @4:00-4:02 + 2km easy",
            "planned_distance_km": "11",
            "planned_duration_min": "",
            "priority": "key",
            "notes": "3 km E + 6 km ciągłego progu 4:00-4:02 + 2 km E",
        },
        {
            "date": "2026-07-31",
            "day": "pt",
            "title": "Strength",
            "description": "strength 45min",
            "planned_distance_km": "",
            "planned_duration_min": "45",
            "priority": "normal",
            "notes": "Siła",
        },
    ]

    workouts = ExistingPlanImporter().import_rows(rows)

    return {
        "imported_count": len(workouts),
        "workouts": [asdict(workout) for workout in workouts],
    }

@app.get("/plan/google-sheets-rows-test")
def google_sheets_rows_test():

    rows = GoogleSheetsPlanSource().fetch_rows()

    return {
        "rows_count": len(rows),
        "sample": rows[:5],
    }

@app.get("/plan/google-sheets-import-test")
def google_sheets_import_test():

    rows = GoogleSheetsPlanSource().fetch_rows()

    workouts = ExistingPlanImporter().import_rows(rows)

    return {
        "rows_count": len(rows),
        "imported_count": len(workouts),
        "workouts": [asdict(workout) for workout in workouts[:10]],
    }

@app.get("/plan/match-test")
def match_planned_workout_test(
    executed_date: str,
):
    plan_source = GoogleSheetsPlanSource()
    importer = ExistingPlanImporter()
    matcher = PlanMatcher()

    rows = plan_source.fetch_rows()
    planned_workouts = importer.import_rows(rows)

    matched_workout = matcher.match_by_date(
        executed_date=executed_date,
        planned_workouts=planned_workouts,
    )

    if matched_workout is None:
        return {
            "executed_date": executed_date,
            "matched": False,
            "planned_workout": None,
        }

    return {
        "executed_date": executed_date,
        "matched": True,
        "planned_workout": matched_workout,
    }

@app.get("/plan/automatic-comparison-test")
def automatic_plan_comparison_test(
    workout_file: str,
):
    return AutomaticPlanComparisonService().compare(
        workout_file=workout_file,
    )

@app.get("/review/week-test")
def weekly_review_test(
    week_start: str,
):
    return WeeklyReviewService().review(
        week_start=week_start,
    )

@app.get("/intervals/connection-test")
def intervals_connection_test():
    athlete = IntervalsIcuClient().get_athlete()

    return {
        "status": "ok",
        "source": "intervals_icu",
        "athlete": athlete,
    }

@app.get("/intervals/activities-test")
def intervals_activities_test(
    oldest: str,
    newest: str,
):
    activities = (
        IntervalsIcuClient().get_activities(
            oldest=oldest,
            newest=newest,
        )
    )

    return {
        "status": "ok",
        "source": "intervals_icu",
        "oldest": oldest,
        "newest": newest,
        "count": len(activities),
        "activities": activities,
    }

@app.post("/intervals/sync-test")
def intervals_sync_test(
    oldest: str,
    newest: str,
):
    return IntervalsActivitySyncService().sync(
        oldest=oldest,
        newest=newest,
    )

@app.get("/intervals/wellness-test")
def intervals_wellness_test(
    oldest: str,
    newest: str,
):
    wellness = (
        IntervalsIcuClient().get_wellness(
            oldest=oldest,
            newest=newest,
        )
    )

    return {
        "status": "ok",
        "source": "intervals_icu",
        "oldest": oldest,
        "newest": newest,
        "count": len(wellness),
        "wellness": wellness,
    }

@app.post("/intervals/wellness-sync-test")
def intervals_wellness_sync_test(
    oldest: str,
    newest: str,
):
    return IntervalsWellnessSyncService().sync(
        oldest=oldest,
        newest=newest,
    )

@app.post("/admin/intervals-backfill")
def intervals_backfill(
    oldest: str,
    newest: str,
    x_sync_key: str | None = Header(
        default=None,
        alias="X-Sync-Key",
    ),
):
    expected_key = os.getenv("SYNC_API_KEY")

    if (
        not expected_key
        or x_sync_key != expected_key
    ):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
        )

    try:
        oldest_date = date.fromisoformat(
            oldest
        )
        newest_date = date.fromisoformat(
            newest
        )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=(
                "oldest and newest must use "
                "YYYY-MM-DD format"
            ),
        )

    if newest_date < oldest_date:
        raise HTTPException(
            status_code=400,
            detail=(
                "newest must be on or after oldest"
            ),
        )

    max_window_days = 31

    if (
        newest_date - oldest_date
    ).days > max_window_days:
        raise HTTPException(
            status_code=400,
            detail=(
                "Backfill window cannot exceed "
                "31 days."
            ),
        )

    source_boundary = date(
        2025,
        2,
        8,
    )

    if oldest_date < source_boundary:
        raise HTTPException(
            status_code=400,
            detail=(
                "Intervals backfill cannot start "
                "before 2025-02-08."
            ),
        )

    result = (
        IntervalsActivitySyncService()
        .sync(
            oldest=oldest_date,
            newest=newest_date,
        )
    )

    return {
        "status": "ok",
        "backfill": result,
    }

@app.post("/admin/historical-backfill")
def historical_backfill(
    payload: HistoricalBackfillPayload,
    x_sync_key: str | None = Header(
        default=None,
        alias="X-Sync-Key",
    ),
):
    expected_key = os.getenv("SYNC_API_KEY")

    if (
        not expected_key
        or x_sync_key != expected_key
    ):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
        )

    cutoff = datetime(
        2025,
        2,
        8,
    )

    if not payload.workouts:
        return {
            "status": "ok",
            "created_workouts": 0,
            "created_laps": 0,
            "skipped_existing": 0,
            "rejected": 0,
        }

    db = SessionLocal()

    created_workouts = 0
    created_laps = 0
    skipped_existing = 0
    rejected = 0

    seen_source_files: set[str] = set()

    try:
        for item in payload.workouts:
            source_file = item.source_file.strip()

            if (
                not source_file
                or item.start_time >= cutoff
            ):
                rejected += 1
                continue

            if source_file in seen_source_files:
                skipped_existing += 1
                continue

            seen_source_files.add(
                source_file
            )

            existing = (
                db.query(WorkoutDB)
                .filter(
                    WorkoutDB.source_file
                    == source_file
                )
                .first()
            )

            if existing is not None:
                skipped_existing += 1
                continue

            db.add(
                WorkoutDB(
                    source_file=source_file,
                    start_time=item.start_time,
                    sport=item.sport,
                    distance_km=item.distance_km,
                    duration_sec=item.duration_sec,
                    avg_hr=item.avg_hr,
                    max_hr=item.max_hr,
                    avg_pace_sec_per_km=(
                        item.avg_pace_sec_per_km
                    ),
                    records_count=item.records_count,
                    laps_count=item.laps_count,
                    activity_name=item.activity_name,
                    description=item.description,
                    external_type=item.external_type,
                    source_platform=(
                        item.source_platform
                    ),
                    training_load=item.training_load,
                    rpe=item.rpe,
                    race=item.race,
                    interval_summary=(
                        item.interval_summary
                    ),
                    declared_workout_type=(
                        item.declared_workout_type
                    ),
                    declared_session_role=(
                        item.declared_session_role
                    ),
                )
            )

            for lap in item.laps:
                db.add(
                    LapDB(
                        workout_file=source_file,
                        lap_number=lap.lap_number,
                        distance_m=lap.distance_m,
                        elapsed_time_sec=(
                            lap.elapsed_time_sec
                        ),
                        avg_hr=lap.avg_hr,
                        max_hr=lap.max_hr,
                    )
                )
                created_laps += 1

            created_workouts += 1

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

    return {
        "status": "ok",
        "created_workouts": created_workouts,
        "created_laps": created_laps,
        "skipped_existing": skipped_existing,
        "rejected": rejected,
    }

@app.post("/sync/daily")
def daily_sync(
    x_sync_key: str | None = Header(
        default=None,
        alias="X-Sync-Key",
    ),
):
    expected_key = os.getenv("SYNC_API_KEY")

    if (
        not expected_key
        or x_sync_key != expected_key
    ):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
        )

    today = date.today()
    oldest = today - timedelta(days=3)

    oldest_str = oldest.isoformat()
    newest_str = today.isoformat()

    wellness_result = (
        IntervalsWellnessSyncService()
        .sync(
            oldest=oldest_str,
            newest=newest_str,
        )
    )

    activities_result = (
        IntervalsActivitySyncService()
        .sync(
            oldest=oldest_str,
            newest=newest_str,
        )
    )

    return {
        "status": "ok",
        "oldest": oldest_str,
        "newest": newest_str,
        "wellness": wellness_result,
        "activities": activities_result,
    }

@app.post("/sync/refresh")
def manual_sync_refresh():
    sync_name = "manual_refresh"
    cooldown_minutes = 5

    can_run, retry_after_seconds = (
        SyncStateService()
        .can_run(
            sync_name=sync_name,
            cooldown_minutes=cooldown_minutes,
        )
    )

    if not can_run:
        raise HTTPException(
            status_code=429,
            detail={
                "message": (
                    "Refresh was performed recently."
                ),
                "retry_after_seconds": (
                    retry_after_seconds
                ),
            },
        )

    today = date.today()
    oldest = today - timedelta(days=3)

    oldest_str = oldest.isoformat()
    newest_str = today.isoformat()

    wellness_result = (
        IntervalsWellnessSyncService()
        .sync(
            oldest=oldest_str,
            newest=newest_str,
        )
    )

    activities_result = (
        IntervalsActivitySyncService()
        .sync(
            oldest=oldest_str,
            newest=newest_str,
        )
    )

    SyncStateService().mark_success(
        sync_name=sync_name
    )

    return {
        "status": "ok",
        "oldest": oldest_str,
        "newest": newest_str,
        "wellness": wellness_result,
        "activities": activities_result,
    }

@app.get("/recovery/snapshot-test")
def recovery_snapshot_test(
    target_date: str,
):
    snapshot = RecoverySnapshotService().build(
        target_date
    )

    return asdict(snapshot)

@app.get("/recovery/trend-test")
def recovery_trend_test(
    target_date: str,
):
    trend = RecoveryTrendService().build(
        target_date
    )

    return asdict(trend)

@app.get("/recovery/training-context-test")
def training_context_test(
    target_date: str,
):
    context = TrainingContextService().build(
        target_date
    )

    return asdict(context)

@app.get("/training/overview")
def training_overview(
    target_date: str | None = None,
):
    resolved_date = (
        target_date
        or date.today().isoformat()
    )

    context = (
        TrainingContextService()
        .build(
            target_date=resolved_date,
            window_days=28,
        )
    )

    return asdict(context)

@app.get("/decision/test")
def decision_test(
    target_date: str,
    planned_workout_type: str,
    planned_session_role: str | None = None,
):
    recovery = RecoverySnapshotService().build(
        target_date
    )

    trend = RecoveryTrendService().build(
        target_date
    )

    training_context = (
        TrainingContextService().build(
            target_date
        )
    )

    decision = TrainingDecisionEngine().decide(
        recovery=recovery,
        trend=trend,
        training_context=training_context,
        planned_workout_type=(
            planned_workout_type
        ),
        planned_session_role=(
            planned_session_role
        ),
    )

    return asdict(decision)

@app.get("/decision/today-test")
def decision_today_test(
    target_date: str,
):
    normalized_date = date.fromisoformat(
        target_date
    )

    rows = (
        GoogleSheetsPlanSource()
        .fetch_rows()
    )

    planned_workouts = (
        ExistingPlanImporter()
        .import_rows(rows)
    )

    planned_for_day = [
        workout
        for workout in planned_workouts
        if (
            workout.planned_date
            == normalized_date
            and workout.workout_type != "off"
        )
    ]

    if not planned_for_day:
        return {
            "target_date": target_date,
            "planned_workout": None,
            "decision": None,
            "recommendation": None,
            "message": (
                "No planned workout found "
                "for this date."
            ),
        }

    planned = planned_for_day[0]

    recovery = (
        RecoverySnapshotService()
        .build(target_date)
    )

    trend = (
        RecoveryTrendService()
        .build(target_date)
    )

    training_context = (
        TrainingContextService()
        .build(target_date)
    )

    decision = (
        TrainingDecisionEngine()
        .decide(
            recovery=recovery,
            trend=trend,
            training_context=training_context,
            planned_workout_type=(
                planned.workout_type
            ),
            planned_session_role=(
                "long_run"
                if planned.workout_type
                in {
                    "long_run",
                    "long_run+progression",
                }
                else None
            ),
        )
    )

    recommendation = (
        TodayRecommendationService()
        .build(
            decision=decision,
            planned_title=planned.title,
            planned_workout_type=(
                planned.workout_type
            ),
            planned_distance_km=(
                planned.planned_distance_km
            ),
            planned_duration_min=(
                planned.planned_duration_min
            ),
        )
    )

    return {
        "target_date": target_date,
        "planned_workout": {
            "title": planned.title,
            "workout_type": (
                planned.workout_type
            ),
            "description": (
                planned.description
            ),
            "planned_distance_km": (
                planned.planned_distance_km
            ),
            "planned_duration_min": (
                planned.planned_duration_min
            ),
            "priority": (
                planned.priority
            ),
        },
        "decision": asdict(decision),
        "recommendation": (
            asdict(recommendation)
        ),
    }

@app.get("/today")
def today(
    target_date: str | None = None,
):
    resolved_date = (
        target_date
        if target_date is not None
        else date.today().isoformat()
    )

    result = PaceMindTodayService().build(
        resolved_date
    )

    return asdict(result)

