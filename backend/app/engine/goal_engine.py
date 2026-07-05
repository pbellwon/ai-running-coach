from datetime import date

from app.models.goal import Goal


class GoalEngine:

    def evaluate(self, goal: Goal):
        target_pace = self._target_pace(goal)
        days_remaining = self._days_remaining(goal)
        weeks_remaining = self._weeks_remaining(days_remaining)

        return {
            "goal_type": goal.goal_type,
            "distance_km": goal.distance_km,
            "target_time_sec": goal.target_time_sec,
            "target_pace_min_per_km": target_pace,
            "target_date": goal.target_date.isoformat() if goal.target_date else None,
            "days_remaining": days_remaining,
            "weeks_remaining": weeks_remaining,
            "requirements": self._requirements(goal.distance_km),
            "priority": goal.priority,
            "notes": goal.notes,
        }

    def summarize(self, goal: Goal):
        return self.evaluate(goal)

    def _target_pace(self, goal: Goal):
        if not goal.distance_km or not goal.target_time_sec:
            return None

        return round(goal.target_time_sec / goal.distance_km / 60, 2)

    def _days_remaining(self, goal: Goal):
        if not goal.target_date:
            return None

        return (goal.target_date - date.today()).days

    def _weeks_remaining(self, days_remaining):
        if days_remaining is None:
            return None

        return round(days_remaining / 7, 1)

    def _requirements(self, distance_km):
        if distance_km is None:
            return {}

        if distance_km <= 5:
            return {
                "weekly_distance_km": "35-55",
                "quality_sessions_per_week": 2,
                "long_run_km": "12-18",
                "strength_sessions_per_week": 2,
                "key_focus": ["speed", "VO2max", "running economy"],
            }

        if distance_km <= 10:
            return {
                "weekly_distance_km": "45-70",
                "quality_sessions_per_week": 2,
                "long_run_km": "14-22",
                "strength_sessions_per_week": 2,
                "key_focus": ["threshold", "VO2max", "running economy"],
            }

        if distance_km <= 21.1:
            return {
                "weekly_distance_km": "55-85",
                "quality_sessions_per_week": 2,
                "long_run_km": "18-28",
                "strength_sessions_per_week": 1,
                "key_focus": ["threshold", "aerobic endurance", "fatigue resistance"],
            }

        return {
            "weekly_distance_km": "65-110",
            "quality_sessions_per_week": 2,
            "long_run_km": "24-34",
            "strength_sessions_per_week": 1,
            "key_focus": ["aerobic endurance", "fueling", "fatigue resistance"],
        }