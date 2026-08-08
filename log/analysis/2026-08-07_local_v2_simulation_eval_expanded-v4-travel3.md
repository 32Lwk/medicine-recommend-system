# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T14:56:22.292893+00:00
- セッション数: 1 / 総ターン: 4
- 自動合格: 0 / 要確認: 1
- GPT シミュレーション: True

## ログ突合サマリ

- 追跡セッション: 1
- counseling_detail マッチ行: 4
- route ログマッチ行: 5

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786114582294893372422` | gpt-gpt-travel-medicine | 4 | REVIEW | 4/4 | 5 | Physical:4, Counseling:1 | タイ旅行にロキソニン持っていきたい→OK; 空港で止められたりすることはありますか？特に海外だと、薬の持ち込みに関して不安が→OK |

## 要確認 — ターン別トランスクリプト

### gpt-gpt-travel-medicine (`1786114582294893372422`)
- failures: judge_low_overall:1.0
#### Turn 1
- **User**: タイ旅行にロキソニン持っていきたい
- **Bot** (`medicine_qa`, 10194ms):

ロキソニンSは、タイ旅行に持参する痛み止め・解熱薬として使われる市販薬です。ドーピング禁止物質は「禁止物質なし」とされているため、一般的には競技会でのドーピング規制対象ではありません。なお、タイへの医薬品持ち込み可否や数量制限などの入国ルールは、この情報だけでは判断できないため、お近くの登録販売者にご相談ください。

#### Turn 2
- **User**: 空港で止められたりすることはありますか？特に海外だと、薬の持ち込みに関して不安があります。
- **Bot** (`medicine_qa`, 15291ms):

ロキソニンSやロキソニンSプレミアムは、提示された情報ではドーピング禁止物質は「禁止物質なし」です。ただし、空港で止められるかどうか、タイへの持ち込み可否や数量制限、申告の要否といった入国・税関上の扱いは、この推奨医薬品情報だけでは判断できません。海外への医薬品持ち込みは国ごとにルールが異なるため、不安がある場合はお近くの登録販売者にご相談ください。

#### Turn 3
- **User**: 海外に持ち込む際は、国によって規制が異なるので注意が必要です。ロキソニンは一般的には問題ないことが多いですが、念のため、処方箋や使用目的を説明できる書類を持っておくと安心かもしれません。
- **Bot** (`medicine_qa`, 10888ms):

ロキソニンSは、提示された情報ではスポーツ競技におけるドーピング禁止物質には該当しません。そのため、競技者が所持・使用するうえで一般的なドーピング上の大きな懸念は低いと考えられます。なお、海外への持ち込み可否、必要書類、税関申告、空港での対応はこの推奨医薬品情報だけでは判断できませんので、お近くの登録販売者にご相談ください。

#### Turn 4
- **User**: そうですね、特に海外では薬の規制が厳しい場合があるので、事前に調べておくのが大切です。ロキソニンを持っていく場合は、使用目的や処方箋を用意しておくと、万が一のトラブルを避けられると思いますよ。
- **Bot** (`medicine_qa`, 16256ms):

ロキソニンS：解熱鎮痛薬で、頭痛・歯痛・生理痛などに用いられます。


## IntentRouter メトリクス

```json
{
  "shadow_total": 4,
  "shadow_mismatch": 4,
  "shadow_mismatch_rate_pct": 100.0,
  "shadow_improvement_mismatch": 2,
  "shadow_improvement_mismatch_rate_pct": 50.0,
  "shadow_regression_mismatch": 1,
  "shadow_regression_mismatch_rate_pct": 25.0,
  "shadow_exempt": 1,
  "shadow_exempt_rate_pct": 25.0,
  "shadow_by_mismatch_kind": {
    "regression": 1,
    "exempt": 1,
    "gate_improvement": 2
  },
  "shadow_by_primary_route": {
    "Physical": 3,
    "Counseling": 1
  },
  "shadow_by_resolved_by": {
    "llm": 1,
    "gate": 2,
    "guard": 1
  },
  "shadow_with_fever_context_flag": 0,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 0,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 1,
  "dispatch_handled": 1,
  "dispatch_unhandled": 0,
  "dispatch_success_rate_pct": 100.0,
  "dispatch_by_handler": {
    "physical_agent": 1
  },
  "execution_total": 0,
  "execution_mismatch": 0,
  "execution_mismatch_rate_pct": 0.0,
  "execution_by_layer_used": {},
  "execution_side_effect_qa": 0,
  "mismatch_samples": [
    {
      "session_id": "1786114582294893372422",
      "user_input": "タイ旅行にロキソニン持っていきたい",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786114582294893372422",
      "user_input": "空港で止められたりすることはありますか？特に海外だと、薬の持ち込みに関して不安があります。",
      "primary_route": "Counseling",
      "triage_category": "Physical",
      "mismatch_kind": "exempt",
      "dialogue_flags": null
    },
    {
      "session_id": "1786114582294893372422",
      "user_input": "海外に持ち込む際は、国によって規制が異なるので注意が必要です。ロキソニンは一般的には問題ないことが多いですが、念のため、処方箋や使用目的を説明できる書類を持って",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786114582294893372422",
      "user_input": "そうですね、特に海外では薬の規制が厳しい場合があるので、事前に調べておくのが大切です。ロキソニンを持っていく場合は、使用目的や処方箋を用意しておくと、万が一のト",
      "primary_route": "Physical",
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
| gpt-gpt-travel-medicine | `1786114582294893372422` |
