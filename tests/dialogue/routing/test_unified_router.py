"""Unified router unit tests。"""
from __future__ import annotations

import pytest

from src.dialogue.routing.context_signals import (
    extract_context_features,
    is_ambiguous_short_follow_up,
    is_explicit_new_meta_topic,
)
from src.dialogue.routing.follow_up_llm import resolve_follow_up_route


def test_ambiguous_short_follow_up_detection():
    assert is_ambiguous_short_follow_up("詳しく教えて")
    assert not is_ambiguous_short_follow_up("ロキソニンって眠い？")


def test_explicit_new_meta_topic_from_changelog_context():
    assert is_explicit_new_meta_topic("あなたについて詳しく", prior_intent="doc_changelog")
    assert is_explicit_new_meta_topic("AWSとGCPの違いは？", prior_intent="doc_changelog")
    assert not is_explicit_new_meta_topic("もっと詳しく", prior_intent="doc_changelog")


def test_follow_up_rule_continues_changelog_for_ambiguous():
    session = {
        "messages": [
            {"type": "bot", "concierge_intent": "doc_changelog"},
        ]
    }
    features = extract_context_features("詳しく教えて", session, "sid")
    assert features.is_ambiguous_short_follow_up
    decision = resolve_follow_up_route("詳しく教えて", features)
    assert decision is not None
    assert decision.sub_route == "doc_changelog"
