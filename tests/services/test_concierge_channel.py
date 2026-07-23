"""Concierge チャネル別 UX。"""
from __future__ import annotations

from src.services.concierge_channel import (
    is_concierge_line_channel,
    line_architecture_follow_up_hint,
    resolve_concierge_channel,
)
from src.services.concierge_templates import (
    _apply_line_channel_body_limits,
    build_dynamic_concierge_line_flex,
)


def test_line_session_detection():
    assert is_concierge_line_channel("line:Uabc123")
    assert not is_concierge_line_channel("web-session-1")
    assert resolve_concierge_channel("line:U1") == "line"
    assert resolve_concierge_channel(None) == "web"


def test_line_shallow_hint_only_when_not_deep():
    assert line_architecture_follow_up_hint(deep=False)
    assert line_architecture_follow_up_hint(deep=True) is None


def test_line_shallow_body_limits():
    long_body = ["段落" + str(i) + "。" * 40 for i in range(8)]
    out = _apply_line_channel_body_limits(long_body, channel="line", deep=False)
    assert len(out) <= 5
    assert any("詳しく" in p or "Web" in p for p in out)


def test_line_deep_uses_standard_truncation():
    flex = build_dynamic_concierge_line_flex(
        title="構成",
        body_text="AWS ステージングの説明。" * 200,
        intent="architecture",
        deep=True,
        channel="line",
    )
    assert flex["body_paragraphs"]
