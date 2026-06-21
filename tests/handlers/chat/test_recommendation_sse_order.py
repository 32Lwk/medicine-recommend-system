"""SSE emit 順序（cards → personalized_advice → reco_detail）のテスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.parametrize("is_line", [False, True])
def test_emit_cards_before_personalized_advice(is_line, monkeypatch):
    """Web は推奨直後に personalized_advice。LINE はスキップ（引き継ぎ時のみ生成）。"""
    call_order: list[str] = []
    sid = "line:U1" if is_line else "web:s1"
    line_session = is_line

    def _emit_cards(*_a, **_k):
        call_order.append("emit_cards")

    def _personalized(*_a, **_k):
        call_order.append("personalized_advice")
        return "advice text"

    def _skipped_line(*_a, **_k):
        call_order.append("personalized_advice_skipped_line")

    monkeypatch.setattr(
        "src.handlers.line.line_session.is_line_session_id",
        lambda s: str(s).startswith("line:"),
    )

    with (
        patch("src.services.sse_emit.emit_cards", side_effect=_emit_cards),
        patch(
            "src.services.chat_response_service.generate_personalized_advice",
            side_effect=_personalized,
        ),
        patch(
            "src.services.pipeline_perf.mark_pipeline_step",
            side_effect=_skipped_line,
        ),
    ):
        recommended = [{"product_name": "A", "name": "A"}]
        if recommended and sid:
            _emit_cards(recommended, session_id=sid)
        if not line_session:
            _personalized({}, recommended, [], MagicMock(), user_text="x", session_id=sid)
        else:
            _skipped_line("personalized_advice_skipped_line")

    if is_line:
        assert call_order == ["emit_cards", "personalized_advice_skipped_line"]
    else:
        assert call_order == ["emit_cards", "personalized_advice"]


def test_emit_reco_detail_after_done_pattern():
    """Sage Web: reco_detail は cards/advice 処理後に emit される想定。"""
    call_order: list[str] = []

    def _emit_cards(*_a, **_k):
        call_order.append("emit_cards")

    def _emit_reco_detail(*_a, **_k):
        call_order.append("emit_reco_detail")

    with (
        patch("src.services.sse_emit.emit_cards", side_effect=_emit_cards),
        patch("src.services.sse_emit.emit_reco_detail", side_effect=_emit_reco_detail),
    ):
        sid = "web:s1"
        meds = [{"product_name": "薬A"}]
        _emit_cards(meds, session_id=sid)
        call_order.append("done")
        _emit_reco_detail({"usage_sections": [], "recommended_medicines": meds}, session_id=sid)

    assert call_order == ["emit_cards", "done", "emit_reco_detail"]
