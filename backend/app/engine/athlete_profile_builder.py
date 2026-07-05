from app.analysis.statistics_engine import StatisticsEngine
from app.models.athlete_profile import AthleteProfile


class AthleteProfileBuilder:

    def __init__(self):
        self.statistics = StatisticsEngine()

    def build(self):

        return AthleteProfile(
            
            total_workouts=self.statistics.total_workouts(),

            total_distance_km=self.statistics.total_distance_km(),

            average_weekly_distance_km=self._average_weekly_distance(),

            running_workouts=self.statistics.running_workouts(),

            running_distance_km=self.statistics.running_distance_km(),

            running_hours=self.statistics.running_hours(),

            cross_training_hours=self.statistics.cross_training_hours(),

            strength_hours=self.statistics.strength_hours(),

            longest_run_km=self.statistics.longest_run_km(),

            training_sessions_per_week=self.statistics.training_days_per_week(),
           
            max_hr=187,

            threshold_hr=None,

            threshold_pace=None,

            easy_pace=None,
        )

    def _average_weekly_distance(self):

        training_days = self.statistics.training_days_per_week()

        if training_days == 0:
            return 0

        total_distance = self.statistics.total_distance_km()
        total_workouts = self.statistics.total_workouts()

        average_distance_per_workout = (
            total_distance / total_workouts
        )

        return round(
            average_distance_per_workout * training_days,
            1,
        )