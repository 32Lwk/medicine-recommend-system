"""medicine_qa_routing — session 文脈付き focus 推定。"""
from __future__ import annotations

from unittest.mock import patch

from src.services.medicine_qa_routing import (
    get_medicine_qa_session_context,
    infer_medicine_qa_focuses_for_session,
)


def test_get_medicine_qa_session_context_reads_recommended_from_bot_diagnosis():
    session = {
        "messages": [
            {"type": "user", "content": "頭痛"},
            {
                "type": "bot",
                "diagnosis": {
                    "recommended_medicines": [{"product_name": "ロキソニン"}],
                },
            },
            {"type": "user", "content": "それの用法は？"},
        ],
        "user_attributes": {"age": 30},
    }
    with patch("src.services.session_manager.get_session_from_db", return_value=session):
        ctx = get_medicine_qa_session_context(session, "sid1")
    assert ctx["recommended_medicines"][0]["product_name"] == "ロキソニン"
    assert ctx["user_attributes"]["age"] == 30
    assert len(ctx["conversation_history"]) == 3


def test_infer_medicine_qa_focuses_for_session_uses_anaphora_with_history():
    session = {
        "messages": [
            {"type": "user", "content": "ロキソニンを飲んでいます"},
            {"type": "bot", "content": "承知しました"},
        ],
    }
    with patch("src.services.session_manager.get_session_from_db", return_value=session):
        focuses = infer_medicine_qa_focuses_for_session("それの用法は？", session, "sid1")
    assert "usage" in focuses
