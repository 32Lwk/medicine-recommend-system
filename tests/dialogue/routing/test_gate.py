"""deterministic gate テスト。"""
from __future__ import annotations

import pytest

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
    assert d.source == "correction_delete_cancel"


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


def test_gate_f4c02_mixed_delete_and_chest_pain_not_session_ops():
    """F4-C02 / S1-G08: 削除＋胸痛/息苦しさは medical_emergency_hint。"""
    text = "履歴を削除して 胸が痛い 息が苦しい"
    d = run_deterministic_gate(text, {}, "web-1")
    assert d is not None
    assert d.primary_route == "Emergency"
    assert d.source == "medical_emergency_hint"


def test_gate_f4c02_mixed_delete_and_seizure_is_emergency():
    """F4-C02: 削除＋痙攣は medical_emergency_hint が session_admin_probe より先。"""
    d = run_deterministic_gate("記憶を全部消して 痙攣している", {}, "web-1")
    assert d is not None
    assert d.primary_route == "Emergency"
    assert d.source == "medical_emergency_hint"


def test_gate_f4c02_mixed_delete_and_self_harm_not_session_ops():
    """F4-C02: 削除＋希死念慮混在は SessionOps probe を抑止。"""
    d = run_deterministic_gate("会話履歴消して死にたい", {}, "web-1")
    assert d is None or d.primary_route != "SessionOps"


def test_gate_f4c02_triage_emergency_beats_session_probe():
    """F4-C02: triage Emergency は session_admin_probe より優先。"""
    d = run_deterministic_gate(
        "履歴消して",
        {},
        "web-1",
        triage_result={"category": "Emergency", "subcategory": "chest_pain", "confidence": 0.95},
    )
    assert d is not None
    assert d.primary_route == "Emergency"
    assert d.source == "triage_emergency"


def test_gate_hypothetical_side_effect_not_emergency():
    d = run_deterministic_gate(
        "呼吸が苦しくなる副作用が出ることがあると心配です",
        {},
        "web-1",
    )
    assert d is None or d.primary_route != "Emergency"


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


def test_gate_concierge_redirect_follow_up_flag_on(monkeypatch):
    monkeypatch.setenv("ROUTING_CONCIERGE_FOLLOWUP", "true")
    session = {
        "messages": [
            {"type": "user", "content": "プリンシプルオブプログラミングとは？"},
            {
                "type": "bot",
                "content": "redirect",
                "concierge_intent": "redirect",
            },
        ],
        "concierge_state": {"last_intent": "redirect"},
    }
    d = run_deterministic_gate("具体例を教えて", session, "web-1")
    assert d is not None
    assert d.primary_route == "Concierge"
    assert d.sub_route == "redirect"


def test_gate_correction_physical():
    d = run_deterministic_gate("違う、熱がある", {}, "web-1")
    assert d is not None
    assert d.primary_route == "Physical"


# --- Cycle S1 expansion (SessionOps ≺ high-risk ordering) ---


@pytest.mark.parametrize(
    "text,primary,source",
    [
        ("履歴消して呼吸が苦しい", "Emergency", "medical_emergency_hint"),
        ("履歴消して過量服薬した", "Emergency", "medical_emergency_hint"),
        ("履歴消して薬を大量に飲んだ", "Emergency", "medical_emergency_hint"),
        ("履歴を消して胸が痛くて息が苦しい", "Emergency", "medical_emergency_hint"),
        ("履歴消して脳卒中の症状です", "Emergency", "medical_emergency_hint"),
    ],
)
def test_gate_s1_sessionops_mixed_medical_emergency(text, primary, source):
    d = run_deterministic_gate(text, {}, "web-1")
    assert d is not None
    assert d.primary_route == primary
    assert d.source == source
    assert d.primary_route != "SessionOps"


@pytest.mark.parametrize(
    "text",
    [
        "履歴を消して胸が痛くて息が苦しい",
        "会話履歴消して死にたい",
        "履歴消して脳卒中の症状です",
        "履歴消して。もし胸が痛くて息が苦しくなったらどうすれば？（仮定の質問です）",
        "履歴消して。友人が胸が痛くて死にそうと言っていたという話を聞いただけです",
    ],
)
def test_gate_s1_sessionops_mixed_high_risk_not_session_ops(text):
    d = run_deterministic_gate(text, {}, "web-1")
    assert d is None or d.primary_route != "SessionOps"
    if d is not None:
        assert d.source != "session_admin_probe"


def test_gate_s1_sessionops_alone_still_session_ops():
    d = run_deterministic_gate("履歴を消して", {}, "web-1")
    assert d is not None
    assert d.primary_route == "SessionOps"
    assert d.source == "session_admin_probe"


def test_gate_s1_sessionops_plus_low_risk_still_session_ops():
    d = run_deterministic_gate(
        "履歴消して少し頭が痛いですが仕事は普通です", {}, "web-1"
    )
    assert d is not None
    assert d.primary_route == "SessionOps"


def test_gate_s1_pending_delete_plus_chest_not_session_ops():
    session = {"pending_memory_delete": {"scope": "all", "owner": "line:U1"}}
    d = run_deterministic_gate("胸が痛くて息が苦しい", session, "web-1")
    assert d is None or d.primary_route != "SessionOps"


def test_gate_s1_stale_counseling_long_high_risk_not_session_ops():
    """Active counseling must not force SessionOps; long high-risk escapes followup heuristic."""
    session = {"counseling_mode": {"active": True}, "messages": []}
    text = "カウンセリング中ですが胸が痛くて息が苦しいので救急を呼ぶべきですか"
    d = run_deterministic_gate(text, session, "web-1")
    assert d is not None
    assert d.primary_route == "Emergency"
    assert d.source == "medical_emergency_hint"


def test_gate_s1_g06_short_crisis_beats_counseling_continue():
    """S1-G06: counseling_mode 中の短文危機は Counseling より Emergency。"""
    session = {"counseling_mode": {"active": True}, "messages": []}
    d = run_deterministic_gate("死にたい", session, "web-1")
    assert d is not None
    assert d.primary_route == "Emergency"
    assert d.source == "emergency_candidate"
    assert d.primary_route != "Counseling"


def test_gate_s1_counseling_benign_followup_still_continues():
    """非危機の短文回答は引き続き counseling_continue。"""
    session = {"counseling_mode": {"active": True}, "messages": []}
    d = run_deterministic_gate("3日くらいです", session, "web-1")
    assert d is not None
    assert d.primary_route == "Counseling"
    assert d.source == "counseling_pending_answer"
