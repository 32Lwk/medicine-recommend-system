"""side_effect_display のユニットテスト。"""
from __future__ import annotations

from src.services.side_effect_display import (
    build_concise_side_effect_answer,
    build_drowsiness_answer,
    build_side_effect_cards_html,
    parse_side_effect_row,
)
from src.services.status_diagnosis_builder import build_side_effect_qa_from_chat_response


LOXO_ROW = {
    "成分名": "ロキソプロフェンナトリウム水和物",
    "副作用レベル": "高",
    "副作用症状": (
        "11.1 重大な副作用 11.1.1 ショック(頻度不明)、アナフィラキシー(頻度不明) "
        "ショック、アナフィラキシー(血圧低下、蕁麻疹、喉頭浮腫、呼吸困難等)があらわれることがある。 "
        "11.1.2 無顆粒球症(頻度不明)、白血球減少(頻度不明) "
        "11.2 その他の副作用 傾眠 頭痛 胃腸障害"
    ),
}


def test_parse_side_effect_row_extracts_serious_and_common():
    parsed = parse_side_effect_row(LOXO_ROW)
    assert "ショック" in parsed["serious"]
    assert "アナフィラキシー" in parsed["serious"]
    assert "傾眠" in parsed["common"] or "頭痛" in parsed["common"]


def test_build_side_effect_cards_html_is_structured_not_raw_pmda():
    html = build_side_effect_cards_html([LOXO_ROW])
    assert "ui-side-effect-card" in html
    assert "11.1 重大な副作用" not in html
    assert "ショック" in html
    assert "アナフィラキシー" in html


def test_build_side_effect_cards_html_groups_related_serious_effects():
    html = build_side_effect_cards_html([LOXO_ROW])
    assert "アナフィラキシーショック" in html
    assert "ショック・アナフィラキシー" not in html


def test_build_side_effect_cards_html_reference_mode_is_collapsed():
    html = build_side_effect_cards_html([LOXO_ROW], reference_only=True)
    assert "ui-side-effect-details" in html
    assert "ui-side-effect-list--compact" in html


def test_build_drowsiness_answer_for_loxoprofen_is_concise():
    answer = build_drowsiness_answer("ロキソニンＳ", [LOXO_ROW])
    assert "ロキソニン" in answer
    assert "11.1" not in answer
    assert len(answer) < 220


def test_build_concise_side_effect_answer_not_wall_of_text():
    answer = build_concise_side_effect_answer("ロキソニンＳ", [LOXO_ROW])
    assert "11.1" not in answer
    assert "主な副作用" in answer or "要点" in answer


def test_build_side_effect_qa_from_chat_response_uses_html_section():
    diag = build_side_effect_qa_from_chat_response(
        {
            "answer": "要点です。",
            "side_effect_html": '<div class="ui-side-effect-list"></div>',
            "qa_kind": "medicine_side_effect_qa",
        }
    )
    assert diag.kind == "medicine_side_effect_qa"
    assert len(diag.sections) == 1
    assert diag.sections[0].html
    assert not diag.sections[0].items
