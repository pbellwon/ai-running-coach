"""Review an accepted campaign and propose bounded patches to that same campaign."""
from copy import deepcopy
from datetime import date,datetime,timedelta
import json
from zoneinfo import ZoneInfo
from sqlalchemy.exc import IntegrityError
from app.db.database import SessionLocal
from app.db.models import PlanExecutionReviewDB,RacePlanDraftDB,PlanCorrectionDB
from app.services.active_plan_service import active_plan
from app.services.plan_correction_service import digest
from app.services.race_plan_service import RacePlanService
from app.services.personal_plan_context import PersonalPlanContext
from app.services.plan_review_evidence import PlanReviewEvidence
from app.services.coach_errors import ChatError
from app.engine.plan_adaptation_engine import PlanAdaptationEngine
from app.engine.race_plan_engine import RacePlanEngine,MARKER,number,parse_calendar
from app.integrations.google_sheets_plan_source import GoogleSheetsPlanSource


def canonical(value):
    return json.loads(json.dumps(value,default=str))


class PlanReviewService:
    def __init__(self,source=None,session_factory=SessionLocal,now=None,athlete_context=None,evidence=None):
        self.source=source or GoogleSheetsPlanSource()
        self.factory=session_factory
        self.now=now or (lambda:datetime.now(ZoneInfo('Europe/Warsaw')))
        self.athlete=athlete_context or PersonalPlanContext(session_factory)
        self.evidence=evidence or PlanReviewEvidence(session_factory)

    def current(self):
        active=active_plan(self.factory)
        plan=active['plan']
        return {'head_id':active['head_id'],'campaign_id':active['campaign_id'],'start':plan.get('campaign_start',plan['start']),'end':plan.get('campaign_end',plan['end']),
                'goal':plan.get('long_term',{}).get('goal'),'cycles':plan.get('cycles',[])}

    def history(self):
        with self.factory() as db:
            return {'items':[json.loads(r.payload) for r in db.query(PlanExecutionReviewDB).order_by(PlanExecutionReviewDB.created_at.desc()).limit(30)]}

    def _capture(self,active,end):
        today=self.now().date()
        start=max(date.fromisoformat(active['plan'].get('campaign_start',active['plan']['start'])),end-timedelta(days=9))
        if end>=today or end<today-timedelta(days=28) or start>end:
            raise ChatError(422,'Wybierz zakończony dzień z ostatnich 28 dni, nie wcześniejszy niż początek planu.')
        athlete=self.athlete.capture(today)
        profile=athlete.get('facts',{}).get('profile',{})
        goal=active['plan'].get('long_term',{}).get('goal')
        if not goal or profile.get('goal')!=goal:
            raise ChatError(409,'Aktywny plan i potwierdzony cel nie są zgodne. Wybierz cel i zaakceptuj właściwy plan przed adaptacją.')
        calendar=self.source.race_calendar_snapshot()
        if goal not in parse_calendar(calendar):
            raise ChatError(409,'Cel zmienił się w kalendarzu. Najpierw potwierdź aktualny cel i plan.')
        baseline=deepcopy(active['plan']['after_snapshot'])
        with self.factory() as db:
            corrections=db.query(PlanCorrectionDB).filter_by(status='applied').order_by(PlanCorrectionDB.created_at).all()
            for correction in corrections:
                change=json.loads(correction.payload)
                index=change.get('row',0)-2
                if change.get('source')==baseline['source'] and 0<=index<len(baseline['rows']) and baseline['rows'][index]==change.get('before'):
                    baseline['rows'][index]=change['after']
        evidence=canonical(self.evidence.build(baseline,start,end,today))
        decision=PlanAdaptationEngine().evaluate(evidence,profile)
        return {'period_start':start.isoformat(),'period_end':end.isoformat(),'evidence':evidence,'assessment':decision,
                'athlete_version':athlete['version'],'calendar_version':digest(calendar),
                'evidence_version':digest(evidence),'goal':goal}

    def review(self,identifier,period_end=None):
        request_hash=digest([period_end])
        with self.factory() as db:
            old=db.get(PlanExecutionReviewDB,identifier)
            if old:
                if old.request_hash!=request_hash: raise ChatError(409,'Identyfikator przeglądu ma inną treść.')
                return json.loads(old.payload)
        active=active_plan(self.factory)
        today=self.now().date()
        completed=[c['end'] for c in active['plan'].get('cycles',[]) if c['end']<today.isoformat()]
        end=date.fromisoformat(period_end) if period_end else date.fromisoformat(max(completed)) if completed else today-timedelta(days=1)
        result=self._capture(active,end)
        result.update(id=identifier,head_id=active['head_id'],campaign_id=active['campaign_id'],created_at=self.now().isoformat(),
                      review_kind='10-day-execution-review')
        with self.factory() as db:
            db.add(PlanExecutionReviewDB(id=identifier,request_hash=request_hash,payload=json.dumps(result),created_at=self.now().replace(tzinfo=None)))
            try: db.commit()
            except IntegrityError:
                db.rollback()
                return self.review(identifier,period_end)
        return result

    def _review(self,identifier):
        with self.factory() as db:
            row=db.get(PlanExecutionReviewDB,identifier)
            if not row: raise ChatError(404,'Nie znaleziono przeglądu.')
            return json.loads(row.payload)

    def validate_patch(self,payload):
        active=active_plan_for_validation(self.factory)
        if active['head_id']!=payload['parent_plan_id'] or active['campaign_id']!=payload['campaign_id']:
            raise ChatError(409,'Plan zmienił wersję po podglądzie korekty. Wykonaj nowy przegląd.')
        fresh=self._capture(active,date.fromisoformat(payload['review_period_end']))
        if fresh['evidence_version']!=payload['review_evidence_version']:
            raise ChatError(409,'Wykonania lub regeneracja zmieniły się po przeglądzie. Przygotuj nową korektę.')

    def propose(self,identifier,review_id,scope):
        if scope not in ('unit','cycle','block'):
            raise ChatError(422,'Nieobsługiwany zakres korekty.')
        request_hash=digest(['adaptation',review_id,scope])
        with self.factory() as db:
            old=db.get(RacePlanDraftDB,identifier)
            if old:
                if old.request_hash!=request_hash: raise ChatError(409,'Identyfikator korekty ma inną treść.')
                return RacePlanService._view(old)
            protected={json.loads(p.payload)['row'] for p in db.query(PlanCorrectionDB).filter_by(status='applied')}
        active=active_plan(self.factory)
        review=self._review(review_id)
        if active['head_id']!=review['head_id']: raise ChatError(409,'Ten przegląd dotyczy wcześniejszej wersji planu.')
        fresh=self._capture(active,date.fromisoformat(review['period_end']))
        if any(fresh[k]!=review[k] for k in ('athlete_version','calendar_version','evidence_version')):
            raise ChatError(409,'Dane zmieniły się po przeglądzie. Odśwież ocenę przed korektą.')
        if not review['assessment']['can_propose']:
            raise ChatError(409,'Przegląd nie uzasadnia automatycznej propozycji zmian. Sprawdź ocenę i ograniczenia.')
        if active['plan']['calendar_version']!=fresh['calendar_version']:
            raise ChatError(409,'Kalendarz zmienił się od zaakceptowania planu. Uzgodnij nowy kalendarz przed adaptacją.')
        before=self.source.correction_snapshot()
        after=deepcopy(before)
        baseline=active['plan']['after_snapshot']
        if before['source']!=baseline['source'] or before['headers']!=baseline['headers']:
            raise ChatError(409,'Źródło lub kolumny planu zmieniły się.')
        today=self.now().date()
        start=today+timedelta(days=1)
        end=min(date.fromisoformat(active['plan'].get('campaign_end',active['plan']['end'])),start+timedelta(days=29 if scope=='block' else 9))
        if start>end: raise ChatError(409,'Plan nie ma przyszłych dni do korekty.')
        events=parse_calendar(self.source.race_calendar_snapshot())
        race_dates={e['date'] for e in events}
        patches=[];skipped=[]
        for index,expected in enumerate(baseline['rows'],2):
            if not start.isoformat()<=expected.get('date','')<=end.isoformat(): continue
            actual=before['rows'][index-2] if len(before['rows'])>=index-1 else None
            if actual is None or any(actual.get(k)!=expected.get(k) for k in ('date','title','description','planned_distance_km','planned_duration_min')):
                skipped.append(f"Wiersz {index}: ręcznie zmieniona jednostka pozostaje zachowana.");continue
            if index in protected or RacePlanEngine._protected_description(actual['description']) or actual['date'] in race_dates:
                skipped.append(f"{actual['date']}: zawody lub chroniona korekta pozostają bez zmian.");continue
            if sum(r.get('date')==actual['date'] for r in before['rows'])>1:
                skipped.append(f"{actual['date']}: kilka jednostek tego dnia pozostaje bez zmian.");continue
            kind=RacePlanEngine._type(actual)
            if kind in ('off','race','strength','mobility'): continue
            if review['assessment']['decision']=='easy' and kind not in ('threshold','vo2max','tempo_run','long_run','threshold+vo2max'): continue
            km=number(actual['planned_distance_km']) if actual['planned_distance_km'] else None
            minutes=number(actual['planned_duration_min']) if actual['planned_duration_min'] else None
            if km is None and minutes is None: continue
            factor=.8 if review['assessment']['decision']=='reduce' else .7
            changed=dict(actual)
            changed['title']='Spokojny bieg po korekcie'
            changed['planned_distance_km']=f'{round(km*factor,1):g}' if km is not None else ''
            changed['planned_duration_min']=str(max(1,round(minutes*factor))) if minutes is not None else ''
            prescription=f"Spokojny bieg w tempie konwersacyjnym, bez akcentów. Dystans: {changed['planned_distance_km'] or 'nie określono'} km; czas: {changed['planned_duration_min'] or 'nie określono'} min."
            note=f"PaceMind {today} | Zmiana: adaptacja istniejącego planu, objętość i charakter jednostki. Uzasadnienie: {review['assessment']['reason']} Cel A: {fresh['goal']['name']}."
            changed['description']=actual['description']+MARKER+prescription+'\n'+note
            if len(changed['description'])>50000: raise ChatError(422,'Opis wraz z historią przekracza limit arkusza.')
            after['rows'][index-2]=changed
            patches.append({'row':index,'action':'replace','before':actual,'after':changed,'phase':review['assessment']['reason']})
            if scope=='unit': break
        payload=deepcopy(active['plan'])
        payload.update(id=identifier,planning_mode='adaptation-10-day-v1',campaign_id=active['campaign_id'],parent_plan_id=active['head_id'],
            review_id=review_id,review_period_end=review['period_end'],review_evidence_version=review['evidence_version'],scope=scope,
            start=start.isoformat(),end=end.isoformat(),created_at=self.now().isoformat(),before_snapshot=before,after_snapshot=after,
            plan_version=digest(before),calendar_version=fresh['calendar_version'],athlete_version=fresh['athlete_version'],
            entries=patches,can_accept=bool(patches),blockers=[] if patches else ['W tym zakresie nie ma jednostek możliwych do bezpiecznej korekty.'],
            warnings=skipped,summary={'added':0,'replaced':len(patches),'kept':len(skipped)},
            adaptation_assessment=review['assessment'])
        # Keep the original campaign horizon and phases even though only a bounded patch is applied.
        payload['campaign_start']=active['plan'].get('campaign_start',active['plan']['start'])
        payload['campaign_end']=active['plan'].get('campaign_end',active['plan']['end'])
        for cycle in payload.get('cycles',[]):
            cycle['planned_km']=round(sum(number(r['planned_distance_km'] or 0) for r in after['rows'] if cycle['start']<=r.get('date','')<=cycle['end']),1)
            if any(cycle['start']<=e['after']['date']<=cycle['end'] for e in patches):
                cycle['threshold_work_min']=None
        with self.factory() as db:
            record=RacePlanDraftDB(id=identifier,request_hash=request_hash,payload=json.dumps(payload),status='preview',created_at=self.now().replace(tzinfo=None))
            db.add(record)
            try: db.commit()
            except IntegrityError:
                db.rollback();return self.propose(identifier,review_id,scope)
            return RacePlanService._view(record)


def active_plan_for_validation(factory):
    # Writer owns the shared gate here; read the head without rejecting its own in-flight write.
    from app.db.models import ActivePlanStateDB
    with factory() as db:
        state=db.get(ActivePlanStateDB,1)
        row=db.get(RacePlanDraftDB,state.head_id)
        return {'head_id':state.head_id,'campaign_id':state.campaign_id,'revision':state.revision,'plan':json.loads(row.payload)}
