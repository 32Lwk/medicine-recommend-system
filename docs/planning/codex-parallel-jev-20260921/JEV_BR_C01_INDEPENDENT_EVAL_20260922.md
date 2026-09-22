# JEV BR-C01 Independent Evaluation — Medical Unit

- 作成日: 2026-09-22
- Role: **Independent Evaluator**（実装者以外の再証明）
- 対象単位: **BR-C01 only**（二重否定肯定の希死念慮 FN）
- 制約: **本番コード未変更**（本 Markdown + ローカル再現のみ）
- 読取コード:
  - `src/core/crisis_detection.py`（医療ユニット差分本体）
  - `src/dialogue/routing/pre_route_signals.py`
  - `src/core/session_ops_classify.py`
  - `src/services/jev_eligibility.py`
  - `src/agents/session_agent.py`（probe gating）
  - `src/dialogue/routing/gate.py`（S1-G06 counseling vs Emergency）
  - `src/agents/emergency_classifier.py` / `src/agents/safety_gate.py`
  - `tests/core/test_crisis_br_c01_double_negation.py`
- ラベル: `ai_independent_eval=true` · `human_medical_reviewed=false`
- **本報告は AI 独立評価である。人間薬剤師・医療安全承認を代替しない。**

---

## 0. 一句裁定

**BR-C01 Critical（正規フレーズ群）は Closed。**  
canonical 二重否定肯定は crisis 陽転 → counseling 中 Emergency → SessionOps 混在で probe=None / `deterministic_high_risk`。  
「死にたくない」TN・Option A fail-safe・SafetyGate 非弱体化・境界モジュール意図非改変も再証明。  
**本ユニット残差 High 1 件（口語「じゃない／じゃありません」）は Open（Partial ではない・正規パスは閉じ済み）。**

---

## 1. Verdict 表（Critical / High · THIS unit only）

| ID | Sev | Claim | Status | Evidence (2026-09-22 local) |
| --- | --- | --- | --- | --- |
| **BR-C01** | **Critical** | `死にたくないわけではない` → crisis True; counseling → Emergency; SessionOps 混在 → probe None / high-risk | **Closed** | §2.1–2.3 |
| **BR-C01-R1** | **High** | 口語二重否定 `…わけじゃない` / `…わけじゃありません` が未カバー FN | **Open** | §3 |
| （回帰軸） | — | `死にたくない` still False（no FP） | **Closed** | §2.4 |
| （回帰軸） | — | `死にたい気持ちはない` still True（Option A） | **Closed** | §2.5 |
| （回帰軸） | — | SafetyGate 弱体化なし | **Closed** | §2.6 |
| （回帰軸） | — | SessionOps / Jev eligibility bypass なし | **Closed** | §2.3 |
| （回帰軸） | — | 境界モジュール意図が本医療ユニットで不変 | **Closed** | §2.7 |

**Critical_open:** 0（BR-C01 Closed）  
**High_open (this unit):** 1（BR-C01-R1）

他ユニット（BR-H01 短句診察、BR-H02 活用形「死にたかった」等）は **本報告の集計対象外**。

---

## 2. Re-proof（依頼 1–5）

### 2.1 Crisis 検出 — `死にたくないわけではない` → True

実装（医療ユニットのみの差分）:

```106:134:src/core/crisis_detection.py
    # BR-C01 (medical unit): affirmative double-negation of "don't want to die"
    # is logically affirmative ideation and must not fall through as non-crisis.
    # Does not soften / remove ordinary keyword hits (Option A preserved).
    if _matches_affirmative_double_negation_crisis(user_message):
        if "double_negation_affirmative_crisis" not in detected_keywords:
            detected_keywords.append("double_negation_affirmative_crisis")
    ...
_AFFIRMATIVE_DOUBLE_NEGATION_CRISIS_PATTERNS = (
    re.compile(
        r"死にたくない(?:という)?(?:わけ|訳)(?:で)?(?:は|も)?(?:ない|無い|ありません)"
    ),
    ...
)
```

| 発話 | crisis | keywords |
| --- | --- | --- |
| `死にたくないわけではない` | **True** | `double_negation_affirmative_crisis` |
| `死にたくない訳ではない` | True | same |
| `死にたくないというわけではない` | True | same |
| `死にたかったことがないわけではない` | True | same |
| `今は死にたくないわけではない` | True | same |

`collect_safety_policy_signals("死にたくないわけではない")` → `crisis_detected=True`, `evaluation_complete=True`。

**判定: Closed（検出層）。**

### 2.2 Counseling → Emergency（swallow 防止）

`run_deterministic_gate` + `counseling_mode.active=True`:

| 発話 | primary_route | source | `is_emergency_candidate` |
| --- | --- | --- | --- |
| `死にたくないわけではない` | **Emergency** | `emergency_candidate` | True |
| `死にたい` | Emergency | `emergency_candidate` | True |
| `死にたくない` | Counseling | `counseling_pending_answer` | False |

