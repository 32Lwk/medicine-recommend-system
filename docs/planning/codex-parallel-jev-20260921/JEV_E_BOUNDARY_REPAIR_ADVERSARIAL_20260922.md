# Worker E — PreRouteSignals 境界修復 敵対的レビュー

- Role: Worker E (Independent Adversarial Reviewer)
- Date: 2026-09-22（初回 + Option B follow-up 再監査）
- Scope: PreRouteSignals 導入後の **architecture / boundary** のみ（7 観点）。医療 BR-* は OUT OF SCOPE
- Method: 指定ソース静的監査 + AST 分類（top-level / lazy）+ 決定論的再現（`.venv`）
- Constraint: 本番コード変更なし。本 Markdown のみ。自己採点禁止。
- 先行: `JEV_AE6_REAUDIT_H1H2_G02_20260922.md` / `JEV_ADVERSARIAL_AGENT_E_ROUND4_20260922.md`
- **統一ステータス正本**: 末尾「Re-audit after Option B follow-up」

## Gate 語（固定・自動合格禁止）

| Gate | 本レビューでの扱い |
| --- | --- |
| **Gate A-code** | **再審査必要**（境界 Critical/High Open=0 でも Passed に書き換えない） |
| Gate A-accuracy | **Not Passed**（正本 `JEV_GATE_A_ACCURACY_VERDICT_20260922.md` / live `012129`。本レビューで触らない） |
| Gate B / primary / staging / prod | **Hard No-Go**（変更なし） |
| live | **Blocked** |
禁止語: 「条件付きPassed」「Gate A Go」「境界修復完了＝code Passed」。

---

## 総合判定

> **統一ステータスは末尾「Re-audit after Option B follow-up」が正本。** 下表は初回監査時点のスナップショット（履歴）→ Option B 後は再監査表を参照。

| # | 観点 | 初回判定 | Option B 後（再監査） |
| --- | --- | --- | --- |
| 1 | Circular `session_agent` ↔ `jev_eligibility` | **Closed** | **Closed**（変更なし） |
| 2 | Detector error → `eligible=true` | Mitigated + High override | **Closed**（decide fail-closed + override 加算のみ） |
| 3 | Accuracy 分母の ineligible placeholder 膨張 | Closed + Medium 残差 | **Closed**（canonical）。Medium 残差継続 |
| 4 | Scenario-id ハードコード除外 | **Closed** | **Closed** |
| 5 | Gate / prod↔eval cue drift | **Open / High** | **Closed**（共有 `medical_emergency_hints`） |
| 6 | SafetyGate / SessionOps → `jev_eligibility` | **Closed** | **Closed** |
| 7 | `pre_route_signals` → `jev_eligibility` | **Closed** | **Closed** |

**boundary_scope Critical_open: 0**  
**boundary_scope High_open: 0**（BE-H1 / BE-H2 / AE6-H2(a) いずれも Closed）  
**Medium_open: 2**（BE-M2 / BE-M3。BE-M1 は Closed）

医療レビュー（Worker F）の **BR-C01 / BR-H01–H05 は OUT OF SCOPE** — 境界 Critical/High には数えない。

---

## 1. Circular dependency `session_agent` ↔ `jev_eligibility`

### 証拠

| モジュール | `jev_eligibility` | `pre_route_signals` | `session_agent` |
| --- | --- | --- | --- |
| `session_agent` | **なし**（全文検索・probe 関数ソース） | lazy: `_session_admin_probe_blocked_by_safety` → `collect_safety_policy_signals` のみ | — |
| `jev_eligibility` | — | **top-level** import `PreRouteSignals` / `collect_pre_route_signals` | **なし** |
| `pre_route_signals` | **なし**（コメント禁止のみ。AST ImportFrom 0） | — | **なし**（Option B: SessionOps は `session_ops_classify` lazy） |

Probe 経路は意図的に SessionOps 分類を呼ばない:

