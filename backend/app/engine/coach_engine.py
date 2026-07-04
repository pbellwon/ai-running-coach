from app.models.workout import Workout


class CoachEngine:

    def make_recommendation(self, metrics: dict):

        intensity = metrics["intensity_score"]
        category = metrics["load_category"]

        if category == "hard":
            return {
                "decision": "reduce_load",
                "message": "Very hard session detected. Next day should be easy or rest.",
                "reasoning": [
                    "High intensity session increases fatigue risk",
                    "Recovery needed to avoid performance drop"
                ]
            }

        if category == "moderate":
            return {
                "decision": "maintain_plan",
                "message": "Training load is balanced. Continue as planned.",
                "reasoning": [
                    "No signs of excessive fatigue",
                    "Training stimulus is adequate"
                ]
            }

        return {
            "decision": "optional_hard_session",
            "message": "Low intensity detected. You may add quality session if feeling good.",
            "reasoning": [
                "Low fatigue level",
                "Opportunity for adaptive overload"
            ]
        }