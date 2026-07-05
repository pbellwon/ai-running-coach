class DataNormalizer:
    @staticmethod
    def normalize_running_cadence(cadence):
        if cadence is None or cadence == 0:
            return None

        if cadence < 120:
            return cadence * 2

        return cadence

    @staticmethod
    def classify_activity_state(speed, cadence):
        if speed is None:
            return "unknown"

        if speed < 0.3:
            return "standing"

        if speed < 1.8:
            return "walking"

        cadence_norm = DataNormalizer.normalize_running_cadence(cadence)

        if cadence_norm and cadence_norm >= 140:
            return "running"

        if speed >= 1.8:
            return "running"

        return "unknown"

    @staticmethod
    def is_moving_record(speed, cadence):
        return DataNormalizer.classify_activity_state(speed, cadence) in {
            "walking",
            "running",
        }

    @staticmethod
    def is_running_record(speed, cadence):
        return DataNormalizer.classify_activity_state(speed, cadence) == "running"

    @staticmethod
    def pace_min_per_km(speed_mps):
        if not speed_mps or speed_mps <= 0:
            return None

        return 1000 / speed_mps / 60