```213:229:src/agents/session_agent.py
def _session_admin_probe_blocked_by_safety(user_text: str) -> bool:
    ...
        from src.dialogue.routing.pre_route_signals import (
            collect_safety_policy_signals,
            safety_or_policy_blocks_session_ops,
        )

        signals = collect_safety_policy_signals(text)
        return safety_or_policy_blocks_session_ops(signals)
```

実行確認: `import src.agents.session_agent` で `jev_*` モジュールはロードされない。`collect_safety_policy_signals` も `jev_eligibility` / 追加の `session_agent` 再入を誘発しない。

### 判定

- **対象の循環（session_agent ↔ jev_eligibility）は解消済み（Closed）。**
- Option B 後: `pre_route_signals` は `session_agent` を import しない。SessionOps は `session_ops_classify` へ。probe は safety-only の一方通行。**BE-M1 Closed**（再監査節）。

### BE-M1.（Medium → **Closed**）旧: lazy 双方向の再発リスク

| 項目 | 内容 |
| --- | --- |
| 初回 | `collect_pre_route_signals` ↔ `session_agent.classify_session_intent` lazy 双方向 |
| Option B | `session_ops_classify.py` 抽出。AST 上 `pre_route`→`session_agent` = 0 |
| 再判定 | **Closed** |
---

## 2. Detector error が `eligible=true` を生むか

### 本番 decide 経路 — fail-closed（OK）

```82:89:src/services/jev_eligibility.py
    if not signals.evaluation_complete:
        return _ineligible(
            JevEligibilityReason.SIGNAL_EVALUATION_ERROR.value,
            ...
        )
```

```237:249:src/dialogue/routing/pre_route_signals.py
    evaluation_complete = len(errors) == 0
    return PreRouteSignals(
        ...
        evaluation_complete=evaluation_complete,
        detector_errors=tuple(errors),
    )
```

`schedule_jev_shadow` の eligibility 例外も API 非呼び出し（AE6-H2(b) Closed と一致）。

Unit: `tests/dialogue/routing/test_pre_route_signals.py::test_decide_fail_closed_on_detector_error` / `test_detector_error_marks_incomplete`。

再現: `PreRouteSignals(evaluation_complete=False, ...)` → `eligible=False`, `signal_evaluation_error`。

### BE-H1.（High → Option B 後 **Closed**）旧: `has_all_overrides` が detector を完全スキップ

初回監査では override 全指定時に detector を飛ばし `evaluation_complete=True` 固定 → 過量テキストが `eligible=True` だった。

Option B 後（再監査正本）: `_signals_from_overrides` は常に `collect_pre_route_signals` を呼び、safety/policy は **加算のみ**。再現:

```text
is_jev_intent_router_eligible(
  "薬を大量に飲んだ",
  deterministic_high_risk=False,
  policy_block_detected=False,
  session_operation_detected=False,
)
→ eligible=False, reason=deterministic_high_risk
```

| 項目 | 内容 |
| --- | --- |
| 再判定 | **Closed**（詳細は末尾 Re-audit 節） |
| 残差 | SessionOps 軸の False override は `session_op` を消せるが、safety detector は消えない |
---

## 3. Accuracy 分母の ineligible placeholder 膨張

### Canonical Gate — Closed（AE6-C1 再確認）

```1338:1352:scripts/eval_jev_intent_router_10.py
    gate_rows = [
        r
        for r in scored
        if not r.get("sub_accuracy_exempt")
        and r.get("outcome") != "skipped_ineligible"
        and r.get("accuracy_gate_eligible", True) is not False
    ]
```

`gate_flags_for_row`: `accuracy_gate_eligible = bool(decision.eligible)` → ineligible placeholder は False。  
二重防御: `outcome != skipped_ineligible`。

Unit: `test_ae6_c1_ineligible_placeholder_not_in_accuracy_gate_pct`。

