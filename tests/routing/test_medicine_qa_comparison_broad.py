"""比較 Q&A — 多様な聞き方・口語・文脈依存の広域回帰テスト。"""
from __future__ import annotations

import pytest

from src.services.medicine_qa_comparison_quality import (
    assess_comparison_qa_response,
    build_comparison_answer_scaffold,
    enrich_thin_comparison_answer,
)
from src.services.medicine_qa_routing import (
    build_focused_qa_sections,
    infer_medicine_qa_focus,
    infer_medicine_qa_focuses,
    is_comparison_pick_question,
    is_medicine_information_question,
    merge_focused_qa_sections,
    prune_qa_response,
)
from src.services.status_diagnosis_builder import build_qa_from_chat_response

# --- フィクスチャ ---

LOX_IB_MEDS = [
    {"product_name": "ロキソニンS", "ingredients": "ロキソプロフェンナトリウム", "usage": "1錠"},
    {"product_name": "イブ", "ingredients": "イブプロフェン", "usage": "2錠"},
]

THREE_MEDS = [
    {"product_name": "ロキソニンS", "ingredients": "ロキソプロフェンナトリウム水和物", "usage": "1錠"},
    {"product_name": "バファリンA", "ingredients": "アスピリン", "usage": "2錠"},
    {"product_name": "イブ", "ingredients": "イブプロフェン", "usage": "2錠"},
]

ACET_NSaid_MEDS = [
    {"product_name": "カロナールA", "ingredients": "アセトアミノフェン", "usage": "1錠"},
    {"product_name": "イブ", "ingredients": "イブプロフェン", "usage": "2錠"},
]

RECO_HISTORY = [
    {"role": "user", "content": "頭が痛い"},
    {
        "role": "assistant",
        "content": "sage_reco",
        "diagnosis": {
            "recommended_medicines": [
                {"product_name": "イブ", "ingredients": "イブプロフェン"},
                {"product_name": "バファリンEX", "ingredients": "ロキソプロフェン"},
                {"product_name": "カロナールA", "ingredients": "アセトアミノフェン"},
            ],
        },
    },
]


def _build_comparison_pipeline(
    user_message: str,
    medicines: list[dict],
    *,
    llm_answer: str = "",
    llm_sections: dict | None = None,
    focuses: list[str] | None = None,
) -> dict:
    """ルールベース + 任意 LLM answer をマージして最終 pruned 応答を返す。"""
    fs = focuses or infer_medicine_qa_focuses(user_message, use_llm_enrichment=False)
    rule = build_focused_qa_sections(user_message, medicines)
    parsed: dict = {
        "answer": llm_answer,
        "medicine_details": "",
        "interactions": "",
        "doping_check": "",
        "side_effects": "",
        "consultation_advice": "",
    }
    if llm_sections:
        parsed.update(llm_sections)
    parsed = merge_focused_qa_sections(parsed, rule, fs)
    pruned = prune_qa_response(parsed, user_message, focuses=fs, answer=llm_answer or None)
    if "comparison" in fs:
        pruned = enrich_thin_comparison_answer(pruned, medicines, user_message=user_message)
    return pruned


# --- 1. 比較 intent 検出（口語・日常表現） ---

COMPARISON_PHRASINGS = [
    "ロキソニンとイブの違いって何？",
    "ロキソニンとバファリンとイブの違いは？",
    "ロキソニン vs イブ どっちがいい",
    "バファリンとイブ、何が違うの？",
    "ロキソニンとイブどう違うんですか",
    "イブとバファリン、使い分け教えて",
    "ロキソニンとイブ 効き目どっち強い？",
    "バファリンAとイブ、胃に優しいのどっち",
    "ロキソニン、イブ、バファリン 迷ってる",
    "ロキソニンとイブ どれ選べばいい？",
    "ロキソニンとイブ おすすめどれ",
    "ロキソニンとイブ 比較して",
    "ロキソニンとイブ 同じなの？",
    "ロキソニンとイブ 別物？",
    "ロキソニンとイブ 代わりになる？",
    "ロキソニンとイブ マイルドなのは？",
    "ロキソニンとイブ 結局どれ",
    "ロキソニンとイブ which is better",
    "ロキソニンとイブとバファリン、どれがいい？",
    "ロキソニンとイブ どっち買えばいい",
]

