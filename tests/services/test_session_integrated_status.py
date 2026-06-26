"""統合ステータスカードのテスト。"""
from src.services.status_diagnosis_builder import build_session_integrated_status


def test_build_session_integrated_status_masks_pii():
    diag = build_session_integrated_status(
        session_snapshot={"messages": [{"type": "user"}], "session_active": True},
        profile={"age": 35, "gender": "女性", "allergies": ["花粉", "卵"]},
        summaries=[{"summary_text": "頭痛相談"}],
    )
    assert diag.kind == "session_integrated_status"
    section_text = " ".join(
        item for sec in (diag.sections or []) for item in (sec.items or [])
    )
    assert "35" not in section_text
    assert "花粉" not in section_text
    assert "登録あり" in section_text or "件登録" in section_text