### BE-M2.（Medium）互換キー / default True の残差

| リスク | 証拠 |
| --- | --- |
| `accuracy_scored_pct` / `accuracy_pct` は placeholder を含み得る | `accuracy_note` 自身が「do not use for Gate」と明記 |
| 未タグ行は `accuracy_gate_eligible` default **True** | 旧 JSON 再集計で Gate 分母に混入し得る |
| `product_regression_pct` は Jev backend で placeholder を含む | コピー route の `pass=True` で製品トラックが楽観的に見える（Gate canonical ではない） |

Gate A-accuracy を本項目で Pass にしない。正本は引き続き Not Passed。

---

## 4. Improper eligibility exclusions（scenario-id ハードコード）

### 判定: Closed

- eval に SessionOps / ineligible を **scenario id 集合で落とす**ロジックは見当たらない。
- 明示コメント: 「SessionOps out via eligibility, **not** scenario-id exclusion」（`_path_kind_summary` / `_build_track_aggregates.tracks_note`）。
- 除外は `decide_jev_intent_eligibility` の reason（`sessionops_fast_path` / `deterministic_high_risk` / `policy_block` / `signal_evaluation_error`）経由。

---

## 5. Gate drift / production vs eval drift

### BE-H2.（High → Option B 後 **Closed**）旧: gate 緊急ヒント ⊄ pre_route テキスト検出

初回監査では gate 側ヒント多数が text-only eligibility をすり抜け（MISS）。

Option B 後（再監査正本）: `src/dialogue/routing/medical_emergency_hints.py` が SSOT。gate と pre_route が同一 `MEDICAL_EMERGENCY_HINTS`（同一オブジェクト）を参照。仮定話法も共有。再現: 24/24 text-only `eligible=False`（MISS=0）。

| 項目 | 内容 |
| --- | --- |
| 再判定 | **Closed**（詳細は末尾 Re-audit 節） |
| 残差（Medium 級） | `is_emergency_candidate` の counseling_active 限定 vs collector 常時。文書上の wrapper 表現 |
### BE-M3.（Medium）`run_jev_shadow_sync(force=True)` デフォルト

```806:823:src/dialogue/routing/jev_router.py
def run_jev_shadow_sync(..., force: bool = True) -> bool:
    """テスト用同期エントリ。"""
    return schedule_jev_shadow(..., force=force)
```

`force=True` は ineligible でも API 投入可。本番 `_maybe_schedule_jev_shadow` は force 未指定（False）。メトリクス比較を歪め得る（先行 AE6-M4）。

---

## 6. SafetyGate / SessionOps → `jev_eligibility`

### 判定: Closed

| コンポーネント | 結果 |
| --- | --- |
| `src/agents/safety_gate.py` | `jev_eligibility` / `pre_route_signals` import **なし** |
| `src/dialogue/routing/gate.py` | import は `RouteDecision` のみ。SessionOps は `session_agent` lazy |
| `session_agent` probe | `pre_route_signals` のみ。コメントで jev 依存禁止。test `test_session_agent_probe_does_not_import_jev` |

`jev_eligibility` を import する本番コードは現状 **`jev_router.schedule_jev_shadow` のみ**（src 配下 grep）。

---

## 7. `pre_route_signals` → `jev_eligibility`（禁止）

### 判定: Closed

- モジュール docstring が明示禁止。
- AST: `Import` / `ImportFrom` に `jev_eligibility` **なし**（文字列ヒットは禁止コメントのみ）。
- Unit: `test_collect_safety_policy_does_not_import_jev`。

依存方向（Option B 後・再監査正本）:

```text
detectors / medical_emergency_hints → pre_route_signals → {session_agent probe(safety), jev_eligibility, …}
pre_route_signals ──→ session_ops_classify ←── session_agent
jev_eligibility ↛ session_agent / SafetyGate / gate.py
session_agent ↛ jev_eligibility
pre_route_signals ↛ session_agent   # 双方向なし
```
---

