# CodeBuild / AWS: Docker Hub 429 回避のため Public ECR ミラーを使用
FROM public.ecr.aws/docker/library/python:3.11-slim AS build-meta

WORKDIR /src

# CI（CodeBuild / Cloud Build）は .ci-commit-sha / build-arg で渡す。ローカルは deploy スクリプトが生成。
COPY scripts/write_build_meta.py scripts/
RUN mkdir -p static
COPY .ci-commit-sha /tmp/.ci-commit-sha
ARG GIT_COMMIT_DATE=
RUN COMMIT="$(tr -d '\n' < /tmp/.ci-commit-sha)" \
 && GIT_COMMIT="$COMMIT" GIT_COMMIT_DATE="${GIT_COMMIT_DATE:-$(date -u +%Y-%m-%d)}" \
    python3 scripts/write_build_meta.py

FROM public.ecr.aws/docker/library/python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off

WORKDIR /app

# 依存関係を先にインストールしてレイヤキャッシュを効かせる
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

# Local RAG コーパス — data/ 変更時のみ再実行（src/ 変更ではレイヤキャッシュを維持）
COPY scripts/build_medicine_kb_documents.py scripts/
COPY data/ data/
RUN python3 scripts/build_medicine_kb_documents.py

# 本番に必要なファイルのみコピー（docs の発表資料等は除外してイメージを軽量化）
COPY start.sh main.py ./
COPY config/ config/
COPY legacy/ legacy/
COPY src/ src/
COPY templates/ templates/
COPY static/ static/
RUN rm -f static/build-meta.json
COPY --from=build-meta /src/static/build-meta.json static/build-meta.json
COPY .ci-commit-sha /tmp/.ci-commit-sha
COPY scripts/write_build_meta.py scripts/
COPY scripts/write_changelog_digest.py scripts/
COPY docs/public/ docs/public/
COPY docs/concierge/ docs/concierge/
COPY docs/ops/ docs/ops/
COPY CHANGELOG.md ./

ARG GIT_COMMIT_DATE=
RUN COMMIT="$(tr -d '\n' < /tmp/.ci-commit-sha)" \
 && GIT_COMMIT="$COMMIT" GIT_COMMIT_DATE="${GIT_COMMIT_DATE:-$(date -u +%Y-%m-%d)}" \
    python3 scripts/write_build_meta.py \
 && python3 scripts/write_changelog_digest.py

# Cloud Run のデフォルトポート（環境変数 PORT が渡される）
# FastAPI は ASGI のため sync ワーカー不可（未設定時のフォールバック）
# Workers 既定 1: Local RAG BM25（~240MiB/worker）で 512Mi インスタンスの OOM を避ける。
# AWS ECS 等はタスク定義で GUNICORN_WORKERS=2 を上書き可能。
ENV PORT=8080 \
    GUNICORN_WORKER_CLASS=uvicorn.workers.UvicornWorker \
    GUNICORN_WORKERS=1

RUN chmod +x start.sh

# FastAPI（main:app）を Gunicorn + UvicornWorker で起動
CMD ["./start.sh"]
