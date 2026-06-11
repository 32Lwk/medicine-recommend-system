FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off

WORKDIR /app

# 依存関係を先にインストールしてレイヤキャッシュを効かせる
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

# 本番に必要なファイルのみコピー（docs の発表資料等は除外してイメージを軽量化）
COPY start.sh main.py ./
COPY config/ config/
COPY src/ src/
COPY templates/ templates/
COPY static/ static/
COPY data/ data/
COPY docs/プライバシーポリシー.md \
     docs/免責事項・利用規約.md \
     docs/医薬品相談先.md \
     docs/アプリ概要.md \
     docs/
COPY docs/concierge/ docs/concierge/

# Cloud Run のデフォルトポート（環境変数 PORT が渡される）
# FastAPI は ASGI のため sync ワーカー不可（未設定時のフォールバック）
ENV PORT=8080 \
    GUNICORN_WORKER_CLASS=uvicorn.workers.UvicornWorker

RUN chmod +x start.sh

# FastAPI（main:app）を Gunicorn + UvicornWorker で起動
CMD ["./start.sh"]

