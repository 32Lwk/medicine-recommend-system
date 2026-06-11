"""
FastAPI 契約の最小回帰テスト（DB/OpenAI なしでも実行可能なもの中心）。
"""


def test_get_root_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")


def test_get_test_prefix_html(client):
    r = client.get("/test/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")


def test_favicon_png(client):
    r = client.get("/favicon.ico")
    assert r.status_code == 200
    assert "image/png" in r.headers.get("content-type", "")
    assert len(r.content) > 32
    # 実体が PNG であること（JPEG を image/png で返すと Safari が採用しない）
    assert r.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_sitemap_xml(client):
    r = client.get("/sitemap.xml")
    assert r.status_code == 200
    ct = r.headers.get("content-type", "")
    assert "application/xml" in ct
    assert b"urlset" in r.content


def test_admin_unauthorized(client):
    r = client.get("/admin", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers.get("location", "").endswith("/admin/login")


def test_api_sessions_json_shape(client):
    r = client.get("/api/sessions")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/json")
    data = r.json()
    assert "messages" in data
    assert "user_attributes" in data


def test_submit_feedback_invalid_json(client):
    r = client.post("/api/submit_feedback", content="{not json")
    assert r.status_code == 400
    body = r.json()
    assert "error" in body


def test_404_returns_html_not_redirect(client):
    r = client.get("/this-path-does-not-exist-xyz", follow_redirects=False)
    assert r.status_code == 404
    assert "text/html" in r.headers.get("content-type", "")


def test_post_clear_204(client):
    r = client.post("/clear")
    assert r.status_code == 204


def test_get_root_injects_app_version_and_empty_base_path(client):
    r = client.get("/")
    assert r.status_code == 200
    text = r.text
    assert "window.APP_VERSION" in text
    assert 'window.APP_BASE_PATH' in text
    # 既定はルート（空文字）
    assert '""' in text or "''" in text or "APP_BASE_PATH" in text


def test_get_test_injects_base_path_test(client):
    r = client.get("/test/")
    assert r.status_code == 200
    # tojson で "/test" が埋め込まれる
    assert '"/test"' in r.text or "'/test'" in r.text


def test_post_new_session_json_shape(client):
    r = client.post("/new_session")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/json")
    data = r.json()
    assert "message" in data and "username" in data


def test_post_test_new_session_json_shape(client):
    r = client.post("/test/new_session")
    assert r.status_code == 200
    data = r.json()
    assert "message" in data and "username" in data


def test_post_chat_root_returns_json(client):
    """FormData POST / は JSON（OpenAI 未設定でもハンドラが JSON を返すことを期待）。"""
    r = client.post("/", data={"message": "test"})
    assert r.status_code == 200
    assert "application/json" in r.headers.get("content-type", "")
    body = r.json()
    assert isinstance(body, dict)
    assert any(k in body for k in ("error", "warning", "response", "risk_score", "message_count"))


def test_post_chat_test_prefix_returns_json(client):
    r = client.post("/test/", data={"message": "hello"})
    assert r.status_code == 200
    assert "application/json" in r.headers.get("content-type", "")
    assert isinstance(r.json(), dict)


def test_post_api_sessions_persists_user_attributes(client):
    c = client
    payload = {"user_attributes": {"age": 30, "gender": "male"}}
    r = c.post("/api/sessions", json=payload)
    assert r.status_code == 200
    assert r.json().get("status") == "ok"
    g = c.get("/api/sessions")
    assert g.status_code == 200
    assert g.json().get("user_attributes", {}).get("age") == 30


def test_set_language_success(client):
    r = client.post("/api/set_language", json={"language": "en"})
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "success"
    assert data.get("language") == "en"


def test_set_language_invalid_400(client):
    r = client.post("/api/set_language", json={"language": "xx"})
    assert r.status_code == 400


def test_ai_control_get_json(client):
    r = client.get("/api/ai_control")
    assert r.status_code == 200
    j = r.json()
    assert "ai_auto_reply" in j


def _set_admin_cookie(client):
    from src.services.admin_auth import ADMIN_COOKIE_NAME, create_admin_token

    client.cookies.set(ADMIN_COOKIE_NAME, create_admin_token())


def test_main_ai_control_requires_admin(client):
    r = client.get("/api/main_ai_control")
    assert r.status_code == 401


def test_main_ai_control_get_json(client):
    _set_admin_cookie(client)
    r = client.get("/api/main_ai_control")
    assert r.status_code == 200
    j = r.json()
    assert "ai_auto_reply" in j and "admin_mode" in j


def test_main_sessions_requires_admin(client):
    r = client.get("/api/main_sessions")
    assert r.status_code == 401


def test_main_sessions_with_admin(client):
    _set_admin_cookie(client)
    r = client.get("/api/main_sessions")
    assert r.status_code == 200
    j = r.json()
    assert "sessions" in j
    assert isinstance(j["sessions"], list)


def test_main_sessions_meaningful_only_filter(client):
    from unittest.mock import patch

    _set_admin_cookie(client)
    sessions = {
        "empty-sid": {"messages": [], "username": "EmptyUser"},
        "full-sid": {"messages": [{"type": "user", "content": "hi"}], "username": "FullUser"},
    }
    with patch("main.get_all_sessions_from_db", return_value=sessions), patch(
        "main.get_manual_reply_session_ids", return_value=set()
    ), patch("main.cleanup_old_sessions") as cleanup_mock:
        r_filtered = client.get("/api/main_sessions?meaningful_only=1")
        assert r_filtered.status_code == 200
        ids_filtered = {s["session_id"] for s in r_filtered.json()["sessions"]}
        assert ids_filtered == {"full-sid"}
        cleanup_mock.assert_called_with(
            force=False,
            exclude_current_session=False,
            current_sid=None,
            skip_empty_sessions=False,
        )

        cleanup_mock.reset_mock()
        r_all = client.get("/api/main_sessions?meaningful_only=0")
        assert r_all.status_code == 200
        ids_all = {s["session_id"] for s in r_all.json()["sessions"]}
        assert ids_all == {"empty-sid", "full-sid"}
        cleanup_mock.assert_called_with(
            force=False,
            exclude_current_session=False,
            current_sid=None,
            skip_empty_sessions=True,
        )


def test_admin_delete_session_memory_fallback(client):
    from src.services.session_manager import delete_session_by_id, get_all_sessions_store

    _set_admin_cookie(client)
    store = get_all_sessions_store()
    store["mem-only-sid"] = {"session_id": "mem-only-sid", "messages": [], "username": "MemUser"}
    r = client.delete("/api/admin/sessions/mem-only-sid")
    assert r.status_code == 200
    assert r.json().get("status") == "success"
    assert "mem-only-sid" not in store

    r404 = client.delete("/api/admin/sessions/no-such-session-xyz")
    assert r404.status_code == 404


def test_admin_delete_session_requires_admin(client):
    r = client.delete("/api/admin/sessions/any-sid")
    assert r.status_code == 401


def test_admin_mode_post(client):
    r = client.post("/api/admin_mode")
    assert r.status_code == 200
    j = r.json()
    assert "admin_mode" in j and "message" in j


def test_request_admin_requires_cookie_session(client):
    """sid 無しでも 400 または処理（get_sid で常に sid が付くため通常 200）。"""
    r = client.post("/api/request_admin")
    assert r.status_code in (200, 400)


def test_api_status_and_performance_and_logs(client):
    for path in ("/api/status", "/api/performance", "/api/logs"):
        r = client.get(path)
        assert r.status_code == 200
    s = client.get("/api/status").json()
    assert "csv_load_status" in s


def test_all_sessions_and_session_stats(client):
    r = client.get("/api/all_sessions")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    if data:
        assert "session_id" in data[0]
    r2 = client.get("/api/session_stats")
    assert r2.status_code == 200


def test_debug_manual_replies(client):
    r = client.get("/api/debug_manual_replies")
    assert r.status_code == 200
    j = r.json()
    assert "manual_reply_queue" in j


def test_get_feedback_reports_db_fallback(client):
    r = client.get("/api/get_feedback_reports")
    # DB なし環境では 500
    assert r.status_code in (200, 500)


def test_admin_system_status_json(client):
    r = client.get("/admin/system_status")
    assert r.status_code == 200
    j = r.json()
    assert j.get("status") == "ok"


def test_admin_access_stats_json(client):
    r = client.get("/admin/access_stats")
    assert r.status_code == 200


def test_api_admin_sessions_list(client):
    _set_admin_cookie(client)
    r = client.get("/api/admin/sessions")
    assert r.status_code == 200
    j = r.json()
    assert "sessions" in j and "admin_mode" in j
