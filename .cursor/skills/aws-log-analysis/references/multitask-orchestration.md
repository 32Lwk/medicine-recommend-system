# Multitask オーケストレーション（aws-log-analysis）

親エージェントが従う起動パターン。GCP 版（gcp-log-analysis）と同一構造。AWS 固有の差分のみここに記載。

## Step 0 — 差分取得（multitask 標準）

**JSON path が無い**、またはユーザーが「最新」「差分」「since last local」と言った場合:

```bash
python scripts/prepare_aws_log_analysis.py --since-last-local --service medicine-recommend
```

- 成功 (`status: ready`) → `output_dir` を `<stem>` として Wave A/B へ
- `no_gap` → 最新である旨を報告
- `aws` 未インストール / 認証エラー → `AWS_PROFILE=medicine-recommend-dev` と IAM を案内

**path あり** → Step 0 スキップ。

## 起動数の式

```
同時サブエージェント数 ≈ 4（Wave A 固定）+ min(セッション数, 20)（Wave B）
```

## Wave A — 固定 4（1 メッセージ・必須）

各 Task の description 例:

- `AWS log: infra_errors`
- `AWS log: performance_cost`
- `AWS log: conversation summary`
- `AWS log: integrations`

各 prompt に必ず含める:

```text
Full Repository Path: <repo root>
Output dir: log/analysis/<stem>/
Platform: aws (CloudWatch / ECS)
Read: sections/<files>.json, metadata.json
Write: log/analysis/<stem>/draft_<group_id>.md
Language: Japanese
Do NOT analyze individual sessions in depth (Wave B handles that).
Note: HTTP errors may be text-only (no httpRequest field).
```

## Wave B — セッション 1 件 = エージェント 1

gcp-log-analysis の Wave B プロンプトと同一。description 例: `AWS session: line_U20a3b...`

## ユーザー向け起動フレーズ（コピー可）

### 標準（差分自動取得）

```text
@aws-log-analysis multitaskモードで解析して。
ローカル最新との差分を AWS CloudWatch から取得してから、Wave A 4エージェント並列 + セッションごとに追加エージェント並列。
service: medicine-recommend
```

### path 指定

```text
@aws-log-analysis multitaskモードで解析して。
Wave A 4エージェント並列 + セッションごとに追加エージェント並列。
path: log/raw/downloaded-aws-logs-20260725-120000.json
```

## マージ順

1. `draft_infra_errors.md`
2. `draft_performance_cost.md`
3. `draft_conversation_quality.md`
4. `draft_integrations.md`
5. `draft_session_*.md`（session_id アルファベット順）
6. 親がエグゼクティブサマリとアクションを上書き統合
