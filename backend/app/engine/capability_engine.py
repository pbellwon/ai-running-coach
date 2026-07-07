from app.models.athlete_profile import AthleteProfile
from app.models.current_fitness import CurrentFitness
from app.models.capability import Capability


class CapabilityEngine:

    def analyze(
        self,
        athlete: AthleteProfile,
        current: CurrentFitness,
    ) -> list[Capability]:

        return [
            self._aerobic_endurance(athlete, current),
            self._strength(athlete, current),
        ]

    def _aerobic_endurance(
        self,
        athlete: AthleteProfile,
        current: CurrentFitness,
    ) -> Capability:

        score = 0
        evidence = []

        if current.average_weekly_distance_km >= 55:
            score += 35
            evidence.append("Current weekly running volume is strong.")
        elif current.average_weekly_distance_km >= 40:
            score += 25
            evidence.append("Current weekly running volume is moderate.")
        else:
            score += 15
            evidence.append("Current weekly running volume is low.")

        if current.longest_run_km >= 20:
            score += 25
            evidence.append("Recent long run capacity is solid.")
        elif current.longest_run_km >= 15:
            score += 15
            evidence.append("Recent long run capacity is moderate.")
        else:
            score += 5
            evidence.append("Recent long run capacity is limited.")

        if current.consistency >= 85:
            score += 25
            evidence.append("Training consistency is high.")
        elif current.consistency >= 65:
            score += 15
            evidence.append("Training consistency is acceptable.")
        else:
            score += 5
            evidence.append("Training consistency is low.")

        if athlete.running_distance_km >= 5000:
            score += 15
            evidence.append("Long-term running history is strong.")
        else:
            score += 5
            evidence.append("Long-term running history is limited.")

        return Capability(
            area="aerobic_endurance",
            score=min(score, 100),
            confidence=0.75,
            evidence=evidence,
        )

    def _strength(
        self,
        athlete: AthleteProfile,
        current: CurrentFitness,
    ) -> Capability:

        score = 0
        evidence = []

        if current.strength_hours >= 6:
            score += 60
            evidence.append("Recent strength training volume is strong.")
        elif current.strength_hours >= 3:
            score += 40
            evidence.append("Recent strength training volume is moderate.")
        else:
            score += 20
            evidence.append("Recent strength training volume is low.")

        if athlete.strength_hours >= 100:
            score += 40
            evidence.append("Long-term strength training history is strong.")
        elif athlete.strength_hours >= 40:
            score += 25
            evidence.append("Long-term strength training history is moderate.")
        else:
            score += 10
            evidence.append("Long-term strength training history is limited.")

        return Capability(
            area="strength",
            score=min(score, 100),
            confidence=0.7,
            evidence=evidence,
        )