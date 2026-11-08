from __future__ import annotations

import os
from copy import deepcopy

from openai import OpenAI


class AIResponseError(RuntimeError):
    def __init__(self, category, message, request_id=None):
        self.category, self.request_id = category, request_id
        super().__init__(message)


def strict_json_schema(schema):
    result = deepcopy(schema)
    def visit(node):
        if isinstance(node, dict):
            node.pop('default', None)
            if node.get('type') == 'object':
                node['required'] = list(node.get('properties', {}))
                node['additionalProperties'] = False
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)
    visit(result)
    return result


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
        max_output_tokens: int | None = None,
        json_schema: dict | None = None,
    ) -> str:
        options = {} if max_output_tokens is None else {"max_output_tokens": max_output_tokens}
        if json_schema is not None:
            options['text'] = {'format': {'type':'json_schema', 'name':'pacemind_plan',
                'strict':True, 'schema':strict_json_schema(json_schema)}}
        response = (
            self.client.responses.create(
                model=self.model,
                instructions=instructions,
                input=input_text,
                **options,
            )
        )

        if getattr(response, 'status', None) in ('incomplete', 'failed', 'cancelled'):
            raise AIResponseError('incomplete', 'OpenAI response was not completed.', getattr(response, '_request_id', None))
        for item in getattr(response, 'output', None) or []:
            for content in getattr(item, 'content', None) or []:
                if getattr(content, 'type', None) == 'refusal':
                    raise AIResponseError('refusal', 'OpenAI declined the generation.', getattr(response, '_request_id', None))
        output_text = getattr(
            response,
            "output_text",
            None,
        )

        if not output_text or not output_text.strip():
            raise AIResponseError('empty', 'OpenAI response did not contain output text.', getattr(response, '_request_id', None))

        return output_text.strip()
