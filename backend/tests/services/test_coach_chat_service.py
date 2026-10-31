import json
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db.models import CoachChatGateDB, CoachChatTurnDB
from app.services.coach_chat_service import CoachChatService, ChatError


@pytest.fixture
def chat():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    now = [datetime(2026, 10, 31, 12)]
    captured = []

    class Context:
        def build(self, selection):
            return {'sources': [{'label': 'Cel 10 km', 'date': '2026-10-31'}],
                    'limitations': ['Brak HRV'], 'facts': {'goal': '38:30'},
                    'as_of': now[0].isoformat(), 'selection': selection}

    class LLM:
        def generate(self, **kwargs):
            captured.append(json.loads(kwargs['input_text']))
            return 'W dostępnych danych widzę pracę nad celem. Brakuje HRV.'

    service = CoachChatService(factory, Context(), LLM(), lambda: now[0])
    conversation = str(uuid4())
    service.create(conversation)
    yield service, factory, now, captured, conversation
    engine.dispose()


def send(chat, message='Jak idą przygotowania?', request_id=None):
    service, _, _, _, conversation = chat
    return service.send(conversation, request_id or str(uuid4()), message, {'kind': 'today'})


def test_persistence_idempotency_and_followup_context(chat):
    service, factory, now, calls, conversation = chat
    request = str(uuid4())
    first = send(chat, request_id=request)
    assert send(chat, request_id=request) == first
    assert len(calls) == 1
    # A new service instance sees the same persisted turn and quota.
    restarted = CoachChatService(session_factory=factory)
    assert restarted.history(conversation)['turns'] == [first]
    assert restarted.conversations()[0]['id'] == conversation
    now[0] += timedelta(seconds=11)
    second = send(chat, message='A co z regeneracją?')
    assert len(calls) == 2
    assert calls[1]['history'][0]['athlete'] == 'Jak idą przygotowania?'
    assert second['as_of'] != first['as_of']
    assert second['sources'] == [{'label': 'Cel 10 km', 'date': '2026-10-31'}]
    assert len(service.history(conversation)['turns']) == 2


def test_request_id_cannot_be_reused_for_changed_question(chat):
    request = str(uuid4())
    send(chat, request_id=request)
    with pytest.raises(ChatError) as error:
        send(chat, message='Zupełnie inne pytanie', request_id=request)
    assert error.value.status == 409


def test_quota_is_shared_and_survives_new_conversation(chat):
    service, factory, now, _, _ = chat
    send(chat)
    other = str(uuid4())
    service.create(other)
    with pytest.raises(ChatError) as error:
        service.send(other, str(uuid4()), 'Pytanie', {'kind': 'today'})
    assert error.value.status == 429
    now[0] += timedelta(seconds=11)
    with factory() as db:
        db.get(CoachChatGateDB, 1).attempts = 60
        db.commit()
    with pytest.raises(ChatError) as error:
        send(chat)
    assert error.value.status == 429
    now[0] += timedelta(days=1)
    send(chat)
    with factory() as db:
        assert db.get(CoachChatGateDB, 1).attempts == 1


def test_failed_generation_is_retryable_without_duplicate_turn(chat):
    service, factory, now, calls, conversation = chat
    good = service.llm

    class Broken:
        def generate(self, **kwargs):
            raise RuntimeError('PRIVATE CREDENTIAL DETAIL')

    service.llm = Broken()
    request = str(uuid4())
    with pytest.raises(ChatError) as error:
        send(chat, request_id=request)
    assert error.value.status == 502
    assert 'PRIVATE' not in str(error.value)
    assert service.history(conversation)['turns'] == []
    now[0] += timedelta(seconds=11)
    service.llm = good
    send(chat, request_id=request)
    with factory() as db:
        assert db.query(CoachChatTurnDB).count() == 1
    assert len(service.history(conversation)['turns']) == 1


def test_pending_request_and_shared_busy_gate_prevent_concurrent_calls(chat):
    service, _, now, calls, _ = chat
    real_context = service.context

    class NestedContext:
        def build(self, selection):
            with pytest.raises(ChatError) as error:
                send(chat, message='Drugie pytanie')
            assert error.value.status == 429
            return real_context.build(selection)

    service.context = NestedContext()
    send(chat)
    assert len(calls) == 1


def test_no_facts_means_no_paid_call(chat):
    service, _, _, calls, _ = chat
    class Missing:
        def build(self, selection):
            return {'sources': []}
    service.context = Missing()
    with pytest.raises(ChatError) as error:
        send(chat)
    assert error.value.status == 503
    assert not calls


def test_expired_context_fetch_cannot_start_a_paid_generation(chat):
    service, _, now, calls, _ = chat
    original = service.context
    class Slow:
        def build(self, selection):
            now[0] += timedelta(seconds=91)
            return original.build(selection)
    service.context = Slow()
    with pytest.raises(ChatError) as error:
        send(chat)
    assert error.value.status == 409
    assert calls == []
