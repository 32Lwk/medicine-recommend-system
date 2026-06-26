# GCP Log Analysis Report

## メタデータ

| 項目 | 値 |
|------|-----|
| ソースファイル | |
| 環境 (service) | |
| 期間 | |
| エントリ数 | |
| 主な revision / commit | |
| セッション数 | counseling N / trace-only M / chat_flow トレース T |

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

### セッション別 — 会話 transcript（必須・全ターン）

**各 session について以下を必ず含める**（抜粋禁止。`sessions/<safe_id>.md` と同等の詳細度）。

#### セッション: `<session_id>`

1. **会話サマリ表**（全ターン）

| # | ユーザー送信（推定） | ボット返信時刻 | ユーザー入力 | ボット返信（全文または十分な長さ） | E2E | pipeline total | 前ターンからの間隔 | ソース |
|---|---------------------|----------------|--------------|-----------------------------------|-----|----------------|-------------------|--------|

`response_missing` の行はボット返信列に「（ログ未記録）」と書く。`turn_source`（counseling_detail / conversation_history / chat_flow）をソース列に記載。

2. **ターン別処理時間**（全ターン・`turns[].timing` を使用）

各ターンごとに:

| フェーズ | 時間 |
|---------|------|
| POST→セキュリティ完了 | … |
| セキュリティ | … |
| トリアージ | … |
| オーケストレーター | … |
| Concierge 応答生成 | … |

3. **LLM 呼び出し**（ターンごと・あれば path / latency / cost）

4. **評価**: input_labels, routing（intent/triage/trace_id）, LLM verdict, 原因

データソース: `sections/user_sessions.json` の `turns[].timing`, `turns[].routing`, `sessions/<safe_id>.md`

### 意図ずれ・品質問題

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

- 抽出: `log/analysis/<stem>/`
- セッション transcript: `sessions/<safe_session_id>.md`
- manifest: `manifest.json`
