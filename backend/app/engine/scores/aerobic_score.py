class AerobicScoreCalculator:

    def calculate(self, athlete):
        score = 0

        if athlete.running_distance_km >= 8000:
            score += 30
        elif athlete.running_distance_km >= 4000:
            score += 20
        else:
            score += 10

        if athlete.average_weekly_distance_km >= 60:
            score += 30
        elif athlete.average_weekly_distance_km >= 45:
            score += 20
        else:
            score += 10

        if athlete.running_hours >= 700:
            score += 25
        elif athlete.running_hours >= 400:
            score += 18
        else:
            score += 10

        if athlete.longest_run_km >= 25:
            score += 15
        elif athlete.longest_run_km >= 18:
            score += 10
        else:
            score += 5

        return min(score, 100)