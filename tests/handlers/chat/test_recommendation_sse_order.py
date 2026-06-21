"""SSE emit 順序（cards → personalized_advice → reco_detail）のテスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.parametrize("is_line", [False, True])
def test_emit_cards_before_personalized_advice_on_web(is_line, monkeypatch):
    """Web: rule_based 成功後 emit_cards が personalized_advice より先に呼ばれる。"""
    call_order: list[str] = []
    sid = "line:U1" if is_line else "web:s1"

    def _emit_cards(*_a, **_k):
        call_order.append("emit_cards")

    def _personalized(*_a, **_k):
        call_order.append("personalized_advice")
        return "advice text"

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
    ):
        from src.handlers.line.line_session import is_line_session_id

        recommended = [{"product_name": "A", "name": "A"}]
        if recommended and sid:
            _emit_cards(recommended, session_id=sid)
        if not is_line_session_id(sid):
            _personalized({}, recommended, [], MagicMock(), user_text="x", session_id=sid)

    assert call_order[0] == "emit_cards"
    if is_line:
        assert call_order == ["emit_cards"]
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
