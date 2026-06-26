---
name: gcp-log-analysis
description: >-
  Analyzes GCP Cloud Logging exports (downloaded-logs-*.json) for medicine-recommend
  Cloud Run. Runs scripts/prepare_gcp_log_analysis.py (optional incremental fetch),
  scripts/analyze_gcp_logs.py, then multitask parallel agents: 4 fixed section groups
  plus one background agent per user session. Writes Markdown to log/analysis/. Use when
  the user paths GCP log JSON, asks for multitask log analysis, per-user session review,
  dev/prod incident investigation, or incremental log sync since last local export.
---

# GCP Log Analysis (medicine-recommend)

## When to use

User provides a **path** to `downloaded-logs-*.json` (GCP Console export) and wants automated analysis.

**Multitask モード**でパス未指定、または「差分」「最新」「since last local」と言われた場合は、Step 0 でローカル最新カバレッジ以降を GCP から自動取得する。

## Workflow overview

```
0. (multitask / 差分) prepare  →  log/raw/downloaded-logs-*.json（incremental）
1. CLI extract  →  log/analysis/<stem>/
2. Wave A       →  4 Task subagents (fixed groups, run_in_background, one message)
3. Wave B       →  N Task subagents (one per session / user, run_in_background, one message)
4. Merge        →  log/analysis/YYYY-MM-DD_<stem>.md
```

詳細オーケストレーション: [references/multitask-orchestration.md](references/multitask-orchestration.md)

## Step 0 — Incremental fetch (multitask / 差分のみ)

ローカル baseline は次を参照する（**より新しい `time_range.end` を採用**）:

- `log/analysis/*/metadata.json`
- `log/raw/export_state.json`（`export_gcp_logs.py` / `prepare_gcp_log_analysis.py` が更新）

### 自動取得（推奨）

repo root から:

```bash
python scripts/prepare_gcp_log_analysis.py --since-last-local --service medicine-recommend-dev
```

| 終了コード / `status` | 意味 | 親エージェントの動作 |
|----------------------|------|---------------------|
| `ready` | 差分取得 + Step 1 完了 | 出力 JSON の `output_dir` / `manifest` で Wave A/B へ |
| `no_gap` | ローカルが既に最新 | ユーザーに報告。必要なら `--freshness` や明示 path を確認 |
| `empty` | 差分期間にログ 0 件 | 報告して終了 |
| `dry_run` | filter / 時間窓のみ | gcloud 実行前の確認用 |

**baseline 無し**（初回）: `--fallback-freshness 24h`（既定）で直近 24 時間を取得。

**本番**を対象にする場合は `--service medicine-recommend` を明示。

### エクスポートのみ（Step 1 前に手動確認したい場合）

```bash
python scripts/export_gcp_logs.py --since-last-local --service medicine-recommend-dev
python scripts/analyze_gcp_logs.py log/raw/downloaded-logs-....json
```

### パス指定時

ユーザーが JSON path を渡した場合は **Step 0 をスキップ**（既存フロー）。比較解析・再解析はそのファイルをそのまま使う。

## Step 1 — Deterministic extraction

Run from repo root（Step 0 で `prepare` 済みなら **再実行不要**。未実行時のみ）:

```bash
python scripts/analyze_gcp_logs.py "<absolute-or-relative-path-to-log.json>"
```

Read `log/analysis/<stem>/manifest.json` and `quality_metrics.json`. Do **not** load the raw multi-MB JSON into context unless a section file is missing.

## Multi-log comparison (on demand)

When the user provides **two paths**, or when comparing deploy before/after would help, ask once then:

1. Run CLI on each log → separate `log/analysis/<stem>/` dirs
2. Compare `quality_metrics.json`, `deploy_revision.json`, `errors_http.json`
3. Diff `session_conversations.sessions_by_grade` and new `issue_type` counts
4. Note revision / commit-sha changes between files

Do not auto-compare unless user requests or agent judges it necessary (e.g. “デプロイ後に悪化”).

## Step 2 — Multitask parallel analysis (必須)

**Multitask モードを使う。** 親エージェントは解析の大部分を自分で抱え込まず、Task サブエージェントに分散する。

### Wave A — 固定 4 エージェント（必ず 1 メッセージで同時起動）

次の **4 つを同じターンで** `Task` 起動する。すべて:

- `subagent_type: generalPurpose`
- `run_in_background: true`

| Group ID | Section files | Draft 出力 |
|----------|---------------|------------|
| `infra_errors` | `errors_http.json`, `deploy_revision.json` | `draft_infra_errors.md` |
| `performance_cost` | `pipeline_perf.json`, `llm_cost.json` | `draft_performance_cost.md` |
| `conversation_quality` | `chat_flow.json`, `user_sessions.json` | `draft_conversation_quality.md`（セッション横断サマリのみ） |
| `integrations` | `line_webhook.json`, `db_neon.json`, `misc_signals.json` | `draft_integrations.md` |

`conversation_quality` エージェントは **セッション別の深掘りをしない**（Wave B に任せる）。横断サマリ・`quality_metrics`・共通パターンのみ。

### Wave B — セッション（ユーザー）ごと追加エージェント

Step 1 後、`user_sessions.json` → `session_conversations.sessions` の件数を数える。

**ルール:**

