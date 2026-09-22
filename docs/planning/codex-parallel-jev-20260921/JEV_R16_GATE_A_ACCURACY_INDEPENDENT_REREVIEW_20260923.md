# JEV R16 — Gate A-accuracy Independent Re-review

**Date**: 2026-09-23  
**Role**: Gate Supervisor (independent of R11–R15 Optimizer)  
**Code / fixture / threshold / population changes**: **なし**  
**New API execution**: **なし**（既存 raw JSON のみ再計算）

---

```text
Gate A-accuracy:
Conditional Passed

併記:
- accuracy numerator/denominator: 70/70 (100%) × seeds 42 and 20260922
- seeds: 42, 20260922 (repeat=10, order=seed_random, same fixture)
- latency CI lower (scenario_cluster_eligible_warm): 989.32ms ; 903.14ms
- threshold: warm_mean_delta ≥900 and CI lower ≥900
- Critical open: 0
- High open: 0
- Medium open: 3 (latency margin fragility; holdout non-independence; dirty WT / post-measure vocab fix provenance)
- cost: jev est ¥0.635728 / run (both seeds); openai intent proxy ≈¥0.85; not pass/fail
- flags: JEV=False SHADOW=False PRIMARY=False D2=False (post-rollback)
- commit/push/live: 未実施 / 禁止
- Gate B: Hard No-Go（不変）
- product safety: 未合格（不変）
```

本判定は Gate A-accuracy に限定され、Gate B、製品安全、Jev primary、本番導入、live、commit、push を承認しない。

---

## 1. Executive verdict

**Gate A-accuracy = Conditional Passed**

Frozen contract（`jev-intent-gate-a-v2` / eligibility-v1）の hard threshold は両 seed で再計算一致。  
一方、latency CI 下限の統計的余裕極小・同一 fixture の seed 再現（非独立 holdout）・dirty worktree / 測定後 vocab 修正の手続き的制約により **Passed（無条件）は不可**。  
hard fail 不在のため **Not Passed も不可**。

Independent auditors（Optimizer 非兼任）:

| Auditor | Agent | Axis |
| --- | --- | --- |
| Accuracy | [Accuracy Auditor](2ebbf5bf-da85-4224-bc8b-034edb01b40d) | Conditional |
| Latency | [Latency Auditor](b6855d6b-1469-4bf5-a2c9-5923d4f447d9) | Conditional |
| Integrity / Medical / Cost | [Integrity Medical Cost](e7c15fad-a434-4ca6-a3a4-09954580260a) | Integrity clean*; Medical Conditional Accept; Cost OK |
| Final Challenger | [Final Adversarial Challenger](015112ae-4165-4b16-a369-f997b78fb772) | **Conditional Passed** |

\*Cost 副監査の「seed20260922 JSON 欠落」は **Supervisor により誤認と訂正**（両 JSON 現存・再計算済）。

## 2. Scope and non-authorizations

**In scope**: Local synthetic shadow evidence for Gate A-accuracy only.  
**Out of scope / not authorized by this verdict**:

- Gate B Go
- product safety Passed
- Jev primary / default ON
- live / production
- commit / push
- fixture・閾値・母集団契約の変更

## 3. Evidence inventory

| Artifact | Role |
| --- | --- |
| `log/analysis/jev_r11_r10_seed42_20260923.json` | raw Stage3 r10 |
| `log/analysis/jev_r11_r10_seed20260922_20260923.json` | raw Stage3b r10 |
| `tests/fixtures/jev_intent_router_eval_10.yaml` | fixture（両 run 同一 SHA） |
| `scripts/eval_jev_intent_router_10.py` | evaluator |
| `JEV_LOCAL_*_20260923.md` + PDCA state/log | claim pack（信用せず raw で検証） |
| `JEV_LOCAL_MEDICAL_ADVERSARIAL_FINAL_20260923.md` | medical axis（独立） |

Fingerprint:

| Item | Value |
| --- | --- |
| fixture SHA256 | `122f047cd2aaee1fd3debae981bde54e59b20008298097a82181ba99402090b9`（両 artifact 埋込一致） |
| evaluator SHA256[:16] | `dcd3653d94f54263`（WT 現在値；artifact に evaluator SHA 埋込なし → Medium provenance） |
| commit_sha (both) | `b7066137…` **dirty_worktree=true** |
| contracts | `jev-intent-gate-a-v2` / `jev-intent-eligibility-v1` |
| model / transport | `jev-latest` / `production` evaluate path（local synthetic fixtures） |

