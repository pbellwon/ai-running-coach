from __future__ import annotations

from datetime import date

from app.models.executed_session import ExecutedSession
from app.models.goal import Goal
from app.models.goal_progress import (
    CapabilityTrend,
    GoalProgress,
)


class GoalProgressEngine:
    """
    Evaluates athlete progress toward a performance goal.

    Sprint 26 MVP uses deterministic capability trends
    comparing recent and previous training windows.
    """

    AEROBIC_BASE_IMPROVING_THRESHOLD = 0.10
    AEROBIC_BASE_DECLINING_THRESHOLD = -0.10

    LONG_RUN_MIN_DISTANCE_KM = 15.0
    LONG_RUN_MIN_DURATION_MIN = 80.0

    LONG_RUN_IMPROVING_THRESHOLD = 0.10
    LONG_RUN_DECLINING_THRESHOLD = -0.10

    THRESHOLD_TYPES = {
        "threshold",
        "tempo",
        "tempo_run",
    }

    THRESHOLD_IMPROVING_THRESHOLD = 0.10
    THRESHOLD_DECLINING_THRESHOLD = -0.10

    HIGH_AEROBIC_TYPES = {
        "vo2max",
        "intervals",
    }

    HIGH_AEROBIC_IMPROVING_THRESHOLD = 0.10
    HIGH_AEROBIC_DECLINING_THRESHOLD = -0.10

    RACE_TYPE = "race"

    RACE_DISTANCE_TOLERANCE = 0.05

    RACE_IMPROVING_THRESHOLD = 0.01
    RACE_DECLINING_THRESHOLD = -0.01

    def analyze(
        self,
        goal: Goal,
        target_date: date,
        recent_sessions: list[ExecutedSession],
        previous_sessions: list[ExecutedSession],
    ) -> GoalProgress:
        capabilities = [
            self.analyze_aerobic_base(
                recent_sessions=recent_sessions,
                previous_sessions=previous_sessions,
            ),
            self.analyze_long_run_durability(
                recent_sessions=recent_sessions,
                previous_sessions=previous_sessions,
            ),
            self.analyze_threshold_development(
                recent_sessions=recent_sessions,
                previous_sessions=previous_sessions,
            ),
            self.analyze_high_aerobic_development(
                recent_sessions=recent_sessions,
                previous_sessions=previous_sessions,
            ),
            self.analyze_race_performance(
                recent_sessions=recent_sessions,
                previous_sessions=previous_sessions,
            ),
        ]

        fitness_trend = self._overall_fitness_trend(
            capabilities
        )

        status = self._goal_progress_status(
            fitness_trend=fitness_trend,
            capabilities=capabilities,
        )

        primary_limiter, secondary_limiter = (
            self._select_limiters(
                capabilities
            )
        )

        confidence = self._overall_confidence(
            capabilities
        )

        goal_gap = self._goal_gap(
            capabilities
        )

        evidence = self._overall_evidence(
            capabilities=capabilities,
            fitness_trend=fitness_trend,
        )

        return GoalProgress(
            target_date=target_date,
            goal_distance_km=goal.distance_km or 0,
            target_time_sec=goal.target_time_sec or 0,
            status=status,
            confidence=confidence,
            fitness_trend=fitness_trend,
            goal_gap=goal_gap,
            primary_limiter=primary_limiter,
            secondary_limiter=secondary_limiter,
            capabilities=capabilities,
            evidence=evidence,
        )

    def analyze_aerobic_base(
        self,
        recent_sessions: list[ExecutedSession],
        previous_sessions: list[ExecutedSession],
    ) -> CapabilityTrend:
        recent_running = self._running_sessions(
            recent_sessions
        )

        previous_running = self._running_sessions(
            previous_sessions
        )

        recent_distance = self._sum_distance(
            recent_running
        )

        previous_distance = self._sum_distance(
            previous_running
        )

        if (
            not recent_running
            and not previous_running
        ):
            return CapabilityTrend(
                area="aerobic_base",
                status="insufficient_evidence",
                trend=None,
                confidence=0.0,
                evidence=[
                    "No running sessions were available "
                    "in either comparison window."
                ],
            )

        if previous_distance <= 0:
            return CapabilityTrend(
                area="aerobic_base",
                status="insufficient_evidence",
                trend=None,
                confidence=0.3,
                evidence=[
                    "The previous comparison window "
                    "contains insufficient running volume."
                ],
            )

        trend = (
            recent_distance
            - previous_distance
        ) / previous_distance

        status = self._trend_status(
            trend
        )

        confidence = self._aerobic_confidence(
            recent_sessions=recent_running,
            previous_sessions=previous_running,
        )

        evidence = [
            (
                f"Recent running distance: "
                f"{recent_distance:.1f} km."
            ),
            (
                f"Previous running distance: "
                f"{previous_distance:.1f} km."
            ),
            (
                f"Running volume changed by "
                f"{trend * 100:.1f}%."
            ),
        ]

        return CapabilityTrend(
            area="aerobic_base",
            status=status,
            trend=round(
                trend,
                3,
            ),
            confidence=confidence,
            evidence=evidence,
        )

    def analyze_long_run_durability(
        self,
        recent_sessions: list[ExecutedSession],
        previous_sessions: list[ExecutedSession],
    ) -> CapabilityTrend:
        recent_long_runs = self._long_run_sessions(
            recent_sessions
        )

        previous_long_runs = self._long_run_sessions(
            previous_sessions
        )

        if (
            not recent_long_runs
            and not previous_long_runs
        ):
            return CapabilityTrend(
                area="long_run_durability",
                status="insufficient_evidence",
                trend=None,
                confidence=0.0,
                evidence=[
                    "No long-run sessions were available "
                    "in either comparison window."
                ],
            )

        recent_longest = self._longest_distance(
            recent_long_runs
        )

        previous_longest = self._longest_distance(
            previous_long_runs
        )

        if previous_longest <= 0:
            return CapabilityTrend(
                area="long_run_durability",
                status="insufficient_evidence",
                trend=None,
                confidence=0.3,
                evidence=[
                    "The previous comparison window "
                    "contains insufficient long-run evidence."
                ],
            )

        trend = (
            recent_longest
            - previous_longest
        ) / previous_longest

        status = self._long_run_trend_status(
            trend
        )

        confidence = self._long_run_confidence(
            recent_sessions=recent_long_runs,
            previous_sessions=previous_long_runs,
        )

        evidence = [
            (
                f"Recent longest run: "
                f"{recent_longest:.1f} km."
            ),
            (
                f"Previous longest run: "
                f"{previous_longest:.1f} km."
            ),
            (
                f"Longest-run distance changed by "
                f"{trend * 100:.1f}%."
            ),
        ]

        return CapabilityTrend(
            area="long_run_durability",
            status=status,
            trend=round(
                trend,
                3,
            ),
            confidence=confidence,
            evidence=evidence,
        )

    def analyze_threshold_development(
        self,
        recent_sessions: list[ExecutedSession],
        previous_sessions: list[ExecutedSession],
    ) -> CapabilityTrend:
        recent_threshold = self._threshold_sessions(
            recent_sessions
        )

        previous_threshold = self._threshold_sessions(
            previous_sessions
        )

        if (
            not recent_threshold
            and not previous_threshold
        ):
            return CapabilityTrend(
                area="threshold_development",
                status="insufficient_evidence",
                trend=None,
                confidence=0.0,
                evidence=[
                    "No threshold-oriented sessions were "
                    "available in either comparison window."
                ],
            )

        recent_duration = self._sum_duration(
            recent_threshold
        )

        previous_duration = self._sum_duration(
            previous_threshold
        )

        if previous_duration <= 0:
            return CapabilityTrend(
                area="threshold_development",
                status="insufficient_evidence",
                trend=None,
                confidence=0.3,
                evidence=[
                    "The previous comparison window "
                    "contains insufficient threshold evidence."
                ],
            )

        trend = (
            recent_duration
            - previous_duration
        ) / previous_duration

        status = self._threshold_trend_status(
            trend
        )

        confidence = self._threshold_confidence(
            recent_sessions=recent_threshold,
            previous_sessions=previous_threshold,
        )

        evidence = [
            (
                f"Recent threshold-oriented sessions: "
                f"{len(recent_threshold)}."
            ),
            (
                f"Previous threshold-oriented sessions: "
                f"{len(previous_threshold)}."
            ),
            (
                f"Recent threshold-session duration: "
                f"{recent_duration:.1f} min."
            ),
            (
                f"Previous threshold-session duration: "
                f"{previous_duration:.1f} min."
            ),
            (
                f"Threshold-session duration changed by "
                f"{trend * 100:.1f}%."
            ),
        ]

        return CapabilityTrend(
            area="threshold_development",
            status=status,
            trend=round(
                trend,
                3,
            ),
            confidence=confidence,
            evidence=evidence,
        )

    def analyze_high_aerobic_development(
        self,
        recent_sessions: list[ExecutedSession],
        previous_sessions: list[ExecutedSession],
    ) -> CapabilityTrend:
        recent_high_aerobic = self._high_aerobic_sessions(
            recent_sessions
        )

        previous_high_aerobic = self._high_aerobic_sessions(
            previous_sessions
        )

        if (
            not recent_high_aerobic
            and not previous_high_aerobic
        ):
            return CapabilityTrend(
                area="high_aerobic_development",
                status="insufficient_evidence",
                trend=None,
                confidence=0.0,
                evidence=[
                    "No high-aerobic sessions were available "
                    "in either comparison window."
                ],
            )

        recent_duration = self._sum_duration(
            recent_high_aerobic
        )

        previous_duration = self._sum_duration(
            previous_high_aerobic
        )

        if previous_duration <= 0:
            return CapabilityTrend(
                area="high_aerobic_development",
                status="insufficient_evidence",
                trend=None,
                confidence=0.3,
                evidence=[
                    "The previous comparison window "
                    "contains insufficient high-aerobic evidence."
                ],
            )

        trend = (
            recent_duration
            - previous_duration
        ) / previous_duration

        status = self._high_aerobic_trend_status(
            trend
        )

        confidence = self._high_aerobic_confidence(
            recent_sessions=recent_high_aerobic,
            previous_sessions=previous_high_aerobic,
        )

        evidence = [
            (
                f"Recent high-aerobic sessions: "
                f"{len(recent_high_aerobic)}."
            ),
            (
                f"Previous high-aerobic sessions: "
                f"{len(previous_high_aerobic)}."
            ),
            (
                f"Recent high-aerobic session duration: "
                f"{recent_duration:.1f} min."
            ),
            (
                f"Previous high-aerobic session duration: "
                f"{previous_duration:.1f} min."
            ),
            (
                f"High-aerobic session duration changed by "
                f"{trend * 100:.1f}%."
            ),
        ]

        return CapabilityTrend(
            area="high_aerobic_development",
            status=status,
            trend=round(
                trend,
                3,
            ),
            confidence=confidence,
            evidence=evidence,
        )

    def analyze_race_performance(
        self,
        recent_sessions: list[ExecutedSession],
        previous_sessions: list[ExecutedSession],
    ) -> CapabilityTrend:
        recent_races = self._race_sessions(
            recent_sessions
        )

        previous_races = self._race_sessions(
            previous_sessions
        )

        if (
            not recent_races
            or not previous_races
        ):
            return CapabilityTrend(
                area="race_performance",
                status="insufficient_evidence",
                trend=None,
                confidence=0.3,
                evidence=[
                    "Comparable race evidence is not available "
                    "in both comparison windows."
                ],
            )

        comparable_pairs = (
            self._comparable_race_pairs(
                recent_races=recent_races,
                previous_races=previous_races,
            )
        )

        if not comparable_pairs:
            return CapabilityTrend(
                area="race_performance",
                status="insufficient_evidence",
                trend=None,
                confidence=0.3,
                evidence=[
                    "Race sessions were found, but no "
                    "comparable race distances were available."
                ],
            )

        recent_race, previous_race = max(
            comparable_pairs,
            key=lambda pair: (
                pair[0].total_distance_km
                or 0
            ),
        )

        recent_pace = self._pace_min_per_km(
            recent_race
        )

        previous_pace = self._pace_min_per_km(
            previous_race
        )

        if (
            recent_pace is None
            or previous_pace is None
            or previous_pace <= 0
        ):
            return CapabilityTrend(
                area="race_performance",
                status="insufficient_evidence",
                trend=None,
                confidence=0.3,
                evidence=[
                    "Comparable race sessions do not contain "
                    "sufficient pace data."
                ],
            )

        trend = (
            previous_pace
            - recent_pace
        ) / previous_pace

        status = self._race_trend_status(
            trend
        )

        confidence = self._race_confidence(
            recent_races=recent_races,
            previous_races=previous_races,
        )

        evidence = [
            (
                f"Recent comparable race: "
                f"{recent_race.total_distance_km:.2f} km "
                f"at {recent_pace:.3f} min/km."
            ),
            (
                f"Previous comparable race: "
                f"{previous_race.total_distance_km:.2f} km "
                f"at {previous_pace:.3f} min/km."
            ),
            (
                f"Race pace changed by "
                f"{trend * 100:.1f}%."
            ),
        ]

        return CapabilityTrend(
            area="race_performance",
            status=status,
            trend=round(
                trend,
                3,
            ),
            confidence=confidence,
            evidence=evidence,
        )

    def _overall_fitness_trend(
        self,
        capabilities: list[CapabilityTrend],
    ) -> str:
        available = [
            capability
            for capability in capabilities
            if capability.status
            != "insufficient_evidence"
        ]

        if not available:
            return "insufficient_evidence"

        race_performance = next(
            (
                capability
                for capability in capabilities
                if capability.area
                == "race_performance"
            ),
            None,
        )

        if (
            race_performance is not None
            and race_performance.status
            == "declining"
        ):
            return "declining"

        improving = sum(
            capability.status == "improving"
            for capability in available
        )

        declining = sum(
            capability.status == "declining"
            for capability in available
        )

        if improving > declining:
            return "improving"

        if declining > improving:
            return "stable"

        return "stable"

    def _goal_progress_status(
        self,
        fitness_trend: str,
        capabilities: list[CapabilityTrend] | None = None,
    ) -> str:
        capabilities = capabilities or []

        race_performance = next(
            (
                capability
                for capability in capabilities
                if capability.area
                == "race_performance"
            ),
            None,
        )

        if (
            race_performance is not None
            and race_performance.status
            == "declining"
        ):
            return "regressing"

        if fitness_trend == "improving":
            return "progressing"

        if fitness_trend == "stable":
            return "stable"

        if fitness_trend == "declining":
            return "stable"

        return "insufficient_evidence"

    def _select_limiters(
        self,
        capabilities: list[CapabilityTrend],
    ) -> tuple[str | None, str | None]:
        """
        Sprint 26 intentionally does not infer physiological
        limiters from training-exposure trends alone.

        Current capability trends describe changes in training
        exposure or race performance. Reduced exposure is not
        sufficient evidence that a capability is an athlete's
        limiting factor.

        Limiter inference will require stronger evidence from
        workout execution, performance response, and longer-term
        athlete history.
        """

        return None, None

    def _overall_confidence(
        self,
        capabilities: list[CapabilityTrend],
    ) -> float:
        if not capabilities:
            return 0.0

        values = [
            capability.confidence
            for capability in capabilities
        ]

        return round(
            sum(values) / len(values),
            2,
        )

    def _goal_gap(
        self,
        capabilities: list[CapabilityTrend],
    ) -> str:
        race = next(
            (
                capability
                for capability in capabilities
                if capability.area
                == "race_performance"
            ),
            None,
        )

        if (
            race is None
            or race.status
            == "insufficient_evidence"
        ):
            return "unknown"

        if race.status == "improving":
            return "narrowing"

        if race.status == "declining":
            return "widening"

        return "stable"

    def _overall_evidence(
        self,
        capabilities: list[CapabilityTrend],
        fitness_trend: str,
    ) -> list[str]:
        improving = [
            capability.area
            for capability in capabilities
            if capability.status == "improving"
        ]

        stable = [
            capability.area
            for capability in capabilities
            if capability.status == "stable"
        ]

        declining = [
            capability.area
            for capability in capabilities
            if capability.status == "declining"
        ]

        insufficient = [
            capability.area
            for capability in capabilities
            if capability.status
            == "insufficient_evidence"
        ]

        evidence = [
            (
                f"Overall fitness trend: "
                f"{fitness_trend}."
            )
        ]

        if improving:
            evidence.append(
                "Improving capabilities: "
                + ", ".join(improving)
                + "."
            )

        if stable:
            evidence.append(
                "Stable capabilities: "
                + ", ".join(stable)
                + "."
            )

        if declining:
            evidence.append(
                "Declining capabilities: "
                + ", ".join(declining)
                + "."
            )

        if insufficient:
            evidence.append(
                "Insufficient evidence for: "
                + ", ".join(insufficient)
                + "."
            )

        return evidence

    def _running_sessions(
        self,
        sessions: list[ExecutedSession],
    ) -> list[ExecutedSession]:
        return [
            session
            for session in sessions
            if session.sport_family == "running"
        ]

    def _long_run_sessions(
        self,
        sessions: list[ExecutedSession],
    ) -> list[ExecutedSession]:
        return [
            session
            for session in sessions
            if (
                session.sport_family == "running"
                and (
                    session.total_distance_km
                    or 0
                )
                >= self.LONG_RUN_MIN_DISTANCE_KM
                and (
                    session.total_duration_min
                    or 0
                )
                >= self.LONG_RUN_MIN_DURATION_MIN
            )
        ]

    def _threshold_sessions(
        self,
        sessions: list[ExecutedSession],
    ) -> list[ExecutedSession]:
        return [
            session
            for session in sessions
            if (
                session.sport_family == "running"
                and session.workout_type
                in self.THRESHOLD_TYPES
            )
        ]

    def _high_aerobic_sessions(
        self,
        sessions: list[ExecutedSession],
    ) -> list[ExecutedSession]:
        return [
            session
            for session in sessions
            if (
                session.sport_family == "running"
                and session.workout_type
                in self.HIGH_AEROBIC_TYPES
            )
        ]

    def _race_sessions(
        self,
        sessions: list[ExecutedSession],
    ) -> list[ExecutedSession]:
        return [
            session
            for session in sessions
            if (
                session.sport_family == "running"
                and session.workout_type
                == self.RACE_TYPE
                and (
                    session.total_distance_km
                    or 0
                ) > 0
                and (
                    session.total_duration_min
                    or 0
                ) > 0
            )
        ]

    def _comparable_race_pairs(
        self,
        recent_races: list[ExecutedSession],
        previous_races: list[ExecutedSession],
    ) -> list[
        tuple[
            ExecutedSession,
            ExecutedSession,
        ]
    ]:
        pairs = []

        for recent in recent_races:
            for previous in previous_races:
                recent_distance = (
                    recent.total_distance_km
                    or 0
                )

                previous_distance = (
                    previous.total_distance_km
                    or 0
                )

                if previous_distance <= 0:
                    continue

                difference = abs(
                    recent_distance
                    - previous_distance
                )

                tolerance = (
                    previous_distance
                    * self.RACE_DISTANCE_TOLERANCE
                )

                if difference <= tolerance:
                    pairs.append(
                        (
                            recent,
                            previous,
                        )
                    )

        return pairs

    def _pace_min_per_km(
        self,
        session: ExecutedSession,
    ) -> float | None:
        distance = (
            session.total_distance_km
            or 0
        )

        duration = (
            session.total_duration_min
            or 0
        )

        if (
            distance <= 0
            or duration <= 0
        ):
            return None

        return duration / distance

    def _sum_distance(
        self,
        sessions: list[ExecutedSession],
    ) -> float:
        return sum(
            session.total_distance_km or 0
            for session in sessions
        )

    def _sum_duration(
        self,
        sessions: list[ExecutedSession],
    ) -> float:
        return sum(
            session.total_duration_min or 0
            for session in sessions
        )

    def _longest_distance(
        self,
        sessions: list[ExecutedSession],
    ) -> float:
        return max(
            (
                session.total_distance_km
                or 0
            )
            for session in sessions
        ) if sessions else 0.0

    def _trend_status(
        self,
        trend: float,
    ) -> str:
        if (
            trend
            >= self.AEROBIC_BASE_IMPROVING_THRESHOLD
        ):
            return "improving"

        if (
            trend
            <= self.AEROBIC_BASE_DECLINING_THRESHOLD
        ):
            return "declining"

        return "stable"

    def _long_run_trend_status(
        self,
        trend: float,
    ) -> str:
        if (
            trend
            >= self.LONG_RUN_IMPROVING_THRESHOLD
        ):
            return "improving"

        if (
            trend
            <= self.LONG_RUN_DECLINING_THRESHOLD
        ):
            return "declining"

        return "stable"

    def _threshold_trend_status(
        self,
        trend: float,
    ) -> str:
        if (
            trend
            >= self.THRESHOLD_IMPROVING_THRESHOLD
        ):
            return "improving"

        if (
            trend
            <= self.THRESHOLD_DECLINING_THRESHOLD
        ):
            return "declining"

        return "stable"

    def _high_aerobic_trend_status(
        self,
        trend: float,
    ) -> str:
        if (
            trend
            >= self.HIGH_AEROBIC_IMPROVING_THRESHOLD
        ):
            return "improving"

        if (
            trend
            <= self.HIGH_AEROBIC_DECLINING_THRESHOLD
        ):
            return "declining"

        return "stable"

    def _race_trend_status(
        self,
        trend: float,
    ) -> str:
        if (
            trend
            >= self.RACE_IMPROVING_THRESHOLD
        ):
            return "improving"

        if (
            trend
            <= self.RACE_DECLINING_THRESHOLD
        ):
            return "declining"

        return "stable"

    def _aerobic_confidence(
        self,
        recent_sessions: list[ExecutedSession],
        previous_sessions: list[ExecutedSession],
    ) -> float:
        total_sessions = (
            len(recent_sessions)
            + len(previous_sessions)
        )

        if total_sessions >= 16:
            return 0.9

        if total_sessions >= 10:
            return 0.8

        if total_sessions >= 6:
            return 0.7

        if total_sessions >= 4:
            return 0.6

        return 0.4

    def _long_run_confidence(
        self,
        recent_sessions: list[ExecutedSession],
        previous_sessions: list[ExecutedSession],
    ) -> float:
        total_long_runs = (
            len(recent_sessions)
            + len(previous_sessions)
        )

        if total_long_runs >= 8:
            return 0.9

        if total_long_runs >= 6:
            return 0.8

        if total_long_runs >= 4:
            return 0.7

        if total_long_runs >= 2:
            return 0.6

        return 0.4

    def _threshold_confidence(
        self,
        recent_sessions: list[ExecutedSession],
        previous_sessions: list[ExecutedSession],
    ) -> float:
        total_sessions = (
            len(recent_sessions)
            + len(previous_sessions)
        )

        if total_sessions >= 8:
            return 0.9

        if total_sessions >= 6:
            return 0.8

        if total_sessions >= 4:
            return 0.7

        if total_sessions >= 2:
            return 0.6

        return 0.4

    def _high_aerobic_confidence(
        self,
        recent_sessions: list[ExecutedSession],
        previous_sessions: list[ExecutedSession],
    ) -> float:
        total_sessions = (
            len(recent_sessions)
            + len(previous_sessions)
        )

        if total_sessions >= 8:
            return 0.9

        if total_sessions >= 6:
            return 0.8

        if total_sessions >= 4:
            return 0.7

        if total_sessions >= 2:
            return 0.6

        return 0.4

    def _race_confidence(
        self,
        recent_races: list[ExecutedSession],
        previous_races: list[ExecutedSession],
    ) -> float:
        total_races = (
            len(recent_races)
            + len(previous_races)
        )

        if total_races >= 6:
            return 0.9

        if total_races >= 4:
            return 0.8

        if total_races >= 2:
            return 0.7

        return 0.4