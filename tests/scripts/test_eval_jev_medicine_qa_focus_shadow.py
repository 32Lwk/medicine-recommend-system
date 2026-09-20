"""Unit tests for medicine_qa_focus shadow scaffold (no network)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "eval_jev_medicine_qa_focus_shadow.py"
FIXTURE = ROOT / "tests" / "fixtures" / "jev_medicine_qa_focus_pilot.yaml"


def _load_mod():
    spec = importlib.util.spec_from_file_location("eval_jev_medicine_qa_focus_shadow", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_validate_fixture_schema_smoke() -> None:
    mod = _load_mod()
    raw = yaml.safe_load(FIXTURE.read_text(encoding="utf-8")) or {}
    issues = mod.validate_fixture_schema(raw)
    assert issues == []


def test_soft_compare_focus_overlap() -> None:
    mod = _load_mod()
    expect = {
        "primary_focus": "comparison",
        "accept_focuses": ["comparison"],
        "physical_symptom_pivot": False,
        "label_status": "draft",
    }
    ok = mod.soft_compare_focus(expect, ["comparison", "general"])
    assert ok["soft_pass"] is True
    assert ok["primary_hit"] is True
    assert ok["eligibility_in_scope"] is False

    miss = mod.soft_compare_focus(expect, ["side_effect"])
    assert miss["soft_pass"] is False


def test_rule_baseline_offline_and_main_dry_run(tmp_path: Path) -> None:
    mod = _load_mod()
    raw = yaml.safe_load(FIXTURE.read_text(encoding="utf-8")) or {}
    scenarios = raw.get("scenarios") or []
    assert len(scenarios) >= 5

    comparison = next(s for s in scenarios if s.get("tag") == "comparison")
    baseline = mod.run_current_focus_baseline(comparison)
    assert baseline["eligibility_called"] is False
    assert "comparison" in baseline["focuses"] or baseline["accept_overlap"]

    out_json = tmp_path / "focus_shadow.json"
    out_md = tmp_path / "focus_shadow.md"
    rc = mod.main(
        [
            "--dry-run",
            "--fixture",
            str(FIXTURE),
            "--output-json",
            str(out_json),
            "--output-md",
            str(out_md),
        ]
    )
    assert rc == 0
    assert out_json.is_file()
    assert out_md.is_file()
    import json

    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["mode"] == "dry_run_schema_only"
    assert payload["eligibility_in_scope"] is False
    assert payload["schema_issues"] == []
