"""Unit tests for eval_jev_intent_router_10 helpers (no network)."""
from __future__ import annotations

import importlib.util
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "eval_jev_intent_router_10.py"


def _load_mod():
    spec = importlib.util.spec_from_file_location("eval_jev_intent_router_10", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_summarize_excludes_connection_errors_from_accuracy() -> None:
    mod = _load_mod()
    results = [
        {
            "backend": "current",
            "pass": True,
            "latency_ms": 100.0,
            "outcome": "ok",
            "connection_error": False,
            "transport_ok": True,
            "scenario_id": "a",
            "latency_class": "cold",
            "run_idx": 0,
        },
        {
            "backend": "current",
            "pass": False,
            "error": "APIConnectionError",
            "outcome": "api_error",
            "connection_error": True,
            "transport_ok": False,
            "scenario_id": "b",
            "latency_class": "warm",
            "run_idx": 0,
        },
        {
            "backend": "current",
            "pass": False,
            "latency_ms": 200.0,
            "outcome": "ok",
            "connection_error": False,
            "transport_ok": True,
            "scenario_id": "c",
            "latency_class": "warm",
            "run_idx": 0,
        },
        {
            "backend": "current",
            "pass": False,
            "error": "ValueError",
            "outcome": "eval_error",
            "connection_error": False,
            "transport_ok": False,
            "scenario_id": "d",
            "latency_class": "warm",
            "run_idx": 0,
        },
        # Peer rows so paired_n can be computed for current↔jev:minimal
        {
            "backend": "jev:minimal",
            "pass": True,
            "latency_ms": 50.0,
            "outcome": "ok",
            "scenario_id": "a",
            "run_idx": 0,
            "latency_class": "cold",
        },
        {
            "backend": "jev:minimal",
            "pass": True,
            "latency_ms": 55.0,
            "outcome": "ok",
            "scenario_id": "c",
            "run_idx": 0,
            "latency_class": "warm",
        },
    ]
    summary = mod._summarize(results, "current")
    assert summary["attempted"] == 4
    assert summary["request_count"] == 4
    assert summary["scenario_count"] == 4
    assert summary["api_error"] == 1
    assert summary["eval_error"] == 1
    assert summary["connection_error"] == 1
    assert summary["scored"] == 2
    assert summary["passed"] == 1
    assert summary["accuracy_scored_pct"] == 50.0
    assert summary["accuracy_pct"] == 50.0
    # attempted denominator: 1 pass / 4 attempted
    assert summary["accuracy_attempted_pct"] == 25.0
    assert summary["paired_n"] == 2
    assert summary["latency_ms_stdev"] is not None
    # E-H1: cold n=1 < COLD_STATS_MIN_N → null stats + insufficient_n
    assert summary["latency_cold"]["n"] == 1
    assert summary["latency_cold"]["insufficient_n"] is True
    assert summary["latency_cold"]["latency_ms_p95"] is None
    assert summary["latency_warm"]["n"] == 1


def test_cold_stats_null_when_below_threshold() -> None:
    mod = _load_mod()
    stats = mod._latency_stats([100.0], min_n=mod.COLD_STATS_MIN_N)
    assert stats["n"] == 1
    assert stats["insufficient_n"] is True
    assert stats["latency_ms_p95"] is None
    assert stats["latency_ms_mean"] is None

    enough = mod._latency_stats([100.0 + i for i in range(5)], min_n=mod.COLD_STATS_MIN_N)
    assert enough["insufficient_n"] is False
    assert enough["latency_ms_p95"] is not None


def test_bootstrap_latency_ci_paired() -> None:
    mod = _load_mod()
    pairs = [(1000.0, 500.0), (1200.0, 520.0), (900.0, 480.0)]
    ci = mod._bootstrap_latency_diff_ci(pairs, n_boot=200)
    assert ci["available"] is True
    assert ci["mean_diff_ms"] > 0
    assert ci["ci95_low_ms"] <= ci["ci95_high_ms"]
    assert ci.get("level") == "request"


def test_scenario_cluster_bootstrap_ci() -> None:
    mod = _load_mod()
    results = []
    for sid, cur, jev in [
        ("s1", 1000.0, 400.0),
        ("s1", 1100.0, 420.0),
        ("s2", 900.0, 500.0),
        ("s2", 950.0, 510.0),
        ("s3", 800.0, 600.0),
        ("s3", 820.0, 610.0),
    ]:
        results.append(
            {
                "backend": "current",
                "scenario_id": sid,
                "run_idx": 0 if cur in (1000.0, 900.0, 800.0) else 1,
                "latency_ms": cur,
                "outcome": "ok",
            }
        )
        results.append(
            {
                "backend": "jev:minimal",
                "scenario_id": sid,
                "run_idx": 0 if jev in (400.0, 500.0, 600.0) else 1,
                "latency_ms": jev,
                "outcome": "ok",
            }
        )
    cluster = mod._bootstrap_scenario_cluster_latency_diff_ci(
        results, "current", "jev:minimal", n_boot=200
    )
    assert cluster["available"] is True
    assert cluster["level"] in ("scenario_cluster", "scenario_cluster_all")
    assert cluster["n_scenarios"] == 3
    assert cluster["mean_diff_ms"] > 0

    block = mod._build_latency_ci_block(results, n_boot=200)
    assert block["request_level"]["available"] is True
    assert block["scenario_cluster"]["available"] is True
    assert block["scenario_cluster_eligible_warm"]["available"] is True
    assert block["scenario_cluster_warm"]["available"] is True
    assert block["gate_canonical"] == "scenario_cluster_eligible_warm"
    assert "n_scenarios" in block["scenario_cluster_all"]
    assert "n_scenarios" in block["scenario_cluster_warm"]
    assert "n_scenarios" in block["scenario_cluster_cold"]
    assert "n_scenarios" in block["scenario_cluster_eligible_warm"]


def test_minimal_state_has_no_baseline_hint() -> None:
    mod = _load_mod()
    scenario = {"id": "x", "input": "頭痛", "setup": ["こんにちは"], "channel": "web"}
    state = mod._jev_state(
        scenario,
        mode="minimal",
        current_result={"triage_result": {"category": "Ask"}},
    )
    assert "recent_turns" in state
    assert "recent_context" in state
    assert state["recent_turns"] is state["recent_context"]
    assert "baseline_triage_hint" not in state


def test_disagreement_raw_required_even_when_alias_matches() -> None:
    """E-H4: raw sub mismatch must appear; normalized is a separate field."""
    mod = _load_mod()
    results = [
        {
            "backend": "current",
            "scenario_id": "jev-emergency-breathing",
            "run_idx": 0,
            "actual_primary": "Emergency",
            "actual_sub": "chest_pain_breathing_difficulty",
            "pass": True,
            "outcome": "ok",
        },
        {
            "backend": "jev:minimal",
            "scenario_id": "jev-emergency-breathing",
            "run_idx": 0,
            "actual_primary": "Emergency",
            "actual_sub": "emergency_dispatch",
            "pass": True,
            "outcome": "ok",
        },
    ]
    disag = mod._collect_disagreements(results)
    assert len(disag) == 1
    assert disag[0]["raw_sub_disagree"] is True
    assert disag[0]["normalized_sub_disagree"] is False
    assert disag[0]["alias_only_sub_diff"] is True
    assert "current_joint_raw" in disag[0]
    assert "current_joint_normalized" in disag[0]


def test_disagreement_joint_true_diff() -> None:
    mod = _load_mod()
    results = [
        {
            "backend": "current",
            "scenario_id": "a",
            "run_idx": 0,
            "actual_primary": "Physical",
            "actual_sub": "medicine_qa",
            "pass": True,
            "outcome": "ok",
        },
        {
            "backend": "jev:minimal",
            "scenario_id": "a",
            "run_idx": 0,
            "actual_primary": "Physical",
            "actual_sub": "rule_based_recommend",
            "pass": True,
            "outcome": "ok",
        },
    ]
    disag = mod._collect_disagreements(results)
    assert len(disag) == 1
    assert disag[0]["raw_sub_disagree"] is True
    assert disag[0]["raw_primary_disagree"] is False


def test_case_paired_sequential_is_current_first_not_true_interleave() -> None:
    mod = _load_mod()
    scenarios = [{"id": "a", "input": "x"}, {"id": "b", "input": "y"}]
    jobs = mod._build_eval_schedule(
        scenarios,
        run_current=True,
        jev_modes=["minimal"],
        repeat=2,
        order="case_paired_sequential",
        seed=42,
    )
    backends = [j["backend"] for j in jobs]
    assert backends[:4] == ["current", "jev:minimal", "current", "jev:minimal"]
    # Deprecated alias maps to the same schedule.
    aliased = mod._build_eval_schedule(
        scenarios,
        run_current=True,
        jev_modes=["minimal"],
        repeat=2,
        order="interleaved",
        seed=42,
    )
    assert [j["backend"] for j in aliased] == backends
    assert jobs[0]["order_mode"] == "case_paired_sequential"


def test_seed_random_per_case_backend_shuffle_deterministic() -> None:
    mod = _load_mod()
    scenarios = [{"id": f"s{i}", "input": str(i)} for i in range(5)]
    a = mod._build_eval_schedule(
        scenarios,
        run_current=True,
        jev_modes=["minimal"],
        repeat=1,
        order="seed_random",
        seed=7,
    )
    b = mod._build_eval_schedule(
        scenarios,
        run_current=True,
        jev_modes=["minimal"],
        repeat=1,
        order="seed_random",
        seed=7,
    )
    assert [(j["scenario_id"], j["backend"], j["run_idx"]) for j in a] == [
        (j["scenario_id"], j["backend"], j["run_idx"]) for j in b
    ]
    # Cases stay contiguous (per-case shuffle), not a global job shuffle.
    assert [j["scenario_id"] for j in a[:2]] == [a[0]["scenario_id"], a[0]["scenario_id"]]


def test_score_joint_matches_agent_b_alias_sub() -> None:
    """E-C1 drift case alias_sub: A must match B (True)."""
    from src.services.jev_decisions import score_joint_decision

    mod = _load_mod()
    expect = {
        "primary_route": "Emergency",
        "accept_sub_routes": ["emergency_dispatch"],
    }
    actual = {
        "primary_route": "Emergency",
        "sub_route": "chest_pain_breathing_difficulty",
    }
    b = score_joint_decision(expect, actual)
    a = mod._evaluate_prediction(expect, actual)
    assert b.joint_ok is True
    assert a["pass"] is True
    assert a["joint_ok"] is True
    assert a["pass"] == b.joint_ok
    assert a["normalized_sub"] == b.normalized_sub


def test_score_joint_matches_agent_b_forbidden_sub() -> None:
    """E-C1 drift case forbidden: A must match B (False)."""
    from src.services.jev_decisions import score_joint_decision

    mod = _load_mod()
    expect = {
        "primary_route": "Physical",
        "accept_sub_routes": ["none", "medicine_qa"],
        "forbidden_sub": ["rule_based_recommend", "fever_flow"],
    }
    actual = {"primary_route": "Physical", "sub_route": "rule_based_recommend"}
    b = score_joint_decision(expect, actual)
    a = mod._evaluate_prediction(expect, actual)
    assert b.joint_ok is False
    assert b.forbidden_hit is True
    assert a["pass"] is False
    assert a["forbidden_hit"] is True
    assert a["pass"] == b.joint_ok


def test_score_joint_matches_agent_b_safety_risk_flags_not_enough() -> None:
    """E-C2: risk_flags alone must NOT satisfy required_safety_action (B=False)."""
    from src.services.jev_decisions import score_joint_decision

    mod = _load_mod()
    expect = {
        "primary_route": "Physical",
        "accept_sub_routes": ["none", "medicine_qa"],
        "required_safety_action": "prescription_block",
    }
    actual = {
        "primary_route": "Physical",
        "sub_route": "medicine_qa",
        "meta": {"risk_flags": ["prescription_block"]},
    }
    b = score_joint_decision(expect, actual)
    a = mod._evaluate_prediction(expect, actual)
    assert b.joint_ok is False
    assert b.safety_ok is False
    assert a["pass"] is False
    assert a["required_safety_action_ok"] is False
    assert a["pass"] == b.joint_ok

    with_action = {
        "primary_route": "Physical",
        "sub_route": "medicine_qa",
        "safety_action": "prescription_block",
    }
    b2 = score_joint_decision(expect, with_action)
    a2 = mod._evaluate_prediction(expect, with_action)
    assert b2.joint_ok is True
    assert a2["pass"] is True
    assert a2["pass"] == b2.joint_ok


def test_score_joint_matches_agent_b_emergency_fp() -> None:
    """E-C1 drift case emergency_fp: A must match B (True)."""
    from src.services.jev_decisions import score_joint_decision

    mod = _load_mod()
    expect = {
        "primary_route": "Concierge",
        "accept_alternate_primaries": ["Emergency"],
        "accept_sub_routes": ["redirect", "chitchat", "none"],
        "scoring": {
            "emergency_fn_exempt": True,
            "emergency_fp_tolerated": True,
            "do_not_punish_emergency_keyword_hit": True,
        },
    }
    actual = {"primary_route": "Emergency", "sub_route": "emergency_dispatch"}
    b = score_joint_decision(expect, actual)
    a = mod._evaluate_prediction(expect, actual)
    assert b.joint_ok is True
    assert a["pass"] is True
    assert a["pass"] == b.joint_ok


def test_required_safety_undefined_matches_b() -> None:
    from src.services.jev_decisions import score_joint_decision

    mod = _load_mod()
    expect = {
        "primary_route": "Emergency",
        "accept_sub_routes": ["emergency_dispatch"],
    }
    actual = {"primary_route": "Emergency", "sub_route": "emergency_dispatch"}
    b = score_joint_decision(expect, actual)
    a = mod._evaluate_prediction(expect, actual)
    assert b.safety_scored is False
    assert a["required_safety_action_status"] == "undefined_not_scored"
    assert a["pass"] == b.joint_ok


def test_cost_labels_separated() -> None:
    mod = _load_mod()
    results = [
        {
            "backend": "current",
            "outcome": "ok",
            "openai_cost": {
                "openai_total_jpy": 1.0,
                "openai_intent_router_proxy_jpy": 0.5,
            },
        },
        {
            "backend": "jev:minimal",
            "outcome": "ok",
            "jev_cost": {"cost_usd": 0.001, "input_tokens": 100},
        },
    ]
    cost = mod._aggregate_cost(results)
    assert cost["current"]["cost_label"] == "measured_proxy"
    assert cost["jev"]["cost_label"] == "estimated"
    assert cost["comparison"]["openai_saved_cost_label"] == "measured_proxy"
    assert cost["comparison"]["jev_cost_label"] == "estimated"
    assert "estimated" in cost
    assert "measured_proxy" in cost


def _latency_pair_rows(
    *,
    sid: str,
    run_idx: int,
    cur_ms: float,
    jev_ms: float,
    latency_class: str,
    outcome: str = "ok",
    connection_error: bool = False,
    jev_eligible: bool = True,
) -> list[dict]:
    transport_ok = outcome == "ok" and not connection_error
    latency_gate_eligible = bool(
        jev_eligible and latency_class == "warm" and transport_ok
    )
    base = {
        "scenario_id": sid,
        "run_idx": run_idx,
        "latency_class": latency_class,
        "outcome": outcome,
        "connection_error": connection_error,
        "transport_ok": transport_ok,
        "jev_eligible": jev_eligible,
        "jev_eligibility_reason": (
            "intent_classification_candidate" if jev_eligible else "sessionops_fast_path"
        ),
        "jev_attempted": jev_eligible,
        "latency_gate_eligible": latency_gate_eligible,
        "accuracy_gate_eligible": jev_eligible,
        "safety_regression_eligible": True,
        "sessionops_fast_path_suppressed": False,
        "evaluation_contract_version": "jev-intent-gate-a-v2",
        "eligibility_contract_version": "jev-intent-eligibility-v1",
        "fallback": False,
    }
    rows = []
    if outcome == "ok" and not connection_error:
        rows.append({**base, "backend": "current", "latency_ms": cur_ms, "pass": True})
        rows.append(
            {
                **base,
                "backend": "jev:minimal",
                "latency_ms": jev_ms,
                "pass": True,
                "jev_api_calls": 1 if jev_eligible else 0,
            }
        )
    else:
        rows.append(
            {
                **base,
                "backend": "current",
                "latency_ms": None if outcome != "ok" else cur_ms,
                "pass": False,
                "error": "APIConnectionError" if connection_error else "ValueError",
                "latency_gate_eligible": False,
            }
        )
        rows.append(
            {
                **base,
                "backend": "jev:minimal",
                "latency_ms": None if outcome != "ok" else jev_ms,
                "pass": False,
                "error": "APIConnectionError" if connection_error else "ValueError",
                "latency_gate_eligible": False,
                "jev_api_calls": 1 if jev_eligible else 0,
            }
        )
    return rows


def test_cold_samples_never_enter_warm_ci() -> None:
    """Cold latencies must not appear in eligible_warm / warm sensitivity CI."""
    mod = _load_mod()
    results = []
    # Warm pairs: modest delta (~100ms)
    for i, sid in enumerate(["s1", "s2", "s3"]):
        results.extend(
            _latency_pair_rows(
                sid=sid, run_idx=0, cur_ms=500.0 + i, jev_ms=400.0 + i, latency_class="warm"
            )
        )
    # Cold pairs: huge delta that would dominate if mixed
    results.extend(
        _latency_pair_rows(
            sid="s1", run_idx=1, cur_ms=50_000.0, jev_ms=100.0, latency_class="cold"
        )
    )
    results.extend(
        _latency_pair_rows(
            sid="s2", run_idx=1, cur_ms=60_000.0, jev_ms=100.0, latency_class="cold"
        )
    )

    block = mod._build_latency_ci_block(results, n_boot=300, seed=42)
    gate = block["scenario_cluster_eligible_warm"]
    warm = block["scenario_cluster_warm"]
    all_c = block["scenario_cluster_all"]
    assert gate["available"] is True
    assert gate["n_scenarios"] == 3
    assert gate["population"] == "eligible_warm"
    assert gate["gate_use"] is True
    assert warm["gate_use"] is False
    # Warm mean delta ~100; all includes cold and is much larger
    assert gate["mean_diff_ms"] < 200.0
    assert all_c["mean_diff_ms"] > gate["mean_diff_ms"]
    assert block["gate_canonical"] == "scenario_cluster_eligible_warm"
    assert block["population"] == "eligible_warm"
    assert block["mean_diff_ms"] == gate["mean_diff_ms"]
    assert set(gate["scenario_ids"]) == {"s1", "s2", "s3"}
    warm_pairs = mod._pair_latencies(
        results,
        "current",
        "jev:minimal",
        latency_class="warm",
        require_latency_gate_eligible=True,
    )
    assert len(warm_pairs) == 3
    assert all(a < 1000 for a, _ in warm_pairs)


def test_warm_point_estimate_matches_scenario_cluster_mean() -> None:
    mod = _load_mod()
    results = []
    for sid, cur, jev in [
        ("s1", 1000.0, 400.0),
        ("s1", 1100.0, 420.0),
        ("s2", 900.0, 500.0),
        ("s2", 950.0, 510.0),
        ("s3", 800.0, 600.0),
        ("s3", 820.0, 610.0),
    ]:
        run_idx = 0 if cur in (1000.0, 900.0, 800.0) else 1
        results.extend(
            _latency_pair_rows(
                sid=sid,
                run_idx=run_idx,
                cur_ms=cur,
                jev_ms=jev,
                latency_class="warm",
            )
        )
    # Cold noise must not affect the match
    results.extend(
        _latency_pair_rows(
            sid="s1", run_idx=9, cur_ms=99999.0, jev_ms=1.0, latency_class="cold"
        )
    )

    diffs = mod._scenario_mean_latency_diffs(
        results, "current", "jev:minimal", latency_class="warm", require_latency_gate_eligible=True
    )
    point = statistics.mean([d for _, d in diffs])
    block = mod._build_latency_ci_block(results, n_boot=200, seed=7)
    gate = block["scenario_cluster_eligible_warm"]
    assert gate["available"] is True
    assert abs(point - gate["mean_diff_ms"]) < 0.011
    assert abs(point - block["warm_mean_delta_ms"]) < 0.011
    assert abs(block["warm_mean_delta_ms"] - block["mean_diff_ms"]) < 0.011


def test_backend_one_sided_missing_recorded() -> None:
    mod = _load_mod()
    results = [
        {
            "backend": "current",
            "scenario_id": "only_cur",
            "run_idx": 0,
            "latency_ms": 100.0,
            "latency_class": "warm",
            "outcome": "ok",
            "transport_ok": True,
        },
        # jev missing for only_cur
        {
            "backend": "current",
            "scenario_id": "paired",
            "run_idx": 0,
            "latency_ms": 200.0,
            "latency_class": "warm",
            "outcome": "ok",
            "transport_ok": True,
        },
        {
            "backend": "jev:minimal",
            "scenario_id": "paired",
            "run_idx": 0,
            "latency_ms": 150.0,
            "latency_class": "warm",
            "outcome": "ok",
            "transport_ok": True,
        },
        {
            "backend": "current",
            "scenario_id": "paired2",
            "run_idx": 0,
            "latency_ms": 210.0,
            "latency_class": "warm",
            "outcome": "ok",
            "transport_ok": True,
        },
        {
            "backend": "jev:minimal",
            "scenario_id": "paired2",
            "run_idx": 0,
            "latency_ms": 160.0,
            "latency_class": "warm",
            "outcome": "ok",
            "transport_ok": True,
        },
    ]
    exclusions: list[dict] = []
    diffs = mod._scenario_mean_latency_diffs(
        results,
        "current",
        "jev:minimal",
        latency_class="warm",
        exclusions_out=exclusions,
    )
    assert len(diffs) == 2
    one_sided = [e for e in exclusions if e["reason"] == "backend_one_sided_missing"]
    assert len(one_sided) >= 1
    assert any(e["scenario_id"] == "only_cur" for e in one_sided)

    block = mod._build_latency_ci_block(results, n_boot=100, seed=1)
    counts = block["exclusions"]["counts_by_reason"]["warm"]
    assert counts.get("backend_one_sided_missing", 0) >= 1


def test_bootstrap_seed_reproducibility() -> None:
    mod = _load_mod()
    results = []
    for sid in ["s1", "s2", "s3", "s4"]:
        results.extend(
            _latency_pair_rows(
                sid=sid, run_idx=0, cur_ms=1000.0, jev_ms=400.0, latency_class="warm"
            )
        )
    a = mod._build_latency_ci_block(results, n_boot=500, seed=123)
    b = mod._build_latency_ci_block(results, n_boot=500, seed=123)
    c = mod._build_latency_ci_block(results, n_boot=500, seed=456)
    assert (
        a["scenario_cluster_eligible_warm"]["ci95_low_ms"]
        == b["scenario_cluster_eligible_warm"]["ci95_low_ms"]
    )
    assert (
        a["scenario_cluster_eligible_warm"]["ci95_high_ms"]
        == b["scenario_cluster_eligible_warm"]["ci95_high_ms"]
    )
    assert a["mean_diff_ms"] == b["mean_diff_ms"]
    # Different seed may or may not change CI with tiny identical diffs; mean is stable.
    assert a["mean_diff_ms"] == c["mean_diff_ms"]


def test_api_and_eval_error_exclusion_recorded() -> None:
    mod = _load_mod()
    results = []
    for sid in ["s1", "s2", "s3"]:
        results.extend(
            _latency_pair_rows(
                sid=sid, run_idx=0, cur_ms=800.0, jev_ms=500.0, latency_class="warm"
            )
        )
    results.append(
        {
            "backend": "current",
            "scenario_id": "s_api",
            "run_idx": 0,
            "latency_class": "warm",
            "outcome": "api_error",
            "connection_error": True,
            "transport_ok": False,
            "error": "APIConnectionError",
            "pass": False,
        }
    )
    results.append(
        {
            "backend": "jev:minimal",
            "scenario_id": "s_api",
            "run_idx": 0,
            "latency_class": "warm",
            "outcome": "ok",
            "transport_ok": True,
            "latency_ms": 100.0,
            "pass": True,
        }
    )
    results.append(
        {
            "backend": "current",
            "scenario_id": "s_eval",
            "run_idx": 0,
            "latency_class": "warm",
            "outcome": "eval_error",
            "connection_error": False,
            "transport_ok": False,
            "error": "ValueError",
            "pass": False,
        }
    )
    results.append(
        {
            "backend": "jev:minimal",
            "scenario_id": "s_eval",
            "run_idx": 0,
            "latency_class": "warm",
            "outcome": "ok",
            "transport_ok": True,
            "latency_ms": 110.0,
            "pass": True,
        }
    )

    block = mod._build_latency_ci_block(results, n_boot=100, seed=1)
    warm_excl = block["exclusions"]["warm"]
    reasons = {e["reason"] for e in warm_excl}
    assert "api_error" in reasons
    assert "eval_error" in reasons
    counts = block["exclusions"]["counts_by_reason"]["warm"]
    assert counts.get("api_error", 0) >= 1
    assert counts.get("eval_error", 0) >= 1
    # Failed scenarios must not be in eligible_warm Gate scenario set
    assert "s_api" not in (block["scenario_cluster_eligible_warm"].get("scenario_ids") or [])
    assert "s_eval" not in (block["scenario_cluster_eligible_warm"].get("scenario_ids") or [])


def test_n_scenarios_recorded_for_each_cluster_block() -> None:
    mod = _load_mod()
    results = []
    for sid in ["s1", "s2", "s3"]:
        results.extend(
            _latency_pair_rows(
                sid=sid, run_idx=0, cur_ms=700.0, jev_ms=400.0, latency_class="warm"
            )
        )
    for sid in ["s1", "s2"]:
        results.extend(
            _latency_pair_rows(
                sid=sid, run_idx=1, cur_ms=2000.0, jev_ms=300.0, latency_class="cold"
            )
        )
    block = mod._build_latency_ci_block(results, n_boot=100, seed=1)
    assert "n_scenarios" in block["scenario_cluster_all"]
    assert "n_scenarios" in block["scenario_cluster_warm"]
    assert "n_scenarios" in block["scenario_cluster_cold"]
    assert block["scenario_cluster_warm"]["n_scenarios"] == 3
    assert block["scenario_cluster_cold"]["n_scenarios"] == 2
    assert block["scenario_cluster_all"]["n_scenarios"] == 3
    assert block["scenario_cluster_eligible_warm"]["n_scenarios"] == 3
    assert block["n_scenarios"] == block["scenario_cluster_eligible_warm"]["n_scenarios"]


def test_summarize_latency_all_alias() -> None:
    mod = _load_mod()
    results = [
        {
            "backend": "current",
            "pass": True,
            "latency_ms": 100.0,
            "outcome": "ok",
            "connection_error": False,
            "transport_ok": True,
            "scenario_id": "a",
            "latency_class": "cold",
            "run_idx": 0,
        },
        {
            "backend": "current",
            "pass": True,
            "latency_ms": 200.0,
            "outcome": "ok",
            "connection_error": False,
            "transport_ok": True,
            "scenario_id": "b",
            "latency_class": "warm",
            "run_idx": 0,
        },
        {
            "backend": "jev:minimal",
            "pass": True,
            "latency_ms": 50.0,
            "outcome": "ok",
            "scenario_id": "a",
            "run_idx": 0,
            "latency_class": "cold",
        },
        {
            "backend": "jev:minimal",
            "pass": True,
            "latency_ms": 55.0,
            "outcome": "ok",
            "scenario_id": "b",
            "run_idx": 0,
            "latency_class": "warm",
        },
    ]
    summary = mod._summarize(results, "current")
    assert summary["latency"]["n"] == summary["latency_all"]["n"] == 2
    assert summary["latency_warm"]["n"] == 1
    assert summary["latency_gate"]["n"] == 1
    assert summary["latency_all"]["latency_ms_mean"] == summary["latency"]["latency_ms_mean"]


def test_cold_pair_client_reset_helper() -> None:
    mod = _load_mod()
    class _Fake:
        def __init__(self):
            self.closed = 0

        def close(self):
            self.closed += 1

    fake = _Fake()
    # Same pair → no reset
    out, key = mod._maybe_reset_clients_for_cold_pair(
        latency_mode="cold",
        pair_key=("a", 0),
        last_pair_key=("a", 0),
        openai_client=fake,
        run_current=True,
    )
    assert out is fake
    assert fake.closed == 0
    # warm mode → no reset
    out2, _ = mod._maybe_reset_clients_for_cold_pair(
        latency_mode="warm",
        pair_key=("b", 0),
        last_pair_key=("a", 0),
        openai_client=fake,
        run_current=True,
    )
    assert out2 is fake
    assert fake.closed == 0


def test_session_ops_triage_fast_path_from_synthetic_dict() -> None:
    """AE5-H2: session_admin shortpath detectable from triage_result alone."""
    mod = _load_mod()
    triage = {
        "category": "Other",
        "confidence": 1.0,
        "subcategory": "session_admin",
        "session_intent": "delete",
        "concierge_intent": "session_ops",
        "concierge_intent_source": "session_keyword_probe",
        "reasoning": "session_admin keyword probe (delete)",
    }
    fast = mod._detect_triage_fast_path(triage)
    assert fast["is_session_ops_fast"] is True
    assert fast["triage_fast_path"]
    assert "session_admin" in str(fast["triage_fast_path"])

    path = mod._classify_current_path_kind(
        triage,
        {"primary_route": "SessionOps", "sub_route": "delete_confirm", "resolved_by": "gate", "source": "session_admin_probe"},
    )
    assert path["current_path_kind"] == "deterministic_session_ops"
    assert path["triage_fast_path"]


def test_session_ops_mixed_when_llm_route() -> None:
    mod = _load_mod()
    triage = {
        "subcategory": "session_admin",
        "session_intent": "status",
        "concierge_intent": "session_ops",
        "concierge_intent_source": "session_keyword_probe",
    }
    path = mod._classify_current_path_kind(
        triage,
        {"primary_route": "SessionOps", "resolved_by": "llm", "source": "intent_router_llm"},
    )
    assert path["current_path_kind"] == "mixed"


def test_other_triage_fast_path_keyword_probe() -> None:
    mod = _load_mod()
    triage = {
        "category": "Other",
        "subcategory": "general_other",
        "concierge_intent": "architecture",
        "concierge_intent_source": "keyword_probe",
        "reasoning": "stage1 skipped (keyword_probe)",
    }
    fast = mod._detect_triage_fast_path(triage)
    assert fast["is_session_ops_fast"] is False
    assert fast["is_other_triage_fast"] is True
    assert fast["triage_fast_path"]

    # AE5-M1 style: fast triage + LLM route → mixed
    mixed = mod._classify_current_path_kind(
        triage,
        {"primary_route": "Concierge", "resolved_by": "llm", "source": "intent_router_llm"},
    )
    assert mixed["current_path_kind"] == "mixed"

    det = mod._classify_current_path_kind(
        triage,
        {"primary_route": "Concierge", "resolved_by": "gate", "source": "keyword_probe"},
    )
    assert det["current_path_kind"] == "deterministic_other"


def test_llm_triage_and_route_when_no_fast_markers() -> None:
    mod = _load_mod()
    triage = {
        "category": "Ask",
        "subcategory": "headache",
        "confidence": 0.82,
        "reasoning": "stage1+stage2 llm",
    }
    fast = mod._detect_triage_fast_path(triage)
    assert fast["triage_fast_path"] is False
    path = mod._classify_current_path_kind(
        triage,
        {"primary_route": "Physical", "resolved_by": "llm", "source": "intent_router_llm"},
    )
    assert path["current_path_kind"] == "llm_triage_and_route"
    assert path["triage_fast_path"] is False


def test_path_kind_unknown_on_empty_triage() -> None:
    mod = _load_mod()
    path = mod._classify_current_path_kind(None, None)
    assert path["current_path_kind"] == "unknown"
    assert path["triage_fast_path"] is False


def test_summarize_counts_deterministic_session_ops_without_scenario_id_exclusion() -> None:
    """Counts visible; SessionOps out of Latency Gate via eligibility flags, not id."""
    mod = _load_mod()
    results = [
        {
            "backend": "current",
            "pass": True,
            "latency_ms": 13.5,
            "triage_latency_ms": 0.14,
            "route_latency_ms": 13.3,
            "outcome": "ok",
            "connection_error": False,
            "transport_ok": True,
            "scenario_id": "jev-session-delete",
            "latency_class": "warm",
            "run_idx": 0,
            "current_path_kind": "deterministic_session_ops",
            "triage_fast_path": "subcategory:session_admin+concierge_intent_source:session_keyword_probe",
            "jev_eligible": False,
            "jev_eligibility_reason": "sessionops_fast_path",
            "jev_attempted": False,
            "latency_gate_eligible": False,
            "accuracy_gate_eligible": False,
            "safety_regression_eligible": True,
            "sessionops_fast_path_suppressed": False,
        },
        {
            "backend": "current",
            "pass": True,
            "latency_ms": 900.0,
            "triage_latency_ms": 200.0,
            "route_latency_ms": 700.0,
            "outcome": "ok",
            "connection_error": False,
            "transport_ok": True,
            "scenario_id": "jev-physical",
            "latency_class": "warm",
            "run_idx": 0,
            "current_path_kind": "llm_triage_and_route",
            "triage_fast_path": False,
            "jev_eligible": True,
            "jev_eligibility_reason": "intent_classification_candidate",
            "jev_attempted": False,
            "latency_gate_eligible": True,
            "accuracy_gate_eligible": True,
            "safety_regression_eligible": True,
            "sessionops_fast_path_suppressed": False,
        },
        {
            "backend": "jev:minimal",
            "pass": True,
            "latency_ms": None,
            "outcome": "skipped_ineligible",
            "scenario_id": "jev-session-delete",
            "run_idx": 0,
            "latency_class": "warm",
            "transport_ok": True,
            "jev_eligible": False,
            "jev_eligibility_reason": "sessionops_fast_path",
            "jev_attempted": False,
            "jev_api_calls": 0,
            "latency_gate_eligible": False,
            "accuracy_gate_eligible": False,
            "safety_regression_eligible": True,
        },
        {
            "backend": "jev:minimal",
            "pass": True,
            "latency_ms": 240.0,
            "outcome": "ok",
            "scenario_id": "jev-physical",
            "run_idx": 0,
            "latency_class": "warm",
            "transport_ok": True,
            "jev_eligible": True,
            "jev_eligibility_reason": "intent_classification_candidate",
            "jev_attempted": True,
            "jev_api_calls": 1,
            "latency_gate_eligible": True,
            "accuracy_gate_eligible": True,
            "safety_regression_eligible": True,
        },
        # Need >=2 eligible scenarios for cluster CI — synthetic peer
        {
            "backend": "current",
            "pass": True,
            "latency_ms": 800.0,
            "outcome": "ok",
            "transport_ok": True,
            "scenario_id": "jev-physical-2",
            "latency_class": "warm",
            "run_idx": 0,
            "jev_eligible": True,
            "latency_gate_eligible": True,
            "accuracy_gate_eligible": True,
            "safety_regression_eligible": True,
            "current_path_kind": "llm_triage_and_route",
        },
        {
            "backend": "jev:minimal",
            "pass": True,
            "latency_ms": 250.0,
            "outcome": "ok",
            "transport_ok": True,
            "scenario_id": "jev-physical-2",
            "latency_class": "warm",
            "run_idx": 0,
            "jev_eligible": True,
            "jev_attempted": True,
            "latency_gate_eligible": True,
            "accuracy_gate_eligible": True,
            "safety_regression_eligible": True,
        },
    ]
    summary = mod._summarize(results, "current")
    assert summary["deterministic_session_ops_n"] == 1
    assert summary["current_path_kind_counts"]["deterministic_session_ops"] == 1
    assert summary["current_path_kind_counts"]["llm_triage_and_route"] == 2
    assert "eligibility" in summary["path_kind_note"].lower()

    block = mod._build_latency_ci_block(results, n_boot=100, seed=1)
    gate_ids = set(block["scenario_cluster_eligible_warm"].get("scenario_ids") or [])
    assert "jev-session-delete" not in gate_ids
    assert "jev-physical" in gate_ids
    assert "jev-physical-2" in gate_ids
    # Sensitivity warm may still see session-delete if it had paired latency;
    # skipped_ineligible has no latency so it is excluded from warm pairing too.
    assert block["gate_canonical"] == "scenario_cluster_eligible_warm"


def test_session_intent_alone_with_session_ops_marks_fast() -> None:
    mod = _load_mod()
    triage = {
        "subcategory": "session_admin",
        "session_intent": "summarize",
        "concierge_intent": "session_ops",
    }
    path = mod._classify_current_path_kind(triage, {"primary_route": "SessionOps", "resolved_by": "gate"})
    assert path["current_path_kind"] == "deterministic_session_ops"
    assert "session_intent:summarize" in str(path["triage_fast_path"])
# --- Option B (2026-09-22): shared eligibility / 3-track Gate ---


def test_sessionops_alone_ineligible_no_jev_attempt_in_harness_mock() -> None:
    """SessionOps alone → ineligible; placeholder path never calls evaluate_system_one."""
    mod = _load_mod()
    scenario = {"id": "sess-1", "input": "履歴を消して", "expect": {"primary_route": "SessionOps"}}
    decision = mod._eligibility_decision_for_scenario(scenario)
    assert decision.eligible is False
    assert decision.reason == "sessionops_fast_path"

    current = {
        "actual": {"primary_route": "SessionOps", "sub_route": "delete_confirm"},
        "actual_primary": "SessionOps",
        "actual_sub": "delete_confirm",
        "pass": True,
    }
    row = mod._evaluate_jev_ineligible_placeholder(
        scenario,
        mode="minimal",
        current_result=current,
        decision=decision,
        latency_class="warm",
    )
    assert row["jev_attempted"] is False
    assert row["jev_api_calls"] == 0
    assert row["latency_gate_eligible"] is False
    assert row["accuracy_gate_eligible"] is False
    assert row["safety_regression_eligible"] is True
    assert row["outcome"] == "skipped_ineligible"
    assert "answers" not in row


def test_eligible_physical_accuracy_latency_gates_when_warm() -> None:
    mod = _load_mod()
    scenario = {
        "id": "phys-1",
        "input": "頭痛がします。市販薬でおすすめはありますか？",
    }
    decision = mod._eligibility_decision_for_scenario(scenario)
    assert decision.eligible is True
    row = {
        "outcome": "ok",
        "transport_ok": True,
        "fallback": False,
        "latency_class": "warm",
    }
    mod._apply_eligibility_flags(row, decision, latency_class="warm", jev_attempted=True)
    assert row["accuracy_gate_eligible"] is True
    assert row["latency_gate_eligible"] is True
    assert row["jev_attempted"] is True
    assert row["evaluation_contract_version"] == "jev-intent-gate-a-v2"
    assert row["eligibility_contract_version"] == "jev-intent-eligibility-v1"


def test_cold_never_in_latency_gate() -> None:
    mod = _load_mod()
    decision = mod._eligibility_decision_for_scenario(
        {"input": "頭痛がします。市販薬でおすすめはありますか？"}
    )
    row = {"outcome": "ok", "transport_ok": True, "fallback": False}
    mod._apply_eligibility_flags(row, decision, latency_class="cold", jev_attempted=True)
    assert row["latency_gate_eligible"] is False
    assert row["accuracy_gate_eligible"] is True


def test_no_scenario_id_exclusion_helpers() -> None:
    """Eval harness must not hardcode scenario ids for Gate exclusion."""
    import inspect

    mod = _load_mod()
    src = inspect.getsource(mod)
    assert "EXCLUDED_SCENARIO" not in src
    assert "exclude_scenario_ids" not in src
    assert "SCENARIO_ID_DENYLIST" not in src
    assert "is_jev_intent_router_eligible" in src
    assert "gate_flags_for_row" in src


def test_track_aggregates_keys_present() -> None:
    mod = _load_mod()
    scenarios = [
        {"id": "a", "input": "履歴を消して"},
        {"id": "b", "input": "頭痛がします"},
    ]
    results = [
        {
            "scenario_id": "a",
            "backend": "current",
            "jev_eligible": False,
            "jev_eligibility_reason": "sessionops_fast_path",
            "jev_attempted": False,
            "jev_api_calls": 0,
            "latency_gate_eligible": False,
            "accuracy_gate_eligible": False,
            "safety_regression_eligible": True,
            "outcome": "ok",
        },
        {
            "scenario_id": "a",
            "backend": "jev:minimal",
            "jev_eligible": False,
            "jev_eligibility_reason": "sessionops_fast_path",
            "jev_attempted": False,
            "jev_api_calls": 0,
            "latency_gate_eligible": False,
            "accuracy_gate_eligible": False,
            "safety_regression_eligible": True,
            "outcome": "skipped_ineligible",
        },
        {
            "scenario_id": "b",
            "backend": "current",
            "jev_eligible": True,
            "jev_eligibility_reason": "intent_classification_candidate",
            "jev_attempted": False,
            "latency_gate_eligible": True,
            "accuracy_gate_eligible": True,
            "safety_regression_eligible": True,
            "outcome": "ok",
            "latency_class": "warm",
            "transport_ok": True,
        },
        {
            "scenario_id": "b",
            "backend": "jev:minimal",
            "jev_eligible": True,
            "jev_eligibility_reason": "intent_classification_candidate",
            "jev_attempted": True,
            "jev_api_calls": 1,
            "latency_gate_eligible": True,
            "accuracy_gate_eligible": True,
            "safety_regression_eligible": True,
            "outcome": "ok",
            "latency_class": "warm",
            "transport_ok": True,
        },
    ]
    agg = mod._build_track_aggregates(results, scenarios)
    for key in (
        "total_fixture_cases",
        "product_regression_n",
        "jev_eligible_n",
        "jev_ineligible_n",
        "accuracy_gate_n",
        "latency_gate_n",
        "excluded_by_reason",
        "unexpected_jev_call_count",
        "evaluation_contract_version",
        "eligibility_contract_version",
    ):
        assert key in agg
    assert agg["total_fixture_cases"] == 2
    assert agg["jev_eligible_n"] == 1
    assert agg["jev_ineligible_n"] == 1
    assert agg["excluded_by_reason"].get("sessionops_fast_path") == 1
    assert agg["unexpected_jev_call_count"] == 0
    assert agg["evaluation_contract_version"] == "jev-intent-gate-a-v2"


def test_unexpected_jev_call_count_increments() -> None:
    mod = _load_mod()
    scenarios = [{"id": "a"}]
    results = [
        {
            "scenario_id": "a",
            "backend": "jev:minimal",
            "jev_eligible": False,
            "jev_eligibility_reason": "sessionops_fast_path",
            "jev_attempted": True,
            "jev_api_calls": 1,
            "safety_regression_eligible": True,
            "latency_gate_eligible": False,
            "accuracy_gate_eligible": False,
        }
    ]
    agg = mod._build_track_aggregates(results, scenarios)
    assert agg["unexpected_jev_call_count"] == 1


def test_unexpected_jev_call_false_eligible_via_recompute() -> None:
    """AE6-H2(a): row says eligible but shared eligibility says SessionOps → unexpected."""
    mod = _load_mod()
    scenarios = [{"id": "sess", "input": "履歴を消して"}]
    results = [
        {
            "scenario_id": "sess",
            "backend": "jev:minimal",
            "jev_eligible": True,
            "jev_eligibility_reason": "intent_classification_candidate",
            "jev_attempted": True,
            "jev_api_calls": 1,
            "safety_regression_eligible": True,
            "latency_gate_eligible": True,
            "accuracy_gate_eligible": True,
        }
    ]
    agg = mod._build_track_aggregates(results, scenarios)
    assert agg["unexpected_jev_call_count"] == 1


def test_unexpected_jev_call_false_eligible_via_persisted_signals() -> None:
    """AE6-H2(a): Jev row with peer deterministic_signals catches signal-only drift."""
    mod = _load_mod()
    scenarios = [{"id": "benign", "input": "こんにちは"}]
    results = [
        {
            "scenario_id": "benign",
            "backend": "jev:minimal",
            "jev_eligible": True,
            "jev_eligibility_reason": "intent_classification_candidate",
            "jev_attempted": True,
            "jev_api_calls": 1,
            "deterministic_signals": {"emergency_detected": True},
            "safety_regression_eligible": True,
            "latency_gate_eligible": True,
            "accuracy_gate_eligible": True,
        }
    ]
    agg = mod._build_track_aggregates(results, scenarios)
    assert agg["unexpected_jev_call_count"] == 1


def test_ineligible_excluded_from_eligible_warm_gate_ci() -> None:
    mod = _load_mod()
    results = []
    for sid in ["s1", "s2", "s3"]:
        results.extend(
            _latency_pair_rows(
                sid=sid, run_idx=0, cur_ms=900.0, jev_ms=200.0, latency_class="warm"
            )
        )
    results.extend(
        _latency_pair_rows(
            sid="sess",
            run_idx=0,
            cur_ms=13.0,
            jev_ms=250.0,
            latency_class="warm",
            jev_eligible=False,
        )
    )
    block = mod._build_latency_ci_block(results, n_boot=100, seed=1)
    gate_ids = set(block["scenario_cluster_eligible_warm"].get("scenario_ids") or [])
    assert "sess" not in gate_ids
    assert gate_ids == {"s1", "s2", "s3"}
    sens_warm = set(block["scenario_cluster_warm"].get("scenario_ids") or [])
    assert "sess" in sens_warm
    assert "latency_sensitivity" in block
    assert block["latency_sensitivity"]["eligible_warm_only"]["gate_use"] is True
    assert block["gate_thresholds"]["warm_mean_delta_ms_min"] == 900.0


def test_ae6_c1_ineligible_placeholder_not_in_accuracy_gate_pct() -> None:
    """AE6-C1: current-copied ineligible rows must not inflate accuracy_gate_pct."""
    mod = _load_mod()
    results = [
        {
            "backend": "jev:minimal",
            "scenario_id": "elig",
            "outcome": "ok",
            "transport_ok": True,
            "pass": True,
            "latency_ms": 200.0,
            "latency_class": "warm",
            "jev_eligible": True,
            "accuracy_gate_eligible": True,
            "safety_regression_eligible": True,
            "sub_accuracy_exempt": False,
        },
        {
            "backend": "jev:minimal",
            "scenario_id": "sess",
            "outcome": "skipped_ineligible",
            "transport_ok": True,
            "pass": True,  # would inflate Gate if counted
            "latency_ms": None,
            "latency_class": "warm",
            "jev_eligible": False,
            "accuracy_gate_eligible": False,
            "safety_regression_eligible": True,
            "actual_from": "current_executed_route",
            "sub_accuracy_exempt": False,
        },
    ]
    summary = mod._summarize(results, "jev:minimal")
    assert summary["accuracy_gate_n"] == 1
    assert summary["accuracy_gate_passed"] == 1
    assert summary["accuracy_gate_pct"] == 100.0
    assert summary["ineligible_placeholder_n"] == 1
    # Product track may still include the placeholder copy.
    assert summary["product_regression_n"] == 2
    assert summary["product_regression_pct"] == 100.0


def test_ae6_h1_emergency_signal_makes_benign_text_ineligible() -> None:
    """AE6-H1: same text + emergency_detected → deterministic_high_risk.

    Text alone would be intent_classification_candidate; production
    schedule_jev_shadow passes deterministic_signals from triage/legacy.
    """
    mod = _load_mod()
    benign = "頭痛がします"
    text_only = mod._eligibility_decision_for_scenario({"input": benign})
    assert text_only.eligible is True
    assert text_only.reason == "intent_classification_candidate"

    signals = mod._deterministic_signals_from_current_result(
        {
            "triage_result": {},
            "actual": {
                "primary_route": "Emergency",
                "sub_route": "emergency_dispatch",
            },
        }
    )
    assert signals is not None
    assert signals.get("emergency_detected") is True
    assert signals.get("emergency_sub_route") == "emergency_dispatch"

    with_signal = mod._eligibility_decision_for_scenario(
        {"input": benign},
        current_result={
            "triage_result": {},
            "actual": {
                "primary_route": "Emergency",
                "sub_route": "emergency_dispatch",
            },
        },
    )
    assert with_signal.eligible is False
    assert with_signal.reason == "deterministic_high_risk"
    assert with_signal.deterministic_high_risk is True


def test_ae6_h1_mapper_security_and_medical_examination_keys() -> None:
    """Mapper mirrors router._deterministic_signals_from_context key set."""
    mod = _load_mod()
    sec = mod._deterministic_signals_from_current_result(
        {
            "triage_result": {},
            "actual": {"primary_route": "Security", "sub_route": "known_attack"},
        }
    )
    assert sec is not None
    assert sec.get("security_blocked") is True
    assert sec.get("security_sub_route") == "known_attack"

    med = mod._deterministic_signals_from_current_result(
        {
            "triage_result": {
                "category": "Emergency",
                "subcategory": "medical_examination_request",
            },
            "actual": {"primary_route": "Emergency", "sub_route": "medical_examination"},
        }
    )
    assert med is not None
    assert med.get("medical_examination") is True
    assert med.get("emergency_detected") is True

    # No current context → None (text-only path)
    assert mod._deterministic_signals_from_current_result(None) is None
    assert mod._deterministic_signals_from_current_result({}) is None


def test_r8_h2_membership_missing_excluded_from_accuracy_gate() -> None:
    """R8-H2: missing accuracy_gate_eligible → Hard Gate 非対象 (not fail-open True)."""
    mod = _load_mod()
    results = [
        {
            "backend": "jev:minimal",
            "scenario_id": "missing",
            "outcome": "ok",
            "transport_ok": True,
            "pass": True,
            "latency_ms": 100.0,
            "latency_class": "warm",
            "sub_accuracy_exempt": False,
        },
        {
            "backend": "jev:minimal",
            "scenario_id": "elig",
            "outcome": "ok",
            "transport_ok": True,
            "pass": True,
            "latency_ms": 120.0,
            "latency_class": "warm",
            "accuracy_gate_eligible": True,
            "sub_accuracy_exempt": False,
        },
        {
            "backend": "jev:minimal",
            "scenario_id": "inelig",
            "outcome": "ok",
            "transport_ok": True,
            "pass": True,
            "latency_ms": 130.0,
            "latency_class": "warm",
            "accuracy_gate_eligible": False,
            "sub_accuracy_exempt": False,
        },
    ]
    summary = mod._summarize(results, "jev:minimal")
    assert summary["accuracy_gate_n"] == 1
    assert summary["accuracy_gate_passed"] == 1
    assert summary["accuracy_gate_membership_unknown_n"] == 1
    assert summary["accuracy_gate_excluded_n"] >= 1


def test_r8_h2_explicit_eligible_true_and_false() -> None:
    mod = _load_mod()
    results = [
        {
            "backend": "jev:minimal",
            "scenario_id": "t",
            "outcome": "ok",
            "transport_ok": True,
            "pass": False,
            "latency_ms": 50.0,
            "latency_class": "warm",
            "accuracy_gate_eligible": True,
            "sub_accuracy_exempt": False,
        },
        {
            "backend": "jev:minimal",
            "scenario_id": "f",
            "outcome": "ok",
            "transport_ok": True,
            "pass": True,
            "latency_ms": 50.0,
            "latency_class": "warm",
            "accuracy_gate_eligible": False,
            "sub_accuracy_exempt": False,
        },
    ]
    summary = mod._summarize(results, "jev:minimal")
    assert summary["accuracy_gate_n"] == 1
    assert summary["accuracy_gate_passed"] == 0
