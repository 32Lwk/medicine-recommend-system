"""dialogue history 解決テスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.dialogue.history import (
    resolve_concierge_history,
    resolve_conversation_history,
    resolve_counseling_history,
)


@patch("src.dialogue.history.is_chat_pipeline_v2_for_session", return_value=False)
def test_resolve_conversation_history_legacy(_v2):
    session = {"messages": [{"type": "user", "content": "a"}]}
    with patch("src.services.triage_history.get_recent_messages", return_value=[{"type": "user"}]) as mock:
        msgs = resolve_conversation_history(session, "web:U1")
    assert len(msgs) == 1
    mock.assert_called_once()


@patch("src.dialogue.history.is_chat_pipeline_v2_for_session", return_value=True)
@patch("src.dialogue.context_provider.build_context_bundle")
def test_resolve_conversation_history_v2(mock_bundle, _v2):
    mock_bundle.return_value = MagicMock(messages=[{"type": "user", "content": "x"}], memory_block="")
    session = {}
    msgs = resolve_conversation_history(session, "line:U1", agent_kind="physical", limit=1)
    assert msgs == [{"type": "user", "content": "x"}]
    mock_bundle.assert_called_once_with(session, "line:U1", agent_kind="physical")


@patch("src.dialogue.history.is_chat_pipeline_v2_for_session", return_value=True)
@patch("src.dialogue.context_provider.build_context_bundle")
def test_resolve_counseling_history_v2_includes_memory(mock_bundle, _v2):
    mock_bundle.return_value = MagicMock(
        messages=[{"type": "user", "content": "眠れない"}],
        memory_block="長期記憶",
    )
    msgs = resolve_counseling_history({}, "line:U1")
    assert msgs[0]["type"] == "system"
    assert msgs[1]["content"] == "眠れない"


@patch("src.dialogue.history.is_chat_pipeline_v2_for_session", return_value=True)
@patch("src.dialogue.context_provider.build_context_bundle")
def test_resolve_counseling_history_v2_limit(mock_bundle, _v2):
    mock_bundle.return_value = MagicMock(
        messages=[{"type": "user", "content": f"m{i}"} for i in range(5)],
        memory_block="",
    )
    msgs = resolve_counseling_history({}, "line:U1", limit=2)
    assert len(msgs) == 2
    assert msgs[-1]["content"] == "m4"


@patch("src.dialogue.history.is_chat_pipeline_v2_for_session", return_value=True)
@patch("src.dialogue.context_provider.build_context_bundle")
def test_resolve_physical_history_v2(mock_bundle, _v2):
    mock_bundle.return_value = MagicMock(
        messages=[{"type": "user", "content": "39度"}],
        memory_block="",
    )
    from src.dialogue.history import resolve_physical_history

    msgs = resolve_physical_history({}, "line:U1")
    assert msgs[0]["content"] == "39度"
    mock_bundle.assert_called_once_with({}, "line:U1", agent_kind="physical")


@patch("src.dialogue.history.is_chat_pipeline_v2_for_session", return_value=True)
@patch("src.dialogue.context_provider.build_context_bundle")
def test_resolve_physical_history_with_fallback_v2(mock_bundle, _v2):
    mock_bundle.return_value = MagicMock(
        messages=[{"type": "user", "content": "頭痛い"}],
        memory_block="",
    )
    from src.dialogue.history import resolve_physical_history_with_fallback

    msgs = resolve_physical_history_with_fallback({}, "line:U1")
    assert msgs[0]["content"] == "頭痛い"


@patch("src.dialogue.history.resolve_physical_history", side_effect=RuntimeError("boom"))
@patch("src.dialogue.history.resolve_conversation_history_with_fallback")
def test_resolve_physical_history_with_fallback_on_error(mock_conv_fb, _phys):
    mock_conv_fb.return_value = [{"type": "user", "content": "fallback"}]
    from src.dialogue.history import resolve_physical_history_with_fallback

    msgs = resolve_physical_history_with_fallback({}, "line:U1")
    assert msgs[0]["content"] == "fallback"
    mock_conv_fb.assert_called_once_with({}, "line:U1", agent_kind="physical", limit=None)


@patch("src.dialogue.history.is_chat_pipeline_v2_for_session", return_value=False)
@patch("src.services.line_memory_context.get_counseling_conversation_history")
def test_resolve_counseling_history_with_fallback_legacy(mock_legacy, _v2):
    mock_legacy.return_value = [{"type": "user", "content": "legacy"}]
    from src.dialogue.history import resolve_counseling_history_with_fallback

    msgs = resolve_counseling_history_with_fallback({}, "line:U1")
    assert msgs[0]["content"] == "legacy"


@patch("src.dialogue.history.is_chat_pipeline_v2_for_session", return_value=True)
@patch("src.dialogue.context_provider.build_context_bundle")
def test_resolve_concierge_history_v2(mock_bundle, _v2):
    mock_bundle.return_value = MagicMock(
        messages=[{"type": "user", "content": "技術スタックは？"}],
        memory_block="",
    )
    msgs = resolve_concierge_history({"messages": []}, "web:U1")
    assert msgs[0]["content"] == "技術スタックは？"


@patch("src.dialogue.history.is_chat_pipeline_v2_for_session", return_value=True)
@patch("src.dialogue.context_provider.build_context_bundle")
def test_resolve_emergency_history_with_fallback_v2(mock_bundle, _v2):
    mock_bundle.return_value = MagicMock(
        messages=[{"type": "user", "content": "胸が痛い"}],
        memory_block="",
    )
    from src.dialogue.history import resolve_emergency_history_with_fallback

    msgs = resolve_emergency_history_with_fallback({}, "line:U1")
    assert msgs[0]["content"] == "胸が痛い"
    mock_bundle.assert_called_once_with({}, "line:U1", agent_kind="emergency")
