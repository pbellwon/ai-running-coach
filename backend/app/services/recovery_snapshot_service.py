from __future__ import annotations

from datetime import date, datetime, timedelta
from statistics import median

from app.db.database import SessionLocal
from app.db.models import DailyAthleteStateDB
from app.models.recovery_snapshot import (
    RecoveryMetric,
    RecoverySnapshot,
)


class RecoverySnapshotService:
    """
    Builds a recovery snapshot for a selected date.

    Baselines are calculated from previous days only.
    The current day is never included in its own baseline.

    Initial thresholds are deliberately conservative.
    They will later be individualized using longer history.
    """

    BASELINE_DAYS = 14
    MIN_BASELINE_SAMPLES = 5

    HRV_WARNING_PERCENT = -10.0
    HRV_CRITICAL_PERCENT = -20.0

    RHR_WARNING_PERCENT = 5.0
    RHR_CRITICAL_PERCENT = 10.0

    SLEEP_WARNING_PERCENT = -10.0
    SLEEP_CRITICAL_PERCENT = -20.0

    SLEEP_SCORE_WARNING = 70.0
    SLEEP_SCORE_CRITICAL = 55.0

    def build(
        self,
        target_date: date | datetime | str,
    ) -> RecoverySnapshot:
        normalized_date = self._normalize_date(
            target_date
        )

        current_state = self._get_state(
            normalized_date
        )

        if current_state is None:
            raise ValueError(
                "No athlete state found for "
                f"{normalized_date.isoformat()}."
            )

        baseline_states = self._get_baseline_states(
            target_date=normalized_date
        )

        hrv = self._build_relative_metric(
            current=current_state.hrv,
            baseline_values=[
                state.hrv
                for state in baseline_states
                if state.hrv is not None
            ],
            higher_is_better=True,
            warning_percent=(
                self.HRV_WARNING_PERCENT
            ),
            critical_percent=(
                self.HRV_CRITICAL_PERCENT
            ),
        )

        resting_hr = self._build_relative_metric(
            current=current_state.resting_hr,
            baseline_values=[
                state.resting_hr
                for state in baseline_states
                if state.resting_hr is not None
            ],
            higher_is_better=False,
            warning_percent=(
                self.RHR_WARNING_PERCENT
            ),
            critical_percent=(
                self.RHR_CRITICAL_PERCENT
            ),
        )

        sleep_duration = self._build_relative_metric(
            current=current_state.sleep_sec,
            baseline_values=[
                state.sleep_sec
                for state in baseline_states
                if state.sleep_sec is not None
            ],
            higher_is_better=True,
            warning_percent=(
                self.SLEEP_WARNING_PERCENT
            ),
            critical_percent=(
                self.SLEEP_CRITICAL_PERCENT
            ),
        )

        sleep_score = self._build_sleep_score_metric(
            current=current_state.sleep_score,
            baseline_values=[
                state.sleep_score
                for state in baseline_states
                if state.sleep_score is not None
            ],
        )

        form = self._calculate_form(
            ctl=current_state.ctl,
            atl=current_state.atl,
        )

        metrics = [
            hrv,
            resting_hr,
            sleep_duration,
            sleep_score,
        ]

        available_metrics = [
            metric
            for metric in metrics
            if metric.current is not None
        ]

        warning_count = sum(
            1
            for metric in available_metrics
            if metric.status in {
                "warning",
                "critical",
            }
        )

        overall_status = self._overall_status(
            metrics=available_metrics
        )

        reasons = self._build_reasons(
            hrv=hrv,
            resting_hr=resting_hr,
            sleep_duration=sleep_duration,
            sleep_score=sleep_score,
            ctl=current_state.ctl,
            atl=current_state.atl,
            form=form,
        )

        return RecoverySnapshot(
            date=normalized_date,
            hrv=hrv,
            resting_hr=resting_hr,
            sleep_duration=sleep_duration,
            sleep_score=sleep_score,
            ctl=current_state.ctl,
            atl=current_state.atl,
            form=form,
            overall_status=overall_status,
            warning_count=warning_count,
            available_metrics_count=len(
                available_metrics
            ),
            reasons=reasons,
        )

    def _get_state(
        self,
        target_date: date,
    ) -> DailyAthleteStateDB | None:
        target_datetime = datetime.combine(
            target_date,
            datetime.min.time(),
        )

        db = SessionLocal()

        try:
            return (
                db.query(DailyAthleteStateDB)
                .filter(
                    DailyAthleteStateDB.date
                    == target_datetime
                )
                .first()
            )
        finally:
            db.close()

    def _get_baseline_states(
        self,
        target_date: date,
    ) -> list[DailyAthleteStateDB]:
        baseline_start = (
            target_date
            - timedelta(days=self.BASELINE_DAYS)
        )

        baseline_end = target_date

        start_datetime = datetime.combine(
            baseline_start,
            datetime.min.time(),
        )

        end_datetime = datetime.combine(
            baseline_end,
            datetime.min.time(),
        )

        db = SessionLocal()

        try:
            return (
                db.query(DailyAthleteStateDB)
                .filter(
                    DailyAthleteStateDB.date
                    >= start_datetime
                )
                .filter(
                    DailyAthleteStateDB.date
                    < end_datetime
                )
                .order_by(
                    DailyAthleteStateDB.date.asc()
                )
                .all()
            )
        finally:
            db.close()

    def _build_relative_metric(
        self,
        current: float | None,
        baseline_values: list[float],
        higher_is_better: bool,
        warning_percent: float,
        critical_percent: float,
    ) -> RecoveryMetric:
        baseline = self._median_or_none(
            baseline_values
        )

        sample_size = len(baseline_values)

        if current is None:
            return RecoveryMetric(
                current=None,
                baseline=baseline,
                difference=None,
                difference_percent=None,
                status="missing",
                sample_size=sample_size,
            )

        if (
            baseline is None
            or sample_size
            < self.MIN_BASELINE_SAMPLES
            or baseline == 0
        ):
            return RecoveryMetric(
                current=current,
                baseline=baseline,
                difference=None,
                difference_percent=None,
                status="insufficient_baseline",
                sample_size=sample_size,
            )

        difference = current - baseline

        difference_percent = round(
            difference / baseline * 100,
            1,
        )

        if higher_is_better:
            status = self._status_for_lower_value(
                difference_percent=difference_percent,
                warning_percent=warning_percent,
                critical_percent=critical_percent,
            )
        else:
            status = self._status_for_higher_value(
                difference_percent=difference_percent,
                warning_percent=warning_percent,
                critical_percent=critical_percent,
            )

        return RecoveryMetric(
            current=round(current, 2),
            baseline=round(baseline, 2),
            difference=round(difference, 2),
            difference_percent=difference_percent,
            status=status,
            sample_size=sample_size,
        )

    def _build_sleep_score_metric(
        self,
        current: float | None,
        baseline_values: list[float],
    ) -> RecoveryMetric:
        baseline = self._median_or_none(
            baseline_values
        )

        sample_size = len(baseline_values)

        if current is None:
            return RecoveryMetric(
                current=None,
                baseline=baseline,
                difference=None,
                difference_percent=None,
                status="missing",
                sample_size=sample_size,
            )

        difference = (
            current - baseline
            if baseline is not None
            else None
        )

        difference_percent = (
            round(
                difference / baseline * 100,
                1,
            )
            if (
                difference is not None
                and baseline != 0
            )
            else None
        )

        if current < self.SLEEP_SCORE_CRITICAL:
            status = "critical"

        elif current < self.SLEEP_SCORE_WARNING:
            status = "warning"

        elif (
            baseline is None
            or sample_size
            < self.MIN_BASELINE_SAMPLES
        ):
            status = "insufficient_baseline"

        else:
            status = "normal"

        return RecoveryMetric(
            current=round(current, 2),
            baseline=(
                round(baseline, 2)
                if baseline is not None
                else None
            ),
            difference=(
                round(difference, 2)
                if difference is not None
                else None
            ),
            difference_percent=(
                difference_percent
            ),
            status=status,
            sample_size=sample_size,
        )

    def _status_for_lower_value(
        self,
        difference_percent: float,
        warning_percent: float,
        critical_percent: float,
    ) -> str:
        if difference_percent <= critical_percent:
            return "critical"

        if difference_percent <= warning_percent:
            return "warning"

        return "normal"

    def _status_for_higher_value(
        self,
        difference_percent: float,
        warning_percent: float,
        critical_percent: float,
    ) -> str:
        if difference_percent >= critical_percent:
            return "critical"

        if difference_percent >= warning_percent:
            return "warning"

        return "normal"

    def _overall_status(
        self,
        metrics: list[RecoveryMetric],
    ) -> str:
        if not metrics:
            return "unknown"

        critical_count = sum(
            1
            for metric in metrics
            if metric.status == "critical"
        )

        warning_count = sum(
            1
            for metric in metrics
            if metric.status == "warning"
        )

        usable_count = sum(
            1
            for metric in metrics
            if metric.status
            not in {
                "missing",
                "insufficient_baseline",
            }
        )

        if usable_count == 0:
            return "insufficient_data"

        if critical_count >= 1:
            return "poor"

        if warning_count >= 2:
            return "poor"

        if warning_count == 1:
            return "caution"

        return "good"

    def _calculate_form(
        self,
        ctl: float | None,
        atl: float | None,
    ) -> float | None:
        if ctl is None or atl is None:
            return None

        return round(
            ctl - atl,
            2,
        )

    def _build_reasons(
        self,
        hrv: RecoveryMetric,
        resting_hr: RecoveryMetric,
        sleep_duration: RecoveryMetric,
        sleep_score: RecoveryMetric,
        ctl: float | None,
        atl: float | None,
        form: float | None,
    ) -> list[str]:
        reasons: list[str] = []

        if hrv.status in {"warning", "critical"}:
            reasons.append(
                "HRV is below the recent baseline."
            )

        if resting_hr.status in {
            "warning",
            "critical",
        }:
            reasons.append(
                "Resting heart rate is above "
                "the recent baseline."
            )

        if sleep_duration.status in {
            "warning",
            "critical",
        }:
            reasons.append(
                "Sleep duration is below "
                "the recent baseline."
            )

        if sleep_score.status in {
            "warning",
            "critical",
        }:
            reasons.append(
                "Sleep score is low."
            )

        if (
            ctl is not None
            and atl is not None
            and form is not None
            and form < -10
        ):
            reasons.append(
                "Short-term training load is "
                "substantially above chronic load."
            )

        if not reasons:
            reasons.append(
                "No material recovery warning "
                "was detected."
            )

        return reasons

    def _median_or_none(
        self,
        values: list[float],
    ) -> float | None:
        if not values:
            return None

        return float(median(values))

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
                return date.fromisoformat(
                    normalized
                )
            except ValueError as exc:
                raise ValueError(
                    "Date must use YYYY-MM-DD format."
                ) from exc

        raise TypeError(
            "Date must be date, datetime or ISO string."
        )