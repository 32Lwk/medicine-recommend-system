"""Tests for session-level conversation analysis."""

from __future__ import annotations

from src.analysis.session_conversation_analysis import (
    build_session_conversations,
    classify_user_input,
    detect_turn_issues,
)


def test_classify_image_gen_and_offensive() -> None:
    assert "image_generation" in classify_user_input("笑顔の画像を生成して")
    assert "offensive" in classify_user_input("🖕")


def test_detect_image_gen_medical_referral() -> None:
    issues = detect_turn_issues(
        user_input="笑顔の画像を生成して",
        response="詳しい症状が分からないため、一度お近くの医療機関にご相談されることをお勧めします。",
        input_labels=classify_user_input("笑顔の画像を生成して"),
        routing={},
        prior_turns=[],
    )
    assert any(i["type"] == "image_gen_medical_referral" for i in issues)


def test_build_session_groups_and_grades() -> None:
    counseling = [
        {
            "timestamp": "2026-06-24T03:00:00",
            "session_id": "line:Uabc",
            "user_input": "やあ",
            "response": "やあ、こちらは市販薬の相談窓口です。",
        },
        {
            "timestamp": "2026-06-24T03:01:00",
            "session_id": "line:Uabc",
            "user_input": "笑顔の画像を生成して",
            "response": "医療機関への受診をお勧めします。",
        },
        {
            "timestamp": "2026-06-24T03:02:00",
            "session_id": "line:Uabc",
            "user_input": "🖕",
            "response": "こんにちは！何かお困りのことがあれば教えてください。",
        },
    ]
    chat_flow = {
        "exported_traces": [
            {
                "trace_id": "t1",
                "session_id": "line:Uabc",
                "started_at": "2026-06-24T03:01:00Z",
                "user_message": "笑顔の画像を生成して",
                "concierge_intent": "greeting",
                "triage": {"category": "Physical", "subcategory": "unknown", "confidence": 0.5},
                "agent_steps": [
                    {
                        "agent": "ConciergeAgent",
                        "step": "complete",
                        "payload": {"handled": True},
                    }
                ],
                "pipeline_perf": {"channel": "line", "total_ms": 3000},
            }
        ]
    }
    result = build_session_conversations(counseling, chat_flow)
    assert result["session_count"] == 1
    session = result["sessions"][0]
    assert session["session_id"] == "line:Uabc"
    assert len(session["turns"]) == 3
    assert session["evaluation"]["overall_grade"] in ("poor", "needs_improvement")
    assert result["mismatch_count"] >= 2
    assert any(m["issue_type"] == "image_gen_medical_referral" for m in result["intent_mismatches"])
