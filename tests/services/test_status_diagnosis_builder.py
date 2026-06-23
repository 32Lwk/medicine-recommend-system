"""Tests for status diagnosis builder."""
from src.services.status_diagnosis_builder import (
    SAGE_STATUS_MARKER,
    build_concierge_app_about_status,
    build_concierge_architecture_status,
    build_concierge_capabilities_status,
    build_concierge_text_status,
    build_counseling_status,
    build_crisis_status,
    build_attribute_update_status,
    build_user_info_registration_status,
    build_diagnosis_notice,
    build_emergency_status,
    build_error_status,
    build_notice_status,
    build_qa_from_chat_response,
    build_store_status,
    build_store_status_from_inquiry_result,
    build_system_error_status,
)

def test_sage_status_marker():
    assert SAGE_STATUS_MARKER == "sage_status"


def test_build_diagnosis_notice():
    diag = build_diagnosis_notice("医師にご相談ください。")
    assert diag.render == "sage_status"
    assert diag.variant == "notice"
    assert "医師" in diag.message


def test_build_error_status():
    diag = build_error_status("no_candidates", {})
    assert diag.variant == "caution"
    assert diag.title


def test_build_system_error_status():
    diag = build_system_error_status()
    assert diag.variant == "error"
    assert diag.kind == "system_error"


def test_build_concierge_text_status():
    diag = build_concierge_text_status("こんにちは。", title="ご挨拶", kind="concierge_greeting")
    assert diag.layout == "plain"
    assert diag.message == "こんにちは。"
    assert diag.show_feedback is False


def test_build_medicine_type_unrecognized_status():
    from src.services.status_diagnosis_builder import build_medicine_type_unrecognized_status

    diag = build_medicine_type_unrecognized_status()
    assert diag.render == "sage_status"
    assert diag.variant == "caution"
    assert diag.title == "症状から医薬品を選べませんでした"
    assert "医薬品種類が判定できませんでした" in diag.message
    assert "⚠️" not in diag.message


def test_build_crisis_status():
    diag = build_crisis_status(
        "相談窓口をご案内します。",
        resources=[{"name": "いのちの電話", "contact": "0120-783-556"}],
    )
    assert diag.variant == "security"
    assert diag.sections


def test_build_store_status():
    diag = build_store_status(simple_message="トイレは2階にございます。", inquiry_type="store_inquiry")
    assert diag.render == "sage_status"
    assert "トイレ" in diag.message


def test_build_store_status_with_html_section():
    diag = build_store_status(
        simple_message="トイレは2階です。",
        inquiry_type="store_inquiry",
        html="<p>詳細案内</p>",
    )
    assert diag.sections
    assert diag.sections[0].html == "<p>詳細案内</p>"


def test_build_store_status_from_inquiry_result_inventory():
    result = {
        "inquiry_type": "inventory",
        "product_category": {
            "category": "ビューティ・トイレタリー",
            "subcategory": "歯ブラシ",
            "product": "歯ブラシ",
        },
    }
    diag = build_store_status_from_inquiry_result(
        result,
        simple_message="「歯ブラシ」の在庫・お取り扱いについてお尋ねいただき、ありがとうございます。",
    )
    assert diag.title == "在庫確認"
    assert "歯ブラシ" in diag.message
    assert not diag.sections


def test_build_store_status_from_inquiry_result_facilities():
    result = {"inquiry_type": "facilities", "facility_name": "コンビニ"}
    diag = build_store_status_from_inquiry_result(result, simple_message="周辺施設について。")
    assert diag.title == "周辺施設"
    assert diag.sections[0].items == ["コンビニ"]


def test_build_emergency_status():
    diag = build_emergency_status(subtype="medical_self", language="ja")
    assert diag.variant == "critical"
    assert diag.title


def test_build_qa_from_chat_response():
    diag = build_qa_from_chat_response(
        {
            "answer": "用法用量を守ってください。",
            "medicine_details": "詳細テキスト",
        },
        feedback_context={"user_message": "q", "ai_response": "a"},
    )
    assert diag.render == "sage_qa"
    assert diag.sections
    assert diag.feedback_context["user_message"] == "q"


def test_build_concierge_capabilities_status():
    diag = build_concierge_capabilities_status()
    assert diag.render == "sage_status"
    assert diag.sections


def test_build_concierge_architecture_status():
    diag = build_concierge_architecture_status()
    assert diag.render == "sage_status"
    assert diag.sections
    assert "アルゴリズム" in diag.sections[0].items[0]


def test_build_concierge_app_about_status():
    diag = build_concierge_app_about_status()
    assert diag.render == "sage_status"
    assert diag.title == "このツールについて"
    assert "こちらは" in diag.message
    assert diag.message.count("\n") == 0


def test_build_notice_status():
    diag = build_notice_status("詳しく症状を教えてください。", title="症状を特定できませんでした")
    assert diag.render == "sage_status"
    assert "症状" in diag.message


def test_build_attribute_update_status():
    diag = build_attribute_update_status({"age": 30, "gender": "女性", "allergies": [], "current_medications": []})
    assert diag.sections
    assert diag.kind == "attribute_update_confirmation"
