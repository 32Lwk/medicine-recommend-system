"""medicine_qa 補足セクションの意図ベース生成テスト。"""
from __future__ import annotations

from src.core.medicine.medicine_response_builder import (
    _build_structured_qa_from_stream,
    detect_medicine_name_in_query,
)
from src.services.medicine_qa_routing import (
    build_focused_qa_sections,
    infer_medicine_qa_focus,
    is_generic_qa_boilerplate,
    prune_qa_response,
)
from src.services.status_diagnosis_builder import build_qa_from_chat_response


def test_comparison_focus_detected():
    msg = "ロキソニンとイブの違いって何？"
    assert infer_medicine_qa_focus(msg) == "comparison"


def test_comparison_sections_omit_generic_boilerplate():
    msg = "ロキソニンとイブの違いって何？"
    meds = [
        {
            "product_name": "ロキソニンＳ",
            "ingredients": "ロキソプロフェンナトリウム",
            "efficacy": "疼痛",
            "medicine_type": "解熱鎮痛薬",
        },
        {
            "product_name": "イブ",
            "ingredients": "イブプロフェン",
            "efficacy": "疼痛",
            "medicine_type": "解熱鎮痛薬",
        },
    ]
    parsed = _build_structured_qa_from_stream(
        msg,
        meds,
        "ロキソニンはロキソプロフェン、イブはイブプロフェンが主成分です。",
    )
    assert not is_generic_qa_boilerplate(parsed.get("medicine_details", ""))
    assert "ロキソニン" in parsed["medicine_details"]
    assert "イブ" in parsed["medicine_details"]
    assert not parsed.get("doping_check")
    assert "風邪薬を複数同時" not in str(parsed.get("interactions", ""))


def test_build_qa_status_uses_comparison_section_title():
    msg = "ロキソニンとイブの違いって何？"
    chat = build_focused_qa_sections(
        msg,
        [
            {"product_name": "ロキソニンＳ", "ingredients": "ロキソプロフェン", "efficacy": "痛"},
            {"product_name": "イブ", "ingredients": "イブプロフェン", "efficacy": "痛"},
        ],
    )
    chat["answer"] = "比較回答"
    pruned = prune_qa_response(chat, msg)
    diag = build_qa_from_chat_response(
        pruned,
        feedback_context={"user_message": msg, "ai_response": "比較回答"},
    )
    titles = [s.title for s in diag.sections]
    assert "製品比較" in titles
    assert "ドーピングチェック" not in titles
    comparison = next(s for s in diag.sections if s.title == "製品比較")
    assert comparison.html
    assert "<strong>ロキソニンＳ</strong>" in comparison.html
    assert "<strong>イブ</strong>" in comparison.html
    assert "<br>" in comparison.html
    assert "**" not in comparison.html


def test_brand_hint_detects_loxonin_and_ib():
    import os

    import pandas as pd

    from src.core.medicine_data import CSV_PATH

    if not os.path.exists(CSV_PATH):
        return
    df = pd.read_csv(CSV_PATH, encoding="utf-8")
    hits = detect_medicine_name_in_query("ロキソニンとイブの違いって何？", df)
    names = {h["product_name"] for h in hits}
    assert any("ロキソニン" in n for n in names)
    assert any("イブ" in n for n in names)
