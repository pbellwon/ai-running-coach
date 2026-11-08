"""All stored training history as monthly context; recorded races remain facts, not forecasts."""
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import math

from app.db.database import SessionLocal
from app.db.models import WorkoutDB
from app.services.composite_session_builder import CompositeSessionBuilder


class AthleteHistoryService:
    def __init__(self, session_factory=SessionLocal, builder=None):
        self.factory = session_factory
        self.builder = builder or CompositeSessionBuilder()

    @staticmethod
    def positive(value):
        return isinstance(value, (int, float)) and math.isfinite(value) and value > 0

    def build(self, today):
        with self.factory() as db:
            activities = db.query(WorkoutDB).filter(
                WorkoutDB.start_time < datetime.combine(today + timedelta(days=1), datetime.min.time())
            ).order_by(WorkoutDB.start_time, WorkoutDB.id).all()
        valid = [w for w in activities if all(value is None or (math.isfinite(value) and value >= 0)
            for value in (w.distance_km, w.duration_sec))]
        sessions = self.builder.build(valid)
        monthly = defaultdict(lambda: {'sessions': 0, 'running_km': 0, 'training_min': 0, 'types': Counter()})
        for session in sessions:
            month = monthly[session.start_time.strftime('%Y-%m')]
            month['sessions'] += 1
            month['types'][session.workout_type] += 1
            if self.positive(session.total_duration_min):
                month['training_min'] += session.total_duration_min
            if session.sport_family == 'running' and self.positive(session.total_distance_km):
                month['running_km'] += session.total_distance_km
        # Use only the activity explicitly marked as a race. Warm-up and cooldown
        # may belong to the same logical session but are not part of its race time.
        races = []
        for activity in valid:
            if (str(activity.sport).lower() not in ('run', 'running')
                    or not (activity.race is True or activity.declared_workout_type == 'race')
                    or not self.positive(activity.distance_km) or not self.positive(activity.duration_sec)):
                continue
            races.append({'id': activity.id, 'date': activity.start_time.date().isoformat(),
                'name': (activity.activity_name or '')[:200], 'distance_km': activity.distance_km,
                'recorded_duration_sec': activity.duration_sec,
                'days_ago': (today - activity.start_time.date()).days,
                'time_basis': 'recorded_activity_duration_not_verified_official_result'})
        # Keep the fastest recorded race in each distance band across the entire
        # archive as well as recent races. Old records never stand in for current form.
        best = {}
        for race in races:
            band = round(race['distance_km'], 1)
            if band not in best or race['recorded_duration_sec'] < best[band]['recorded_duration_sec']:
                best[band] = race
        recent = races[-20:]
        selected = {r['id']: r for r in [*best.values(), *recent]}
        return {'coverage_start': activities[0].start_time.date().isoformat() if activities else None,
            'coverage_end': activities[-1].start_time.date().isoformat() if activities else None,
            'source_activities_count': len(activities), 'invalid_activities_count': len(activities)-len(valid), 'logical_sessions_count': len(sessions),
            'months': [{'month': key, **value, 'running_km': round(value['running_km'], 1),
                'training_min': round(value['training_min'], 1), 'types': dict(value['types'])}
                for key, value in sorted(monthly.items())],
            'race_activities_count': len(races), 'race_results': sorted(selected.values(), key=lambda r: (r['date'], r['id'])),
            'limitations': ['Historia obejmuje wszystkie treningi zapisane w bazie PaceMind do wskazanego dnia, nie niezarejestrowane aktywności.',
                'Dawne najlepsze wyniki pokazują historię, nie potwierdzają aktualnej formy.',
                'Czas aktywności z oznaczeniem zawodów nie jest zweryfikowanym wynikiem oficjalnym; trasa, pogoda i sposób rejestracji mogą wpływać na porównanie.',
                'Nie ma podstaw do wyliczania procentowych szans ani gwarantowanego wyniku ze zgodności wykonania lub samej objętości.']
                + ([f'Pominięto {len(activities)-len(valid)} aktywności z nieprawidłowym dystansem lub czasem.'] if len(valid) != len(activities) else [])}
