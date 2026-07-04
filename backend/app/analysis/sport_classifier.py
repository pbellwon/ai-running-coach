class SportClassifier:
    PRIMARY = {"running"}

    ENDURANCE_CROSS_TRAINING = {
        "cycling",
        "swimming",
        "hiking",
        "walking",
    }

    STRENGTH = {
        "training",
        "fitness_equipment",
    }

    OTHER = {
        "kayaking",
        "surfing",
        "stand_up_paddleboarding",
        "mountaineering",
    }

    def classify(self, sport: str) -> str:
        if sport in self.PRIMARY:
            return "primary_running"

        if sport in self.ENDURANCE_CROSS_TRAINING:
            return "endurance_cross_training"

        if sport in self.STRENGTH:
            return "strength"

        return "other"