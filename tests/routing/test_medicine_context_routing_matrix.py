"""競技・推奨文脈ルーティング — YAML マトリクス＋追加境界ケース。"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.dialogue.routing.gate import run_deterministic_gate
from src.dialogue.routing.guards import apply_post_route_guards
from src.dialogue.routing.types import RouteDecision
from src.services.medicine_context_routing import (
    is_ambiguous_medicine_context,
    is_post_reco_followup_reference,
    resolve_medicine_context_route_rule,
)

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "medicine_context_routing_cases.yaml"


def _load_routing_cases() -> list[dict]:
    data = yaml.safe_load(_FIXTURE.read_text(encoding="utf-8"))
    return list(data.get("routing_cases") or [])


def _session_for_profile(profile: str) -> dict:
    if profile == "empty":
        return {"messages": []}
    if profile == "with_reco":
        return {
            "messages": [
                {"type": "user", "content": "頭が痛いです"},
                {
                    "type": "bot",
                    "content": "sage_reco",
                    "diagnosis": {
                        "render": "sage_reco",
                        "symptoms": ["頭痛"],
                        "recommended_medicines": [
                            {
                                "product_name": "カロナールＡ",
                                "doping_prohibited": "禁止物質なし",
                            },
                            {
                                "product_name": "タイレノールＡ",
                                "doping_prohibited": "禁止物質なし",
                            },
                            {
                                "product_name": "トキワイブプロエースＡ",
                                "doping_prohibited": "禁止物質なし",
                            },
                        ],
                    },
                },
            ]
        }
    if profile == "with_reco_and_greeting":
        base = _session_for_profile("with_reco")
        base["messages"] = [
            {"type": "user", "content": "こんにちは"},
            {"type": "bot", "content": "こんにちは！"},
        ] + base["messages"]
        return base
    if profile == "with_qa_only":
        return {
            "messages": [
                {
                    "type": "bot",
                    "diagnosis": {
                        "render": "sage_qa",
                        "is_question": True,
                        "chat_response": {"answer": "テスト回答"},
                    },
                }
            ]
        }
    raise ValueError(f"unknown profile: {profile}")


@pytest.mark.parametrize(
    "case",
    _load_routing_cases(),
    ids=[c["id"] for c in _load_routing_cases()],
)
def test_routing_matrix_from_yaml(case: dict, monkeypatch):
    if case.get("requires_reco_cold_nlu_v2"):
        monkeypatch.setenv("RECO_COLD_NLU_V2", "true")
        monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    session = _session_for_profile(case["session_profile"])
    route = resolve_medicine_context_route_rule(session, "matrix-sid", case["message"])
    assert route == case["expected_route"], (
        f"case={case['id']} message={case['message']!r} got={route}"
    )


# --- 追加境界: is_post_reco_followup_reference ---
@pytest.mark.parametrize(
    "message,expected",
    [
        ("陸上競技大会の前に使えるのはどれ？", True),
        ("使えますか？", False),
        ("大会前に大丈夫？", True),
        ("ドーピングは？", True),
        ("先ほどの薬どれ？", True),
        ("3つ目の副作用は？", False),
        ("頭痛が痛い", False),
        ("", False),
    ],
    ids=[
        "track_which_one",
        "bare_usage",
        "race_ok",
        "doping_only",
        "saki_hodo_dore",
        "third_side_effect",
        "symptom_only",
        "empty",
    ],
)
def test_is_post_reco_followup_reference_matrix(message: str, expected: bool):
    assert is_post_reco_followup_reference(message) is expected


# --- gate: 推奨後競技は medicine_followup_qa ---
@pytest.mark.parametrize(
    "message",
    [
        "陸上競技大会の前に使えるのはどれ？",
        "マラソン前に飲めるのはどれ？",
        "試合で使える薬はどれですか？",
        "アンチドーピングで大丈夫なのは？",
    ],
)
def test_gate_post_reco_sports_followup(message: str):
    session = _session_for_profile("with_reco")
    decision = run_deterministic_gate(
        message, session, "gate-sid", triage_result={"category": "Ask"}
    )
    assert decision is not None
    assert decision.sub_route == "medicine_followup_qa"


# --- guard: LLM が Physical に振っても補正 ---
@pytest.mark.parametrize(
    "message",
    [
        "陸上競技大会の前に使えるのはどれ？",
        "レース前に使えるのはどっち？",
    ],
)
def test_guard_overrides_llm_physical(message: str):
    session = _session_for_profile("with_reco")
    decision = RouteDecision(
        primary_route="Physical",
        sub_route="rule_based_recommend",
        confidence=0.9,
        resolved_by="llm",
        source="intent_router_llm",
    )
    out = apply_post_route_guards(
        decision, message, session, triage_result={"category": "Ask", "confidence": 0.95}
    )
    assert out.sub_route == "medicine_followup_qa"


# --- 初回競技のみ → symptom_prompt gate ---
@pytest.mark.parametrize(
    "message",
    [
        "陸上競技前に使える薬は？",
        "大会前に飲める市販薬は？",
        "マラソンのレース前に使える薬を教えて",
    ],
)
def test_gate_cold_sports_symptom_prompt(message: str):
    session = _session_for_profile("empty")
    decision = run_deterministic_gate(
        message, session, None, triage_result={"category": "Ask"}
    )
    assert decision is not None
    assert decision.sub_route == "symptom_prompt_sports"


# --- 曖昧ケース（LLM 対象）---
@pytest.mark.parametrize(
    "message",
    [
        "あの3つについて教えて",
    ],
)
def test_ambiguous_eligible_with_reco(message: str):
    session = _session_for_profile("with_reco")
    assert resolve_medicine_context_route_rule(session, "sid", message) == "none"
    assert is_ambiguous_medicine_context(session, "sid", message)


# --- 非曖昧（ルール確定で LLM 不要）---
@pytest.mark.parametrize(
    "message",
    [
        "陸上競技大会の前に使えるのはどれ？",
        "陸上競技前に使える薬は？",
    ],
)
def test_not_ambiguous_when_rule_decides(message: str):
    session = _session_for_profile("with_reco")
    if "どれ" in message:
        assert is_ambiguous_medicine_context(session, "sid", message) is False
    else:
        session = _session_for_profile("empty")
        assert is_ambiguous_medicine_context(session, None, message) is False
