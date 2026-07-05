from app.models.goal import Goal


class AthleteGapAnalyzer:

    def analyze(self, goal: Goal, athlete_profile: dict):

        gaps = []

        weekly_distance = athlete_profile.get("weekly_distance_km", 0)
        long_run = athlete_profile.get("long_run_km", 0)
        threshold_pace = athlete_profile.get("threshold_pace")
        easy_pace = athlete_profile.get("easy_pace")

        if goal.distance_km == 10:

            if weekly_distance < 50:
                gaps.append({
                    "area": "aerobic_endurance",
                    "priority": 1,
                    "reason": "Weekly volume below recommended range."
                })

            if long_run < 16:
                gaps.append({
                    "area": "long_run",
                    "priority": 2,
                    "reason": "Long run shorter than recommended."
                })

            if threshold_pace is None:
                gaps.append({
                    "area": "threshold",
                    "priority": 3,
                    "reason": "Threshold pace not established."
                })

            if easy_pace is None:
                gaps.append({
                    "area": "running_economy",
                    "priority": 4,
                    "reason": "Easy pace profile unavailable."
                })

        gaps.sort(key=lambda g: g["priority"])

        return gaps