| 条件 | 動作 |
|------|------|
| 毎回 | `sessions` の **各 `session_id` に 1 サブエージェント** |
| 同一メッセージ | Wave B の全サブエージェントを **1 ターンでまとめて起動**（`run_in_background: true`） |
| 上限 | 同時起動 **最大 20 セッション**。超える場合は `evaluation.overall_grade` が悪い順・`issue_count` 多い順に 20 件まで。残りは親が要約のみ |
| 出力 | `draft_session_<safe_session_id>.md`（`:` `/` は `_` に置換。例: `line_U20a3beee...`） |

各セッションサブエージェントの必須作業:

1. 当該 `session` オブジェクトのみ読む（`conversation_history`, 全 `turns`）
2. `heuristic_signals` は参考。LLM が **全ターン再判定** + **セッション総合評価**
3. `physical_recommendation_summary` / `medicine_recommendation_review` があれば `medicine-recommendation-advisor` を参照
4. 日本語で `draft_session_*.md` を書く（時系列ターン表、意図ずれ、原因、推奨アクション）

### 完了待ちとマージ

1. Wave A + Wave B の完了通知を待つ（バックグラウンド完了を消費）
2. 欠けた draft があれば親が補完
3. Step 3 で最終 Markdown に統合（**各 session の transcript 全文・処理時間表を省略しない**）

CLI は `log/analysis/<stem>/sessions/<safe_id>.md` にセッション transcript を自動生成する。Wave B / 最終レポートはこれを参照・拡張する。

### Step 1 で組み立てるセッション transcript（2026-06 改善）

`build_session_conversations` は次の **3 ソース** をマージして全ターンを復元する:

| ソース | 内容 | 優先度 |
|--------|------|--------|
| `counseling_detail` | ユーザー入力・ボット返信全文・timestamp | 最高 |
| `counseling_detail.conversation_history` | 同一レコード内の先行ターン（絵文字・挨拶など） | 中 |
| `chat_flow.exported_traces` | `user_message` + ルーティング/遅延（返信本文なしの場合あり） | 補完 |

- `counseling_detail` が **0 件でも** `chat_flow` に `session_id` があるセッションは **trace-only セッション** として `sessions[]` に含める。
- 返信本文が無いターンは `response_missing: true` とし、transcript に「ログ未記録」と明記する。
- **アプリ側（2026-06）**: 全経路で `finalize_pipeline_response` が `counseling_detail` を **非同期**（`ThreadPoolExecutor`）で全文出力。応答パスはブロックしない。デプロイ後は `response_missing` ターンが減る。
- `quality_metrics.json` の `trace_only_session_count` / `chat_flow_trace_count` でギャップを確認できる。

**Wave B / マージ時の必須ルール**: `sessions/<safe_id>.md` と `turns[]` の **全ターン** を最終レポートに転記する（1ターンに潰さない）。`response_missing` ターンはルーティング・遅延のみ評価可。

### Subagent prompt template（Wave A 共通）

1. Read the assigned `log/analysis/<stem>/sections/<name>.json` files.
2. Read `metadata.json` for service/environment/time range.
3. Cross-reference codebase when needed (`src/agents/`, `src/services/chat_response_service.py`, `src/services/session_manager.py`, LINE handlers).
4. Write **Japanese** analysis to `log/analysis/<stem>/draft_<group_id>.md` with:
   - Executive bullets (max 5)
   - Findings with timestamps and evidence
   - Severity: 🔴 critical / 🟡 warning / 🟢 info
   - Recommended actions (concrete file or config hints when possible)
5. Wave A `conversation_quality` only: cross-session summary; **do not** write per-session deep dives.

Do **not** block the parent on Wave A before launching Wave B — start Wave B in the **next turn immediately after** reading session count (or same turn if session list is already known).

## Step 3 — Merge final report

After **all Wave A + Wave B** drafts exist, merge into:

```
log/analysis/YYYY-MM-DD_<stem>.md
```

Use [references/report-template.md](references/report-template.md). Include:

1. Metadata table (source, service, time range, entry count, revisions)
2. Executive summary (5–10 lines)
3. Sections from the 4 groups (dedupe repeated SIGTERM deploy noise)
4. **Intent mismatch review** table from `intent_mismatches` (not all turns)
5. **Session evaluation** — one subsection per `draft_session_*.md` (Wave B)
6. Prioritized action list

Delete or keep `draft_*.md` — prefer keeping drafts for audit.

## LLM-heavy interpretation rules

- **Final verdict = LLM**, not `heuristic_signals` or `turn_grade` from CLI.
- Prefer `conversation_history` + section JSON over raw JSON.
- `quality_metrics.json` summarizes trends; cite it in executive summary.
- Quote log evidence briefly (timestamp + message snippet); no huge dumps.
- Distinguish **benign deploy noise** (Worker SIGTERM during rollout) from **user-facing 503**.
- `service_name` in metadata determines dev vs prod; state which environment in the report.
- If `counseling_details` is empty but `chat_flow` has traces, note possible log level / export filter gap — **trace-only sessions are still exported** with `response_missing` turns; recommend enabling `counseling_detail` on greeting/emoji/concierge routes for full bot text.

## Optional deep dive

If user asks for a specific `trace_id` or `session_id`:

1. Grep the **source JSON** for that id (shell `rg`), or narrow `chat_flow` trace.
2. Append an addendum section to the report.

## Related

- Incremental export: `scripts/prepare_gcp_log_analysis.py`, `scripts/export_gcp_logs.py`
- Ad-hoc prototype: `tmp_log_analysis.py` (superseded by this skill + CLI)
- Recommendation quality reviews: `medicine-recommendation-advisor` → `log/reviews/`
- Dev daily logs (local): `log/log/yyyy-mm-dd-n.md` (different format)
