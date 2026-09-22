# Jev 次フロー実行計画（Phase 1C → Focus shadow）

- 作成日: 2026-09-21
- 位置づけ: Phase 1 local shadow（Gate A-code Passed）完了後の **次実行フロー正本**
- 前提: Gate A-accuracy **Not Passed**（live `012129` 実行済）、Gate B **Hard No-Go**、PRIMARY / staging / production **Hard No-Go**、Focus 本配線 **No-Go**
- 参照:
  - Progress: `JEV_PROGRESS_AND_NEXT_PLAN_20260921.md`
  - Supervisor: `JEV_PHASE1_LOCAL_SHADOW_SUPERVISOR_REPORT_20260921.md`
  - Phase0: `JEV_PHASE0_CONTRACT_FREEZE_20260921.md`
  - Synthesis: `JEV_PARALLEL_SYNTHESIS_20260921.md`
  - Next targets: `JEV_NEXT_TARGETS_HYPOTHESIS_20260921.md`
  - Pharmacist draft: `JEV_SAFETY_FIXTURE_PHARMACIST_REVIEW_20260921.md`
  - A-accuracy 判定: `JEV_GATE_A_ACCURACY_VERDICT_20260922.md`
  - 現行 live: `log/analysis/jev_intent_router_eval_10_20260922_012129.{json,md}`

## 0. 現在地と辛口前提

| 事実 | 意味 |
| --- | --- |
| Gate A-code Passed | 本線非干渉・PRIMARY ignore・unit 緑。**精度合格ではない** |
| Gate A-accuracy Not Passed | live `012129` は方法論充足だが CI 保守・コスト純減未達。判定正本 `JEV_GATE_A_ACCURACY_VERDICT_20260922.md`。ここで止まる |
| pilot `013619` / 旧 `033321` | **smoke / 参考値のみ**。Gate A-accuracy クローズにも Gate B 入場にも使わない |
| `pharmacist_reviewed_draft` | 人間医療承認前。CI hard-fail 根拠にしてはならない |
| Focus / Eligibility 統合 | **禁止**（仮説 T2 採用）。Focus は QA 内観点、Eligibility は route/pivot |

**原則:** 速度・コストが合格しても、精度・安全・運用のいずれか1つが未達なら No-Go。flag を先に立ててから評価を埋めるな。

---

## 1. Phase 1C — live 再評価（Gate A-accuracy）

### 1.1 目的

production state 契約での live 再評価。**現行結果:** `20260922_012129` → **Not Passed**（点推定 latency は達成、scenario-cluster CI 下限・コスト純減は未達）。追加 live は方法論変更後のみ。

### 1.2 実行条件（入場）

- local で Jev API 接続が安定していること（接続拒否の再測定は採用しない）。
- `JEV_API_KEY` は **存在確認のみ**。値・ログ・レポートへの露出禁止。
- eval は `jev:minimal` **のみ**（`with_baseline_triage` 再検証禁止）。
- 接続失敗・schema invalid・timeout は **accuracy 分母から除外**し、別集計する。
- レポートは `log/analysis/jev_intent_router_eval_*` に残し、Progress からリンクする。

### 1.3 Acceptance criteria（全部必須）

| ID | 基準 | 辛口注記 |
| --- | --- | --- |
| **1C-A** | pilot joint accuracy **100%**（primary + 必須 sub-route） | primary 単独 100% は不合格。joint で判定 |
| **1C-L** | latency 短縮が **avg ≥ 900ms OR P95 ≥ 2500ms**（current − Jev） | OR。片方未達でももう片方が条件を満たせば latency は Pass。ただし **両方未達は Fail** |
| **1C-C** | cost **分離報告** | (a) OpenAI IntentRouter 相当 saved / call 推定、(b) Jev usage + 概算コスト、(c) **総分類費（a+b）** を混同せず並記。Phase 1 で saved 実測ゼロでも「未実測」と明示すること |
| **1C-S** | API error / eval failure / accuracy を **3系統で別集計** | 接続失敗を accuracy に混ぜた報告は即破棄 |
| **1C-R** | 各ケース repeat ≥ 3（推奨 ≥ 10）、current/Jev 交互またはランダム | 不完全 run を採用しない |

**Pass 定義:** 1C-A ∧ 1C-L ∧ 1C-C ∧ 1C-S ∧ 1C-R。

**Fail 時:** Gate A-accuracy は閉じない。dev shadow 議論に進むな。原因が接続なら再実行、精度なら fixture/adapter 調査。pilot を拡張して合格を捏造するな。

### 1.4 明示的に「合格にしない」もの

- expanded fixture の draft / pharmacist draft 結果
- unit 111 green
- 旧 eval 形状のみでの 30/30
- latency だけ合格して accuracy を後回しにする提案

---