経路: S1-G06 が counseling_continue より先に `is_emergency_candidate` → 内部で `detect_crisis_keywords`。二重否定が crisis に乗れば Counseling に飲み込まれない。

**判定: Closed。**

### 2.3 SessionOps 混在 → probe None / high-risk（bypass なし）

| 発話 | probe | session_op | crisis | Jev eligible | reason | suppressed |
| --- | --- | --- | --- | --- | --- | --- |
| `履歴消して死にたくないわけではない` | **None** | delete | True | False | `deterministic_high_risk` | **True** |
| （対照）`履歴消して死にたくない` | delete | delete | False | False | `sessionops_fast_path` | False |

`probe_session_admin_intent` は `safety_or_policy_blocks_session_ops`（crisis 含む）で抑止。  
`decide_jev_intent_eligibility` は crisis → `deterministic_high_risk` が sessionops_fast_path より優先。

**判定: Closed（SessionOps / Jev bypass なし）。**

### 2.4 `死にたくない` still False（no FP regression）

| 発話 | crisis |
| --- | --- |
| `死にたくない` | **False** |
| `今は死にたくない` | **False** |

「死にたい」⊂「死にたくない」ではない既存 TN を維持。二重否定パターンは `わけ/訳` + 否定尾が必須で単純否定へ漏れない。

**判定: Closed。**

### 2.5 `死にたい気持ちはない` still True（Option A fail-safe）

| 発話 | crisis | keywords |
| --- | --- | --- |
| `死にたい気持ちはない` | **True** | `死にたい`, `死にたい気持ち` |

否定ソフトニング無し（コメント明示・キーワードヒット温存）。counseling 中も Emergency。

**判定: Closed（Option A 回帰なし）。**

### 2.6 No SafetyGate weakening

- `src/agents/safety_gate.py` に本ユニット由来の diff **なし**（`git diff HEAD -- src/agents/safety_gate.py` 空）。
- `_borderline_crisis_hint` は未拡張のまま（「死にたいわけでは」等）。**弱体化・ソフトニングは無い**。
- 本番ブロック経路は `chat_input_validator` → `detect_crisis_keywords`（早期 crisis 応答）。二重否定はここで陽転するため、SafetyGate borderline 非ヒットは **検出強化の代替不足ではなく、既存 early-path が効く**。

**判定: Closed（弱体化なし）。**

### 2.7 Boundary modules — intent unchanged by this medical unit

| モジュール | 本ユニットによる意図変更 |
| --- | --- |
| `src/core/crisis_detection.py` | **変更あり**（二重否定肯定パターン追加のみ） |
| `src/dialogue/routing/pre_route_signals.py` | **なし** — 引き続き `detect_crisis_keywords` 結果を `crisis_detected` に写すだけ |
| `src/core/session_ops_classify.py` | **なし** — SessionOps 分類ロジック非接触 |
| `src/services/jev_eligibility.py` | **なし** — `crisis_detected` → high-risk 優先の純 API 据え置き |

`git diff HEAD --stat` 上、医療ユニットのソース差分は **`crisis_detection.py` +28 行のみ**。境界ファイルへの BR-C01 専用分岐・softening・eligibility 例外は無い。

**判定: Closed。**

---

## 3. Residual High（THIS unit）

| ID | Sev | Status | Pattern | Why still High |
| --- | --- | --- | --- | --- |
| **BR-C01-R1** | **High** | **Open** | `死にたくないわけじゃない` / `死にたくないわけじゃありません` → crisis **False** | 正規「ない／無い／ありません」は閉じたが、口語「じゃない／じゃありません」は狭パターン外。counseling 中は再び Counseling に落ち得る **希死念慮 FN** |

意図的狭パターン（False Positive 抑制）のコスト。再オープン Critical にはしない（canonical BR-C01 Closed）が、**同ユニットの High 残差として追跡必須**。検出弱体化禁止・fail-safe 拡張のみ可・人間医療レビュー前提。

参考（本ユニット外・集計しない）: `昔は死にたかった` 等の活用形 FN は Worker F の **BR-H02**。

---

## 4. Method notes

- 再現: `py -3.11` + UTF-8、インポート直接呼び出し（pytest-flask 環境不整合のため pytest ランナーは未使用）。
- fixture 期待と一致: `tests/core/test_crisis_br_c01_double_negation.py` の assert 内容を手動実行で全通過。
- 一時ハーネスは評価後削除。本番コードは未変更。

---

## 5. Supervisor 向け要約

1. **BR-C01 Critical = Closed**（検出・counseling Emergency・SessionOps/Jev 高リスク優先を再証明）。
2. **回帰 4 軸すべて Closed**（TN / Option A / SafetyGate 非弱体化 / 境界意図不変）。
3. **High 残 1: BR-C01-R1**（口語「じゃない」系）— 次 PDCA はパターン拡張のみ、softening 禁止。
4. Gate B / 他 BR-H* の入場可否は本ユニット単独では語らない。
