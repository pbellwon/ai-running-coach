class StrengthScoreCalculator:

    def calculate(self, athlete):
        if athlete.strength_hours >= 150:
            return 90

        if athlete.strength_hours >= 80:
            return 75

        if athlete.strength_hours >= 40:
            return 55

        return 30