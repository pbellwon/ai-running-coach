from dataclasses import replace
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.db.database import Base
from app.db.models import AdaptationDecisionRecordDB
from app.models.adaptation_proposal import AdaptationProposal
from app.services.adaptation_decision_service import AdaptationDecisionService


@pytest.fixture
def adaptive_api(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    service = AdaptationDecisionService(factory)
    state = {"proposal": AdaptationProposal(
        target_date=date(2026, 10, 29),
        original_workout_title="Threshold 3 x 10 min",
        original_workout_type="threshold",
        decision="reduce_load",
        proposed_workout_type="threshold",
        proposed_distance_km=8.0,
        proposed_duration_min=45,
        reason="Recent fatigue",
    )}

    class PlanService:
        def build(self, target_date):
            return state["proposal"]

    monkeypatch.setattr(main, "AdaptivePlanningService", PlanService)
    monkeypatch.setattr(main, "AdaptationDecisionService", lambda: service)
    with TestClient(main.app) as client:
        yield client, state, factory
    engine.dispose()


def payload_for(proposal, response="accepted"):
    return {
        "proposal_id": proposal.proposal_id,
        "target_date": proposal.target_date.isoformat(),
        "original_workout_type": proposal.original_workout_type,
        "proposed_workout_type": proposal.proposed_workout_type,
        "proposal_decision": proposal.decision,
        "athlete_response": response,
    }


@pytest.mark.parametrize("response", ["accepted", "rejected"])
def test_decision_survives_reload_without_duplicate_records(adaptive_api, response):
    client, state, factory = adaptive_api
    url = "/adaptive-plan?target_date=2026-10-29"
    initial = client.get(url).json()
    assert initial["athlete_decision"] is None
    assert initial["proposal"]["proposal_id"] == state["proposal"].proposal_id

    payload = payload_for(state["proposal"], response)
    saved = client.post("/adaptive-plan/decision", json=payload)
    assert saved.status_code == 200
    assert saved.json()["athlete_response"] == response
    assert client.get(url).json()["athlete_decision"] == saved.json()

    # Retries and another tab cannot overwrite an already answered proposal.
    payload["athlete_response"] = "rejected" if response == "accepted" else "accepted"
    assert client.post("/adaptive-plan/decision", json=payload).json() == saved.json()
    with factory() as db:
        assert db.query(AdaptationDecisionRecordDB).count() == 1


def test_changed_workout_does_not_inherit_old_acceptance(adaptive_api):
    client, state, _ = adaptive_api
    payload = payload_for(state["proposal"])
    assert client.post("/adaptive-plan/decision", json=payload).status_code == 200
    state["proposal"] = replace(state["proposal"], proposed_distance_km=6.0)
    current = client.get("/adaptive-plan?target_date=2026-10-29").json()
    assert current["athlete_decision"] is None
    assert current["proposal"]["proposal_id"] != payload["proposal_id"]
    assert client.post("/adaptive-plan/decision", json=payload).status_code == 409


@pytest.mark.parametrize("changes", [
    {"proposed_workout_type": "easy_run"},
    {"proposal_decision": "rest"},
    {"original_workout_type": "long_run"},
])
def test_mismatched_proposal_is_not_saved(adaptive_api, changes):
    client, state, factory = adaptive_api
    payload = payload_for(state["proposal"])
    payload.update(changes)
    assert client.post("/adaptive-plan/decision", json=payload).status_code == 409
    with factory() as db:
        assert db.query(AdaptationDecisionRecordDB).count() == 0


def test_missing_workout_cannot_be_answered(adaptive_api):
    client, state, _ = adaptive_api
    payload = payload_for(state["proposal"])
    state["proposal"] = None
    result = client.get("/adaptive-plan?target_date=2026-10-29").json()
    assert result["status"] == "no_planned_workout"
    assert result["athlete_decision"] is None
    assert client.post("/adaptive-plan/decision", json=payload).status_code == 409


@pytest.mark.parametrize("changes", [
    {"decision": "keep_plan"}, {"requires_athlete_approval": False},
])
def test_non_actionable_proposals_do_not_accept_decisions(adaptive_api, changes):
    client, state, _ = adaptive_api
    proposal = replace(state["proposal"], **changes)
    state["proposal"] = proposal
    result = client.post("/adaptive-plan/decision", json=payload_for(proposal))
    assert result.status_code == 400


def test_invalid_response_is_rejected(adaptive_api):
    client, state, _ = adaptive_api
    payload = payload_for(state["proposal"], "unknown")
    assert client.post("/adaptive-plan/decision", json=payload).status_code == 400


def test_legacy_requests_remain_compatible_but_do_not_answer_new_proposals(adaptive_api):
    client, state, _ = adaptive_api
    payload = payload_for(state["proposal"])
    del payload["proposal_id"]
    assert client.post("/adaptive-plan/decision", json=payload).status_code == 200
    result = client.get("/adaptive-plan?target_date=2026-10-29").json()
    assert result["athlete_decision"] is None


def test_explanation_changes_preserve_identity(adaptive_api):
    _, state, _ = adaptive_api
    proposal = state["proposal"]
    assert replace(proposal, reason="Updated explanation", evidence=["New fact"]).proposal_id == proposal.proposal_id
    assert replace(proposal, proposed_duration_min=30).proposal_id != proposal.proposal_id
    assert replace(proposal, original_workout_title="Other workout").proposal_id != proposal.proposal_id
