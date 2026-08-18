from app.services.intervals_declared_type_classifier import (
    IntervalsDeclaredTypeClassifier,
)


def classify(name):
    return (
        IntervalsDeclaredTypeClassifier()
        .classify(name=name)
    )


def test_long_run_role():
    result = classify(
        "Gdynia - long"
    )

    assert result.session_role == "long_run"
    assert result.workout_type is None


def test_long_tempo_has_two_dimensions():
    result = classify(
        "Long tempo"
    )

    assert result.session_role == "long_run"
    assert result.workout_type == "tempo_run"


def test_long_threshold_has_two_dimensions():
    result = classify(
        "Long threshold"
    )

    assert result.session_role == "long_run"
    assert result.workout_type == "threshold"


def test_threshold():
    result = classify(
        "6 km threshold"
    )

    assert result.session_role is None
    assert result.workout_type == "threshold"


def test_easy_strides():
    result = classify(
        "Rumia - Easy + 6x rytmy"
    )

    assert result.session_role is None
    assert (
        result.workout_type
        == "easy_run+strides"
    )


def test_race():
    result = (
        IntervalsDeclaredTypeClassifier()
        .classify(
            name="Saturday run",
            race=True,
        )
    )

    assert result.workout_type == "race"


def test_strength():
    result = (
        IntervalsDeclaredTypeClassifier()
        .classify(
            name=None,
            external_type="WeightTraining",
        )
    )

    assert result.workout_type == "strength"