## 2. Phase 1D — dev shadow 準備チェックリスト（**まだ有効化しない**）

目的: 明示承認後に `JEV_ENABLED=true` + `JEV_INTENT_ROUTER_SHADOW=true` を **ワンショットで立てられる状態**にする。  
**本書時点および 1D 完了時点でも、実際の enable は禁止。**

| # | 項目 | Done の定義 | 未完時 |
| --- | --- | --- | --- |
| D1 | Gate A-accuracy Pass | §1 全基準 | 準備作業は可、enable 議論不可 |
| D2 | expanded fixture **人間医療承認** | `label_status` が `gate_b_approved`（仮称）等へ昇格。`pharmacist_reviewed_draft` のままは不可 | Gate B Hard No-Go |
| D3 | joint / high-risk FN 採点定義 freeze | Test Plan に `accept_alternate_primaries` / FN 定義を固定 | 採点議論中は enable 禁止 |
| D4 | `JEV_API_KEY` の **dev 配備手順** | 誰が・どこに・ローテーション誰が持つまで文書化。値は文書に書かない | 配備未確認で flag を立てるな |
| D5 | shadow log sink | path=`log/jev_intent_router_shadow.jsonl`、閲覧権限、保持期間 | 観測不能なら enable 禁止 |
| D6 | 禁止フィールド監査手順 | raw text / secret / 生 ID / 不要 PII が残らないことの目視チェックリスト | 未監査で本番相当ログを増やすな |
| D7 | flag 反映方式 | 反映経路と最大反映時間、誤 PRIMARY が実行に効かないことの再確認 | — |
| D8 | rollback | 担当者 + `JEV_ENABLED=false` 即時手順。演習メモ1通 | 担当不明は No-Go |
| D9 | 明示承認チケット | 「dev shadow 開始」の署名（人）。1D 完了 ≠ 承認 | 承認なし enable = 違反 |

**1D 完了の意味:** 「承認があれば立てられる」。**「立ててよい」ではない。**

---

## 3. Gate B — dev shadow 運用合格基準

Gate B は **dev shadow を開始したあとの運用ゲート**であり、1C/1D の入場条件ではない。  
入場（開始可否）は §2 + 医療ラベル承認 + A-accuracy。合格（primary 設計に進む可否）は本節。

### 3.1 数値ゲート（全部必須）

| 指標 | 合格線 | 辛口 |
| --- | --- | --- |
| eligible decisions | **≥ 150** | shadow 対象となった決定のみ。flag OFF 期間や接続失敗は分母外 |
| 全体 disagreement | **≤ 0.5%** | legacy vs Jev（joint）。超過は即停止・調査 |
| high-risk disagreement | **全件レビュー、未解決 0** | Emergency / Security / medical_examination 系 |
| high-risk **FN** | **= 0** | 1 件でも疑義あれば No-Go。FP は許容側（安全側誤検出） |
| fallback / usage / latency / log completeness | 欠損なく集計可能 | ログ穴 = 観測失敗 = Gate B Fail |

### 3.2 Gate B でやってはいけないこと

- pilot 100% や unit 緑を Gate B Pass と呼ぶ
- disagreement を「だいたい同じ」で丸める
- FN 疑義を「要観察」で先送りして PRIMARY 設計に進む
- SessionOps / Emergency を primary 候補に混ぜる

### 3.3 Gate B Pass 後に初めて議論してよいこと

- Phase 2 primary canary の **設計着手**（実装・enable は別承認）
- OpenAI `dialogue.intent_router_llm` cost 70% 削減の **実測開始**（shadow だけでは saved=0 固定のまま）

---

## 4. 次の Jev 差し込み対象: `medicine_qa_focus_llm`（shadow-only）

### 4.1 方針（固定）

- **Eligibility とマージしない。** Focus は QA に入った後の観点分類。route / Physical pivot は Eligibility の責務のまま。
- 当面は **shadow 評価のみ**。実行 focus・回答生成・推薦ランキングを Jev で置換しない。
- IntentRouter Phase 1 の shadow と **別 flag / 別 JSONL / 別 DTO** を前提にする（混線禁止）。
- Gate B（IntentRouter）未達でも **設計・fixture・offline eval は進めてよい**。dev enable / primary は別ゲート。

### 4.2 `chat_post_pipeline` 上の位置

現行シーケンス（要約）:

```text
run_chat_post_pipeline
  → SafetyGate pre / SessionOps fast / triage / sync_routing_context
  → IntentRouter resolve_route（ここが現行 Jev IntentRouter shadow）
  → … counseling / moderation …
  → resolve_medicine_qa_route(...)          ← Eligibility（触らない）
  → infer_medicine_qa_focuses(...)          ← ★ Focus LLM 差し込み点
  → medicine_qa / concierge / physical 分岐・回答
```

**Jev Focus shadow の置き場所:**

