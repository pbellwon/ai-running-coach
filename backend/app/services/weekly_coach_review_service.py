"""Compose a bounded weekly coach review from existing calculations and evidence."""
from dataclasses import asdict
from datetime import date, datetime, timedelta

from app.engine.weekly_coach_review_engine import WeeklyCoachReviewEngine
from app.services.recovery_snapshot_service import RecoverySnapshotService
from app.services.recovery_trend_service import RecoveryTrendService
from app.services.weekly_review_service import WeeklyReviewService


class WeeklyCoachReviewService:
    def __init__(self, weekly_service=None, snapshot_service=None, coach_engine=None, today=None):
        self.weekly_service = weekly_service or WeeklyReviewService()
        self.snapshot_service = snapshot_service or RecoverySnapshotService()
        self.coach_engine = coach_engine or WeeklyCoachReviewEngine()
        self.today = today or date.today

    def build(self, week_start: date | str | None = None) -> dict:
        today = self.today()
        current_monday = today - timedelta(days=today.weekday())
        if week_start is None:
            start = current_monday - timedelta(days=7)
        elif isinstance(week_start, datetime):
            start = week_start.date()
        elif isinstance(week_start, date):
            start = week_start
        else:
            try:
                start = date.fromisoformat(week_start)
            except (ValueError, TypeError) as exc:
                raise ValueError("week_start must use YYYY-MM-DD format.") from exc
        if start.weekday() != 0:
            raise ValueError("week_start must be a Monday.")
        if start > current_monday:
            raise ValueError("A future week cannot be reviewed yet.")

        end = start + timedelta(days=6)
        as_of = min(end, today)
        weekly = self.weekly_service.review(
            start, include_execution_reviews=True, as_of_date=today,
        )
        recovery = self._recovery(start, as_of)
        sessions_count = weekly["summary"]["executed_sessions_count"]
        coach = self.coach_engine.review(weekly, recovery)
        return {
            "week_start": start.isoformat(),
            "week_end": end.isoformat(),
            "as_of_date": as_of.isoformat(),
            "current_week_start": current_monday.isoformat(),
            "period_status": "completed" if end < today else "in_progress",
            "status": "ready" if sessions_count else "no_execution_data",
            "summary": weekly["summary"],
            "training_distribution": weekly["training_distribution"],
            "days": weekly["days"],
            "recovery": recovery,
            "coach": coach,
        }

    def _recovery(self, start: date, end: date) -> dict:
        snapshots = {}
        missing_baseline_days = 0
        for offset in range((end - start).days + 1):
            day = start + timedelta(days=offset)
            try:
                snapshot = self.snapshot_service.build(day)
            except ValueError as exc:
                # A missing day is expected; calculation defects must still fail.
                if not str(exc).startswith("No athlete state found for "):
                    raise
                continue
            if snapshot.available_metrics_count == 0 and snapshot.form is None:
                continue
            snapshots[day] = snapshot
            if any(
                metric.current is not None and metric.status == "insufficient_baseline"
                for metric in (snapshot.hrv, snapshot.resting_hr, snapshot.sleep_duration)
            ):
                missing_baseline_days += 1

        class WeekSnapshots:
            def build(self, target_date):
                if target_date not in snapshots:
                    raise ValueError(f"No athlete state found for {target_date}.")
                return snapshots[target_date]

        trend = RecoveryTrendService(snapshot_service=WeekSnapshots()).build(end)
        usable_trend_days = sum(
            snapshot.date >= end - timedelta(days=trend.window_days - 1)
            and (
                snapshot.form is not None
                or any(metric.status in {"normal", "warning", "critical"} for metric in (
                    snapshot.hrv, snapshot.resting_hr, snapshot.sleep_duration, snapshot.sleep_score,
                ))
            )
            for snapshot in snapshots.values()
        )
        sleep = [s.sleep_duration.current / 3600 for s in snapshots.values() if s.sleep_duration.current is not None]
        trend_data = asdict(trend)
        if usable_trend_days < 2:
            trend_data["fatigue_signal"] = "insufficient_data"
            trend_data["reasons"] = ["Za mało porównywalnych danych na koniec tygodnia do oceny sygnału zmęczenia."]
        return {
            "available_days": len(snapshots),
            "missing_days": (end - start).days + 1 - len(snapshots),
            "missing_baseline_days": missing_baseline_days,
            "average_sleep_hours": round(sum(sleep) / len(sleep), 1) if sleep else None,
            "status_counts": {
                status: sum(s.overall_status == status for s in snapshots.values())
                for status in ("good", "caution", "poor", "insufficient_data", "unknown")
            },
            "fatigue_signal": trend_data["fatigue_signal"],
            "trend": trend_data,
            "days": [asdict(snapshot) for snapshot in snapshots.values()],
        }
