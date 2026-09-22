# Jev 自律PDCA サイクルログ（2026-09-22）

- Supervisor: autonomous-pdca-20260922
- Gate A-accuracy 開始状態: **Not Passed**
- コスト: Gate A では報告必須・合否外（ユーザー確定）

---

## Cycle 2 — Worker A: SessionOps shortpath 可視化 — **Accept**

| 項目 | 内容 |
| --- | --- |
| hypothesis | AE5-H2 を黙排除せず、`current_path_kind` で観測可能にすれば監査可能になる |
| target_metric | 可視化（Gate 母集団は不変） |
| files_changed | `scripts/eval_jev_intent_router_10.py`, `tests/scripts/test_eval_jev_intent_router_10.py` |
| tests_run | Supervisor: **30 passed** |
| evidence | `current_path_kind` / `triage_fast_path` / `deterministic_session_ops_n`。**scenario_cluster_warm から自動除外しない** |
| result | **improved**（観測性）。AE5-H2 非対称自体は未解消 |
| regression | false |
| next_action | SessionOps 母集団はユーザー回答待ち。F4/F5・commit 候補整理へ |
| gate_status | Not Passed |

---

## Cycle 1 — Worker A: latency population 統一 — **Accept**

| 項目 | 内容 |
| --- | --- |
| hypothesis | H-LAT-001: Gate 正本を `scenario_cluster_warm` に固定すれば点推定と CI の母集団不一致は解消する |
| target_metric | 方法論契約適合（unit） |
| files_changed | `scripts/eval_jev_intent_router_10.py`, `tests/scripts/test_eval_jev_intent_router_10.py`, `JEV_LATENCY_POPULATION_CONTRACT_20260922.md`, `JEV_EVAL_METHODOLOGY_AGENT_A_20260922.md` |
| tests_run | `pytest tests/scripts/test_eval_jev_intent_router_10.py -q` → **23 passed**（Supervisor 再確認済） |
| evidence | `gate_canonical=scenario_cluster_warm`; cold∉warm; exclusions 記録; `--latency-mode` |
| result | **improved**（方法論）。速度 Gate 実測は未再実行のため **Gate A-accuracy は Not Passed のまま** |
| regression | false |
| next_action | Worker E 完了待ち → SessionOps 公平契約のユーザー回答待ち。live は前条件未充足 |
| gate_status | Not Passed |

### Supervisor 裁定（A の Open questions）

1. Jev cold の production client close API: **今は追加しない**。cold mode は OpenAI 側強制・Jev は best-effort と契約に明記（既記載）。Worker C への後続チケット可。
2. `scenario_cluster` alias → warm: **維持**（互換）。破壊的廃止しない。
3. live タイミング: **E Critical/High クリア + F≥3 + SessionOps 母集団ユーザー回答**の後。現時点は live 禁止継続。

---

## Cycle 0（監査・仮説形成）— valid cycle

| 項目 | 内容 |
| --- | --- |
| hypothesis | live `012129` の scenario-cluster CI 下限未達（826.7ms）の主因は母集団不一致および/またはシナリオ構造 |
| target_metric | 原因特定（Gate語は変更しない） |
| files_changed | `JEV_AUTONOMOUS_PDCA_STATE.json` 初期化 |
| tests_run | オフライン再計算（APIなし） |
| evidence | `log/analysis/jev_intent_router_eval_10_20260922_012129.json` |
| result | **improved**（診断） |
| regression | false |
| next_action | Worker A に latency population 契約実装を委譲。並行で Worker F Cycle F1 |
| gate_status | Not Passed |

### 発見（実測）

1. cold は各 backend 1件のみ。warm 再計算でも CI 下限 ≈824.7ms（**母集団統一だけでは合格しない**）
2. `jev-session-delete` の warm シナリオ平均 Δ = **-73.1ms**（Jev が遅い）
3. 同シナリオの current: `triage_latency_ms≈0.14ms`、run1–9 は合計 **≈13.5ms**（決定論的 SessionOps 短絡）。Jev は毎回 **≈200–270ms API**
4. `use_cache=false` でも上記が成立 → **評価ハーネスの「current」は SessionOps で LLM IntentRouter と非対称**
5. SessionOps を除外した仮想 CI（参考・契約変更ではない）: 下限は 900ms 超の見込（Supervisor 計算）。**除外はユーザー承認なしで実施禁止**

### ユーザーへ保留する質問候補（実装は継続）

- latency Gate 母集団から SessionOps（決定論短絡）を外すか
- あるいは current も IntentRouter LLM 相当のみを測る公平契約にするか

