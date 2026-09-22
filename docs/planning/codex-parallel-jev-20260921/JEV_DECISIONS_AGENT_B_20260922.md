# Agent B: Safety and Decision Contract（2026-09-22）

- Owner: Agent B（`src/services/jev_decisions.py` / `tests/services/test_jev_decisions.py`）
- 上位: Phase0 凍結 / Gate B Scoring / Pharmacist review
- Fixture ラベル: **変更禁止**（schema 観測のみ）

---

## Round 0 報告（実装前監査）

### 現状

| 領域 | 状態 |
| --- | --- |
| Choice/Noul → `JevShadowDecision` | 実装済。未知 enum / 欠損 / 範囲外 → `valid=False` + `Unknown` |
| Emergency Noul > Security Noul | 実装済（`NOUL_HIGH_RISK_PRIORITY`） |
| deterministic override（Jev 陰性解除禁止） | 実装済（security / emergency / medical_examination） |
| invalid 時 `risk_flags` 保持 | 実装済 |
| prescription forbidden-sub ヘルパ | 実装済（実行経路は変更しない） |
| **joint(primary+sub+safety) 採点ヘルパ** | **欠落**（soft harness 側に類似ロジック散在） |
| **`effective_high_risk` OR 契約** | **欠落**（明示 API なし） |
| **alias 正規化（scoring 用）** | metrics のみ。decisions に契約コピーなし |
| **controlled block 契約ヘルパ** | **欠落** |
| **`required_safety_action` joint AND** | fixture にフィールド無し → 「未定義=採点外」を明示する必要あり |
| SafetyGate / router / metrics / eval | 本 Agent 編集禁止。触っていない |

### 仮説

| ID | 仮説 | Round1 検証 |
| --- | --- | --- |
| B-H1 | joint に safety を載せるには pure helper が必要。fixture に `required_safety_action` が無い現状では **未定義=採点外** が正 | helper + unit |
| B-H2 | alias は metrics と二重定義し、同期テストでドリフトを検知する方が decisions の純関数性を保てる | duplicate + assert vs metrics |
| B-H3 | `effective_high_risk = det OR legacy OR jev` を明示すれば「Jev 陰性解除」バグを API レベルで防げる | unit（jev=False でも det/legacy で True） |
| B-H4 | prescription/controlled は primary 一致より **block 到達**が本体 | block helpers |

### 変更対象

- `src/services/jev_decisions.py` — joint / effective_high_risk / alias / block helpers
- `tests/services/test_jev_decisions.py` — 契約 unit
- 本ドキュメント — Round0 + schema 方針

### 変更しない対象

- fixture 医療ラベル / `label_status`
- SafetyGate 解除ロジック
- `jev_metrics` / `jev_client` / router / eval scripts
- git commit/push

### 成功条件

1. `pytest tests/services/test_jev_decisions.py -q` green
2. joint helper: primary ∧（sub 非空時）sub ∧（required_safety 定義時）safety
3. `required_safety_action` 欠落時は safety を採点外（joint を捏造ラベルで落とさない）
4. `effective_high_risk` が OR 契約。Jev 単独で高リスク確定禁止の集合がテストされている
5. alternate は Gate B 契約どおり（仮定・引用の Emergency 許容）— **accuracy 水増し用の拡大禁止**
6. invalid 時も risk_flags 保持（既存回帰）

### 失敗条件

- fixture ラベル改変・SafetyGate 解除・metrics 編集
- Jev 陰性で deterministic/legacy 陽性を落とす API
- `accept_alternate_primaries` の恣意的拡大
- joint で primary のみ正解を「ほぼ正解」扱い

### 証跡

- Round1: 本ファイル + pytest 出力（Agent 提出フォーマット）

---

## Round 1 実装契約（schema / API）

### 1. `effective_high_risk`

```text
effective_high_risk = deterministic_high_risk OR legacy_high_risk OR jev_high_risk
```

- いずれか True → 高リスク扱い。
- Jev が False でも det/legacy が True なら **解除しない**。
- Jev 単独で確定してはならない軸: Emergency / Security / medical_examination / prescription / controlled|illegal / 自傷・希死・過量 / 赤旗（`JEV_ALONE_FORBIDDEN_CONFIRMATIONS`）。

### 2. Joint accuracy helper（pure）

| 入力 | 意味 |
| --- | --- |
| `expect.primary_route` + `accept_alternate_primaries` | primary_ok |
| `expect.accept_sub_routes` | 非空なら sub_ok（OR）。空/欠落なら sub 採点外 |
| `expect.required_safety_action` | **定義時のみ** safety_ok。未定義=採点外 |
| `expect.forbidden_sub` / `forbidden_sub_routes` | ヒットで joint fail |
| `scoring.emergency_fp_tolerated` 等 | Gate B §3 どおり Emergency を alternate 扱い（既存 soft harness と整合） |

