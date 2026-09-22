# BR-H03〜H05 Option A 設計（runtime / Gate B 分離）

- Date: 2026-09-22
- Supervisor choice: **A**（薄い deterministic policy/security resolution 段）
- commit / push / live: **禁止**
- Gate A-accuracy: **Not Passed** / Gate B: **Hard No-Go** / live: **Blocked**
- 本ドキュメントは **設計・契約候補**。テスト合格 ≠ 製品安全合格。

## Candidate split

| ID | Candidate | 本ドキュメントでの扱い |
| --- | --- | --- |
| H03/H05 | **policy/security runtime commit candidate** | 設計固定・実装は未着手 |
| H04 | **Gate B contract/fixture candidate** | runtime と **完全分離** |
| — | boundary / medical safety | 触らない |

---

## 固定優先順位（明示）

```text
Emergency / Crisis
  > Security          # known_attack / aggressive_input のみ（従来）
  > Policy block      # prescription / controlled|illegal / medical_examination（新規・型付き）
  > SessionOps
  > Counseling / Physical / Concierge / Store
  > Jev eligibility   # 決定者にしない（閉じるだけ）
```

制約の実装解釈:

| 制約 | 設計上の帰結 |
| --- | --- |
| SafetyGate を弱体化しない | Emergency/Crisis/Security 既存段の後ろに Policy を挿さない（**前**に挿すのは Emergency/Crisis/Security の後、SessionOps の前） |
| Jev を安全性・規制判断の決定者にしない | Policy は deterministic gate + 既存 detector。Jev は eligibility で skip するだけ |
| SessionOps による policy/security 迂回禁止 | Policy hit 時は `probe_session_admin_intent` に到達させない |
| medical examination を便宜的に Security へ分類しない | **Security primary に載せない**（下記契約変更） |
| prescription / controlled / medical_examination を型付きで区別 | `sub_route` または typed policy enum で区別。単一 `policy_block` 文字列に潰さない |
| 既存 RouteDecision で表現できない場合 | **Security 誤分類で逃げない** → 契約変更を先に提示 |
| handler/UX が無い route を返さない | 下記 GAP を閉じるまで primary を増やして return しない |
| detector hit だけで Closed としない | handler 到達・案内 UX まで統合テスト |

---

## 契約変更案（実装前に必要な決定）

### Measured gap

- `PrimaryRoute` に Policy 相当なし（`Physical|SessionOps|Concierge|Emergency|Security|Store|Counseling|Unknown`）。
- `dispatcher._dispatch_security` は `handle_inappropriate_message_if_detected`（攻撃的/input_block）のみ。  
  **prescription / controlled / medical_examination UX は Security ディスパッチでは到達しない。**
- medical examination 境界 UX は `chat_symptom_route` / controlled_drug_routing 側に既存。
- eligibility / `PreRouteSignals` は既に三信号を区別して Jev を閉じる（H03 の「primary 到達」とは別層）。

### 推奨契約（Option A-1）

**新しい primary は当面追加しない。** 代わりに:

1. gate 内に `resolve_policy_decision(text, signals, triage) -> PolicyDecision | None`  
   - typed: `prescription` | `controlled_or_illegal` | `medical_examination`
2. 各 type を **既存 handler が既に受け取れる dispatch 形**へ写像する（新 primary 禁止の間）:
   - `prescription` → 既存 prescription/inappropriate block 経路（現行 triage/handler の正を調査して固定）
   - `controlled_or_illegal` → `controlled_drug_routing` 系
   - `medical_examination` → medical examination boundary 系（**Security にしない**）
3. 写像先 handler が無い type は **実装せず契約チケットを Open のまま残す**（偽 Security 禁止）。

### 代替契約（Option A-2 — より大きい変更）

`PrimaryRoute` に `"Policy"` を追加し、dispatcher に `_dispatch_policy` を新設。  
→ 型はきれいだが、enum/i18n/評価器/Gate 母集団の契約変更が広い。**A-1 で handler 到達が証明できるなら A-2 は後続。**

**本サイクルの Act 既定:** A-1。A-2 は A-1 の写像が破綻したときのみ再提案。

---

## H03/H05 runtime 設計（薄い段）

### 挿入位置（`run_deterministic_gate`）

```text
… known_attack / aggressive_input (Security)
… Emergency / crisis hints / counseling-emergency
→ ★ NEW: policy resolution（SessionOps probe より前）
… SessionOps probe
… Physical / Store / …
```

### 疑似コード（仕様・未実装）

```text
policy = resolve_policy_decision(...)
if policy is not None:
    return route_for_policy(policy)  # typed mapping; never invent Security for exam
```

