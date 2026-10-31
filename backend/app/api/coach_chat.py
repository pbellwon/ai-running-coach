"""Owner-only chat endpoints. No access code means chat is disabled."""
import hmac
import os
from datetime import date as CalendarDate, timedelta
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel, Field, model_validator
from app.services.coach_chat_service import CoachChatService, ChatError

router = APIRouter(prefix="/coach", tags=["coach-chat"])


def require_chat_access(response: Response, authorization: str | None = Header(default=None)):
    response.headers["Cache-Control"] = "no-store"
    expected = os.getenv("COACH_CHAT_ACCESS_CODE", "").strip()
    if len(expected) < 16:
        raise HTTPException(503, "Rozmowa z trenerem nie została jeszcze skonfigurowana.")
    provided = authorization[7:] if authorization and authorization.startswith("Bearer ") else ""
    if not hmac.compare_digest(provided.encode(), expected.encode()):
        raise HTTPException(401, "Nieprawidłowy kod dostępu.", headers={"WWW-Authenticate": "Bearer"})


class Selection(BaseModel):
    kind: Literal["today", "week", "workout"] = "today"
    week_start: CalendarDate | None = None
    session_id: str | None = Field(default=None, min_length=1, max_length=200)
    date: CalendarDate | None = None

    @model_validator(mode="after")
    def validate_selection(self):
        today = CalendarDate.today()
        if self.kind == "week":
            if self.week_start is None or self.week_start.weekday() != 0:
                raise ValueError("Wybierz poniedziałek tygodnia.")
            if self.week_start > today - timedelta(days=today.weekday()):
                raise ValueError("Nie można analizować przyszłego tygodnia.")
        if self.kind == "workout" and (not self.session_id or not self.date or self.date > today):
            raise ValueError("Wybierz zapisany trening i jego datę.")
        return self


class ConversationRequest(BaseModel):
    id: UUID


class ChatRequest(BaseModel):
    conversation_id: UUID
    request_id: UUID
    message: str = Field(min_length=1, max_length=2000)
    context: Selection = Field(default_factory=Selection)

    @model_validator(mode="after")
    def trim_message(self):
        self.message = self.message.strip()
        if not self.message:
            raise ValueError("Wpisz pytanie.")
        return self


def service():
    return CoachChatService()


def call(fn, *args):
    try:
        return fn(*args)
    except ChatError as exc:
        raise HTTPException(exc.status, exc.message) from exc
    except Exception as exc:
        raise HTTPException(503, "Rozmowa jest chwilowo niedostępna. Spróbuj ponownie.") from exc


@router.get("/conversations", dependencies=[Depends(require_chat_access)])
def list_conversations(chat=Depends(service)):
    return {"items": call(chat.conversations)}


@router.post("/conversations", dependencies=[Depends(require_chat_access)])
def create_conversation(payload: ConversationRequest, chat=Depends(service)):
    return call(chat.create, str(payload.id))


@router.get("/conversations/{conversation_id}", dependencies=[Depends(require_chat_access)])
def history(conversation_id: UUID, chat=Depends(service)):
    return call(chat.history, str(conversation_id))


@router.post("/chat", dependencies=[Depends(require_chat_access)])
def send(payload: ChatRequest, chat=Depends(service)):
    return call(chat.send, str(payload.conversation_id), str(payload.request_id), payload.message,
                payload.context.model_dump(mode="json", exclude_none=True))
