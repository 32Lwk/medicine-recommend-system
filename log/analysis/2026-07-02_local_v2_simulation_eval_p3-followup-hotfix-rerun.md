# Chat Pipeline v2 シミュレーション意図評価 (2026-07-02)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-07-02T02:57:25.130265+00:00
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
| `1782961045158280845886` | concierge-followup-01 | 2 | PASS | 2/2 | 4 | Concierge:4 | 技術スタックは？→OK; 技術面を詳しく→OK |
| `1782961073388630286351` | concierge-followup-02 | 2 | PASS | 2/2 | 4 | Concierge:4 | 技術スタックは？→OK; もっと詳しく→OK |
| `1782961101143250306195` | concierge-followup-03 | 2 | PASS | 2/2 | 4 | Concierge:4 | プリンシプルオブプログラミングとは？→OK; 具体例を教えて→OK |
| `1782961121567414745595` | concierge-followup-04 | 2 | REVIEW | 2/2 | 4 | Concierge:4 | Sage Terraceとは→OK; もう少し教えて→OK |
| `1782961149256044827428` | concierge-followup-05 | 2 | PASS | 2/2 | 4 | Concierge:4 | APIの仕組みを教えて→OK; SSEについて→OK |
| `1782961177246937590788` | concierge-followup-06 | 2 | PASS | 2/2 | 4 | Concierge:4 | インフラ構成を教えて→OK; Cloud Runは？→OK |
| `1782961202919885999899` | concierge-followup-07 | 2 | PASS | 2/2 | 4 | Concierge:4 | 医薬品推奨の仕組み→OK; rule_basedの詳細→OK |
| `1782961232194561245205` | concierge-followup-08 | 2 | PASS | 2/2 | 4 | Concierge:4 | 対応言語は？→OK; 英語でも使えますか→OK |

## 要確認 — ターン別トランスクリプト

### concierge-followup-04 (`1782961121567414745595`)
- failures: missing_context_kw:Sage
#### Turn 1
- **User**: Sage Terraceとは
- **Bot** (`concierge_architecture`, 12045ms):

Sage Terraceは、症状や相談内容に応じて複数の専門担当が連携し、必要な案内へ振り分けるチャット型の市販薬相談ツールです。

質問の内容に合わせて、挨拶や案内、症状の整理、市販薬候補の提示、緊急時の誘導などを役割分担して進めます。

市販薬の候補は、自由に薬名を作るのではなく、症状や条件をもとにルールベースで選ばれます。

必要なら、仕組みや技術構成ももう少し詳しく説明できます。

#### Turn 2
- **User**: もう少し教えて
- **Bot** (`concierge_architecture`, 13298ms):

複数の担当が、質問の種類に応じて順番に案内を受け持つ仕組みです。

たとえば、雑談や使い方の案内、症状の整理、市販薬候補の確認、緊急性の判断を、それぞれに得意な流れでつなぎます。

市販薬の候補は、雰囲気で決めるのではなく、症状・年齢・注意点などをもとにルールで絞り込みます。

画面側はHTML/CSS/バニラJSで作られ、やり取りや状況はJSONL形式のログで記録される設計です。

必要なら次に、「どういう流れで質問が進むのか」か「技術構成をもっと具体的に」どちらかに絞って説明できます。


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
    "legacy": 16
  },
  "shadow_with_fever_context_flag": 0,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 0,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 16,
  "dispatch_handled": 14,
  "dispatch_unhandled": 2,
  "dispatch_success_rate_pct": 87.5,
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
| concierge-followup-01 | `1782961045158280845886` |
| concierge-followup-02 | `1782961073388630286351` |
| concierge-followup-03 | `1782961101143250306195` |
| concierge-followup-04 | `1782961121567414745595` |
| concierge-followup-05 | `1782961149256044827428` |
| concierge-followup-06 | `1782961177246937590788` |
| concierge-followup-07 | `1782961202919885999899` |
| concierge-followup-08 | `1782961232194561245205` |
