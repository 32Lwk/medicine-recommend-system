# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T11:23:54.094125+00:00
- 所要時間: 279.8s
- シナリオ/セッション: 12 / 総ターン: 24
- 自動合格: 10 / 要確認: 2
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **anaphora**: 4/5 自動合格 / 11 ターン
- **chitchat**: 1/1 自動合格 / 1 ターン
- **clarify**: 0/1 自動合格 / 1 ターン
- **correction**: 1/1 自動合格 / 3 ターン
- **medicine_thread**: 2/2 自動合格 / 5 ターン
- **pivot**: 1/1 自動合格 / 2 ターン
- **session_ops**: 1/1 自動合格 / 1 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **97.75%** (1001/1024) |
| **shadow_regression_mismatch_rate_pct** | **3.11%** (65/2093) |
| shadow_mismatch_rate_pct | 13.47% |
| shadow_improvement_mismatch_rate_pct | 9.56% |
| shadow_exempt_rate_pct | 0.81% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:1811, exempt:17, gate_improvement:200, regression:65 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| anaphora | 5 | 11 | 4 | 1 |
| chitchat | 1 | 1 | 1 | 0 |
| clarify | 1 | 1 | 0 | 1 |
| correction | 1 | 3 | 1 | 0 |
| medicine_thread | 2 | 5 | 2 | 0 |
| pivot | 1 | 2 | 1 | 0 |
| session_ops | 1 | 1 | 1 | 0 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 24
- end-to-end: p50 9605.0ms / **p95 26311.0ms** / max 61171.0ms
- pipeline total: p50 9465.11ms / p95 26129.94ms / max 44322.26ms
- LLM 呼び出し: 合計 74 / リクエストあたり平均 3.08

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| medicine_response_builder.chat_context | 9 | 57369.39 | 6933.87 | 8364.11 |
| medicine_qa/focus_llm | 32 | 36736.27 | 1098.55 | 1469.2 |
| llm_triage.stage1 | 18 | 29917.96 | 1632.07 | 2110.77 |
| explanation_generator.batch_usage_notes | 2 | 9795.98 | 4659.92 | 5136.06 |
| llm_triage.stage2 | 3 | 5358.34 | 1635.76 | 2212.01 |
| missing_info_service | 2 | 4838.26 | 2056.27 | 2781.99 |
| chat_response_service.personalized_advice | 2 | 3308.28 | 1569.71 | 1738.57 |
| concierge_agent.chitchat | 2 | 2834.53 | 1328.81 | 1505.72 |
| concierge_agent.meta_architecture | 1 | 1692.17 | 1692.17 | 1692.17 |
| concierge_agent.greeting | 1 | 1537.52 | 1537.52 | 1537.52 |
| dialogue.intent_router_llm | 1 | 1260.03 | 1260.03 | 1260.03 |
| concierge_agent.thanks | 1 | 1107.31 | 1107.31 | 1107.31 |

## 意図評価（intent evaluation）

