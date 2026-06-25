"""法令・コンプライアンス質問の Concierge ルーティングテスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.agents.concierge_agent import build_concierge_payload, should_concierge_handle
from src.services.concierge_intent import (
    is_legal_compliance_meta_question,
    probe_meta_concierge_intent,
    should_exit_counseling_for_concierge,
)
from src.services.concierge_orchestrator import enrich_other_concierge_intent


@pytest.mark.parametrize(
    "text",
    [
        "薬機法上問題ないの？",
        "薬機法大丈夫？",
        "このアプリは違法じゃない？",
    ],
)
def test_legal_compliance_is_not_medicine_consultation(text: str):
    from src.services.concierge_intent import _is_medicine_consultation

    assert is_legal_compliance_meta_question(text)
    assert not _is_medicine_consultation(text)


def test_yakujihou_routes_to_doc_terms_probe():
    assert probe_meta_concierge_intent("薬機法上問題ないの？") == "doc_terms"


def test_purapori_routes_to_doc_privacy_probe():
    assert probe_meta_concierge_intent("プラポリは？") == "doc_privacy"


def test_should_concierge_handle_yakujihou_without_prior_intent():
    triage = {"category": "Other", "confidence": 0.95}
    assert should_concierge_handle("薬機法上問題ないの？", triage)


def test_should_exit_counseling_for_yakujihou():
    assert should_exit_counseling_for_concierge("薬機法上問題ないの？")


def test_enrich_other_keyword_probe_yakujihou():
    triage = {"category": "Other", "confidence": 0.99, "subcategory": "general_other"}
    enriched = enrich_other_concierge_intent(
        triage,
        "薬機法上問題ないの？",
        MagicMock(),
        conversation_history=[],
    )
    assert enriched.get("concierge_intent") == "doc_terms"
    assert enriched.get("concierge_intent_source") == "keyword_probe"


@patch("src.agents.concierge_agent.concierge_chat")
def test_yakujihou_doc_terms_payload(mock_chat):
    mock_chat.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content=(
                        "・本アプリは診断・処方を行わないOTC参考案内のβ版です。\n"
                        "・第3条に基づき、薬機法・景表法を踏まえた設計を目指しています。\n"
                        "・法令適合を運営者が保証するものではありません。\n"
                        "・詳細は画面右上の ℹ️ から利用規約全文をご確認ください。"
                    )
                )
            )
        ]
    )
    p = build_concierge_payload(
        "doc_terms",
        "薬機法上問題ないの？",
        MagicMock(),
    )
    assert p["concierge_intent"] == "doc_terms"
    assert p.get("content_format") == "status_card"
    assert "ℹ️" in p["sage_diagnosis"]["message"] or "ℹ" in p["sage_diagnosis"]["message"]
