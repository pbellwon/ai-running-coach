"""Owner-authorized review and explicit acceptance of existing plan corrections."""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict, model_validator
from app.api.coach_chat import require_chat_access
from app.services.plan_correction_service import PlanCorrectionService
from app.services.coach_chat_service import ChatError

router = APIRouter(prefix='/coach/corrections', tags=['plan-corrections'],
                   dependencies=[Depends(require_chat_access)])


class Change(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    title: str = Field(min_length=1, max_length=200)
    planned_distance_km: float | None = Field(default=None, ge=0, le=300)
    planned_duration_min: int | None = Field(default=None, ge=0, le=2000)
    description: str = Field(min_length=1, max_length=4000)

    @model_validator(mode='after')
    def trim(self):
        self.title, self.description = self.title.strip(), self.description.strip()
        if not self.title or not self.description:
            raise ValueError('Podaj tytuł i konkretny przebieg treningu.')
        return self


class Preview(BaseModel):
    id: UUID
    version: str = Field(min_length=64, max_length=64)
    row: int = Field(ge=2)
    change: Change
    reason: str = Field(min_length=1, max_length=1000)

    @model_validator(mode='after')
    def trim(self):
        self.reason = self.reason.strip()
        if not self.reason:
            raise ValueError('Podaj uzasadnienie korekty.')
        return self


class Decision(BaseModel):
    decision: Literal['accept', 'reject']


def service():
    return PlanCorrectionService()


def call(fn, *args):
    try:
        return fn(*args)
    except ChatError as exc:
        raise HTTPException(exc.status, exc.message) from exc
    except Exception as exc:
        raise HTTPException(503, 'Arkusz jest niedostępny. Sprawdź historię i ponów tę samą operację.') from exc


@router.get('/plan')
def plan(svc=Depends(service)):
    return call(svc.plan)


@router.get('')
def history(svc=Depends(service)):
    return call(svc.history)


@router.post('/preview')
def preview(payload: Preview, svc=Depends(service)):
    return call(svc.preview, str(payload.id), payload.version, payload.row,
                payload.change.model_dump(), payload.reason)


@router.post('/{correction_id}/decision')
def decide(correction_id: UUID, payload: Decision, svc=Depends(service)):
    return call(svc.decide, str(correction_id), payload.decision == 'accept')
