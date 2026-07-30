# GCP Log Analysis Report — 改善デプロイ後比較（dev / 本番）

## メタデータ

| 項目 | dev（改善後ウィンドウ） | 本番（72h 窓） |
|------|------------------------|----------------|
| ソース | `downloaded-logs-20260728-20260729-20260729-043016.json` | `downloaded-logs-20260726-20260729-20260729-043138.json` |
| 環境 | `medicine-recommend-dev` | `medicine-recommend` |
| 期間 | 2026-07-28 06:21 UTC 〜 07-29 04:30 UTC（22h） | 2026-07-26 05:17 UTC 〜 07-29 03:43 UTC（72h） |
| エントリ数 | 36,987 | 26,100 |
| 主 revision | `00228-dsp`（commit `e909a8c`） | `00068-xbz` / `00089-gc6` 等 20 revision |
| セッション | counseling 8 / trace-only 0 / chat_flow 22 | counseling 11 / trace-only 0 / chat_flow 25 |

---

## エグゼクティブサマリー

1. **dev は改善前比でレイテンシ中央値が改善**（PIPELINE_PERF 中央値 **19.5s → 14.9s**、正常系 **15.6s → 14.4s**）。HTTP **429 は 18件 → 0件**、**SSE 180s タイムアウトは 6件 → 0件**。
2. **ただし dev には Gunicorn Workers=2 が未反映** — 起動ログはすべて **`Workers: 1`**（11回）。コードデプロイ（`e909a8c`）はされているが **`GUNICORN_WORKERS=2` の env デプロイが dev に未到達**の可能性が高い。
3. **本番は Workers=2 確認済み**。07-28 06:00 UTC 以降の PIPELINE_PERF は **n=2、中央値 20.9s、120s 超 0件** と安定。改善前（07-28 以前）は **500s 級 SSE orphan が 4件**。
4. **新たなボトルネック**: dev で **Physical 推奨 315s**（`1785258775748832445132`）— SSE orphan ではなく **`rb_scoring` 91s + `rb_explain_batch` 196s**（LLM 計測 0 回 = explain タイムアウト/ハング疑い）。
5. **構造的課題は継続**: `medicine_qa/focus_llm` が dev **20/55（36%）**、本番 **69/105（66%）** の LLM 呼び出しを占有。
6. **DB（Neon）・LINE は問題なし**。本番 HTTP 429 は **2件のみ**（dev 以前の 18件から大幅改善）。
7. **課題のレイヤー移動**: Cloud Run HTTP 429 は解消した一方、**OpenAI API 429 が ERROR 259件**（07-29 01:17 / 01:41 UTC）。**LINE 試験セッション（JST 10:17〜）と時間帯が重なる** — `focus_llm` enrichment 17件、triage/intent 各4件。
8. **本番 07-27 の orphan 4件（458〜503s）** は LLM ~15s 後に ~7分空白 — 07-28 06:00 UTC 以降は **max 24s** に収束。ただし post-deploy サンプル **n=2** のみで継続監視要。

---

## 改善前後比較（dev）

| 指標 | 改善前（07-26〜28） | 改善後（07-28〜29） | 判定 |
|------|---------------------|---------------------|------|
| PIPELINE_PERF 件数 | 14 | 23 | トラフィック増 |
| total_ms 中央値 | 19.5s | **14.9s** | ✅ 改善 |
| total_ms 平均 | 77.8s | **27.7s** | ✅ 改善 |
| 正常系（<120s）中央値 | 15.6s | **14.4s** | ✅ 微改善 |
| 120s 超 | 3件（最大 351s） | **1件**（315s） | ✅ 改善 |
| POST /api/chat/stream p95 | **182.5s** | **33.4s** | ✅ 大幅改善 |
| POST /api/chat/stream max | **182.8s** | **121.1s** | ✅ 改善 |
| SSE 180s timeout | **6件** | **0件** | ✅ 解消 |
| Cloud Run HTTP 429 | **18件** | **0件** | ✅ 解消 |
| OpenAI API 429（ERROR） | 1（OOM 等） | **259件** | ⚠️ レイヤー移動 |
| Gunicorn Workers | 1 | **1（未変更）** | ⚠️ 要デプロイ |

---

## 改善前後比較（本番）

| 指標 | 07-28 06:00 以前 | 07-28 06:00 以降 | 判定 |
|------|------------------|------------------|------|
| PIPELINE_PERF | n=14, 中央値 **33.6s** | n=2, 中央値 **20.9s** | ✅ 改善 |
| 120s 超 | **4件**（07-27、458〜503s） | **0件** | ✅ 解消 |
| SSE 180s timeout | 1件（07-27 09:00 UTC） | 0件 | ✅ |
| Gunicorn Workers | 2 | 2 | ✅ |
| HTTP 429 | 2件（sessions / activity） | 0件 | 🟢 |
| メモリ OOM | 15件（07-26〜27） | 0件 | 🟡 要監視 |
| CRITICAL WORKER TIMEOUT | 8件（07-26 のみ） | 0件 | ✅ |