## 4. Accuracy recomputation

Supervisor recompute from `results[]` (`accuracy_gate_eligible is True`, pass via `joint_ok`/`pass`):

| Seed | backend | eligible | passed | membership_unknown | api_err | fallback | retry |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 42 | jev:minimal | 70 | 70 | 0 | 0 | 0 | 0 |
| 42 | current | 70 | 70 | 0 | 0 | 0 | 0 |
| 20260922 | jev:minimal | 70 | 70 | 0 | 0 | 0 | 0 |
| 20260922 | current | 70 | 70 | 0 | 0 | 0 | 0 |

- 分母 70 = 7 eligible scenarios × 10 repeats（契約どおり）
- `raw_passized=0`；eligible 行に deterministic override による raw 誤答の pass 化なし
- ineligible 30 は `outcome=skipped_ineligible` で Gate 分母外（executed route コピーは product 観測用のみ）

## 5. Latency recomputation

Gate canonical: `scenario_cluster_eligible_warm`（numpy bootstrap, n_scenarios=7, n_boot=2000）

| Seed | mean_diff_ms | CI95 low | CI95 high | margin vs 900 |
| --- | ---: | ---: | ---: | ---: |
| 42 | 1245.75 | **989.32** | 1656.8 | +89.32 |
| 20260922 | 1143.8 | **903.14** | 1483.05 | **+3.14** |

[Latency Auditor](b6855d6b-1469-4bf5-a2c9-5923d4f447d9) 感度:

- 厳密列挙の 2.5% 点 ≈ 900.05ms（丸めで Pass を捏造していない）
- 同一 scenario means で bootstrap RNG を振ると **約 46%** が CI low < 900 → **統計的脆弱性（High finding, contract hard-fail ではない）**
- SessionOps / Emergency / Security 除外は eligibility 契約；cold 1 本は Gate 非混入
- 点推定のみでの合格主張なし（CI を使用）

### Independent bootstrap shell (post-hoc confirmation)

同一 raw JSON から scenario means → bootstrap / exact / leave-one-out を再実行（新 API なし）:

| Seed | reported CI low | recomputed boot low* | exact 2.5% | RNG×1000 below 900 |
| --- | ---: | ---: | ---: | ---: |
| 42 | 989.32 | 985.44 | 988.53 | **0 / 1000** |
| 20260922 | 903.14 | 902.52 | **900.05** | **461 / 1000** |

\*boot seed = eval seed；reported との数 ms 差は Monte Carlo 乱数差。mean_diff は両 run で reported と一致（1245.75 / 1143.8）。

leave-one-out（契約外の感度のみ）: seed20260922 で `jev-store-locator` 除外時 CI low ≈ 860.63。Conditional 条件（margin fragility）を補強し、Gate 判定は変更しない。

## 6. Population audit

| Population | Count / note |
| --- | --- |
| accuracy_gate eligible | 70 / seed（7 scenarios） |
| accuracy_gate excluded | 30 = SessionOps 10 + Emergency 10 + Security 10 |
| exclusion reasons | `sessionops_fast_path`×10, `deterministic_high_risk`×20 |
| latency Gate | eligible_warm scenario cluster（SessionOps 非混入） |
| scored_pct 79–82% | attempted 分母（ineligible placeholder None fail）≠ Gate 分母 → **矛盾ではない** |

## 7. Repeat / seed audit

| Stage | Result |
| --- | --- |
| repeat=1 / 3 | prior PDCA: Gate metrics pass（配線・分散） |
| repeat=10 seed42 | pass（本審査再計算） |
| repeat=10 seed20260922 | pass（本審査再計算） |
| fixture identity | **同一** SHA（独立 holdout ではない） |
| order | `seed_random` のみ差分 → **再現性確認**であり外部一般化の証明ではない |

Optimizer 改善用と最終測定は同一 10-case fixture。**holdout 独立性に限界**あり → Conditional 条件に列挙。

## 8. Evaluator integrity

