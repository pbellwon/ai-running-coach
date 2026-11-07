from datetime import date, datetime, timedelta
from typing import Annotated, Literal
from zoneinfo import ZoneInfo
from pydantic import BaseModel, ConfigDict, Field, model_validator


def today():
    return datetime.now(ZoneInfo('Europe/Warsaw')).date()


class MemoryChange(BaseModel):
    model_config = ConfigDict(extra='forbid')
    kind: Literal['memory'] = 'memory'
    category: Literal['training_agreement', 'injury', 'restriction', 'training_response', 'other']
    text: str = Field(min_length=1, max_length=2000)
    fact_status: Literal['current', 'historical', 'resolved']
    observed_on: date = Field(default_factory=today)
    replace_id: int | None = Field(default=None, ge=1)

    @model_validator(mode='after')
    def validate_values(self):
        self.text = self.text.strip()
        if not self.text or not date(2000, 1, 1) <= self.observed_on <= today():
            raise ValueError('Podaj treść i datę zgłoszenia nie późniejszą niż dziś.')
        return self


class CycleChange(BaseModel):
    model_config = ConfigDict(extra='forbid')
    kind: Literal['cycle'] = 'cycle'
    cycle_days: Literal[10] = 10
    anchor_date: date | None = None

    @model_validator(mode='after')
    def validate_anchor(self):
        if self.anchor_date and not date(2000, 1, 1) <= self.anchor_date <= today()+timedelta(days=30):
            raise ValueError('Początek cyklu może przypadać najwyżej 30 dni naprzód.')
        return self


class GoalChange(BaseModel):
    model_config = ConfigDict(extra='forbid')
    kind: Literal['goal'] = 'goal'
    calendar_version: str = Field(min_length=64, max_length=64)
    race_key: str = Field(min_length=64, max_length=64)


ProfileChange = Annotated[MemoryChange | CycleChange | GoalChange, Field(discriminator='kind')]


class MemorySuggestion(BaseModel):
    model_config = ConfigDict(extra='forbid')
    category: Literal['training_agreement', 'injury', 'restriction', 'training_response', 'other']
    text: str = Field(min_length=1, max_length=2000)
    fact_status: Literal['current', 'historical', 'resolved']
    quote: str = Field(min_length=3, max_length=2000)
    replace_id: int | None = Field(default=None, ge=1)


class ChatWithMemory(BaseModel):
    model_config = ConfigDict(extra='forbid')
    answer: str = Field(min_length=1, max_length=16000)
    suggestions: list[MemorySuggestion] = Field(default_factory=list, max_length=1)
