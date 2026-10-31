"""Bounded, fresh coaching facts. This layer never calls an LLM or writes training data."""
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone

from app.services.coach_context_service import CoachContextService
from app.services.weekly_coach_review_service import WeeklyCoachReviewService
from app.services.weekly_review_service import WeeklyReviewService
from app.services.workout_explanation_service import WorkoutExplanationService
from app.services.recent_execution_review_service import RecentExecutionReviewService
from app.integrations.google_sheets_plan_source import GoogleSheetsPlanSource


class CoachChatContextService:
    def __init__(self, base=None, weekly=None, plan=None, workout=None, today=None):
        self.base = base or CoachContextService()
        self.weekly = weekly
        self.plan = plan
        self.workout = workout
        self.today = today or date.today

    def build(self, selection):
        today = self.today()
        facts, sources, limitations = {}, [], []
        # Reuse one Sheets read per answer, including failures; refresh on the next answer.
        class PlanSnapshot:
            loaded, rows, error = False, None, None
            def fetch_rows(self):
                if not self.loaded:
                    self.loaded = True
                    try:
                        self.rows = GoogleSheetsPlanSource().fetch_rows()
                    except Exception as exc:
                        self.error = exc
                if self.error is not None:
                    raise self.error
                return self.rows
        plan_source = PlanSnapshot()
        weekly = self.weekly or WeeklyCoachReviewService(
            weekly_service=WeeklyReviewService(plan_source=plan_source), today=self.today)
        plan = self.plan or WeeklyReviewService(plan_source=plan_source)
        workout = self.workout or WorkoutExplanationService(
            execution_review_service=RecentExecutionReviewService(plan_source=plan_source))

        def collect(key, label, fn, **reference):
            try:
                facts[key] = fn()
                sources.append({"label": label, **reference})
            except LookupError:
                limitations.append(f"{label}: brak zapisu w dostępnej historii.")
            except Exception:
                # Partial upstream failure must not become a fabricated healthy reading.
                limitations.append(f"{label}: dane są obecnie niedostępne.")

        collect("goal", "Aktualny cel", lambda: asdict(self.base.current_goal_service.get()))
        collect("athlete", "Rekomendacja dnia, postęp celu i pamięć zawodnika",
                lambda: asdict(self.base.build(today)), date=today.isoformat())
        if "athlete" not in facts:
            # Missing wellness can make the combined daily context unavailable;
            # it must not hide independently available history or athlete memory.
            collect("goal_progress", "Postęp przygotowań do celu", lambda: asdict(
                self.base.goal_progress_service.build(
                    goal=self.base.current_goal_service.get(), target_date=today)))
            collect("athlete_memory", "Zapisana pamięć zawodnika", lambda: [
                asdict(item) for item in self.base.athlete_memory_service.list_active()])
        monday = today - timedelta(days=today.weekday())
        start = today - timedelta(days=27)
        first_monday = start - timedelta(days=start.weekday())
        for offset in range((monday-first_monday).days // 7 + 1):
            week = first_monday + timedelta(days=7*offset)
            collect(f"history_{week.isoformat()}", "Historia treningów", lambda week=week:
                    self._compact_week(weekly.build(week), since=start),
                    week_start=week.isoformat(), date=max(start, week).isoformat(),
                    end_date=min(today, week+timedelta(days=6)).isoformat())
        collect("upcoming_plan", "Plan na najbliższe siedem dni", lambda: [
            asdict(p) for p in plan.planned_between(today, today + timedelta(days=6))
        ][:40], date=today.isoformat())
        if selection["kind"] == "week":
            selected = date.fromisoformat(selection["week_start"])
            collect("selected_week", "Wybrany tydzień",
                    lambda: self._compact_week(weekly.build(selected)), week_start=selected.isoformat())
        if selection["kind"] == "workout":
            collect("selected_workout", "Wybrany trening", lambda: asdict(workout.build(
                selection["session_id"], selection["date"])),
                session_id=selection["session_id"], date=selection["date"])
        return {"as_of": datetime.now(timezone.utc).isoformat(), "facts": facts,
                "sources": sources, "limitations": limitations,
                "selection": selection}

    @staticmethod
    def _compact_week(week, since=None):
        result = {"week_start": week["week_start"], "week_end": week["week_end"],
                "period_status": week["period_status"], "summary": week["summary"],
                "coach": week["coach"],
                "recovery": {k: week["recovery"][k] for k in
                             ("available_days", "fatigue_signal", "average_sleep_hours")},
                "sessions": [{"date": d["date"], "sessions": [
                    {k: s.get(k) for k in ("session_id", "workout_type", "total_distance_km",
                                           "total_duration_min", "execution_review")}
                    for s in d["executed_sessions"][:12]]} for d in week["days"] if since is None or d["date"] >= since.isoformat()]}
        if since and week["week_start"] < since.isoformat():
            # Whole-week aggregates would include days outside the advertised 28-day window.
            result.pop("summary")
            result.pop("coach")
            result.pop("recovery")
        return result
