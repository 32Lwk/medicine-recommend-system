# Chat Pipeline v2 シミュレーション意図評価 (2026-07-02)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-07-02T07:38:09.197608+00:00
- セッション数: 32 / 総ターン: 32
- 自動合格: 32 / 要確認: 0
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 32
- counseling_detail マッチ行: 32
- route ログマッチ行: 40

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1782977889225725391189` | session-ops-01 | 1 | PASS | 1/1 | 0 | — | ステータスを教えて→OK |
| `1782977895697178669800` | session-ops-02 | 1 | PASS | 1/1 | 0 | — | 何が記録されてる？→OK |
| `1782977901499440238086` | session-ops-03 | 1 | PASS | 1/1 | 0 | — | 履歴を要約して→OK |
| `1782977907794315988161` | session-ops-04 | 1 | PASS | 1/1 | 0 | — | 履歴を教えて→OK |
| `1782977914442521967593` | session-ops-05 | 1 | PASS | 1/1 | 0 | — | 記憶を消して→OK |
| `1782977920813171356162` | session-ops-06 | 1 | PASS | 1/1 | 0 | — | 履歴消して→OK |
| `1782977927106847240245` | session-ops-07 | 1 | PASS | 1/1 | 0 | — | 会話を削除したい→OK |
| `1782977933109186514100` | session-ops-08 | 1 | PASS | 1/1 | 0 | — | 今の状態を教えて→OK |
| `1782977939431063939342` | session-ops-09 | 1 | PASS | 1/1 | 0 | — | セッションの状態は？→OK |
| `1782977945761271360271` | session-ops-10 | 1 | PASS | 1/1 | 0 | — | これまでの会話をまとめて→OK |
| `1782977951543413296375` | session-ops-11 | 1 | PASS | 1/1 | 0 | — | 保存されている情報は？→OK |
| `1782977957324317242231` | session-ops-12 | 1 | PASS | 1/1 | 0 | — | 要約して→OK |
| `1782977963367494144932` | concierge-01 | 1 | PASS | 1/1 | 2 | Concierge:2 | こんにちは→OK |
| `1782977973941730564529` | concierge-02 | 1 | PASS | 1/1 | 2 | Concierge:2 | 技術スタックは？→OK |
| `1782977987999170391297` | concierge-03 | 1 | PASS | 1/1 | 2 | Concierge:2 | プリンシプルオブプログラミングとは？→OK |
| `1782978001775819234068` | concierge-04 | 1 | PASS | 1/1 | 2 | Concierge:2 | このサービスは何ができますか？→OK |
| `1782978013195807766768` | concierge-05 | 1 | PASS | 1/1 | 2 | Concierge:2 | Sage Terraceとは→OK |
| `1782978026044704159112` | concierge-06 | 1 | PASS | 1/1 | 2 | Concierge:2 | APIの仕組みを教えて→OK |
| `1782978039408607134453` | concierge-07 | 1 | PASS | 1/1 | 2 | Concierge:2 | データはどこに保存されますか？→OK |
| `1782978053128901824528` | concierge-08 | 1 | PASS | 1/1 | 2 | Concierge:2 | プライバシーについて→OK |
| `1782978067096174828430` | concierge-09 | 1 | PASS | 1/1 | 2 | Concierge:2 | 対応言語は？→OK |
| `1782978079512501669677` | concierge-10 | 1 | PASS | 1/1 | 2 | Concierge:2 | 医薬品推奨の仕組み→OK |
| `1782978096339486675035` | concierge-11 | 1 | PASS | 1/1 | 2 | Concierge:2 | rule_basedとは→OK |
| `1782978110240452932828` | concierge-12 | 1 | PASS | 1/1 | 2 | Concierge:2 | インフラ構成を教えて→OK |
| `1782978124369208942322` | store-01 | 1 | PASS | 1/1 | 2 | Store:2 | 近くの薬局を教えて→OK |
| `1782978137413880726841` | store-02 | 1 | PASS | 1/1 | 2 | Store:2 | ドラッグストアはどこ？→OK |
| `1782978150307969167095` | store-03 | 1 | PASS | 1/1 | 2 | Store:2 | OTCを買える店→OK |
| `1782978163022518301409` | store-04 | 1 | PASS | 1/1 | 2 | Store:2 | 処方箋なしで買える場所→OK |
| `1782978178992741645716` | store-05 | 1 | PASS | 1/1 | 2 | Store:2 | マツキヨは近くにありますか→OK |
| `1782978191791289903190` | store-06 | 1 | PASS | 1/1 | 2 | Store:2 | 市販薬の購入先→OK |
| `1782978205115009309561` | store-matsukiyo-01 | 1 | PASS | 1/1 | 2 | Store:2 | マツキヨは近くにありますか→OK |
| `1782978215277913992334` | store-drugstore-where-01 | 1 | PASS | 1/1 | 2 | Store:2 | ドラッグストアはどこ？→OK |

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
    "llm": 11
  },
  "shadow_with_fever_context_flag": 0,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 0,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 20,
  "dispatch_handled": 20,
  "dispatch_unhandled": 0,
  "dispatch_success_rate_pct": 100.0,
  "dispatch_by_handler": {
    "concierge_agent": 12,
    "store_inquiry": 8
  },
  "mismatch_samples": [
    {
      "session_id": "1782978124369208942322",
      "user_input": "近くの薬局を教えて",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782978137413880726841",
      "user_input": "ドラッグストアはどこ？",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782978150307969167095",
      "user_input": "OTCを買える店",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782978163022518301409",
      "user_input": "処方箋なしで買える場所",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782978178992741645716",
      "user_input": "マツキヨは近くにありますか",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782978191791289903190",
      "user_input": "市販薬の購入先",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782978205115009309561",
      "user_input": "マツキヨは近くにありますか",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782978215277913992334",
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
| session-ops-01 | `1782977889225725391189` |
| session-ops-02 | `1782977895697178669800` |
| session-ops-03 | `1782977901499440238086` |
| session-ops-04 | `1782977907794315988161` |
| session-ops-05 | `1782977914442521967593` |
| session-ops-06 | `1782977920813171356162` |
| session-ops-07 | `1782977927106847240245` |
| session-ops-08 | `1782977933109186514100` |
| session-ops-09 | `1782977939431063939342` |
| session-ops-10 | `1782977945761271360271` |
| session-ops-11 | `1782977951543413296375` |
| session-ops-12 | `1782977957324317242231` |
| concierge-01 | `1782977963367494144932` |
| concierge-02 | `1782977973941730564529` |
| concierge-03 | `1782977987999170391297` |
| concierge-04 | `1782978001775819234068` |
| concierge-05 | `1782978013195807766768` |
| concierge-06 | `1782978026044704159112` |
| concierge-07 | `1782978039408607134453` |
| concierge-08 | `1782978053128901824528` |
| concierge-09 | `1782978067096174828430` |
| concierge-10 | `1782978079512501669677` |
| concierge-11 | `1782978096339486675035` |
| concierge-12 | `1782978110240452932828` |
| store-01 | `1782978124369208942322` |
| store-02 | `1782978137413880726841` |
| store-03 | `1782978150307969167095` |
| store-04 | `1782978163022518301409` |
| store-05 | `1782978178992741645716` |
| store-06 | `1782978191791289903190` |
| store-matsukiyo-01 | `1782978205115009309561` |
| store-drugstore-where-01 | `1782978215277913992334` |
