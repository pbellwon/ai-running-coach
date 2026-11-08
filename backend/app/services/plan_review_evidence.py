"""Reuse existing execution, feedback, recovery and goal trend calculations."""
from dataclasses import asdict
from datetime import date,timedelta
from app.services.weekly_review_service import WeeklyReviewService
from app.services.weekly_coach_review_service import WeeklyCoachReviewService
from app.services.recovery_snapshot_service import RecoverySnapshotService
from app.services.current_goal_service import CurrentGoalService
from app.services.goal_progress_service import GoalProgressService


class PlanReviewEvidence:
    def __init__(self,factory):
        self.factory=factory

    def build(self,snapshot,start,end,today):
        class Snapshot:
            def fetch_rows(self): return snapshot['rows']
        weekly=WeeklyReviewService(session_factory=self.factory,plan_source=Snapshot())
        monday=start-timedelta(days=start.weekday())
        days=[]
        while monday<=end:
            report=weekly.review(monday,include_execution_reviews=True,as_of_date=today)
            days.extend(d for d in report['days'] if start.isoformat()<=d['date']<=end.isoformat())
            monday+=timedelta(days=7)
        recovery=WeeklyCoachReviewService(snapshot_service=RecoverySnapshotService(self.factory))._recovery(start,end)
        current_recovery=WeeklyCoachReviewService(snapshot_service=RecoverySnapshotService(self.factory))._recovery(today-timedelta(days=5),today-timedelta(days=1))
        goal=CurrentGoalService(self.factory).get()
        progress=GoalProgressService(self.factory).build(goal,today-timedelta(days=1))
        return {'days':days,'recovery':recovery,'current_recovery':current_recovery,'goal_progress':asdict(progress)}
