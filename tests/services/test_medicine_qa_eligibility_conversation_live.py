"""
medicine_qa_eligibility — 多ターン会話のライブ LLM 検証。

文脈・意図の継続が routing ゲートで維持されるかを確認する。
OPENAI_API_KEY 必須。CI では skip。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import pytest

from src.services.medicine_qa_eligibility import MedicineQaRoute, resolve_medicine_qa_route

pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY unset — live conversation tests skipped",
)


@dataclass(frozen=True)
class ConversationTurn:
    user: str
    expected_routes: frozenset[MedicineQaRoute]
    allowed_intents: frozenset[str] | None = None


@dataclass(frozen=True)
class ConversationCase:
    id: str
    turns: list[ConversationTurn]


def _run_conversation(
    case: ConversationCase,
    client: Any,
) -> list[tuple[ConversationTurn, Any]]:
    history: list[dict[str, Any]] = []
    results = []
    for turn in case.turns:
        decision = resolve_medicine_qa_route(
            turn.user,
            conversation_history=list(history),
            client=client,
        )
        results.append((turn, decision))
        history.append({"type": "user", "content": turn.user})
        history.append({"type": "bot", "content": "…"})
    return results


CONVERSATION_CASES = [
    ConversationCase(
        "conv_arch_then_followup",
        [
            ConversationTurn(
                "このサービスどこにデプロイしてる？",
                frozenset({MedicineQaRoute.CONCIERGE}),
                frozenset({"architecture", "redirect"}),
            ),
            ConversationTurn(
                "もうちょい詳しく",
                frozenset({MedicineQaRoute.CONCIERGE}),
                frozenset({"architecture"}),
            ),
        ],
    ),
    ConversationCase(
        "conv_reco_then_medicine_qa",
        [
            ConversationTurn(
                "頭痛がひどい",
                frozenset({MedicineQaRoute.PHYSICAL, MedicineQaRoute.MEDICINE_QA}),
            ),
            ConversationTurn(
                "2番目の薬、眠くなる？",
                frozenset({MedicineQaRoute.MEDICINE_QA}),
            ),
        ],
    ),
    ConversationCase(
        "conv_offtopic_then_clarify",
        [
            ConversationTurn(
                "今日の天気教えて",
                frozenset({MedicineQaRoute.CONCIERGE}),
                frozenset({"redirect", "chitchat"}),
            ),
            ConversationTurn(
                "じゃあ風邪薬で眠くならないやつある？",
                frozenset({MedicineQaRoute.MEDICINE_QA}),
            ),
        ],
    ),
    ConversationCase(
        "conv_chitchat_not_medicine_qa",
        [
            ConversationTurn(
                "暇だから話相手になって",
                frozenset({MedicineQaRoute.CONCIERGE}),
                frozenset({"chitchat", "redirect"}),
            ),
            ConversationTurn(
                "GitHubとGitLabの違いって何？",
                frozenset({MedicineQaRoute.CONCIERGE}),
                frozenset({"architecture", "redirect"}),
            ),
        ],
    ),
]


@pytest.fixture(scope="module")
def openai_client():
    from openai import OpenAI

    return OpenAI(api_key=os.environ["OPENAI_API_KEY"])


@pytest.mark.parametrize("case", CONVERSATION_CASES, ids=lambda c: c.id)
def test_live_conversation_routing(case: ConversationCase, openai_client):
    history: list[dict[str, Any]] = []
    recs: list[dict[str, Any]] | None = None

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
            assert decision.concierge_intent in turn.allowed_intents, (
                f"{case.id} turn {i}: intent {decision.concierge_intent}"
            )

        history.append({"type": "user", "content": turn.user})
        if i == 0 and turn.user == "頭痛がひどい":
            recs = [{"product_name": "A"}, {"product_name": "B"}]
            history.append({
                "type": "bot",
                "content": "推奨",
                "diagnosis": {"recommended_medicines": recs},
            })
        elif decision.concierge_intent == "architecture":
            history.append({
                "type": "bot",
                "content": "AWS/GCP…",
                "concierge_intent": "architecture",
            })
        else:
            history.append({"type": "bot", "content": "…"})
