# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-08)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-08T02:48:49.757872+00:00
- 所要時間: 218.0s
- シナリオ/セッション: 4 / 総ターン: 16
- 自動合格: 4 / 要確認: 0
- GPT ユーザーシミュレータ: True
- GPT スケールモード: True

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **tier1_allergen**: 1/1 自動合格 / 4 ターン
- **tier1_anaphora**: 1/1 自動合格 / 4 ターン
- **tier1_correction**: 1/1 自動合格 / 4 ターン
- **tier1_triage**: 1/1 自動合格 / 4 ターン

## IntentRouter Shadow / Dispatch KPI

_`--skip-metrics` のため計測スキップ_

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| tier1_allergen | 1 | 4 | 1 | 0 |
| tier1_anaphora | 1 | 4 | 1 | 0 |
| tier1_correction | 1 | 4 | 1 | 0 |
| tier1_triage | 1 | 4 | 1 | 0 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 16
- end-to-end: p50 14143.0ms / **p95 22445.0ms** / max 23294.0ms
- pipeline total: p50 13781.2ms / p95 22102.22ms / max 22943.62ms
- LLM 呼び出し: 合計 78 / リクエストあたり平均 4.88

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| medicine_qa/focus_llm | 39 | 40038.94 | 977.65 | 1345.99 |
| medicine_response_builder.chat_context | 5 | 24513.19 | 5301.18 | 6194.39 |
| llm_triage.stage1 | 12 | 19092.02 | 1594.3 | 1646.66 |
| explanation_generator.batch_usage_notes | 4 | 16735.45 | 4258.56 | 4266.05 |
| missing_info_service | 5 | 12189.98 | 2348.5 | 2677.03 |
| dialogue.medicine_context_classifier | 7 | 9964.43 | 1461.38 | 1575.88 |
| chat_response_service.personalized_advice | 4 | 5924.88 | 1642.62 | 1647.17 |
| llm_triage.stage2 | 2 | 2844.5 | 1271.68 | 1572.82 |

## 意図評価（intent evaluation）

