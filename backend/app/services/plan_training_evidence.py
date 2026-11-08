"""Recorded work intervals are distinct from total session time or a planned title."""
import math
from app.analysis.executed_workout_structure_analyzer import ExecutedWorkoutStructureAnalyzer
from app.services.composite_session_builder import CompositeSessionBuilder


class PlanTrainingEvidence:
    def __init__(self, factory):
        self.analyzer = ExecutedWorkoutStructureAnalyzer(factory)

    def build(self, workouts, feedback):
        feedback = {f.session_id:f for f in feedback}
        threshold, strength = [], []
        valid=[w for w in workouts if all(v is None or (math.isfinite(v) and v>=0) for v in (w.distance_km,w.duration_sec))]
        for session in CompositeSessionBuilder().build(valid):
            if session.workout_type == 'strength' and session.total_duration_min and session.total_duration_min > 0:
                strength.append({'date':session.start_time.date().isoformat(), 'minutes':session.total_duration_min})
            if session.workout_type not in ('threshold','threshold+vo2max'):
                continue
            segments=[]
            for component in session.components:
                if component.workout.race:
                    continue
                structure=self.analyzer.analyze(component.workout_file)
                if structure['summary'].get('confidence',0) >= .6:
                    segments.extend(s for s in structure['segments'] if s.get('intensity')=='threshold' or (s.get('intensity')=='tempo' and component.workout.declared_workout_type=='threshold'))
            durations=[]
            for segment in segments:
                if segment.get('duration_sec'):
                    durations.append(segment['duration_sec']/60)
                elif segment.get('avg_duration_sec') and segment.get('repetitions'):
                    durations.extend([segment['avg_duration_sec']/60]*segment['repetitions'])
                elif segment.get('duration_min'):
                    durations.append(segment['duration_min'])
            if not durations:
                continue
            feeling=feedback.get(session.session_id)
            concern=bool((feeling and ((feeling.perceived_effort or 0)>=9 or feeling.execution_feeling in ('too_hard','harder_than_expected')))
                or any((c.workout.rpe or 0)>=9 for c in session.components))
            threshold.append({'date':session.start_time.date().isoformat(), 'session_id':session.session_id,
                'work_min':round(sum(durations),1), 'blocks_min':[round(v,1) for v in durations],
                'feedback_concern':concern})
        reference=max((s['work_min'] for s in threshold if not s['feedback_concern']),default=0)
        return {'threshold_sessions':threshold, 'reference_threshold_work_min':reference,
            'max_observed_threshold_work_min':max((s['work_min'] for s in threshold),default=0),
            'strength_sessions':strength,
            'limitations':['Minuty progu pochodzą z rozpoznanych odcinków wykonania, bez rozgrzewki i schłodzenia.',
                'Zarejestrowana dawka nie potwierdza dzisiejszej tolerancji ani gotowości do zwiększenia obciążenia.',
                'Brak rozpoznanej struktury odcinków nie oznacza, że nie wykonywano treningów progowych.']}
