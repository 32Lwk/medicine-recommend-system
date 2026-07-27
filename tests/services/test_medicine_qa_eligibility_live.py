"""
medicine_qa_eligibility — ライブ LLM 検証（OPENAI_API_KEY 必須）。

コスト・レイテンシを抑えるため、曖昧入力のみ少数ケース。CI では skip。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional

import pytest

from src.services.medicine_qa_eligibility import MedicineQaRoute, resolve_medicine_qa_route

pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY unset — live LLM tests skipped",
)


@dataclass(frozen=True)
class LiveCase:
    id: str
    text: str
    expected_routes: frozenset[MedicineQaRoute]
    allowed_intents: frozenset[str] | None = None
    history: list[dict[str, Any]] | None = None


LIVE_AMBIGUOUS_CASES = [
    LiveCase(
        "live_offtopic_game",
        "ポケモンの最新アップデート教えて",
        frozenset({MedicineQaRoute.DEFER, MedicineQaRoute.CONCIERGE}),
        allowed_intents=frozenset({"redirect", "chitchat", None}),
    ),
    LiveCase(
        "live_app_creator",
        "このアプリ誰が作ったの？",
        frozenset({MedicineQaRoute.CONCIERGE}),
        allowed_intents=frozenset({"app_about", "doc_operator", "architecture"}),
    ),
    LiveCase(
        "live_medicine_ambiguous",
        "大会前なんだけど何か飲んどいていい？",
        frozenset({MedicineQaRoute.MEDICINE_QA, MedicineQaRoute.DEFER}),
    ),
    LiveCase(
        "live_chitchat",
        "暇だから話相手になって",
        frozenset({MedicineQaRoute.CONCIERGE}),
        allowed_intents=frozenset({"chitchat", "redirect"}),
    ),
    LiveCase(
        "live_changelog",
        "このチャット最近改良されたとこある？",
        frozenset({MedicineQaRoute.CONCIERGE}),
        allowed_intents=frozenset({"doc_changelog", "architecture", "capabilities"}),
    ),
    LiveCase(
        "live_casual_medicine",
        "なんか風邪っぽいんだけど、大会前に飲んでいい薬ある？",
        frozenset({MedicineQaRoute.MEDICINE_QA, MedicineQaRoute.DEFER}),
    ),
    LiveCase(
        "live_recipe_redirect",
        "カレーのレシピ教えて",
        frozenset({MedicineQaRoute.CONCIERGE, MedicineQaRoute.DEFER}),
        allowed_intents=frozenset({"redirect", "chitchat", None}),
    ),
    LiveCase(
        "live_lonely",
        "寂しいから誰か話聞いて",
        frozenset({MedicineQaRoute.CONCIERGE}),
        allowed_intents=frozenset({"chitchat", "redirect"}),
    ),
    LiveCase(
        "live_data_privacy",
        "会話内容どこに保存されてるの？",
        frozenset({MedicineQaRoute.CONCIERGE}),
        allowed_intents=frozenset({"architecture", "doc_privacy", "redirect"}),
    ),
]

LIVE_CONTEXT_CASES = [
    LiveCase(
        "live_arch_followup",
        "もうちょい詳しく",
        frozenset({MedicineQaRoute.CONCIERGE}),
        allowed_intents=frozenset({"architecture"}),
        history=[
            {"type": "user", "content": "技術構成教えて"},
            {"type": "bot", "content": "AWS/GCP...", "concierge_intent": "architecture"},
        ],
    ),
    LiveCase(
        "live_reco_followup",
        "2番目のやつ、眠くなる？",
        frozenset({MedicineQaRoute.MEDICINE_QA}),
        history=[
            {"type": "user", "content": "頭痛"},
            {
                "type": "bot",
                "content": "推奨",
                "diagnosis": {
                    "recommended_medicines": [
                        {"product_name": "A"},
                        {"product_name": "B"},
                    ]
                },
            },
        ],
    ),
]


@pytest.fixture(scope="module")
def openai_client():
    from openai import OpenAI

    return OpenAI(api_key=os.environ["OPENAI_API_KEY"])


@pytest.mark.parametrize("case", LIVE_AMBIGUOUS_CASES, ids=lambda c: c.id)
def test_live_llm_ambiguous_routing(case: LiveCase, openai_client):
    decision = resolve_medicine_qa_route(
        case.text,
        conversation_history=case.history,
        client=openai_client,
    )
    assert decision.route in case.expected_routes, (
        f"{case.id}: got {decision.route.value} source={decision.source} "
        f"intent={decision.concierge_intent}"
    )
    if case.allowed_intents is not None and decision.concierge_intent is not None:
        assert decision.concierge_intent in case.allowed_intents, (
            f"{case.id}: intent {decision.concierge_intent} not in {case.allowed_intents}"
        )
    if case.allowed_intents is not None and decision.concierge_intent is None:
        assert None in case.allowed_intents or MedicineQaRoute.DEFER in case.expected_routes


@pytest.mark.parametrize("case", LIVE_CONTEXT_CASES, ids=lambda c: c.id)
def test_live_llm_context_routing(case: LiveCase, openai_client):
    decision = resolve_medicine_qa_route(
        case.text,
        conversation_history=case.history,
        client=openai_client,
    )
    assert decision.route in case.expected_routes, (
        f"{case.id}: got {decision.route.value} intent={decision.concierge_intent}"
    )
    if case.allowed_intents and decision.concierge_intent:
        assert decision.concierge_intent in case.allowed_intents


def test_live_llm_meta_none_routes_medicine_not_redirect(openai_client):
    """meta_triage=none の曖昧医薬品相談が redirect 固定にならないこと。"""
    decision = resolve_medicine_qa_route(
        "競技会で使える解熱剤ってある？",
        client=openai_client,
    )
    assert decision.route in (MedicineQaRoute.MEDICINE_QA, MedicineQaRoute.DEFER)
    assert decision.concierge_intent != "redirect" or decision.route == MedicineQaRoute.DEFER
