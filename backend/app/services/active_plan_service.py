import json
from sqlalchemy.exc import IntegrityError
from app.db.models import ActivePlanStateDB, RacePlanDraftDB, PlanWriteGateDB
from app.services.coach_errors import ChatError


def ensure_active(factory):
    with factory() as db:
        if not db.get(ActivePlanStateDB,1):
            latest=db.query(RacePlanDraftDB).filter_by(status='applied').order_by(RacePlanDraftDB.created_at.desc()).first()
            root=json.loads(latest.payload).get('campaign_id',latest.id) if latest else None
            db.add(ActivePlanStateDB(id=1,head_id=latest.id if latest else None,campaign_id=root,revision=0))
            try: db.commit()
            except IntegrityError: db.rollback()


def active_plan(factory):
    ensure_active(factory)
    with factory() as db:
        gate=db.get(PlanWriteGateDB,1)
        if gate and gate.owner:
            raise ChatError(409,'Zapis planu czeka na potwierdzenie. Sprawdź jego wynik przed przeglądem.')
        state=db.get(ActivePlanStateDB,1)
        if not state.head_id:
            raise ChatError(422,'Brak zaakceptowanego planu. Przegląd i adaptacja wymagają najpierw zapisanej wersji planu.')
        head=db.get(RacePlanDraftDB,state.head_id)
        return {'head_id':state.head_id,'campaign_id':state.campaign_id,'revision':state.revision,'plan':json.loads(head.payload)}


def set_active(db,record,payload):
    state=db.get(ActivePlanStateDB,1)
    state.head_id=record.id
    state.campaign_id=payload.get('campaign_id',record.id)
    state.revision+=1
