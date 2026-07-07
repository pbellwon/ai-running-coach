from app.models.goal import Goal
from app.models.gap import Gap
from app.models.capability import Capability


class AthleteGapAnalyzer:

    def analyze(
        self,
        goal: Goal,
        capabilities: list[Capability],
    ) -> list[Gap]:

        gaps = []

        for capability in capabilities:
            target = self._target_score(goal, capability.area)

            if target is None:
                continue

            gaps.append(
                Gap(
                    area=capability.area,
                    current_score=capability.score,
                    target_score=target,
                    reason=self._reason(capability.area),
                )
            )

        gaps.sort(key=lambda g: g.gap, reverse=True)

        return gaps

    def _target_score(self, goal: Goal, area: str):

        if goal.distance_km <= 5:
            targets = {
                "aerobic_endurance": 70,
                "strength": 70,
            }

        elif goal.distance_km <= 10:
            targets = {
                "aerobic_endurance": 80,
                "strength": 70,
            }

        elif goal.distance_km <= 21.1:
            targets = {
                "aerobic_endurance": 90,
                "strength": 65,
            }

        else:
            targets = {
                "aerobic_endurance": 95,
                "strength": 60,
            }

        return targets.get(area)

    def _reason(self, area: str):

        reasons = {
            "aerobic_endurance": "Aerobic capability compared to goal requirements.",
            "strength": "Strength capability compared to goal requirements.",
        }

        return reasons.get(area, "Capability compared to goal requirements.")