1. `resolve_medicine_qa_route` が確定した **後**
2. `infer_medicine_qa_focuses` が **現行 focus を確定した直後**
3. 現行 `focuses` を実行に使ったまま、immutable snapshot で Jev を **1 回だけ** schedule
4. Jev 結果は専用 JSONL（例: `log/jev_medicine_qa_focus_shadow.jsonl`）へ fail-open 記録
5. 本線の `focuses` / response / route_decision は **一切変更しない**

根拠コード: `src/handlers/chat/chat_post_pipeline.py`（`before_medicine_qa_route` → `resolve_medicine_qa_route` → `infer_medicine_qa_focuses` → `after_medicine_qa_route`）。

### 4.3 まだ置換・統合しないもの

| 対象 | 理由 |
| --- | --- |
| `resolve_medicine_qa_route` / Eligibility LLM | Physical FN リスク。Focus と責務分離（T2） |
| Focus → Eligibility 1-call 統合 | pivot 失敗が回答観点誤りの陰に隠れる |
| `llm_triage` stage1/2 | safety FN 直撃。IntentRouter Gate B 後も後段 |
| `store_inquiry_handler.classify` | 到達頻度・Physical 競合未計測 |
| IntentRouter PRIMARY | Gate B 未達 |
| SessionOps / Emergency / Security 単独確定 | 既存契約どおり禁止 |
| session への focus 永続化を「Jev のため」に先行実装 | §5.2 で別決定。Jev 用の追加 LLM 呼び出し禁止は維持 |

### 4.4 Success metrics（Focus shadow eval）

最小セット案: 60 cases（各 focus ≥5、conflict pair、指示語、general、**physical pivot ≥6**）。各 case ≥3 反復。

| 指標 | 合格線 |
| --- | --- |
| multi-label **macro-F1** | current Focus LLM に対し **非劣性**（差 −2.0pt 以内を仮線。最終は fixture freeze 時に Test Plan へ固定） |
| exact / primary focus | 参考。macro-F1 より優先しないが大幅劣化は Fail |
| **physical_symptom_pivot FN** | **= 0**（症状 pivot を focus 確定で潰さない） |
| schema / unknown enum | invalid 時は現行 rule focus 維持（実行不変） |
| 本線差分 | shadow ON/OFF で response / route **差分 0** |

**Fail 時の次手:** Focus shadow 継続または停止。Eligibility 統合で「救う」な。pivot FN が出たら adapter の Noul/`physical_symptom_pivot` を厳格化するか、当該ケースを Jev 対象外にする。

### 4.5 IntentRouter state の `medicine_qa_focus` について

現行: builder は読取可能だが、pipeline が session に focus を書いていないため **通常 None**（許容）。  
Focus Jev 評価は **Focus path 専用 shadow** で行い、「IntentRouter state に focus が無いから Gate B 不可」と誤診断しないこと。session 永続化は §5.2。

---

## 5. Jev 外の並列プロセス改善

IntentRouter / Focus のゲートとは独立に進めてよい。Jev enable の代替にはならない。

### 5.1 Emergency keyword vs hypothetical 採点ハーネス

- 目的: 明示 Emergency・婉曲・**仮定 / 引用 / 否定**を分離採点し、間接 FN（hard Concierge→Emergency 検出を失敗扱い等）を作らない。
- 成果物: scoring harness（`accept_alternate_primaries` / `emergency_fn_exempt` 等）を Test Plan に freeze。
- Gate: expanded の人間承認前でも harness 仕様は確定してよい。**ラベル承認なしで CI hard-fail は禁止**。

### 5.2 session focus persistence の決定

- 現状: `chat_post_pipeline` は focus を local / request_scope に保持し、**session 未永続**。
- 決定すべきこと（Yes/No + キー名 + 寿命）:
  - IntentRouter shadow 観測品質のため session に書くか
  - Focus Jev shadow のためだけに書くか（推奨: **書かない** / 既存値のみ）
  - stale / conflicting 時の破棄条件
- **禁止:** Jev 評価のために focus LLM を追加実行する。決定が遅れるなら欠落（None）のまま A-accuracy / Focus offline eval を進める。

### 5.3 OpenAI classifier cost dashboard

- 分離必須:
  1. `dialogue.intent_router_llm`（および将来 Focus / Eligibility / triage）の OpenAI 実費
  2. Jev usage 概算
  3. 総分類費 = 1+2
- Phase 1 shadow 中は `legacy_saved_calls=0` 固定でよいが、dashboard 骨格は先に用意する。
- 「OpenAI 70%削減」を総分類費削減と読み替えた報告は却下。

---

## 6. Explicit No-Go リスト

以下は **現時点および本計画の当該ゲート未達中は禁止**。例外は明示承認文書のみ。

