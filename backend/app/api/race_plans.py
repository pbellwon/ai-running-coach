"""Private evidence-based coaching and full-plan review API."""
from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from gspread.exceptions import WorksheetNotFound
from pydantic import BaseModel, ConfigDict, Field
from app.api.coach_chat import require_chat_access
from app.services.coach_chat_service import ChatError
from app.services.race_plan_service import RacePlanService

router = APIRouter(prefix='/coach/race-plans', tags=['race-plans'], dependencies=[Depends(require_chat_access)])


class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: UUID
    plan_version: str = Field(min_length=64, max_length=64)
    calendar_version: str = Field(min_length=64, max_length=64)
    athlete_version: str = Field(min_length=64, max_length=64)
    note: str = Field(default='', max_length=2000)
    start: date
    end: date
    replace_existing: bool = False


class Decision(BaseModel):
    decision: Literal['accept', 'reject']


def service():
    return RacePlanService()


def call(fn, *args):
    try:
        return fn(*args)
    except ChatError as exc:
        raise HTTPException(exc.status, exc.message) from exc
    except WorksheetNotFound as exc:
        raise HTTPException(422, 'Sprawdź, czy arkusz zawiera zakładki plan_import i race_calendar z wymaganymi nagłówkami.') from exc
    except Exception as exc:
        raise HTTPException(503, 'Dane planu są chwilowo niedostępne. Sprawdź historię przed ponowieniem zapisu.') from exc


@router.get('/context')
def context(svc=Depends(service)):
    return call(svc.context)


@router.put('/preferences')
def retired_preferences():
    raise HTTPException(410, 'Preferencje dni i limitów czasu zastąpiła propozycja trenera oparta na historii i cyklu 10-dniowym.')


@router.get('')
def history(svc=Depends(service)):
    return call(svc.history)


@router.post('/preview')
def preview(payload: PreviewRequest, svc=Depends(service)):
    return call(svc.preview, str(payload.id), payload.model_dump(mode='json', exclude={'id'}))


@router.get('/{identifier}')
def detail(identifier: UUID, svc=Depends(service)):
    return call(svc.get, str(identifier))


@router.post('/{identifier}/decision')
def decide(identifier: UUID, payload: Decision, svc=Depends(service)):
    return call(svc.decide, str(identifier), payload.decision == 'accept')
