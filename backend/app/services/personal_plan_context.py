"""Read-only athlete evidence for planning. Conversations are PaceMind's saved chats."""
from collections import defaultdict
from datetime import datetime, timedelta
import math

from app.db.database import SessionLocal
from app.db.models import WorkoutDB, AthleteMemoryDB, CoachChatTurnDB, WorkoutFeedbackDB, DailyAthleteStateDB
from app.services.plan_correction_service import digest


class PersonalPlanContext:
    def __init__(self, session_factory=SessionLocal):
        self.factory = session_factory

    def capture(self, today):
        def dt(value):
            return value.isoformat() if value else None
        def fields(record, keys):
            return {k: dt(getattr(record, k)) if isinstance(getattr(record, k), datetime) else getattr(record, k) for k in keys}
        with self.factory() as db:
            runs = db.query(WorkoutDB).filter(WorkoutDB.start_time >= datetime.combine(today - timedelta(days=84), datetime.min.time()),
                WorkoutDB.start_time < datetime.combine(today + timedelta(days=1), datetime.min.time())).order_by(WorkoutDB.start_time, WorkoutDB.id).all()
            memories = db.query(AthleteMemoryDB).filter_by(is_active=True).order_by(AthleteMemoryDB.id).all()
            turns = db.query(CoachChatTurnDB).filter_by(status='completed').order_by(CoachChatTurnDB.created_at.desc()).limit(60).all()
            # Include older health and cycle discussions that would otherwise fall out of the recent window.
            from sqlalchemy import or_
            relevant = db.query(CoachChatTurnDB).filter(CoachChatTurnDB.status == 'completed', or_(*[
                CoachChatTurnDB.message.ilike(f'%{word}%') for word in ('kontuz', 'ból', 'boli', 'injur', '10 dni', '10-dni', 'mikrocykl')
            ])).order_by(CoachChatTurnDB.created_at.desc()).limit(30).all()
            turns = sorted({t.id: t for t in turns + relevant}.values(), key=lambda t: (t.created_at, t.id))
            feedback = db.query(WorkoutFeedbackDB).order_by(WorkoutFeedbackDB.updated_at.desc()).limit(120).all()
            wellness = db.query(DailyAthleteStateDB).filter(DailyAthleteStateDB.date >= datetime.combine(today - timedelta(days=27), datetime.min.time()),
                DailyAthleteStateDB.date < datetime.combine(today + timedelta(days=1), datetime.min.time())).order_by(DailyAthleteStateDB.date).all()
            raw = {
                'activities': [fields(w, ['id', 'start_time', 'sport', 'distance_km', 'duration_sec', 'declared_workout_type', 'training_load', 'rpe', 'race', 'avg_hr', 'activity_name', 'description']) for w in runs],
                'memory': [fields(m, ['id', 'category', 'memory_text', 'source', 'confidence', 'updated_at']) for m in memories],
                'conversations': [fields(t, ['id', 'created_at', 'message', 'answer']) for t in turns],
                'feedback': [fields(f, ['id', 'session_id', 'perceived_effort', 'execution_feeling', 'comment', 'updated_at']) for f in feedback],
                'recovery': [fields(w, ['date', 'hrv', 'resting_hr', 'sleep_sec', 'fatigue', 'soreness', 'ctl', 'atl']) for w in wellness]}
        daily = defaultdict(lambda: {'km': 0, 'minutes': 0, 'types': []})
        for item in raw['activities']:
            if str(item['sport']).lower() not in ('run', 'running') or not item['distance_km'] or not item['duration_sec']:
                continue
            if not math.isfinite(item['distance_km']) or not math.isfinite(item['duration_sec']) or item['distance_km'] <= 0 or item['duration_sec'] <= 0:
                continue
            day = item['start_time'][:10]
            daily[day]['km'] += item['distance_km']
            daily[day]['minutes'] += item['duration_sec'] / 60
            daily[day]['types'].append(item['declared_workout_type'])
        recent = {day: value for day, value in daily.items() if (today - timedelta(days=28)).isoformat() <= day < today.isoformat()}
        enough = len(recent) >= 6 and max(recent, default='') >= (today - timedelta(days=7)).isoformat()
        baseline = round(sum(v['km'] for v in recent.values()) * 10 / 28, 1)
        limits = {'cycle_days': 10, 'max_cycle_km': baseline, 'max_session_km': round(max((v['km'] for v in recent.values()), default=0) * 1.1, 1),
                  'max_session_minutes': round(max((v['minutes'] for v in recent.values()), default=0) * 1.1), 'history_sufficient': enough}
        chats = [{**t, 'answer': (t['answer'] or '')[:1000], 'answer_truncated': len(t['answer'] or '') > 1000} for t in raw['conversations']]
        activities = [{**w, 'description': (w['description'] or '')[:1500]} for w in raw['activities'][-30:]]
        facts = {'running_days': [{'date': d, **v} for d, v in sorted(daily.items())],
                 'recent_activities': activities, 'memory': raw['memory'],
                 'conversations': chats, 'feedback': raw['feedback'], 'recovery': raw['recovery']}
        sources = [{'id': 'history', 'label': 'Zarejestrowane treningi: ostatnie 84 dni'}, {'id': 'recovery', 'label': 'Regeneracja: ostatnie 28 dni'}]
        for key in ('memory', 'conversations', 'feedback'):
            for item in raw[key]:
                label = (f"Pamięć zawodnika ({item['category']}): {item['memory_text'][:160]}" if key == 'memory' else f"Rozmowa: {item['message'][:120]}" if key == 'conversations' else f"Odczucia po treningu: {(item['comment'] or item['execution_feeling'] or '')[:120]}")
                sources.append({'id': f'{key}:{item["id"]}', 'label': label})
        return {'version': digest(raw), 'facts': facts, 'limits': limits, 'sources': sources,
                'limitations': ['Dostęp obejmuje rozmowy zapisane w PaceMind; nie obejmuje innych rozmów w ChatGPT.',
                    'Historia i feedback pokazują reakcje na obciążenia, ale same nie dowodzą przyczynowej skuteczności treningu.',
                    'Brak wpisu o bólu nie potwierdza braku kontuzji. Stare i sprzeczne zgłoszenia wymagają wyjaśnienia.']}