- 追跡セッション: 0
- counseling_detail マッチ: 0
- route ログマッチ: 0

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786157329760015514850` | gpt-gpt-correction-user | 4 | 0/0 | 0 | — |
| `1786157404574643787800` | gpt-gpt-allergy-check | 4 | 0/0 | 0 | — |
| `1786157448468482463049` | gpt-gpt-vague-to-specific | 4 | 0/0 | 0 | — |
| `1786157496211417699561` | gpt-gpt-implicit-short | 4 | 0/0 | 0 | — |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "intent_router_shadow_skipped": true,
  "latency_this_run": {
    "turns_measured": 16,
    "e2e_ms_p50": 14143.0,
    "e2e_ms_p95": 22445.0,
    "e2e_ms_max": 23294.0,
    "phase_breakdown": {
      "pipeline_perf_requests": 16,
      "total_ms_p50": 13781.2,
      "total_ms_p95": 22102.22,
      "total_ms_max": 22943.62,
      "llm_calls_total": 78,
      "llm_calls_per_request_avg": 4.88,
      "llm_by_path": {
        "medicine_qa/focus_llm": {
          "count": 39,
          "latency_ms_sum": 40038.94,
          "latency_ms_p50": 977.65,
          "latency_ms_p95": 1345.99
        },
        "medicine_response_builder.chat_context": {
          "count": 5,
          "latency_ms_sum": 24513.19,
          "latency_ms_p50": 5301.18,
          "latency_ms_p95": 6194.39
        },
        "llm_triage.stage1": {
          "count": 12,
          "latency_ms_sum": 19092.02,
          "latency_ms_p50": 1594.3,
          "latency_ms_p95": 1646.66
        },
        "explanation_generator.batch_usage_notes": {
          "count": 4,
          "latency_ms_sum": 16735.45,
          "latency_ms_p50": 4258.56,
          "latency_ms_p95": 4266.05
        },
        "missing_info_service": {
          "count": 5,
          "latency_ms_sum": 12189.98,
          "latency_ms_p50": 2348.5,
          "latency_ms_p95": 2677.03
        },
        "dialogue.medicine_context_classifier": {
          "count": 7,
          "latency_ms_sum": 9964.43,
          "latency_ms_p50": 1461.38,
          "latency_ms_p95": 1575.88
        },
        "chat_response_service.personalized_advice": {
          "count": 4,
          "latency_ms_sum": 5924.88,
          "latency_ms_p50": 1642.62,
          "latency_ms_p95": 1647.17
        },
        "llm_triage.stage2": {
          "count": 2,
          "latency_ms_sum": 2844.5,
          "latency_ms_p50": 1271.68,
          "latency_ms_p95": 1572.82
        }
      },
      "breakdown_steps_avg_ms": {
        "after_counseling_flow": 1558.48,
        "after_get_session_db": 12.21,
        "after_medicine_qa_route": 2530.35,
        "after_security": 80.1,
        "after_triage": 1486.02,
        "after_triage_follow_ups": 1512.24,
        "before_emoji_route": 80.78,
        "before_llm_setup": 14.41,
        "before_medicine_qa_route": 1923.92,
        "before_orchestrator": 2126.22,
        "before_security": 18.05,
        "before_triage": 80.79,
        "emit_cards_early": 9266.48,
        "explanation_phase_done": 17191.41,
        "explanation_phase_start": 17191.4,
        "line_carousel_push": 17181.46,
        "medicine_information_qa_end": 9837.16,
        "medicine_information_qa_start": 4678.83,
        "medicine_qa_early_route_end": 4246.44,
        "medicine_qa_early_route_start": 3508.31,
        "medicine_qa_physical_priority": 1548.04,
        "medicine_qa_thread_route_end": 9043.4,
        "medicine_qa_thread_route_start": 3605.9,
        "moderation_done": 1558.52,
        "nlu_batch_done": 4260.7,
        "nlu_batch_start": 2595.47,
        "parsed_message": 9.96,
        "personalized_advice": 18682.78,
        "post_start": 9.86,
        "product_image_fast_path_end": 9837.17,
        "product_image_fast_path_start": 4678.83,
        "rb_explain_batch_done": 17179.95,
        "rb_missing_info_done": 6754.12,
        "rb_scoring_only_done": 9266.45,
        "rule_based_scoring_only_done": 14893.53,
        "rule_based_start": 4307.93,
        "safety_gate_done": 1510.91,
        "session_db_read": 9.99,
        "short_symptom_triage_skip_llm": 93.54
      }
    }
  },
  "turn_eval_kpi": {
    "turns_evaluated": 0,
    "turn_rule_pass": 0,
    "reject_no_reco": 0,
    "comparison_loop": 0,
    "judge_turns": 0,
    "judge_aligned": 0,
    "turn_rows": []
  }
}
```


## ターン別評価 KPI

- 評価ターン数: 0
- ターン rule pass: 0
- reject_no_reco 検知: 0
- comparison_loop 検知: 0
- judge aligned: 0 / judged 0

| scenario | turn | rule | judge | prompt | failures |
|----------|------|------|-------|--------|----------|

## 要確認シナリオ

_自動評価で不一致なし（手動確認推奨）_

## 全セッション — 完全トランスクリプト

### gpt-gpt-correction-user — tier1_correction (PASS)
- session_id: `1786157329760015514850`
- wave: gpt-scale
- persona: gpt-correction-user
- 症状訂正
#### Turn 1
- **User**: 鼻水が止まらない
- **Bot** (`unknown`, 17079ms):

鼻水が止まらないのはつらいですね。鼻水が中心なら、まずは鼻づまりやくしゃみにも使いやすいスカイブブロンHIや、鼻に直接使えるスカイブブロンNAスプレーが合いやすいです。発熱・強いだるさがあれば風邪やインフルエンザの可能性もあるので受診を。持病や妊娠中なら購入前にご相談ください。

#### Turn 2
- **User**: やっぱ咳の方がキツい。どんな薬がいい？
- **Bot** (`medicine_qa`, 15670ms):

