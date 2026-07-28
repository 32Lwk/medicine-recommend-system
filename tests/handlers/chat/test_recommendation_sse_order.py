"""SSE emit 順序（cards → personalized_advice → reco_detail）のテスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.parametrize("is_line", [False, True])
def test_emit_cards_before_personalized_advice(is_line, monkeypatch):
    """Web / LINE ともに推奨直後に personalized_advice を生成する。"""
    call_order: list[str] = []
    sid = "line:U1" if is_line else "web:s1"
    line_session = is_line

    def _emit_cards(*_a, **_k):
        call_order.append("emit_cards")

    def _personalized(*_a, **_k):
        call_order.append("personalized_advice")
        return "advice text"

    def _mark_step(name):
        call_order.append(name)

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
            side_effect=_mark_step,
        ),
    ):
        recommended = [{"product_name": "A", "name": "A"}]
        if recommended and sid:
            _emit_cards(recommended, session_id=sid)
        if recommended:
            _personalized({}, recommended, [], MagicMock(), user_text="x", session_id=sid)
            _mark_step("personalized_advice")

    assert call_order == ["emit_cards", "personalized_advice", "personalized_advice"]


def test_sage_web_skips_progressive_reco_sse():
    """Sage Web は diagnosis 一括返却のため cards/reco_detail SSE を省略。"""
    from src.services.recommendation_client_payload import should_skip_reco_progressive_sse

    session = {"ui_variant": "sage"}
    assert should_skip_reco_progressive_sse(session, "web:s1") is True
    assert should_skip_reco_progressive_sse(session, "line:U1") is True


def test_legacy_web_keeps_progressive_reco_sse_pattern():
    """非 Sage Web は cards → done の段階 SSE パターンを維持。"""
    call_order: list[str] = []

    def _emit_cards(*_a, **_k):
        call_order.append("emit_cards")

    with patch("src.services.sse_emit.emit_cards", side_effect=_emit_cards):
        sid = "web:s1"
        meds = [{"product_name": "薬A"}]
        _emit_cards(meds, session_id=sid)
        call_order.append("done")

    assert call_order == ["emit_cards", "done"]
