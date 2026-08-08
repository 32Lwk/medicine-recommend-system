# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-08)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-08T02:45:43.081429+00:00
- 所要時間: 161.2s
- シナリオ/セッション: 10 / 総ターン: 10
- 自動合格: 10 / 要確認: 0
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **physical**: 10/10 自動合格 / 10 ターン

## IntentRouter Shadow / Dispatch KPI

_`--skip-metrics` のため計測スキップ_

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| physical | 10 | 10 | 10 | 0 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 10
- end-to-end: p50 16890.0ms / **p95 24495.0ms** / max 24495.0ms
- pipeline total: p50 16595.22ms / p95 23602.52ms / max 23602.52ms
- LLM 呼び出し: 合計 36 / リクエストあたり平均 3.6

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| explanation_generator.batch_usage_notes | 8 | 32942.65 | 4324.62 | 4497.36 |
| missing_info_service | 10 | 18886.33 | 1856.51 | 2094.96 |
| chat_response_service.personalized_advice | 8 | 12566.85 | 1562.46 | 1726.98 |
| medicine_qa/focus_llm | 10 | 12398.34 | 1064.04 | 2665.42 |

## 意図評価（intent evaluation）

- 追跡セッション: 0
- counseling_detail マッチ: 0
- route ログマッチ: 0

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786157143109544235300` | physical-symptom-01 | 1 | 0/0 | 0 | — |
| `1786157167888535859398` | physical-symptom-02 | 1 | 0/0 | 0 | — |
| `1786157186655387574592` | physical-symptom-03 | 1 | 0/0 | 0 | — |
| `1786157205389060924226` | physical-symptom-04 | 1 | 0/0 | 0 | — |
| `1786157223519035431927` | physical-symptom-05 | 1 | 0/0 | 0 | — |
| `1786157242554120248207` | physical-symptom-06 | 1 | 0/0 | 0 | — |
| `1786157251079207742766` | physical-symptom-07 | 1 | 0/0 | 0 | — |
| `1786157266786613722869` | physical-symptom-08 | 1 | 0/0 | 0 | — |
| `1786157280899520747895` | physical-symptom-09 | 1 | 0/0 | 0 | — |
| `1786157298069472554153` | physical-symptom-10 | 1 | 0/0 | 0 | — |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "intent_router_shadow_skipped": true,
  "latency_this_run": {
    "turns_measured": 10,
    "e2e_ms_p50": 16890.0,
    "e2e_ms_p95": 24495.0,
    "e2e_ms_max": 24495.0,
    "phase_breakdown": {
      "pipeline_perf_requests": 10,
      "total_ms_p50": 16595.22,
      "total_ms_p95": 23602.52,
      "total_ms_max": 23602.52,
      "llm_calls_total": 36,
      "llm_calls_per_request_avg": 3.6,
      "llm_by_path": {
        "explanation_generator.batch_usage_notes": {
          "count": 8,
          "latency_ms_sum": 32942.65,
          "latency_ms_p50": 4324.62,
          "latency_ms_p95": 4497.36
        },
        "missing_info_service": {
          "count": 10,
          "latency_ms_sum": 18886.33,
          "latency_ms_p50": 1856.51,
          "latency_ms_p95": 2094.96
        },
        "chat_response_service.personalized_advice": {
          "count": 8,
          "latency_ms_sum": 12566.85,
          "latency_ms_p50": 1562.46,
          "latency_ms_p95": 1726.98
        },
        "medicine_qa/focus_llm": {
          "count": 10,
          "latency_ms_sum": 12398.34,
          "latency_ms_p50": 1064.04,
          "latency_ms_p95": 2665.42
        }
      },
      "breakdown_steps_avg_ms": {
        "after_counseling_flow": 156.84,
        "after_get_session_db": 12.02,
        "after_medicine_qa_route": 166.03,
        "after_security": 110.46,
        "after_triage": 119.24,
        "after_triage_follow_ups": 137.96,
        "before_emoji_route": 114.67,
        "before_llm_setup": 14.19,
        "before_medicine_qa_route": 162.77,
        "before_orchestrator": 192.22,
        "before_security": 17.67,
        "before_triage": 114.77,
        "emit_cards_early": 7988.1,
        "explanation_phase_done": 16027.1,
        "explanation_phase_start": 16027.1,
        "line_carousel_push": 16017.11,
        "medicine_qa_physical_priority": 166.75,
        "moderation_done": 156.86,
        "nlu_batch_done": 3912.63,
        "nlu_batch_start": 1697.8,
        "parsed_message": 9.94,
        "personalized_advice": 17608.85,
        "post_start": 9.83,
        "rb_explain_batch_done": 16015.56,
        "rb_missing_info_done": 5858.29,
        "rb_scoring_only_done": 7988.08,
        "rule_based_scoring_only_done": 14869.99,
        "rule_based_start": 3960.01,
        "safety_gate_done": 135.69,
        "session_db_read": 9.98,
        "short_symptom_triage_skip_llm": 119.23
      }
    }
  },
  "turn_eval_kpi": {
    "turns_evaluated": 10,
    "turn_rule_pass": 10,
    "reject_no_reco": 0,
    "comparison_loop": 0,
    "judge_turns": 0,
    "judge_aligned": 0,
    "turn_rows": [
      {
        "scenario_id": "physical-symptom-01",
        "turn_index": 0,
        "rule_pass": true,
        "judge_grade": null,
        "prompt_turns": null,
        "failures": []
      },
      {
        "scenario_id": "physical-symptom-02",
        "turn_index": 0,
        "rule_pass": true,
        "judge_grade": null,
        "prompt_turns": null,
        "failures": []
      },
      {
        "scenario_id": "physical-symptom-03",
        "turn_index": 0,
        "rule_pass": true,
        "judge_grade": null,
        "prompt_turns": null,
        "failures": []
      },
      {
        "scenario_id": "physical-symptom-04",
        "turn_index": 0,
        "rule_pass": true,
        "judge_grade": null,
        "prompt_turns": null,
        "failures": []
      },
      {
        "scenario_id": "physical-symptom-05",
        "turn_index": 0,
        "rule_pass": true,
        "judge_grade": null,
        "prompt_turns": null,
        "failures": []
      },
      {
        "scenario_id": "physical-symptom-06",
        "turn_index": 0,
        "rule_pass": true,
        "judge_grade": null,
        "prompt_turns": null,
        "failures": []
      },
      {
        "scenario_id": "physical-symptom-07",
        "turn_index": 0,
        "rule_pass": true,
        "judge_grade": null,
        "prompt_turns": null,
        "failures": []
      },
      {
        "scenario_id": "physical-symptom-08",
        "turn_index": 0,
        "rule_pass": true,
        "judge_grade": null,
        "prompt_turns": null,
        "failures": []
      },
      {
        "scenario_id": "physical-symptom-09",
        "turn_index": 0,
        "rule_pass": true,
        "judge_grade": null,
        "prompt_turns": null,
        "failures": []
      },
      {
        "scenario_id": "physical-symptom-10",
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

- 評価ターン数: 10
- ターン rule pass: 10
- reject_no_reco 検知: 0
- comparison_loop 検知: 0
- judge aligned: 0 / judged 0

| scenario | turn | rule | judge | prompt | failures |
|----------|------|------|-------|--------|----------|
| physical-symptom-01 | 0 | PASS | None | None |  |
| physical-symptom-02 | 0 | PASS | None | None |  |
| physical-symptom-03 | 0 | PASS | None | None |  |
| physical-symptom-04 | 0 | PASS | None | None |  |
| physical-symptom-05 | 0 | PASS | None | None |  |
| physical-symptom-06 | 0 | PASS | None | None |  |
| physical-symptom-07 | 0 | PASS | None | None |  |
| physical-symptom-08 | 0 | PASS | None | None |  |
| physical-symptom-09 | 0 | PASS | None | None |  |
| physical-symptom-10 | 0 | PASS | None | None |  |

## 要確認シナリオ

_自動評価で不一致なし（手動確認推奨）_

## 全セッション — 完全トランスクリプト

### physical-symptom-01 — physical (PASS)
- session_id: `1786157143109544235300`
- wave: 1b
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 24495ms):

頭痛いの、つらいですね。まずはイブやバファリンEX、カロナールAのような痛み止めで様子を見るのがよいです。空腹時は避け、説明書どおりに服用してください。熱やのど痛みもある、急に強くなった、いつもと違う頭痛なら、インフルエンザや別の病気も考えられるので受診をおすすめします。

### physical-symptom-02 — physical (PASS)
- session_id: `1786157167888535859398`
- wave: 1b
#### Turn 1
- **User**: 頭が痛いです
- **Bot** (`unknown`, 18484ms):

頭が痛いんですね、つらいですね。まずは無理せず静かな場所で休み、水分をとってください。イブやバファリンEXは頭痛に使いやすく、カロナールAは胃への負担が比較的少なめです。空腹時は避け、他の痛み止めとの重ね飲みに注意してください。発熱やのどの痛みもあれば、インフルエンザの可能性もあるので早めに受診を。

### physical-symptom-03 — physical (PASS)
- session_id: `1786157186655387574592`
- wave: 1b
#### Turn 1
- **User**: 咳が出ます
- **Bot** (`unknown`, 18406ms):

咳が出てしんどいですね。今回の症状なら、のどの刺激を和らげるトローチが使いやすいです。トピックGトローチなどは、咳き込みの原因になりやすいのどの不快感をケアできます。水分をこまめにとり、声を休めてください。発熱や強いだるさ、インフルエンザが疑われるときは受診を。

### physical-symptom-04 — physical (PASS)
- session_id: `1786157205389060924226`
- wave: 1b
#### Turn 1
- **User**: のどが痛い
- **Bot** (`unknown`, 17844ms):

のどが痛いんですね、つらいですよね。まずはのどをうるおし、刺激の少ない飲み物で休んでください。スカイブブロンのどスプレーやルルのどスプレーは、痛むところに直接使えてのどの炎症を和らげやすいです。発熱や強いだるさがあればインフルエンザも考え、無理せず受診を。イブスリーショットプレミアムはのど以外の症状がある時に検討を。

### physical-symptom-05 — physical (PASS)
- session_id: `1786157223519035431927`
- wave: 1b
#### Turn 1
- **User**: 鼻水が止まらない
- **Bot** (`unknown`, 18709ms):

鼻水が止まらないのはつらいですね。スカイブブロンHIは鼻水を含むかぜ症状をまとめてケアしやすく、スカイブブロンNAスプレーは鼻づまりにも使いやすいです。スカイブゴールドも症状が複数ある時に役立ちます。発熱や強いだるさがあればインフルエンザの可能性もあるので受診を。妊娠中は使用前に確認してください。

### physical-symptom-06 — physical (PASS)
- session_id: `1786157242554120248207`
- wave: 1b
#### Turn 1
- **User**: 胃が痛い
- **Bot** (`system_error`, 8251ms):

処理中に問題が発生しました。しばらく時間をおいてからもう一度お試しください。

### physical-symptom-07 — physical (PASS)
- session_id: `1786157251079207742766`
- wave: 1b
#### Turn 1
- **User**: 下痢をしています
- **Bot** (`unknown`, 15427ms):

下痢でつらいですね。オウレン末はいけだや／高砂オウレンは、下痢に伴うお腹の不調を整える目的で選ばれています。まずは水分をこまめにとり、脂っこい物や冷たい物は控えてください。血便、高熱、強い腹痛、脱水がある、または2日以上続く場合は早めに受診してください。

### physical-symptom-08 — physical (PASS)
- session_id: `1786157266786613722869`
- wave: 1b
#### Turn 1
- **User**: 便秘です
- **Bot** (`unknown`, 13837ms):

便秘でおつらいですね。まずは水分をしっかりとり、食事や軽い運動も試してみてください。すぐ出したい強い便秘なら、浣腸のミカサ浣腸N40やコトブキ浣腸40が合いやすいです。腹痛、吐き気、血便がある、数日続く場合は受診してください。大柴胡湯は体質に合うときに使います。

### physical-symptom-09 — physical (PASS)
- session_id: `1786157280899520747895`
- wave: 1b
#### Turn 1
- **User**: 目がかゆい
- **Bot** (`unknown`, 16890ms):

目がかゆいのはつらいですね。まずは目をこすらず、清潔に保ってください。アイブルー抗菌目薬αやアイエースVクールは、かゆみや炎症をやわらげるのに使いやすいです。コンタクト使用中なら外し、症状が強い・充血や目やにが増える・見えにくい場合は受診を。

### physical-symptom-10 — physical (PASS)
- session_id: `1786157298069472554153`
- wave: 1b
#### Turn 1
- **User**: 耳が痛い
- **Bot** (`physical_no_recommendation`, 5906ms):

耳の痛みですね、つらいですね。解熱鎮痛薬で一時的に和らぐこともありますが、発熱・聞こえにくさ・膿・強い痛みがある場合は早めに耳鼻咽喉科を受診してください。いつから・片耳か両耳かも教えていただけると安心です。

