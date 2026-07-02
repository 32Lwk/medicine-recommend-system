"""p3-followup-hotfix: concierge-followup-02/03 REVIEW 是正のユニットテスト。

対象:
- followup-03: redirect フォローアップの同文ループ回避（ROUTING_CONCIERGE_FOLLOWUP ON 限定）
- followup-02: architecture フォローアップで技術スタック言及が欠落した場合の補足
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.agents.concierge_agent import (
    _append_tech_stack_reminder,
    _prior_topic_mentions_tech_stack,
    _resolve_redirect_text,
    build_concierge_payload,
)
from src.services.concierge_templates import build_redirect_followup_text, build_redirect_text


def _history_redirect_repeat():
    return [
        {"type": "user", "content": "プリンシプルオブプログラミングとは？"},
        {
            "type": "bot",
            "content": build_redirect_text(),
            "concierge_intent": "redirect",
        },
        {"type": "user", "content": "具体例を教えて"},
    ]


class TestRedirectFollowUpLoopAvoidance:
    def test_flag_off_keeps_static_redirect_text(self, monkeypatch):
        monkeypatch.setenv("ROUTING_CONCIERGE_FOLLOWUP", "false")
        text = _resolve_redirect_text("具体例を教えて", _history_redirect_repeat())
        assert text == build_redirect_text()

    def test_flag_on_first_redirect_stays_static(self, monkeypatch):
        monkeypatch.setenv("ROUTING_CONCIERGE_FOLLOWUP", "true")
        # 直前 bot が redirect ではない（初回）ので固定文のまま
        history = [{"type": "user", "content": "プリンシプルオブプログラミングとは？"}]
        text = _resolve_redirect_text("プリンシプルオブプログラミングとは？", history)
        assert text == build_redirect_text()

    def test_flag_on_repeat_redirect_uses_followup_text_with_topic_keyword(
        self, monkeypatch
    ):
        monkeypatch.setenv("ROUTING_CONCIERGE_FOLLOWUP", "true")
        text = _resolve_redirect_text("具体例を教えて", _history_redirect_repeat())
        assert text != build_redirect_text()
        assert "プログラミング" in text
        assert "rule_based" in text

    def test_build_concierge_payload_redirect_uses_resolver(self, monkeypatch):
        monkeypatch.setenv("ROUTING_CONCIERGE_FOLLOWUP", "true")
        payload = build_concierge_payload(
            "redirect",
            "具体例を教えて",
            MagicMock(),
            history=_history_redirect_repeat(),
        )
        assert "プログラミング" in payload["content"]
        assert payload["concierge_intent"] == "redirect"


class TestTechStackFollowUpKeyword:
    def test_prior_topic_detects_tech_stack_mention(self):
        history = [
            {"type": "user", "content": "技術スタックは？"},
            {"type": "bot", "content": "フロントエンドは...", "concierge_intent": "architecture"},
        ]
        assert _prior_topic_mentions_tech_stack(history, "もっと詳しく") is True

    def test_prior_topic_no_tech_stack_mention(self):
        history = [
            {"type": "user", "content": "インフラ構成を教えて"},
            {"type": "bot", "content": "Cloud Run 等", "concierge_intent": "architecture"},
        ]
        assert _prior_topic_mentions_tech_stack(history, "もっと詳しく") is False

    def test_append_tech_stack_reminder_adds_keyword(self):
        text = _append_tech_stack_reminder("振り分けの仕組みについて説明します。")
        assert "スタック" in text

    def test_append_tech_stack_reminder_handles_empty_text(self):
        text = _append_tech_stack_reminder("")
        assert "スタック" in text
