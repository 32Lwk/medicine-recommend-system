# GCP Log Analysis Report

## メタデータ

| 項目 | 値 |
|------|-----|
| ソースファイル | |
| 環境 (service) | |
| 期間 | |
| エントリ数 | |
| 主な revision / commit | |

## エグゼクティブサマリー

（5–10行。最重要の障害・性能・会話品質問題を述べる）

## インフラ・エラー（infra_errors）

### HTTP 異常

### テキスト ERROR

### デプロイ境界

## 性能・コスト（performance_cost）

### PIPELINE_PERF

### LLM コスト

## 会話品質（conversation_quality）

### セッション総合評価サマリー

| session_id | channel | ターン数 | 総合 grade | critical | warning | 要約 |
|------------|---------|----------|------------|----------|---------|------|

grade: `good` / `acceptable_with_issues` / `needs_improvement` / `poor`

### セッション別詳細（問題のあるセッション優先）

各セッションについて:

1. **時系列ターン一覧**（user_input → input_labels → routing → turn_grade）
2. **セッション全体の強み / 弱み**（`evaluation.strengths` / `weaknesses`）
3. **文脈を踏まえた総合コメント**（繰り返し挨拶、説明後の「えっ？」など）

### 意図ずれ・品質問題（自動検出）

`user_sessions.intent_mismatches` を使用:

| 時刻 | session_id | ユーザー入力 | issue_type | 深刻度 | 原因仮説 |
|------|------------|--------------|------------|--------|----------|

### 遅い trace（≥8s）

## 連携・その他（integrations）

### LINE webhook

### DB / Neon

### その他シグナル

## 推奨アクション

1. 🔴
2. 🟡
3. 🟢

## 付録

- 抽出ディレクトリ: `log/analysis/<stem>/`
- セッション JSON: `sections/user_sessions.json` → `session_conversations`
- manifest: `manifest.json`
