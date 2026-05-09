# FastAPI 構成（Flask 一括移行後）

## エントリポイント

- **`main.py`**: FastAPI `app` 単体。本番は `gunicorn -k uvicorn.workers.UvicornWorker main:app`（`start.sh`）。
- **レガシー**: `app.py`（Flask）は参照・比較用に残存しうるが、本番起動スクリプトは ASGI を指す。

## モジュール境界

| 層 | 役割 | 主なパス |
|----|------|----------|
| ルート | HTTP 契約（URL・Status・JSON/HTML） | `main.py`（将来 `routers/*` へ分割可能） |
| 設定 | CORS・Cookie・ログ・`.env` | `config/app_config.py` |
| セッション | `sid` Cookie + DB 正 | `src/services/session_manager.py` |
| 永続化 | PostgreSQL（Neon） | `src/services/database.py` |
| ドメイン | 薬学ロジック・チャット処理 | `src/core/*`, `src/handlers/chat_handler.py` |
| チャット POST | `handle_chat_post` → `tuple[dict, int]`、`main.py` は `JSONResponse` に変換 | `main.py`, `src/utils/chat_http_context.py` |

**原則**: `src/core/*` は変更しない。差分はアダプタ（`main.py` / handlers）に閉じる。

## CORS（t03）

- `config/app_config.get_cors_config()` の **`origins` / `methods` / `allow_headers` / `supports_credentials`** を `CORSMiddleware` にそのまま反映。
- フロントの `fetch(..., { credentials: 'include' })` と整合するよう **`allow_credentials=True`** を維持。

## Cookie（セッション ID）

- Cookie 名: 環境変数 `SID_COOKIE_NAME`（既定 `sid`）。
- 属性: `get_session_config()` の **`SESSION_COOKIE_SECURE` / `SESSION_COOKIE_SAMESITE` / `SESSION_COOKIE_HTTPONLY`** を `_compute_cookie_settings()` で Starlette の `set_cookie` にマップ。
- Flask 署名セッションの継続は不要（移行時に新 `sid` でよい）。

## 静的・テンプレ

- `/static` → `StaticFiles(directory="static")`。
- Jinja2: `templates.env.globals["url_for"]` で Flask 風 `url_for('static', filename=...)` を互換。

## 末尾スラッシュ

- `FastAPI(redirect_slashes=False)`。`POST /`・`POST /test/`・`/api/*` で **307/308 を出さない**。

## エラー応答（HTML / JSON）

- **404**: `index.html` を **404** で返却（Flask `error_handlers.handle_404` 相当）。
- **422**: バリデーション失敗は JSON `detail`。
- **その他未処理例外**: `POST` または `Content-Type: application/json` なリクエストは **JSON 500**（`error` / `response` / 非本番時 `error_type`）。それ以外は簡易 HTML 500。

## デプロイ

- Cloud Run 等は **`PORT`** でバインド。`start.sh` で `PORT` を gunicorn に渡す。
