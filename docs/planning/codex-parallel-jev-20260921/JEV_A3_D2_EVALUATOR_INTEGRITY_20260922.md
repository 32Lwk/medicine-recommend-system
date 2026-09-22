# JEV A-3 / D2 Evaluator Integrity Audit

Date: 2026-09-22
Auditor: Bias / false-pass evaluator
Scope: `tests/` and related source for `policy_enforcement`, `turn_signal_snapshot`, `canonical_normalize`, `pre_route_signals`, `jev_router`, Security fixtures

## Executive Summary

Critical は未検出。

ただし High 2件、Medium 2件を確認した。最も重要なのは、`eval_jev_safety_fixture_soft.py` が一部ケースで評価前に deterministic override を注入しており、Jev の生出力誤りを pass に変換できる点と、`eval_jev_intent_router_10.py` の accuracy gate 集計が membership 欠落時に fail-open である点である。どちらも evaluator integrity 観点では false-pass / population contamination の直接的な経路になる。

## Inspection Coverage

確認対象:

- `tests/dialogue/routing/test_pre_route_signals.py`
- `tests/dialogue/routing/test_jev_router.py`
- `tests/dialogue/routing/test_gate.py`
- `tests/dialogue/routing/test_jev_shadow_integration.py`
- `tests/scripts/test_eval_jev_intent_router_10.py`
- `tests/scripts/test_eval_jev_safety_fixture_soft.py`
- `tests/services/test_jev_decisions.py`
- `tests/services/test_jev_eligibility.py`
- `tests/services/test_jev_eligibility_sessionops_matrix.py`
- `tests/fixtures/jev_intent_router_eval_10.yaml`
- `tests/fixtures/jev_intent_router_safety_expanded.yaml`
- `src/dialogue/routing/pre_route_signals.py`
- `src/dialogue/routing/turn_signal_snapshot.py`
- `src/dialogue/routing/canonical_normalize.py`
- `src/dialogue/routing/policy_resolve.py`
- `src/dialogue/routing/policy_types.py`
- `src/dialogue/routing/router.py`
- `src/dialogue/routing/jev_router.py`
- `src/services/jev_decisions.py`
- `src/services/jev_eligibility.py`
- `scripts/eval_jev_intent_router_10.py`
- `scripts/eval_jev_safety_fixture_soft.py`

未検出:

- `tests/` 配下に `turn_signal_snapshot`, `canonical_normalize`, `policy_enforcement`, `policy_resolve`, `policy_types` を直接対象にした専用テスト

## Findings

### High

#### H1. Soft safety evaluator が medical_examination ケースで評価前 mutation を入れており、raw Jev 誤りを pass に変換できる

対象:

- `scripts/eval_jev_safety_fixture_soft.py`
- `tests/scripts/test_eval_jev_safety_fixture_soft.py`

根拠:

- `deterministic_signals_for_scenario()` は `medical_examination` 系ケースに対し `{"medical_examination": True, "emergency_sub_route": "medical_examination"}` を強制注入する。
- `_call_jev_live()` はその signal を `parse_jev_answers(..., deterministic_signals=signals)` に渡す。
- テスト `test_medical_examination_deterministic_overrides_physical_jev_answers()` は、Jev の mocked `Physical/rule_based_recommend` 出力が deterministic override により `Emergency/medical_examination` に変換され、そのまま `soft_pass=True` になることを明示的に固定している。

影響:

- evaluator が raw Jev 判定を観測せず、production override を先に適用してしまう。
- モデルが medical examination 境界を誤っても、soft harness 上は pass し得る。
- これは「policy evaluator」ではなく「production post-override result evaluator」になっており、false-pass の温床になる。

監査判断:

- soft harness であり CI hard gate ではない点は考慮しても、evaluator integrity の観点では High。

推奨:

- raw Jev 判定と post-override 判定を別列で記録する。
- `soft_pass_raw` と `soft_pass_effective` を分離し、draft fixture でも mutation の有無を可視化する。

#### H2. Accuracy gate 集計が membership 欠落時に fail-open で、Security / policy ケース再混入の余地がある

対象:

- `scripts/eval_jev_intent_router_10.py`
- 関連テスト: `tests/scripts/test_eval_jev_intent_router_10.py`

根拠:

- `_summarize()` の `gate_rows` は `r.get("accuracy_gate_eligible", True) is not False` を採用しており、flag 欠落行を accuracy gate に含める。
- `_latency_row_excludable()` も `latency_gate_eligible` 欠落時は一部 legacy/synthetic compatibility のため fail-open に寄る。
- 既存テストは「正しく flag が付く」ケースや「scenario-id hardcode がない」ことは押さえているが、「Security / policy row で membership 欠落時に fail-closed する」契約は押さえていない。

影響:

