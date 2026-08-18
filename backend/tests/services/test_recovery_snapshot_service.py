from app.services.recovery_snapshot_service import (
    RecoverySnapshotService,
)


def test_lower_hrv_is_warning():
    service = RecoverySnapshotService()

    result = service._build_relative_metric(
        current=54,
        baseline_values=[
            60,
            61,
            59,
            62,
            60,
            60,
            61,
        ],
        higher_is_better=True,
        warning_percent=-10,
        critical_percent=-20,
    )

    assert result.baseline == 60
    assert result.difference_percent == -10
    assert result.status == "warning"


def test_higher_resting_hr_is_warning():
    service = RecoverySnapshotService()

    result = service._build_relative_metric(
        current=44,
        baseline_values=[
            41,
            42,
            40,
            41,
            41,
            42,
            40,
        ],
        higher_is_better=False,
        warning_percent=5,
        critical_percent=10,
    )

    assert result.baseline == 41
    assert result.difference_percent == 7.3
    assert result.status == "warning"


def test_metric_requires_minimum_baseline():
    service = RecoverySnapshotService()

    result = service._build_relative_metric(
        current=60,
        baseline_values=[
            61,
            59,
            60,
        ],
        higher_is_better=True,
        warning_percent=-10,
        critical_percent=-20,
    )

    assert result.status == "insufficient_baseline"
    assert result.sample_size == 3


def test_overall_status_good_without_warnings():
    service = RecoverySnapshotService()

    metric = service._build_relative_metric(
        current=60,
        baseline_values=[
            60,
            61,
            59,
            62,
            60,
            60,
            61,
        ],
        higher_is_better=True,
        warning_percent=-10,
        critical_percent=-20,
    )

    assert (
        service._overall_status(
            [metric]
        )
        == "good"
    )


def test_overall_status_poor_with_two_warnings():
    service = RecoverySnapshotService()

    hrv = service._build_relative_metric(
        current=54,
        baseline_values=[
            60,
            61,
            59,
            62,
            60,
            60,
            61,
        ],
        higher_is_better=True,
        warning_percent=-10,
        critical_percent=-20,
    )

    resting_hr = service._build_relative_metric(
        current=44,
        baseline_values=[
            41,
            42,
            40,
            41,
            41,
            42,
            40,
        ],
        higher_is_better=False,
        warning_percent=5,
        critical_percent=10,
    )

    assert (
        service._overall_status(
            [
                hrv,
                resting_hr,
            ]
        )
        == "poor"
    )


def test_form_is_ctl_minus_atl():
    service = RecoverySnapshotService()

    assert (
        service._calculate_form(
            ctl=34,
            atl=40,
        )
        == -6
    )