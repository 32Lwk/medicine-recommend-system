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


def test_gate_pharmacy_location():
    d = run_deterministic_gate("近くの薬局を教えて", {}, "web-1")
    assert d is not None
    assert d.primary_route == "Store"


def test_gate_store_procurement_intent():
    d = run_deterministic_gate("市販薬の購入先", {}, "web-1")
    assert d is not None
    assert d.primary_route == "Store"


def test_gate_drugstore_where_not_physical():
    d = run_deterministic_gate("ドラッグストアはどこ？", {}, "web-1")
    assert d is not None
    assert d.primary_route == "Store"
    assert d.primary_route != "Physical"


def test_gate_matsukiyo_locator():
    d = run_deterministic_gate("マツキヨは近くにありますか", {}, "web-1")
    assert d is not None
    assert d.primary_route == "Store"


def test_gate_medical_emergency_seizure():
    d = run_deterministic_gate("痙攣している", {}, "web-1")
    assert d is not None
    assert d.primary_route == "Emergency"


def test_gate_concierge_architecture_follow_up():
    session = {
        "messages": [
            {"type": "user", "content": "技術スタックは？"},
            {
                "type": "bot",
                "content": "architecture info",
                "concierge_intent": "architecture",
            },
        ],
        "concierge_state": {"last_intent": "architecture"},
    }
    d = run_deterministic_gate("もっと詳しく", session, "web-1")
    assert d is not None
    assert d.primary_route == "Concierge"
    assert d.sub_route == "architecture"


def test_gate_correction_physical():
    d = run_deterministic_gate("違う、熱がある", {}, "web-1")
    assert d is not None
    assert d.primary_route == "Physical"
