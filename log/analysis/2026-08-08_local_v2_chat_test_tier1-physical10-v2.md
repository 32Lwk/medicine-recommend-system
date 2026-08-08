# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-08)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-08T02:40:12.810859+00:00
- 所要時間: 137.2s
- シナリオ/セッション: 10 / 総ターン: 10
- 自動合格: 9 / 要確認: 1
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **physical**: 9/10 自動合格 / 10 ターン

## IntentRouter Shadow / Dispatch KPI

_`--skip-metrics` のため計測スキップ_

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| physical | 10 | 10 | 9 | 1 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 10
- end-to-end: p50 13553.0ms / **p95 17641.0ms** / max 17641.0ms
- pipeline total: p50 13257.65ms / p95 16570.29ms / max 16570.29ms
- LLM 呼び出し: 合計 38 / リクエストあたり平均 3.8

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| explanation_generator.batch_usage_notes | 9 | 37836.65 | 4161.64 | 4585.26 |
| missing_info_service | 10 | 20605.67 | 1993.93 | 2409.89 |
| chat_response_service.personalized_advice | 9 | 13072.15 | 1448.85 | 1687.04 |
| medicine_qa/focus_llm | 10 | 9664.91 | 959.99 | 1167.15 |

## 意図評価（intent evaluation）

- 追跡セッション: 0
- counseling_detail マッチ: 0
- route ログマッチ: 0

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786156812838160215049` | physical-symptom-01 | 1 | 0/0 | 0 | — |
| `1786156830776634919892` | physical-symptom-02 | 1 | 0/0 | 0 | — |
| `1786156846727632396531` | physical-symptom-03 | 1 | 0/0 | 0 | — |
| `1786156860614464156633` | physical-symptom-04 | 1 | 0/0 | 0 | — |
| `1786156875731015371447` | physical-symptom-05 | 1 | 0/0 | 0 | — |
| `1786156890829732100979` | physical-symptom-06 | 1 | 0/0 | 0 | — |
| `1786156903610764800744` | physical-symptom-07 | 1 | 0/0 | 0 | — |
| `1786156917192849467112` | physical-symptom-08 | 1 | 0/0 | 0 | — |
| `1786156929586632544364` | physical-symptom-09 | 1 | 0/0 | 0 | — |
| `1786156943953087544215` | physical-symptom-10 | 1 | 0/0 | 0 | — |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "intent_router_shadow_skipped": true,
  "latency_this_run": {
    "turns_measured": 10,
    "e2e_ms_p50": 13553.0,
    "e2e_ms_p95": 17641.0,
    "e2e_ms_max": 17641.0,
    "phase_breakdown": {
      "pipeline_perf_requests": 10,
      "total_ms_p50": 13257.65,
      "total_ms_p95": 16570.29,
      "total_ms_max": 16570.29,
      "llm_calls_total": 38,
      "llm_calls_per_request_avg": 3.8,
      "llm_by_path": {
        "explanation_generator.batch_usage_notes": {
          "count": 9,
          "latency_ms_sum": 37836.65,
          "latency_ms_p50": 4161.64,
          "latency_ms_p95": 4585.26
        },
        "missing_info_service": {
          "count": 10,
          "latency_ms_sum": 20605.67,
          "latency_ms_p50": 1993.93,
          "latency_ms_p95": 2409.89
        },
        "chat_response_service.personalized_advice": {
          "count": 9,
          "latency_ms_sum": 13072.15,
          "latency_ms_p50": 1448.85,
          "latency_ms_p95": 1687.04
        },
        "medicine_qa/focus_llm": {
          "count": 10,
          "latency_ms_sum": 9664.91,
          "latency_ms_p50": 959.99,
          "latency_ms_p95": 1167.15
        }
      },
      "breakdown_steps_avg_ms": {
        "after_counseling_flow": 225.54,
        "after_get_session_db": 13.06,
        "after_medicine_qa_route": 234.06,
        "after_security": 148.55,
        "after_triage": 176.95,
        "after_triage_follow_ups": 206.84,
        "before_emoji_route": 168.87,
        "before_llm_setup": 23.67,
        "before_medicine_qa_route": 232.11,
        "before_orchestrator": 259.89,
        "before_security": 28.66,
        "before_triage": 170.35,
        "emit_cards_early": 8174.98,
        "explanation_phase_done": 12402.57,
        "explanation_phase_start": 12402.56,
        "line_carousel_push": 12392.27,
        "medicine_qa_physical_priority": 234.89,
        "moderation_done": 225.56,
        "nlu_batch_done": 3690.56,
        "nlu_batch_start": 1499.12,
        "parsed_message": 10.93,
        "personalized_advice": 13867.72,
        "post_start": 10.8,
        "rb_explain_batch_done": 12388.92,
        "rb_missing_info_done": 5813.57,
        "rb_scoring_only_done": 8174.96,
        "rule_based_scoring_only_done": 11700.96,
        "rule_based_start": 3743.5,
        "safety_gate_done": 202.52,
        "session_db_read": 10.97,
        "short_symptom_triage_skip_llm": 176.94
      }
    }
  },
  "turn_eval_kpi": {
    "turns_evaluated": 10,
    "turn_rule_pass": 9,
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
        "rule_pass": false,
        "judge_grade": null,
        "prompt_turns": null,
        "failures": [
          "route_mismatch expected=Physical got=unknown"
        ]
      }
    ]
  }
}
```


## ターン別評価 KPI

