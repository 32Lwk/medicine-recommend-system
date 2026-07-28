"""SSE chat stream API"""
import time
from unittest.mock import patch

from src.handlers.chat_stream import _extract_done_messages
from src.handlers.sse_events import SseDoneEvent


def _sse_line(event, data, event_id=None):
    import json

    lines = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    lines.append(f"data: {json.dumps(data, ensure_ascii=False)}")
    lines.append("")
    return "\n".join(lines) + "\n"


def test_sse_line_format():
    line = _sse_line("advice_delta", {"text": "あ"}, event_id="42")
    assert "event: advice_delta" in line
    assert "id: 42" in line
    assert '"あ"' in line


def test_sse_done_payload_trace():
    payload = SseDoneEvent(http_status=200, status="ok", message_count=2, trace_id="t-99").to_payload()
    assert payload["trace_id"] == "t-99"
    assert payload["message_count"] == 2


def test_sse_done_payload_includes_bot_message():
    bot = {"type": "bot", "content": "案内です", "store_inquiry": True}
    user = {"type": "user", "content": "トイレはどこ？"}
    payload = SseDoneEvent(
        message_count=2,
        bot_message=bot,
        user_message=user,
    ).to_payload()
    assert payload["bot_message"] == bot
    assert payload["user_message"] == user


def test_sse_done_payload_includes_dev_error_fields():
    payload = SseDoneEvent(
        http_status=200,
        message_count=1,
        error=True,
        response="【開発プレビュー】クライアント側のエラーカード表示です。",
        dev_preview_kind="client_error",
    ).to_payload()
    assert payload["error"] is True
    assert "開発プレビュー" in payload["response"]
    assert payload["dev_preview_kind"] == "client_error"


def test_build_sse_done_event_from_dev_client_error():
    from src.handlers.chat_stream import _build_sse_done_event

    body = {
        "error": True,
        "response": "【開発プレビュー】クライアント側のエラーカード表示です。",
        "message_count": 1,
        "dev_preview_kind": "client_error",
    }
    messages = [{"type": "user", "content": "mrcdev00000000000001"}]
    done = _build_sse_done_event(body, 200, messages)
    payload = done.to_payload()
    assert payload["error"] is True
    assert payload["message_count"] == 1
    assert "bot_message" not in payload
    assert payload["dev_preview_kind"] == "client_error"


def test_sse_stream_emits_client_preview_before_done():
    import re
    from unittest.mock import patch
    from starlette.testclient import TestClient
    from src.services.chat_inflight import end_chat_job
    from src.services.sse_emit import clear_session_stream_state
    import main

    sid = "sid-dev-preview-sse"
    end_chat_job(sid)
    clear_session_stream_state(sid)
    try:
        with patch("src.handlers.chat.chat_dev_triggers.is_development_runtime", return_value=True):
            with patch("src.handlers.chat.chat_dev_triggers.save_session_to_db"):
                with patch("src.handlers.chat.chat_dev_triggers.get_session_from_db", return_value=None):
                    with TestClient(main.app) as client:
                        client.cookies.set("sid", sid)
                        response = client.post(
                            "/api/chat/stream",
                            data={"message": "mrcdev00000000000001"},
                            headers={"Accept": "text/event-stream"},
                        )
                        assert response.status_code == 200
                        text = response.text
                        preview_match = re.search(r"event: client_preview\s*\ndata: (.+)", text)
                        done_match = re.search(r"event: done\s*\ndata: (.+)", text)
                        assert preview_match is not None
                        assert done_match is not None
                        assert text.index("event: client_preview") < text.index("event: done")
                        assert '"error": true' in preview_match.group(1) or '"error":true' in preview_match.group(1)
    finally:
        end_chat_job(sid)
        clear_session_stream_state(sid)


def test_extract_done_messages_when_last_is_bot():
    messages = [
        {"type": "user", "content": "こんにちは"},
        {"type": "bot", "content": "返信", "counseling": True},
    ]
    bot, user = _extract_done_messages(messages)
    assert bot["content"] == "返信"
    assert user["content"] == "こんにちは"


def test_extract_done_messages_when_trailing_user():
    messages = [
        {"type": "user", "content": "a"},
        {"type": "bot", "content": "返信", "counseling": True},
        {"type": "user", "content": "a"},
    ]
    bot, user = _extract_done_messages(messages)
    assert bot["content"] == "返信"
    assert user["content"] == "a"