- H2: membership **`is True` only**（fail-open なし）— コード確認
- H1: raw/effective 分離；本 artifact で `raw_passized=0`
- fixture gold-label 変更なし（両 run 同一 SHA）
- 歴史的 CI low 826.7 は **Not Passed 参考**であり合格証拠に未混入
- PDCA cycle_id 再利用なし（state JSON）
- MD/JSON 件数と Supervisor 再計算一致
- Low: evaluator SHA が JSON に未埋込；dirty WT

## 9. Medical safety（独立軸）

正本: `JEV_LOCAL_MEDICAL_ADVERSARIAL_FINAL_20260923.md`

| Phase | Verdict |
| --- | --- |
| Initial G/H | Reject（High vocab / eligibility） |
| R11 vocab + `policy_block` eligibility fix | tests green |
| Reaudit G+H | **Critical=0 High=0 Conditional Accept**（LOCAL adversarial only） |

**product safety Passed と呼ばない。** Accuracy 合否に医療 Conditional を混ぜないが、Gate A-accuracy の **Conditional 条件**として併記する。

## 10. Cost

両 seed JSON 現存（Cost 副監査の欠落主張を訂正）:

| Seed | jev input tokens | jev ¥ (est) | openai intent proxy ¥ | api_err | retry |
| --- | ---: | ---: | ---: | ---: | ---: |
| 42 | 96410 | 0.635728 | 0.8522 | 0 | 0 |
| 20260922 | 96410 | 0.635728 | 0.8526 | 0 | 0 |

重複暴走・別モデル混入の兆候なし。コストは合否非必須。

## 11. Findings by severity

### Critical
なし

### High
1. **LAT-MARGIN / BOOT-SENS**: seed20260922 CI lower +3.14ms；代替 bootstrap seed の約半数で <900 の感度  
2. （医療軸は再監査後 High=0 — Accuracy Gate の High としては扱わない）

### Medium
1. **HOLDOUT**: 両 seed 同一 fixture → 非独立 holdout  
2. **PROVENANCE**: dirty_worktree=true；測定後 vocab fix の clean re-run なし（eligible 70 は修正 path 非依存だが手続き制約）  
3. **LIVE-POP**: 正式 live / 実患者母集団未確認（本 Gate 範囲外だが条件）

### Low
- evaluator SHA 未埋込 artifact  
- scored vs gate 分母の読者混同リスク（契約上は正当）  
- Integrity 副監査の seed20260922 欠落誤認（Supervisor 訂正）

## 12. Residuals

- bootstrap 頑健化（n_boot↑ / multi-RNG）または margin 拡大再測定（**新 API は本 R16 では未実施・未要求**）
- clean commit 上での再現測定（commit 承認後）
- paraphrase 拡張 holdout（fixture 契約変更は別承認）
- Primary ON 前の named-drug / exam phrasing 残差（医療文書 H-RR）

## 13. Gate A-accuracy verdict

**Conditional Passed**

Challenger Q1/Q2/Q5 反証失敗；Q3/Q4 部分成立 → Passed 否定・Not Passed 否定。

## 14. Conditions（Conditional の内容）

1. 証拠は **ローカル合成 fixture** に限定；live 母集団へ自動延長しない  
2. seed 差分は **同一 10-case の再現性**であり独立 holdout ではない  
3. latency は契約上 Pass だが **seed20260922 の CI 余裕が極小**；bootstrap 感度を残差とする  
4. 測定時 dirty WT + 事後 vocab 修正あり；eligible accuracy 分母は不変でも **clean re-run は未実施**  
5. 医療は LOCAL **Conditional Accept**（Critical=0 High=0）；製品安全合格ではない  
6. flags は rollback 後すべて OFF；本判定は flag ON を許可しない

**Passed への昇格に必要な追加（提案のみ・本 R16 では実行しない）**:  
multi-RNG / 高 n_boot で CI 頑健性確認、clean tree 再走、拡張 holdout（要契約承認）。

## 15. Recommended next phase

1. Owner が本 Conditional Passed を正式簿記するか確認  
2. staging 候補は `JEV_LOCAL_STAGING_CANDIDATES_20260923.md` の L1（vocab）を先頭に、**commit は別承認**  
3. Gate B / primary / live は **新規指令なしでは開始しない**  
4. latency 頑健化または holdout 拡張は **改善フェーズ（R17+）** として分離し、Optimizer≠Gate 判定者を維持

---

```text
本判定はGate A-accuracyに限定され、
Gate B、製品安全、Jev primary、本番導入、live、
commit、pushを承認しない。
```
