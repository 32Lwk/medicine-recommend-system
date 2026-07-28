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


def test_redis_unavailable_falls_back_to_local_inflight(monkeypatch):
    """REDIS_URL あり・redis 未接続時もローカル inflight で reserve できること。"""
    from src.services.chat_inflight import _begin_chat_job_token, reserve_chat_job

    sid = "test-redis-unavailable-fallback"
    end_chat_job(sid)
    monkeypatch.setattr(
        "src.services.chat_inflight._redis_client_available",
        lambda: False,
    )
    token = reserve_chat_job(sid)
    assert token
    assert _begin_chat_job_token(sid) is None
    end_chat_job(sid)
