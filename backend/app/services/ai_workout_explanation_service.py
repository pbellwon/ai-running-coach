from __future__ import annotations

import json

from app.ai.openai_client import (
    PaceMindOpenAIClient,
)
from app.services.ai_explanation_cache_service import (
    AIExplanationCacheService,
)
from app.services.workout_explanation_service import (
    WorkoutExplanationService,
)


class AIWorkoutExplanationService:
    EXPLANATION_TYPE = "workout"
    PROMPT_VERSION = "1.3"

    INSTRUCTIONS = """
You are PaceMind, an evidence-based endurance running coach.

Your task is not to merely summarize the workout.
Your primary task is to interpret how the athlete executed the
session and provide useful coaching feedback.

Use only the structured PaceMind context provided to you.

Coaching priorities:
1. Identify the intended purpose of the workout.
2. Judge how well the athlete executed that purpose.
3. Identify the most important execution strength or problem.
4. Explain why it matters from a training perspective.
5. Give one concrete coaching cue for the next similar session,
   when the available data supports it.

Write like a coach speaking directly to the athlete after training,
not like a database report.

Prefer interpretation over repetition of raw facts.

For example, instead of only saying that three threshold repetitions
were completed, assess whether they were controlled, consistent,
progressive, too aggressive, or otherwise notable when the available
data supports that conclusion.

If pacing data is available, look for meaningful patterns such as:
- starting too fast,
- slowing substantially across repetitions,
- progressive acceleration,
- inconsistent repetitions,
- controlled and repeatable pacing.

Do not call a repetition too fast or too slow unless the planned
target, workout intent, or other structured context supports that
judgement.

For interval or threshold sessions, compare repetitions with each
other when possible. Small differences should not be exaggerated.

For easy and recovery sessions, focus on whether the execution
remained appropriately controlled rather than rewarding faster pace.

For long runs, evaluate pacing, progression and relevant late-run
changes when supported by the data.

Athlete feedback is important. If subjective feedback conflicts with
apparently good objective execution, mention that discrepancy rather
than ignoring it.

Rules:
- Do not invent facts.
- Do not change the deterministic review status.
- Treat the planned workout type as the primary session intent.
- Treat the executed workout type as the execution profile,
  not necessarily as the name of the session.
- If the plan says long_run and execution says easy_run,
  describe it as a long run performed mostly at easy intensity.
- Use execution structure to support coaching conclusions,
  not merely to list workout segments.
- Mention raw distance, duration and segment counts only when they
  help explain a coaching conclusion.
- In execution_structure segments, duration_sec and duration_min
  represent elapsed time and may include stopped-clock periods.
- moving_time_sec and moving_duration_min represent moving time.
  Use moving time when describing running duration or pace.
- avg_pace_sec_per_km is calculated from moving time when
  complete moving-time data is available.
- If moving_time_sec or avg_pace_sec_per_km is null, do not infer
  moving time or running pace from elapsed duration.
- For recoveries between repetitions, count only segments named
  recovery. Do not count transition as another recovery.
- Distinguish warmup from cooldown.
- Use athlete feedback when available.
- Mention relevant uncertainty when it materially affects the
  coaching conclusion.
- You may give execution advice for the next similar workout,
  such as pacing or effort-control cues.
- Do not modify the athlete's training schedule, prescribe a new
  workout, or change future training load unless the structured
  context explicitly contains such a recommendation.
- Focus on the one or two most useful coaching observations.
- Avoid generic encouragement and filler.
- Be concise but conversational.
- Address the athlete directly.
- If the athlete's first name is present in the supplied context,
  you may use it naturally. Never invent a name.
- Answer in Polish.
- Return plain text only.
- Do not use Markdown formatting.
""".strip()

    def __init__(
        self,
        explanation_service=None,
        llm_client=None,
        cache_service=None,
    ):
        self.explanation_service = (
            explanation_service
            if explanation_service is not None
            else WorkoutExplanationService()
        )

        self.llm_client = (
            llm_client
            if llm_client is not None
            else PaceMindOpenAIClient()
        )

        self.cache_service = (
            cache_service
            if cache_service is not None
            else AIExplanationCacheService()
        )

    def build(
        self,
        session_id: str,
        target_date=None,
    ) -> str:
        explanation = (
            self.explanation_service.build(
                session_id=session_id,
                target_date=target_date,
            )
        )

        payload = {
            "prompt_version": (
                self.PROMPT_VERSION
            ),
            "session_id": (
                explanation.session_id
            ),
            "target_date": (
                explanation.target_date
            ),
            "status": (
                explanation.status
            ),
            "confidence": (
                explanation.confidence
            ),
            "planned_workout": (
                explanation.planned_workout
            ),
            "executed_workout": (
                explanation.executed_workout
            ),
            "execution_structure": (
                explanation.execution_structure
            ),
            "athlete_feedback": (
                explanation.athlete_feedback
            ),
            "key_evidence": (
                explanation.key_evidence
            ),
            "warnings": (
                explanation.warnings
            ),
            "uncertainties": (
                explanation.uncertainties
            ),
            "context": (
                explanation.context
            ),
        }

        context_hash = (
            self.cache_service
            .build_context_hash(
                payload
            )
        )

        cached = (
            self.cache_service.get(
                context_hash
            )
        )

        if cached is not None:
            return (
                cached.explanation_text
            )

        input_text = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
        )

        explanation_text = (
            self.llm_client.generate(
                instructions=(
                    self.INSTRUCTIONS
                ),
                input_text=(
                    input_text
                ),
            )
        )

        self.cache_service.save(
            explanation_type=(
                self.EXPLANATION_TYPE
            ),
            target_date=(
                explanation.target_date
            ),
            context_hash=(
                context_hash
            ),
            model=(
                self.llm_client.model
            ),
            explanation_text=(
                explanation_text
            ),
        )

        return explanation_text