今回の推奨医薬品の中には、咳を主な対象にした薬は含まれていません。スカイブブロンHI・スカイブブロンNAスプレー・スカイブゴールドはいずれも鼻症状向けで、イブは痛みや発熱向けのため、咳がつらい場合に合うとは言えません。咳に合う薬の選択は、この情報だけでは適切に案内できないため、お近くの登録販売者にご相談ください。

#### Turn 3
- **User**: 咳がひどくて夜も眠れないんだけど、何かいい市販薬ある？
- **Bot** (`medicine_qa`, 15005ms):

スカイブブロンHI：花粉,ハウスダスト(室内塵)などによる次のような鼻のアレルギー症状の緩和:くしゃみ,鼻みず,鼻づまりなどの症状緩和に用いる一般用医薬品です。スカイブブロンNAスプレー：急性鼻炎,アレルギー性鼻炎又は副鼻腔炎による次の諸症状の緩和:

#### Turn 4
- **User**: 咳がひどくて、特に夜が辛いんだけど、咳に効く市販薬はないの？
- **Bot** (`medicine_qa`, 23294ms):

今回の推奨医薬品の中には、咳を主な対象にした市販薬はありません。スカイブブロンHI・スカイブブロンNAスプレー・スカイブゴールドはいずれも鼻症状向けで、イブは痛みや発熱向けのため、夜につらい咳に合うとは言えません。咳に効く市販薬の選択はこの情報だけでは適切に案内できないため、お近くの登録販売者にご相談ください。

### gpt-gpt-allergy-check — tier1_allergen (PASS)
- session_id: `1786157404574643787800`
- wave: gpt-scale
- persona: gpt-allergy-check
- アレルギー確認
#### Turn 1
- **User**: 蕁麻疹出た
- **Bot** (`physical_no_recommendation`, 5951ms):

皮膚の症状ですね、つらいですね。かゆみ止めの内服や外用で様子を見られることもあります。広がる・呼吸が苦しい・唇や顔が腫れる場合は、すぐに医療機関へ。出始めた時期や範囲を教えていただくと、より安全な市販薬をご案内できます。

#### Turn 2
- **User**: 最近、卵料理を食べた後に出たんです。卵アレルギーの可能性が心配です。
- **Bot** (`unknown`, 22445ms):

卵料理の後に蕁麻疹やかゆみが出たなら、卵アレルギーの可能性もあります。まずは卵をいったん避けて、症状が強い時はかゆみ・発疹を抑える市販薬で様子見を。総合感冒薬は今回の主症状には合いにくいです。息苦しさ、唇や顔の腫れ、広がる発疹はすぐ受診してください。

#### Turn 3
- **User**: やっぱり、卵アレルギーの可能性があるなら、気をつけた方がいいよね。どんな市販薬が使えるの？
- **Bot** (`medicine_qa`, 6973ms):

卵アレルギーがある場合、エスタックイブファイン顆粒に卵由来添加物が含まれていないか、包装の成分表記でご確認ください。不安がある場合は登録販売者に相談してください。

#### Turn 4
- **User**: エスタックイブファイン顆粒の成分表記、確認してみるね。卵由来のものが入ってなければ大丈夫かな？
- **Bot** (`medicine_qa`, 4628ms):

イブを海外へ持ち込む際の一般的な注意点です。① 元の包装・成分表記ラベルを残す ② 個人使用の量に収める（大量持ち込みは別審査になりやすい） ③ 必要に応じて医師の診断書・処方箋写し・使用目的メモを用意 ④ 入国カードや税関で申告が求められる場合がある ⑤ 最新の規制は外務省「海外安全ホームページ」や渡航先大使館で確認。不安があれば出発前に登録販売者や航空会社にもご確認ください。

### gpt-gpt-vague-to-specific — tier1_triage (PASS)
- session_id: `1786157448468482463049`
- wave: gpt-scale
- persona: gpt-vague-to-specific
- 曖昧→具体化
#### Turn 1
- **User**: なんか調子悪い
- **Bot** (`unknown`, 17772ms):

「なんか調子悪い」ときは、まず無理せず休んでください。倦怠感・疲労感があるので、ハイチオールC系で体のだるさのケア、もしむくみや頭重感、水分バランスの乱れが気になるならアルピタンγも候補です。発熱や咳、のど痛みがあればインフルエンザも疑って受診を。症状が続く・強い場合は早めに相談してください。

