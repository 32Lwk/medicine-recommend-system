---
name: aws-log-analysis
description: >-
  Analyzes AWS CloudWatch Logs exports (downloaded-aws-logs-*.json) for medicine-recommend
  ECS staging. Runs scripts/prepare_aws_log_analysis.py (optional incremental fetch),
  scripts/analyze_aws_logs.py, then multitask parallel agents: 4 fixed section groups
  plus one background agent per user session. Writes Markdown to log/analysis/. Use when
  the user paths AWS log JSON, asks for AWS/CloudWatch log analysis, multitask log analysis,
  per-user session review, staging incident investigation, or incremental log sync since
  last local export.
---

# AWS Log Analysis (medicine-recommend)

## When to use

User provides a **path** to `downloaded-aws-logs-*.json` (CloudWatch export) and wants automated analysis.

**Multitask モード**でパス未指定、または「差分」「最新」「since last local」と言われた場合は、Step 0 でローカル最新カバレッジ以降を AWS CloudWatch から自動取得する。

## Workflow overview

```
0. (multitask / 差分) prepare  →  log/raw/downloaded-aws-logs-*.json（incremental）
1. CLI extract  →  log/analysis/<stem>/
2. Wave A       →  4 Task subagents (fixed groups, run_in_background, one message)
3. Wave B       →  N Task subagents (one per session / user, run_in_background, one message)
4. Merge        →  log/analysis/YYYY-MM-DD_<stem>.md
```

詳細オーケストレーション: [references/multitask-orchestration.md](references/multitask-orchestration.md)

## Step 0 — Incremental fetch (multitask / 差分のみ)

ローカル baseline は次を参照する（**より新しい `time_range.end` を採用**）:

- `log/analysis/*/metadata.json`（`platform: "aws"` または `source_name` が `downloaded-aws-logs-` 始まり）
- `log/raw/aws_export_state.json`（`export_aws_logs.py` / `prepare_aws_log_analysis.py` が更新）

### 自動取得（推奨）

repo root から:

```bash
python scripts/prepare_aws_log_analysis.py --since-last-local --service medicine-recommend
```

| 終了コード / `status` | 意味 | 親エージェントの動作 |
|----------------------|------|---------------------|
| `ready` | 差分取得 + Step 1 完了 | 出力 JSON の `output_dir` / `manifest` で Wave A/B へ |
| `no_gap` | ローカルが既に最新 | ユーザーに報告。必要なら `--freshness` や明示 path を確認 |
| `empty` | 差分期間にログ 0 件 | 報告して終了 |
| `dry_run` | filter / 時間窓のみ | aws 実行前の確認用 |

**baseline 無し**（初回）: `--fallback-freshness 24h`（既定）で直近 24 時間を取得。

**Log Group 明示**が必要な場合: `--log-group /ecs/medicine-recommend`（`--service medicine-recommend` と同等）。

**AWS 認証**: ローカルは `AWS_PROFILE=medicine-recommend-dev`（[scripts/lib/aws_common.sh](../../scripts/lib/aws_common.sh) 参照）。

### エクスポートのみ（Step 1 前に手動確認したい場合）

```bash
python scripts/export_aws_logs.py --since-last-local --service medicine-recommend
python scripts/analyze_aws_logs.py log/raw/downloaded-aws-logs-....json
```

### パス指定時

ユーザーが JSON path を渡した場合は **Step 0 をスキップ**（既存フロー）。

## Step 1 — Deterministic extraction

Run from repo root（Step 0 で `prepare` 済みなら **再実行不要**。未実行時のみ）:

```bash
python scripts/analyze_aws_logs.py "<absolute-or-relative-path-to-log.json>"
```

Read `log/analysis/<stem>/manifest.json` and `quality_metrics.json`. Do **not** load the raw multi-MB JSON into context unless a section file is missing.

## Multi-log comparison (on demand)

GCP 版と同様。2 つの export を比較する場合:

1. Run CLI on each log → separate `log/analysis/<stem>/` dirs
2. Compare `quality_metrics.json`, `deploy_revision.json`, `errors_http.json`
3. Diff `session_conversations.sessions_by_grade` and new `issue_type` counts
4. Note ECS task definition revision changes between files

## Step 2 — Multitask parallel analysis (必須)

**Multitask モードを使う。** 親エージェントは解析の大部分を自分で抱え込まず、Task サブエージェントに分散する。

### Wave A — 固定 4 エージェント（必ず 1 メッセージで同時起動）

| Group ID | Section files | Draft 出力 |
|----------|---------------|------------|
| `infra_errors` | `errors_http.json`, `deploy_revision.json` | `draft_infra_errors.md` |
| `performance_cost` | `pipeline_perf.json`, `llm_cost.json` | `draft_performance_cost.md` |
| `conversation_quality` | `chat_flow.json`, `user_sessions.json` | `draft_conversation_quality.md` |
| `integrations` | `line_webhook.json`, `db_neon.json`, `misc_signals.json` | `draft_integrations.md` |

Wave A `conversation_quality` は **セッション別深掘りをしない**（Wave B に任せる）。

### Wave B — セッションごと追加エージェント

Step 1 後、`user_sessions.json` → `session_conversations.sessions` の件数を数える。

| 条件 | 動作 |
|------|------|
| 毎回 | 各 `session_id` に 1 サブエージェント |
| 同一メッセージ | Wave B 全サブエージェントを 1 ターンで起動（`run_in_background: true`） |
| 上限 | 同時起動 **最大 20 セッション** |
| 出力 | `draft_session_<safe_session_id>.md` |

各セッションサブエージェントの必須作業は gcp-log-analysis と同一（全ターン再判定、`medicine-recommendation-advisor` 参照、日本語 draft）。

## Step 3 — Merge final report

After **all Wave A + Wave B** drafts exist, merge into:

```
log/analysis/YYYY-MM-DD_<stem>.md
```

Use [references/report-template.md](references/report-template.md).

## AWS-specific interpretation rules

- **環境**: `metadata.platform == "aws"`、`log_group`（例: `/ecs/medicine-recommend`）、`region`（例: `ap-northeast-1`）をレポートに明記。
- **HTTP エラー**: CloudWatch には GCP の `httpRequest` フィールドが無い。`errors_http.json` の text_errors と、アプリログ内の gunicorn/ALB 形式を優先。ALB アクセスログは S3 別途（本 skill 対象外）。
- **デプロイ境界**: ECS task definition revision（`task_definitions` / `deploy_revision.json`）と CodePipeline ログを参照。SIGTERM / gunicorn worker 再起動は benign deploy noise として GCP 版と同様に扱う。
- **アプリログ形式**: GCP Cloud Run と同一 Python logging 形式のため、会話品質・PIPELINE_PERF・counseling_detail 解析は共通ロジック。
- **Final verdict = LLM**, not heuristic grades.

## Optional deep dive

If user asks for a specific `trace_id` or `session_id`:

1. Grep the **source JSON** for that id (shell `rg`), or narrow `chat_flow` trace.
2. Append an addendum section to the report.

## Related

- Incremental export: `scripts/prepare_aws_log_analysis.py`, `scripts/export_aws_logs.py`
- GCP 同等 skill: `gcp-log-analysis`
- AWS infra: `docs/ops/AWS_INFRA.md`
- Recommendation quality: `medicine-recommendation-advisor` → `log/reviews/`