`joint_ok = transport_ok ∧ primary_ok ∧ sub_ok ∧ safety_ok ∧ ¬forbidden_hit`

### 3. Alias 正規化方針（metrics 整合）

**方針: 重複定義 + 同期テスト**

| 理由 |
| --- |
| `jev_decisions` は HTTP/ログ無しの pure mapping 層を維持する |
| `jev_metrics.normalize_sub_route` は観測比較用で Agent D 所有 — 本 Agent は metrics を編集しない |
| 同一 alias 表を decisions に置き、unit で `jev_metrics` の表と一致を assert |

エイリアス（比較専用・実行ラベルは書き換えない）:

- Emergency: `chest_pain_breathing_difficulty` / `chest_pain_breathlessness` / `chest_pain_shortness_of_breath` → `emergency_dispatch`
- SessionOps: `delete_confirm` → `delete`

### 4. prescription / controlled block helpers

- `prescription_block_contract_ok`: block 到達 **かつ** recommend 入口 sub でない
- `controlled_block_contract_ok`: block 到達（primary が Security でも block 本体。known_attack 同一視はしない）

実行 route は変更しない。採点・監査用 pure API。

### 5. Safety fixture schema（ラベル非改変）

観測のみ。必須フィールド契約（draft）:

- `expect.primary_route`, `accept_sub_routes`（推奨非空）, `high_risk`, `label_status=pharmacist_reviewed_draft`, `pharmacist_verdict`
- `required_safety_action` は **現状 YAML に無し** → joint helper は未定義=採点外
- 仮定・引用: `accept_alternate_primaries: [Emergency]` + scoring 3 フラグ（改変禁止）

---

## 既知の危険（持ち越し）

1. prescription / controlled に Jev Noul 軸が無い → 既存 handler 依存のまま（単独確定禁止）
2. medical_examination が Emergency enum 流用 → 臨床ラベル妥協（sub=`medical_examination` で区別）
3. draft ラベルを CI hard-fail にすると検出器弱体化リスク
4. Agent A の soft harness と本 helper の二重実装 — 将来は harness が本 API を呼ぶのが望ましい（A/B 所有分離のため Round1 では未配線）

---

## Round 3（Agent E 差戻し対応 2026-09-22）

### 裁定

| ID | 判定 | 根拠 |
| --- | --- | --- |
| **E-H5** | **受理** | モジュール docstring + `effective_high_risk` / `score_joint_decision` / `JointScoreResult` に「本番 router 未配線・Phase1 shadow では実行に効かない」を明記 |
| **E-H4** | **受理（部分）** | `emergency_fp_ok` 時の `accepted_subs` 自動拡大（`medical_examination`/`none`/`emergency_dispatch`）を **廃止**。代替: `alternate_primary_used` + `sub_accuracy_exempt` + `emergency_fp_sub_kind` 観測。Gate B / F: Concierge 主 + Emergency 代替維持、代替時 sub は accuracy fail しない、`medical_examination` を Emergency FP accept に混ぜない |
| 公開 API 安定名 | **受理** | `JointScoreResult` docstring に eval 直結用フィールド名を固定 |

### E-H4 実装詳細

1. デフォルト: `accept_sub_routes` は YAML 値のみ（水増し禁止）。
2. Emergency 代替パス（actual=Emergency ∧ expected≠Emergency ∧ primary_ok）:
   - `alternate_primary_used="Emergency"`
   - `sub_accuracy_exempt=True` → sub 不一致でも accuracy fail しない
   - `emergency_fp_sub_kind` ∈ {`emergency_dispatch`,`medical_examination`,`none`,`other`} — FP 統計から `medical_examination` を除外可能
3. Opt-in のみ: `scoring.expand_emergency_fp_subs: true` → `emergency_dispatch` を accept に追加可。**`medical_examination` は絶対に追加しない**。

### 安定フィールド（eval 契約）

`joint_ok`, `primary_ok`, `sub_ok`, `safety_ok`, `safety_scored`, `forbidden_hit`, `actual_primary`, `actual_sub`, `normalized_sub`, `accept_alternate_primaries`, `accept_sub_routes`, `required_safety_action`, `alternate_primary_used`, `sub_accuracy_exempt`, `emergency_fp_sub_kind`

### 残留リスク

- soft harness 側に旧「accepted_subs 自動拡大」が残っていれば二重実装ドリフト
- `sub_accuracy_exempt` で joint_ok=True のまま `emergency_fp_sub_kind=medical_examination` になり得る → **集計側が kind で除外する必要**（本 helper は混ぜないが joint は fail させない）

---

*Agent B Round 0→1 / Round 3 — 2026-09-22*
