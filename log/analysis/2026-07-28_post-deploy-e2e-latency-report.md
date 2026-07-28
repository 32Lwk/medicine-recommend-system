# 返信遅延改善 v3 — デプロイ後 E2E・速度レポート

**日付**: 2026-07-28  
**コミット**: `d24f4f7`（feat: 返信遅延改善 v3）  
**実施者**: Cursor Agent（デプロイ監視 + E2E + GCP ログ解析）

---

## 1. デプロイ結果

| 環境 | Cloud Build ID | 状態 | 新リビジョン | トリガー |
|------|----------------|------|-------------|---------|
| **dev** | `c9298f35-2854-4a84-a480-ff04fc47c9cd` | SUCCESS | `medicine-recommend-dev-00222-v5z` | GitLab `main` push |
| **本番** | `17e4506f-fb31-4a1c-8f62-88c05d2fce16` | SUCCESS | `medicine-recommend-00087-fsw` | GitHub `main` push |

- dev URL: https://medicine-recommend-dev-4jnmo2x4wa-an.a.run.app/
- 本番 URL: https://medicine-recommend-4jnmo2x4wa-an.a.run.app/
- Cloud Run リソース: **memory=1Gi**, **concurrency=10**, **max-instances=2**（dev CPU=1 / 本番 CPU=2）

### デプロイ前後比較（dev ログ `deploy_revision.json`）

| 時刻 (UTC) | リビジョン | commit |
|------------|-----------|--------|
| 06:05:03 | `medicine-recommend-dev-00222-v5z` | `d24f4f7` ← **今回** |
| 05:43:44 | `medicine-recommend-dev-00221-5pc` | `91ead57` |

---

## 2. E2E 実施（dev 向け 3 シナリオ）

`scripts/routing_e2e_live_runner.py` を dev Cloud Run に対して実行。

| # | シナリオ ID | カテゴリ | 入力 | 期待ルート | 結果 | 応答時間 |
|---|------------|---------|------|-----------|------|---------|
| 1 | `tech_gitlab_github_diff` | Concierge | GitlabとGithubの違いは？ | Concierge | **PASS** | **26.3s** |
| 2 | `tech_stack_casual` | Concierge | このアプリ何で動いてるの？ | Concierge | **PASS** | **16.9s** |
| 3 | `symptom_polite_sore_throat` | Physical | のどが痛くてつらいです | Physical (sage_reco) | **PASS** | **67.5s** |

**精度所見**

- Concierge 2 件: ルート・kind とも期待どおり。医薬品 Q&A への誤ルーティングなし。
- Physical 1 件: `sage_reco` 経路で推奨フロー完走。内容は症状に沿った案内。
- 参考: `symptom_casual_headache`（「頭バキバキ…」）は **初回ターンが greeting 扱い** で render=sage_status となり E2E 期待と不一致（**レイテンシ問題ではなくルーティング仕様**）。GCP ログ上は triage が Physical/headache と正しく分類（`dialogue_route_shadow` mismatch=false）。

レポート原文:

- `log/analysis/2026-07-28_local_post-deploy-e2e-dev-concierge.md`
- `log/analysis/2026-07-28_local_post-deploy-e2e-dev-stack2.md`（全 23 シナリオ中 21 PASS）

---

## 3. GCP ログ解析（デプロイ後 ~2h）

**ソース**: `log/raw/downloaded-logs-20260728-20260728-20260728-062153.json`（108MB — GitHub 100MB 制限のため raw はローカルのみ、解析成果物は push 済み）  
**期間**: 2026-07-28T04:49:21Z 〜 2026-07-28T06:21:53Z（incremental）  
**分析出力**: `log/analysis/downloaded-logs-20260728-20260728-20260728-062153/`

### 3.1 速度 KPI（v3 目標との照合）

| 指標 | デプロイ前（7/26–28 分析） | デプロイ後（本ログ） | v3 目標 | 判定 |
|------|---------------------------|---------------------|---------|------|
| POST `/` p95 | 180s 級ハングあり | **66.7s** | 通常 p95 < 25s | ⚠️ 改善、目標未達 |
| pipeline total_ms p95 (web) | — | **61.1s** | Physical p95 < 60s | ⚠️ 境界 |
| 180s ハング | 複数 | **0 件** | 0 | ✅ |
| HTTP 429 | 複数 | **0 件** | 0 | ✅ |
| HTTP 4xx/5xx | — | **0 件** | — | ✅ |

**POST `/` レイテンシ分布**（`errors_http.json` slow_endpoints）:

| 統計 | 値 (秒) |
|------|--------|
| count | 21 |
| median | 17.8 |
| avg | 27.9 |
| p95 | 66.7 |
| max | 67.4 |

**pipeline_perf (web channel, n=20)**:

| 統計 | total_ms |
|------|----------|
| median | 15,229 |
| avg | 24,279 |
| p95 | 61,061 |
| max | 65,496 |

### 3.2 精度・品質シグナル

| 指標 | 値 |
|------|-----|
| セッション数 | 19 |
| heuristic_mismatch | **0** |
| 会話 grade=good | 19/19 |
| Physical advisor hook | 8 セッション |

### 3.3 残課題

1. **Physical フル推奨 p95 ~61–67s**: rule_based + explain バッチが支配的（最遅 65.5s の内訳: `rb_explain_batch_done` ≈ 63s）。`LATENCY_*` フラグは有効だが、コールド NLU バッチが依然ボトルネック。
2. **Gunicorn Workers ログ**: 起動ログに `Workers: 1` が残存。`GUNICORN_WORKERS=2` の反映要確認（Cloud Run env は deploy 済み）。
3. **口語症状の初回 greeting**: 「頭バキバキ…」等、短い口語入力が concierge_greeting になるケースは別途 triage 調整候補。

---

## 4. ローカル回帰（デプロイ前実施・参考）

| テスト | 結果 |
|--------|------|
| `verify_latency_plan.py` | 107 passed |
| local v2 YAML (138 ターン) | p50 4.5s / p95 23.2s / max 27.9s / ≥180s **0** |

本番 Cloud Run はコールドスタート・Neon レイテンシ・並行負荷の影響でローカルより遅い。

---

## 5. 結論

| 項目 | 評価 |
|------|------|
| **デプロイ** | dev + 本番とも SUCCESS、`d24f4f7` 反映済み |
| **180s ハング解消** | ✅ デプロイ後ログで 0 件 |
| **429 解消** | ✅ 0 件 |
| **E2E 精度（3 件）** | ✅ 3/3 PASS |
| **速度 KPI** | ⚠️ Concierge ~17–26s は良好。Physical フル推奨は p95 ~61–67s で目標ギリギリ超過 |

**推奨フォローアップ**

1. `min-instances=1` でコールドスタート影響を分離計測
2. Gunicorn Workers=2 の起動確認（`gcloud run services describe` env + 起動ログ）
3. Physical 初回口語入力の triage → Physical 直行率向上（精度 issue、v3 スコープ外）

---

## 参照

- 技術正本: [`docs/ops/LATENCY_IMPROVEMENT_V3.md`](../../docs/ops/LATENCY_IMPROVEMENT_V3.md)
- CHANGELOG: [`CHANGELOG.md`](../../CHANGELOG.md) § 2026-07-28
- デプロイ前分析: [`log/analysis/2026-07-28_downloaded-logs-20260726-20260728-slow-response.md`](2026-07-28_downloaded-logs-20260726-20260728-slow-response.md)
