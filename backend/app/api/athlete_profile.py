from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from gspread.exceptions import WorksheetNotFound
from pydantic import BaseModel, Field, model_validator
from app.api.coach_chat import require_chat_access
from app.models.profile_changes import ProfileChange
from app.services.athlete_profile_service import AthleteProfileService
from app.services.coach_errors import ChatError

router = APIRouter(prefix='/coach/profile', tags=['athlete-profile'], dependencies=[Depends(require_chat_access)])


class ProposalRequest(BaseModel):
    id: UUID
    version: str = Field(min_length=64, max_length=64)
    change: ProfileChange
    source_turn_id: UUID | None = None
    quote: str | None = Field(default=None, min_length=3, max_length=2000)

    @model_validator(mode='after')
    def bind_source(self):
        if bool(self.source_turn_id) != bool(self.quote):
            raise ValueError('Cytat i identyfikator wiadomości muszą wskazywać wspólne źródło.')
        return self


class Decision(BaseModel):
    decision: Literal['accept', 'reject']


def service():
    return AthleteProfileService()


def call(fn, *args):
    try:
        return fn(*args)
    except ChatError as exc:
        raise HTTPException(exc.status, exc.message) from exc
    except WorksheetNotFound as exc:
        raise HTTPException(422, 'Nie znaleziono zakładki race_calendar.') from exc
    except Exception as exc:
        raise HTTPException(503, 'Profil jest chwilowo niedostępny. Ponów tę samą operację.') from exc


@router.get('')
def profile(svc=Depends(service)):
    return call(svc.snapshot, True)


@router.get('/calendar')
def calendar(svc=Depends(service)):
    return call(svc.calendar)


@router.post('/proposals')
def propose(payload: ProposalRequest, svc=Depends(service)):
    return call(svc.propose, str(payload.id), payload.version, payload.change.model_dump(mode='json'),
                str(payload.source_turn_id) if payload.source_turn_id else None, payload.quote)


@router.post('/proposals/{identifier}/decision')
def decide(identifier: UUID, payload: Decision, svc=Depends(service)):
    return call(svc.decide, str(identifier), payload.decision == 'accept')
