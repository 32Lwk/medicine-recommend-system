# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-08)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-08T02:45:43.080927+00:00
- 所要時間: 30.3s
- シナリオ/セッション: 3 / 総ターン: 3
- 自動合格: 3 / 要確認: 0
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **physical**: 3/3 自動合格 / 3 ターン

## IntentRouter Shadow / Dispatch KPI

_`--skip-metrics` のため計測スキップ_

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| physical | 3 | 3 | 3 | 0 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 3
- end-to-end: p50 8210.0ms / **p95 18218.0ms** / max 18218.0ms
- pipeline total: p50 7455.14ms / p95 17883.08ms / max 17883.08ms
- LLM 呼び出し: 合計 7 / リクエストあたり平均 2.33

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| missing_info_service | 2 | 4213.48 | 1976.46 | 2237.02 |
| explanation_generator.batch_usage_notes | 1 | 3505.49 | 3505.49 | 3505.49 |
| medicine_qa/focus_llm | 3 | 3173.3 | 992.57 | 1240.5 |
| chat_response_service.personalized_advice | 1 | 1365.48 | 1365.48 | 1365.48 |

## 意図評価（intent evaluation）

- 追跡セッション: 0
- counseling_detail マッチ: 0
- route ログマッチ: 0

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786157143083009189313` | tier1-short-urticaria | 1 | 0/0 | 0 | — |
| `1786157151637039998750` | tier1-short-cough | 1 | 0/0 | 0 | — |
| `1786157170183633209674` | tier1-short-fever-child | 1 | 0/0 | 0 | — |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "intent_router_shadow_skipped": true,
  "latency_this_run": {
    "turns_measured": 3,
    "e2e_ms_p50": 8210.0,
    "e2e_ms_p95": 18218.0,
    "e2e_ms_max": 18218.0,
    "phase_breakdown": {
      "pipeline_perf_requests": 3,
      "total_ms_p50": 7455.14,
      "total_ms_p95": 17883.08,
      "total_ms_max": 17883.08,
      "llm_calls_total": 7,
      "llm_calls_per_request_avg": 2.33,
      "llm_by_path": {
        "missing_info_service": {
          "count": 2,
          "latency_ms_sum": 4213.48,
          "latency_ms_p50": 1976.46,
          "latency_ms_p95": 2237.02
        },
        "explanation_generator.batch_usage_notes": {
          "count": 1,
          "latency_ms_sum": 3505.49,
          "latency_ms_p50": 3505.49,
          "latency_ms_p95": 3505.49
        },
        "medicine_qa/focus_llm": {
          "count": 3,
          "latency_ms_sum": 3173.3,
          "latency_ms_p50": 992.57,
          "latency_ms_p95": 1240.5
        },
        "chat_response_service.personalized_advice": {
          "count": 1,
          "latency_ms_sum": 1365.48,
          "latency_ms_p50": 1365.48,
          "latency_ms_p95": 1365.48
        }
      },
      "breakdown_steps_avg_ms": {
        "after_counseling_flow": 251.38,
        "after_get_session_db": 13.99,
        "after_medicine_qa_route": 729.33,
        "after_security": 175.19,
        "after_triage": 196.45,
        "after_triage_follow_ups": 224.46,
        "before_emoji_route": 188.68,
        "before_llm_setup": 28.19,
        "before_medicine_qa_route": 272.84,
        "before_orchestrator": 781.15,
        "before_security": 34.12,
        "before_triage": 189.06,
        "emit_cards_early": 9377.42,
        "explanation_phase_done": 16375.99,
        "explanation_phase_start": 16375.99,
        "line_carousel_push": 16366.6,
        "medicine_qa_physical_priority": 729.67,
        "moderation_done": 251.41,
        "nlu_batch_done": 3798.79,
        "nlu_batch_start": 1751.69,
        "parsed_message": 11.2,
        "personalized_advice": 17785.25,
        "post_start": 10.99,
        "rb_explain_batch_done": 16365.24,
        "rb_missing_info_done": 6595.83,
        "rb_scoring_only_done": 9377.4,
        "rule_based_scoring_only_done": 11875.18,
        "rule_based_start": 4479.86,
        "safety_gate_done": 219.76,
        "session_db_read": 11.29,
        "short_symptom_triage_skip_llm": 196.44
      }
    }
  },
  "turn_eval_kpi": {
    "turns_evaluated": 3,
    "turn_rule_pass": 3,
    "reject_no_reco": 0,
    "comparison_loop": 0,
    "judge_turns": 0,
    "judge_aligned": 0,
    "turn_rows": [
      {
        "scenario_id": "tier1-short-urticaria",
        "turn_index": 0,
        "rule_pass": true,
        "judge_grade": null,
        "prompt_turns": 1,
        "failures": []
      },
      {
        "scenario_id": "tier1-short-cough",
        "turn_index": 0,
        "rule_pass": true,
        "judge_grade": null,
        "prompt_turns": null,
        "failures": []
      },
      {
        "scenario_id": "tier1-short-fever-child",
        "turn_index": 0,
        "rule_pass": true,
        "judge_grade": null,
        "prompt_turns": null,
        "failures": []
      }
    ]
  }
}
```


## ターン別評価 KPI

- 評価ターン数: 3
- ターン rule pass: 3
- reject_no_reco 検知: 0
- comparison_loop 検知: 0
- judge aligned: 0 / judged 0

| scenario | turn | rule | judge | prompt | failures |
|----------|------|------|-------|--------|----------|
| tier1-short-urticaria | 0 | PASS | None | 1 |  |
| tier1-short-cough | 0 | PASS | None | None |  |
| tier1-short-fever-child | 0 | PASS | None | None |  |

## 要確認シナリオ

_自動評価で不一致なし（手動確認推奨）_

## 全セッション — 完全トランスクリプト

### tier1-short-urticaria — physical (PASS)
- session_id: `1786157143083009189313`
- wave: tier1
#### Turn 1
- **User**: 蕁麻疹出た
- **Bot** (`physical_no_recommendation`, 8210ms):

皮膚の症状ですね、つらいですね。かゆみ止めの内服や外用で様子を見られることもあります。広がる・呼吸が苦しい・唇や顔が腫れる場合は、すぐに医療機関へ。出始めた時期や範囲を教えていただくと、より安全な市販薬をご案内できます。

### tier1-short-cough — physical (PASS)
- session_id: `1786157151637039998750`
- wave: tier1
#### Turn 1
- **User**: 咳がひどい
- **Bot** (`unknown`, 18218ms):

咳がひどいのはつらいですね。トローチはのどの炎症や刺激をやわらげ、咳で荒れたのどをケアしやすいので、今回の症状に合っています。水分をこまめにとり、空気の乾燥も避けてください。発熱や強いだるさ、息苦しさがあればインフルエンザ等も考えられるので早めに受診を。

### tier1-short-fever-child — physical (PASS)
- session_id: `1786157170183633209674`
- wave: tier1
#### Turn 1
- **User**: 子供熱出た
- **Bot** (`pediatric_age_required`, 2905ms):

お子さまの年齢が分かると、より安全な市販薬をご案内できます。何歳か教えていただけますか。高熱が続く場合や状態が悪い場合は、早めに医療機関へご相談ください。