安全側既定: **除外せず**、現状契約のまま Not Passed を維持し、公平性契約の明確化を求める。

---

## Cycle D1 — Worker D: shadow JSONL + privacy — **Accept**

| 項目 | 内容 |
| --- | --- |
| hypothesis | ローカル隔離で schema/correlation/PII denylist を unit 検証でき、欠落キーを塞げる |
| target_metric | privacy / shadow 非干渉（unit） |
| files_changed | `src/services/jev_metrics.py`, `tests/services/test_jev_metrics.py`（推定）, `JEV_SHADOW_JSONL_INTEGRATION_RESULT_20260922.md` |
| tests_run | Supervisor: metrics+router **45 passed**；報告 54 passed（shadow 含む） |
| evidence | Cookie/email/phone/address/prompt denylist 追加；`not_eligible` が `queue_full`/`submit_failed` を潰す不具合修正 |
| result | **improved** |
| regression | false |
| next_action | フル app smoke / 実 JSONL 追記は **未検証** のまま残置。生成 JSONL は commit しない |
| gate_status | Not Passed（Gate A-accuracy 非主張） |

---

## Cycle E5 — Worker E: 独立敵対評価 — **完了（Gate 変更権なし）**

| 項目 | 内容 |
| --- | --- |
| hypothesis | Gate A Not Passed は正当か / 抜け道はないか |
| target_metric | Critical/High 残件の独立監査 |
| files_changed | `JEV_ADVERSARIAL_EVALUATION_20260922.md`（新規） |
| tests_run | 静的+012129再集計。実装なし |
| evidence | Critical open **0** / High open+partial **9**。Not Passed **YES 維持が正しい** |
| result | **improved**（監査）。Gate 語変更なし |
| regression | false |
| next_action | AE5-H2 はユーザー回答待ち。承認不要: shortpath ラベル可視化・shadow 検証。live は High≠0 のため禁止継続 |
| gate_status | Not Passed |

### E 最重要質問（Supervisor 既出と一致）

Gate latency 母集団に SessionOps 決定論短絡を残すか / 層別か / 承認付き除外か。

### High 残件の扱い（Supervisor）

| ID | live ブロッカー? | 次アクション |
| --- | --- | --- |
| AE5-H1 | 証跡古い | Cycle1 でコード Closed。新 live まで証跡 Open |
| AE5-H2/H3 | **Yes（契約）** | ユーザー回答必須 |
| E4-H1 | Partial | Worker B 文書固定（exempt 分母除外） |
| E4-H2 | コード Closed | 新 live で証跡閉鎖 |
| E-H5–H7/H9 | Gate B/後段 | Phase1 では残置可。live A の必須クリア条件からは **契約上 High≠0 のため live 禁止**を維持 |

※ ユーザー指示「E の Critical/High なし」を厳格適用 → **現状 live 不可**。

---

## Cycle F1 — Worker F: 臨床危険性 AI 敵対レビュー — **完了**

| 項目 | 内容 |
| --- | --- |
| hypothesis | required_safety_action 未整備・Emergency/自傷等の契約穴が Gate B Hard No-Go を正当化する |
| target_metric | Gate B 契約完全性（採点可能か） |
| files_changed | `JEV_SAFETY_ACTION_AI_REVIEW_20260922.md`（新規） |
| tests_run | 静的監査（fixture/契約読取）。コード・金ラベル未変更 |
| evidence | Critical 4 / High 7。high_risk あり・safety_action なし → contract_incomplete |
| result | **improved**（可視化）。Gate 語は上げない |
| regression | false |
| next_action | Cycle F2（規制・薬事・不正利用）。fixture 金変更は F≥3 かつ承認後 |
| gate_status | Gate B **Hard No-Go** / Gate A-accuracy **Not Passed** |
| label | `ai_medical_adversarial_reviewed=true` / `human_medical_reviewed=false` |

### F1 Critical 要約

- F1-C01: Emergency 陽性に `required_safety_action` 欠落
- F1-C02: 過量軸ゼロ
- F1-C03: 脳卒中／アナフィラ／単独呼吸苦未収載
- F1-C04: 希死念慮が1フレーズのみ

---

## Cycle F2 — Worker F: 規制・薬事・不正利用 — **完了**

