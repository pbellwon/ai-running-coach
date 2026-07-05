from app.models.athlete_profile import AthleteProfile


class AthleteProfileBuilder:

    def build(self):

        return AthleteProfile(
            total_workouts=0,
            total_distance_km=0,
            average_weekly_distance_km=0,
            longest_run_km=0,
            average_long_run_km=0,
            training_days_per_week=0,
            max_hr=187,
            threshold_hr=None,
            threshold_pace=None,
            easy_pace=None,
        )