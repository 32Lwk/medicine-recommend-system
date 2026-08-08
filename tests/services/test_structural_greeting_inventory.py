"""structural greeting ブロック — medicine inventory followup"""
from __future__ import annotations

from src.services.concierge_agent_history import should_block_structural_greeting
from src.services.concierge_intent import infer_structural_concierge_intent


def test_structural_greeting_blocked_after_medicine_qa_inventory():
    history = [
        {"type": "user", "content": "ロキソニンの写真を見せてください"},
        {
            "type": "bot",
            "content": "sage_qa",
            "diagnosis": {"kind": "medicine_qa", "message": "ロキソニンSの画像です。"},
        },
    ]
    assert should_block_structural_greeting(
        "家にもあります",
        conversation_history=history,
    )
    assert infer_structural_concierge_intent(
        "家にもあります",
        conversation_history=history,
    ) is None


def test_structural_greeting_allowed_without_medicine_context():
    assert not should_block_structural_greeting("やあ")
    assert infer_structural_concierge_intent("やあ") == "greeting"