- 評価ターン数: 10
- ターン rule pass: 9
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
| physical-symptom-10 | 0 | FAIL | None | None | route_mismatch expected=Physical got=unknown |

## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| physical-symptom-10 | physical | `1786156943953087544215` | t0:route_mismatch expected=Physical got=unknown | None |

## 全セッション — 完全トランスクリプト

### physical-symptom-01 — physical (PASS)
- session_id: `1786156812838160215049`
- wave: 1b
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 17641ms):

頭痛いの、つらいですね。まずは無理せず休んで、水分をとってください。イブやバファリンEXは、つらい頭痛をやわらげやすいお薬です。胃が弱い方、妊娠中の方、他の痛み止めを飲んでいる方は注意が必要です。発熱やのどの痛みもあるなら、インフルエンザの可能性もあるので受診も考えてください。

### physical-symptom-02 — physical (PASS)
- session_id: `1786156830776634919892`
- wave: 1b
#### Turn 1
- **User**: 頭が痛いです
- **Bot** (`unknown`, 15662ms):

頭が痛いのですね、つらいですね。まずは無理をせず、暗い静かな場所で休み、水分を少しずつとってください。おすすめのイブ、バファリンEX、カロナールAは、頭痛の痛みを和らげるのに向いています。胃が弱い方は食後に。発熱やのどの痛みもあれば、インフルエンザの可能性もあるので注意し、強い痛みや長引く場合は受診してください】【。

### physical-symptom-03 — physical (PASS)
- session_id: `1786156846727632396531`
- wave: 1b
#### Turn 1
- **User**: 咳が出ます
- **Bot** (`unknown`, 13553ms):

咳が出てつらいですね。のどの刺激で出る咳には、トローチでのどをうるおし、症状を和らげる方法が合いやすいです。水分をこまめにとり、乾燥やたばこ煙は避けてください。高熱や強いだるさ、息苦しさ、咳が長引く場合は受診を。インフルエンザが疑わしいときも早めの受診が安心です】【。

### physical-symptom-04 — physical (PASS)
- session_id: `1786156860614464156633`
- wave: 1b
#### Turn 1
- **User**: のどが痛い
- **Bot** (`unknown`, 14834ms):

のどが痛いのはつらいですね。まずは刺激の少ないのどスプレーで、痛む部分を直接ケアするのがおすすめです。スカイブブロンのどスプレーやルルのどスプレーは、のどの炎症や痛みに使いやすいです。発熱や強いだるさ、関節痛があればインフルエンザの可能性もあるので受診を。気になる場合は薬剤師にご相談ください。

### physical-symptom-05 — physical (PASS)
- session_id: `1786156875731015371447`
- wave: 1b
#### Turn 1
- **User**: 鼻水が止まらない
- **Bot** (`unknown`, 14820ms):

鼻水が止まらないのはつらいですね。スカイブブロンHIは鼻水だけでなく、かぜの他の症状も一緒に見たいときに向いています。鼻づまりが強ければスカイブブロンNAスプレーも使いやすいです。発熱や強いだるさがあればインフルエンザの可能性もあるので受診を。眠気や運転前は注意してください。

### physical-symptom-06 — physical (PASS)
- session_id: `1786156890829732100979`
- wave: 1b
#### Turn 1
- **User**: 胃が痛い
- **Bot** (`unknown`, 12458ms):

胃が痛いのですね、つらいですね。第一三共胃腸薬グリーン微粒や新キャベジンコーワSは、胃酸の出すぎや胃の荒れによる胃痛に使いやすいです。まずは刺激物・お酒・空腹を避け、無理せず休んでください。黒い便、吐血、強い痛みや発熱があれば早めに受診を。

### physical-symptom-07 — physical (PASS)
- session_id: `1786156903610764800744`
- wave: 1b
#### Turn 1
- **User**: 下痢をしています
- **Bot** (`unknown`, 13295ms):

下痢でつらいですね。オウレン末は、腸の動きを整えて水様便を落ち着かせたい時に使われる生薬です。まずは水分をこまめに取り、脂っこい物や冷たい飲み物は控えてください。発熱、強い腹痛、血便、嘔吐を伴う、または2日以上続く場合は受診をおすすめします。

### physical-symptom-08 — physical (PASS)
- session_id: `1786156917192849467112`
- wave: 1b
#### Turn 1
- **User**: 便秘です
- **Bot** (`unknown`, 12107ms):

便秘でおつらいですね。まずは水分をしっかりとり、軽い運動や食物繊維も意識してください。つらい張りには、比較的すぐ出したい場合はミカサ浣腸N40／コトブキ浣腸40が役立ちます。お腹の張りや食べすぎもあるなら大柴胡湯も候補です。強い腹痛、血便、数日続く便秘は受診してください。

### physical-symptom-09 — physical (PASS)
- session_id: `1786156929586632544364`
- wave: 1b
#### Turn 1
- **User**: 目がかゆい
- **Bot** (`unknown`, 14074ms):

目がかゆいのですね、つらいですね。かゆみが中心なら、目の炎症や充血にも使いやすいアイエースVクールやアイリス50が候補です。まずは手でこすらず、コンタクトは外して使ってください。痛み・目やに・見えにくさがある、または長引く場合は受診をおすすめします。

### physical-symptom-10 — physical (REVIEW)
- session_id: `1786156943953087544215`
- wave: 1b
#### Turn 1
- **User**: 耳が痛い
- **Bot** (`unknown`, 5804ms):

該当する医薬品が見つかりませんでした

