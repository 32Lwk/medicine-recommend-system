"""
medicine_qa_eligibility — 多様な入力パターンのマトリクステスト。

割合目安:
  医薬品 Q&A  ~40%
  Concierge   ~35%（architecture / redirect / app_about / chitchat 等）
  Physical    ~15%
  DEFER       ~10%
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
from unittest.mock import MagicMock, patch

import pytest

from src.services.medicine_qa_eligibility import (
    MedicineQaRoute,
    resolve_medicine_qa_route,
)


@dataclass(frozen=True)
class EligibilityCase:
    id: str
    text: str
    expected_route: MedicineQaRoute
    expected_intent: Optional[str] = None
    history: Optional[list[dict[str, Any]]] = None
    recs: Optional[list[dict[str, Any]]] = None
    triage: Optional[dict[str, Any]] = None
    use_llm_mock: Optional[str] = None  # mock LLM return intent


# --- 医薬品 Q&A（明示・口語・競技・属性） ---
MEDICINE_QA_CASES = [
    EligibilityCase("mq_explicit_cold", "陸上競技でも使える風邪薬を教えてください。", MedicineQaRoute.MEDICINE_QA),
    EligibilityCase("mq_side_effect", "ロキソニンの副作用は？", MedicineQaRoute.MEDICINE_QA),
    EligibilityCase("mq_doping", "ドーピングに引っかかる？", MedicineQaRoute.MEDICINE_QA),
    EligibilityCase("mq_pregnancy", "妊娠中でも大丈夫？", MedicineQaRoute.MEDICINE_QA),
    EligibilityCase("mq_compare", "カロナールとロキソニンどっちがいい？", MedicineQaRoute.MEDICINE_QA),
    EligibilityCase("mq_casual", "風邪薬ある？", MedicineQaRoute.MEDICINE_QA),
    EligibilityCase("mq_otc_slang", "市販薬でなんとかならない？", MedicineQaRoute.MEDICINE_QA),
    EligibilityCase("mq_ingredient", "この成分、眠くなる？", MedicineQaRoute.MEDICINE_QA),
    EligibilityCase("mq_interaction", "他の薬と飲み合わせ大丈夫？", MedicineQaRoute.MEDICINE_QA),
    EligibilityCase("mq_child", "5歳の子供に飲ませていい？", MedicineQaRoute.MEDICINE_QA),
    EligibilityCase("mq_anaphora", "先ほどの1番の薬、眠くなる？", MedicineQaRoute.MEDICINE_QA,
                    recs=[{"product_name": "カロナール"}]),
    EligibilityCase("mq_history_followup", "それ、競技前でも平気？", MedicineQaRoute.MEDICINE_QA,
                    history=[
                        {"type": "user", "content": "頭痛がする"},
                        {"type": "bot", "content": "推奨", "diagnosis": {
                            "recommended_medicines": [{"product_name": "イブ"}]
                        }},
                    ]),
    EligibilityCase("mq_photo", "パッケージ見せて", MedicineQaRoute.MEDICINE_QA,
                    recs=[{"product_name": "ルルアタック"}]),
    EligibilityCase("mq_marathon", "マラソン前に飲んでいい風邪薬ある？", MedicineQaRoute.MEDICINE_QA),
    EligibilityCase("mq_throat_casual", "のどイガイガなんだけど市販薬でなんとかなる？", MedicineQaRoute.MEDICINE_QA),
    EligibilityCase("mq_drowsy_casual", "眠くならない薬教えて", MedicineQaRoute.MEDICINE_QA),
    EligibilityCase("mq_elderly", "80代でも飲める？", MedicineQaRoute.MEDICINE_QA),
    EligibilityCase("mq_casual_want", "風邪薬ほしいんだけど", MedicineQaRoute.MEDICINE_QA),
    EligibilityCase("mq_soft_ask", "これ飲んでも平気？", MedicineQaRoute.MEDICINE_QA,
                    recs=[{"product_name": "バファリン"}]),
    EligibilityCase("mq_dose_casual", "何錠飲めばいい？", MedicineQaRoute.MEDICINE_QA,
                    recs=[{"product_name": "イブ"}]),
    EligibilityCase("mq_alcohol", "お酒飲んだあとでも飲める？", MedicineQaRoute.MEDICINE_QA),
    EligibilityCase("mq_timing", "食前食後どっち？", MedicineQaRoute.MEDICINE_QA,
                    recs=[{"product_name": "ルル"}]),
    EligibilityCase("mq_generic", "市販薬のジェネリックとブランドの違い", MedicineQaRoute.MEDICINE_QA),
    EligibilityCase("mq_english_mix", "Ibuprofen 日本で買える？", MedicineQaRoute.MEDICINE_QA),
    EligibilityCase("mq_worry", "副作用怖いんだけど大丈夫？", MedicineQaRoute.MEDICINE_QA),
    EligibilityCase("mq_nursing", "授乳中でも使える？", MedicineQaRoute.MEDICINE_QA),
]

# --- Concierge（技術・メタ・オフトピック） ---
CONCIERGE_CASES = [
    EligibilityCase("cg_gitlab", "GitlabとGithubの違いは？", MedicineQaRoute.CONCIERGE, "architecture"),
    EligibilityCase("cg_deploy", "このサービスのデプロイ先は？", MedicineQaRoute.CONCIERGE, "architecture"),
    EligibilityCase("cg_stack", "技術スタック教えて", MedicineQaRoute.CONCIERGE, "architecture"),
    EligibilityCase("cg_weather", "今日の天気は？", MedicineQaRoute.CONCIERGE, "redirect"),
    EligibilityCase("cg_news", "今日のニュースは？", MedicineQaRoute.CONCIERGE, "redirect"),
    EligibilityCase("cg_math", "1+1は？", MedicineQaRoute.CONCIERGE, "redirect"),
    EligibilityCase("cg_capabilities", "何ができる？", MedicineQaRoute.CONCIERGE, "capabilities"),
    EligibilityCase("cg_app_about", "あなたは誰？", MedicineQaRoute.CONCIERGE, "app_about"),
    EligibilityCase("cg_privacy", "プライバシーポリシーは？", MedicineQaRoute.CONCIERGE, "doc_privacy"),
    EligibilityCase("cg_changelog", "最近何が変わった？", MedicineQaRoute.CONCIERGE, "doc_changelog"),
    EligibilityCase("cg_greeting", "こんにちは", MedicineQaRoute.CONCIERGE, "greeting"),
    EligibilityCase("cg_thanks", "ありがとう", MedicineQaRoute.CONCIERGE, "thanks"),
    EligibilityCase("cg_clinic_check", "ここは病院ですか？", MedicineQaRoute.CONCIERGE, "app_about"),
    EligibilityCase("cg_llm_chitchat", "暇つぶしに話しかけただけなんだけど、返事くれる？",
                    MedicineQaRoute.CONCIERGE, "chitchat", use_llm_mock="chitchat"),
    EligibilityCase("cg_llm_pokemon", "ポケモンの最新アップデート教えて",
                    MedicineQaRoute.DEFER, use_llm_mock=None),
    EligibilityCase("cg_casual_tech", "このチャットGPT使ってる？", MedicineQaRoute.CONCIERGE, "architecture"),
    EligibilityCase("cg_operator", "運営者に連絡したい", MedicineQaRoute.CONCIERGE, "doc_operator"),
    EligibilityCase("cg_terms", "利用規約見たい", MedicineQaRoute.CONCIERGE, "doc_terms"),
    EligibilityCase("cg_casual_who", "このボット誰が作ったの？", MedicineQaRoute.CONCIERGE, "app_about"),
    EligibilityCase("cg_repo", "GitHubのURL教えて", MedicineQaRoute.CONCIERGE, "architecture"),
    EligibilityCase("cg_data_store", "会話内容どこに保存されてる？", MedicineQaRoute.CONCIERGE, "architecture"),
    EligibilityCase("cg_recipe", "カレーの作り方教えて", MedicineQaRoute.CONCIERGE, "redirect"),
    EligibilityCase("cg_stock", "今日の株価は？", MedicineQaRoute.CONCIERGE, "redirect"),
    EligibilityCase("cg_movie", "おすすめ映画ある？", MedicineQaRoute.CONCIERGE, "redirect"),
    EligibilityCase("cg_chitchat_probe", "暇だから話相手になって", MedicineQaRoute.CONCIERGE, "chitchat"),
    EligibilityCase("cg_lonely", "寂しいから誰か話聞いて", MedicineQaRoute.CONCIERGE, "chitchat"),
    EligibilityCase("cg_how_works", "このチャットどうやって動いてる？", MedicineQaRoute.CONCIERGE, "architecture"),
    EligibilityCase("cg_otc_meaning", "OTCって何？", MedicineQaRoute.CONCIERGE, "capabilities"),
    EligibilityCase("cg_session_delete", "会話履歴消して", MedicineQaRoute.CONCIERGE, "session_ops"),
]

# --- Physical（症状・口語） ---
PHYSICAL_CASES = [
    EligibilityCase("ph_headache", "頭痛がする", MedicineQaRoute.PHYSICAL),
    EligibilityCase("ph_casual", "のど痛い", MedicineQaRoute.PHYSICAL),
    EligibilityCase("ph_dialect", "しんどい", MedicineQaRoute.PHYSICAL),
    EligibilityCase("ph_fever", "熱ある", MedicineQaRoute.PHYSICAL),
    EligibilityCase("ph_dialect2", "めっちゃ頭痛い", MedicineQaRoute.PHYSICAL),
    EligibilityCase("ph_stomach", "お腹ぐるぐる", MedicineQaRoute.PHYSICAL),
    EligibilityCase("ph_vague", "なんか調子悪い", MedicineQaRoute.PHYSICAL),
    EligibilityCase("ph_cough", "咳が止まらない", MedicineQaRoute.PHYSICAL),
    EligibilityCase("ph_nausea", "気持ち悪い", MedicineQaRoute.PHYSICAL),
    EligibilityCase("ph_runny", "鼻水が止まらん", MedicineQaRoute.PHYSICAL),
    EligibilityCase("ph_chill", "寒気がする", MedicineQaRoute.PHYSICAL),
]

# --- DEFER（質問形式でない短文・相槌は Concierge 挨拶へ） ---
DEFER_CASES = [
    EligibilityCase("df_ack", "うん", MedicineQaRoute.CONCIERGE, "greeting"),
    EligibilityCase("df_ok", "了解", MedicineQaRoute.CONCIERGE, "greeting"),
    EligibilityCase("df_hai", "はい", MedicineQaRoute.CONCIERGE, "greeting"),
    EligibilityCase("df_thx_short", "サンキュー", MedicineQaRoute.CONCIERGE, "thanks"),
]

ALL_CASES = MEDICINE_QA_CASES + CONCIERGE_CASES + PHYSICAL_CASES + DEFER_CASES


@pytest.mark.parametrize("case", ALL_CASES, ids=lambda c: c.id)
def test_eligibility_matrix(case: EligibilityCase):
    if case.use_llm_mock is not None or case.id == "cg_llm_pokemon":
        with patch(
            "src.services.medicine_qa_eligibility.is_medicine_qa_eligibility_llm_enabled",
            return_value=True,
        ), patch(
            "src.services.medicine_qa_eligibility._llm_resolve_concierge_intent",
            return_value=case.use_llm_mock,
        ):
            decision = resolve_medicine_qa_route(
                case.text,
                triage_result=case.triage,
                conversation_history=case.history,
                recommended_medicines=case.recs,
                client=MagicMock(),
            )
    else:
        decision = resolve_medicine_qa_route(
            case.text,
            triage_result=case.triage,
            conversation_history=case.history,
            recommended_medicines=case.recs,
            client=None,
        )

    assert decision.route == case.expected_route, (
        f"[{case.id}] text={case.text!r} got route={decision.route.value} "
        f"source={decision.source} intent={decision.concierge_intent}"
    )
    if case.expected_intent is not None:
        assert decision.concierge_intent == case.expected_intent, (
            f"[{case.id}] expected intent={case.expected_intent}, got {decision.concierge_intent}"
        )


def test_context_followup_after_architecture():
    """直前が architecture 説明のとき「もっと詳しく」は Concierge 継続。"""
    history = [
        {"type": "user", "content": "技術スタック教えて"},
        {"type": "bot", "content": "AWSとGCP...", "concierge_intent": "architecture"},
    ]
    decision = resolve_medicine_qa_route(
        "もっと詳しく",
        conversation_history=history,
        client=None,
    )
    # follow-up は resolve_concierge_intent 側だが、ゲートでは redirect でも Concierge へ
    assert decision.route == MedicineQaRoute.CONCIERGE


def test_triage_concierge_intent_respected():
    decision = resolve_medicine_qa_route(
        "なんか教えて",
        triage_result={"category": "Ask", "concierge_intent": "redirect"},
        client=None,
    )
    assert decision.route == MedicineQaRoute.CONCIERGE
    assert decision.concierge_intent == "redirect"
