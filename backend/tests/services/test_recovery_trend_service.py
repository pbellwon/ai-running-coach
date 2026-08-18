from datetime import date

from app.models.recovery_snapshot import (
    RecoveryMetric,
    RecoverySnapshot,
)
from app.services.recovery_trend_service import (
    RecoveryTrendService,
)


def make_metric(
    current: float | None,
    status: str = "normal",
) -> RecoveryMetric:
    return RecoveryMetric(
        current=current,
        baseline=60,
        difference=0,
        difference_percent=0,
        status=status,
        sample_size=10,
    )


def make_snapshot(
    snapshot_date: date,
    hrv: float,
    resting_hr: float,
    sleep_sec: float,
    sleep_score: float,
    overall_status: str = "good",
    hrv_status: str = "normal",
    resting_hr_status: str = "normal",
    sleep_status: str = "normal",
    sleep_score_status: str = "normal",
    form: float = 0,
) -> RecoverySnapshot:
    return RecoverySnapshot(
        date=snapshot_date,
        hrv=make_metric(
            hrv,
            hrv_status,
        ),
        resting_hr=make_metric(
            resting_hr,
            resting_hr_status,
        ),
        sleep_duration=make_metric(
            sleep_sec,
            sleep_status,
        ),
        sleep_score=make_metric(
            sleep_score,
            sleep_score_status,
        ),
        ctl=35,
        atl=35 - form,
        form=form,
        overall_status=overall_status,
        warning_count=0,
        available_metrics_count=4,
        reasons=[],
    )


class FakeSnapshotService:
    def __init__(
        self,
        snapshots: dict[date, RecoverySnapshot],
    ):
        self.snapshots = snapshots

    def build(
        self,
        target_date,
    ) -> RecoverySnapshot:
        if target_date not in self.snapshots:
            raise ValueError("Missing state")

        return self.snapshots[target_date]


def test_detects_worsening_hrv_and_resting_hr():
    snapshots = {
        date(2026, 8, 1): make_snapshot(
            date(2026, 8, 1),
            hrv=65,
            resting_hr=40,
            sleep_sec=28000,
            sleep_score=90,
        ),
        date(2026, 8, 2): make_snapshot(
            date(2026, 8, 2),
            hrv=61,
            resting_hr=42,
            sleep_sec=27500,
            sleep_score=85,
        ),
        date(2026, 8, 3): make_snapshot(
            date(2026, 8, 3),
            hrv=56,
            resting_hr=44,
            sleep_sec=27000,
            sleep_score=80,
            hrv_status="warning",
            resting_hr_status="warning",
        ),
    }

    service = RecoveryTrendService(
        snapshot_service=FakeSnapshotService(
            snapshots
        )
    )

    result = service.build("2026-08-03")

    assert result.hrv.direction == "worsening"
    assert (
        result.resting_hr.direction
        == "worsening"
    )
    assert result.available_days == 3
    assert result.fatigue_signal in {
        "watch",
        "accumulating",
        "high",
    }


def test_stable_metrics_return_no_fatigue():
    snapshots = {
        date(2026, 8, 1): make_snapshot(
            date(2026, 8, 1),
            hrv=60,
            resting_hr=40,
            sleep_sec=28000,
            sleep_score=90,
        ),
        date(2026, 8, 2): make_snapshot(
            date(2026, 8, 2),
            hrv=60,
            resting_hr=40,
            sleep_sec=28000,
            sleep_score=90,
        ),
        date(2026, 8, 3): make_snapshot(
            date(2026, 8, 3),
            hrv=60,
            resting_hr=40,
            sleep_sec=28000,
            sleep_score=90,
        ),
    }

    service = RecoveryTrendService(
        snapshot_service=FakeSnapshotService(
            snapshots
        )
    )

    result = service.build("2026-08-03")

    assert result.hrv.direction == "stable"
    assert result.resting_hr.direction == "stable"
    assert result.fatigue_signal == "none"
    assert result.fatigue_score == 0


def test_repeated_poor_recovery_is_high_signal():
    snapshots = {
        date(2026, 8, 1): make_snapshot(
            date(2026, 8, 1),
            hrv=60,
            resting_hr=41,
            sleep_sec=25000,
            sleep_score=65,
            overall_status="poor",
            sleep_status="warning",
            sleep_score_status="warning",
        ),
        date(2026, 8, 2): make_snapshot(
            date(2026, 8, 2),
            hrv=55,
            resting_hr=43,
            sleep_sec=23000,
            sleep_score=52,
            overall_status="poor",
            hrv_status="warning",
            resting_hr_status="warning",
            sleep_status="critical",
            sleep_score_status="critical",
        ),
        date(2026, 8, 3): make_snapshot(
            date(2026, 8, 3),
            hrv=50,
            resting_hr=45,
            sleep_sec=22000,
            sleep_score=48,
            overall_status="poor",
            hrv_status="critical",
            resting_hr_status="critical",
            sleep_status="critical",
            sleep_score_status="critical",
            form=-16,
        ),
    }

    service = RecoveryTrendService(
        snapshot_service=FakeSnapshotService(
            snapshots
        )
    )

    result = service.build("2026-08-03")

    assert result.poor_days == 3
    assert result.fatigue_signal == "high"
    assert result.fatigue_score >= 8


def test_missing_day_is_allowed():
    snapshots = {
        date(2026, 8, 1): make_snapshot(
            date(2026, 8, 1),
            hrv=60,
            resting_hr=40,
            sleep_sec=28000,
            sleep_score=90,
        ),
        date(2026, 8, 3): make_snapshot(
            date(2026, 8, 3),
            hrv=58,
            resting_hr=41,
            sleep_sec=27000,
            sleep_score=85,
        ),
    }

    service = RecoveryTrendService(
        snapshot_service=FakeSnapshotService(
            snapshots
        )
    )

    result = service.build("2026-08-03")

    assert result.available_days == 2
    assert result.hrv.valid_samples == 2


def test_single_day_returns_insufficient_data():
    snapshots = {
        date(2026, 8, 3): make_snapshot(
            date(2026, 8, 3),
            hrv=60,
            resting_hr=40,
            sleep_sec=28000,
            sleep_score=90,
        )
    }

    service = RecoveryTrendService(
        snapshot_service=FakeSnapshotService(
            snapshots
        )
    )

    result = service.build("2026-08-03")

    assert result.available_days == 1
    assert (
        result.fatigue_signal
        == "insufficient_data"
    )