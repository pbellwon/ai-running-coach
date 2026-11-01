"""Reviewed, durable single-workout changes. No calendar plan generation."""
import hashlib
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from app.db.database import SessionLocal
from app.db.models import PlanCorrectionDB, PlanWriteGateDB
from app.integrations.google_sheets_plan_source import GoogleSheetsPlanSource
from app.services.coach_chat_service import ChatError

FIELDS = ('title', 'planned_distance_km', 'planned_duration_min', 'description')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class PlanCorrectionService:
    def __init__(self, source=None, session_factory=SessionLocal, now=None):
        self.source = source or GoogleSheetsPlanSource()
        self.factory = session_factory
        self.now = now or (lambda: datetime.now(ZoneInfo('Europe/Warsaw')))

    def plan(self):
        snapshot = self.source.correction_snapshot()
        today = self.now().date().isoformat()
        return {'version': digest(snapshot), 'items': [
            {**row, 'row': i + 2} for i, row in enumerate(snapshot['rows'])
            if row.get('date', '') >= today]}

    def history(self):
        with self.factory() as db:
            return {'items': [json.loads(x.payload) | {'status': x.status}
                for x in db.query(PlanCorrectionDB).order_by(PlanCorrectionDB.created_at.desc()).limit(100)]}

    def preview(self, request_id, version, row_number, change, reason):
        request_hash = digest([version, row_number, change, reason])
        with self.factory() as db:
            previous = db.get(PlanCorrectionDB, request_id)
            if previous:
                if previous.request_hash != request_hash:
                    raise ChatError(409, 'Ten identyfikator jest już użyty dla innej korekty.')
                return json.loads(previous.payload) | {'status': previous.status}
        snapshot = self.source.correction_snapshot()
        if digest(snapshot) != version:
            raise ChatError(409, 'Plan zmienił się. Wczytaj go i przygotuj nowy podgląd.')
        if not 2 <= row_number <= len(snapshot['rows']) + 1:
            raise ChatError(404, 'Nie znaleziono treningu.')
        before = snapshot['rows'][row_number - 2]
        if before.get('date', '') < self.now().date().isoformat():
            raise ChatError(409, 'Nie można zmieniać minionych treningów.')
        if not set(FIELDS).issubset(before):
            raise ChatError(409, 'Plan nie ma wymaganych kolumn.')
        after = dict(before)
        after.update({k: str(change[k]) if change[k] is not None else '' for k in FIELDS if k != 'description'})
        prescription = change['description'].strip()
        reason = reason.strip()
        labels = {'title': 'tytuł', 'planned_distance_km': 'dystans', 'planned_duration_min': 'czas'}
        scope = ', '.join(labels[k] for k in labels if before[k] != after[k])
        scope = (scope + ', opis treningu').lstrip(', ')
        note = f"PaceMind {self.now().date().isoformat()} | Zmiana: {scope}. Uzasadnienie: {reason}"
        # Keep all previous notes and prescriptions verbatim, including other people's comments.
        after['description'] = before['description'] + '\n\nObowiązujący trening po korekcie PaceMind:\n' + prescription + '\n' + note
        payload = {'id': request_id, 'row': row_number, 'before': before, 'after': after,
                   'reason': reason, 'created_at': self.now().isoformat(), 'version': version,
                   'source': snapshot['source']}
        with self.factory() as db:
            db.add(PlanCorrectionDB(id=request_id, request_hash=request_hash, payload=json.dumps(payload),
                                   status='preview', created_at=self.now().replace(tzinfo=None)))
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                return self.preview(request_id, version, row_number, change, reason)
        return payload | {'status': 'preview'}

    def decide(self, correction_id, accept):
        # Permanent claim: a timed-out or crashed writer is never automatically replayed.
        with self.factory() as db:
            if not db.get(PlanWriteGateDB, 1):
                db.add(PlanWriteGateDB(id=1, owner=''))
                try:
                    db.commit()
                except IntegrityError:
                    db.rollback()
        with self.factory() as db:
            item = db.get(PlanCorrectionDB, correction_id)
            if not item:
                raise ChatError(404, 'Nie znaleziono korekty.')
            payload = json.loads(item.payload)
            if item.status in ('applied', 'rejected'):
                if (item.status == 'applied') != accept:
                    raise ChatError(409, 'Korekta ma już inną decyzję.')
                return payload | {'status': item.status}
            if item.status == 'writing':
                if not accept:
                    raise ChatError(409, 'Zapis już rozpoczęty. Sprawdź jego wynik.')
                return self._reconcile(db, item, payload)
            if item.status != 'preview':
                raise ChatError(409, 'Plan zmienił się. Przygotuj nową korektę.')
            if not accept:
                changed = db.query(PlanCorrectionDB).filter_by(id=correction_id, status='preview').update({'status': 'rejected'})
                if not changed:
                    db.rollback()
                    raise ChatError(409, 'Korekta jest już przetwarzana.')
                db.commit()
                return payload | {'status': 'rejected'}
            acquired = db.query(PlanWriteGateDB).filter_by(id=1, owner='').update({'owner': correction_id})
            if not acquired:
                raise ChatError(409, 'Inny zapis oczekuje na potwierdzenie. Sprawdź historię korekt.')
            claimed = db.query(PlanCorrectionDB).filter_by(id=correction_id, status='preview').update({'status': 'writing'})
            if not claimed:
                db.rollback()
                raise ChatError(409, 'Korekta jest już przetwarzana.')
            db.commit()
        # Check freshness after claiming the global writer gate, immediately before mutation.
        snapshot = self.source.correction_snapshot()
        if digest(snapshot) != payload['version'] or payload['before']['date'] < self.now().date().isoformat():
            self._finish(correction_id, 'stale')
            raise ChatError(409, 'Plan zmienił się lub trening jest miniony. Przygotuj nowy podgląd.')
        try:
            self.source.write_correction(snapshot, payload['row'], payload['before'], payload['after'])
        except Exception:
            # Includes an ambiguous transport error after a successful remote update.
            pass
        with self.factory() as db:
            return self._reconcile(db, db.get(PlanCorrectionDB, correction_id), payload)

    def _reconcile(self, db, item, payload):
        snapshot = self.source.correction_snapshot()
        rows = snapshot['rows']
        if (snapshot['source'] == payload['source'] and len(rows) >= payload['row'] - 1
                and rows[payload['row'] - 2] == payload['after']):
            item.status = 'applied'
            db.query(PlanWriteGateDB).filter_by(id=1, owner=item.id).update({'owner': ''})
            db.commit()
            return payload | {'status': 'applied'}
        raise ChatError(409, 'Wynik zapisu nie jest potwierdzony. Ponów sprawdzenie tej korekty; nie twórz nowego zapisu. W razie trwałego błędu potrzebna jest weryfikacja arkusza przez administratora.')

    def _finish(self, correction_id, status):
        with self.factory() as db:
            db.query(PlanCorrectionDB).filter_by(id=correction_id).update({'status': status})
            db.query(PlanWriteGateDB).filter_by(id=1, owner=correction_id).update({'owner': ''})
            db.commit()
