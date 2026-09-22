"""R7-C01 follow-up: crisis detector view reaches emergency path (D2 ON)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.dialogue.routing.turn_signal_snapshot import create_turn_signal_snapshot


def test_snapshot_exposes_detector_text_without_zw():
    snap = create_turn_signal_snapshot("死\u200bにたい、履歴を削除して", turn_id="c01")
    assert snap.signals.crisis_detected is True
    assert "\u200b" not in snap.detector_text
    assert "死にたい" in snap.detector_text


def test_d2_pipeline_dispatches_emergency_on_detector_text():
    """When D2 ON, ZW crisis must call emergency with detector_text, not only block pure."""
    snap = create_turn_signal_snapshot("死\u200bにたい、履歴を削除して", turn_id="c01b")
    assert snap.signals.crisis_detected is True

    with patch(
        "src.handlers.chat.chat_emergency_handler.handle_emergency_if_detected",
        return_value=({"status": "crisis"}, 200),
    ) as emergency:
        # Simulate the pipeline fragment after safety pre
        detect_text = snap.detector_text
        from src.handlers.chat.chat_emergency_handler import handle_emergency_if_detected

        resp = handle_emergency_if_detected(
            {},
            MagicMock(),
            "sid",
            detect_text,
            MagicMock(),
            {"category": "Emergency", "requires_immediate_action": True},
        )
        assert resp is not None
        emergency.assert_called()
        args = emergency.call_args[0]
        assert "\u200b" not in args[3]
        assert "死にたい" in args[3]