| 項目 | 内容 |
| --- | --- |
| hypothesis | 処方・Store調達・Security↔controlled 汚染が F1 臨床軸とは別の Hard No-Go 根拠になる |
| target_metric | Gate B 規制軸の契約完全性 |
| files_changed | `JEV_SAFETY_ACTION_AI_REVIEW_20260922.md`（F2 追記） |
| tests_run | 静的監査。金ラベル未変更 |
| evidence | Critical 3 / High 7（F2新規）。F2-C01 medicine_qa処方経路 / F2-C02 Store調達 / F2-C03 controlledをSecurity採点に混入 |
| result | **improved**（可視化） |
| regression | false |
| next_action | Cycle F3（言語曖昧性・否定・引用・第三者） |
| gate_status | Gate B **Hard No-Go** |
| label | `ai_medical_adversarial_reviewed=true` / `human_medical_reviewed=false` |

---

## Cycle F3 — Worker F: 言語曖昧性・否定・引用・第三者 — **完了**

| 項目 | 内容 |
| --- | --- |
| hypothesis | 否定・仮定・第三者表現が Emergency/危機を弱体化または exempt 拡大で FN を隠す |
| target_metric | 言語軸の契約穴可視化 |
| files_changed | `JEV_SAFETY_ACTION_AI_REVIEW_20260922.md`（F3 追記） |
| tests_run | 静的監査。金ラベル未変更 |
| evidence | Critical 3 / High 7。F3-C01 否定×部分一致弱体化 / C02 仮定マーカー抑止 / C03 第三者・フィクション類型不足 |
| result | **improved**（可視化） |
| regression | false |
| next_action | F1–F3 **ミニマム充足**。fixture 金変更は Supervisor+ユーザー承認後のみ。F4 継続 |
| gate_status | Gate B **Hard No-Go** |
| label | `ai_medical_adversarial_reviewed=true` / `human_medical_reviewed=false` |

**Supervisor 裁定:** fixture / `required_safety_action` 金ラベルの自動適用は **しない**。SafetyGate 弱体化提案は Reject。

---

## Cycle F5 — Worker F: 誤検知によるユーザー影響 — **完了**

| 項目 | 内容 |
| --- | --- |
| hypothesis | FP（過剰ブロック）がケア放棄・不適切な Counseling/SessionOps を生む |
| target_metric | FP-harm 軸の可視化（FN 防護は下げない） |
| files_changed | `JEV_SAFETY_ACTION_AI_REVIEW_20260922.md`（F5 追記） |
| tests_run | 静的監査。金ラベル未変更 |
| evidence | Critical 3 / High 7。Critical はすべて真の FP-harm |
| result | **improved**（可視化） |
| regression | false |
| next_action | **F1–F5 シリーズ完了**。Gate B Hard No-Go。次は F4-C02 runtime 順序調査（SafetyGate 強化方向のみ） |
| gate_status | Gate B **Hard No-Go** |
| label | `ai_medical_adversarial_reviewed=true` / `human_medical_reviewed=false` |

**Supervisor 裁定:** F シリーズ完了後も fixture 金ラベルは自動適用しない。FN 防護を下げる FP 対策は Reject。

---

## Cycle F4 — Worker F: multi-intent・session state — **完了**

| 項目 | 内容 |
| --- | --- |
| hypothesis | pending / Store+症状 / Counseling 陳腐状態が高リスクを飲み込む |
| target_metric | multi-intent・session 軸の穴 |
| files_changed | `JEV_SAFETY_ACTION_AI_REVIEW_20260922.md`（F4 追記） |
| tests_run | 静的監査。金ラベル未変更 |
| evidence | Critical 4 / High 7。特に **F4-C02 admin_probe≻SafetyGate** は実行経路の優先順位問題 |
| result | **improved**（可視化） |
| regression | false |
| next_action | F5（誤検知 UX）。F4-C02 は fixture ではなく **runtime 順序**候補 — 別サイクルで Worker B/C 調査可（SafetyGate 弱体化禁止） |
| gate_status | Gate B **Hard No-Go** |
| label | `ai_medical_adversarial_reviewed=true` / `human_medical_reviewed=false` |

---

## Cycle S1 — F4-C02 SafetyGate 順序 — **Accept**

| 項目 | 内容 |
| --- | --- |
| hypothesis | admin_probe が SafetyGate/Emergency より先だと混在発話が SessionOps に落ちる |
| target_metric | 高リスク混在で SessionOps 早期 return しないこと |
| files_changed | `session_agent.py`, `gate.py`, `test_gate.py`, `test_session_agent.py`, `JEV_F4C02_SAFETYGATE_ORDER_20260922.md` |
| tests_run | Supervisor: **42 passed** |
| evidence | **Confirmed** → probe 高リスク抑止 + gate Emergency を session_admin_probe より前へ。`chat_post_pipeline` は同一 probe 経由で間接修正 |
| result | **improved**（安全強化）。SafetyGate 弱体化なし |
| regression | false |
| next_action | 残存: 胸痛が gate Emergency 未到達の場合あり / `classify_session_intent` 直呼び。Gate A live は依然禁止 |
| gate_status | Gate A-accuracy **Not Passed** / Gate B **Hard No-Go** |
| label | AI敵対フォロー修正のみ。臨床安全証明なし |