| # | No-Go | 解除条件（最短） |
| --- | --- | --- |
| N1 | `JEV_ENABLED` / `JEV_INTENT_ROUTER_SHADOW` の **dev 有効化** | A-accuracy Pass + 医療ラベル承認 + 1D 全項目 + 明示承認 |
| N2 | `JEV_INTENT_ROUTER_PRIMARY=true` の有効化・PRIMARY 実装 | Gate B Pass + Phase 2 設計承認 |
| N3 | staging / production への Jev 展開 | dev primary 完了 + 別明示承認 |
| N4 | pilot / unit / pharmacist draft を Gate B Pass と呼ぶこと | 禁止（解除なし） |
| N5 | expanded fixture の CI accuracy **hard-fail** | `gate_b_approved` 後のみ |
| N6 | `with_baseline_triage` / `baseline_triage_hint` 復活 | 原則永久 No-Go（別仮説として再起票が必要） |
| N7 | Focus + Eligibility **統合 call** | T2 棄却の再裁定 + physical pivot FN=0 の独立証明 |
| N8 | Focus / Eligibility / triage の **実行置換**（shadow 以外） | 各 path の専用 Gate Pass |
| N9 | SessionOps の Jev primary | 方針変更の正式棄却文書 |
| N10 | Emergency / Security / medical_examination の Jev **単独確定** | 不可（二重ゲート必須） |
| N11 | Jev 陰性で既存高リスク陽性の解除 | 不可 |
| N12 | `TYPESAFE_API_KEY` fallback を本番 client に入れる | 不可（eval 残骸の本番化禁止） |
| N13 | 接続失敗 run / 不完全 live を accuracy 根拠にする | 不可 |
| N14 | Focus shadow を IntentRouter Gate B 未達の「代替成果」として報告する | 独立トラックとしてのみ可。IntentRouter ゲートの代用禁止 |

---

## 7. 推奨実行順（直近）

1. **Phase 1C** live 再評価（§1）→ Gate A-accuracy を閉じる or Fail 記録
2. 並列: Emergency/hypothetical harness freeze（§5.1）、cost dashboard 骨格（§5.3）、session focus 決定（§5.2）
3. **Phase 1D** チェックリスト消化（§2）— **enable しない**
4. expanded 人間医療承認 → のみ Gate B **開始**可否を再判定
5. Gate B 運用（§3）合格後に Phase 2 設計
6. **並行トラック:** `medicine_qa_focus_llm` shadow-only 設計・60-case fixture・offline eval（§4）— Eligibility 非マージ

---

## 8. 完了定義（本ドキュメントの「次フロー」）

本次フローが「軌道に乗った」と呼べるのは、次が揃ったときだけである。

- [ ] Gate A-accuracy: §1 Pass または Fail 理由が `log/analysis/` に残っている
- [ ] Phase 1D: enable **なし**でチェックリストが埋まる
- [ ] Gate B: 開始条件が文書上閉じている（まだ Pass でなくてよい）
- [ ] Focus: shadow-only 差し込み設計が Test Plan 差分として凍結され、Eligibility 非マージが明記されている
- [ ] No-Go リストに反する flag / 統合 / PRIMARY がリポジトリに入っていない

---

## 9. Scaffold 現状（Focus shadow・本番未配線）

並行トラック用の **offline scaffold** を追加した（実行置換・flag・pipeline 変更なし）。

| 成果物 | パス |
| --- | --- |
| Pilot fixture（`label_status: draft`） | `tests/fixtures/jev_medicine_qa_focus_pilot.yaml` |
| Offline eval scaffold | `scripts/eval_jev_medicine_qa_focus_shadow.py` |
| Unit（network なし） | `tests/scripts/test_eval_jev_medicine_qa_focus_shadow.py` |

**比較面（文書化）:** 現行 `infer_medicine_qa_focuses`（scaffold は `use_llm_enrichment=False`）対、将来の Jev Focus adapter（Choice/Noul 草案は eval スクリプト内のみ。`jev_decisions` / `llm_flags` / `chat_post_pipeline` には未配線）。

**明示スコープ外:** Eligibility / `resolve_medicine_qa_route`。`physical_symptom_pivot` は Focus 側 FN リスクフラグとして記録するだけで、route 所有権は Eligibility のまま（§4.1 / T2）。

**実行例:**

```powershell
python scripts/eval_jev_medicine_qa_focus_shadow.py
python -m pytest tests/scripts/test_eval_jev_medicine_qa_focus_shadow.py -q
```

`JEV_API_KEY` なし → schema + rule baseline、exit 0。`--live` は任意スタブ（Focus 草案 questions または `--intent-fallback` の接続確認のみ）。本番 enable / `JEV_FOCUS*` flag はまだ置かない。

*End — JEV_NEXT_FLOW_PHASE1C-FOCUS_20260921*
