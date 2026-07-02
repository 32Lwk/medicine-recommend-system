# Chat Pipeline v2 シミュレーション意図評価 (2026-07-02)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-07-02T02:53:07.123638+00:00
- セッション数: 8 / 総ターン: 16
- 自動合格: 7 / 要確認: 1
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 8
- counseling_detail マッチ行: 16
- route ログマッチ行: 32

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1782960787152015191840` | concierge-followup-01 | 2 | PASS | 2/2 | 4 | Concierge:4 | 技術スタックは？→OK; 技術面を詳しく→OK |
| `1782960815807965288976` | concierge-followup-02 | 2 | PASS | 2/2 | 4 | Concierge:4 | 技術スタックは？→OK; もっと詳しく→OK |
| `1782960843755518784689` | concierge-followup-03 | 2 | PASS | 2/2 | 4 | Concierge:4 | プリンシプルオブプログラミングとは？→OK; 具体例を教えて→OK |
| `1782960869542695199133` | concierge-followup-04 | 2 | REVIEW | 2/2 | 4 | Concierge:4 | Sage Terraceとは→OK; もう少し教えて→OK |
| `1782960897195829581386` | concierge-followup-05 | 2 | PASS | 2/2 | 4 | Concierge:4 | APIの仕組みを教えて→OK; SSEについて→OK |
| `1782960928513239590871` | concierge-followup-06 | 2 | PASS | 2/2 | 4 | Concierge:4 | インフラ構成を教えて→OK; Cloud Runは？→OK |
| `1782960954447568411766` | concierge-followup-07 | 2 | PASS | 2/2 | 4 | Concierge:4 | 医薬品推奨の仕組み→OK; rule_basedの詳細→OK |
| `1782960986301540882933` | concierge-followup-08 | 2 | PASS | 2/2 | 4 | Concierge:4 | 対応言語は？→OK; 英語でも使えますか→OK |

## 要確認 — ターン別トランスクリプト

### concierge-followup-04 (`1782960869542695199133`)
- failures: missing_context_kw:Sage
#### Turn 1
- **User**: Sage Terraceとは
- **Bot** (`concierge_architecture`, 11712ms):

Sage Terraceは、この市販薬相談ツールの内部で使う仕組みや案内名のようなもので、会話内容に応じて適切な担当へ振り分けるための考え方を指します。

複数の専門担当が連携するマルチエージェント構成で、雑談や説明、症状の案内、緊急時の誘導などを分担します。

市販薬の候補を出す場面では、薬名を自由に作るのではなく、症状や条件をもとにルールベースで選ぶ仕組みです。

#### Turn 2
- **User**: もう少し教えて
- **Bot** (`concierge_architecture`, 13620ms):

この仕組みは、1人が全部答えるのではなく、内容に応じて複数の専門担当に振り分けて案内する作りです。

たとえば、ふつうの説明や雑談、症状の相談、緊急性の高い案内のように、得意な役割を分けています。

市販薬を案内する場面では、薬名を自由に作るのではなく、症状や条件をもとにルールに沿って候補を絞る方式です。

なので、会話の目的に合わせて“説明する人”と“選ぶ仕組み”が分かれている、というイメージです。


## IntentRouter メトリクス

```json
{
  "shadow_total": 16,
  "shadow_mismatch": 0,
  "shadow_mismatch_rate_pct": 0.0,
  "shadow_improvement_mismatch": 0,
  "shadow_improvement_mismatch_rate_pct": 0.0,
  "shadow_regression_mismatch": 0,
  "shadow_regression_mismatch_rate_pct": 0.0,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 16
  },
  "shadow_by_primary_route": {
    "Concierge": 16
  },
  "shadow_by_resolved_by": {
    "legacy": 15,
    "llm": 1
  },
  "shadow_with_fever_context_flag": 0,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 0,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 16,
  "dispatch_handled": 15,
  "dispatch_unhandled": 1,
  "dispatch_success_rate_pct": 93.75,
  "dispatch_by_handler": {
    "concierge_agent": 16
  },
  "mismatch_samples": []
}
```

## Admin 確認

- [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) → サイドバー「**v2テストのみ**」を ON
- 検索: `v2-test` または `session_id`（下表）

| scenario_id | session_id |
|-------------|------------|
| concierge-followup-01 | `1782960787152015191840` |
| concierge-followup-02 | `1782960815807965288976` |
| concierge-followup-03 | `1782960843755518784689` |
| concierge-followup-04 | `1782960869542695199133` |
| concierge-followup-05 | `1782960897195829581386` |
| concierge-followup-06 | `1782960928513239590871` |
| concierge-followup-07 | `1782960954447568411766` |
| concierge-followup-08 | `1782960986301540882933` |
