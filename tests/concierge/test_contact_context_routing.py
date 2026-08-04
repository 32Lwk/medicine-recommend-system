"""Contact channel context routing tests."""
from __future__ import annotations

from src.services.contact_channel_intent import (
    classify_contact_channel_question,
    is_service_contact_ui_request,
    normalize_operator_intro_for_inline_card,
)
from src.services.medicine_qa_eligibility import MedicineQaRoute, resolve_medicine_qa_route


def test_resolve_prior_meta_from_session_messages():
    from src.services.concierge_agent_history import resolve_prior_meta_intent

    session = {
        "messages": [
            {"type": "user", "content": "運用者はだれ？"},
            {
                "type": "bot",
                "concierge_intent": "doc_operator",
                "diagnosis": {"kind": "concierge_doc_operator"},
            },
        ]
    }
    assert resolve_prior_meta_intent(session=session) == "doc_operator"


def test_normalize_operator_intro_replaces_deferred_card_wording():
    raw = "ご連絡先はこの直後の案内カードにありますので、そちらからお問い合わせください。"
    out = normalize_operator_intro_for_inline_card(raw)
    assert "直後の案内カード" not in out
    assert "下記" in out


def test_standalone_guide_card_not_payment_inquiry():
    from src.services.store_inquiry_handler import (
        detect_payment_inquiry,
        is_probable_store_inquiry,
    )

    t = "案内カード見せて"
    assert detect_payment_inquiry(t) is False
    assert is_probable_store_inquiry(t, {"category": "Other"}) is False
    assert classify_contact_channel_question(t) == "operator_contact"


def test_service_contact_follow_up_after_operator():
    history = [
        {"type": "user", "content": "運用者はだれ？"},
        {
            "type": "bot",
            "content": "sage_status",
            "diagnosis": {
                "kind": "concierge_doc_operator",
                "message": "下記のお問い合わせ欄からご連絡ください。",
            },
        },
    ]
    assert is_service_contact_ui_request("見せて", history=history)
    assert classify_contact_channel_question("見せて", history=history) == "operator_contact"


def test_card_follow_up_not_medicine_qa():
    history = [
        {"type": "user", "content": "運用者はだれ？"},
        {"type": "bot", "content": "sage_status", "diagnosis": {"kind": "concierge_operator"}},
    ]
    d = resolve_medicine_qa_route("案内カード見せて", conversation_history=history)
    assert d.route == MedicineQaRoute.CONCIERGE
    assert d.concierge_intent == "doc_operator"


def test_build_operator_status_has_sections():
    from src.services.status_diagnosis_builder import build_concierge_operator_status

    diag = build_concierge_operator_status("お問い合わせありがとうございます。")
    assert diag.layout == "card"
    assert diag.sections
    assert "mailto:" in (diag.sections[0].html or "")
