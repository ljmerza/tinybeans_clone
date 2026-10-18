"""The provider client: request shape, fixed error codes, and strict parsing of the model's answer."""

import traceback

import pytest
import requests

from mysite.ai import client, prompts
from mysite.ai.providers import ProviderConfig

from .helpers import BASE_URL, MODEL, chat_response, status_response

CONFIG = ProviderConfig(base_url=BASE_URL, model=MODEL, timeout_seconds=90)
SECRET_BODY = "PROVIDER-BODY Grandma's secret caption about Sophia"


def classify(**config):
    return client.classify_post(ProviderConfig(**{**CONFIG.__dict__, **config}), "Big day", "She walked!")


class TestRequest:
    def test_request_shape(self, provider):
        provider.return_value = chat_response({"is_milestone": True, "label": "First steps", "reason": "Walked."})

        classify()

        provider.assert_called_once()
        args, kwargs = provider.call_args
        assert args == (f"{BASE_URL}/chat/completions",)
        assert kwargs["allow_redirects"] is False
        assert kwargs["timeout"] == (client.CONNECT_TIMEOUT_SECONDS, 90)
        assert "Authorization" not in kwargs["headers"]
        payload = kwargs["json"]
        assert payload["model"] == MODEL
        assert payload["temperature"] == 0
        assert payload["max_tokens"] == 1024
        assert payload["stream"] is False
        assert "tools" not in payload
        assert payload["response_format"] == {
            "type": "json_schema",
            "json_schema": {"name": "milestone_verdict", "schema": prompts.VERDICT_SCHEMA},
        }

    def test_key_is_sent_as_bearer(self, provider):
        provider.return_value = chat_response({"is_milestone": False, "label": "", "reason": "No."})

        classify(base_url="https://api.example.com/v1", api_key="sk-secret-value")

        assert provider.call_args.kwargs["headers"]["Authorization"] == "Bearer sk-secret-value"


class TestErrors:
    @pytest.mark.parametrize(
        ("status_code", "code"),
        [
            (301, client.HTTP_ERROR),
            (302, client.HTTP_ERROR),
            (400, client.HTTP_ERROR),
            (401, client.AUTH_FAILED),
            (403, client.AUTH_FAILED),
            (404, client.MODEL_MISSING),
            (429, client.PROVIDER_UNAVAILABLE),
            (500, client.HTTP_ERROR),
            (503, client.PROVIDER_UNAVAILABLE),
        ],
    )
    def test_status_codes(self, provider, status_code, code):
        provider.return_value = status_response(status_code, {"error": SECRET_BODY})

        with pytest.raises(client.AiError) as excinfo:
            classify()

        assert excinfo.value.code == code
        assert str(excinfo.value) == code

    @pytest.mark.parametrize(
        ("exception", "code"),
        [
            (requests.ConnectTimeout(SECRET_BODY), client.TIMEOUT),
            (requests.ReadTimeout(SECRET_BODY), client.TIMEOUT),
            (requests.ConnectionError(SECRET_BODY), client.UNREACHABLE),
            (requests.TooManyRedirects(SECRET_BODY), client.UNREACHABLE),
        ],
    )
    def test_transport_errors(self, provider, exception, code):
        provider.side_effect = exception

        with pytest.raises(client.AiError) as excinfo:
            classify()

        assert excinfo.value.code == code
        assert excinfo.value.__cause__ is None
        assert excinfo.value.__suppress_context__ is True

    @pytest.mark.parametrize(
        "body",
        [{}, {"choices": []}, {"choices": [{"message": {}}]}, {"choices": [{"message": {"content": 5}}]}, ["x"]],
    )
    def test_not_a_chat_completion(self, provider, body):
        provider.return_value = status_response(200, body)

        with pytest.raises(client.AiError) as excinfo:
            classify()

        assert excinfo.value.code == client.BAD_RESPONSE

    def test_cut_off_at_max_tokens_is_a_bad_response(self, provider):
        # A reasoning model that thinks past max_tokens: a failed call (no row), not an invalid answer.
        provider.return_value = chat_response(
            '{"is_milestone": true, "label": "First steps", "reason": "Walked."}', finish_reason="length"
        )

        with pytest.raises(client.AiError) as excinfo:
            classify()

        assert excinfo.value.code == client.BAD_RESPONSE

    def test_non_json_body(self, provider):
        response = status_response(200)
        response.json.side_effect = ValueError(SECRET_BODY)
        provider.return_value = response

        with pytest.raises(client.AiError) as excinfo:
            classify()

        assert excinfo.value.code == client.BAD_RESPONSE
        assert SECRET_BODY not in str(excinfo.value)

    @pytest.mark.parametrize(
        "answer",
        [
            status_response(500, {"error": SECRET_BODY}),
            chat_response(SECRET_BODY),
            requests.ConnectionError(SECRET_BODY),
        ],
    )
    def test_provider_body_never_reaches_the_exception(self, provider, answer):
        # Log output is checked end to end in test_scan (the scan is what logs).
        if isinstance(answer, Exception):
            provider.side_effect = answer
        else:
            provider.return_value = answer

        with pytest.raises((client.AiError, client.InvalidOutput)) as excinfo:
            classify()

        shown = "".join(traceback.format_exception(excinfo.value))
        assert SECRET_BODY not in shown


class TestParsing:
    @pytest.mark.parametrize(
        "content",
        [
            '{"is_milestone": true, "label": "First steps", "reason": "Walked."}',
            '<think>\nThe caption says she walked. That is a first.\n</think>\n{"is_milestone": true, '
            '"label": "First steps", "reason": "Walked."}',
            '```json\n{"is_milestone": true, "label": "First steps", "reason": "Walked."}\n```',
            '<think>hmm</think>\n```\n{"is_milestone": true, "label": "First steps", "reason": "Walked."}\n```',
        ],
    )
    def test_think_blocks_and_fences_are_stripped(self, provider, content):
        provider.return_value = chat_response(content)

        assert classify() == client.Verdict(True, "First steps", "Walked.")

    @pytest.mark.parametrize(
        "content",
        [
            '{"is_milestone": "true", "label": "First steps", "reason": "Walked."}',
            '{"is_milestone": 1, "label": "First steps", "reason": "Walked."}',
            '{"label": "First steps", "reason": "Walked."}',
            '{"is_milestone": true, "label": 5, "reason": "Walked."}',
            '{"is_milestone": true, "label": "x", "reason": ["Walked."]}',
            "[true]",
            "yes, it is a milestone",
            "",
            "<think>never closed",
        ],
    )
    def test_invalid_answers(self, provider, content):
        provider.return_value = chat_response(content)

        with pytest.raises(client.InvalidOutput):
            classify()

    def test_text_is_cleaned_and_truncated(self, provider):
        provider.return_value = chat_response(
            {
                "is_milestone": True,
                "label": "First​ steps\x00" + "!" * 200,
                "reason": "Line one.\nLine\ttwo ‮" + "x" * 500,
            }
        )

        result = classify()

        assert result.label.startswith("First steps!")
        assert len(result.label) == client.LABEL_MAX
        assert result.reason.startswith("Line one. Line two x")
        assert len(result.reason) == client.REASON_MAX
        assert "‮" not in result.reason

    def test_missing_label_and_reason_default_to_empty(self, provider):
        provider.return_value = chat_response('{"is_milestone": false}')

        assert classify() == client.Verdict(False, "", "")
