"""One confirmed primary goal. Calendar edits require a fresh confirmation."""
import json
from datetime import date
from app.db.database import SessionLocal
from app.db.models import AthleteProfileStateDB
from app.models.goal import Goal


class CurrentGoalService:
    def __init__(self, session_factory=SessionLocal):
        self.factory = session_factory

    def get(self) -> Goal:
        with self.factory() as db:
            state = db.get(AthleteProfileStateDB, 1)
            event = json.loads(state.goal_json) if state and state.goal_json else None
        if not event:
            return Goal(goal_type='unconfigured', distance_km=None, target_time_sec=None,
                        target_date=None, notes='Wybierz i potwierdź cel główny w profilu zawodnika.')
        parts = [int(p) for p in event['target_time'].split(':')] if event['target_time'] else []
        seconds = sum(v*60**i for i, v in enumerate(reversed(parts))) if parts else None
        return Goal(goal_type='race_time' if seconds else 'race_completion', distance_km=event['distance_km'],
                    target_time_sec=seconds, target_date=date.fromisoformat(event['date']), priority='A',
                    notes=f"{event['name']}. {event['notes']}")
