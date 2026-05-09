#!/bin/bash
# Gunicorn起動スクリプト
# コマンドライン引数でタイムアウトを明示的に指定

# 環境変数からタイムアウトを取得（デフォルト: 120秒）
GUNICORN_TIMEOUT=${GUNICORN_TIMEOUT:-120}
GUNICORN_GRACEFUL_TIMEOUT=${GUNICORN_GRACEFUL_TIMEOUT:-30}
GUNICORN_WORKERS=${GUNICORN_WORKERS:-2}
# ASGI(FastAPI) では UvicornWorker を使用する
GUNICORN_WORKER_CLASS=${GUNICORN_WORKER_CLASS:-uvicorn.workers.UvicornWorker}

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

