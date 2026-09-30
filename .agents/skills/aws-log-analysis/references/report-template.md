# AWS Log Analysis Report

## メタデータ

| 項目 | 値 |
|------|-----|
| プラットフォーム | aws |
| ソースファイル | |
| Log Group | |
| Region | |
| ECS Service | |
| 期間 | |
| エントリ数 | |
| 主な task definition / commit | |
| セッション数 | counseling N / trace-only M / chat_flow トレース T |

## エグゼクティブサマリー

（5–10行。最重要の障害・性能・会話品質問題を述べる）

## インフラ・エラー（infra_errors）

### HTTP / アプリ ERROR

CloudWatch には GCP 型 `httpRequest` が無い場合あり。text_errors と gunicorn/ALB ログを参照。

### ECS デプロイ境界

task definition revision のタイムライン。

## 性能・コスト（performance_cost）

### PIPELINE_PERF

### LLM コスト

## 会話品質（conversation_quality）

（gcp-log-analysis report-template と同一: セッションサマリ表、全ターン transcript、意図ずれ表）

## 連携・その他（integrations）

### LINE webhook

### DB (Neon)

### その他シグナル

## 優先アクション

| 優先度 | アクション | 根拠 |
|--------|-----------|------|

## 付録

- 生ログ: `log/raw/downloaded-aws-logs-*.json`
- セクション JSON: `log/analysis/<stem>/sections/`
- Draft: `log/analysis/<stem>/draft_*.md`
