# ベースイメージ: 既定は AWS Public ECR（Docker Hub 429 回避）。
# GCP Cloud Build は --build-arg PYTHON_BASE=mirror.gcr.io/library/python:3.11-slim を渡す。
ARG PYTHON_BASE=public.ecr.aws/docker/library/python:3.11-slim
FROM ${PYTHON_BASE} AS build-meta

WORKDIR /src
ARG GIT_COMMIT=
ARG GIT_COMMIT_DATE=
ARG COMMIT_SHA=
ENV GIT_COMMIT=${GIT_COMMIT:-${COMMIT_SHA}} \
    GIT_COMMIT_DATE=${GIT_COMMIT_DATE}

# CI（CodeBuild / Cloud Build）は build-arg で渡す。ローカルは static/build-meta.json をフォールバック。
# CodeBuild 等は .git を含まないため COPY .git は行わない（write_build_meta.py が env / 既存 JSON を参照）。
COPY scripts/write_build_meta.py scripts/
COPY static/build-meta.json static/
# ARG を RUN 直前に再宣言 — cache-from 利用時も GIT_COMMIT 変更で RUN を無効化
ARG GIT_COMMIT=
ARG GIT_COMMIT_DATE=
ENV GIT_COMMIT=${GIT_COMMIT} GIT_COMMIT_DATE=${GIT_COMMIT_DATE}
# CI では repo 同梱の build-meta.json（古いコミットの可能性）を使わない
RUN COMMIT="${GIT_COMMIT:-${COMMIT_SHA}}" \
 && if [ -n "$COMMIT" ]; then echo '{}' > static/build-meta.json; fi \
 && GIT_COMMIT="$COMMIT" python3 scripts/write_build_meta.py

ARG PYTHON_BASE=public.ecr.aws/docker/library/python:3.11-slim
FROM ${PYTHON_BASE}

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off

WORKDIR /app

# 依存関係を先にインストールしてレイヤキャッシュを効かせる
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

# Local RAG コーパス — data/ または ingredient_synonym_registry 変更時に再実行
COPY scripts/build_medicine_kb_documents.py scripts/
COPY data/ data/
COPY src/ src/
RUN python3 scripts/build_medicine_kb_documents.py

# 本番に必要なファイルのみコピー（docs の発表資料等は除外してイメージを軽量化）
COPY start.sh main.py ./
COPY config/ config/
COPY legacy/ legacy/
COPY templates/ templates/
COPY static/ static/
COPY --from=build-meta /src/static/build-meta.json static/build-meta.json
COPY scripts/write_build_meta.py scripts/
COPY scripts/write_changelog_digest.py scripts/
COPY docs/public/ docs/public/
COPY docs/concierge/ docs/concierge/
COPY docs/ops/ docs/ops/
COPY CHANGELOG.md ./

# build-arg が渡された場合は build-meta ステージの結果を上書きする
ARG GIT_COMMIT=
ARG GIT_COMMIT_DATE=
ARG COMMIT_SHA=
ENV GIT_COMMIT=${GIT_COMMIT:-${COMMIT_SHA}} \
    GIT_COMMIT_DATE=${GIT_COMMIT_DATE}
# ARG を RUN 直前に再宣言 — cache-from 利用時も GIT_COMMIT 変更で RUN を無効化
ARG GIT_COMMIT=
ARG GIT_COMMIT_DATE=
ENV GIT_COMMIT=${GIT_COMMIT} GIT_COMMIT_DATE=${GIT_COMMIT_DATE}
RUN COMMIT="${GIT_COMMIT:-${COMMIT_SHA}}" \
 && if [ -n "$COMMIT" ]; then echo '{}' > static/build-meta.json; fi \
 && GIT_COMMIT="$COMMIT" python3 scripts/write_build_meta.py \
 && python3 scripts/write_changelog_digest.py

# Cloud Run のデフォルトポート（環境変数 PORT が渡される）
# FastAPI は ASGI のため sync ワーカー不可（未設定時のフォールバック）
# Workers 既定 1: ローカル 512Mi 向け OOM 回避。Cloud Run は cloudbuild.yaml が 1Gi + GUNICORN_WORKERS=2 で上書き。
ENV PORT=8080 \
    GUNICORN_WORKER_CLASS=uvicorn.workers.UvicornWorker \
    GUNICORN_WORKERS=1

RUN chmod +x start.sh

# FastAPI（main:app）を Gunicorn + UvicornWorker で起動
CMD ["./start.sh"]
