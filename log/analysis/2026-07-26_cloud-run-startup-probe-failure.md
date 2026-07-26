# Cloud Run startup probe 失敗（medicine-recommend-dev-00195-99t）

## 概要

- Build / Push 成功、Deploy で startup probe 失敗
- 対象 commit: `79f6f25`（UI 修正）。実害の根因は直前の `d42d494`（Local RAG）で lifespan に同期 BM25 warmup が追加されたこと

## 再現計測（ローカル）

| 項目 | 値 |
|------|-----|
| medicine chunks | 61,951 |
| concierge chunks | 207 |
| 同期 warmup 時間 | 約 47s（フル CPU） |
| import main RSS | ~120 MiB |
| warmup 後 RSS（1 worker） | ~240 MiB |
| 2 workers 想定 | ~480 MiB + master → **512Mi で OOM しやすい** |

Cloud Run startup probe（典型）: `failureThreshold=24 × periodSeconds=5` ≈ **120s**。  
CPU スロットリング下では 47s が伸び、lifespan 完了前に `/health` が応答できず probe 失敗。

## 修正

1. `main.py`: BM25 warmup を daemon スレッドで非同期化（`/health` をブロックしない）
2. `Dockerfile`: `GUNICORN_WORKERS=1`（512Mi でも OOM 回避。AWS はタスク定義で上書き）
3. `cloudbuild.yaml`: `--memory=1Gi`、`failureThreshold=36`（構成ファイル利用時）

## デプロイ経路メモ

今回の Cloud Build ログは Step 名が Build/Push/Deploy で、リポジトリ `cloudbuild.yaml`（write_build_meta 先行）とは異なる。  
GitHub 連携の自動生成ビルドの場合、`cloudbuild.yaml` の memory/probe は効かない → **コード側（lifespan + workers）が必須**。メモリが 512Mi のままならコンソールで 1Gi へ上げることを推奨。
