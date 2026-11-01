"""Private calendar, training preferences and full-plan review API."""
from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from gspread.exceptions import WorksheetNotFound
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.api.coach_chat import require_chat_access
from app.services.coach_chat_service import ChatError
from app.services.race_plan_service import RacePlanService

router = APIRouter(prefix='/coach/race-plans', tags=['race-plans'], dependencies=[Depends(require_chat_access)])


class Preferences(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    weekdays: list[int] = Field(min_length=2, max_length=6)
    long_run_day: int = Field(ge=0, le=6)
    weekly_distance_km: float = Field(ge=5, le=200)
    easy_pace_min_km: float = Field(ge=3, le=12)
    max_minutes: dict[str, int]

    @model_validator(mode='after')
    def check(self):
        if len(set(self.weekdays)) != len(self.weekdays) or any(d < 0 or d > 6 for d in self.weekdays):
            raise ValueError('Wybierz od 2 do 6 różnych dni tygodnia.')
        if self.long_run_day not in self.weekdays:
            raise ValueError('Długi bieg musi przypadać w wybrany dzień treningowy.')
        if set(self.max_minutes) != set('0123456') or any(v < 15 or v > 240 for v in self.max_minutes.values()):
            raise ValueError('Podaj limity 15–240 minut dla każdego dnia tygodnia.')
        self.weekdays.sort()
        return self


class SettingsRequest(BaseModel):
    version: str = Field(min_length=64, max_length=64)
    value: Preferences


class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: UUID
    plan_version: str = Field(min_length=64, max_length=64)
    calendar_version: str = Field(min_length=64, max_length=64)
    preferences_version: str = Field(min_length=64, max_length=64)
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
def save_preferences(payload: SettingsRequest, svc=Depends(service)):
    return call(svc.save_preferences, payload.value.model_dump(), payload.version)


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
