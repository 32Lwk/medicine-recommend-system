# Worker F — BR-C01 Medical Unit Review（Affirmative Double-Negation Crisis FN）

- 作成日: 2026-09-22
- Worker: **F — Medical Adversarial Reviewer**（medicine-recommendation-advisor 安全原則: **fail-safe ≻ 検出精密化**。臨床承認ではない）
- Scope: **BR-C01 medical unit ONLY**
  - 対象発話（計画どおり）: `死にたくないわけではない` / `訳ではない` / `というわけではない` / `死にたかったことがないわけではない`
  - 単純否定 `死にたくない` は non-crisis 維持
- Code under review:
  - `src/core/crisis_detection.py`（`_AFFIRMATIVE_DOUBLE_NEGATION_CRISIS_PATTERNS` 追加のみ）
  - Fixtures: `tests/core/test_crisis_br_c01_double_negation.py`
- **境界修復アーキテクチャ（PreRouteSignals / jev_eligibility / gate 順序）は本変更で壊れていない限り再開しない** — 本レビュー時点で再開不要。
- ラベル: `ai_medical_adversarial_reviewed=true` · `human_medical_reviewed=false`
- **本報告は AI 敵対的医療レビューである。人間薬剤師・医療安全担当の承認を代替しない。製品安全パス / Gate B Go は主張しない。**

---

## 0. 一句裁定

**BR-C01 Critical（宣言パターン）は fail-safe 拡張で Closed。SafetyGate / Option A は弱体化していない。**  
口語ゆれ（`わけじゃない` / `ってわけ` / カタカナ `ワケ` 等）は **本ユニット残差 High**。BR-H02（過去形・仮定活用）は **本ユニット外のまま**。  
**製品安全合格・Gate B Go・human medical approval は主張しない。**

---

## 1. 評価問への回答

### 1.1 修正は BR-C01 Critical を閉じ、SafetyGate を弱めていないか？

| 観点 | 判定 | 根拠 |
| --- | --- | --- |
| 宣言 Critical パターン | **Closed（AI）** | fixture 5 発話が `detect_crisis_keywords` で陽転。トークン `double_negation_affirmative_crisis` を **追加**するのみ |
| SafetyGate 弱体化 | **なし** | 既存 `crisis_keywords` ループ・除外ロジックを削除/緩和していない。ヒット後に二重否定を **OR 追加** |
| Option A（否定 soft 禁止） | **維持** | `死にたい気持ちはない` は従来どおり crisis=True（fail-safe FP）。コメント明示: softening 再導入なし |
| Counseling 閉じ込み FN | **宣言パターンでは解消** | active counseling 下 `run_deterministic_gate("死にたくないわけではない")` → `Emergency` / `emergency_candidate`（旧: Counseling） |
| SessionOps 迂回 | **宣言パターンでは抑止** | `履歴消して死にたくないわけではない` → probe=`None` · `deterministic_high_risk` · fast-path suppressed |
| PreRouteSignals | **配線 Intact** | `collect_safety_policy_signals` が crisis を拾い `crisis_detected=True`（fixture） |
| 境界修復再開 | **不要** | 検出器拡張のみ。eligibility / Shared signals 契約を変更していない |

**ローカル検証（2026-09-22）:**  
`.venv` で `tests/core/test_crisis_br_c01_double_negation.py` **12 passed**、`tests/core/test_crisis_detection.py` 併用 **20 passed**。

### 1.2 単純否定 / Option A フレーズの FP リスク

| 発話型 | 例 | 期待 | 実測 | 読み |
| --- | --- | --- | --- | --- |
| 単純否定（TN） | `死にたくない` / `今は死にたくない` | non-crisis | non-crisis | **Accept** — 「死にたい」部分一致にならない従来挙動維持 |
| Option A fail-safe FP | `死にたい気持ちはない` | crisis=True | crisis=True | **Accept** — soft で消さない意図的コスト |
| 部分否定（トークン残） | `死にたいわけではない` | crisis=True | crisis=True（`死にたい`） | **Accept** — Option A と同型 |
| 二重否定（肯定） | `死にたくないわけではない` | crisis=True | crisis=True（新パターン） | **Accept（本修正の目的）** |
| 混在自傷 | `…わけではないがリストカットした` | crisis | crisis（自傷語も残存） | **Accept** — 既存ヒットを消さない |

**FP 結論:** 単純否定への誤陽転は **本パターンでは観測せず**。Option A の意図的 FP は **温存（弱体化禁止）**。検出感度を下げて FP を減らす提案はしない。

### 1.3 残 High（BR-H02 過去形等）は本ユニット外か？

