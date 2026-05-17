"""Concierge カード HTML のスナップショット的検証"""
from src.services.concierge_templates import (
    format_concierge_architecture_card,
    format_concierge_capabilities_card,
    format_concierge_operator_card,
)


def test_capabilities_card_contains_otc():
    html = format_concierge_capabilities_card()
    assert "chat-status-card" in html
    assert "OTC" in html or "一般用" in html
    assert "処方" in html


def test_architecture_card_lists_agents():
    html = format_concierge_architecture_card()
    assert "ルールベース" in html
    assert "TriageAgent" in html
    assert "ConciergeAgent" in html
    assert "案内できません" not in html


def test_operator_card_has_clickable_links_without_personal_attributes():
    html = format_concierge_operator_card(
        intro_text="試験運用中のβ版です。",
    )
    assert "chat-status-card" in html
    assert "お問い合わせ・試験運用について" in html
    assert "試験運用中のβ版です。" in html
    assert 'href="https://forms.gle/UB8kZHd4VHenmRUN6"' in html
    assert 'href="mailto:weary-scoots.7y@icloud.com"' in html
    assert "川嶋" not in html
    assert "名古屋大学" not in html
    assert "GitHub" not in html
