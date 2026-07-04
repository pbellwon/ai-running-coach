class DataNormalizer:
    @staticmethod
    def normalize_running_cadence(cadence):
        if cadence is None:
            return None

        if cadence == 0:
            return None

        if cadence < 120:
            return cadence * 2

        return cadence

    @staticmethod
    def is_moving_record(speed, cadence):
        if speed is None:
            return False

        if speed < 1.5:
            return False

        if cadence is not None and cadence == 0:
            return False

        return True

    @staticmethod
    def pace_min_per_km(speed_mps):
        if not speed_mps or speed_mps <= 0:
            return None

        return 1000 / speed_mps / 60