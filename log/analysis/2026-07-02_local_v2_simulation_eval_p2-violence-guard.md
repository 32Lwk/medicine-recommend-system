# Chat Pipeline v2 シミュレーション意図評価 (2026-07-02)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-07-01T18:37:07.133102+00:00
- セッション数: 13 / 総ターン: 26
- 自動合格: 13 / 要確認: 0
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 13
- counseling_detail マッチ行: 75
- route ログマッチ行: 52

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1782931027158311526743` | counseling-ctx-01 | 2 | PASS | 5/5 | 4 | Counseling:2, Physical:2 | 最近眠れません→OK; 最近眠れません→OK |
| `1782931078368812582916` | counseling-ctx-02 | 2 | PASS | 6/6 | 4 | Counseling:4 | 仕事がつらい→OK; 仕事がつらい→OK |
| `1782931106644709650590` | counseling-ctx-03 | 2 | PASS | 6/6 | 4 | Counseling:4 | 不安感が続きます→OK; 不安感が続きます→OK |
| `1782931136475776119228` | counseling-ctx-04 | 2 | PASS | 4/4 | 4 | Counseling:2, Concierge:2 | ストレスが溜まっています→OK; ストレスが溜まっています→OK |
| `1782931165823843435463` | counseling-ctx-05 | 2 | PASS | 6/6 | 4 | Counseling:4 | 気分が落ち込みます→OK; 気分が落ち込みます→OK |
| `1782931193609518445938` | counseling-ctx-06 | 2 | PASS | 6/6 | 4 | Counseling:4 | 人間関係で悩んでいます→OK; 人間関係で悩んでいます→OK |
| `1782931222994520639935` | counseling-ctx-07 | 2 | PASS | 6/6 | 4 | Counseling:4 | 勉強のプレッシャー→OK; 勉強のプレッシャー→OK |
| `1782931253028499370273` | counseling-ctx-08 | 2 | PASS | 6/6 | 4 | Counseling:4 | 孤独を感じます→OK; 孤独を感じます→OK |
| `1782931285607654627479` | counseling-ctx-09 | 2 | PASS | 7/7 | 4 | Counseling:4 | イライラします→OK; イライラします→OK |
| `1782931313309498790139` | counseling-ctx-10 | 2 | PASS | 6/6 | 4 | Counseling:4 | 落ち着きません→OK; 落ち着きません→OK |
| `1782931344917332941315` | counseling-ctx-11 | 2 | PASS | 4/4 | 4 | Physical:2, Counseling:2 | 疲れが取れません→OK; 残業が続いています→OK |
| `1782931387121814831584` | counseling-ctx-12 | 2 | PASS | 6/6 | 4 | Counseling:4 | 気持ちを整理したい→OK; 気持ちを整理したい→OK |
| `1782931415824729618800` | insomnia-followup-duration-01 | 2 | PASS | 7/7 | 4 | Counseling:4 | 最近眠れません→OK; 最近眠れません→OK |

## 要確認 — ターン別トランスクリプト


## IntentRouter メトリクス

```json
{
  "shadow_total": 26,
  "shadow_mismatch": 3,
  "shadow_mismatch_rate_pct": 11.54,
  "shadow_by_primary_route": {
    "Counseling": 23,
    "Physical": 2,
    "Concierge": 1
  },
  "shadow_by_resolved_by": {
    "gate": 13,
    "legacy": 10,
    "llm": 3
  },
  "shadow_with_fever_context_flag": 0,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 0,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 26,
  "dispatch_handled": 25,
  "dispatch_unhandled": 1,
  "dispatch_success_rate_pct": 96.15,
  "dispatch_by_handler": {
    "counseling_processor": 23,
    "physical_agent": 2,
    "concierge_agent": 1
  },
  "mismatch_samples": [
    {
      "session_id": "1782931106644709650590",
      "user_input": "1ヶ月ほどです",
      "primary_route": "Counseling",
      "triage_category": "Ask",
      "dialogue_flags": null
    },
    {
      "session_id": "1782931344917332941315",
      "user_input": "残業が続いています",
      "primary_route": "Counseling",
      "triage_category": "Physical",
      "dialogue_flags": null
    },
    {
      "session_id": "1782931415824729618800",
      "user_input": "2週間くらいです",
      "primary_route": "Counseling",
      "triage_category": "Ask",
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
| counseling-ctx-01 | `1782931027158311526743` |
| counseling-ctx-02 | `1782931078368812582916` |
| counseling-ctx-03 | `1782931106644709650590` |
| counseling-ctx-04 | `1782931136475776119228` |
| counseling-ctx-05 | `1782931165823843435463` |
| counseling-ctx-06 | `1782931193609518445938` |
| counseling-ctx-07 | `1782931222994520639935` |
| counseling-ctx-08 | `1782931253028499370273` |
| counseling-ctx-09 | `1782931285607654627479` |
| counseling-ctx-10 | `1782931313309498790139` |
| counseling-ctx-11 | `1782931344917332941315` |
| counseling-ctx-12 | `1782931387121814831584` |
| insomnia-followup-duration-01 | `1782931415824729618800` |
