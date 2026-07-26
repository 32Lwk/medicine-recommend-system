# CodeBuild / AWS: Docker Hub 429 回避のため Public ECR ミラーを使用
FROM public.ecr.aws/docker/library/python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off

WORKDIR /app

# 依存関係を先にインストールしてレイヤキャッシュを効かせる
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

# 本番に必要なファイルのみコピー（docs の発表資料等は除外してイメージを軽量化）
COPY start.sh main.py ./
COPY config/ config/
COPY legacy/ legacy/
COPY src/ src/
COPY templates/ templates/
COPY static/ static/
COPY scripts/write_build_meta.py scripts/
COPY scripts/write_changelog_digest.py scripts/
COPY scripts/build_medicine_kb_documents.py scripts/
COPY data/ data/
COPY docs/public/ docs/public/
COPY docs/concierge/ docs/concierge/
COPY docs/ops/ docs/ops/
COPY CHANGELOG.md ./

# Local RAG コーパス（build/ は .gitignore — イメージ内で生成）
RUN python3 scripts/build_medicine_kb_documents.py

# Cloud Run 等 .git なし環境向け: ビルド引数から Git メタを ENV と static/build-meta.json に焼き込む
# リポジトリ同梱の static/build-meta.json がある場合は COPY 済み。未設定時のみビルド引数で上書き。
ARG GIT_COMMIT=
ARG GIT_COMMIT_DATE=
ARG COMMIT_SHA=
ENV GIT_COMMIT=${GIT_COMMIT:-${COMMIT_SHA}} \
    GIT_COMMIT_DATE=${GIT_COMMIT_DATE}
RUN python3 scripts/write_build_meta.py \
 && python3 scripts/write_changelog_digest.py

# Cloud Run のデフォルトポート（環境変数 PORT が渡される）
# FastAPI は ASGI のため sync ワーカー不可（未設定時のフォールバック）
ENV PORT=8080 \
    GUNICORN_WORKER_CLASS=uvicorn.workers.UvicornWorker

RUN chmod +x start.sh

# FastAPI（main:app）を Gunicorn + UvicornWorker で起動
CMD ["./start.sh"]