| ID | Sev | 例 | 本修正後 | 本ユニット |
| --- | --- | --- | --- | --- |
| **BR-H02** | High | `昔は死にたかった` / `もし死にたくなったら` / `死にたかった` | 依然 crisis=False | **OUT OF SCOPE（別変更単位）** |
| BR-H01 / H03–H05 等 | High | 短句診察・gate policy 未配線等 | 非対象 | **OUT OF SCOPE**（境界修復再開せず） |

二重否定の **過去閉じ** `死にたくないわけではなかった` は形態的に二重否定族だが、計画スコープ外の口語/時制ゆれとして **§1.4 残差**に置く（BR-H02 の「死にたかった」単体とは別バケット）。

### 1.4 本ユニット限定の Critical / High 残差

#### Critical（本ユニット）

| ID | Status | Note |
| --- | --- | --- |
| **BR-C01**（宣言パターン） | **Closed（AI adversarial）** | fixture カバーの肯定二重否定。人間医療レビュー未了のため **製品 Closed ではない** |

#### High（本ユニット残差 — 同臨床クラス・正規表現外）

口語・表記ゆれで **crisis=False → active counseling 下 Counseling**（旧 BR-C01 と同害: 希死念慮肯定の閉じ込み）をローカル再現:

| ID | Sev | 例 | Why harmful |
| --- | --- | --- | --- |
| **BR-C01-R01** | **High** | `死にたくないわけじゃない` / `わけじゃありません` | 口語二重否定。正規表現が `ない|無い|ありません` のみで **じゃない** 未対応 |
| **BR-C01-R02** | **High** | `死にたくないってわけではない` | `という` は任意だが **って** 未対応 |
| **BR-C01-R03** | **High** | `死にたくないワケではない` | カタカナ `ワケ` 未対応（`わけ|訳` のみ） |
| **BR-C01-R04** | **Medium→監視** | `死にたくないわけではなかった` | 過去形クローズ。現在も希死念慮語りの可能性。次サイクルで High 昇格可否を人間レビュー |

**カバー済み（残差にしない）:** `死にたくないというわけでもない` / `わけでもない` / `わけはありません` / `訳でもありません` / `わけでは無い` — 現行 regex で陽転。

**本ユニット Critical 新規オープン:** なし（宣言パターン Closed）。  
**本ユニット High 残:** R01–R03（口語・表記）。弱体化ではなく **fail-safe パターン拡張＋人間レビュー** が次手。

---

## 2. コード事実（安全読み）

```text
detect_crisis_keywords:
  1) 既存 keyword スキャン（変更なし・Option A）
  2) _matches_affirmative_double_negation_crisis → トークン追加のみ
  → return len(detected) > 0

Narrow patterns (意図的に狭い):
  死にたくない(?:という)?(?:わけ|訳)(?:で)?(?:は|も)?(?:ない|無い|ありません)
  死にたかった(?:こと)?(?:が|は)?ない(?:という)?(?:わけ|訳)(?:で)?(?:は|も)?(?:ない|無い|ありません)
```

- **Additive-only** → SafetyGate 感度低下なし。
- `is_emergency_candidate` / `collect_safety_policy_signals` は既存どおり `detect_crisis_keywords` 依存 → 宣言パターンは Emergency / high-risk に乗る。
- Softening（否定で危機を消す）は **再導入されていない**（Option A Accept 継続）。

---

## 3. Gate B / 製品安全についての明示的非主張

| 主張 | 本レポート |
| --- | --- |
| 製品安全パス | **しない** |
| Gate B Go / No-Go 解除 | **しない**（本ユニットは BR-C01 医療単位の AI レビューのみ） |
| human medical approval | **なし**（`human_medical_reviewed=false`） |
| fixture 金の無断昇格 | **しない** — 12 passed は回帰証拠であり臨床証明ではない |

境界修復全体の Gate B Hard No-Go（既往 F レポート）は、本ユニット外残差（BR-H01 等）と契約 incomplete のため **本文書では再裁定しない**。ただし **本修正を Gate B 入場根拠に使ってはならない**。

---

## 4. 必須ラベル

```text
ai_medical_adversarial_reviewed = true
human_medical_reviewed = false
```

- 人間臨床承認・薬剤師承認・「Passed / 臨床安全証明 / Gate B Pass」は **主張しない**。
- 本番コード変更の是非は Supervisor / 人間医療レビュー待ち。Worker F は本 Markdown の敵対的評価のみ。

---

## 5. Supervisor 向け一行

**BR-C01 Critical（宣言二重否定）Closed · Option A / SafetyGate 非弱体化 · 口語ゆれは本ユニット High 残差 · BR-H02 は別単位 · 製品安全パス/Gate B Go なし · human_medical_reviewed=false。**
