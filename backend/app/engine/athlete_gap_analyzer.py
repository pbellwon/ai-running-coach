from app.engine.scores.aerobic_score import AerobicScoreCalculator
from app.engine.scores.strength_score import StrengthScoreCalculator

from app.models.goal import Goal
from app.models.gap import Gap
from app.models.athlete_profile import AthleteProfile


class AthleteGapAnalyzer:

    def __init__(self):
        self.aerobic = AerobicScoreCalculator()
        self.strength = StrengthScoreCalculator()

    def analyze(
        self,
        goal: Goal,
        athlete: AthleteProfile,
    ) -> list[Gap]:

        gaps = []

        aerobic = self._aerobic_gap(goal, athlete)
        if aerobic:
            gaps.append(aerobic)

        strength = self._strength_gap(goal, athlete)
        if strength:
            gaps.append(strength)

        gaps.sort(key=lambda g: g.gap, reverse=True)

        return gaps

    def _aerobic_gap(self, goal, athlete):

        score = self.aerobic.calculate(athlete)

        target = self._target_aerobic_score(goal)

        return Gap(
            area="aerobic_endurance",
            current_score=score,
            target_score=target,
            reason="Current aerobic base compared to goal requirements.",
        )

    def _strength_gap(self, goal, athlete):

        score = self.strength.calculate(athlete)

        target = 70

        return Gap(
            area="strength",
            current_score=score,
            target_score=target,
            reason="Current strength support compared to goal requirements.",
        )

    def _target_aerobic_score(self, goal):

        if goal.distance_km <= 5:
            return 70

        if goal.distance_km <= 10:
            return 80

        if goal.distance_km <= 21.1:
            return 90

        return 95