## Critical / High / Medium 一覧

> **Option B 後の統一状態は「Re-audit after Option B follow-up」を正本とする。** 下表は履歴＋再監査反映。

### Critical（boundary_scope）

| ID | 状態 | 要約 |
| --- | --- | --- |
| （boundary 新規） | **なし / Open=0** | 循環・decide fail-open・override skip・cue drift は閉じた |

### High（boundary_scope）

| ID | 初回 | Option B 後 | 要約 |
| --- | --- | --- | --- |
| **BE-H1** | Open | **Closed** | override は collect 後・safety/policy 加算のみ |
| **BE-H2** | Open | **Closed** | `medical_emergency_hints` SSOT（24/24 text-only ineligible） |
| AE6-H2(a) | Partial | **Closed** | Jev attempted 行へ signals 永続化 + recompute 参照 |

### Medium（boundary_scope）

| ID | 状態 | 要約 |
| --- | --- | --- |
| **BE-M1** | **Closed** | `session_ops_classify` 分離で双方向消滅 |
| **BE-M2** | Open | Gate 以外 accuracy キー / default `accuracy_gate_eligible=True` / product placeholder |
| **BE-M3** | Open | `run_jev_shadow_sync` の `force=True` デフォルト |

### OUT OF SCOPE（医療 — 境界カウント外）

| ID | 状態（本 E レビュー） | 出典 |
| --- | --- | --- |
| BR-C01, BR-H01–H05 | **数えない** | `JEV_F_BOUNDARY_REPAIR_MEDICAL_REVIEW_20260922.md` |

### Closed（本スコープで確認）

| ID | 要約 |
| --- | --- |
| BE-C0 / 循環 | `session_agent` ↔ `jev_eligibility` なし |
| session_agent ↔ pre_route | **双方向なし**（Option B: session_ops_classify） |
| Detector fail-closed（decide / schedule 例外） | `evaluation_complete=False` → ineligible；例外時 API スキップ |
| BE-H1 / BE-H2 / AE6-H2(a) | Option B 後 Closed |
| AE6-C1 accuracy_gate | placeholder は canonical 分母外 |
| Scenario-id 除外 | なし |
| SafetyGate/SessionOps/pre_route → jev_eligibility | 禁止どおり |

---

## Gate A-code 再審査チェックリスト（自動 Pass 禁止）

再審査で **Passed** を主張するなら、最低限すべて証拠付きで閉じること（詳細チェックは再監査節）:

1. [x] BE-H1: override 加算のみ + 過量 + 全 False → ineligible
2. [x] BE-H2: 緊急ヒント単一ソース
3. [x] AE6-H2(a): Jev 行 signals 永続化 + recompute
4. [x] BE-M1: SessionOps 分類モジュール分離
5. [ ] 文書: eval「production も wrapper」記述の訂正確認

**境界 Critical/High Open=0 でも Gate A-code = 再審査必要（Passed ではない）。**
---

## 参照ファイル

- `src/dialogue/routing/pre_route_signals.py`
- `src/services/jev_eligibility.py`
- `src/agents/session_agent.py`（probe / classify）
- `src/dialogue/routing/gate.py`（imports + `_MEDICAL_EMERGENCY_HINTS`）
- `src/dialogue/routing/jev_router.py`（eligibility path）
- `src/dialogue/routing/router.py`（`_deterministic_signals_from_context`）
- `tests/dialogue/routing/test_pre_route_signals.py`
- `scripts/eval_jev_intent_router_10.py`（accuracy_gate / unexpected_jev / eligibility）

---

## 結論（1 段落・初回監査）

