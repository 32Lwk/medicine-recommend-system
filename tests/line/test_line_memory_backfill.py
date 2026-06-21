"""line_memory_backfill のテスト。"""
from __future__ import annotations

from unittest.mock import patch

from src.services.line_memory_backfill import (
    _profile_has_data,
    collect_line_session_messages,
    run_line_memory_backfill,
    split_archive_into_episodes,
)


def test_split_archive_into_episodes_on_sage_reco():
    messages = [
        {"type": "user", "content": "頭痛"},
        {"type": "bot", "content": "sage_reco", "diagnosis": {"render": "sage_reco", "recommended_medicines": [{}]}},
        {"type": "user", "content": "咳"},
        {"type": "bot", "content": "ok"},
    ]
    episodes = split_archive_into_episodes(messages)
    assert len(episodes) == 2
    assert episodes[0][0]["content"] == "頭痛"


def test_split_archive_single_episode_without_reco():
    messages = [{"type": "user", "content": "こんにちは"}]
    assert len(split_archive_into_episodes(messages)) == 1


def test_profile_has_data():
    assert _profile_has_data({"age": 30}) is True
    assert _profile_has_data({"age": None, "allergies": []}) is False


@patch("src.services.line_memory_backfill.extract_profile_from_messages")
@patch("src.services.line_memory_backfill.save_line_memory")
@patch("src.services.session_manager.save_session_to_db")
@patch("src.services.session_manager.get_session_from_db")
@patch("src.services.line_memory_backfill.load_line_memory", return_value=({}, []))
def test_backfill_merges_session_user_attributes(_load, mock_get_db, _save_db, _save_mem, _extract):
    mock_get_db.return_value = {
        "session_id": "line:U1",
        "user_attributes": {"age": 25, "gender": "女性"},
        "message_archive": [{"type": "user", "content": "頭痛"}],
        "messages": [],
    }
    _extract.side_effect = lambda p, _m: p
    result = run_line_memory_backfill("line:U1", force=False)
    assert result["profile_updated"] is True
    assert result["has_profile"] is True
    _save_mem.assert_called()


@patch("src.agents.episode_summary_agent.run_episode_summary_agent", return_value={"summary_text": "x"})
@patch("src.services.line_memory_backfill.extract_profile_from_messages")
@patch("src.services.line_memory_backfill.save_line_memory")
@patch("src.services.session_manager.save_session_to_db")
@patch("src.services.session_manager.get_session_from_db")
@patch(
    "src.services.line_memory_backfill.load_line_memory",
    side_effect=[({}, []), ({}, [{"summary_text": "x"}])],
)
def test_backfill_generates_summaries_when_empty(
    _load, mock_get_db, _save_db, _save_mem, _extract, mock_summary
):
    mock_get_db.return_value = {
        "session_id": "line:U1",
        "user_attributes": {},
        "message_archive": [
            {"type": "user", "content": "頭痛"},
            {"type": "bot", "content": "sage_reco", "diagnosis": {"render": "sage_reco", "recommended_medicines": [{}]}},
        ],
        "messages": [],
    }
    _extract.side_effect = lambda p, _m: p
    result = run_line_memory_backfill("line:U1", force=False)
    assert result["summaries_added"] == 1
    mock_summary.assert_called_once()


def test_collect_line_session_messages_merges_archive_and_live():
    data = {
        "message_archive": [{"type": "user", "content": "a"}],
        "messages": [{"type": "user", "content": "b"}],
    }
    msgs = collect_line_session_messages(data)
    assert len(msgs) >= 1
