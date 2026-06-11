"""chat_inflight の重複 POST 防止"""
from src.services.chat_inflight import end_chat_job, try_begin_chat_job


def test_try_begin_chat_job_blocks_duplicate_sid():
    sid = "test-session-inflight-1"
    end_chat_job(sid)
    assert try_begin_chat_job(sid) is True
    assert try_begin_chat_job(sid) is False
    end_chat_job(sid)
    assert try_begin_chat_job(sid) is True
    end_chat_job(sid)