PreRouteSignals 導入により **禁止されていた `session_agent`↔`jev_eligibility` 循環と `pre_route`→`jev` 逆依存は消えた**。detector 失敗の decide 経路も fail-closed。accuracy Gate 分母の placeholder 膨張も canonical では閉じている。一方で **override API の誤 eligible 足場**と **gate 緊急ヒント vs collector の text-only drift** が High で残り、Gate A-code を Passed に自動昇格してはならない。**再審査必要。**

---

## Re-audit after Option B follow-up

- Role: Worker E (Independent Adversarial Reviewer)
- Date: 2026-09-22（Option B follow-up 後）
- Method: AST Import/ImportFrom 分類（top-level / nested）+ ソース読取 + 決定論的再現（`.venv`）
- Constraint: 本番コード変更なし。本 Markdown のみ更新。
- Scope: **BOUNDARY REPAIR ONLY**（医療 BR-C01 / BR-H01–H05 は別変更単位）

### Gate 語（再確認・自動合格禁止）

| Gate | 扱い |
| --- | --- |
| **Gate A-code** | **再審査必要**（境界 Critical/High は 0 だが Medium 残差・医療スコープ外 Critical/High・ライブ未検証のため **Passed に書き換えない**） |
| Gate A-accuracy | **Not Passed**（正本変更なし） |
| Gate B / primary / staging / prod | **Hard No-Go** |
| live | **Blocked** |

禁止語維持: 「条件付きPassed」「Gate A Go」「境界修復完了＝code Passed」。

### A. Dependency graph（AST / 実行）

| Edge | 形態 | 判定 |
| --- | --- | --- |
| `session_agent` → `jev_eligibility` | なし | **OK（循環なし）** |
| `jev_eligibility` → `session_agent` | なし | **OK** |
| `pre_route_signals` → `session_agent` | AST ImportFrom **0** | **OK — 双方向解消** |
| `session_agent` → `pre_route_signals` | lazy: `collect_safety_policy_signals` / `safety_or_policy_blocks_session_ops` のみ | **一方通行（許可）** |
| `pre_route_signals` → `session_ops_classify` | lazy in `collect_pre_route_signals` | **一方通行** |
| `session_agent` → `session_ops_classify` | top-level `classify_session_intent` 等 | **一方通行** |
| `session_ops_classify` → `session_agent` / `pre_route` / `jev_*` | なし | **OK** |
| `gate` / `pre_route_signals` → `medical_emergency_hints` | top-level | **共有 SSOT** |
| `pre_route_signals` → `jev_eligibility` | なし（禁止コメントのみ） | **OK** |

実行: `import src.agents.session_agent` 後に `jev_eligibility` / `pre_route_signals` は未ロード。probe 実行後も `jev_eligibility` 未ロード、`pre_route_signals` のみロード。

現状依存（Option B 後）:

```text
detectors / medical_emergency_hints
        ↓
pre_route_signals  ──lazy──→ session_ops_classify
        ↑ safety-only lazy          ↑ top-level
session_agent ──────────────────────┘
        ↓（なし）
jev_eligibility ──top──→ pre_route_signals
```

**BE-M1 再判定: Closed**（`session_ops_classify` 抽出により `session_agent` ↔ `pre_route_signals` の lazy 双方向は消滅）。

### B. BE-H1 / BE-H2 再判定（各ちょうど 1 つ）

| ID | 再判定 | 証拠要約 |
| --- | --- | --- |
| **BE-H1** | **Closed** | `_signals_from_overrides` は常に `collect_pre_route_signals` を実行。high-risk / policy の False override は detector 陽性を消さない（加算のみ）。再現: `"薬を大量に飲んだ"` + 三 boolean False → `eligible=False`, `deterministic_high_risk`。`evaluation_complete` は collected 由来。旧 `has_all_overrides` スキップ経路はソース上消滅。 |
| **BE-H2** | **Closed** | `MEDICAL_EMERGENCY_HINTS`（24）は `medical_emergency_hints.py` が SSOT。`gate._MEDICAL_EMERGENCY_HINTS` は同一オブジェクト。`medical_emergency_hint_hit` を pre_route が消費。text-only eligibility で 24/24 ineligible（MISS=0）。仮定話法は gate / pre_route とも共有 helper で抑止（対称）。 |

