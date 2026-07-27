"""
GPT ユーザーシミュレーション — 多ターン会話（6〜8 ターン）。

OpenAI にユーザー役の follow-up を生成させ、routing ゲートが
文脈転換・意図を追跡できるか検証する。OPENAI_API_KEY 必須。
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

import pytest

from src.services.medicine_qa_eligibility import MedicineQaRoute, resolve_medicine_qa_route

pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY unset",
)

_MAX_TURNS = 6


@dataclass(frozen=True)
class PersonaScenario:
    id: str
    opening: str
    persona: str
    routing_expectations: tuple[tuple[int, frozenset[MedicineQaRoute]], ...]


PERSONA_SCENARIOS = [
    PersonaScenario(
        "gpt_athlete_cold",
        "陸上の大会が3日後なんだけど、のどが痛くてつらい",
        "20代の陸上競技者。競技とドーピング、眠くならない薬が気になる。"
        "口語・短文。時々技術の話に脱線する。",
        (
            (0, frozenset({MedicineQaRoute.PHYSICAL, MedicineQaRoute.MEDICINE_QA, MedicineQaRoute.DEFER})),
            (2, frozenset({MedicineQaRoute.MEDICINE_QA, MedicineQaRoute.PHYSICAL, MedicineQaRoute.CONCIERGE, MedicineQaRoute.DEFER})),
            (4, frozenset({MedicineQaRoute.MEDICINE_QA, MedicineQaRoute.CONCIERGE, MedicineQaRoute.DEFER, MedicineQaRoute.PHYSICAL})),
        ),
    ),
    PersonaScenario(
        "gpt_curious_tech",
        "このチャット、どうやって動いてるの？",
        "IT に興味のある一般ユーザー。技術質問の後、薬の話に切り替える。"
        "カジュアルな日本語。",
        (
            (0, frozenset({MedicineQaRoute.CONCIERGE})),
            (2, frozenset({MedicineQaRoute.CONCIERGE, MedicineQaRoute.DEFER, MedicineQaRoute.MEDICINE_QA, MedicineQaRoute.PHYSICAL})),
            (4, frozenset({MedicineQaRoute.MEDICINE_QA, MedicineQaRoute.PHYSICAL, MedicineQaRoute.CONCIERGE, MedicineQaRoute.DEFER})),
        ),
    ),
    PersonaScenario(
        "gpt_elderly_careful",
        "80代の母に風邪薬を考えてるんだけど",
        "高齢者の家族。丁寧語。副作用・飲み合わせ・病院の線引きを気にする。",
        (
            (0, frozenset({MedicineQaRoute.MEDICINE_QA, MedicineQaRoute.PHYSICAL, MedicineQaRoute.DEFER})),
            (3, frozenset({MedicineQaRoute.MEDICINE_QA, MedicineQaRoute.CONCIERGE, MedicineQaRoute.DEFER})),
        ),
    ),
]


@pytest.fixture(scope="module")
def openai_client():
    from openai import OpenAI

    return OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def _generate_user_utterance(
    client: Any,
    *,
    persona: str,
    history: list[dict[str, Any]],
    turn_index: int,
) -> str:
    transcript = []
    for msg in history[-8:]:
        role = "ユーザー" if msg.get("type") == "user" else "ボット"
        transcript.append(f"{role}: {msg.get('content', '')[:200]}")
    hist_block = "\n".join(transcript) or "(会話開始)"

    prompt = f"""あなたは市販薬相談チャットの「ユーザー役」です。
ペルソナ: {persona}

これまでの会話:
{hist_block}

ターン {turn_index + 1}/{_MAX_TURNS} として、自然な次のユーザー発話を1文だけ生成してください。
- 医薬品相談・症状・技術質問・雑談のいずれか（文脈に合わせる）
- 1〜80文字、日本語、口語可
- JSON のみ: {{"message": "..."}}"""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "JSON のみ返す。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=120,
    )
    raw = (resp.choices[0].message.content or "").strip()
    try:
        data = json.loads(raw)
        msg = str(data.get("message") or "").strip()
        if msg:
            return msg[:120]
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(0))
            return str(data.get("message") or raw)[:120]
        except json.JSONDecodeError:
            pass
    return raw[:120] or "うん、教えて"


def _simulate_bot_reply(
    history: list[dict[str, Any]],
    decision: Any,
    recs: list[dict[str, Any]] | None,
) -> list[dict[str, Any]] | None:
    if decision.route == MedicineQaRoute.PHYSICAL:
        new_recs = recs or [{"product_name": "A"}, {"product_name": "B"}]
        history.append({
            "type": "bot",
            "content": "症状に合わせて市販薬をご提案しました。",
            "diagnosis": {"recommended_medicines": new_recs},
        })
        return new_recs
    if decision.route == MedicineQaRoute.MEDICINE_QA:
        history.append({"type": "bot", "content": "医薬品の情報をお伝えします。"})
        return recs
    if decision.concierge_intent == "architecture":
        history.append({
            "type": "bot",
            "content": "本サービスは GCP/AWS のクロスクラウド構成です。",
            "concierge_intent": "architecture",
        })
        return recs
    history.append({"type": "bot", "content": "承知しました。"})
    return recs


@pytest.mark.parametrize("scenario", PERSONA_SCENARIOS, ids=lambda s: s.id)
def test_gpt_simulated_multi_turn_routing(scenario: PersonaScenario, openai_client):
    history: list[dict[str, Any]] = []
    recs: list[dict[str, Any]] | None = None
    routes_log: list[MedicineQaRoute] = []

    user_text = scenario.opening
    for turn in range(_MAX_TURNS):
        decision = resolve_medicine_qa_route(
            user_text,
            conversation_history=list(history) if history else None,
            recommended_medicines=recs,
            client=openai_client,
        )
        routes_log.append(decision.route)

        for expect_turn, allowed in scenario.routing_expectations:
            if turn == expect_turn:
                assert decision.route in allowed, (
                    f"{scenario.id} turn {turn}: {user_text!r} → {decision.route.value} "
                    f"not in {[r.value for r in allowed]}"
                )

        history.append({"type": "user", "content": user_text})
        recs = _simulate_bot_reply(history, decision, recs)

        if turn + 1 >= _MAX_TURNS:
            break
        user_text = _generate_user_utterance(
            openai_client,
            persona=scenario.persona,
            history=history,
            turn_index=turn + 1,
        )
        assert user_text and len(user_text) >= 2

    assert len(routes_log) == _MAX_TURNS
    assert MedicineQaRoute.DEFER not in routes_log or len(routes_log) > 2, (
        f"{scenario.id}: too many DEFER routes: {[r.value for r in routes_log]}"
    )
