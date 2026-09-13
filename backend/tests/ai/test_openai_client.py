from app.ai.openai_client import (
    PaceMindOpenAIClient,
)


class FakeResponse:
    def __init__(
        self,
        output_text,
    ):
        self.output_text = output_text


class FakeResponsesAPI:
    def __init__(self):
        self.calls = []

    def create(
        self,
        **kwargs,
    ):
        self.calls.append(
            kwargs
        )

        return FakeResponse(
            "  Training looks good.  "
        )


class FakeOpenAIClient:
    def __init__(self):
        self.responses = (
            FakeResponsesAPI()
        )


def test_generate_uses_responses_api():
    fake_client = (
        FakeOpenAIClient()
    )

    client = PaceMindOpenAIClient(
        client=fake_client,
        model="test-model",
    )

    result = client.generate(
        instructions=(
            "Explain the decision."
        ),
        input_text=(
            '{"decision":"do_as_planned"}'
        ),
    )

    assert (
        result
        == "Training looks good."
    )

    assert (
        len(
            fake_client
            .responses
            .calls
        )
        == 1
    )

    call = (
        fake_client
        .responses
        .calls[0]
    )

    assert (
        call["model"]
        == "test-model"
    )

    assert (
        call["instructions"]
        == "Explain the decision."
    )

    assert (
        call["input"]
        == (
            '{"decision":"do_as_planned"}'
        )
    )


def test_raises_when_response_has_no_text():
    class EmptyResponse:
        output_text = ""

    class EmptyResponsesAPI:
        def create(
            self,
            **kwargs,
        ):
            return EmptyResponse()

    class EmptyClient:
        responses = (
            EmptyResponsesAPI()
        )

    client = PaceMindOpenAIClient(
        client=EmptyClient(),
        model="test-model",
    )

    try:
        client.generate(
            instructions="Test",
            input_text="Test",
        )

    except RuntimeError as exc:
        assert (
            str(exc)
            == (
                "OpenAI response did not "
                "contain output text."
            )
        )

    else:
        raise AssertionError(
            "Expected RuntimeError."
        )