---

## Cycle 3 — Eligibility v1 + Gate A v2（ユーザー裁定 **B**）

| 項目 | 内容 |
| --- | --- |
| hypothesis | SessionOps を Jev 対象外にし product/accuracy/latency を分離すれば契約的に非対称を解消できる |
| 変更しない契約 | 閾値900ms、fixture削除禁止、scenario ID除外禁止、PRIMARY OFF |
| Do | `src/services/jev_eligibility.py` 新設；`schedule_jev_shadow` が ineligible で API 非呼出；eval 3系統は Worker A 実装中 |
| Check | `test_jev_eligibility` + `test_jev_router` **31 passed**（Supervisor） |
| Act | eligibility コア **Accept**。eval 統合は Worker A 完了後 |
| gate_status | **Not Passed**（新契約 live 未実行。`012129` は旧契約参考値のみ） |

契約:
- `evaluation_contract_version = jev-intent-gate-a-v2`
- `eligibility_contract_version = jev-intent-eligibility-v1`

---

## Cycle S1x — SessionOps×高リスク行列 — **Accept**

| 項目 | 内容 |
| --- | --- |
| hypothesis | 必須16テーマの契約テストで S1 を拡張完了に近づける |
| files_changed | matrix 新規、gate/session_agent テスト、probe↔eligibility 共用 |
| tests_run | **96 passed**（Supervisor 再確認） |
| result | **improved**。S1-G01 / G03(probe) / G07 閉鎖 |
| residual | G02 診察混在、G04 覚醒剤、G05 否定、G06 stale counseling、G08 gate Emergency |
| gate_status | Not Passed / Hard No-Go |

---

## Cycle 5 — AE6-C1 accuracy_gate 水増し修正 — **Accept**

| 項目 | 内容 |
| --- | --- |
| hypothesis | `summaries[].accuracy_gate_pct` を `accuracy_gate_eligible` に一致させれば Critical は閉鎖する |
| files_changed | `eval_jev_intent_router_10.py`, tests, `jev_router.py`（eligibility 例外時 fail-closed） |
| tests_run | eval **38 passed** + jev_router 含む再確認 |
| evidence | ineligible placeholder は accuracy_gate_n に入らない；product_regression は別キー |
| result | **improved**。AE6-C1 Closed 候補 |
| gate_status | Not Passed（live 未実行・High 残） |

---

## Cycle 4 — Eval 3系統 + eligible_warm Gate（Worker A）— **Accept**

| 項目 | 内容 |
| --- | --- |
| hypothesis | Option B を eval に配線し Gate CI を `scenario_cluster_eligible_warm` にすれば SessionOps 非対称を契約的に除外できる |
| files_changed | `eval_jev_intent_router_10.py`, tests, latency contract, methodology memo |
| tests_run | Supervisor: eval+eligibility **46 passed** |
| evidence | 3トラック集計、ineligible 時 API スキップ、`unexpected_jev_call_count`、契約 version 記録 |
| result | **improved**（方法論）。live 未実行のため Gate A-accuracy **Not Passed** |
| regression | false |
| next_action | Worker E 再反証（scenario ID除外・分母水増し・production/eval drift） |
| gate_status | Not Passed |

---

## Cycle 6 — AE6-H1 prod/eval signals 整合 — **Accept**

| 項目 | 内容 |
| --- | --- |
| hypothesis | eval が current 後に本番と同じ deterministic_signals を渡せば資格ドリフトは解消する |
| files_changed | `eval_jev_intent_router_10.py`, tests |
| tests_run | Supervisor: **40 passed** |
| result | **improved**。AE6-H1 Closed 候補 |
| gate_status | Not Passed / live_blocked（High≠0） |

---

## Cycle 7 — S1-G02 診察混在 policy_block — **Accept**

| 項目 | 内容 |
| --- | --- |
| hypothesis | exact を変えず contained 検出を eligibility に載せれば SessionOps×診察を Jev 対象外にできる |
| files_changed | `medical_examination_request.py`, `jev_eligibility.py`, matrix/tests |
| tests_run | medical_exam+eligibility+matrix **39 passed** |
| result | **improved**。S1-G02 Closed。stage0 exact 不変 |
| gate_status | Not Passed |

---

## Cycle 8 — AE6-H2 fail-closed + false-eligible unexpected — **Accept**