- 追跡セッション: 12
- counseling_detail マッチ: 24
- route ログマッチ: 26
- IntentRouter metrics: `{"shadow_total": 23, "shadow_mismatch": 5, "shadow_mismatch_rate_pct": 21.74, "shadow_improvement_mismatch": 4, "shadow_improvement_mismatch_rate_pct": 17.39, "shadow_regression_mismatch": 1, "shadow_regression_mismatch_rate_pct": 4.35, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"gate_improvement": 4, "agree": 18, "regression": 1}, "shadow_by_primary_route": {"Physical": 20, "Concierge": 3}, "shadow_by_resolved_by": {"gate": 12, "llm": 9, "guard": 2}, "shadow_`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786101834139364194297` | golden-loxonin-home-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786101901488551231698` | golden-loxonin-s-variant-01 | 3 | 3/3 | 4 | Physical:4 |
| `1786101923479877980363` | golden-warafin-anaphora-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786101947753182174380` | golden-compare-followup-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786101982711112450080` | golden-correction-pivot-01 | 3 | 3/3 | 4 | Physical:4 |
| `1786102029822706262755` | golden-meta-pivot-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |
| `1786102045916368407724` | golden-alcohol-anaphora-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786102074234559363840` | golden-clarify-ambiguous-01 | 1 | 1/1 | 1 | Physical:1 |
| `1786102077854089324444` | golden-chitchat-health-01 | 1 | 1/1 | 1 | Physical:1 |
| `1786102081389801830434` | golden-session-delete-01 | 1 | 1/1 | 0 | — |
| `1786102081991760980532` | golden-thanks-followup-01 | 3 | 3/3 | 3 | Physical:2, Concierge:1 |
| `1786102104493749236719` | golden-casual-home-kansai-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786101834.0941212,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 10592,
      "with_response": 10592,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2093,
        "shadow_mismatch": 282,
        "shadow_mismatch_rate_pct": 13.47,
        "shadow_improvement_mismatch": 200,
        "shadow_improvement_mismatch_rate_pct": 9.56,
        "shadow_regression_mismatch": 65,
        "shadow_regression_mismatch_rate_pct": 3.11,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 0.81,
        "shadow_by_mismatch_kind": {
          "agree": 1811,
          "gate_improvement": 200,
          "exempt": 17,
          "regression": 65
        },
        "shadow_by_primary_route": {
          "Physical": 1090,
          "Concierge": 758,
          "Counseling": 102,
          "Emergency": 35,
          "Store": 63,
          "Unknown": 14,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 976,
          "legacy": 44,
          "llm": 810,
          "guard": 263
        },
        "shadow_with_fever_context_flag": 82,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 65,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1024,
        "dispatch_handled": 1001,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 97.75,
        "dispatch_by_handler": {
          "concierge_agent": 379,
          "physical_agent": 490,
          "counseling_processor": 72,
          "store_inquiry": 65,
          "emergency_agent": 6,
          "security_gate": 6,
          "session_ops": 6
        },
        "execution_total": 0,
        "execution_mismatch": 0,
        "execution_mismatch_rate_pct": 0.0,
        "execution_by_layer_used": {},
        "execution_side_effect_qa": 0,
        "mismatch_samples": [
          {
            "session_id": "1782973789622525865487",
            "user_input": "近くの薬局",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782973917916280451456",
            "user_input": "近くの薬局を教えて",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782973931406085911208",
            "user_input": "ドラッグストアはどこ？",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782973944286547860166",
            "user_input": "OTCを買える店",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782973958078709834251",
            "user_input": "処方箋なしで買える場所",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782973972138396339780",
            "user_input": "マツキヨは近くにありますか",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782973985776412873150",
            "user_input": "市販薬の購入先",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782974025130304889943",
            "user_input": "マツキヨは近くにありますか",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782974034953233964996",
            "user_input": "ドラッグストアはどこ？",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782974044763563580264",
            "user_input": "2週間くらいです",
            "primary_route": "Counseling",
            "triage_category": "Ask",
            "mismatch_kind": "exempt",
            "dialogue_flags": null
          },
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
          },
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
          }
        ]
      },
      "latency": {
        "pipeline_perf_requests": 3122,
        "total_ms_p50": 9895.44,
        "total_ms_p95": 38871.05,
        "total_ms_max": 227145.5,
        "llm_calls_total": 9212,
        "llm_calls_per_request_avg": 2.95,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 647,
            "latency_ms_sum": 5053398.87,
            "latency_ms_p50": 7848.34,
            "latency_ms_p95": 13152.19
          },
          "medicine_qa/focus_llm": {
            "count": 2974,
            "latency_ms_sum": 3448531.55,
            "latency_ms_p50": 1060.97,
            "latency_ms_p95": 1754.73
          },
          "llm_triage.stage1": {
            "count": 1607,
            "latency_ms_sum": 2447906.06,
            "latency_ms_p50": 1403.06,
            "latency_ms_p95": 2295.42
          },
          "medicine_response_builder.chat_context": {
            "count": 299,
            "latency_ms_sum": 1864825.9,
            "latency_ms_p50": 5555.16,
            "latency_ms_p95": 13908.89
          },
          "missing_info_service": {
            "count": 745,
            "latency_ms_sum": 1745690.34,
            "latency_ms_p50": 2211.8,
            "latency_ms_p95": 2947.21
          },
          "dialogue.intent_router_llm": {
            "count": 688,
            "latency_ms_sum": 895772.16,
            "latency_ms_p50": 1216.85,
            "latency_ms_p95": 1783.56
          },
          "chat_response_service.personalized_advice": {
            "count": 525,
            "latency_ms_sum": 859129.68,
            "latency_ms_p50": 1475.63,
            "latency_ms_p95": 2334.8
          },
          "llm_triage.stage2": {
            "count": 455,
            "latency_ms_sum": 626718.38,
            "latency_ms_p50": 1255.07,
            "latency_ms_p95": 2015.68
          },
          "concierge_agent.meta_architecture": {
            "count": 287,
            "latency_ms_sum": 506450.54,
            "latency_ms_p50": 1694.15,
            "latency_ms_p95": 2371.86
          },
          "concierge_agent.greeting": {
            "count": 150,
            "latency_ms_sum": 278876.3,
            "latency_ms_p50": 1705.04,
            "latency_ms_p95": 2810.44
          },
          "counseling_followup.alt": {
            "count": 175,
            "latency_ms_sum": 256975.07,
            "latency_ms_p50": 1320.89,
            "latency_ms_p95": 1981.2
          },
          "counseling_generator.main": {
            "count": 210,
            "latency_ms_sum": 250875.25,
            "latency_ms_p50": 1124.45,
            "latency_ms_p95": 1723.71
          },
          "concierge_agent.meta_architecture_deep": {
            "count": 68,
            "latency_ms_sum": 152809.2,
            "latency_ms_p50": 2219.77,
            "latency_ms_p95": 3016.74
          },
          "concierge_agent.chitchat": {
            "count": 61,
            "latency_ms_sum": 86894.61,
            "latency_ms_p50": 1243.57,
            "latency_ms_p95": 1697.32
          },
          "concierge_agent.doc_changelog_intro": {
            "count": 45,
            "latency_ms_sum": 62888.77,
            "latency_ms_p50": 1308.98,
            "latency_ms_p95": 1862.15
          },
          "concierge_agent.meta_capabilities": {
            "count": 41,
            "latency_ms_sum": 54896.3,
            "latency_ms_p50": 1171.58,
            "latency_ms_p95": 2327.98
          },
          "llm_medicine_service.select_symptoms": {
            "count": 56,
            "latency_ms_sum": 47626.6,
            "latency_ms_p50": 798.85,
            "latency_ms_p95": 1162.21
          },
          "llm_triage.combined": {
            "count": 21,
            "latency_ms_sum": 34766.56,
            "latency_ms_p50": 1544.03,
            "latency_ms_p95": 2305.76
          },
          "medicine_response_builder.chat_context.answer_stream": {
            "count": 14,
            "latency_ms_sum": 28119.14,
            "latency_ms_p50": 2011.12,
            "latency_ms_p95": 2400.1
          },
          "concierge_agent.doc_privacy": {
            "count": 9,
            "latency_ms_sum": 27845.57,
            "latency_ms_p50": 2996.27,
            "latency_ms_p95": 3532.23
          },
      
```


