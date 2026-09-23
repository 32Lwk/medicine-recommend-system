"""Adversarial / false-negative oriented tests for Jev free-text PII redaction."""
from __future__ import annotations

import pytest

from src.dialogue.routing.jev_pii_redact import redact_pii_text
from src.dialogue.routing.jev_router import (
    ForbiddenJevStateError,
    build_jev_router_state,
    scrub_forbidden_jev_state_keys,
    validate_jev_state_contract,
)


@pytest.mark.parametrize(
    "raw,must_absent,rule",
    [
        (
            "連絡先は taro.yamada+otc@example.co.jp です。頭痛がします",
            "taro.yamada+otc@example.co.jp",
            "email",
        ),
        (
            "電話は 090-1234-5678 です。咳が止まりません",
            "090-1234-5678",
            "phone",
        ),
        (
            "携帯09012345678にかけてください。熱があります",
            "09012345678",
            "phone",
        ),
        (
            "Call me at +1 (415) 555-0199 about my stomachache",
            "415",
            "phone",
        ),
        (
            "住所は〒150-0001 東京都渋谷区神宮前1-2-3です。のどが痛い",
            "150-0001",
            "postal",
        ),
        (
            "カード 4111 1111 1111 1111 で払い、胃薬ください",
            "4111 1111 1111 1111",
            "cardish",
        ),
        (
            "LINEは U0123456789abcdef0123456789abcdef です。薬局どこ？",
            "U0123456789abcdef0123456789abcdef",
            "line_user",
        ),
        (
            "神奈川県横浜市西区みなとみらい1-1-1に住んでいます。鼻水が止まらない",
            "横浜市西区",
            "jp_address",
        ),
        (
            "氏名：山田太郎 です。風邪薬を探しています",
            "山田太郎",
            "labeled_name",
        ),
        (
            "マイナンバーは 1234-5678-9012 です。眠気があります",
            "1234-5678-9012",
            "my_numberish",
        ),
    ],
)
def test_adversarial_pii_false_negatives_are_redacted(raw, must_absent, rule):
    out, hits = redact_pii_text(raw)
    assert must_absent not in out
    assert rule in hits
    assert "[REDACTED_" in out


def test_medical_symptom_without_identifiers_is_preserved():
    raw = "昨日から頭痛と発熱があります。市販の解熱剤はありますか？"
    out, hits = redact_pii_text(raw)
    assert out == raw
    assert hits == []


def test_build_state_redacts_user_input_and_recent_turns():
    session = {
        "messages": [
            {"type": "user", "content": "連絡先 mail@evil.example です"},
            {"type": "bot", "content": "承知しました"},
        ]
    }
    state = build_jev_router_state(
        "電話 080-1111-2222 と 大阪府大阪市北区梅田1-1 です。咳が続きます",
        session,
        "sid-pii",
    )
    assert "080-1111-2222" not in state["user_input"]
    assert "mail@evil.example" not in str(state["recent_turns"])
    assert "active_symptoms" not in state.get("meta", {})
    assert len(state["recent_turns"]) <= 2


def test_forbidden_medical_profile_and_system_prompt_keys():
    bad = {
        "channel": "web",
        "user_input": "x",
        "recent_turns": [],
        "recent_context": [],
        "meta": {"system_prompt": "secret", "active_symptoms": ["発熱"]},
        "app_context": "Japanese OTC medicine routing",
        "medical_profile": {"age": 40},
    }
    with pytest.raises(ForbiddenJevStateError):
        validate_jev_state_contract(bad)
    removed = scrub_forbidden_jev_state_keys(bad)
    assert "medical_profile" in removed
    assert "meta.system_prompt" in removed or "meta.active_symptoms" in removed
    assert "medical_profile" not in bad
    assert "system_prompt" not in bad.get("meta", {})
    assert "active_symptoms" not in bad.get("meta", {})


def test_diagnosis_symptoms_in_session_are_not_exported():
    session = {
        "messages": [
            {
                "type": "bot",
                "content": "症状を確認しました",
                "diagnosis": {"symptoms": ["高熱", "激しい咳", "私の住所は東京都新宿区"]},
            }
        ]
    }
    state = build_jev_router_state("続きの質問", session, "sid")
    assert "active_symptoms" not in state.get("meta", {})
    blob = str(state)
    assert "高熱" not in blob
    assert "diagnosis" not in state
