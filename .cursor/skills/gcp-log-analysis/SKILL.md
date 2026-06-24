---
name: gcp-log-analysis
description: >-
  Analyzes GCP Cloud Logging exports (downloaded-logs-*.json) for medicine-recommend
  Cloud Run. Runs deterministic extraction via scripts/analyze_gcp_logs.py, then
  parallel LLM interpretation of section JSON (errors, pipeline perf, LINE webhook,
  chat flow, DB, LLM cost, deploy revisions, user intent mismatches). Writes
  Markdown reports to log/analysis/. Use when the user attaches or paths GCP log
  JSON, asks to analyze production/dev logs, investigate 503/errors, or review
  chat quality from Cloud Run logs.
---

# GCP Log Analysis (medicine-recommend)

## When to use

User provides a **path** to `downloaded-logs-*.json` (GCP Console export) and wants automated analysis.

## Workflow overview

```
1. CLI extract  →  log/analysis/<stem>/sections/*.json
2. Parallel LLM  →  4 section groups (multitask / run_in_background)
3. Merge         →  log/analysis/YYYY-MM-DD_<stem>.md
```

## Step 1 — Deterministic extraction

Run from repo root:

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

## Step 2 — Parallel LLM analysis (multitask)

Launch **4 Task subagents in one message**, each with `run_in_background: true` and `subagent_type: generalPurpose`.

| Group ID | Section files | Focus |
|----------|---------------|-------|
| `infra_errors` | `errors_http.json`, `deploy_revision.json` | 4xx/5xx, 503 bursts, gunicorn SIGTERM noise vs real errors, revision/commit changes correlated with failures |
| `performance_cost` | `pipeline_perf.json`, `llm_cost.json` | Slow paths (web/line), security/triage waits, LLM cost hotspots, p95 latency |
| `conversation_quality` | `chat_flow.json`, `user_sessions.json` | **session_conversations**（ユーザー単位タイムライン）、ターンごとの routing 紐づけ、**自動検出された意図ずれ**（`intent_mismatches`）、セッション総合 grade |
| `integrations` | `line_webhook.json`, `db_neon.json`, `misc_signals.json` | LINE locks/duplicates, Neon/DB errors, budget/emergency/moderation signals |

### Subagent prompt template

Each subagent must:

1. Read the assigned `log/analysis/<stem>/sections/<name>.json` files.
2. Read `metadata.json` for service/environment/time range.
3. Cross-reference codebase when needed (`src/agents/`, `src/services/chat_response_service.py`, `src/services/session_manager.py`, LINE handlers).
4. Write **Japanese** analysis to `log/analysis/<stem>/draft_<group_id>.md` with:
   - Executive bullets (max 5)
   - Findings with timestamps and evidence
   - Severity: 🔴 critical / 🟡 warning / 🟢 info
   - Recommended actions (concrete file or config hints when possible)
5. For `conversation_quality` (**LLM が最終判定**):
   - Read `user_sessions.json` → `session_conversations.sessions`
   - **Every session** has `conversation_history` and each turn has `conversation_history` (prior turns) — use for context
   - `heuristic_signals` / `intent_mismatches` are **hints only**; LLM must re-judge all turns and session overall grade
   - Override `evaluation.overall_grade` in the report when LLM disagrees with heuristic grade (explain why)
   - Per session: strengths, weaknesses, **文脈を踏まえた総合評価**（繰り返し・前ターン無視など）
   - For turns with `medicine_recommendation_review.eligible_for_advisor`: load **`medicine-recommendation-advisor`** skill and evaluate top medicines if log events exist; otherwise note “推奨ログなし”
   - Link `turns[].routing` when explaining root cause

Do **not** wait for all subagents before starting Step 3 polling — use completion notifications.

## Step 3 — Merge final report

After all 4 drafts exist, merge into:

```
log/analysis/YYYY-MM-DD_<stem>.md
```

Use [references/report-template.md](references/report-template.md). Include:

1. Metadata table (source, service, time range, entry count, revisions)
2. Executive summary (5–10 lines)
3. Sections from the 4 groups (dedupe repeated SIGTERM deploy noise)
4. **Intent mismatch review** table from `intent_mismatches` (not all turns)
5. **Session evaluation** table + narrative for sessions with grade ≠ `good`
6. Prioritized action list

Delete or keep `draft_*.md` — prefer keeping drafts for audit.

## LLM-heavy interpretation rules

- **Final verdict = LLM**, not `heuristic_signals` or `turn_grade` from CLI.
- Prefer `conversation_history` + section JSON over raw JSON.
- `quality_metrics.json` summarizes trends; cite it in executive summary.
- Quote log evidence briefly (timestamp + message snippet); no huge dumps.
- Distinguish **benign deploy noise** (Worker SIGTERM during rollout) from **user-facing 503**.
- `service_name` in metadata determines dev vs prod; state which environment in the report.
- If `counseling_details` is empty but `chat_flow` has traces, note possible log level / export filter gap.

## Optional deep dive

If user asks for a specific `trace_id` or `session_id`:

1. Grep the **source JSON** for that id (shell `rg`), or narrow `chat_flow` trace.
2. Append an addendum section to the report.

## Related

- Ad-hoc prototype: `tmp_log_analysis.py` (superseded by this skill + CLI)
- Recommendation quality reviews: `medicine-recommendation-advisor` → `log/reviews/`
- Dev daily logs (local): `log/log/yyyy-mm-dd-n.md` (different format)
