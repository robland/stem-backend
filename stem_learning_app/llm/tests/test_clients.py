from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import openai
import pytest
from django.core.exceptions import ImproperlyConfigured
from pydantic import BaseModel

from llm.clients import ImageInput, get_client
from llm.clients.fake import FakeLLMClient
from llm.clients.openai import OpenAIClient
from llm.exceptions import LLMError, LLMOutputInvalid, LLMRefusal
from llm.prompts import RenderedPrompt

PROMPT = RenderedPrompt(id="demo.v1", system="Système", user="Utilisateur")
IMAGE = ImageInput(data=b"\x89PNG", mime_type="image/png")


class Answer(BaseModel):
    value: int


def completion(parsed=None, refusal=None):
    message = SimpleNamespace(parsed=parsed, refusal=refusal)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message)],
        model="gpt-test",
        usage=SimpleNamespace(prompt_tokens=120, completion_tokens=30),
    )


@pytest.fixture
def sdk():
    return MagicMock()


@pytest.fixture
def client(sdk):
    return OpenAIClient(sdk_client=sdk)


class TestImageInput:
    def test_data_url(self):
        assert IMAGE.data_url() == "data:image/png;base64,iVBORw=="

    def test_rejects_unsupported_type(self):
        with pytest.raises(ValueError):
            ImageInput(data=b"%PDF", mime_type="application/pdf")


class TestOpenAIClient:
    def test_sends_structured_request(self, client, sdk, settings):
        settings.LLM_MODELS = {"extraction": "gpt-extraction"}
        sdk.chat.completions.parse.return_value = completion(parsed=Answer(value=42))

        result = client.generate(task="extraction", prompt=PROMPT, output_schema=Answer, images=[IMAGE])

        kwargs = sdk.chat.completions.parse.call_args.kwargs
        assert kwargs["model"] == "gpt-extraction"
        assert kwargs["response_format"] is Answer
        assert kwargs["messages"][0] == {"role": "system", "content": "Système"}
        assert kwargs["messages"][1]["content"] == [
            {"type": "text", "text": "Utilisateur"},
            {"type": "image_url", "image_url": {"url": IMAGE.data_url(), "detail": "high"}},
        ]
        assert result.output == Answer(value=42)
        assert (result.model, result.prompt_id) == ("gpt-test", "demo.v1")
        assert (result.input_tokens, result.output_tokens) == (120, 30)

    def test_unknown_task_is_a_configuration_error(self, client):
        with pytest.raises(ImproperlyConfigured):
            client.generate(task="inconnue", prompt=PROMPT, output_schema=Answer)

    def test_refusal(self, client, sdk):
        sdk.chat.completions.parse.return_value = completion(refusal="Je ne peux pas.")

        with pytest.raises(LLMRefusal):
            client.generate(task="extraction", prompt=PROMPT, output_schema=Answer)

    def test_empty_response(self, client, sdk):
        sdk.chat.completions.parse.return_value = completion()

        with pytest.raises(LLMOutputInvalid):
            client.generate(task="extraction", prompt=PROMPT, output_schema=Answer)

    def test_truncated_response(self, client, sdk):
        sdk.chat.completions.parse.side_effect = openai.LengthFinishReasonError(completion=completion())

        with pytest.raises(LLMOutputInvalid):
            client.generate(task="extraction", prompt=PROMPT, output_schema=Answer)

    def test_invalid_json(self, client, sdk):
        sdk.chat.completions.parse.side_effect = lambda **kw: Answer.model_validate_json('{"value": "x"}')

        with pytest.raises(LLMOutputInvalid):
            client.generate(task="extraction", prompt=PROMPT, output_schema=Answer)

    def test_network_error(self, client, sdk):
        request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        sdk.chat.completions.parse.side_effect = openai.APITimeoutError(request=request)

        with pytest.raises(LLMError, match="APITimeoutError"):
            client.generate(task="extraction", prompt=PROMPT, output_schema=Answer)

    def test_logs_metrics_without_content(self, client, sdk, caplog):
        sdk.chat.completions.parse.return_value = completion(parsed=Answer(value=42))

        with caplog.at_level("INFO", logger="llm.clients.openai"):
            client.generate(task="extraction", prompt=PROMPT, output_schema=Answer, images=[IMAGE])

        assert "prompt=demo.v1" in caplog.text
        assert "Utilisateur" not in caplog.text and "Système" not in caplog.text


class TestFakeLLMClient:
    def test_settings_select_fake_client(self):
        assert isinstance(get_client(), FakeLLMClient)

    def test_returns_validated_responses_in_order(self, fake_llm):
        fake_llm.queue({"value": 1}, Answer(value=2))

        first = fake_llm.generate(task="extraction", prompt=PROMPT, output_schema=Answer)
        second = fake_llm.generate(task="extraction", prompt=PROMPT, output_schema=Answer, images=[IMAGE])

        assert (first.output.value, second.output.value) == (1, 2)
        assert fake_llm.calls[1]["images"] == [IMAGE]

    def test_invalid_dict_raises_like_the_real_client(self, fake_llm):
        fake_llm.queue({"value": "x"})

        with pytest.raises(LLMOutputInvalid):
            fake_llm.generate(task="extraction", prompt=PROMPT, output_schema=Answer)

    def test_queued_exception_is_raised(self, fake_llm):
        fake_llm.queue(LLMRefusal("refus"))

        with pytest.raises(LLMRefusal):
            fake_llm.generate(task="extraction", prompt=PROMPT, output_schema=Answer)

    def test_empty_queue_fails_loudly(self, fake_llm):
        with pytest.raises(AssertionError):
            fake_llm.generate(task="extraction", prompt=PROMPT, output_schema=Answer)
