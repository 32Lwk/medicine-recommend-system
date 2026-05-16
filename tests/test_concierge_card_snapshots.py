"""Concierge カード HTML の安定性（スナップショット的検証）"""
import hashlib

from src.services.concierge_templates import (
    format_concierge_app_about_card,
    format_concierge_architecture_card,
    format_concierge_capabilities_card,
)


def _stable_hash(html: str) -> str:
    normalized = " ".join(html.split())
    return hashlib.sha256(normalized.encode()).hexdigest()


def test_capabilities_card_stable_structure():
    fb = {"user_message": "test", "ai_response": "concierge:capabilities"}
    html = format_concierge_capabilities_card(feedback_data=fb)
    assert "chat-status-card--notice" in html
    assert "できること" in html
    assert "できないこと" in html
    assert "feedback-buttons" in html
    h1 = _stable_hash(html)
    h2 = _stable_hash(format_concierge_capabilities_card(feedback_data=fb))
    assert h1 == h2


def test_architecture_card_stable_structure():
    html = format_concierge_architecture_card()
    assert "TriageAgent" in html
    assert "PhysicalOrchestrator" in html
    assert "ConciergeAgent" in html
    h1 = _stable_hash(html)
    h2 = _stable_hash(format_concierge_architecture_card())
    assert h1 == h2


def test_app_about_card_stable_structure():
    html = format_concierge_app_about_card()
    assert "β版" in html or "試験" in html
    h1 = _stable_hash(html)
    h2 = _stable_hash(format_concierge_app_about_card())
    assert h1 == h2
