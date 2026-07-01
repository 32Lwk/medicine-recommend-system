"""Wave 1a pipeline hook テスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.dialogue.pipeline import try_session_ops_route


@patch("src.dialogue.pipeline.is_chat_pipeline_v2_for_session", return_value=False)
def test_hook_skipped_when_v2_off(_v2):
    session: dict = {"messages": []}
    assert (
        try_session_ops_route(session, "line:U1", "ステータス", MagicMock()) is None
    )


@patch("src.dialogue.pipeline.is_chat_pipeline_v2_for_session", return_value=True)
@patch("src.dialogue.pipeline.try_handle_session_ops")
def test_hook_delegates_when_v2_on(mock_ops, _v2):
    mock_ops.return_value = ({"status": "ok"}, 200)
    session: dict = {"messages": []}
    resp = try_session_ops_route(
        session,
        "line:U1",
        "ステータス",
        MagicMock(),
        phase="fast",
    )
    assert resp == ({"status": "ok"}, 200)
    mock_ops.assert_called_once()
