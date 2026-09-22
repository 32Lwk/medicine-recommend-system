# BR-H03〜H05 停止メモ（契約変更候補）

- Date: 2026-09-22
- Status: **停止してユーザー確認**（改善継続ではなく契約分岐）

## 事実

| ID | 内容 |
| --- | --- |
| BR-H03 | `run_deterministic_gate` に prescription / controlled / medical-examination の **policy primary 段が無い**。probe 抑止後 `None` になり得る |
| BR-H04 | Gate B 契約の `required_safety_action`（prescription/controlled）が **contract_incomplete**（fixture/契約） |
| BR-H05 | Security の gate primary 到達がマトリクス未証明。eligibility 閉じ ≠ Security UX 到達 |

BR-C01 / H01 / H02（検出器加算）は医療単位で対応済み。H03–H05 は **検出ではなくルーティング契約／Gate B 契約**の話。

## 原因

境界修復は「Jev を呼ばない／SessionOps を抑止する」まで。  
本番の拒否・Security・診察境界の **IntentRouter primary 文言**は別レイヤー（triage/handler）依存のまま。

## 推奨案（2026-09-22 更新）

- **A-1:** Rejected / Stop（R2）
- **A-2 Policy primary:** 保留
- **A-3 / D2:** 本線 — R4 Design Accept；**R5 Contract Freeze（技術）Conditional Go**；文言レビュー未了のため **Implementation Stop**（`JEV_BR_H03_H05_OPTION_A3_R5_CONTRACT_FREEZE_20260922.md`）
- **H04:** runtime から分離・未変更

## 代替案

**B:** H03–H05 を観測のみ残し、現行 triage/handler UX を正として Gate B Hard No-Go 維持。  
**C:** fixture/契約のみ先に埋め、runtime は触らない（H04 寄り）。

## 影響

| 案 | 影響 |
| --- | --- |
| A-3 / D2-b | Safety pre は副作用あり → snapshot 前は canonical normalize のみ。人間レビュー完了まで実装禁止 |
| A-2 | intent と permission を同軸化 |
| B/C | 観測/fixture のみ |

## 回答なしの安全側既定

観測のみ Open / Hard No-Go / live Blocked。Implementation Stop。commit / push / live 禁止。

## 本停止中も維持

- 境界修復 commit 候補は凍結のまま（再承認待ち）
- Gate A-accuracy Not Passed / Gate B Hard No-Go / live Blocked
- commit / push / repeat=10 live は実行しない