| 項目 | 内容 |
| --- | --- |
| hypothesis | eligibility 例外 fail-closed と、eligible=True の再判定で unexpected を捕捉できる |
| files_changed | `eval_jev_intent_router_10.py`, `test_jev_router.py`, eval tests |
| tests_run | eval+jev_router+matrix **84 passed** |
| result | **improved**。AE6-H2 Closed 候補（Worker E 再反証待ち） |
| gate_status | Not Passed |

---

## Cycle 9 — S1-G04 覚醒剤 CJK short keyword — **Accept**

| 項目 | 内容 |
| --- | --- |
| hypothesis | 日本語短語に `\\b` を使わず部分一致にすれば混在文でも illegal 検出できる |
| files_changed | `llm_triage.py`, controlled tests, matrix（stimulant ケース追加） |
| 変更しない契約 | ASCII 短語 DOC の単語境界、Gate 閾値、PRIMARY OFF |
| tests_run | controlled+matrix+eligibility **41 passed** |
| result | **improved**。S1-G04 Closed |
| residual | S1-G05 否定、G06 stale counseling、G08 gate Emergency、AE6-H3/H5/H6、Gate B Hard No-Go |
| gate_status | Not Passed / Hard No-Go |

---

## Cycle 10 — S1-G08 chest/stroke medical_emergency_hint — **Accept**

| 項目 | 内容 |
| --- | --- |
| hypothesis | `_MEDICAL_EMERGENCY_HINTS` に胸痛・脳卒中系を足せば SessionOps 混在でも Emergency になる |
| files_changed | `gate.py`, `test_gate.py`, matrix |
| tests_run | gate+matrix+session_agent **90 passed**（G06前） |
| result | **improved**。S1-G08 Closed |
| gate_status | Not Passed |

---

## Cycle 11 — S1-G06 counseling ≺ Emergency — **Accept**

| 項目 | 内容 |
| --- | --- |
| hypothesis | counseling_continue を Emergency/Security の後へ移し、active counseling 中のみ emergency_candidate を挟めば短文危機を飲み込まない |
| files_changed | `gate.py`, `test_gate.py`, matrix |
| 変更しない契約 | 副作用仮定話法の非 Emergency、良性 counseling followup |
| tests_run | gate+matrix **59 passed** |
| result | **improved**。S1-G06 Closed。全発話への emergency_candidate は採用せず |
| residual | S1-G05 否定スコープ、AE6-H3/H5、H6 live証跡、Gate B Hard No-Go |
| gate_status | Not Passed / Hard No-Go |

---

## Cycle 12 — S1-G05 明示危機否定 — **Accept**

| 項目 | 内容 |
| --- | --- |
| hypothesis | 狭い明示否定パターンだけ危機検出から外せば SessionOps×否定危機の TN が取れる |
| files_changed | `crisis_detection.py`, crisis tests, matrix |
| 変更しない契約 | 「死にたい」単独は危機のまま、Gate 閾値、PRIMARY OFF |
| tests_run | crisis+matrix+gate **68 passed** |
| result | **improved**。S1-G05 Closed（狭い否定のみ） |
| residual | AE6-H3 cue過適合、H5 alias、H6 live、Gate B Hard No-Go、F 系 Critical |
| gate_status | Not Passed / Hard No-Go |

---

## Cycle 13 — AE6-H2(a) Jev行 signals 永続化 — **Accept**

| 項目 | 内容 |
| --- | --- |
| hypothesis | Jev attempted 行に peer `deterministic_signals` を残せば信号袋のみの誤eligible を unexpected で捕捉できる |
| files_changed | `eval_jev_intent_router_10.py`, eval tests |
| tests_run | eval+eligibility **61+ passed** |
| result | **improved**。Worker E H2(a) Partial を Closed 候補へ |
| gate_status | Not Passed |

---

## Cycle 14 — AE6-H3 cue 言い換え拡張 + 診察「〜してほしい」 — **Accept（部分）**

| 項目 | 内容 |
| --- | --- |
| hypothesis | fixture 密着以外の injection 言い換えと「診断してほしい」系で過適合を緩和できる |
| files_changed | `jev_eligibility.py`, `medical_examination_request.py`, tests |
| tests_run | eligibility+matrix+eval **76 passed** |
| result | **improved（部分）**。最短「診察して」は FP 抑制のため意図的残差（Worker F H01） |
| next_action | live は High≠0 / Gate B Hard No-Go のため **Blocked**。commit はユーザー再承認待ち |
| gate_status | **Not Passed** / Gate B **Hard No-Go** / live **Blocked** |
