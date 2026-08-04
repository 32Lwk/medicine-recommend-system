"""連絡チャネル（LINE / 運営者）意図分類の拡張テスト。"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from src.agents.concierge_agent import (
    build_concierge_payload,
    generate_doc_operator_intro,
    resolve_concierge_intent,
)
from src.services.contact_channel_intent import (
    classify_contact_channel_llm,
    classify_contact_channel_question,
    contact_channel_to_concierge_intent,
    is_line_account_link_question,
    is_operator_contact_question,
    is_operator_identity_question,
)
from src.services.concierge_intent import probe_meta_concierge_intent

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "concierge_contact_channel.yaml"


def _load_cases():
    data = yaml.safe_load(_FIXTURE.read_text(encoding="utf-8"))
    return data.get("cases") or []


def _load_dialogues():
    data = yaml.safe_load(_FIXTURE.read_text(encoding="utf-8"))
    return data.get("dialogue_scenarios") or []


@pytest.fixture(scope="module")
def contact_cases():
    return _load_cases()


@pytest.fixture(scope="module")
def dialogue_scenarios():
    return _load_dialogues()


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
def test_classify_contact_channel_from_fixture(case):
    history = case.get("history")
    kind = classify_contact_channel_question(case["text"], history=history)
    expected = case.get("expected_kind")
    if expected is None:
        assert kind is None
    else:
        assert kind == expected


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
def test_contact_channel_to_concierge_intent_from_fixture(case):
    history = case.get("history")
    kind = classify_contact_channel_question(case["text"], history=history)
    intent = contact_channel_to_concierge_intent(kind)
    assert intent == case.get("expected_intent")


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
def test_probe_meta_matches_contact_channel(case):
    history = case.get("history")
    expected_intent = case.get("expected_intent")
    if history or expected_intent is None:
        return
    probed = probe_meta_concierge_intent(case["text"])
    if expected_intent in ("capabilities", "doc_operator", "architecture"):
        assert probed == expected_intent


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
def test_resolve_concierge_intent_contact_channel(case):
    history = case.get("history") or []
    expected = case.get("expected_intent")
    if expected is None:
        return
    session = {"concierge_state": {}}
    triage = {"category": "Other", "confidence": 0.9, "concierge_intent": "doc_operator"}
    resolved = resolve_concierge_intent(
        case["text"],
        session,
        triage_result=triage,
        client=MagicMock(),
        conversation_history=history,
    )
    assert resolved == expected


@pytest.mark.parametrize("scenario", _load_dialogues(), ids=lambda s: s["id"])
def test_multi_turn_contact_channel_dialogue(scenario):
    session = {"concierge_state": {}}
    history: list = []
    for turn in scenario["turns"]:
        user = turn["user"]
        expected = turn.get("expect_intent")
        resolved = resolve_concierge_intent(
            user,
            session,
            triage_result={"category": "Other", "confidence": 0.85},
            client=MagicMock(),
            conversation_history=history,
        )
        if expected is None:
            assert resolved != "capabilities" or not is_line_account_link_question(
                user, history=history
            )
        else:
            assert resolved == expected
        history.append({"type": "user", "content": user})
        if resolved == "capabilities":
            history.append(
                {
                    "type": "bot",
                    "content": "sage_status",
                    "diagnosis": {"kind": "concierge_line_account", "title": "LINE で相談する"},
                }
            )
        elif resolved == "doc_operator":
            history.append(
                {
                    "type": "bot",
                    "content": "sage_status",
                    "diagnosis": {"kind": "concierge_operator"},
                }
            )


@patch(
    "config.line_config.get_line_official_account_url",
    return_value="https://lin.ee/no4FYRe",
)
@patch(
    "config.line_config.get_line_official_account_qr_url",
    return_value="https://medicine.yutok.dev/static/line/line-official-qr.png",
)
def test_line_payload_casual_variants(_mock_qr, _mock_url):
    client = MagicMock()
    variants = [
        "ラインの友だち追加したい",
        "line url 欲しい",
        "このアプリLINEある？",
    ]
    for text in variants:
        p = build_concierge_payload("doc_operator", text, client)
        assert p["concierge_intent"] == "capabilities", text
        assert "LINE で相談する" in p["content"], text
        assert "https://lin.ee/no4FYRe" in p["content"], text
        assert "運営者は誰" not in p["sage_diagnosis"]["message"], text


def test_operator_contact_intro():
    intro = generate_doc_operator_intro(MagicMock(), "不具合報告したい", history=[])
    assert "フォーム" in intro or "メール" in intro
    assert "個人を特定" not in intro
    intro = generate_doc_operator_intro(MagicMock(), "運営者は誰？", history=[])
    assert "個人を特定" in intro or "お伝えしておりません" in intro
    assert "lin.ee" not in intro.lower()
    assert "友だち追加" not in intro


def test_operator_contact_vs_identity_helpers():
    assert is_operator_identity_question("開発者誰？")
    assert not is_operator_identity_question("不具合報告したい")
    assert is_operator_contact_question("不具合報告したい")
    assert is_operator_contact_question("運営者は誰？")


@patch("src.services.contact_channel_intent.classify_contact_channel_question", return_value=None)
@patch("src.core.llm_client.chat_completion_create")
def test_classify_contact_channel_llm_fallback(mock_chat, _mock_regex):
    body = json.dumps({"kind": "line_account", "confidence": 0.88})
    mock_chat.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=body))]
    )
    kind = classify_contact_channel_llm(
        "LINEのURLちょうだい",
        MagicMock(),
        history=[],
    )
    assert kind == "line_account"
    assert contact_channel_to_concierge_intent(kind) == "capabilities"


@patch("src.core.llm_client.chat_completion_create")
def test_classify_contact_channel_llm_low_confidence_ignored(mock_chat):
    body = json.dumps({"kind": "line_account", "confidence": 0.3})
    mock_chat.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=body))]
    )
    assert (
        classify_contact_channel_llm("なんか連絡したい", MagicMock(), history=[])
        is None
    )


@patch("src.core.llm_client.chat_completion_create")
def test_resolve_uses_llm_when_regex_ambiguous(mock_chat):
    body = json.dumps({"kind": "operator_contact", "confidence": 0.82})
    mock_chat.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=body))]
    )
    session = {"concierge_state": {}}
    resolved = resolve_concierge_intent(
        "開発チームに連絡したい",
        session,
        triage_result={"category": "Other", "confidence": 0.7},
        client=MagicMock(),
        conversation_history=[],
    )
    assert resolved == "doc_operator"