def test_run_chat_post_records_worker_timing():
    from src.handlers.chat_stream import _run_chat_post
    from src.utils.chat_http_context import ChatClientInfo
    from src.utils.request_safe_session import RequestSafeSession

    session = RequestSafeSession()
    client_info = ChatClientInfo(user_agent="", client_ip="127.0.0.1")
    monitor = object()
    timing: dict = {"started": False, "started_at": None}

    with patch("src.handlers.chat_stream.bind_worker_stream_sink"):
        with patch("src.handlers.chat_stream.handle_chat_post", return_value=({"status": "ok"}, 200)):
            _run_chat_post(session, client_info, "test", "sid-timing", monitor, timing)

    assert timing["started"] is True
    assert timing["started_at"] is not None


def test_stream_elapsed_sec_before_and_after_worker_start():
    from src.handlers.chat_stream import _stream_elapsed_sec

    started_at = time.monotonic()
    timing = {"started": False, "started_at": None}
    elapsed, worker_started = _stream_elapsed_sec(started_at, timing)
    assert worker_started is False
    assert elapsed >= 0

    timing["started"] = True
    timing["started_at"] = time.monotonic()
    elapsed2, worker_started2 = _stream_elapsed_sec(started_at, timing)
    assert worker_started2 is True
    assert elapsed2 >= 0


def test_build_stream_done_payload():
    from src.handlers.chat_stream import build_stream_done_payload

    bot = {"type": "bot", "content": "ok", "diagnosis": {"render": "sage_reco"}}
    user = {"type": "user", "content": "test"}
    session = {"messages": [user, bot]}
    payload = build_stream_done_payload(
        {"status": "ok", "message_count": 2},
        200,
        session,
        "sid1",
    )
    assert payload["bot_message"]["content"] == "ok"
    assert payload["message_count"] == 2


def test_peek_stream_result_does_not_consume():
    from src.services.sse_emit import peek_stream_result, pop_stream_result, set_stream_result

    set_stream_result("sid-peek", {"status": "ok", "message_count": 1}, 200)
    assert peek_stream_result("sid-peek") is not None
    assert peek_stream_result("sid-peek") is not None
    assert pop_stream_result("sid-peek") is not None
    assert peek_stream_result("sid-peek") is None


def test_second_stream_post_does_not_return_stale_cached_done():
    """2通目以降の POST が前ターンの stream_result キャッシュで短絡されないこと。"""
    from starlette.testclient import TestClient
    from src.services.sse_emit import peek_stream_result, set_stream_result
    from src.services.chat_inflight import end_chat_job
    from src.services.sse_emit import clear_session_stream_state
    import main

    sid = "sid-two-turn-cache"
    end_chat_job(sid)
    clear_session_stream_state(sid)
    seen_messages = []

    def fake_handle_chat_post(session, client_info, message, sid_arg, monitor, job_meta=None, **kwargs):
        seen_messages.append(message)
        return {"status": "ok", "message_count": len(seen_messages) * 2}, 200

    with patch("src.handlers.chat_stream.handle_chat_post", side_effect=fake_handle_chat_post):
        with patch("src.handlers.chat_stream.persist_session_from_chat_state"):
            with TestClient(main.app) as client:
                client.cookies.set("sid", sid)
                set_stream_result(sid, {"status": "ok", "message_count": 2}, 200)

                response = client.post(
                    "/api/chat/stream",
                    data={"message": "頭が痛い"},
                    headers={"Accept": "text/event-stream"},
                )
                assert response.status_code == 200
                assert "event: status" in response.text
                assert seen_messages == ["頭が痛い"]
                assert "event: done" in response.text


def test_duplicate_post_preserves_stream_result_for_reattach():
    """ワーカー完了後の duplicate POST が stream_result を消さず done を返すこと。"""
    from starlette.testclient import TestClient
    from src.services.chat_inflight import end_chat_job
    from src.services.sse_emit import clear_session_stream_state, note_stream_turn_message, set_stream_result
    import main

    sid = "sid-dup-post-preserve-result"
    end_chat_job(sid)
    clear_session_stream_state(sid)
    msg = "免責事項の違いは？"
    body = {
        "status": "ok",
        "message_count": 2,
    }
    set_stream_result(sid, body, 200)
    note_stream_turn_message(sid, msg)
    try:
        with TestClient(main.app) as client:
            client.cookies.set("sid", sid)
            response = client.post(
                "/api/chat/stream",
                data={"message": "免責事項の違いは？"},
                headers={"Accept": "text/event-stream"},
            )
            assert response.status_code == 200
            assert "event: done" in response.text
    finally:
        end_chat_job(sid)
        clear_session_stream_state(sid)