---

## インフラ・エラー

### dev

| ステータス | 件数 | 備考 |
|-----------|------|------|
| 404 | 10 | apple-touch-icon / robots.txt（ボット） |
| 429 | **0** | 改善前 18件から解消 |
| 5xx | 0 | |

- デプロイ: 6 revision（`00222`〜`00228`）、`00228-dsp` が 32,001 エントリ（86.5%）で ~12.5h 安定稼働
- **OpenAI API 429 — ERROR 259件**（Cloud Run HTTP 429 とは別レイヤー）:

| 発生源 | 件数 |
|--------|------|
| `openai/_base_client.py`（共通） | 234 |
| `medicine_qa_focus_llm.py` | 17 |
| `llm_triage.py` | 4 |
| `intent_router_llm.py` | 4 |

| 時刻 (UTC) | 内容 |
|------------|------|
| 07-29 01:17:02〜01:17:13 | 高密度 burst（40件超 / 11秒） |
| 07-29 01:41:30〜01:41:33 | 第2クラスタ（~20件 / 3秒） |

→ `00228-dsp` 安定稼働 ~9.5h 後の発生のため、デプロイ副作用ではなく **throughput 向上に伴う TPM/RPM 上限接触** と判断。詳細: [`draft_infra_errors.md`](downloaded-logs-20260728-20260729-20260729-043016/draft_infra_errors.md)

### 本番

| ステータス | 件数 |
|-----------|------|
| 404 | 46 |
| 405 | 10 |
| 422 | 2 |
| 429 | **2** |
| 5xx | 0 |

- Gunicorn **CRITICAL WORKER TIMEOUT ×8**（07-26 のみ）、**メモリ OOM ×15**（07-26〜27、`00068`/`00069` 期）
- 07-28 以降の新規 CRITICAL timeout / OOM は未確認

**07-27 SSE orphan 4件**（`rb_scoring` ~53s 後に ~7分空白、LLM 計測 ~15s で終了）:

| 時刻 (UTC) | session_id | total_ms |
|------------|------------|----------|
| 07-27 10:52 | `1785149022180487798100` | 502,596 |
| 07-27 11:11 | `1785150228497408585586` | 474,558 |
| 07-27 11:31 | `1785151386548951630839` | 499,619 |
| 07-27 11:50 | `1785152564413894809137` | 458,944 |

→ 詳細: [`draft_performance_cost.md`](downloaded-logs-20260726-20260729-20260729-043138/draft_performance_cost.md)

---

## 性能・コスト

### dev — PIPELINE_PERF（23件）

| 指標 | 値 |
|------|-----|
| 中央値 | 14.9s |
| 平均 | 27.7s |
| p95（chat/stream HTTP） | 33.4s |
| 最大 | **315.6s** |

**315s 異常の内訳**（session `1785258775748832445132`）:

| フェーズ | 時間 | 割合 |
|---------|------|------|
| triage + safety + medicine_qa_route | 10.4s | 3% |
| nlu_batch | 2.8s | 1% |
| rb_missing_info | 2.2s | 1% |
| **rb_scoring_only** | **91.0s** | **29%** |
| **rb_explain_batch** | **196.0s** | **62%** |
| LLM 計測 | 0s | — |

→ **SSE orphan ではなく Physical 推奨の rule-based scoring / explain batch がボトルネック**。dev LLM コスト **55回 / ¥3.33**（PRE: 48回 / ¥2.48）。詳細: [`draft_performance_cost.md`](downloaded-logs-20260728-20260729-20260729-043016/draft_performance_cost.md)

### 本番 — PIPELINE_PERF（16件）

| 指標 | 全期間 | 07-28 以降のみ |
|------|--------|---------------|
| 中央値 | 41.2s | **20.9s** |
| 最大 | 502.6s | 24.0s |
| 120s 超 | 4 | 0 |

500s 級 4件はすべて **07-27**（上表）。`POST /api/chat/stream` 全期間 p95 **184s** / max **301s** は Before 期の長尾部が支配。

**After 2件**（Concierge greeting、LLM 2回/ターン）: 17.8s / 24.0s — rule-based フェーズなし。

本番 LLM: **105回 / ¥3.02** / 合計レイテンシ 144s。

### LLM コスト

| 環境 | 呼び出し | 合計レイテンシ | 最多パス |
|------|---------|---------------|---------|
| dev | 55 | 80.6s | focus_llm 20（36%） |
| 本番 | 105 | 144.4s | focus_llm 69（66%） |