残差（High 再オープンしない）:

- SessionOps 軸のみ: `session_operation_detected=False` は `session_op` を None にできる（safety / policy 軸とは別）。BE-H1 の対象外。
- `is_emergency_candidate` を gate は counseling_active 時のみ、collector は常時 — Medium 級の経路差として残し得るが、緊急ヒント SSOT 化で BE-H2 High は閉じた。

### C. Critical / High カウント（境界スコープのみ）

#### boundary_scope（本レビューが数える）

| 深刻度 | Open 件数 | IDs |
| --- | --- | --- |
| **Critical** | **0** | — |
| **High** | **0** | BE-H1 Closed / BE-H2 Closed / AE6-H2(a) Closed（Jev attempted 行へ `deterministic_signals` 永続化 + recompute 参照） |

#### OUT OF SCOPE（医療・別変更単位 — 境界 Critical/High に加算しない）

| ID | 深刻度（Worker F） | 扱い |
| --- | --- | --- |
| **BR-C01** | Critical | OUT OF SCOPE（二重否定希死念慮 FN 等） |
| **BR-H01** | High | OUT OF SCOPE（短句診察 × SessionOps） |
| **BR-H02** | High | OUT OF SCOPE（危機活用形 FN） |
| **BR-H03** | High | OUT OF SCOPE（gate policy primary 未配線） |
| **BR-H04** | High | OUT OF SCOPE（required_safety_action 未定義） |
| **BR-H05** | High | OUT OF SCOPE（Security primary / Gate B 軸） |

医療側を境界スコアに混ぜると誤って Hard stop 理由を境界に帰属させる。**停止理由が医療 Critical/High なら Worker F 変更単位で扱う。**

#### Medium（境界・継続）

| ID | 状態 | 要約 |
| --- | --- | --- |
| **BE-M1** | **Closed** | SessionOps 分類モジュール分離済み |
| **BE-M2** | Open | 互換 accuracy キー / `accuracy_gate_eligible` default True |
| **BE-M3** | Open | `run_jev_shadow_sync(force=True)` デフォルト |

### D. Verdict（統一）

```text
boundary_scope Critical=0 High=0
boundary Critical/High remaining Open: none
Gate A-code: 再審査必要（Passed ではない）
Gate A-accuracy: Not Passed
Gate B: Hard No-Go
live: Blocked
```

Option B follow-up により **境界修復スコープの Critical/High はすべて Closed**。それでも Gate A-code Passed・Gate B・live の昇格はしない（Medium 残差、医療 OUT OF SCOPE の Critical/High、accuracy/live 未達）。

### Gate A-code チェックリスト更新（自動 Pass 禁止）

1. [x] BE-H1: override は detector 実行後・safety/policy 加算のみ + 再現（過量 + 全 False → ineligible）
2. [x] BE-H2: `medical_emergency_hints` 単一ソース（gate + pre_route）
3. [x] AE6-H2(a): attempted Jev 行に `deterministic_signals` 永続化、recompute が参照
4. [x] BE-M1: `session_ops_classify` 分離（双方向消滅）
5. [ ] 文書: eval「production も wrapper」記述の最終訂正確認（未監査で残し得る）

項目 1–4 が閉じても **Gate A-code = 再審査必要**（Passed 主張禁止。医療・accuracy・live と独立）。

### 参照追加（Option B）

- `src/dialogue/session_ops_classify.py`
- `src/dialogue/routing/medical_emergency_hints.py`
- `src/services/jev_eligibility.py`（`_signals_from_overrides` 加算のみ）
- `JEV_F_BOUNDARY_REPAIR_MEDICAL_REVIEW_20260922.md`（BR-* OUT OF SCOPE 一覧の出典）
