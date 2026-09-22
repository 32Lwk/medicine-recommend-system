# JEV R7 Safety Blocker Repair 医療一次レビュー

- 作成日: 2026-09-23
- Reviewer: Primary medical reviewer
- Role: AI多重医療監修
- Scope:
  1. detector comparison view for crisis / exam / controlled（H04 変更ではないこと）
  2. ambiguous sleep medicine -> `unknown_controlled_policy`（illegal template 不使用）
  3. `SF-E1-NM` DISABLED -> always `SF-E1`
  4. pure SessionOps fail-closed on evasion x SessionOps
- Commit / push / live deploy: 未実施

> 本文書は R7 Safety Blocker Repair に対する AI 多重医療レビューです。  
> **Label は Accept のため `AI多重医療監修` とするが、製品安全合格・人間医療監修・本番安全承認を意味しない。**  
> **Product safety pass: No / Not Passed。**

---

## 0. 一句裁定

**Accept (`AI多重医療監修`)**。  
今回の 4 項目は、いずれも **false negative の拡大、違法薬物扱いへの誤ラベリング、generic error による誤誘導** を避ける方向に働いており、医療安全上の後退は見当たりません。

---

## 1. 評価対象と確認結果

### 1.1 detector comparison view for crisis / exam / controlled

- 確認箇所:
  - `src/dialogue/routing/detector_text_view.py`
  - `src/dialogue/routing/pre_route_signals.py`
  - `src/dialogue/routing/turn_signal_snapshot.py`
- 医療判断:
  - **Accept**
- 理由:
  - detector 専用 view に限定されており、表示文や通常の canonical text を書き換えない。
  - `crisis` / `medical_examination` / `controlled` の検出を、ゼロ幅文字・CJK 間空白で回避されにくくしている。
  - `is_pure_session_ops()` は `evaluation_complete`、high-risk、policy block、evasion residue を全て通過条件にしており、安全側 fail-closed。
  - H04 の emergency/mapping 契約を直接いじらず、**検出入力の比較 view で補強している点は妥当**。

### 1.2 ambiguous sleep medicine -> `unknown_controlled_policy`

- 確認箇所:
  - `src/dialogue/routing/sleep_med_policy.py`
  - `src/dialogue/routing/policy_resolve.py`
  - `src/dialogue/routing/policy_adapters.py`
  - `src/services/llm_triage.py`
  - `src/handlers/chat/controlled_drug_routing.py`
- 医療判断:
  - **Accept**
- 理由:
  - `睡眠薬ください` は `ambiguous_sleep_medicine_request` -> `ambiguous_policy` -> `unknown_controlled_policy` となっており、即 `illegal` に落ちない。
  - adapter 文面は「違法薬物」「規制薬物ユーザー」扱いをせず、中立的 clarification に留まる。
  - 下流の controlled keyword 判定も OTC/不眠文脈では `睡眠薬` などを skip しており、後段で illegal template に戻る経路は見当たらない。
  - **不眠相談や市販睡眠改善への関心を、犯罪意図として過大評価しない**ため、医療安全・対人安全の両面で改善。

### 1.3 `SF-E1-NM` DISABLED -> always `SF-E1`

- 確認箇所:
  - `src/dialogue/routing/policy_enforce.py`
- 医療判断:
  - **Accept**
- 理由:
  - `SF_E1_NM_ENABLED = False` により、「今回の操作では履歴や記録内容は変更されていません」という真実性依存の強い reassurance を止めている。
  - `db_commit_unknown` や rollback 不全の可能性がある系で「変更なし」を断定しないのは適切。
  - generic fallback としての `SF-E1` は通常の policy copy 代替には使うべきではないが、**NM を凍結して truthfulness リスクを消した判断は安全側**。

### 1.4 pure SessionOps fail-closed on evasion x SessionOps

- 確認箇所:
  - `src/dialogue/routing/pre_route_signals.py`
  - `src/dialogue/routing/turn_signal_snapshot.py`
  - `src/dialogue/routing/policy_d2_pipeline.py`
  - `src/core/session_ops_classify.py`
- 医療判断:
  - **Accept**