- 将来、`_apply_eligibility_flags()` を経由しない行、あるいは partial row が results に混ざると、Security / medical_examination / prescription / controlled-drug ケースが canonical accuracy population に再流入しうる。
- contamination は scenario-id ではなく row-shape 欠落から起きるため、検知しづらい。

監査判断:

- 現行の合成テスト群では直ちに誤集計していないが、population integrity を fail-open にしているため High。

推奨:

- canonical gate は `accuracy_gate_eligible is True` のみ採用する fail-closed に変更する。
- backward-compat 集計が必要なら別メトリクス名に分離する。
- Security / policy rows の missing-flag contamination を明示検出するテストを追加する。

### Medium

#### M1. Safety fixture の一部 expected は独立 oracle ではなく、現実装都合へ明示的に整列している

対象:

- `tests/fixtures/jev_intent_router_safety_expanded.yaml`

根拠:

- `safety-medical-examination-request` は note で「契約上 Emergency primary に合わせる」と明記している。
- `safety-prescription-request` は「primary Physical は既存 inappropriate/prescription handler 接続の仮置き」としている。
- `safety-controlled-drug` は「Security primary は enum 不足の妥協」と明記している。

影響:

- fixture が「望ましい policy truth」ではなく「現行 adapter / enum / handler 制約込みの contract truth」になっている。
- 実装回り込みを将来の gold と誤認すると、期待値が実装へ追従し、境界不整合を見逃しやすい。

監査判断:

- これは YAML 内に明示されており隠れた改ざんではない。
- ただし independent evaluator ではないため Medium。

推奨:

- `contract_expected` と `clinical_or_policy_oracle` を分離する。
- draft fixture を hard gate へ昇格させない運用を継続する。

#### M2. `TurnSignalSnapshot` / `canonical_normalize` / `PolicyDecision` 系の境界に専用テストがなく、RouteDecision↔PolicyDecision の re-mix を将来防げていない

対象:

- `src/dialogue/routing/turn_signal_snapshot.py`
- `src/dialogue/routing/canonical_normalize.py`
- `src/dialogue/routing/policy_resolve.py`
- `src/dialogue/routing/policy_types.py`
- `tests/` 全体

根拠:

- `tests/` に上記モジュール名へ直接対応する専用テストが見当たらない。
- `policy_resolve.py` は docstring で「no RouteDecision mapping」を明示し、`policy_types.py` も typed `PolicyDecision` 分離を意図しているが、その契約を固定するテストが無い。
- `turn_signal_snapshot.py` の `with_additive()` は SessionOps frozen / additive-only / incomplete non-recoverable という重要契約を持つが、専用テストが無い。
- `canonical_normalize.py` は policy/crisis/security marker を落とさない前提だが、専用テストが無い。

影響:

- 将来の refactor で `PolicyDecision` が `RouteDecision` へ再マッピングされたり、normalization が cue を落としたり、snapshot merge が signal を弱めても、現在の evaluator tests だけでは即検知できない。
- false-pass というより boundary regression の未検出リスク。

監査判断:

- 現時点で re-mix 実装を直接確認したわけではないため Medium。

推奨:

- `tests/dialogue/routing/` に snapshot / normalize / policy resolve 専用 contract tests を追加する。
- 少なくとも以下を固定する:
  - `PolicyDecision` は `RouteDecision` へ coercion しない
  - `with_additive()` は True→False を許さず `session_operation` を書き換えない
  - `canonical_normalize()` は prompt injection / crisis / policy marker を落とさない

## Non-Findings / Existing Strengths

以下は integrity 面で良い防波堤として機能している:

- `test_eval_jev_intent_router_10.py` で `_evaluate_prediction()` が `score_joint_decision()` と一致することを押さえており、別実装による force-pass drift を一定程度防いでいる。
- `test_jev_eligibility.py` で scenario-id hardcoding が無いこと、Security paraphrase が fixture wording 以外でも ineligible になることを押さえており、fixture overfit への対策が入っている。
- `test_eval_jev_intent_router_10.py` で raw disagreement と normalized disagreement を分離しており、 alias normalization で raw mismatch を隠さない設計は妥当。
- `test_pre_route_signals.py` と `test_jev_eligibility_sessionops_matrix.py` は SessionOps fast-path と high-risk / policy suppress の共有契約をかなり明確に固定している。

## Bottom Line

現在の最大リスクは「soft safety evaluator の事前 mutation」と「gate membership の fail-open 集計」であり、どちらも false-pass / contamination に直結する。逆に、scenario-id hardcoding や raw-vs-normalized disagreement 隠しについては、現状の tests は比較的よく守れている。

このため、次の優先順位は以下が妥当:

1. `eval_jev_safety_fixture_soft.py` の raw/effective 分離
2. `eval_jev_intent_router_10.py` の canonical gate fail-closed 化
3. `turn_signal_snapshot` / `canonical_normalize` / `policy_resolve` の専用 contract tests 追加
