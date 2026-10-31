from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from app import main
from app.api import coach_chat

client = TestClient(main.app)
CODE = 'test-only-access-code-12345'
HEADERS = {'Authorization': f'Bearer {CODE}'}


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    monkeypatch.setenv('COACH_CHAT_ACCESS_CODE', CODE)
    yield
    main.app.dependency_overrides.pop(coach_chat.service, None)


def payload():
    return {'conversation_id': str(uuid4()), 'request_id': str(uuid4()),
            'message': 'Co wynika z ostatniego tygodnia?', 'context': {'kind': 'today'}}


def test_all_chat_endpoints_require_access_before_loading_data():
    for method, url, body in [
        ('GET', '/coach/conversations', None),
        ('POST', '/coach/conversations', {'id': str(uuid4())}),
        ('GET', f'/coach/conversations/{uuid4()}', None),
        ('POST', '/coach/chat', payload()),
    ]:
        response = client.request(method, url, json=body)
        assert response.status_code == 401
        assert CODE not in response.text


def test_missing_or_short_config_fails_closed(monkeypatch):
    monkeypatch.delenv('COACH_CHAT_ACCESS_CODE')
    assert client.get('/coach/conversations', headers=HEADERS).status_code == 503
    monkeypatch.setenv('COACH_CHAT_ACCESS_CODE', '1234')
    assert client.get('/coach/conversations', headers=HEADERS).status_code == 503


def test_schema_rejects_blank_oversize_and_invalid_context():
    for message in ['   ', 'x'*2001]:
        data = payload(); data['message'] = message
        assert client.post('/coach/chat', json=data, headers=HEADERS).status_code == 422
    for context in [{'kind': 'week', 'week_start': '2026-10-27'}, {'kind': 'workout'},
                    {'kind': 'week', 'week_start': '2099-10-26'}, {'kind': 'unknown'}]:
        data = payload(); data['context'] = context
        assert client.post('/coach/chat', json=data, headers=HEADERS).status_code == 422


def test_authenticated_request_passes_only_validated_fields():
    seen = []
    class Service:
        def send(self, *args):
            seen.append(args)
            return {'answer': 'Wniosek trenera'}
    main.app.dependency_overrides[coach_chat.service] = Service
    data = payload()
    assert client.post('/coach/chat', json=data, headers=HEADERS).json()['answer'] == 'Wniosek trenera'
    assert seen[0][3] == {'kind': 'today'}


def test_provider_failures_do_not_expose_private_details():
    class Service:
        def conversations(self):
            raise RuntimeError('PRIVATE DATABASE DETAIL')
    main.app.dependency_overrides[coach_chat.service] = Service
    response = client.get('/coach/conversations', headers=HEADERS)
    assert response.status_code == 503
    assert 'PRIVATE' not in response.text


def test_secret_file_newline_is_normalized_and_responses_are_not_cacheable(monkeypatch):
    monkeypatch.setenv('COACH_CHAT_ACCESS_CODE', CODE + '\n')
    class Service:
        def conversations(self): return []
    main.app.dependency_overrides[coach_chat.service] = Service
    response = client.get('/coach/conversations', headers=HEADERS)
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
