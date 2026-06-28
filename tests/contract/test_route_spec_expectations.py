"""Contract tests: ROUTE_SPEC scenarios + expected_v2_diff (Wave 0)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


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


@pytest.fixture(scope="module")
def diff_doc() -> dict:
    return _load_yaml(FIXTURES / "expected_v2_diff.yaml")


def test_scenario_count_at_least_30(scenarios_doc: dict) -> None:
    scenarios = scenarios_doc.get("scenarios") or []
    assert len(scenarios) >= 30, f"expected >= 30 scenarios, got {len(scenarios)}"


def test_scenario_ids_unique(scenarios_doc: dict) -> None:
    ids = [s["id"] for s in scenarios_doc["scenarios"]]
    assert len(ids) == len(set(ids)), "duplicate scenario ids"


def test_scenario_groups_coverage(scenarios_doc: dict) -> None:
    ids = [s["id"] for s in scenarios_doc["scenarios"]]
    prefixes = {
        "line": sum(1 for i in ids if i.startswith("line-")),
        "web": sum(1 for i in ids if i.startswith("web-")),
        "handoff": sum(1 for i in ids if i.startswith("handoff-")),
        "emergency": sum(1 for i in ids if i.startswith("emergency-")),
        "session": sum(1 for i in ids if i.startswith("session-")),
        "corr": sum(1 for i in ids if i.startswith("corr-")),
    }
    assert prefixes["line"] >= 5
    assert prefixes["web"] >= 5
    assert prefixes["handoff"] >= 5
    assert prefixes["emergency"] >= 5
    assert prefixes["session"] + prefixes["corr"] >= 5


def test_each_scenario_has_required_fields(scenarios_doc: dict) -> None:
    for s in scenarios_doc["scenarios"]:
        assert "id" in s
        assert "channel" in s
        assert "input" in s
        assert "expect" in s
        assert s["channel"] in ("line", "web")


def test_diff_doc_has_changes(diff_doc: dict) -> None:
    changes = diff_doc.get("changes") or []
    assert len(changes) >= 10
    for c in changes:
        assert "id" in c
        assert "old_behavior" in c
        assert "new_behavior" in c
        assert "wave" in c


def test_diff_scenario_refs_exist(scenarios_doc: dict, diff_doc: dict) -> None:
    ids = {s["id"] for s in scenarios_doc["scenarios"]}
    for change in diff_doc.get("changes") or []:
        for sid in change.get("scenarios") or []:
            assert sid in ids, f"diff {change['id']} references unknown scenario {sid}"


def test_dialogue_schema_valid_json() -> None:
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "schemas"
        / "dialogue_context_v1.json"
    )
    data = json.loads(schema_path.read_text(encoding="utf-8"))
    assert data["title"] == "DialogueContext"
    assert data["properties"]["version"]["const"] == 1


def test_intent_router_schema_valid_json() -> None:
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "schemas"
        / "intent_router_v1.json"
    )
    data = json.loads(schema_path.read_text(encoding="utf-8"))
    assert data["title"] == "IntentRouterLLMOutput"
    assert "Physical" in data["properties"]["primary_route"]["enum"]


def test_chat_pipeline_v2_flag_default_off() -> None:
    from config.llm_flags import is_chat_pipeline_v2_enabled, is_chat_pipeline_v2_for_session

    assert is_chat_pipeline_v2_enabled() is False
    assert is_chat_pipeline_v2_for_session("line:U1") is False
