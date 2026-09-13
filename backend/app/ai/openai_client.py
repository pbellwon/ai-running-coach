from __future__ import annotations

import os

from openai import OpenAI


class PaceMindOpenAIClient:
    """
    Thin wrapper around the OpenAI Responses API.

    Responsibilities:
    - configure the OpenAI client;
    - send text instructions and input;
    - return plain output text.

    This class does not contain coaching logic.
    """

    DEFAULT_MODEL = "gpt-5.6-luna"

    def __init__(
        self,
        client=None,
        model: str | None = None,
    ):
        self.client = (
            client
            if client is not None
            else OpenAI(
                api_key=os.getenv(
                    "OPENAI_API_KEY"
                )
            )
        )

        self.model = (
            model
            or os.getenv(
                "OPENAI_MODEL"
            )
            or self.DEFAULT_MODEL
        )

    def generate(
        self,
        instructions: str,
        input_text: str,
    ) -> str:
        response = (
            self.client.responses.create(
                model=self.model,
                instructions=instructions,
                input=input_text,
            )
        )

        output_text = getattr(
            response,
            "output_text",
            None,
        )

        if not output_text:
            raise RuntimeError(
                "OpenAI response did not "
                "contain output text."
            )

        return output_text.strip()