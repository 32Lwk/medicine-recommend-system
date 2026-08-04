"""medicine_information_qa タイムアウト・比較 fast path のテスト。"""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from src.handlers.chat.medicine_context_handlers import handle_medicine_information_qa
from src.services.medicine_qa_generation import (
    begin_medicine_qa_generation,
    cancel_medicine_qa_generation,
    is_medicine_qa_generation_stale,
)


def test_medicine_qa_generation_cancel_marks_stale():
    session = {}
    gen = begin_medicine_qa_generation(session)
    assert not is_medicine_qa_generation_stale(session, None, gen)
    cancel_medicine_qa_generation(session)
    assert is_medicine_qa_generation_stale(session, None, gen)


@patch("src.services.pipeline_perf.mark_pipeline_step")
@patch("concurrent.futures.ThreadPoolExecutor")
def test_handle_medicine_information_qa_timeout_returns_quickly(
    mock_executor_cls,
    _mock_mark,
):
    """タイムアウト後に executor shutdown(wait=True) で HTTP がブロックされないこと。"""
    from concurrent.futures import TimeoutError as FuturesTimeout

    mock_future = mock_executor_cls.return_value.submit.return_value
    mock_future.result.side_effect = FuturesTimeout()

    session = {}
    start = time.monotonic()
    body, status = handle_medicine_information_qa(
        session,
        client_info=type("C", (), {"client_ip": "127.0.0.1", "user_agent": "test"})(),
        sid="sid-timeout-test",
        user_message="ロキソニンとバファリンとカロナールでおすすめは？",
    )
    elapsed = time.monotonic() - start

    assert status == 504
    assert body.get("error") is True
    assert elapsed < 1.0
    mock_executor_cls.return_value.shutdown.assert_called_once_with(
        wait=False,
        cancel_futures=True,
    )
    assert is_medicine_qa_generation_stale(session, None, 1)


@patch("src.services.pipeline_perf.mark_pipeline_step")
@patch("src.handlers.chat.chat_medicine_qa_html.run_medicine_question_qa")
def test_handle_medicine_information_qa_success(mock_run_qa, _mock_mark):
    mock_run_qa.return_value = (3, {"answer": "ok"})
    session = {}
    body, status = handle_medicine_information_qa(
        session,
        client_info=type("C", (), {"client_ip": "127.0.0.1", "user_agent": "test"})(),
        sid="sid-ok",
        user_message="ロキソニンとバファリンとカロナールでおすすめは？",
    )
    assert status == 200
    assert body["message_count"] == 3


def test_try_fast_comparison_qa_response_builds_sections():
    from src.core.medicine.medicine_response_builder import _try_fast_comparison_qa_response

    medicines = [
        {
            "product_name": "ロキソニンS",
            "ingredients": "ロキソプロフェンナトリウム水和物",
            "efficacy": "頭痛・生理痛",
        },
        {
            "product_name": "バファリンA",
            "ingredients": "アスピリン 合成ヒドロタルサイト",
            "efficacy": "頭痛・生理痛",
        },
        {
            "product_name": "カロナールA",
            "ingredients": "アセトアミノフェン",
            "efficacy": "頭痛・生理痛",
        },
    ]
    result = _try_fast_comparison_qa_response(
        "ロキソニンとバファリンとカロナールでおすすめは？",
        medicines,
        qa_focuses=["comparison"],
    )
    assert result is not None
    assert result.get("answer")
    assert "ui-qa-product-line" in str(result.get("medicine_details") or "")
    assert str(result.get("interactions") or "").strip()
