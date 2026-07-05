class GoalFeasibility:

    def evaluate(self, goal_summary: dict):

        weeks = goal_summary.get("weeks_remaining")

        if weeks is None:
            return {
                "status": "unknown",
                "reason": "Target date not provided."
            }

        distance = goal_summary.get("distance_km")

        minimum_weeks = {
            5: 8,
            10: 10,
            21.1: 12,
            42.2: 16,
        }

        required = minimum_weeks.get(distance)

        if required is None:
            return {
                "status": "unknown",
                "reason": "Unsupported distance."
            }

        if weeks >= required:
            return {
                "status": "feasible",
                "required_weeks": required,
                "available_weeks": weeks,
            }

        return {
            "status": "aggressive",
            "required_weeks": required,
            "available_weeks": weeks,
            "missing_weeks": round(required - weeks, 1),
        }