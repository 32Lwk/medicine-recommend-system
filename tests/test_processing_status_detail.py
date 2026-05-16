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