## ターン別評価 KPI

- 評価ターン数: 13
- ターン rule pass: 11
- reject_no_reco 検知: 1
- comparison_loop 検知: 0
- judge aligned: 0 / judged 0

| scenario | turn | rule | judge | prompt | failures |
|----------|------|------|-------|--------|----------|
| golden-loxonin-home-01 | 0 | PASS | None | None |  |
| golden-loxonin-home-01 | 1 | PASS | None | None |  |
| golden-loxonin-s-variant-01 | 2 | PASS | None | 1 |  |
| golden-warafin-anaphora-01 | 1 | FAIL | None | None | reject_no_reco; missing_context_kw:ロキソニン; must_not_contain:推奨医薬品の情報では回答できません; mu |
| golden-compare-followup-01 | 1 | PASS | None | 1 |  |
| golden-correction-pivot-01 | 2 | PASS | None | 1 |  |
| golden-meta-pivot-01 | 1 | PASS | None | None |  |
| golden-alcohol-anaphora-01 | 1 | PASS | None | None |  |
| golden-clarify-ambiguous-01 | 0 | FAIL | None | None | no_clarify_when_ambiguous:missing_clarify |
| golden-chitchat-health-01 | 0 | PASS | None | None |  |
| golden-session-delete-01 | 0 | PASS | None | None |  |
| golden-thanks-followup-01 | 2 | PASS | None | None |  |
| golden-casual-home-kansai-01 | 1 | PASS | None | None |  |

## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| golden-warafin-anaphora-01 | anaphora | `1786101923479877980363` | t1:reject_no_reco; t1:missing_context_kw:ロキソニン; t1:must_not_contain:推奨医薬品の情報では回答できません; t1:must_refer | medicine_qa |
| golden-clarify-ambiguous-01 | clarify | `1786102074234559363840` | t0:no_clarify_when_ambiguous:missing_clarify | concierge_chitchat |

## 全セッション — 完全トランスクリプト

### golden-loxonin-home-01 — anaphora (PASS)
- session_id: `1786101834139364194297`
- wave: golden-pr
- ロキソニンスレッド — 家にも（greeting リセット禁止）
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 61171ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 5529ms):

おうちにもロキソニンがあるのですね。同じ成分の市販薬を重ねて飲まないよう、用法用量と説明書の注意を確認して使ってください。他に気になることがあれば、いつでも聞いてください。

