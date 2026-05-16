"""processing_status detail_code / detail_label"""
from __future__ import annotations

from src.services.processing_status import (
    clear_processing_status,
    get_processing_status,
    mark_processing_step,
    set_processing_language,
)


def test_mark_processing_step_with_detail():
    sid = "test-proc-detail-1"
    clear_processing_status(sid)
    set_processing_language(sid, "ja")
    mark_processing_step(sid, "emergency", detail_code="medical_self")
    st = get_processing_status(sid)
    assert st["active"] is True
    assert st["step_id"] == "emergency"
    assert st.get("detail_code") == "medical_self"
    assert "医療緊急" in (st.get("detail_label") or "")
    clear_processing_status(sid)


def test_symptom_analysis_detail_llm_classify():
    sid = "test-proc-detail-symptom"
    clear_processing_status(sid)
    from src.services.processing_status import set_processing_flow

    set_processing_flow(sid, "physical")
    mark_processing_step(sid, "symptom_analysis", detail_code="llm_classify")
    st = get_processing_status(sid)
    assert st["step_id"] == "symptom_analysis"
    assert st.get("detail_code") == "llm_classify"
    assert "市販薬" in (st.get("detail_label") or st.get("label") or "")
    assert "PhysicalOrchestrator" in (st.get("agent_display") or "")
    assert st.get("slow_hint")
    clear_processing_status(sid)


def test_safety_contra_check_has_agent_display():
    sid = "test-proc-detail-safety"
    clear_processing_status(sid)
    from src.services.processing_status import set_processing_flow

    set_processing_flow(sid, "physical")
    mark_processing_step(sid, "safety", detail_code="contra_check")
    st = get_processing_status(sid)
    assert st["step_id"] == "safety"
    assert "妊娠" in (st.get("label") or "")
    assert "SafetyGate" in (st.get("agent_display") or "")
    clear_processing_status(sid)
