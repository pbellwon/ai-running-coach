from __future__ import annotations

import json

from app.ai.openai_client import (
    PaceMindOpenAIClient,
)
from app.services.today_explanation_service import (
    TodayExplanationService,
)


class AITodayExplanationService:
    """
    Turns deterministic PaceMind explainability data
    into a concise natural-language coaching explanation.

    The LLM does not make the training decision.
    It only explains the already-computed PaceMind state.
    """

    INSTRUCTIONS = """
You are PaceMind's explanation layer.

Your job is to explain the training recommendation or
completed-session status using only the structured context
provided by PaceMind.

Rules:
- Do not invent facts.
- Do not change the training decision.
- Do not prescribe a different workout unless the structured
  PaceMind recommendation already contains that change.
- Prefer concrete evidence over generic coaching language.
- Mention uncertainty when it is present.
- Keep the explanation concise.
- Write in Polish.
""".strip()

    def __init__(
        self,
        explanation_service=None,
        llm_client=None,
    ):
        self.explanation_service = (
            explanation_service
            if explanation_service is not None
            else TodayExplanationService()
        )

        self.llm_client = (
            llm_client
            if llm_client is not None
            else PaceMindOpenAIClient()
        )

    def build(
        self,
        target_date: str,
    ) -> str:
        explanation = (
            self.explanation_service
            .build(
                target_date=target_date
            )
        )

        payload = {
            "target_date": (
                explanation.target_date
            ),
            "status": explanation.status,
            "decision": (
                explanation.decision
            ),
            "recommendation_type": (
                explanation
                .recommendation_type
            ),
            "confidence": (
                explanation.confidence
            ),
            "key_reasons": (
                explanation.key_reasons
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

        return self.llm_client.generate(
            instructions=self.INSTRUCTIONS,
            input_text=json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        )