### golden-loxonin-s-variant-01 — anaphora (PASS)
- session_id: `1786101901488551231698`
- wave: golden-pr
- S 表記フォロー — 文脈維持
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 1922ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`concierge_greeting`, 6484ms):

こんにちは！ロキソニンをお持ちなんですね。こちらは市販薬の相談窓口ですので、頭痛やのどの痛みなどの症状についてお話しできますよ。何かお困りのことがあれば、ぜひ教えてください。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`medicine_qa`, 12806ms):

承知しました。お手元のものは「ロキソニンS」ではなく、医療用の「ロキソニン」の可能性があります。ただし、今回ご提示の推奨情報には市販薬の「ロキソニンS」「ロキソニンSプレミアム」しかないため、Sがつかない製品そのものについては正確に案内できません。お近くの登録販売者に、箱やPTPシートの表示を見せて確認してもらうのが確実です。

### golden-warafin-anaphora-01 — anaphora (REVIEW)
- session_id: `1786101923479877980363`
- wave: golden-pr
- 「それと」併用確認 — active product 維持
#### Turn 1
- **User**: 今ロキソニンを飲んでいます
- **Bot** (`medicine_qa`, 10963ms):

ロキソニンSを服用中とのことですね。一般的には、痛みや発熱を抑える目的で使われる解熱鎮痛薬です。ほかの解熱鎮痛薬やかぜ薬などと重なる場合があるため、追加で別の薬を飲む前は成分の重複に注意してください。不安がある場合は、お近くの登録販売者にご相談ください。

#### Turn 2
- **User**: それと一緒に飲んでも大丈夫？
- **Bot** (`medicine_qa`, 12377ms):

申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。

### golden-compare-followup-01 — medicine_thread (PASS)
- session_id: `1786101947753182174380`
- wave: golden-pr
- 推奨後比較 — comparison ループ禁止
#### Turn 1
- **User**: 頭が痛い
- **Bot** (`unknown`, 26311ms):

頭が痛いんですね、つらいですね。まずは無理をせず、静かな場所で休み、水分をしっかりとってください。イブやバファリンEXは頭痛に使いやすく、カロナールAは胃への負担が比較的少なめです。空腹時は避け、用法用量を守ってください。発熱や強いだるさがあればインフルエンザの可能性もあるので受診を。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 8075ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### golden-correction-pivot-01 — correction (PASS)
- session_id: `1786101982711112450080`
- wave: golden-pr
- ユーザー訂正 — イブへ pivot
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 24041ms):

頭痛いのはつらいですね。まずは少し休んで、水分をとってください。イブやバファリンEXは、急な頭痛を和らげやすい薬です。胃が弱い方、妊娠中、持病や他のお薬がある場合は、カロナールAのほうが使いやすいこともあります。発熱やのどの痛みがあれば、インフルエンザの可能性もあるので無理せず受診を。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 8852ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

#### Turn 3
- **User**: いや、違う、イブの方が気になる
- **Bot** (`medicine_qa`, 13431ms):

イブが気になるなら、主成分はイブプロフェンです。頭痛や発熱時に使われる解熱鎮痛薬で、炎症を伴う痛みにも用いられるタイプです。一般に、同じ解熱鎮痛薬でもアセトアミノフェンとは成分が異なり、使い分けの判断には体質や胃の弱さ、持病、服用中の薬が関わるため、その点が気になる場合はお近くの登録販売者にご相談ください。

