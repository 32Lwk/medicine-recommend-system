"""chat_inflight.py — duplicate POST guard."""
from src.services.chat_inflight import (
    end_chat_job,
    get_chat_job_token,
    is_chat_job_in_flight,
    should_orphan_persist,
    try_begin_chat_job,
)


def test_try_begin_and_end_local():
    sid = "test-session-inflight-1"
    end_chat_job(sid)
    assert try_begin_chat_job(sid) is True
    assert is_chat_job_in_flight(sid) is True
    token = get_chat_job_token(sid)
    assert token
    assert try_begin_chat_job(sid) is False
    end_chat_job(sid)
    assert is_chat_job_in_flight(sid) is False


def test_should_orphan_persist_stale():
    sid = "test-session-inflight-2"
    end_chat_job(sid)
    assert try_begin_chat_job(sid) is True
    orphan = get_chat_job_token(sid)
    end_chat_job(sid)
    assert try_begin_chat_job(sid) is True
    new_token = get_chat_job_token(sid)
    assert orphan != new_token
    assert should_orphan_persist(sid, orphan) is False
    assert should_orphan_persist(sid, new_token) is True
    end_chat_job(sid)