---

## 連携（integrations）

| 項目 | dev AFTER | 本番 72h |
|------|-----------|----------|
| Neon DB | 安定（ERROR 0） | 安定（`channel_binding` WARNING のみ） |
| Redis triage_cache | hit **1回** | ログなし |
| LINE Webhook | **5 req / 全 200**（p95 15.7s） | **0 req** |
| SSE 180s timeout | **0** | **1**（07-27 09:00 UTC） |
| OpenAI API 429 | **~234件**（LINE 試験時 burst） | **0** |
| Cloud Run HTTP 429 | **0** | **2** |
| Gunicorn Workers | **1**（起動 11回） | **2** |

### Neon DB

- dev / 本番とも接続失敗 **0件**。`session_db_read` 中央値 **<10ms** — ボトルネックではない
- 本番: `channel_binding=require` 自動除去 WARNING は起動時のみ（接続自体は成功）

### Redis / Upstash

- dev: `triage_cache event=hit reason=redis` **1件**（hit=3, miss=0）、障害なし
- 本番: triage_cache ログ **0件**（設定差分またはサンプル不足）

### LINE Webhook

- dev: **5リクエスト・全 200**（同一 userId `U20a3beee...`）。07-29 JST 10:16〜10:43 に集中 — **OpenAI 429 burst と時間帯重複**
- 本番: **0リクエスト**（Web チャネルのみ）

詳細: [`draft_integrations.md`（dev）](downloaded-logs-20260728-20260729-20260729-043016/draft_integrations.md) / [`draft_integrations.md`（本番）](downloaded-logs-20260726-20260729-20260729-043138/draft_integrations.md)

---

## 会話品質サマリー

### dev（8セッション）

| grade | 件数 |
|-------|------|
| good | 6 |
| acceptable_with_issues | 2 |

- heuristic mismatch: `greeting_to_non_greeting` ×2（warning）
- Physical 推奨ログ 88件（テスト活発）
- LINE セッション 1（`line:U20a3beee...`）— grade good

### 本番（11セッション）

| grade | 件数 |
|-------|------|
| good | 11 |

- heuristic mismatch **0件**
- Physical advisor hook 6セッション

---

## 優先アクション

| 優先 | アクション | 対象 |
|------|-----------|------|
| 🔴 P0 | **OpenAI 429 制御** — 全 LLM 経路でリトライ/backoff 統一、`focus_llm` 並列 enrichment の逐次化またはバッチサイズ制限 | dev |
| 🔴 P0 | **dev に `GUNICORN_WORKERS=2` を cloudbuild デプロイ** — 現状 Workers=1 のまま | dev |
| 🔴 P0 | **315s Physical 異常の調査** — `rb_explain_batch` 196s / LLM 0回。`EXPLAIN_BATCH_HARD_TIMEOUT_SEC` ログ確認 | dev |
| 🟡 P1 | **本番 post-deploy 72h ウォッチ** — orphan 再発・120s 超・OOM 監視（現状 n=2） | 本番 |
| 🟡 P1 | **orphan キャンセル** — SSE 切断後の rule-based 後半処理を abort | 本番 |
| 🟡 P1 | **focus_llm バッチ化** — dev 36% / 本番 66% の LLM | 両方 |
| 🟡 P1 | stream p95 / HTTP 429 / OpenAI 429 を同一ダッシュボード化 | dev |
| 🟢 P2 | Neon `channel_binding=require` を接続文字列から除去（本番 WARNING 削減） | 本番 |
| 🟢 P2 | dev `min-instances=1` でコールドスタート評価 | dev |

---

## データソース

- dev 分析: `log/analysis/downloaded-logs-20260728-20260729-20260729-043016/`
- 本番分析: `log/analysis/downloaded-logs-20260726-20260729-20260729-043138/`
- 改善前 baseline: `log/analysis/downloaded-logs-20260726-20260728-20260728-044951/`
- Wave A ドラフト（dev）: `draft_infra_errors.md`, `draft_performance_cost.md`, `draft_integrations.md`
- Wave A ドラフト（本番）: `draft_performance_cost.md`, `draft_integrations.md`
- 取得: `scripts/prepare_gcp_log_analysis.py --since-last-local`（dev）/ `--fallback-freshness 72h`（本番初回）

---

*Generated: 2026-07-29. Wave A: [infra errors](04f7fa97-92fe-4863-8686-481675b0d231), [dev performance](86dfaf43-42b1-4084-9b38-a6b521977951), [prod performance](c342df33-4584-4f78-ac38-59228f06a1da), [integrations](008fff65-c25a-4f0c-b92c-c0a7051f164a). Skill: gcp-log-analysis.*