### golden-meta-pivot-01 — pivot (PASS)
- session_id: `1786102029822706262755`
- wave: golden-pr
- 医薬品スレッド中のメタ質問 → Concierge
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_qa`, 11548ms):

ロキソニンS（主成分：ロキソプロフェンナトリウム水和物）は、痛みや発熱を抑える解熱鎮痛薬です。副作用として比較的みられるのは胃の不快感、腹痛、吐き気などの消化器症状ですが、まれに重い副作用が起こることもあります。重い副作用として、ショック・アナフィラキシー、重い皮膚症状、腎障害、消化管出血・胃潰瘍、呼吸困難などがあり、発疹、息苦しさ、強い腹痛、黒い便、血を吐く、むくみ、尿が出にくいなどの症状があれば、すぐに服用をやめて医療機関を受診してください。

#### Turn 2
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 4014ms):

技術スタックは、バックエンドが FastAPI、フロントエンドが HTML/CSS/バニラ JavaScript です。

チャット入力は HTTP エンドポイントで受け、回答の配信には SSE を使っています。

市販薬の候補選定は、症状や効能、年齢、副作用、相互作用などを組み合わせたルールベースのスコアリングで行います。

読み上げや翻訳は環境によって使い分けていて、AWS ステージングでは Amazon Polly と Amazon Translate、GCP 側では Google Cloud Text-to-Speech と DeepL を使っています。

### golden-alcohol-anaphora-01 — anaphora (PASS)
- session_id: `1786102045916368407724`
- wave: golden-pr
- 指示語なし併用禁忌 — ロキソニン文脈
#### Turn 1
- **User**: 今ロキソニン飲んでます
- **Bot** (`medicine_qa`, 13546ms):

ロキソニンSを服用中とのことですね。一般に、同じ成分や同系統の解熱鎮痛薬を重ねて飲まないこと、空腹時を避け、用法・用量を守ることが大切です。症状が続く、胃痛や発疹など気になる症状がある場合は、服用を続けず医師またはお近くの登録販売者にご相談ください。

#### Turn 2
- **User**: お酒飲んでも平気？
- **Bot** (`medicine_qa`, 14247ms):

ロキソニンSを飲んでいる間の飲酒は、できれば避けるのが無難です。ロキソプロフェンは胃腸への負担が出ることがあり、アルコールで胃痛・吐き気・胃荒れなどが起こりやすくなる可能性があります。少量でも体調によっては負担になるため、服用中や服用直後の飲酒は控えてください。

### golden-clarify-ambiguous-01 — clarify (REVIEW)
- session_id: `1786102074234559363840`
- wave: golden-pr
- 品目未特定の飲み合わせ — Clarify 期待
#### Turn 1
- **User**: 他の薬と一緒に飲んでも大丈夫？
- **Bot** (`concierge_chitchat`, 3339ms):

飲み合わせは、市販薬の種類や今飲んでいるお薬によって変わります。もし候補の市販薬名や、他に飲んでいるお薬の名前が分かれば、注意したい組み合わせを一緒に確認できます。

### golden-chitchat-health-01 — chitchat (PASS)
- session_id: `1786102077854089324444`
- wave: golden-pr
- 品目なし健康一般論 — 拒否テンプレ禁止
#### Turn 1
- **User**: 最近疲れが取れなくて、市販薬に頼りすぎかもしれません
- **Bot** (`concierge_chitchat`, 3264ms):

疲れが抜けない感じ、つらいですよね。市販薬に頼りすぎかも…と気になっているなら、今どんな疲れ方かや、飲んでいる市販薬の種類を一緒に整理できます。気になることがあれば、お気軽にお聞かせください。

### golden-session-delete-01 — session_ops (PASS)
- session_id: `1786102081389801830434`
- wave: golden-pr
- 削除依頼 — SessionOps 一貫
#### Turn 1
- **User**: この会話を削除して
- **Bot** (`memory_delete_confirm`, 325ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### golden-thanks-followup-01 — medicine_thread (PASS)
- session_id: `1786102081991760980532`
- wave: golden-pr
- 感謝後も医薬品スレッド継続
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_qa`, 9605ms):

ロキソニンSの主成分ロキソプロフェンでは、比較的みられやすい副作用として胃痛、胃の不快感、吐き気、食欲不振、眠気、めまい、発疹などがあります。まれですが重い副作用として、ショック・アナフィラキシー、重い皮膚症状、腎障害、消化管出血・胃潰瘍、消化管穿孔、心不全、心筋梗塞・脳血管障害、間質性肺炎などが報告されています。強い腹痛、黒い便、吐血、息苦しさ、全身の発疹、顔やのどの腫れなどがあれば、服用を中止してすぐ受診してください。

#### Turn 2
- **User**: ありがとう
- **Bot** (`concierge_thanks`, 1705ms):

どういたしまして。市販薬のことでまた気になることがあれば、いつでも聞いてくださいね。

#### Turn 3
- **User**: あと眠くなる？
- **Bot** (`medicine_qa`, 10409ms):

はい、ロキソニンSでは眠気やめまいが比較的みられることがあります。強い眠気は多くありませんが、服用後にぼんやりする・ふらつく感じがあれば、車の運転や危険な作業は避けてください。なお、ロキソニンSプレミアムは無水カフェインを含むため、眠気が出にくい場合もありますが、個人差があります。

### golden-casual-home-kansai-01 — anaphora (PASS)
- session_id: `1786102104493749236719`
- wave: golden-pr
- 関西弁フォロー — うちにも
#### Turn 1
- **User**: ロキソニンの写真見せて
- **Bot** (`medicine_qa`, 3184ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: うちにもあるわ
- **Bot** (`medicine_qa`, 5659ms):

おうちにもロキソニンがあるのですね。同じ成分の市販薬を重ねて飲まないよう、用法用量と説明書の注意を確認して使ってください。他に気になることがあれば、いつでも聞いてください。