PICK_PHRASINGS = [
    "ロキソニンとイブどっちがいい？",
    "ロキソニンとイブ どれ使う？",
    "ロキソニンとイブ 選べない",
    "ロキソニンとイブ オススメは？",
    "ロキソニンとイブとバファリン、どれがいい？",
]

NOT_COMPARISON = [
    ("ロキソニンって眠い？", "side_effect"),
    ("イブの副作用は？", "side_effect"),
    ("ロキソニンとイブ 一緒に飲んで平気？", None),  # interaction/comparison 混在可、side_effect ではない
    ("頭が痛い", None),
    ("ロキソニンの写真見せて", "product_image"),
]


@pytest.mark.parametrize("msg", COMPARISON_PHRASINGS)
def test_comparison_phrasing_detects_focus(msg: str):
    assert infer_medicine_qa_focus(msg) == "comparison"
    assert is_medicine_information_question(msg)


@pytest.mark.parametrize("msg", PICK_PHRASINGS)
def test_pick_phrasing_is_comparison(msg: str):
    assert "comparison" in infer_medicine_qa_focuses(msg, use_llm_enrichment=False)
    assert is_comparison_pick_question(msg)


@pytest.mark.parametrize("msg,expected_primary", NOT_COMPARISON)
def test_non_comparison_routes(msg: str, expected_primary: str | None):
    if expected_primary == "side_effect":
        focuses = infer_medicine_qa_focuses(msg, use_llm_enrichment=False)
        assert focuses == ["side_effect"] or focuses[0] == "side_effect"
    elif expected_primary == "product_image":
        assert infer_medicine_qa_focus(msg) == "product_image"


# --- 2. 文脈依存（推奨履歴・指示語） ---

CONTEXT_COMPARISON_CASES = [
    ("この3つどれがいい？", RECO_HISTORY, THREE_MEDS),
    ("さっきの薬、どれ使えばいい？", RECO_HISTORY, THREE_MEDS),
    ("推奨された中で一番マイルドなのは？", RECO_HISTORY, THREE_MEDS),
    ("1番と2番、何が違う？", RECO_HISTORY, LOX_IB_MEDS),
]

@pytest.mark.parametrize("msg,history,meds", CONTEXT_COMPARISON_CASES)
def test_context_comparison_intent(msg: str, history: list, meds: list):
    focuses = infer_medicine_qa_focuses(
        msg,
        conversation_history=history,
        recommended_medicines=meds,
        use_llm_enrichment=False,
    )
    assert "comparison" in focuses


def test_context_pick_without_drug_names_in_utterance():
    msg = "どれがいい？"
    focuses = infer_medicine_qa_focuses(
        msg,
        conversation_history=RECO_HISTORY,
        recommended_medicines=THREE_MEDS,
        use_llm_enrichment=False,
    )
    assert "comparison" in focuses


# --- 3. 応答品質（構造ベース — 特定文言に依存しない） ---

QUALITY_CASES = [
    ("ロキソニンとイブの違いは？", LOX_IB_MEDS, ""),
    ("ロキソニンとイブどっちがいい？", LOX_IB_MEDS, ""),
    ("ロキソニンとバファリンとイブの違いは？", THREE_MEDS, ""),
    ("カロナールとイブ どっちが胃に優しい？", ACET_NSaid_MEDS, ""),
    ("ロキソニンとイブ 効き目比較", LOX_IB_MEDS, "両方解熱鎮痛薬です。"),  # 薄い LLM → enrich
    ("ロキソニンとイブの違い", LOX_IB_MEDS, "お近くの登録販売者にご相談ください。"),  # 汎用のみ → enrich
]

@pytest.mark.parametrize("msg,meds,llm_answer", QUALITY_CASES)
def test_comparison_response_quality(msg: str, meds: list, llm_answer: str):
    pruned = _build_comparison_pipeline(msg, meds, llm_answer=llm_answer)
    report = assess_comparison_qa_response(pruned, medicines=meds)
    assert report.ok, report.issues


