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


def test_classify_meta_follow_up() -> None:
    assert "meta_follow_up" in classify_user_input("技術面を詳しく")


def test_detect_meta_follow_up_to_greeting() -> None:
    issues = detect_turn_issues(
        user_input="技術面を詳しく",
        response="こんにちは！市販薬に関する相談を承っております。",
        input_labels=classify_user_input("技術面を詳しく"),
        routing={"concierge_intent": "greeting"},
        prior_turns=[],
    )
    assert any(i["type"] == "meta_follow_up_to_greeting" for i in issues)
    assert any(i["severity"] == "critical" for i in issues)


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


def test_build_session_expands_conversation_history() -> None:
    counseling = [
        {
            "timestamp": "2026-06-25T05:36:23",
            "session_id": "line:Uabc",
            "user_input": "おまえだれ？",
            "response": "私はツールです。",
            "conversation_history": [
                {"type": "user", "content": "😄"},
                {"type": "bot", "content": "絵文字だけだと意図が伝わりにくい場合があります。"},
                {"type": "user", "content": "ああ"},
                {"type": "bot", "content": "こんにちは！お越しいただきありがとうございます。"},
                {"type": "user", "content": "おまえだれ？"},
            ],
        }
    ]
    result = build_session_conversations(counseling, {"exported_traces": []})
    session = result["sessions"][0]
    assert len(session["turns"]) == 3
    assert session["turns"][0]["user_input"] == "😄"
    assert session["turns"][-1]["user_input"] == "おまえだれ？"


def test_build_session_includes_trace_only_turns() -> None:
    chat_flow = {
        "trace_count": 2,
        "exported_traces": [
            {
                "trace_id": "t1",
                "session_id": "sess-web",
                "started_at": "2026-06-24T03:00:00Z",
                "user_message": "このツールで何ができる？",
                "concierge_intent": "capabilities",
                "pipeline_perf": {"channel": "web", "total_ms": 5000.0, "sid": "sess-web"},
            },
            {
                "trace_id": "t2",
                "session_id": "sess-web",
                "started_at": "2026-06-24T03:01:00Z",
                "user_message": "誰が答えた？",
                "concierge_intent": "architecture",
                "pipeline_perf": {"channel": "web", "total_ms": 4000.0, "sid": "sess-web"},
            },
        ],
    }
    result = build_session_conversations([], chat_flow)
    assert result["trace_only_session_count"] == 1
    session = result["sessions"][0]
    assert session["session_id"] == "sess-web"
    assert session["trace_only"] is True
    assert len(session["turns"]) == 2
    assert session["turns"][0]["response_missing"] is True
    assert session["turns"][0]["routing"]["concierge_intent"] == "capabilities"