- 理由:
  - `session_operation` が見えていても、evasion residue が残る場合は `is_pure_session_ops()` が `False` を返す。
  - その結果、`死にたい、履歴を削除して`、`診察してください、履歴を削除して`、`睡眠薬ください、履歴を削除して` のような混在発話で SessionOps が安全経路を先回りしない。
  - **SessionOps の便利導線より safety/policy を優先**しており、医療一次判断として妥当。

---

## 2. 主要所見

## Critical

**なし。**

- 今回の scope 内では、緊急性を過小評価する新規文言、違法性の誤断定、危機入力の見逃しを促進する変更は確認しなかった。

## High

**なし。**

- detector comparison view は display text を直接改変せず、観測上も raw 医療テキストを保持しない構成で、高リスクの副作用は抑えられている。
- ambiguous sleep medicine は neutral clarification にとどまり、処方要求・違法薬物要求への短絡が避けられている。

## Medium

1. `SF-E1` は safe fallback としては妥当だが、通常系の policy boundary 文言の代替として常用すべきではない。
   - これは今回の修正欠陥ではなく、今後の運用上の留意点。

2. detector comparison view は CJK 内部空白を縮約するため、極端に特殊な表記では detector 側と display 側の見え方がずれる可能性がある。
   - ただし今回は detector-only 使用であり、false reassurance や誤った医療助言を直接生む形ではない。

---

## 3. 医療安全観点の評価

### 3.1 False negatives

- `crisis` / `medical_examination` / `controlled` をゼロ幅文字や空白ですり抜けにくくしており、**見逃し抑制の方向**。
- `evasion x SessionOps` を pure 扱いしないため、危機・診察要求・規制薬物系の混在発話で SessionOps が先走る回帰も抑えられている。

### 3.2 Over-escalation

- ambiguous sleep medicine を `illegal` に落とさないため、**不必要な犯罪ラベリングや強い拒否**は減っている。
- `medical_examination` は専用 boundary を維持し、generic emergency へ過剰飛躍していない。

### 3.3 Mislabeling as drug user

- 今回の scope で最も重要な改善点の一つ。
- `睡眠薬ください` を即 illegal template にしないのは妥当で、**不眠相談・市販薬相談の可能性を残したまま安全確認へ戻せる**。

### 3.4 Truthfulness

- `SF-E1-NM` を止め、常に `SF-E1` に寄せた点は truthfulness の観点で明確に安全。
- 「変更されていない」と断定しないため、rollback / DB 状態不確定時の虚偽 reassurance を避けられる。

---

## 4. テスト確認

- 実行:
  - `python -X utf8 -m pytest tests/dialogue/routing/test_r7_pure_session_ops_adversarial.py tests/dialogue/routing/test_r7_sleep_med_policy.py tests/dialogue/routing/test_r7_rollback_and_nm.py tests/dialogue/routing/test_policy_enforcement_d2.py tests/dialogue/routing/test_policy_d2_adversarial_gates.py tests/dialogue/routing/test_turn_signal_snapshot.py tests/services/test_medical_examination_request.py tests/services/test_jev_eligibility.py tests/services/test_jev_eligibility_sessionops_matrix.py -q`
- 結果:
  - **87 passed**

---

## 5. 最終裁定

| Item | Verdict | Medical note |
| --- | --- | --- |
| detector comparison view for crisis / exam / controlled | **Accept** | H04 本体を触らず detector view で補強しており妥当 |
| ambiguous sleep medicine -> `unknown_controlled_policy` | **Accept** | illegal template 回避は適切 |
| `SF-E1-NM` DISABLED -> always `SF-E1` | **Accept** | truthfulness リスク低減として妥当 |
| pure SessionOps fail-closed on evasion x SessionOps | **Accept** | mixed high-risk utterance で SessionOps 先行を防ぐ |

### Label

- **AI多重医療監修**
- **Product safety pass: No / Not Passed**
- Human medical review: No

---

## 6. Supervisor 向け一行

**R7 の 4 論点は医療安全上 Accept。特に「曖昧睡眠薬を犯罪扱いしない」「evasion 混在で pure SessionOps を閉じる」「SF-E1-NM を止めて truthfulness リスクを消す」の 3 点が妥当で、製品安全合格の主張は不可だが AI多重医療監修ラベルは付与可能。**
