from __future__ import annotations

from datetime import date, datetime, timedelta

from app.models.recovery_snapshot import RecoverySnapshot
from app.models.recovery_trend import (
    MetricTrend,
    RecoveryTrend,
)
from app.services.recovery_snapshot_service import (
    RecoverySnapshotService,
)


class RecoveryTrendService:
    """
    Evaluates short-term recovery trends.

    The service uses up to three consecutive calendar days,
    including the target date.

    It distinguishes:
    - a single weak reading;
    - repeated warning signals;
    - accumulating fatigue.

    It does not yet prescribe training changes.
    """

    WINDOW_DAYS = 5
    MIN_TREND_SAMPLES = 2

    def __init__(
        self,
        snapshot_service: RecoverySnapshotService | None = None,
    ):
        self.snapshot_service = (
            snapshot_service
            or RecoverySnapshotService()
        )

    def build(
        self,
        target_date: date | datetime | str,
    ) -> RecoveryTrend:
        normalized_date = self._normalize_date(
            target_date
        )

        snapshots = self._get_snapshots(
            target_date=normalized_date
        )

        hrv_values = [
            snapshot.hrv.current
            for snapshot in snapshots
        ]

        resting_hr_values = [
            snapshot.resting_hr.current
            for snapshot in snapshots
        ]

        sleep_duration_values = [
            snapshot.sleep_duration.current
            for snapshot in snapshots
        ]

        sleep_score_values = [
            snapshot.sleep_score.current
            for snapshot in snapshots
        ]

        hrv_trend = self._build_metric_trend(
            values=hrv_values,
            higher_is_better=True,
        )

        resting_hr_trend = self._build_metric_trend(
            values=resting_hr_values,
            higher_is_better=False,
        )

        sleep_duration_trend = self._build_metric_trend(
            values=sleep_duration_values,
            higher_is_better=True,
        )

        sleep_score_trend = self._build_metric_trend(
            values=sleep_score_values,
            higher_is_better=True,
        )

        caution_days = sum(
            1
            for snapshot in snapshots
            if snapshot.overall_status == "caution"
        )

        poor_days = sum(
            1
            for snapshot in snapshots
            if snapshot.overall_status == "poor"
        )

        fatigue_score, reasons = (
            self._calculate_fatigue_score(
                snapshots=snapshots,
                hrv_trend=hrv_trend,
                resting_hr_trend=resting_hr_trend,
                sleep_duration_trend=(
                    sleep_duration_trend
                ),
                sleep_score_trend=sleep_score_trend,
                caution_days=caution_days,
                poor_days=poor_days,
            )
        )

        fatigue_signal = self._fatigue_signal(
            score=fatigue_score,
            available_days=len(snapshots),
        )

        if not reasons:
            reasons.append(
                "No accumulating recovery problem detected."
            )

        return RecoveryTrend(
            target_date=normalized_date,
            window_days=self.WINDOW_DAYS,
            available_days=len(snapshots),
            hrv=hrv_trend,
            resting_hr=resting_hr_trend,
            sleep_duration=sleep_duration_trend,
            sleep_score=sleep_score_trend,
            caution_days=caution_days,
            poor_days=poor_days,
            fatigue_signal=fatigue_signal,
            fatigue_score=fatigue_score,
            reasons=reasons,
        )

    def _get_snapshots(
        self,
        target_date: date,
    ) -> list[RecoverySnapshot]:
        start_date = (
            target_date
            - timedelta(days=self.WINDOW_DAYS - 1)
        )

        snapshots: list[RecoverySnapshot] = []

        for day_offset in range(self.WINDOW_DAYS):
            current_date = (
                start_date
                + timedelta(days=day_offset)
            )

            try:
                snapshot = self.snapshot_service.build(
                    current_date
                )
            except ValueError:
                continue

            snapshots.append(snapshot)

        return snapshots

    def _build_metric_trend(
        self,
        values: list[float | None],
        higher_is_better: bool,
    ) -> MetricTrend:
        valid_values = [
            value
            for value in values
            if value is not None
        ]

        if len(valid_values) < self.MIN_TREND_SAMPLES:
            direction = "insufficient_data"

        elif self._strictly_increasing(valid_values):
            direction = (
                "improving"
                if higher_is_better
                else "worsening"
            )

        elif self._strictly_decreasing(valid_values):
            direction = (
                "worsening"
                if higher_is_better
                else "improving"
            )

        elif self._is_stable(valid_values):
            direction = "stable"

        else:
            direction = "mixed"

        return MetricTrend(
            values=values,
            direction=direction,
            valid_samples=len(valid_values),
        )

    def _calculate_fatigue_score(
        self,
        snapshots: list[RecoverySnapshot],
        hrv_trend: MetricTrend,
        resting_hr_trend: MetricTrend,
        sleep_duration_trend: MetricTrend,
        sleep_score_trend: MetricTrend,
        caution_days: int,
        poor_days: int,
    ) -> tuple[int, list[str]]:
        score = 0
        reasons: list[str] = []

        if not snapshots:
            return 0, reasons

        latest = snapshots[-1]

        if hrv_trend.direction == "worsening":
            score += 1
            reasons.append(
                "HRV has declined across recent days."
            )

        if latest.hrv.status == "warning":
            score += 1

        elif latest.hrv.status == "critical":
            score += 2

        if resting_hr_trend.direction == "worsening":
            score += 1
            reasons.append(
                "Resting heart rate has risen "
                "across recent days."
            )

        if latest.resting_hr.status == "warning":
            score += 1

        elif latest.resting_hr.status == "critical":
            score += 2

        sleep_warning_days = sum(
            1
            for snapshot in snapshots
            if snapshot.sleep_duration.status
            in {
                "warning",
                "critical",
            }
        )

        low_sleep_score_days = sum(
            1
            for snapshot in snapshots
            if snapshot.sleep_score.status
            in {
                "warning",
                "critical",
            }
        )

        if sleep_warning_days >= 2:
            score += 2
            reasons.append(
                "Sleep duration has been low "
                "on multiple recent days."
            )

        elif sleep_warning_days == 1:
            score += 1

        if low_sleep_score_days >= 2:
            score += 2
            reasons.append(
                "Sleep score has been low "
                "on multiple recent days."
            )

        elif low_sleep_score_days == 1:
            score += 1

        if (
            sleep_duration_trend.direction
            == "worsening"
        ):
            score += 1
            reasons.append(
                "Sleep duration is trending downward."
            )

        if sleep_score_trend.direction == "worsening":
            score += 1
            reasons.append(
                "Sleep score is trending downward."
            )

        if poor_days >= 2:
            score += 3
            reasons.append(
                "Recovery status was poor "
                "on multiple recent days."
            )

        elif poor_days == 1:
            score += 2

        if caution_days >= 2:
            score += 2
            reasons.append(
                "Recovery status showed repeated caution."
            )

        elif caution_days == 1:
            score += 1

        if (
            latest.form is not None
            and latest.form <= -15
        ):
            score += 2
            reasons.append(
                "Acute training load is substantially "
                "above chronic training load."
            )

        elif (
            latest.form is not None
            and latest.form <= -10
        ):
            score += 1
            reasons.append(
                "Acute training load is above "
                "chronic training load."
            )

        return score, reasons

    def _fatigue_signal(
        self,
        score: int,
        available_days: int,
    ) -> str:
        if available_days < 2:
            return "insufficient_data"

        if score >= 8:
            return "high"

        if score >= 5:
            return "accumulating"

        if score >= 2:
            return "watch"

        return "none"

    def _strictly_increasing(
        self,
        values: list[float],
    ) -> bool:
        return all(
            current > previous
            for previous, current
            in zip(values, values[1:])
        )

    def _strictly_decreasing(
        self,
        values: list[float],
    ) -> bool:
        return all(
            current < previous
            for previous, current
            in zip(values, values[1:])
        )

    def _is_stable(
        self,
        values: list[float],
    ) -> bool:
        if not values:
            return False

        average = sum(values) / len(values)

        if average == 0:
            return all(value == 0 for value in values)

        spread_percent = (
            max(values) - min(values)
        ) / abs(average) * 100

        return spread_percent <= 3.0

    def _normalize_date(
        self,
        value: date | datetime | str,
    ) -> date:
        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        if isinstance(value, str):
            normalized = value.strip()

            try:
                return date.fromisoformat(normalized)

            except ValueError as exc:
                raise ValueError(
                    "Date must use YYYY-MM-DD format."
                ) from exc

        raise TypeError(
            "Date must be date, datetime or ISO string."
        )