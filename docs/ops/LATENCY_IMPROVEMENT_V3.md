# 返信遅延改善計画 v3 — 実装正本

**実施日**: 2026-07-28  
**分析正本**: [`log/analysis/2026-07-28_downloaded-logs-20260726-20260728-slow-response.md`](../../log/analysis/2026-07-28_downloaded-logs-20260726-20260728-slow-response.md)

## 目的

GCP dev ログで特定した 180〜351s ハング・429 輻輳・構造 LLM 累積を、**推奨精度・返信品質を維持**したまま解消する。

## KPI（目標）

| メトリクス | 目標 |
|-----------|------|
| 通常ターン p95 | < 25s |
| Physical 推奨 p95 | < 60s |
| SSE 180s+ ハング | 0 |

## インフラ（Cloud Run）

| 項目 | dev | 本番 |
|------|-----|------|
| memory | 1Gi | 1Gi |
| CPU | 1 | **2** |
| GUNICORN_WORKERS | 2 | 2 |
| concurrency | 10 | 10 |
| max-instances | 2 | 2 |
| min-instances | 0 | 0 |

`cloudbuild.yaml` の deploy 引数で設定。`[skip deploy]` または docs/log のみ変更時は deploy スキップ。

## 環境変数（レイテンシ）

| 変数 | 値 | 用途 |
|------|-----|------|
| `CHAT_STREAM_TIMEOUT_SEC` | 120 | SSE ワーカー処理タイムアウト |
| `CHAT_STREAM_ORPHAN_MAX_SEC` | 120 | 切断後 orphan 上限 |
| `LATENCY_TRIAGE_SINGLE_CALL` | 1 | triage stage1+2 統合 |
| `LATENCY_EXPLAIN_CACHE` | 1 | explain Redis キャッシュ |
| `LATENCY_SCORE_PARALLEL` | 1 | rule_based スコア並列 |
| `LATENCY_RECO_PARALLEL` | 1 | 推奨候補並列 |

詳細: [`CLOUD_RUN_LLM_ENV.md`](CLOUD_RUN_LLM_ENV.md)

## Redis（Upstash — GCP dev + 本番）

- cross-worker `chat_inflight`（SET NX）
- triage / explain キャッシュ read-through
- `REDIS_URL=rediss://...`（Secret Manager）
- セットアップ: [`scripts/setup-gcp-upstash-redis.sh`](../../scripts/setup-gcp-upstash-redis.sh)
- AWS staging: ElastiCache 維持

## 主要コード変更

| 領域 | ファイル | 内容 |
|------|---------|------|
| SSE / in_flight | `chat_stream.py`, `chat_inflight.py` | タイムアウト時 `end_chat_job`、orphan 120s、stale persist |
| Redis | `redis_cache.py`, `triage_cache.py`, `explanation_generator.py` | cross-worker ロック・キャッシュ |
| パイプライン | `chat_post_pipeline.py`, `medicine_qa_routing.py` | ルート先行、focus_llm スキップ、計測細分化 |
| session 混線 | `session_sid.py`, `sse_emit.py`, `main.js` | sid 束縛、StreamSink クリア、activeSubmitSid |
| LLM dedup | `request_scope_cache.py`, `meta_triage.py` | ターン内キャッシュ |
| フロント | `processing_status.js`, `main.js`, `chat_sse.js` | poll 停止、backoff、Abort、マルチタブ |
| shadow / timeout | `shadow.py`, `medicine_context_handlers.py` | shadow 非同期、product_image 30s |

## デプロイ前検証

```powershell
python scripts/verify_latency_plan.py
python scripts/verify_latency_plan.py --smoke-v2   # app.py :5000 起動後
```

## デプロイ後確認

1. Cloud Run ログで `Workers: 2` を確認
2. GCP ログ再分析（`prepare_gcp_log_analysis.py --since-last-local`）
3. `session_sid_mismatch` / `SSE chat worker timeout` の件数確認
