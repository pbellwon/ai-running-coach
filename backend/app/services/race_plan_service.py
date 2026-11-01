"""Persistent full-plan previews sharing the single-workout Sheets writer gate."""
from copy import deepcopy
from datetime import date, datetime, timedelta
import json
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from app.db.database import SessionLocal
from app.db.models import RacePlanDraftDB, TrainingPreferencesDB, PlanWriteGateDB, PlanCorrectionDB, WorkoutDB
from app.engine.race_plan_engine import RacePlanEngine, parse_calendar
from app.integrations.google_sheets_plan_source import GoogleSheetsPlanSource
from app.services.coach_chat_service import ChatError
from app.services.plan_correction_service import digest


class RacePlanService:
    def __init__(self, source=None, session_factory=SessionLocal, now=None):
        self.source = source or GoogleSheetsPlanSource()
        self.factory = session_factory
        self.now = now or (lambda: datetime.now(ZoneInfo('Europe/Warsaw')))

    def preferences(self):
        with self.factory() as db:
            record = db.get(TrainingPreferencesDB, 1)
            value = json.loads(record.payload) if record else None
            return {'value': value, 'version': digest(value)}

    def save_preferences(self, value, version):
        with self.factory() as db:
            record = db.get(TrainingPreferencesDB, 1)
            current = json.loads(record.payload) if record else None
            if digest(current) != version:
                raise ChatError(409, 'Preferencje zmieniły się. Wczytaj je ponownie.')
            encoded = json.dumps(value, sort_keys=True)
            if record:
                changed = db.query(TrainingPreferencesDB).filter_by(id=1, payload=record.payload).update({'payload': encoded})
                if not changed:
                    db.rollback()
                    raise ChatError(409, 'Preferencje zmieniły się. Wczytaj je ponownie.')
            else:
                db.add(TrainingPreferencesDB(id=1, payload=encoded))
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                raise ChatError(409, 'Preferencje zmieniły się. Wczytaj je ponownie.')
        return {'value': value, 'version': digest(value)}

    def context(self):
        snapshot = self.source.correction_snapshot()
        calendar = self.source.race_calendar_snapshot()
        races = parse_calendar(calendar)
        today = self.now().date()
        future = [e for e in races if e['date'] > today.isoformat()]
        next_a = next((e for e in future if e['priority'] == 'A'), None)
        with self.factory() as db:
            workouts = db.query(WorkoutDB).filter(WorkoutDB.start_time >= datetime.combine(today - timedelta(days=28), datetime.min.time()),
                WorkoutDB.start_time < datetime.combine(today, datetime.min.time())).all()
            running = [w for w in workouts if str(w.sport).lower() in ('run', 'running') and w.distance_km and w.distance_km > 0]
            average = round(sum(w.distance_km for w in running) / 4, 1) if running else None
        return {'plan_version': digest(snapshot), 'calendar_version': digest(calendar), 'races': future,
                'preferences': self.preferences(), 'recent_weekly_km': average,
                'default_start': (today + timedelta(days=1)).isoformat(),
                'default_end': (date.fromisoformat(next_a['date']) + timedelta(days=7)).isoformat() if next_a else None,
                'existing_days': len({r['date'] for r in snapshot['rows'] if r.get('date', '') > today.isoformat()})}

    def history(self):
        with self.factory() as db:
            return {'items': [{'id': item.id, 'status': item.status, **{k: json.loads(item.payload)[k]
                    for k in ('start', 'end', 'created_at', 'summary')}}
                for item in db.query(RacePlanDraftDB).order_by(RacePlanDraftDB.created_at.desc()).limit(30)]}

    def get(self, identifier):
        with self.factory() as db:
            record = db.get(RacePlanDraftDB, identifier)
            if not record:
                raise ChatError(404, 'Nie znaleziono wersji planu.')
            return self._view(record)

    @staticmethod
    def _view(record):
        payload = json.loads(record.payload)
        # Internal whole-sheet audit snapshots stay in the DB, not in every UI response.
        return {k: v for k, v in payload.items() if k not in ('before_snapshot', 'after_snapshot')} | {'status': record.status}

    def preview(self, identifier, request):
        request_hash = digest(request)
        with self.factory() as db:
            previous = db.get(RacePlanDraftDB, identifier)
            if previous:
                if previous.request_hash != request_hash:
                    raise ChatError(409, 'Identyfikator został już użyty do innego planu.')
                return self._view(previous)
            protected = {json.loads(c.payload)['row'] for c in db.query(PlanCorrectionDB).filter_by(status='applied')}
        preferences = self.preferences()
        if not preferences['value']:
            raise ChatError(422, 'Zapisz najpierw dni, objętość i limity czasu.')
        snapshot = self.source.correction_snapshot()
        calendar = self.source.race_calendar_snapshot()
        if (digest(snapshot) != request['plan_version'] or digest(calendar) != request['calendar_version']
                or preferences['version'] != request['preferences_version']):
            raise ChatError(409, 'Plan, kalendarz lub preferencje zmieniły się. Wczytaj aktualne dane.')
        result = RacePlanEngine().build(snapshot, parse_calendar(calendar), preferences['value'],
            date.fromisoformat(request['start']), date.fromisoformat(request['end']),
            request['replace_existing'], protected, self.now().date())
        after = deepcopy(snapshot)
        for entry in result['entries']:
            if entry['action'] == 'replace':
                after['rows'][entry['row'] - 2] = entry['after']
            elif entry['action'] == 'add':
                after['rows'].append(entry['after'])
                entry['row'] = len(after['rows']) + 1
        changes = sum(e['action'] != 'keep' for e in result['entries'])
        if not changes:
            result['blockers'].append('W tym zakresie nie ma zmian do zapisania. Wydłuż okres lub wybierz przebudowę niechronionych jednostek.')
            result['can_accept'] = False
        payload = {**request, **result, 'id': identifier, 'created_at': self.now().isoformat(),
                   'preferences': preferences['value'], 'before_snapshot': snapshot, 'after_snapshot': after,
                   'summary': {'added': sum(e['action'] == 'add' for e in result['entries']),
                               'replaced': sum(e['action'] == 'replace' for e in result['entries']),
                               'kept': sum(e['action'] == 'keep' for e in result['entries'])}}
        with self.factory() as db:
            record = RacePlanDraftDB(id=identifier, request_hash=request_hash, payload=json.dumps(payload),
                                    status='preview', created_at=self.now().replace(tzinfo=None))
            db.add(record)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                return self.preview(identifier, request)
            return self._view(record)

    def decide(self, identifier, accept):
        with self.factory() as db:
            if not db.get(PlanWriteGateDB, 1):
                db.add(PlanWriteGateDB(id=1, owner=''))
                try:
                    db.commit()
                except IntegrityError:
                    db.rollback()
        with self.factory() as db:
            record = db.get(RacePlanDraftDB, identifier)
            if not record:
                raise ChatError(404, 'Nie znaleziono planu.')
            payload = json.loads(record.payload)
            if record.status in ('applied', 'rejected'):
                if (record.status == 'applied') != accept:
                    raise ChatError(409, 'Ten plan ma już inną decyzję.')
                return self._view(record)
            if record.status == 'writing':
                if not accept:
                    raise ChatError(409, 'Zapis rozpoczęty. Sprawdź jego wynik.')
                return self._reconcile(db, record)
            if record.status != 'preview':
                raise ChatError(409, 'Podgląd jest nieaktualny. Przygotuj nowy.')
            if accept and not payload['can_accept']:
                raise ChatError(409, 'Plan ma nierozstrzygnięte konflikty. Sprawdź podgląd.')
            if not accept:
                changed = db.query(RacePlanDraftDB).filter_by(id=identifier, status='preview').update({'status': 'rejected'})
                if not changed:
                    db.rollback()
                    raise ChatError(409, 'Plan jest już przetwarzany.')
                db.commit()
                return self.get(identifier)
            if not db.query(PlanWriteGateDB).filter_by(id=1, owner='').update({'owner': identifier}):
                raise ChatError(409, 'Inny zapis planu lub korekty czeka na potwierdzenie. Sprawdź historię.')
            if not db.query(RacePlanDraftDB).filter_by(id=identifier, status='preview').update({'status': 'writing'}):
                db.rollback()
                raise ChatError(409, 'Plan jest już przetwarzany.')
            db.commit()
        # No automatic replay after this durable claim, including process restarts.
        snapshot = self.source.correction_snapshot()
        calendar = self.source.race_calendar_snapshot()
        if (digest(snapshot) != payload['plan_version'] or digest(calendar) != payload['calendar_version']
                or self.preferences()['version'] != payload['preferences_version']
                or date.fromisoformat(payload['start']) <= self.now().date()):
            self._finish(identifier, 'stale')
            raise ChatError(409, 'Plan, kalendarz, preferencje lub data są nieaktualne. Przygotuj nowy podgląd.')
        try:
            self.source.write_generated_plan(snapshot, payload['after_snapshot'])
        except Exception:
            pass  # Reconcile even when the write succeeded but its response was lost.
        with self.factory() as db:
            return self._reconcile(db, db.get(RacePlanDraftDB, identifier))

    def _reconcile(self, db, record):
        payload = json.loads(record.payload)
        snapshot = self.source.correction_snapshot()
        if snapshot == payload['after_snapshot']:
            record.status = 'applied'
            db.query(PlanWriteGateDB).filter_by(id=1, owner=record.id).update({'owner': ''})
            db.commit()
            return self._view(record)
        raise ChatError(409, 'Wynik zapisu planu jest niepotwierdzony. Sprawdź ponownie tę samą wersję w historii. Kolejne zapisy są zablokowane do rozstrzygnięcia.')

    def _finish(self, identifier, status):
        with self.factory() as db:
            db.query(RacePlanDraftDB).filter_by(id=identifier).update({'status': status})
            db.query(PlanWriteGateDB).filter_by(id=1, owner=identifier).update({'owner': ''})
            db.commit()
