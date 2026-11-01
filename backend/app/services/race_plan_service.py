"""Persistent full-plan previews sharing the single-workout Sheets writer gate."""
from copy import deepcopy
from datetime import date, datetime, timedelta
import json
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from app.db.database import SessionLocal
from app.db.models import RacePlanDraftDB, PlanWriteGateDB, PlanCorrectionDB
from app.engine.race_plan_engine import RacePlanEngine, parse_calendar
from app.integrations.google_sheets_plan_source import GoogleSheetsPlanSource
from app.services.coach_chat_service import ChatError
from app.services.plan_correction_service import digest
from app.services.personal_plan_context import PersonalPlanContext
from app.services.personal_plan_coach import PersonalPlanCoach, planning_attempt
from app.services.recent_execution_review_service import RecentExecutionReviewService


class RacePlanService:
    def __init__(self, source=None, session_factory=SessionLocal, now=None, athlete_context=None, coach=None):
        self.source = source or GoogleSheetsPlanSource()
        self.factory = session_factory
        self.athlete_context = athlete_context or PersonalPlanContext(session_factory)
        self.coach = coach or PersonalPlanCoach()
        self.now = now or (lambda: datetime.now(ZoneInfo('Europe/Warsaw')))

    def context(self):
        snapshot = self.source.correction_snapshot()
        calendar = self.source.race_calendar_snapshot()
        races = parse_calendar(calendar)
        today = self.now().date()
        future = [e for e in races if e['date'] > today.isoformat()]
        next_a = next((e for e in future if e['priority'] == 'A'), None)
        athlete = self.athlete_context.capture(today)
        return {'plan_version': digest(snapshot), 'calendar_version': digest(calendar), 'athlete_version': athlete['version'],
                'races': future, 'cycle_days': 10, 'sources': athlete['sources'], 'limitations': athlete['limitations'],
                'default_start': (today + timedelta(days=1)).isoformat(),
                'default_end': (date.fromisoformat(next_a['date']) + timedelta(days=7)).isoformat() if next_a else None}

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
        return {k: v for k, v in payload.items() if k not in ('before_snapshot', 'after_snapshot', 'athlete_context')} | {'status': record.status}

    def preview(self, identifier, request):
        request_hash = digest(request)
        with self.factory() as db:
            previous = db.get(RacePlanDraftDB, identifier)
            if previous:
                if previous.request_hash != request_hash:
                    raise ChatError(409, 'Identyfikator został już użyty do innego planu.')
                return self._view(previous)
            protected = {json.loads(c.payload)['row'] for c in db.query(PlanCorrectionDB).filter_by(status='applied')}
        athlete = self.athlete_context.capture(self.now().date())
        snapshot = self.source.correction_snapshot()
        calendar = self.source.race_calendar_snapshot()
        if (digest(snapshot) != request['plan_version'] or digest(calendar) != request['calendar_version']
                or athlete['version'] != request['athlete_version']):
            raise ChatError(409, 'Plan, kalendarz lub informacje o zawodniku zmieniły się. Wczytaj aktualne dane.')
        events = parse_calendar(calendar)
        start, end = date.fromisoformat(request['start']), date.fromisoformat(request['end'])
        if start <= self.now().date() or end < start or (end-start).days > 365 or (start-self.now().date()).days > 30:
            raise ChatError(422, 'Wybierz przyszły zakres do 366 dni, rozpoczynający się najwyżej 30 dni naprzód.')
        if not any(e['priority'] == 'A' and start.isoformat() <= e['date'] <= end.isoformat() for e in events):
            raise ChatError(422, 'W okresie planu musi być start główny A.')
        with planning_attempt(self.factory) as check:
            # Recheck after acquiring the shared paid-AI gate: a retried request may already be saved.
            with self.factory() as db:
                previous = db.get(RacePlanDraftDB, identifier)
                if previous:
                    if previous.request_hash != request_hash:
                        raise ChatError(409, 'Identyfikator został już użyty.')
                    return self._view(previous)
            class Snapshot:
                def fetch_rows(self):
                    return snapshot['rows']
            try:
                athlete['facts']['execution_reviews'] = RecentExecutionReviewService(
                    session_factory=self.factory, plan_source=Snapshot()).build(target_date=self.now().date(), limit=20)
                if athlete['facts']['execution_reviews']:
                    athlete['sources'].append({'id': 'reviews', 'label': 'Oceny wykonania ostatnich 20 jednostek'})
                else:
                    athlete['limitations'].append('Brak zapisanych ocen wykonania; trener korzysta z historii i dostępnych odczuć.')
            except Exception:
                athlete['limitations'].append('Oceny wykonania są niedostępne; trener ma tylko zapisy treningów i feedback.')
            check(renew=True)
            strategy = self.coach.propose(athlete, events, request.get('note', ''))
            check()
            if strategy['status'] == 'ready':
                result = RacePlanEngine().build(snapshot, events, strategy, start, end,
                    request['replace_existing'], protected, self.now().date(), athlete['limits'])
            else:
                result = {'entries': [], 'cycles': [], 'weeks': [], 'warnings': [], 'blockers': strategy['questions'],
                          'races': events, 'can_accept': False, 'cycle_days': 10}
            result['coaching'] = strategy
            result['sources'] = athlete['sources']
            result['limitations'] = athlete['limitations']
            after = deepcopy(snapshot)
            for entry in result['entries']:
                if entry['action'] == 'replace':
                    after['rows'][entry['row'] - 2] = entry['after']
                elif entry['action'] == 'add':
                    after['rows'].append(entry['after'])
                    entry['row'] = len(after['rows']) + 1
            changes = sum(e['action'] != 'keep' for e in result['entries'])
            if not changes and strategy['status'] == 'ready':
                result['blockers'].append('W tym zakresie nie ma zmian do zapisania. Wydłuż okres lub wybierz przebudowę niechronionych jednostek.')
                result['can_accept'] = False
            payload = {**request, **result, 'id': identifier, 'created_at': self.now().isoformat(),
                       'planning_mode': 'personal-10-day', 'athlete_context': athlete, 'before_snapshot': snapshot, 'after_snapshot': after,
                       'summary': {'added': sum(e['action'] == 'add' for e in result['entries']),
                                   'replaced': sum(e['action'] == 'replace' for e in result['entries']),
                                   'kept': sum(e['action'] == 'keep' for e in result['entries'])}}
            with self.factory() as db:
                record = RacePlanDraftDB(id=identifier, request_hash=request_hash, payload=json.dumps(payload),
                                        status='preview', created_at=self.now().replace(tzinfo=None))
                db.add(record)
                try:
                    check()
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    existing = db.get(RacePlanDraftDB, identifier)
                    if not existing or existing.request_hash != request_hash:
                        raise ChatError(409, 'Identyfikator został już użyty.')
                    return self._view(existing)
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
            if accept and payload.get('planning_mode') != 'personal-10-day':
                raise ChatError(409, 'To podgląd ze starego generatora tygodniowego. Przygotuj nową propozycję w cyklu 10-dniowym.')
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
                or self.athlete_context.capture(self.now().date())['version'] != payload['athlete_version']
                or date.fromisoformat(payload['start']) <= self.now().date()):
            self._finish(identifier, 'stale')
            raise ChatError(409, 'Plan, kalendarz, dane zawodnika lub data są nieaktualne. Przygotuj nowy podgląd.')
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
