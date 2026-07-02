# Chat Pipeline v2 シミュレーション意図評価 (2026-07-02)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-07-02T07:15:47.321530+00:00
- セッション数: 32 / 総ターン: 32
- 自動合格: 32 / 要確認: 0
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 32
- counseling_detail マッチ行: 32
- route ログマッチ行: 39

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1782976547349586264774` | session-ops-01 | 1 | PASS | 1/1 | 0 | — | ステータスを教えて→OK |
| `1782976554320049508374` | session-ops-02 | 1 | PASS | 1/1 | 0 | — | 何が記録されてる？→OK |
| `1782976560368449760731` | session-ops-03 | 1 | PASS | 1/1 | 0 | — | 履歴を要約して→OK |
| `1782976566720731992859` | session-ops-04 | 1 | PASS | 1/1 | 0 | — | 履歴を教えて→OK |
| `1782976572592918335707` | session-ops-05 | 1 | PASS | 1/1 | 0 | — | 記憶を消して→OK |
| `1782976578518309959062` | session-ops-06 | 1 | PASS | 1/1 | 0 | — | 履歴消して→OK |
| `1782976584381257132977` | session-ops-07 | 1 | PASS | 1/1 | 0 | — | 会話を削除したい→OK |
| `1782976590367993893588` | session-ops-08 | 1 | PASS | 1/1 | 0 | — | 今の状態を教えて→OK |
| `1782976596233236764832` | session-ops-09 | 1 | PASS | 1/1 | 0 | — | セッションの状態は？→OK |
| `1782976602154419122082` | session-ops-10 | 1 | PASS | 1/1 | 0 | — | これまでの会話をまとめて→OK |
| `1782976608154822383601` | session-ops-11 | 1 | PASS | 1/1 | 0 | — | 保存されている情報は？→OK |
| `1782976615140744835912` | session-ops-12 | 1 | PASS | 1/1 | 0 | — | 要約して→OK |
| `1782976621264096257937` | concierge-01 | 1 | PASS | 1/1 | 2 | Concierge:2 | こんにちは→OK |
| `1782976633046331299877` | concierge-02 | 1 | PASS | 1/1 | 2 | Concierge:2 | 技術スタックは？→OK |
| `1782976647410215410927` | concierge-03 | 1 | PASS | 1/1 | 2 | Concierge:2 | プリンシプルオブプログラミングとは？→OK |
| `1782976658592050462969` | concierge-04 | 1 | PASS | 1/1 | 2 | Concierge:2 | このサービスは何ができますか？→OK |
| `1782976671941692428502` | concierge-05 | 1 | PASS | 1/1 | 2 | Concierge:2 | Sage Terraceとは→OK |
| `1782976685098279400926` | concierge-06 | 1 | PASS | 1/1 | 2 | Concierge:2 | APIの仕組みを教えて→OK |
| `1782976699695325909412` | concierge-07 | 1 | PASS | 1/1 | 2 | Concierge:2 | データはどこに保存されますか？→OK |
| `1782976713399308469768` | concierge-08 | 1 | PASS | 1/1 | 1 | Concierge:1 | プライバシーについて→OK |
| `1782976728434883420318` | concierge-09 | 1 | PASS | 1/1 | 2 | Concierge:2 | 対応言語は？→OK |
| `1782976742383297257598` | concierge-10 | 1 | PASS | 1/1 | 2 | Concierge:2 | 医薬品推奨の仕組み→OK |
| `1782976760109286134952` | concierge-11 | 1 | PASS | 1/1 | 2 | Concierge:2 | rule_basedとは→OK |
| `1782976774798820225179` | concierge-12 | 1 | PASS | 1/1 | 2 | Concierge:2 | インフラ構成を教えて→OK |
| `1782976790703085148705` | store-01 | 1 | PASS | 1/1 | 2 | Store:2 | 近くの薬局を教えて→OK |
| `1782976803771382313097` | store-02 | 1 | PASS | 1/1 | 2 | Store:2 | ドラッグストアはどこ？→OK |
| `1782976817282718313459` | store-03 | 1 | PASS | 1/1 | 2 | Store:2 | OTCを買える店→OK |
| `1782976831242466417989` | store-04 | 1 | PASS | 1/1 | 2 | Store:2 | 処方箋なしで買える場所→OK |
| `1782976844060063906193` | store-05 | 1 | PASS | 1/1 | 2 | Store:2 | マツキヨは近くにありますか→OK |
| `1782976857874404248980` | store-06 | 1 | PASS | 1/1 | 2 | Store:2 | 市販薬の購入先→OK |
| `1782976871542386910077` | store-matsukiyo-01 | 1 | PASS | 1/1 | 2 | Store:2 | マツキヨは近くにありますか→OK |
| `1782976882031883795208` | store-drugstore-where-01 | 1 | PASS | 1/1 | 2 | Store:2 | ドラッグストアはどこ？→OK |

## 要確認 — ターン別トランスクリプト


## IntentRouter メトリクス

```json
{
  "shadow_total": 20,
  "shadow_mismatch": 8,
  "shadow_mismatch_rate_pct": 40.0,
  "shadow_improvement_mismatch": 8,
  "shadow_improvement_mismatch_rate_pct": 40.0,
  "shadow_regression_mismatch": 0,
  "shadow_regression_mismatch_rate_pct": 0.0,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 12,
    "gate_improvement": 8
  },
  "shadow_by_primary_route": {
    "Concierge": 12,
    "Store": 8
  },
  "shadow_by_resolved_by": {
    "gate": 9,
    "llm": 10,
    "guard": 1
  },
  "shadow_with_fever_context_flag": 0,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 0,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 19,
  "dispatch_handled": 19,
  "dispatch_unhandled": 0,
  "dispatch_success_rate_pct": 100.0,
  "dispatch_by_handler": {
    "concierge_agent": 11,
    "store_inquiry": 8
  },
  "mismatch_samples": [
    {
      "session_id": "1782976790703085148705",
      "user_input": "近くの薬局を教えて",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782976803771382313097",
      "user_input": "ドラッグストアはどこ？",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782976817282718313459",
      "user_input": "OTCを買える店",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782976831242466417989",
      "user_input": "処方箋なしで買える場所",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782976844060063906193",
      "user_input": "マツキヨは近くにありますか",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782976857874404248980",
      "user_input": "市販薬の購入先",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782976871542386910077",
      "user_input": "マツキヨは近くにありますか",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782976882031883795208",
      "user_input": "ドラッグストアはどこ？",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    }
  ]
}
```

## Admin 確認

- [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) → サイドバー「**v2テストのみ**」を ON
- 検索: `v2-test` または `session_id`（下表）

| scenario_id | session_id |
|-------------|------------|
| session-ops-01 | `1782976547349586264774` |
| session-ops-02 | `1782976554320049508374` |
| session-ops-03 | `1782976560368449760731` |
| session-ops-04 | `1782976566720731992859` |
| session-ops-05 | `1782976572592918335707` |
| session-ops-06 | `1782976578518309959062` |
| session-ops-07 | `1782976584381257132977` |
| session-ops-08 | `1782976590367993893588` |
| session-ops-09 | `1782976596233236764832` |
| session-ops-10 | `1782976602154419122082` |
| session-ops-11 | `1782976608154822383601` |
| session-ops-12 | `1782976615140744835912` |
| concierge-01 | `1782976621264096257937` |
| concierge-02 | `1782976633046331299877` |
| concierge-03 | `1782976647410215410927` |
| concierge-04 | `1782976658592050462969` |
| concierge-05 | `1782976671941692428502` |
| concierge-06 | `1782976685098279400926` |
| concierge-07 | `1782976699695325909412` |
| concierge-08 | `1782976713399308469768` |
| concierge-09 | `1782976728434883420318` |
| concierge-10 | `1782976742383297257598` |
| concierge-11 | `1782976760109286134952` |
| concierge-12 | `1782976774798820225179` |
| store-01 | `1782976790703085148705` |
| store-02 | `1782976803771382313097` |
| store-03 | `1782976817282718313459` |
| store-04 | `1782976831242466417989` |
| store-05 | `1782976844060063906193` |
| store-06 | `1782976857874404248980` |
| store-matsukiyo-01 | `1782976871542386910077` |
| store-drugstore-where-01 | `1782976882031883795208` |