#### Turn 2
- **User**: なんか体がだるくて、頭も重い感じがする。
- **Bot** (`medicine_qa`, 4319ms):

ハイチオールCプラスはアスコルビン酸 パントテン酸カルシウム L−システイン（解熱鎮痛）、ハイチオールCホワイティアはアスコルビン酸 パントテン酸カルシウム L−システイン（解熱鎮痛）、アルピタンγ(五苓散)はインチンコウ 桂枝 タクシャ チョレイ ビャクジュツ ブクリョウ（解熱鎮痛）。まず主成分の系統（解熱鎮痛薬 / アセトアミノフェン）で絞り込むと選びやすくなります。

#### Turn 3
- **User**: ハイチオールCプラスってどんな効果があるの？
- **Bot** (`medicine_qa`, 9527ms):

ハイチオールCプラスは、アスコルビン酸・パントテン酸カルシウム・L-システインを含む製品で、今回の候補では全身のだるさ（全身倦怠）や二日酔いのケアに使えるのが特徴です。ハイチオールCホワイティアも主成分は同じなので、効き目の強さや胃への負担に大きな差はつきにくく、使い分けは製品名や入手しやすさで選ぶイメージです。いっぽうアルピタンγ(五苓散)は漢方処方で、のどの渇きや尿量が少ない、むくみ感を伴う二日酔い寄りの不調に向きやすく、だるさ中心ならハイチオールCプラスのほうが候補にしやすいです。

#### Turn 4
- **User**: ハイチオールCプラスは飲める？
- **Bot** (`medicine_qa`, 12484ms):

はい、ハイチオールCプラスは飲めます。今回の候補の中では、全身のだるさ（全身倦怠）や二日酔いに使える製品です。用法・用量は成人（15才以上）で1回2錠を1日3回、7才〜14才は1回1錠を1日3回、水またはぬるま湯で服用し、7才未満は服用しないでください。

### gpt-gpt-implicit-short — tier1_anaphora (PASS)
- session_id: `1786157496211417699561`
- wave: gpt-scale
- persona: gpt-implicit-short
- 超短文指示語
#### Turn 1
- **User**: のど痛い
- **Bot** (`unknown`, 18969ms):

のど痛いのはつらいですね。まずはスカイブブロンのどスプレーやルルのどスプレーで、痛む部分を直接ケアすると楽になりやすいです。発熱や強いだるさがあれば、イブスリーショットプレミアムも候補です。水分と加湿を心がけ、息苦しさや高熱、インフルエンザが疑われる時は受診してください。

#### Turn 2
- **User**: それ？
- **Bot** (`medicine_qa`, 8341ms):

スカイブブロンのどスプレーはポビドンヨード（解熱鎮痛）、イブスリーショットプレミアムはアセトアミノフェン NSAID 無水カフェイン 酸化マグネシウム（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））、ルルのどスプレーはアズレンスルホン酸ナトリウム水和物（解熱鎮痛）。胃が弱い・NSAIDsが合わない場合はアセトアミノフェン系が候補になりやすいです。

#### Turn 3
- **User**: 平気？
- **Bot** (`medicine_qa`, 14143ms):

はい、一般には使えますが、どれが「平気」かは症状と体質で少し変わります。のどの痛み中心ならスカイブブロンのどスプレーやルルのどスプレーが候補で、発熱や全身の痛みもあるならイブスリーショットプレミアムが候補です。過去に薬で具合が悪くなったことがある、妊娠中・授乳中、持病がある場合は自己判断せず、お近くの登録販売者にご相談ください。

#### Turn 4
- **User**: 1番？
- **Bot** (`medicine_qa`, 7333ms):

スカイブブロンのどスプレーはポビドンヨード（解熱鎮痛）、イブスリーショットプレミアムはアセトアミノフェン NSAID 無水カフェイン 酸化マグネシウム（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））、ルルのどスプレーはアズレンスルホン酸ナトリウム水和物（解熱鎮痛）。胃が弱い・NSAIDsが合わない場合はアセトアミノフェン系が候補になりやすいです。

