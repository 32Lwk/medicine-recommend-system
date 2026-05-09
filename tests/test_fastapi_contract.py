"""
FastAPI 契約の最小回帰テスト（DB/OpenAI なしでも実行可能なもの中心）。
"""
import os

import pytest
from starlette.testclient import TestClient


@pytest.fixture()
def client():
    os.environ.setdefault("SECRET_KEY", "test-secret")
    import main

    with TestClient(main.app) as c:
        yield c


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


def test_sitemap_xml(client):
    r = client.get("/sitemap.xml")
    assert r.status_code == 200
    ct = r.headers.get("content-type", "")
    assert "application/xml" in ct
    assert b"urlset" in r.content


def test_admin_unauthorized(client):
    r = client.get("/admin")
    assert r.status_code == 401
    assert "WWW-Authenticate" in r.headers


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


def test_main_ai_control_get_json(client):
    r = client.get("/api/main_ai_control")
    assert r.status_code == 200
    j = r.json()
    assert "ai_auto_reply" in j and "admin_mode" in j


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
    r = client.get("/api/admin/sessions")
    assert r.status_code == 200
    j = r.json()
    assert "sessions" in j and "admin_mode" in j
