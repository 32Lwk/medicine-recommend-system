"""LLM ストリーミング"""
from unittest.mock import MagicMock, patch

from src.core.llm_client import chat_completion_stream, text_completion_adapter


def _chunk(text: str):
    c = MagicMock()
    c.choices = [MagicMock(delta=MagicMock(content=text))]
    return c


def test_chat_completion_stream_collects_deltas():
    client = MagicMock()
    client.chat.completions.create.return_value = iter([_chunk("こ"), _chunk("んにちは")])

    deltas = []
    with patch("src.core.llm_client.check_llm_allowed", return_value=(True, None)):
        with patch("src.core.llm_client.use_responses_api_for_role", return_value=False):
            with patch("src.core.llm_client.get_model", return_value="gpt-4o-mini"):
                with patch("src.services.llm_metrics.record_llm_call"):
                    with patch("src.services.budget_guard.add_monthly_cost"):
                        text = chat_completion_stream(
                            client,
                            model_role="counsel",
                            path="test",
                            messages=[{"role": "user", "content": "hi"}],
                            on_delta=deltas.append,
                        )
    assert text == "こんにちは"
    assert deltas == ["こ", "んにちは"]


def test_text_completion_adapter():
    resp = text_completion_adapter("ok")
    assert resp.choices[0].message.content == "ok"
