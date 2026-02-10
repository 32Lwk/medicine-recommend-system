FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off

WORKDIR /app

# 依存関係を先にインストールしてレイヤキャッシュを効かせる
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリコードをコピー
COPY . .

# Cloud Run のデフォルトポート（環境変数 PORT が渡される）
ENV PORT=8080

# Gunicorn 起動スクリプトを実行可能に
RUN chmod +x start.sh

# Flask アプリ(app:app)を Gunicorn で起動
CMD ["./start.sh"]