@pytest.mark.parametrize("msg,meds", [
    ("ロキソニンとイブの違い", LOX_IB_MEDS),
    ("ロキソニンとバファリンとイブ", THREE_MEDS),
])
def test_comparison_status_sections_render(msg: str, meds: list):
    pruned = _build_comparison_pipeline(msg, meds)
    diag = build_qa_from_chat_response(
        pruned,
        feedback_context={"user_message": msg, "ai_response": pruned.get("answer", "")},
    )
    titles = [s.title for s in diag.sections]
    assert "製品比較" in titles
    assert "選び方のポイント" in titles
    assert "剤形はこの情報" not in " ".join(titles)


# --- 4. 成分系統の汎用シナリオ（ロキソニン特化でない） ---

def test_acetaminophen_vs_ibuprofen_scenario_hint():
    pruned = _build_comparison_pipeline(
        "カロナールとイブ どっち？",
        ACET_NSaid_MEDS,
    )
    pick = str(pruned.get("consultation_advice") or "")
    assert "アセトアミノフェン" in pick or "胃" in pick or "NSAIDs" in pick or "向き" in pick


def test_three_way_pick_has_per_product_hints():
    pruned = _build_comparison_pipeline(
        "ロキソニンとイブとバファリン どれ？",
        THREE_MEDS,
    )
    pick = str(pruned.get("consultation_advice") or "")
    assert pick.count("ui-qa-product-line__lead") >= 2


def test_scaffold_enriches_empty_answer():
    out = enrich_thin_comparison_answer({"answer": ""}, LOX_IB_MEDS)
    assert out["answer"]
    assert "ロキソニン" in out["answer"] or "ロキソプロフェン" in out["answer"]


def test_scaffold_builds_ingredient_based_summary():
    text = build_comparison_answer_scaffold(THREE_MEDS)
    assert "ロキソニン" in text
    assert "イブ" in text or "イブプロフェン" in text


def test_expand_medicines_for_comparison_adds_acetaminophen_class():
    from src.services.medicine_qa_comparison_quality import expand_medicines_for_comparison

    session_meds = [
        {"product_name": "イブ", "ingredients": "イブプロフェン"},
        {"product_name": "ノーシンエフ200", "ingredients": "イブプロフェン"},
    ]
    msg = "イブプロフェンとアセトアミノフェンの違いを比較して"
    expanded = expand_medicines_for_comparison(msg, session_meds)
    classes = set()
    for med in expanded:
        ing = str(med.get("ingredients") or "").lower()
        if "アセトアミノフェン" in ing and "イブプロフェン" not in ing:
            classes.add("acet")
        elif "イブプロフェン" in ing or "ロキソプロフェン" in ing:
            classes.add("nsaid")
    assert "acet" in classes
    assert "nsaid" in classes


def test_unwrap_embedded_json_answer():
    from src.services.concierge_output_sanitize import sanitize_medicine_ask_output

    raw = '{ "answer": "はい、飲み合わせは大事です。", "medicine_details": "..." }'
    out = sanitize_medicine_ask_output(raw)
    assert out == "はい、飲み合わせは大事です。"
    assert "medicine_details" not in out


# --- 5. LLM ノイズ上書き（任意入力パターン） ---

LLM_NOISE_PATTERNS = [
    "剤形はこの情報では確認できません",
    "この情報からは確認できません",
    "詳細は登録販売者にご確認ください",
]

@pytest.mark.parametrize("noise", LLM_NOISE_PATTERNS)
def test_rule_sections_override_llm_noise(noise: str):
    msg = "ロキソニンとイブの違い"
    pruned = _build_comparison_pipeline(
        msg,
        LOX_IB_MEDS,
        llm_answer="2つとも解熱鎮痛薬です。",
        llm_sections={
            "medicine_details": f"【ロキソニン】{noise}",
            "consultation_advice": "医師に相談してください。",
        },
    )
    details = str(pruned.get("medicine_details") or "")
    assert "ui-qa-product-line" in details
    assert noise not in details


# --- 6. 併用確認は comparison 単独にしない ---

def test_concurrent_use_not_pure_comparison():
    msg = "ロキソニンとイブ 一緒に飲んで平気？"
    focuses = infer_medicine_qa_focuses(msg, use_llm_enrichment=False)
    # interaction が主。comparison のみにはならない想定
    assert "interaction" in focuses or "comparison" not in focuses or len(focuses) >= 2
