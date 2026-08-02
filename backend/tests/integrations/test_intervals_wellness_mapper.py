from datetime import date

from app.integrations.intervals_wellness_mapper import (
    IntervalsWellnessMapper,
)


def test_maps_intervals_wellness():
    wellness = {
        "id": "2026-07-25",
        "ctl": 33.919296,
        "atl": 36.726906,
        "rampRate": -0.6804657,
        "weight": None,
        "restingHR": 41,
        "hrv": 61,
        "hrvSDNN": None,
        "sleepSecs": 28260,
        "sleepScore": 92,
        "sleepQuality": 1,
        "avgSleepingHR": None,
        "soreness": None,
        "fatigue": None,
        "stress": None,
        "mood": None,
        "motivation": None,
        "readiness": None,
        "spO2": None,
        "vo2max": 54,
        "steps": 15866,
    }

    state = (
        IntervalsWellnessMapper().map(
            wellness
        )
    )

    assert state.date == date(
        2026,
        7,
        25,
    )

    assert state.resting_hr == 41
    assert state.hrv == 61

    assert state.sleep_sec == 28260
    assert state.sleep_score == 92
    assert state.sleep_quality == 1

    assert round(state.ctl, 2) == 33.92
    assert round(state.atl, 2) == 36.73
    assert round(state.ramp_rate, 2) == -0.68

    assert state.vo2max == 54
    assert state.steps == 15866

    assert state.weight_kg is None
    assert state.readiness is None


def test_missing_optional_values_are_allowed():
    wellness = {
        "id": "2026-07-26",
        "restingHR": 40,
        "hrv": 64,
    }

    state = (
        IntervalsWellnessMapper().map(
            wellness
        )
    )

    assert state.resting_hr == 40
    assert state.hrv == 64
    assert state.sleep_sec is None
    assert state.ctl is None