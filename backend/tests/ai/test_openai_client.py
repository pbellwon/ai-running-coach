from app.ai.openai_client import (
    PaceMindOpenAIClient,
    AIResponseError,
)
import pytest
from types import SimpleNamespace
from app.services.personal_plan_coach import Strategy


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


def test_plan_generation_sends_complete_strict_schema_to_responses_api():
    sdk = FakeOpenAIClient()
    client = PaceMindOpenAIClient(client=sdk,model='test-model')
    client.generate('Plan','{}',max_output_tokens=6000,json_schema=Strategy.model_json_schema())
    schema = sdk.responses.calls[0]['text']['format']
    assert schema['type'] == 'json_schema' and schema['strict'] is True
    for definition in [schema['schema'],schema['schema']['$defs']['Session']]:
        assert set(definition['required']) == set(definition['properties'])
        assert definition['additionalProperties'] is False
        assert all('default' not in field for field in definition['properties'].values())


@pytest.mark.parametrize('response,code', [
    (SimpleNamespace(status='incomplete',output_text='{"cycle_days":10}'),'incomplete'),
    (SimpleNamespace(status='completed',output_text='',output=[SimpleNamespace(content=[SimpleNamespace(type='refusal')])]),'refusal'),
])
def test_partial_or_refused_response_is_not_used_as_a_plan(response,code):
    sdk = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs:response))
    with pytest.raises(AIResponseError) as error:
        PaceMindOpenAIClient(client=sdk).generate('Plan','{}')
    assert error.value.category == code


def test_actual_openai_sdk_serializes_schema_and_extracts_completed_response_without_network():
    import json
    import httpx2
    from openai import OpenAI
    calls=[]
    def handler(request):
        calls.append(json.loads(request.content))
        return httpx2.Response(200,json={'id':'resp_test','created_at':0,'model':'test-model',
            'object':'response','status':'completed','error':None,'incomplete_details':None,
            'parallel_tool_calls':True,'tools':[],'tool_choice':'auto','output':[
                {'id':'msg_test','type':'message','role':'assistant','status':'completed','content':[
                    {'type':'output_text','text':'{"accepted":true}','annotations':[]}]}]})
    with httpx2.Client(transport=httpx2.MockTransport(handler)) as transport:
        with OpenAI(api_key='local-test-key',base_url='https://openai.invalid/v1',http_client=transport) as sdk:
            value=PaceMindOpenAIClient(client=sdk,model='test-model').generate('Plan','{}',json_schema=Strategy.model_json_schema())
    assert value=='{"accepted":true}'
    assert len(calls)==1 and calls[0]['text']['format']['strict'] is True
