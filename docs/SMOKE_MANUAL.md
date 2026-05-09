# 手動スモーク（互換確認チェックリスト）

ローカル: `.venv` を有効化し `python -m uvicorn main:app --host 127.0.0.1 --port $PORT` または `bash start.sh`。

| # | 確認内容 | 手順 | 期待結果 |
|---|----------|------|----------|
| 1 | GET `/` | ブラウザまたは `curl -i` | 200, `text/html`, UI 表示、`Set-Cookie: sid`（初回） |
| 2 | GET `/test/` | 同上 | 200, `APP_BASE_PATH=/test` 相当の動作（JS が `/test/` に POST） |
| 3 | 末尾スラッシュ | `curl -i -X POST http://127.0.0.1:8000/`（FormData） | **307/308 なし** |
| 4 | POST チャット `/` | `curl -F "message=hello" -b cookies.txt -c cookies.txt` | 200 `application/json`、キー `error`/`response`/`risk_score` 等がフロント契約と一致 |
| 5 | GET `/api/sessions` | `curl -b cookies.txt` | 200 JSON、`messages` / `user_attributes` / `latest_usage_notes` |
| 6 | POST `/clear` | `curl -i -X POST -b cookies.txt` | **204** |
| 7 | POST `/new_session` | `curl -X POST -b cookies.txt` | 200 JSON `message`, `username` |
| 8 | `/test/clear`, `/test/new_session` | 上記と同様に `/test/...` | 同じ Status/形 |
| 9 | GET `/favicon.ico` | `curl -i` | **200**、`Content-Type: image/png`（アセット無し時のみ 204） |
|10 | GET `/sitemap.xml` | `curl -i` | 200, `application/xml; charset=utf-8` |
|11 | GET `/admin` | 認証なし `curl -i` | **401**, `WWW-Authenticate: Basic realm="Admin Area"` |
|12 | GET `/admin` | Basic 正しい認証情報 | 200 `admin_chat.html` |
|13 | GET `/admin/system_status` ほか | 管理 UI または curl | 200 JSON（監視モーダル用） |
|14 | POST `/api/submit_feedback` | 正しい JSON 本体 | DB あり: `success` + `feedback_id`；DB なし: 500 `Database not available` |
|15 | POST `/api/submit_feedback` | 60秒以内に同一 `sid` で再送 | **429** |
|16 | POST `/api/submit_feedback` | 不正 JSON | **400** `Invalid JSON` |
|17 | CORS | 別オリジンから `credentials: 'include'`（許可 origin のみ） | ブラウザで CORS エラーにならない |
|18 | POST `/clear_logs` | 管理操作 | 200 JSON `status: ok`、ログファイル・キュー・セッションが Flask 同等にクリア |

**根拠ファイル**: `main.py`, `config/app_config.py`, `static/js/main.js`, `static/js/admin_chat.js`
