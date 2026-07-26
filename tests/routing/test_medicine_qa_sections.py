"""medicine_qa 補足セクションの意図ベース生成テスト。"""
from __future__ import annotations

from src.core.medicine.medicine_response_builder import (
    _build_structured_qa_from_stream,
    _finalize_structured_qa_response,
    detect_medicine_name_in_query,
)
from src.services.medicine_qa_routing import (
    _pick_advice_lines,
    build_focused_qa_sections,
    infer_medicine_qa_focus,
    infer_medicine_qa_focuses,
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
    assert "ui-qa-product-line" in comparison.html
    assert "NSAIDs" not in comparison.html
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


def test_pick_advice_differentiates_loxonin_and_ib():
    msg = "ロキソニンとイブどっちがいい？"
    meds = [
        {"product_name": "ロキソニンＳ", "ingredients": "ロキソプロフェンナトリウム"},
        {"product_name": "イブ", "ingredients": "イブプロフェン"},
    ]
    advice = _pick_advice_lines(meds, msg)
    assert "ui-qa-product-line" in advice
    assert "効き目を重視" in advice
    assert "マイルド" in advice
    assert advice.count("効き目重視向き") <= 1


def test_product_image_focus_excludes_comparison():
    msg = "ロキソニンとイブの画像見せて"
    focuses = infer_medicine_qa_focuses(msg)
    assert focuses == ["product_image"]


def test_streaming_qa_attaches_product_images_and_unifies_answer():
    msg = "ロキソニンとイブの画像見せて"
    meds = [
        {"product_name": "ロキソニンＳ", "ingredients": "ロキソプロフェン"},
        {"product_name": "イブ", "ingredients": "イブプロフェン"},
    ]
    parsed = _build_structured_qa_from_stream(
        msg,
        meds,
        "この画面では画像を直接お見せできません。",
        qa_focuses=["product_image"],
    )
    assert "product_images_html" in parsed
    assert "ui-qa-product-images" in parsed["product_images_html"]
    assert "お見せできません" not in parsed["answer"]
    assert "見せられません" not in parsed["answer"]
    assert "パッケージ画像" in parsed["answer"]
    assert "まだ準備できていません" not in parsed["answer"]
    assert "ロキソプロフェン" in parsed["answer"]
    assert "イブプロフェン" in parsed["answer"]
    assert not parsed.get("interactions")


def test_fast_product_image_qa_skips_llm_and_kb(monkeypatch):
    from src.core.medicine.medicine_response_builder import chat_with_medicine_context

    monkeypatch.setattr(
        "src.dialogue.routing.context_signals.extract_drug_entities",
        lambda _t: ["ロキソニン", "イブ"],
    )
    monkeypatch.setattr(
        "src.core.medicine.medicine_response_builder.detect_medicine_name_in_query",
        lambda *_a, **_k: [
            {"product_name": "ロキソニンS", "ingredients": "ロキソプロフェン"},
            {"product_name": "イブ", "ingredients": "イブプロフェン"},
        ],
    )
    monkeypatch.setattr(
        "src.core.medicine.medicine_response_builder.pd.read_csv",
        lambda *_a, **_k: object(),
    )

    def _fail_llm(*_a, **_k):
        raise AssertionError("LLM should not be called for product_image QA")

    def _fail_kb(*_a, **_k):
        raise AssertionError("KB augment should not run for product_image QA")

    monkeypatch.setattr(
        "src.core.llm_client.chat_completion_create",
        _fail_llm,
    )
    monkeypatch.setattr(
        "src.core.llm_client.chat_completion_stream",
        _fail_llm,
    )
    monkeypatch.setattr(
        "src.services.bedrock_kb_retrieve.augment_medicine_prompt_with_kb",
        _fail_kb,
    )

    parsed = chat_with_medicine_context(
        "ロキソニンとイブの画像見せて",
        [],
        [],
        session_id="sid-fast-product-image",
    )
    assert "product_images_html" in parsed
    assert "パッケージ画像" in parsed["answer"]


def test_finalize_structured_qa_preserves_prebuilt_html_sections():
    msg = "ロキソニンとイブどっちがいい？"
    meds = [
        {"product_name": "ロキソニンＳ", "ingredients": "ロキソプロフェン", "efficacy": "痛"},
        {"product_name": "イブ", "ingredients": "イブプロフェン", "efficacy": "痛"},
    ]
    focused = build_focused_qa_sections(msg, meds)
    focused["answer"] = "比較回答"
    finalized = _finalize_structured_qa_response(
        focused,
        msg,
        meds,
        qa_focuses=["comparison"],
        answer="比較回答",
    )
    diag = build_qa_from_chat_response(
        finalized,
        feedback_context={"user_message": msg, "ai_response": "比較回答"},
    )
    pick = next(s for s in diag.sections if s.title == "選び方のポイント")
    assert "ui-qa-product-line__lead" in pick.html
    assert "マイルド" in pick.html
