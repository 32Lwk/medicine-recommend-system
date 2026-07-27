"""
多ターン会話フロー — ライブ LLM 検証（5〜7 ターン）。

カウンセリング→推奨→医薬品Q&A、技術→雑談→技術、境界質問など
文脈転換・意図継続を routing ゲートで検証する。
OPENAI_API_KEY 必須。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import pytest

from src.services.medicine_qa_eligibility import MedicineQaRoute, resolve_medicine_qa_route

pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY unset",
)


@dataclass
class FlowTurn:
    user: str
    expected_routes: frozenset[MedicineQaRoute]
    allowed_intents: frozenset[str] | None = None
    on_bot: Optional[Callable[[dict[str, Any], Any], None]] = None


@dataclass
class FlowCase:
    id: str
    turns: list[FlowTurn]
    initial_recs: list[dict[str, Any]] | None = None


def _append_bot(
    history: list[dict[str, Any]],
    recs: list[dict[str, Any]] | None,
    decision: Any,
    turn: FlowTurn,
) -> None:
    history.append({"type": "user", "content": turn.user})
    state: dict[str, Any] = {"history": history, "recs": recs, "decision": decision}
    if turn.on_bot:
        turn.on_bot(state, decision)
    elif decision.concierge_intent == "architecture":
        history.append({
            "type": "bot",
            "content": "AWS/GCP 構成…",
            "concierge_intent": "architecture",
        })
    elif recs and decision.route == MedicineQaRoute.MEDICINE_QA:
        history.append({
            "type": "bot",
            "content": "医薬品情報…",
            "diagnosis": {"recommended_medicines": recs},
        })
    elif decision.route == MedicineQaRoute.PHYSICAL:
        history.append({
            "type": "bot",
            "content": "推奨結果",
            "diagnosis": {
                "recommended_medicines": recs or [
                    {"product_name": "A"},
                    {"product_name": "B"},
                ]
            },
        })
    else:
        history.append({"type": "bot", "content": "…"})


FLOW_CASES: list[FlowCase] = [
    FlowCase(
        "flow_counseling_to_qa_5turn",
        [
            FlowTurn("のど痛くてつらい", frozenset({MedicineQaRoute.PHYSICAL})),
            FlowTurn("了解", frozenset({MedicineQaRoute.CONCIERGE})),
            FlowTurn("1番目の薬、ドーピング大丈夫？", frozenset({MedicineQaRoute.MEDICINE_QA})),
            FlowTurn("もっと詳しく", frozenset({MedicineQaRoute.MEDICINE_QA, MedicineQaRoute.CONCIERGE})),
            FlowTurn("ありがとう", frozenset({MedicineQaRoute.CONCIERGE})),
        ],
    ),
    FlowCase(
        "flow_tech_medicine_switch_6turn",
        [
            FlowTurn(
                "技術スタック教えて",
                frozenset({MedicineQaRoute.CONCIERGE}),
                frozenset({"architecture"}),
            ),
            FlowTurn(
                "もうちょい詳しく",
                frozenset({MedicineQaRoute.CONCIERGE}),
                frozenset({"architecture"}),
            ),
            FlowTurn(
                "話変わるけど、頭痛がする",
                frozenset({MedicineQaRoute.PHYSICAL}),
            ),
            FlowTurn(
                "2番目のやつ眠くなる？",
                frozenset({MedicineQaRoute.MEDICINE_QA}),
            ),
            FlowTurn(
                "GitHubは正本？",
                frozenset({MedicineQaRoute.CONCIERGE}),
                frozenset({"architecture", "redirect"}),
            ),
            FlowTurn("サンキュー", frozenset({MedicineQaRoute.CONCIERGE})),
        ],
    ),
    FlowCase(
        "flow_boundary_mixed_5turn",
        [
            FlowTurn(
                "のど痛いんだけど、このチャットGPT使ってる？",
                frozenset({MedicineQaRoute.PHYSICAL, MedicineQaRoute.CONCIERGE}),
            ),
            FlowTurn(
                "じゃあ薬の話に戻るけど、眠くならないのある？",
                frozenset({MedicineQaRoute.MEDICINE_QA, MedicineQaRoute.PHYSICAL}),
            ),
            FlowTurn(
                "データ保存先も気になる",
                frozenset({MedicineQaRoute.CONCIERGE}),
                frozenset({"architecture", "redirect"}),
            ),
            FlowTurn("うん", frozenset({MedicineQaRoute.CONCIERGE, MedicineQaRoute.DEFER})),
            FlowTurn(
                "市販薬相談したい、あとAWSとGCPの違いも",
                frozenset({MedicineQaRoute.MEDICINE_QA, MedicineQaRoute.CONCIERGE}),
            ),
        ],
    ),
    FlowCase(
        "flow_offtopic_recovery_6turn",
        [
            FlowTurn(
                "今日の天気は？",
                frozenset({MedicineQaRoute.CONCIERGE}),
                frozenset({"redirect", "chitchat"}),
            ),
            FlowTurn(
                "ごめん、薬の話。風邪っぽい",
                frozenset({MedicineQaRoute.PHYSICAL, MedicineQaRoute.MEDICINE_QA}),
            ),
            FlowTurn(
                "このアプリ誰が作った？",
                frozenset({MedicineQaRoute.CONCIERGE}),
                frozenset({"app_about", "architecture", "doc_operator"}),
            ),
            FlowTurn("了解", frozenset({MedicineQaRoute.CONCIERGE})),
            FlowTurn(
                "大会前に飲んでいい解熱剤ある？",
                frozenset({MedicineQaRoute.MEDICINE_QA, MedicineQaRoute.DEFER}),
            ),
            FlowTurn(
                "ルールベース推奨の仕組みも教えて",
                frozenset({MedicineQaRoute.CONCIERGE}),
                frozenset({"architecture"}),
            ),
        ],
    ),
    FlowCase(
        "flow_session_ops_interrupt_5turn",
        [
            FlowTurn("頭痛", frozenset({MedicineQaRoute.PHYSICAL})),
            FlowTurn(
                "会話履歴消して",
                frozenset({MedicineQaRoute.CONCIERGE}),
                frozenset({"session_ops", "redirect"}),
            ),
            FlowTurn("こんにちは", frozenset({MedicineQaRoute.CONCIERGE})),
            FlowTurn("のど痛い", frozenset({MedicineQaRoute.PHYSICAL})),
            FlowTurn(
                "最近何か変わった？",
                frozenset({MedicineQaRoute.CONCIERGE}),
                frozenset({"doc_changelog", "architecture", "capabilities"}),
            ),
        ],
    ),
    FlowCase(
        "flow_chitchat_to_technical_5turn",
        [
            FlowTurn(
                "暇だから話相手になって",
                frozenset({MedicineQaRoute.CONCIERGE}),
                frozenset({"chitchat", "redirect"}),
            ),
            FlowTurn(
                "このサービス何ができる？",
                frozenset({MedicineQaRoute.CONCIERGE}),
                frozenset({"capabilities", "redirect"}),
            ),
            FlowTurn(
                "Bedrock KB 動いてる？",
                frozenset({MedicineQaRoute.CONCIERGE}),
                frozenset({"architecture"}),
            ),
            FlowTurn(
                "競技前に飲む薬と、ルールベース推奨の仕組み",
                frozenset({MedicineQaRoute.MEDICINE_QA, MedicineQaRoute.CONCIERGE}),
            ),
            FlowTurn("お疲れ", frozenset({MedicineQaRoute.CONCIERGE, MedicineQaRoute.DEFER})),
        ],
    ),
]


@pytest.fixture(scope="module")
def openai_client():
    from openai import OpenAI

    return OpenAI(api_key=os.environ["OPENAI_API_KEY"])


@pytest.mark.parametrize("case", FLOW_CASES, ids=lambda c: c.id)
def test_live_conversation_flow(case: FlowCase, openai_client):
    history: list[dict[str, Any]] = []
    recs: list[dict[str, Any]] | None = case.initial_recs

    for i, turn in enumerate(case.turns):
        decision = resolve_medicine_qa_route(
            turn.user,
            conversation_history=list(history) if history else None,
            recommended_medicines=recs,
            client=openai_client,
        )
        assert decision.route in turn.expected_routes, (
            f"{case.id} turn {i}: {turn.user!r} → {decision.route.value} "
            f"(source={decision.source}, intent={decision.concierge_intent})"
        )
        if turn.allowed_intents and decision.concierge_intent:
            assert decision.concierge_intent in turn.allowed_intents

        _append_bot(history, recs, decision, turn)
        if decision.route == MedicineQaRoute.PHYSICAL:
            last = history[-1]
            diag = last.get("diagnosis") or {}
            recs = diag.get("recommended_medicines") or recs
