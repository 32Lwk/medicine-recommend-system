# ルート仕様表（FastAPI `main.py` / Flask 互換）

根拠: `main.py`, `src/routes/main_routes.py`, `src/routes/api_routes.py`, `src/routes/feedback_routes.py`, `src/routes/admin_routes.py`

凡例: **sid** = Cookie `sid`（`SID_COOKIE_NAME`）。**Basic** = `Authorization: Basic`（ユーザー名 `admin` / `ADMIN_PASSWORD`）。

| Method | Path | Input | 典型 Status | Content-Type | sid / ガード | 備考 |
|--------|------|-------|-------------|--------------|--------------|------|
| GET | `/` | — | 200 | text/html | `get_sid` で発行 | `index.html` |
| GET | `/test/` | — | 200 | text/html | 同上 | `app_base_path=/test` |
| GET | `/favicon.ico` | — | 204 | (empty) | — | |
| GET | `/sitemap.xml` | — | 200 | application/xml; charset=utf-8 | — | `PUBLIC_SITE_URL` |
| POST | `/` | `multipart/form-data` `message` | 200 | application/json | チャット用 | Flask handler 互換層 |
| POST | `/test/` | 同上 | 200 | application/json | 同上 | |
| POST | `/clear` | — | 204 | — | DB 更新 | |
| POST | `/test/clear` | — | 204 | — | 同上 | |
| POST | `/new_session` | — | 200 | application/json | 新 sid cookie | `message`, `username` |
| POST | `/test/new_session` | — | 200 | application/json | 同上 | |
| GET | `/api/sessions` | — | 200 | application/json | 必須 | `messages`, `user_attributes`, `latest_usage_notes` |
| POST | `/api/sessions` | JSON `user_attributes` | 200 | application/json | 必須 | |
| POST | `/api/submit_feedback` | JSON | 200/400/429/500 | application/json | 60秒レート | 必須フィールドあり |
| GET | `/api/get_feedback_reports` | `limit`, `unresolved_only` | 200/500 | application/json | — | DB |
| POST | `/api/resolve_feedback/{id}` | — | 200/500 | application/json | — | |
| POST | `/api/delete_feedback/{id}` | — | 200/500 | application/json | — | |
| GET | `/admin` | — | 200/401 | text/html | **Basic** | `admin_chat.html` |
| GET | `/api/main_sessions` | — | 200 | application/json | | |
| GET/POST | `/api/main_manual_reply_queue` | POST: JSON | 200/400 | application/json | | |
| GET/POST | `/api/main_ai_control` | POST: JSON | 200/400 | application/json | | |
| GET/POST | `/api/manual_reply_message` | POST: JSON | 200/400 | application/json | | |
| GET | `/api/status` | — | 200 | application/json | Depends sid | |
| GET | `/api/performance` | — | 200 | application/json | | |
| GET | `/api/logs` | — | 200 | application/json | | |
| POST | `/api/admin_mode` | — | 200 | application/json | | |
| GET/POST | `/api/ai_control` | POST: JSON | 200/400 | application/json | | |
| GET/POST | `/api/manual_reply_queue` | POST: JSON | 200/400 | application/json | | |
| GET | `/api/all_sessions` | — | 200 | application/json | | |
| GET | `/api/session_stats` | — | 200 | application/json | | |
| GET | `/api/debug_manual_replies` | — | 200 | application/json | | |
| POST | `/api/set_language` | JSON `language` | 200/400 | application/json | sid 推奨 | `ja`/`en`/`ko`/`zh` |
| GET/POST | `/api/user_attributes` | POST: JSON | 200/400 | application/json | sid | |
| POST | `/api/translate` | JSON | 200/400/500 | application/json | | |
| GET | `/admin/system_status` | — | 200 | application/json | | 監視 |
| GET | `/admin/access_stats` | — | 200 | application/json | | |
| GET | `/admin/performance_stats` | — | 200 | application/json | | |
| GET | `/admin/browser_distribution` | — | 200 | application/json | | |
| GET | `/admin/os_distribution` | — | 200 | application/json | | |
| GET | `/admin/device_distribution` | — | 200 | application/json | | |
| GET | `/admin/realtime_monitoring` | — | 200 | application/json | | |
| GET | `/admin/export_monitoring_data` | — | 200 | application/json | | |
| POST | `/admin/ai_control` | JSON `mode` on/off | 200/400 | application/json | | グローバル AI |
| POST | `/admin/medicine_chat` | JSON `message` | 200/400/500 | application/json | | 推奨テスト |
| POST | `/clear_logs` | — | 200 | application/json | | セッション・キュー・ログファイル |
| GET | `/api/admin/sessions` | — | 200 | application/json | | cleanup 呼び出し |
| DELETE | `/api/admin/sessions/{session_id}` | — | 200/404/500 | application/json | | |
| DELETE | `/api/admin/sessions/delete_all` | — | 200/500 | application/json | | |
| PUT | `/api/admin/sessions/{session_id}` | JSON | 200/404 | application/json | | |
| POST | `/api/admin/send_message` | JSON | 200/400/404 | application/json | | |
| POST | `/api/request_admin` | — | 200/400 | application/json | sid | |

**CORS**: `config/app_config.get_cors_config()` → `CORSMiddleware`（`allow_credentials` 含む）。

**404**: 未一致パスは `index.html` を **404** で返却（自動リダイレクトなし）。

**未確定・環境依存**: OpenAI/DB 接続が無い場合の各エンドポイントのメッセージは `.env` と `init_database()` の成否に依存。
