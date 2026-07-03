"""doc_changelog 意図判定（LLM のみ。キーワードプローブ・除外 regex は使わない）。"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from src.content.changelog_digest import format_changelog_llm_reference, load_changelog_digest
from src.services.concierge_intent import probe_meta_concierge_intent
from src.services.meta_triage import classify_meta_concierge_intent


def _mock_response(intent: str):
    body = json.dumps({"intent": intent, "confidence": 0.95})
    msg = MagicMock()
    msg.content = body
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def test_probe_does_not_route_doc_changelog_by_keywords():
    """更新系フレーズはキーワードプローブせず LLM へ。"""
    for text in (
        "アプリの更新内容を教えてください",
        "更新教えて",
        "最近のあなたの更新内容を教えて",
        "CHANGELOGを見せて",
    ):
        assert probe_meta_concierge_intent(text) is None, text


@patch("src.core.llm_client.chat_completion_create")
def test_meta_triage_doc_changelog_including_short_phrase(mock_chat):
    phrases = [
        "アプリの更新内容を教えてください",
        "更新教えて",
        "このチャット最近どう変わった？",
        "リリースで入ったことは？",
    ]
    for phrase in phrases:
        mock_chat.return_value = _mock_response("doc_changelog")
        intent = classify_meta_concierge_intent(phrase, MagicMock())
        assert intent == "doc_changelog", phrase


@patch("src.core.llm_client.chat_completion_create")
def test_meta_triage_llm_decides_not_doc_changelog_for_other_topics(mock_chat):
    """誤爆防止は LLM 分類に委ねる（モックで none / chitchat を返す想定）。"""
    cases = [
        ("ポケモンの更新があったんだってどん内容かな", "chitchat"),
        ("最近の私は人間として更新しているんだ", "chitchat"),
        ("頭痛がします", "none"),
    ]
    for phrase, llm_intent in cases:
        mock_chat.return_value = _mock_response(llm_intent)
        intent = classify_meta_concierge_intent(phrase, MagicMock())
        expected = None if llm_intent == "none" else llm_intent
        assert intent == expected, phrase


def test_changelog_llm_reference_is_compact_not_full_file():
    header, releases = load_changelog_digest(max_releases=4)
    ref = format_changelog_llm_reference(releases, header_date=header)
    assert len(ref) < 12_000
    assert len(releases) > 0