def test_stream_result_api_honors_submit_sid_query():
    from starlette.testclient import TestClient
    from src.services.sse_emit import clear_session_stream_state, set_stream_result
    import main

    sid = "sid-stream-result-query"
    clear_session_stream_state(sid)
    set_stream_result(sid, {"status": "ok", "message_count": 1}, 200)
    try:
        with TestClient(main.app) as client:
            client.cookies.set("sid", "sid-other-cookie")
            response = client.get(f"/api/chat/stream-result?submit_sid={sid}")
            assert response.status_code == 200
            data = response.json()
            assert data.get("ready") is True
            assert data.get("done", {}).get("message_count") == 1
    finally:
        clear_session_stream_state(sid)


def test_second_stream_post_reattaches_when_job_in_flight():
    """処理中の duplicate POST が sink を閉じず reattach すること。"""
    import threading
    from starlette.testclient import TestClient
    from src.services.chat_inflight import end_chat_job
    from src.services.sse_emit import clear_session_stream_state
    import main

    sid = "sid-inflight-reattach"
    end_chat_job(sid)
    clear_session_stream_state(sid)
    post_started = threading.Event()
    release_post = threading.Event()
    call_count = {"n": 0}
    results: dict = {}

    def slow_handle_chat_post(session, client_info, message, sid_arg, monitor, job_meta=None, **kwargs):
        call_count["n"] += 1
        post_started.set()
        release_post.wait(timeout=5)
        session["messages"] = [
            {"type": "user", "content": message},
            {"type": "bot", "content": "回答です"},
        ]
        return {"status": "ok", "message_count": 2}, 200

    def run_post(label: str, client: TestClient):
        results[label] = client.post(
            "/api/chat/stream",
            data={"message": "免責事項の違いは？"},
            headers={"Accept": "text/event-stream"},
        )

    try:
        with patch("src.handlers.chat_stream.handle_chat_post", side_effect=slow_handle_chat_post):
            with patch("src.handlers.chat_stream.persist_session_from_chat_state"):
                with TestClient(main.app) as client:
                    client.cookies.set("sid", sid)
                    th1 = threading.Thread(target=run_post, args=("first", client))
                    th1.start()
                    assert post_started.wait(timeout=10)
                    th2 = threading.Thread(target=run_post, args=("second", client))
                    th2.start()
                    release_post.set()
                    th1.join(timeout=30)
                    th2.join(timeout=30)

                r1 = results.get("first")
                r2 = results.get("second")

                assert r1.status_code == 200
                assert r2.status_code == 200
                assert call_count["n"] == 1
                assert "duplicate_skip" not in r2.text
                assert "event: done" in r1.text
                assert "event: done" in r2.text
    finally:
        end_chat_job(sid)
        clear_session_stream_state(sid)


def test_run_chat_post_uses_sync_handler_not_nested_asyncio():
    """GUNICORN_WORKERS=1 でも SSE ワーカーが同一 ThreadPool でデッドロックしないこと。"""
    from src.handlers.chat_stream import _run_chat_post
    from src.utils.chat_http_context import ChatClientInfo
    from src.utils.request_safe_session import RequestSafeSession

    session = RequestSafeSession()
    client_info = ChatClientInfo(user_agent="", client_ip="127.0.0.1")
    monitor = object()

    with patch("src.handlers.chat_stream.bind_worker_stream_sink") as bind_mock:
        with patch("src.handlers.chat_stream.handle_chat_post", return_value=({"status": "ok"}, 200)) as post_mock:
            body, status = _run_chat_post(session, client_info, "こんにちは", "sid-test", monitor, {})

    assert status == 200
    bind_mock.assert_called_once_with("sid-test")
    post_mock.assert_called_once()
    assert post_mock.call_args.args[:5] == (session, client_info, "こんにちは", "sid-test", monitor)


def test_messages_for_sse_done_falls_back_to_db_when_session_empty():
    from src.handlers.chat_stream import _build_sse_done_event, _messages_for_sse_done

    bot = {
        "type": "bot",
        "content": "sage_qa",
        "diagnosis": {"render": "sage_qa", "message": "回答"},
    }
    user = {"type": "user", "content": "ロキソニンって眠くなる？"}
    db_messages = [user, bot]
    session = {}

    with patch("src.handlers.chat_stream.get_session_from_db", return_value={"messages": db_messages}):
        messages = _messages_for_sse_done(session, "sid1", {"status": "ok", "message_count": 2})

    assert messages == db_messages
    done = _build_sse_done_event({"status": "ok", "message_count": 2}, 200, messages)
    payload = done.to_payload()
    assert payload["bot_message"] == bot
    assert payload["diagnosis"]["render"] == "sage_qa"
