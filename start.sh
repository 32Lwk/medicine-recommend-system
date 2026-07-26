#!/bin/bash
# Gunicorn起動スクリプト
# コマンドライン引数でタイムアウトを明示的に指定

# イメージに焼き込んだ build-meta.json を実行時 ENV へ反映（Cloud Run の古い GIT_COMMIT 上書き防止）
META_FILE="/app/static/build-meta.json"
if [ -f "$META_FILE" ]; then
  eval "$(python3 - <<'PY'
import json
import shlex

try:
    with open("/app/static/build-meta.json", encoding="utf-8") as fh:
        meta = json.load(fh)
    commit = str(meta.get("gitCommitShort") or "").strip()
    date = str(meta.get("gitCommitDateIso") or "").strip()
    if commit:
        print(f"export GIT_COMMIT={shlex.quote(commit)}")
    if date:
        print(f"export GIT_COMMIT_DATE={shlex.quote(date)}")
except Exception:
    pass
PY
)"
fi

# 環境変数からタイムアウトを取得（デフォルト: 300秒・LINE/推奨の長時間処理向け）
GUNICORN_TIMEOUT=${GUNICORN_TIMEOUT:-300}
GUNICORN_GRACEFUL_TIMEOUT=${GUNICORN_GRACEFUL_TIMEOUT:-60}
GUNICORN_WORKERS=${GUNICORN_WORKERS:-2}
# ASGI(FastAPI) では UvicornWorker を使用する
GUNICORN_WORKER_CLASS=${GUNICORN_WORKER_CLASS:-uvicorn.workers.UvicornWorker}
# WSGI 用ワーカー（sync 等）が環境変数で指定されていると FastAPI が TypeError で落ちる
case "${GUNICORN_WORKER_CLASS}" in
  sync|gevent|eventlet|gthread|tornado)
    echo "⚠️ GUNICORN_WORKER_CLASS=${GUNICORN_WORKER_CLASS} は FastAPI(ASGI) と非互換のため uvicorn.workers.UvicornWorker に切り替えます。"
    GUNICORN_WORKER_CLASS=uvicorn.workers.UvicornWorker
    ;;
esac

# ポート番号を環境変数から取得（Render.comでは自動設定される）
PORT=${PORT:-5000}

echo "🚀 Starting Gunicorn with the following settings:"
echo "   - Timeout: ${GUNICORN_TIMEOUT}s"
echo "   - Graceful Timeout: ${GUNICORN_GRACEFUL_TIMEOUT}s"
echo "   - Workers: ${GUNICORN_WORKERS}"
echo "   - Worker Class: ${GUNICORN_WORKER_CLASS}"
echo "   - Port: ${PORT}"

# コマンドライン引数でタイムアウトを明示的に指定
exec gunicorn \
    --bind 0.0.0.0:${PORT} \
    --workers ${GUNICORN_WORKERS} \
    --worker-class ${GUNICORN_WORKER_CLASS} \
    --timeout ${GUNICORN_TIMEOUT} \
    --graceful-timeout ${GUNICORN_GRACEFUL_TIMEOUT} \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --keep-alive 5 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --name medicine-recommend-app \
    main:app

