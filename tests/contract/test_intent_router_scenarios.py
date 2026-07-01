"""Contract tests: route_spec scenarios vs IntentRouter resolve_route (Wave 1b)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

SUB_ROUTE_ALIASES: dict[str, str] = {
    "status": "status_card",
    "delete": "delete_confirm",
}

ROUTER_CONTRACT_SKIP: frozenset[str] = frozenset(
    {
        # Wave 2 / 観測のみ — dispatch 契約対象外
        "line-counseling-followup",
        "web-architecture-followup",
        # 複雑な handoff セットアップ（Wave 2）
        "handoff-web-continue",
        "handoff-line-status-after-web",
        "handoff-episode-persist",
        # triage / concierge 曖昧（manual_queue vs escalate）
        "emergency-manual-queue",
        # pending 補正フロー — corr-recommend-rerun は scenario 未定義
    }
)


def _load_yaml(path: Path) -> dict:
    try:
        import yaml  # type: ignore
    except ImportError:
        pytest.skip("PyYAML required: pip install PyYAML")
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def scenarios_doc() -> dict:
    return _load_yaml(FIXTURES / "route_spec_scenarios.yaml")


def _collect_scenario_ids(scenarios_doc: dict) -> list[str]:
    return [s["id"] for s in scenarios_doc["scenarios"] if s["id"] not in ROUTER_CONTRACT_SKIP]


def _all_router_scenario_ids() -> list[str]:
    return _collect_scenario_ids(_load_yaml(FIXTURES / "route_spec_scenarios.yaml"))


def _find_scenario(scenarios_doc: dict, scenario_id: str) -> dict:
    for s in scenarios_doc["scenarios"]:
        if s["id"] == scenario_id:
            return s
    raise KeyError(scenario_id)


def _sid_for(scenario: dict) -> str:
    prefix = scenario.get("sid_prefix") or ""
    channel = scenario.get("channel", "line")
    if prefix:
        return f"{prefix}U-contract"
    return f"{channel}:U-contract"


def _build_session(scenario: dict) -> dict[str, Any]:
    setup = scenario.get("setup") or []
    session: dict[str, Any] = {"messages": []}
    for step in setup:
        text = str(step)
        session["messages"].append({"type": "user", "content": text})
        if any(k in text for k in ("39度", "38.5", "熱")):
            session["_fever_context_active"] = True
        if any(k in text for k in ("消して", "消す", "記憶を消")):
            session["pending_memory_delete"] = {"kind": "memory_delete_confirm"}
    return session


def _triage_stub(scenario: dict) -> dict[str, Any] | None:
    expect = scenario.get("expect") or {}
    primary = expect.get("primary_route")
    sub = expect.get("sub_route")

    if primary == "Emergency":
        return {
            "category": "Emergency",
            "subcategory": sub or "emergency_dispatch",
            "confidence": 0.95,
        }
    if primary == "Counseling":
        return {
            "category": "Emotional",
            "subcategory": sub or "emotional_support",
            "confidence": 0.85,
        }
    if primary == "Concierge" and sub:
        return {
            "category": "Other",
            "concierge_intent": sub,
            "confidence": 0.85,
        }
    return None


def _normalize_sub_route(sub: str | None) -> str | None:
    if sub is None:
        return None
    return SUB_ROUTE_ALIASES.get(sub, sub)


@pytest.mark.parametrize("scenario_id", _all_router_scenario_ids())
def test_resolve_route_matches_contract(scenario_id: str, scenarios_doc: dict) -> None:
    """route_spec の primary_route（+ sub_route エイリアス）が resolve_route と一致する。"""
    scenario = _find_scenario(scenarios_doc, scenario_id)
    session = _build_session(scenario)
    sid = _sid_for(scenario)
    triage = _triage_stub(scenario)

    from src.dialogue.routing.router import resolve_route

    decision = resolve_route(
        scenario["input"],
        session,
        sid,
        triage_result=triage,
    )

    expect = scenario["expect"]
    assert decision.primary_route == expect["primary_route"], (
        f"{scenario_id}: expected primary {expect['primary_route']}, "
        f"got {decision.primary_route} (sub={decision.sub_route}, by={decision.resolved_by})"
    )

    expected_sub = expect.get("sub_route")
    if expected_sub:
        assert _normalize_sub_route(decision.sub_route) == _normalize_sub_route(expected_sub), (
            f"{scenario_id}: expected sub {expected_sub}, got {decision.sub_route}"
        )

    must_not = expect.get("must_not") or []
    if "store" in must_not:
        assert decision.primary_route != "Store", f"{scenario_id}: store must be blocked"
