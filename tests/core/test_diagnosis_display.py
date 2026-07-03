"""診断名のユーザー向け表示・略称マッチテスト。"""
from __future__ import annotations

from src.core.diagnosis_display import (
    format_diagnosis_user_label,
    format_diagnosis_user_label_quoted,
    join_diagnosis_user_labels,
)
from src.core.diagnosis_detection import (
    find_diagnosis_match_span,
    is_diagnosis_term,
)


def test_format_abbreviation_with_expansion():
    assert format_diagnosis_user_label("AN") == "AN（神経性無食欲症）"
    assert format_diagnosis_user_label("PTSD") == "PTSD（心的外傷後ストレス障害）"
    assert format_diagnosis_user_label_quoted("AN") == "「AN（神経性無食欲症）」"


def test_format_full_name_unchanged():
    assert format_diagnosis_user_label("糖尿病") == "糖尿病"
    assert format_diagnosis_user_label("神経性無食欲症") == "神経性無食欲症"


def test_join_multiple_labels():
    joined = join_diagnosis_user_labels(["AN", "糖尿病"])
    assert joined == "AN（神経性無食欲症）、糖尿病"


def test_diagnosis_message_includes_expanded_label():
    _, _, response = is_diagnosis_term("ANですが、頭痛があります")
    assert response is not None
    message = response.get("message") or ""
    assert "AN（神経性無食欲症）" in message
    assert message.startswith("「AN（神経性無食欲症）」をお持ちの方へ")


def test_abbreviation_not_matched_inside_english_word():
    assert find_diagnosis_match_span("AN", "CHANGELOG digest ってなに？") is None
    assert find_diagnosis_match_span("PE", "OPEN") is None
    is_diagnosis, _, _ = is_diagnosis_term("CHANGELOG digest ってなに？")
    assert is_diagnosis is False


def test_abbreviation_matches_at_word_boundary():
    assert find_diagnosis_match_span("AN", "ANです") == (0, 2)
    assert find_diagnosis_match_span("ADHD", "ADHDの治療について") == (0, 4)
    is_diagnosis, diagnosis_type, _ = is_diagnosis_term("ANです。")
    assert is_diagnosis is True
    assert diagnosis_type == "mental_health"


def test_abbreviation_labels_medically_precise():
    assert format_diagnosis_user_label("ITP") == "ITP（免疫性血小板減少症）"
    assert format_diagnosis_user_label("IPF") == "IPF（特発性肺線維症）"


def test_non_medical_context_blocks_short_abbrev():
    assert find_diagnosis_match_span("IC", "ICカードをなくした") is None
    assert find_diagnosis_match_span("MS", "MS Officeの設定") is None
    assert find_diagnosis_match_span("FD", "FD口座に振り込み") is None
    assert find_diagnosis_match_span("IC", "ICの症状について") == (0, 2)
