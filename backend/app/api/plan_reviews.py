from datetime import date
from typing import Literal
from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel
from app.api.coach_chat import require_chat_access
from app.api.race_plans import call
from app.services.plan_review_service import PlanReviewService
from app.services.race_plan_service import RacePlanService

router=APIRouter(prefix='/coach/plan-reviews',tags=['plan-reviews'],dependencies=[Depends(require_chat_access)])


class ReviewRequest(BaseModel):
    id: UUID
    period_end: date | None = None


class PatchRequest(BaseModel):
    id: UUID
    review_id: UUID
    scope: Literal['unit','cycle','block']='cycle'


class Decision(BaseModel):
    decision: Literal['accept','reject']


def service(): return PlanReviewService()


@router.get('/current')
def current(svc=Depends(service)): return call(svc.current)


@router.get('')
def history(svc=Depends(service)): return call(svc.history)


@router.post('')
def review(payload:ReviewRequest,svc=Depends(service)):
    return call(svc.review,str(payload.id),payload.period_end.isoformat() if payload.period_end else None)


@router.post('/proposals')
def propose(payload:PatchRequest,svc=Depends(service)):
    return call(svc.propose,str(payload.id),str(payload.review_id),payload.scope)


@router.post('/proposals/{identifier}/decision')
def decide(identifier:UUID,payload:Decision,svc=Depends(service)):
    writer=RacePlanService(svc.source,svc.factory,now=svc.now,athlete_context=svc.athlete)
    return call(writer.decide,str(identifier),payload.decision=='accept')