### Fail-closed

- detector 例外 → policy を「無い」とみなして SessionOps へ落として迂回させない。  
  **安全側:** SessionOps を抑止し、既存 fail-closed / clarification / 上位 Safety に委ねる（具体 UX は既存契約に合わせる。新 route を捏造しない）。
- 信号収集エラーは eligibility と同様に「Jev を呼ばない」に加え、gate では SessionOps を抑止。

### 必須テスト行列（runtime commit 時）

| # | ケース | 期待 |
| --- | --- | --- |
| 1 | prescription × SessionOps | SessionOps にならない；policy UX 到達 |
| 2 | controlled/illegal × SessionOps | 同上 |
| 3 | medical examination × SessionOps | Security にならない；exam boundary UX |
| 4 | known attack × SessionOps | Security；Policy より優先 |
| 5 | aggressive × SessionOps | Security |
| 6 | crisis/emergency 競合 | Emergency/Crisis ≻ Policy ≻ SessionOps |
| 7 | counseling active 競合 | 既存 S1-G06 順序を壊さない；Policy は SessionOps 前 |
| 8 | detector 例外 | fail-closed（SessionOps 迂回なし） |
| 9 | policy → 最終 handler/UX | dispatcher 経由で案内文まで |
| 10 | Security accuracy 母集団 | policy 事例を Security 集計へ混入しない |

---

## H04 — Gate B fixture / 金ラベル契約（runtime 分離）

### 原則

- fixture 期待値を実装結果に合わせて **自動変更しない**。
- `required_safety_action` が未定義なら **contract_incomplete**（Hard No-Go 維持）。
- prescription / controlled は joint accuracy より **block 到達**が本体指標（既存 Gate B scoring contract）。
- Security accuracy 母集団に policy 事例を入れない（軸分離）。

### 先に確定する金ラベル項目（実装前）

| field | prescription | controlled/illegal | medical_examination |
| --- | --- | --- | --- |
| high_risk axis | prescription_block | controlled_block | medical_examination |
| required_safety_action | block/拒否 UX | block/拒否 UX | boundary 案内 UX |
| forbidden sub | rule_based_recommend 等 | 推奨入口 | Security 誤分類 |
| label_status | gate_b_approved のみ Hard 集計 | 同左 | 同左 |

未承認ラベルは Soft CI / Hard No-Go のまま。

---

## PDCA（本サイクル）

### Cycle R1 — Plan

- 優先順位・契約ギャップ・A-1 写像を文書化（本ファイル）。
- runtime 実装は **handler 到達写像の inventory 完了後**。

### Cycle R1 — Do

- 設計ドキュメント作成のみ（コード変更なし）。

### Cycle R1 — adversarial Check

| 仮説 | 結果 |
| --- | --- |
| Security に載せて手早く閉じられる | **却下**（exam 誤分類禁止・dispatch UX 不一致） |
| eligibility skip だけで H03 Closed | **却下**（detector hit ≠ UX） |
| 新 primary `Policy` が必須 | **未決**（A-1 で足りるか inventory 待ち） |

### Cycle R1 — independent evaluator（自己分離）

- Measured: Security dispatch は input_block 系のみ。
- Inferred: A-1 写像は既存 handler 調査が必要（未完了 = Open）。
- 製品安全合格は主張しない。

### Cycle R1 — Act

- 次サイクルの **新しい**作業: 既存 handler inventory（prescription / controlled / exam の実入口と ResponseTuple）をコード追跡し、A-1 写像表を埋める。  
  同一 fixture の表面修正ループは開始しない。

### Cycle R2（完了・停止）

- 証跡: `JEV_BR_H03_H05_OPTION_A1_R2_INVENTORY_20260922.md`
- **停止:** gate RouteDecision → 既存 policy UX handler 到達不能；A-1 では primary 偽装または Security 誤分類が必要。
- **Act:** runtime 実装しない。A-2 vs 観測のみ Open を Supervisor 提出。H04 未変更。

### Cycle R3+（未実行・要契約承認）

- R3: A-2 契約承認後のみ enum/dispatcher 設計（または Open 維持）
- R4: H04 金ラベル（runtime 分離のまま）

---

## Unresolved risks

1. A-1 写像不能 type が残る → A-2（PrimaryRoute 拡張）または「観測のみ Open」へ戻す。  
2. Policy を gate に入れると Gate A-code 再審査対象が増える（Passed 主張はしない）。  
3. Security 母集団汚染を採点ハーネス側で防ぐ契約が未コード化。
