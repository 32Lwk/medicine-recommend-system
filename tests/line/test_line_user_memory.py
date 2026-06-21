"""LINE 長期記憶のテスト。"""
from __future__ import annotations

from unittest.mock import patch

from src.agents.memory_delete_agent import classify_memory_delete_intent, execute_memory_delete
from src.services.line_memory_context import build_long_term_memory_block, compress_message_for_llm
from src.services.line_user_memory import (
    append_consultation_summary,
    delete_line_memory,
    merge_user_attributes,
    persist_profile_from_session,
    resolve_memory_owner_sid,
)


def test_resolve_memory_owner_line_sid():
    assert resolve_memory_owner_sid("line:Uabc") == "line:Uabc"


def test_resolve_memory_owner_handoff():
    session = {"handoff_from_line": "line:Uxyz"}
    assert resolve_memory_owner_sid("999888", session) == "line:Uxyz"


def test_merge_user_attributes_lists():
    base = {"allergies": ["花粉"], "age": 30}
    incoming = {"allergies": ["ペニシリン"], "gender": "女性"}
    merged = merge_user_attributes(base, incoming)
    assert "花粉" in merged["allergies"]
    assert "ペニシリン" in merged["allergies"]
    assert merged["gender"] == "女性"
    assert merged["age"] == 30


@patch("src.services.line_user_memory.save_line_memory")
@patch("src.services.line_user_memory.load_line_memory", return_value=({}, []))
def test_persist_profile_from_session(_load, mock_save):
    persist_profile_from_session("line:U1", {"age": 25, "gender": "男性"})
    mock_save.assert_called_once()


@patch("src.services.line_user_memory.save_line_memory")
@patch(
    "src.services.line_user_memory.load_line_memory",
    return_value=({"age": 20}, [{"id": "s1", "summary_text": "頭痛"}]),
)
def test_append_consultation_summary(_load, mock_save):
    append_consultation_summary("line:U1", {"summary_text": "発熱"})
    args = mock_save.call_args.kwargs
    assert len(args["summaries"]) == 2


@patch("src.services.session_lifecycle.append_lifecycle_event")
@patch("src.services.session_manager.save_session_to_db")
@patch("src.services.session_manager.get_session_from_db")
@patch(
    "src.services.line_user_memory.load_line_memory",
    return_value=(
        {"age": 30, "allergies": ["a", "b"], "gender": "女性"},
        [{"id": "ep1"}],
    ),
)
def test_delete_partial_profile(_load, mock_get_db, mock_save_db, _lifecycle):
    mock_get_db.return_value = {"session_id": "line:U1", "messages": []}
    delete_line_memory("line:U1", profile_keys=["allergies"])
    saved = mock_save_db.call_args[0][1]
    assert saved["line_user_profile"]["allergies"] == []


def test_classify_memory_delete_all():
    plan = classify_memory_delete_intent("記憶を全部消して", client=None)
    assert plan.get("is_delete_request") is True
    assert plan.get("scope") == "all"


def test_classify_memory_delete_partial_allergy():
    plan = classify_memory_delete_intent("アレルギー情報だけ消して", client=None)
    assert plan.get("is_delete_request") is True
    assert "allergies" in (plan.get("profile_keys") or [])


def test_compress_sage_reco_message():
    msg = {
        "type": "bot",
        "content": "sage_reco",
        "diagnosis": {
            "render": "sage_reco",
            "symptoms": ["頭痛"],
            "recommended_medicines": [{"product_name": "イブA錠"}],
        },
    }
    out = compress_message_for_llm(msg)
    assert "イブA錠" in out["content"]
    assert "頭痛" in out["content"]


@patch(
    "src.services.line_memory_context.load_line_memory",
    return_value=({"age": 40, "allergies": ["花粉"]}, [{"summary_text": "前回頭痛", "created_at": "2026-06-20"}]),
)
def test_build_long_term_memory_block(_load):
    block = build_long_term_memory_block({"user_attributes": {}}, "line:U1")
    assert "長期プロファイル" in block
    assert "40" in block
    assert "前回頭痛" in block


def test_memory_digest_changes_cache_key():
    from src.services.triage_cache import build_cache_key
    from src.services.triage_history import memory_digest

    block_a = "【ユーザー長期プロファイル】\n年齢: 40"
    block_b = block_a + "\nアレルギー: 花粉"
    k1 = build_cache_key("頭痛", memory_digest=memory_digest(block_a))
    k2 = build_cache_key("頭痛", memory_digest=memory_digest(block_b))
    assert k1 != k2


@patch("src.services.line_user_memory.save_line_memory")
@patch(
    "src.services.line_user_memory.load_line_memory",
    return_value=({"age": 20}, [{"id": "s1", "summary_text": "頭痛", "episode_id": "ep1"}]),
)
def test_upsert_consultation_summary_same_episode(_load, mock_save):
    from src.services.line_user_memory import upsert_consultation_summary

    upsert_consultation_summary("line:U1", {"summary_text": "発熱"}, episode_id="ep1")
    args = mock_save.call_args.kwargs
    assert len(args["summaries"]) == 1
    assert args["summaries"][0]["summary_text"] == "発熱"


@patch("src.services.session_lifecycle.append_lifecycle_event")
@patch("src.services.session_manager.save_session_to_db")
@patch("src.services.session_manager.get_session_from_db")
@patch(
    "src.services.line_user_memory.load_line_memory",
    return_value=(
        {"age": 30, "allergies": ["a"], "gender": "女性"},
        [{"id": "ep1", "summary_text": "x"}],
    ),
)
def test_delete_all_includes_archive(_load, mock_get_db, mock_save_db, mock_lifecycle):
    mock_get_db.return_value = {
        "session_id": "line:U1",
        "message_archive": [{"type": "user", "content": "hi"}],
        "messages": [{"type": "user", "content": "x"}],
    }
    delete_line_memory("line:U1", clear_profile=True, clear_summaries=True, clear_archive=True)
    saved = mock_save_db.call_args[0][1]
    assert saved["message_archive"] == []
    mock_lifecycle.assert_called_once()
    assert mock_lifecycle.call_args[0][1] == "line_memory_deleted"
