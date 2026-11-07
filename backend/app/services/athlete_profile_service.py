"""Confirmed athlete knowledge, immutable revisions, and one selected primary race."""
from datetime import date, datetime, timezone
import hashlib
import json
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from app.db.database import SessionLocal
from app.db.models import AthleteProfileStateDB, AthleteMemoryDB, AthleteMemoryDetailsDB, AthleteProfileProposalDB, CoachChatTurnDB
from app.integrations.google_sheets_plan_source import GoogleSheetsPlanSource
from app.engine.race_plan_engine import parse_calendar
from app.services.coach_errors import ChatError


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def memory_record(item, detail=None):
    return {'id': item.id, 'category': item.category, 'text': item.memory_text, 'source': item.source,
            'confidence': item.confidence, 'active': item.is_active, 'created_at': item.created_at.isoformat(),
            'status': detail.status if detail else 'unreviewed', 'observed_on': detail.observed_on if detail else None,
            'source_turn_id': detail.source_turn_id if detail else None, 'source_quote': detail.source_quote if detail else None,
            'supersedes_id': detail.supersedes_id if detail else None,
            'confirmed_at': detail.confirmed_at.isoformat() if detail else None}


class AthleteProfileService:
    def __init__(self, session_factory=SessionLocal, source=None, today=None):
        self.factory, self.source = session_factory, source
        self.today = today or (lambda: datetime.now(ZoneInfo('Europe/Warsaw')).date())

    @staticmethod
    def now():
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def ensure(self):
        with self.factory() as db:
            if not db.get(AthleteProfileStateDB, 1):
                db.add(AthleteProfileStateDB(id=1, revision=0, goal_json=None,
                    cycle_json=json.dumps({'cycle_days': 10, 'anchor_date': None}), updated_at=self.now()))
                try:
                    db.commit()
                except IntegrityError:
                    db.rollback()

    def _snapshot(self, db, state=None, history=False):
        state = state or db.get(AthleteProfileStateDB, 1)
        rows = db.query(AthleteMemoryDB).order_by(AthleteMemoryDB.id).all()
        details = {d.memory_id: d for d in db.query(AthleteMemoryDetailsDB).all()}
        active = [memory_record(m, details.get(m.id)) for m in rows if m.is_active]
        base = {'revision': state.revision, 'goal': json.loads(state.goal_json) if state.goal_json else None,
                'cycle': json.loads(state.cycle_json), 'memory': active}
        result = base | {'version': fingerprint(base)}
        if history:
            result['memory_history'] = [memory_record(m, details.get(m.id)) for m in rows if not m.is_active]
            result['proposals'] = [self._proposal(p) for p in db.query(AthleteProfileProposalDB)
                .order_by(AthleteProfileProposalDB.created_at.desc()).limit(50)]
        anchor = base['cycle'].get('anchor_date')
        result['today'] = self.today().isoformat()
        result['cycle_day'] = (self.today()-date.fromisoformat(anchor)).days % 10 + 1 if anchor and anchor <= self.today().isoformat() else None
        return result

    def snapshot(self, history=False):
        self.ensure()
        with self.factory() as db:
            return self._snapshot(db, history=history)

    def calendar(self):
        source = self.source or GoogleSheetsPlanSource()
        snapshot = source.race_calendar_snapshot()
        events = [e for e in parse_calendar(snapshot) if e['date'] >= self.today().isoformat()]
        return {'version': fingerprint(snapshot), 'items': [dict(e, key=fingerprint(e)) for e in events if e['priority'] == 'A']}

    @staticmethod
    def _proposal(record):
        return json.loads(record.payload) | {'id': record.id, 'status': record.status,
                'created_at': record.created_at.isoformat(), 'decided_at': record.decided_at.isoformat() if record.decided_at else None,
                'result': json.loads(record.result_json) if record.result_json else None}

    def for_turn(self, turn_id):
        with self.factory() as db:
            return [self._proposal(p) for p in db.query(AthleteProfileProposalDB).filter_by(source_turn_id=turn_id).order_by(AthleteProfileProposalDB.created_at)]

    def propose(self, identifier, version, change, source_turn_id=None, quote=None):
        self.ensure()
        request_hash = fingerprint([version, change, source_turn_id, quote])
        with self.factory() as db:
            previous = db.get(AthleteProfileProposalDB, identifier)
            if previous:
                if previous.request_hash != request_hash:
                    raise ChatError(409, 'Identyfikator jest już użyty do innego ustalenia.')
                return self._proposal(previous)
        # Only a new goal proposal needs a remote calendar read.
        if change['kind'] == 'goal':
            calendar = self.calendar()
            if calendar['version'] != change['calendar_version']:
                raise ChatError(409, 'Kalendarz zmienił się. Wczytaj starty ponownie.')
            selected = next((e for e in calendar['items'] if e['key'] == change['race_key']), None)
            if not selected:
                raise ChatError(422, 'Wybierz przyszły start główny A.')
            change = dict(change, race={k: v for k, v in selected.items() if k != 'key'})
        with self.factory() as db:
            previous = db.get(AthleteProfileProposalDB, identifier)
            if previous:
                if previous.request_hash != request_hash:
                    raise ChatError(409, 'Identyfikator jest już użyty do innego ustalenia.')
                return self._proposal(previous)
            result = self.stage(db, identifier, version, change, source_turn_id, quote, request_hash)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                existing = db.get(AthleteProfileProposalDB, identifier)
                if not existing or existing.request_hash != request_hash:
                    raise ChatError(409, 'Identyfikator jest już użyty.')
                return self._proposal(existing)
            return result

    def stage(self, db, identifier, version, change, source_turn_id=None, quote=None, request_hash=None):
        current = self._snapshot(db)
        if current['version'] != version:
            raise ChatError(409, 'Pamięć lub cel zmieniły się. Wczytaj aktualny profil.')
        if source_turn_id:
            turn = db.get(CoachChatTurnDB, source_turn_id)
            if not turn or turn.status != 'completed' or not quote or quote not in turn.message:
                raise ChatError(422, 'Źródłem ustalenia musi być dokładny cytat z Twojej zapisanej wiadomości.')
        kind = change['kind']
        before = None
        if kind == 'memory':
            if change.get('replace_id'):
                before = next((m for m in current['memory'] if m['id'] == change['replace_id']), None)
                if not before:
                    raise ChatError(409, 'Poprzednia wersja informacji nie jest już aktualna.')
            after = {k: v for k, v in change.items() if k not in ('kind', 'replace_id')}
        elif kind == 'cycle':
            before, after = current['cycle'], {'cycle_days': 10, 'anchor_date': change.get('anchor_date')}
        elif kind == 'goal':
            before, after = current['goal'], change['race']
        else:
            raise ChatError(422, 'Nieobsługiwany rodzaj ustalenia.')
        payload = {'base_version': version, 'change': change, 'before': before, 'after': after,
                   'source_turn_id': source_turn_id, 'quote': quote}
        record = AthleteProfileProposalDB(id=identifier, request_hash=request_hash or fingerprint([version, change, source_turn_id, quote]),
            payload=json.dumps(payload), status='pending', source_turn_id=source_turn_id, created_at=self.now())
        db.add(record)
        return self._proposal(record)

    def decide(self, identifier, accept):
        self.ensure()
        with self.factory() as db:
            record = db.get(AthleteProfileProposalDB, identifier)
            if not record:
                raise ChatError(404, 'Nie znaleziono ustalenia.')
            payload = json.loads(record.payload)
            if record.status != 'pending':
                if (record.status == 'applied') != accept:
                    raise ChatError(409, 'To ustalenie ma już inną decyzję.')
                return self._proposal(record)
        if accept and payload['change']['kind'] == 'goal':
            if self.calendar()['version'] != payload['change']['calendar_version']:
                raise ChatError(409, 'Kalendarz zmienił się od podglądu. Wybierz cel ponownie.')
        with self.factory() as db:
            record = db.get(AthleteProfileProposalDB, identifier)
            state = db.get(AthleteProfileStateDB, 1)
            current = self._snapshot(db, state)
            if accept and current['version'] != payload['base_version']:
                raise ChatError(409, 'Profil zmienił się od podglądu. Przygotuj nowe ustalenie.')
            if accept and not db.query(AthleteProfileStateDB).filter_by(id=1, revision=state.revision).update({'revision': state.revision+1}):
                raise ChatError(409, 'Inny zapis profilu jest w toku. Wczytaj profil ponownie.')
            if not db.query(AthleteProfileProposalDB).filter_by(id=identifier, status='pending').update({'status': 'applied' if accept else 'rejected'}):
                db.rollback()
                return self.decide(identifier, accept)
            if accept:
                change = payload['change']
                if change['kind'] == 'memory':
                    old_id = change.get('replace_id')
                    if old_id:
                        db.query(AthleteMemoryDB).filter_by(id=old_id, is_active=True).update({'is_active': False, 'updated_at': self.now()})
                    item = AthleteMemoryDB(category=change['category'], memory_text=change['text'], source='athlete_confirmed',
                        confidence=None, is_active=True, created_at=self.now(), updated_at=self.now())
                    db.add(item)
                    db.flush()
                    db.add(AthleteMemoryDetailsDB(memory_id=item.id, status=change['fact_status'], observed_on=change['observed_on'],
                        source_turn_id=payload['source_turn_id'], source_quote=payload['quote'], supersedes_id=old_id, confirmed_at=self.now()))
                    record.result_json = json.dumps({'memory_id': item.id})
                elif change['kind'] == 'goal':
                    state.goal_json = json.dumps(payload['after'])
                else:
                    state.cycle_json = json.dumps(payload['after'])
            if accept:
                state.updated_at = self.now()
            record.decided_at = self.now()
            db.commit()
            return self._proposal(record)
