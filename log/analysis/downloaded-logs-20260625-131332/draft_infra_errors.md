# Wave A — infra_errors 分析

**環境**: `medicine-recommend-dev`（本番 `medicine-recommend` は含まない）  
**ログ期間**: 2026-06-24T18:08:04Z 〜 2026-06-25T04:13:20Z（10,000 エントリ）  
**コミット**: `a7455d2bb00b2538316be114a876bf78f10f4544`（全期間同一）

---

## Executive Summary

- **ユーザー向け HTTP エラーはゼロ** — 4xx/5xx は 0 件。503 によるサービス不可は本ログ窓では検出されない。
- **リビジョン切替は 1 回** — `00122-44q` → `00123-bpf`（2026-06-25T02:44:09Z）。コード SHA は同一のため、設定・再デプロイのみの可能性が高い。
- **デプロイ直後の SIGTERM は正常なロールアウト** — 旧リビジョン worker への SIGTERM は新 revision 起動約 22 秒後。`errors_http` に 503 が無いため、ユーザー影響はないと判断。
- **Gunicorn worker の定期再起動** — デプロイ以外にも worker exit/boot が 3 回。`max_requests=1000` による循環またはインスタンス入替と整合。
- **`POST /api/chat/stream` が遅い** — 5 秒超が 4 件（平均 9.7s）。インフラ障害ではなくパイプライン遅延のシグナル（詳細は performance_cost グループへ）。

---

## Findings

### 1. HTTP エラー・テキストエラーなし

| 指標 | 値 |
|------|-----|
| `http_4xx_5xx_total` | 0 |
| `by_status` | （空） |
| `text_errors.count` | 0 |

**Severity**: 🟢 info

**根拠**: `sections/errors_http.json` — エクスポート窓全体で Cloud Run ロードバランサ／アプリ層の失敗応答は記録されていない。

---

### 2. リビジョン切替（デプロイ）

| 時刻 (UTC) | リビジョン | commit_sha |
|------------|-----------|------------|
| 2026-06-24T18:08:04Z（窓開始） | `medicine-recommend-dev-00122-44q` | `a7455d2…` |
| 2026-06-25T02:44:09Z | `medicine-recommend-dev-00123-bpf` | `a7455d2…` |
| 2026-06-25T02:44:23Z | `00123-bpf`（継続） | null |

**ログ件数**: 旧 revision 6,862 / 新 revision 3,135（`metadata.json`）

**Severity**: 🟢 info（計画デプロイ）

**解釈**:
- 同一 commit SHA のまま revision 番号のみ増加 → Cloud Build 再デプロイ、環境変数変更、またはトラフィック切替によるリビジョン再作成の典型パターン。
- 切替時刻 02:44:09Z に Gunicorn 起動ログ（Workers: 2, Timeout: 300s, Graceful: 60s）が出力。設定は `start.sh` の dev 既定と一致。

---

### 3. デプロイ SIGTERM vs ユーザー向け 503（区別）

**SIGTERM（良性・デプロイノイズ）**

| 時刻 (UTC) | 証拠 |
|------------|------|
| 2026-06-25T02:44:10Z | 新 revision で Gunicorn / worker pid 2, 3 が Boot |
| 2026-06-25T02:44:31Z | `[ERROR] Worker (pid:34) was sent SIGTERM!` |
| 2026-06-25T02:44:31Z | `[ERROR] Worker (pid:43) was sent SIGTERM!` |

- 旧 revision の worker（pid 34, 43）が新 revision 起動後に SIGTERM される。Cloud Run のローリング更新で期待される挙動。
- Gunicorn は SIGTERM を ERROR レベルで記録するが、**単体では障害ではない**（`config/gunicorn_config.py` / `start.sh` の `graceful_timeout=60s` 内での終了想定）。

**ユーザー向け 503**

- `errors_http.json` の `http_4xx_5xx_total: 0` — **本窓では 503 は検出されず**、デプロイ時刻（02:44 UTC）前後にユーザー向けサービス不可はないと判断。
- デプロイ中に in-flight の `POST /api/chat/stream` が切断された場合は 5xx に現れるが、今回の集計では該当なし。

**Severity**: 🟢 info（SIGTERM）/ 該当なし（503）

---

### 4. デプロイ以外の Gunicorn worker 循環

| 時刻 (UTC) | イベント |
|------------|----------|
| 2026-06-24T19:57:54Z | Worker exiting (pid:3) → Booting pid:31 |
| 2026-06-24T23:24:24Z | Worker exiting (pid:31) → Booting pid:34 |
| 2026-06-25T02:18:04Z | Worker exiting (pid:2) → Booting pid:43 |

**Severity**: 🟢 info

**解釈**: `start.sh` の `--max-requests 1000` による worker ローテーション、または Cloud Run インスタンスのスケール／ヘルスチェック入替。いずれも HTTP エラー増加と相関せず。

---

### 5. 遅延エンドポイント（インフラ障害ではないが注意）

| エンドポイント | 件数 (≥5s) | min | max | avg | p95 |
|----------------|-----------|-----|-----|-----|-----|
| `POST /api/chat/stream` | 4 | 8.39s | 11.91s | 9.68s | 11.91s |

**Severity**: 🟡 warning（UX・タイムアウトリスク）

**根拠**: `errors_http.json` → `slow_endpoints_ge_5s`。Gunicorn timeout 300s 内だが、クライアント側タイムアウトやストリーム体感遅延の可能性。原因切り分けは `pipeline_perf.json` / LLM レイテンシを参照。

---

## Recommended Actions

| 優先度 | アクション | 参照 |
|--------|-----------|------|
| 低 | **現状維持** — HTTP エラー・503 なし。dev 環境の計画デプロイは正常完了。 | — |
| 低 | デプロイ監視では **SIGTERM ERROR ログをアラート対象から除外**、または `revision` ラベルと相関して「ロールアウト中」フラグを付与。 | Cloud Logging フィルタ / アラートポリシー |
| 中 | `POST /api/chat/stream` の 8–12s 応答を追跡。Wave A `performance_cost` と合わせ、ボトルネック（LLM・DB・セキュリティチェック）を特定。 | `sections/pipeline_perf.json`, `src/services/chat_response_service.py` |
| 低 | 同一 SHA で revision のみ変わる場合、デプロイ理由（env 変更等）を Cloud Build / GitLab パイプライン履歴で記録しておくと次回分析が容易。 | `docs/ops/GITLAB_TEMPORARY_MIGRATION.md` |
| 参考 | 長時間ストリーム中のデプロイで切断リスクを下げる場合、`GUNICORN_GRACEFUL_TIMEOUT`（現 60s）と Cloud Run `terminationGracePeriodSeconds` の整合を確認。 | `start.sh`, `docs/ops/CLOUD_RUN_LLM_ENV.md` |

---

## データソース

- `log/analysis/downloaded-logs-20260625-131332/metadata.json`
- `log/analysis/downloaded-logs-20260625-131332/sections/errors_http.json`
- `log/analysis/downloaded-logs-20260625-131332/sections/deploy_revision.json`
- `log/analysis/downloaded-logs-20260625-131332/quality_metrics.json`（`infra.http_4xx_5xx_total: 0` で相互確認）
- コード参照: `start.sh`, `config/gunicorn_config.py`

*注: Gunicorn SIGTERM / worker 循環のタイムスタンプは `misc_signals.json`（integrations グループ）と突合してデプロイ文脈を補強。割当セクションの HTTP 集計結果は変更なし。*
