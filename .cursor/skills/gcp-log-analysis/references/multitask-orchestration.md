# Multitask オーケストレーション（gcp-log-analysis）

親エージェントが従う起動パターン。ユーザーが「multitask」「並列」「ユーザーごと」と言ったときも同じ。

## Step 0 — 差分取得（multitask 標準）

**JSON path が無い**、またはユーザーが「最新」「差分」「since last local」と言った場合、Wave A より前に必ず実行:

```bash
python scripts/prepare_gcp_log_analysis.py --since-last-local --service medicine-recommend-dev
```

- 成功 (`status: ready`) → `output_dir` を `<stem>` として Wave A/B へ（Step 1 は prepare 内で済み）
- `no_gap` → 最新である旨を報告。全量再取得が必要なら `--freshness 24h` または path 指定をユーザーに確認
- `gcloud` 未インストール / 認証エラー → ユーザーに SDK 設定を案内。path 指定があれば Step 0 スキップ可

**path あり** → Step 0 スキップ。`analyze_gcp_logs.py` のみ（または prepare に path を渡す）。

## 起動数の式

```
同時サブエージェント数 ≈ 4（Wave A 固定）+ min(セッション数, 20)（Wave B）
```

例: セッション 3 → 合計 7 エージェント。セッション 25 → 4 + 20 = 24（上位 20 セッションのみ深掘り）。

## Wave A — 固定 4（1 メッセージ・必須）

```text
Task × 4, run_in_background: true, subagent_type: generalPurpose
```

各 Task の description 例:

- `GCP log: infra_errors`
- `GCP log: performance_cost`
- `GCP log: conversation summary`
- `GCP log: integrations`

各 prompt に必ず含める:

```text
Full Repository Path: d:\Programing\medicine-recommend
Output dir: log/analysis/<stem>/
Read: sections/<files>.json, metadata.json
Write: log/analysis/<stem>/draft_<group_id>.md
Language: Japanese
Do NOT analyze individual sessions in depth (Wave B handles that).
```

## Wave B — セッション 1 件 = エージェント 1（1 メッセージ・必須）

CLI 後に `session_conversations.sessions` を読み、**リスト化してから**一括起動。

```text
Task × N, run_in_background: true, subagent_type: generalPurpose
（N = sessions.length、上限 20）
```

優先順位（上限超え時）:

1. `evaluation.overall_grade`: poor → needs_improvement → acceptable_with_issues → good
2. 同順位なら `evaluation.issue_count` 降順

各 Task の description 例: `GCP session: line_U20a3b...`

各 prompt に必ず含める:

```text
Full Repository Path: d:\Programing\medicine-recommend
Session JSON path: log/analysis/<stem>/sections/user_sessions.json
Target session_id: <exact session_id>
Read ONLY that session object inside session_conversations.sessions[].
Use conversation_history and every turn's conversation_history for context.
heuristic_signals are hints only — LLM makes final judgment.
If medicine_recommendation_review.eligible_for_advisor: follow medicine-recommendation-advisor skill.
Write: log/analysis/<stem>/draft_session_<safe_id>.md
Sections required:
  - Session metadata (channel, time_range, turn count)
  - **Full conversation table** (all turns): send time, reply time, user text, bot text, E2E, pipeline total, gap since prev turn
  - **Per-turn processing breakdown** from turns[].timing.phase_summary_ms and llm_calls (all turns, not excerpt)
  - Turn-by-turn LLM quality verdict with routing
  - Session overall grade (LLM) vs heuristic grade
  - Intent mismatches with root cause
  - Recommended actions
Also read pre-generated: log/analysis/<stem>/sessions/<safe_id>.md if present; merge or extend it.
Language: Japanese
```

### safe_session_id

`session_id` の `:` `/` `\` を `_` に置換。先頭 48 文字まで。例:

- `line:U20a3beee49563dcd07bb3dd0fc1ca32c` → `line_U20a3beee49563dcd07bb3dd0fc1ca32c`

## 親エージェントの禁止事項

- Wave A を 4 回に分けて直列起動しない
- セッション深掘りを親が全部やってサブエージェントを使わない
- Wave B をセッション数分のメッセージに分割して時間を空けない（可能な限り 1 メッセージで N 並列）

## ユーザー向け起動フレーズ（コピー可）

### 標準（差分自動取得 + 4 + セッション数）

```text
@gcp-log-analysis multitaskモードで解析して。
ローカル最新との差分を GCP から取得してから、Wave A 4エージェント並列 + セッションごとに追加エージェント並列。
service: medicine-recommend-dev
```

### 標準（path 指定・差分取得なし）

```text
@gcp-log-analysis multitaskモードで解析して。
Wave A 4エージェント並列 + セッションごとに追加エージェント並列。
path: c:\Users\yutok\Downloads\downloaded-logs-20260625-004004.json
```

### セッション深掘りを強調

```text
@gcp-log-analysis
downloaded-logs-20260625-004004.json を解析。
固定4並列に加え、ユーザー（session）ごとに1エージェントずつ立てて会話全体を評価して。
```

### 2 ログ比較 + multitask

```text
@gcp-log-analysis multitask
比較: log-A.json と log-B.json
各ログで 4+セッション数 エージェント並列 → 比較レポート
```

## マージ順

1. `draft_infra_errors.md`
2. `draft_performance_cost.md`
3. `draft_conversation_quality.md`
4. `draft_integrations.md`
5. `draft_session_*.md`（session_id アルファベット順）
6. 親がエグゼクティブサマリとアクションを上書き統合
