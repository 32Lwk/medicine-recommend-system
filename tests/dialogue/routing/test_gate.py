"""deterministic gate テスト。"""
from __future__ import annotations

from src.dialogue.routing.gate import run_deterministic_gate


def test_gate_session_ops_status():
    d = run_deterministic_gate("ステータスを教えて", {}, "line:U1")
    assert d is not None
    assert d.primary_route == "SessionOps"
    assert d.sub_route == "status"


def test_gate_physical_headache():
    d = run_deterministic_gate("頭痛い", {}, "web-1")
    assert d is not None
    assert d.primary_route == "Physical"


def test_gate_fever():
    d = run_deterministic_gate("39度の熱があります", {}, "line:U1")
    assert d is not None
    assert d.primary_route == "Physical"
    assert d.sub_route == "fever_flow"


def test_gate_security_aggressive():
    d = run_deterministic_gate("しね", {}, "line:U1")
    assert d is not None
    assert d.primary_route == "Security"


def test_gate_concierge_greeting():
    d = run_deterministic_gate("こんにちは", {}, "web-1")
    assert d is not None
    assert d.primary_route == "Concierge"
    assert d.sub_route == "greeting"


def test_gate_pending_delete_headache_routes_physical():
    session = {"pending_memory_delete": {"scope": "all", "owner": "line:U1"}}
    d = run_deterministic_gate("頭痛い", session, "line:U1")
    assert d is not None
    assert d.primary_route == "Physical"
    assert d.sub_route == "rule_based_recommend"


def test_gate_pending_delete_status_still_session_ops():
    session = {"pending_memory_delete": {"scope": "all", "owner": "line:U1"}}
    d = run_deterministic_gate("ステータスを教えて", session, "line:U1")
    assert d is not None
    assert d.primary_route == "SessionOps"
    assert d.sub_route == "status"


def test_gate_pending_delete_cancel():
    session = {"pending_memory_delete": {"scope": "all", "owner": "line:U1"}}
    d = run_deterministic_gate("やっぱり消さない", session, "line:U1")
    assert d is not None
    assert d.primary_route == "SessionOps"
    assert d.sub_route == "pending_clear"
    assert d.source == "pending_delete_cancel"
