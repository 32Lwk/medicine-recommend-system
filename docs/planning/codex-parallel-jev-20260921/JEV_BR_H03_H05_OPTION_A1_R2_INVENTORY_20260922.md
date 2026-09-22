# BR-H03/H05 Option A-1 — Cycle R2 Handler Inventory（read-only）

- Date: 2026-09-22
- Scope: **read-only inventory + 契約表**。runtime / fixture / 金ラベル **変更なし**
- H04: 分離維持・未変更
- Gate A-accuracy Not Passed / Gate B Hard No-Go / live Blocked / product safety 未合格

## R2 停止判定（先出し）

**A-1 では runtime 実装へ進まない（停止条件ヒット）。**

| 停止条件 | 判定 | 根拠 |
| --- | --- | --- |
| 写像先 handler が存在しない | 部分的に **存在はする**（orchestrator 側） | 下記表 |
| **gate の RouteDecision から既存 handler へ到達できない** | **HIT（confirmed）** | `try_agent_dispatch` の `_DISPATCH_TABLE` に prescription/controlled/exam 入口なし。`Security` → `handle_inappropriate_message_if_detected`（input_block）のみ |
| medical examination を Security へ載せる必要 | A-1 を無理に閉じると **必要になり得る** → 禁止 | Security ≠ exam UX |
| primary の意味を偽装する必要 | A-1 で dispatcher に載せるなら **HIT** | Unknown/Concierge 等に載せるのは偽装 |
| final UX 到達を統合テストできない | gate→dispatch 経路では **現状不可** | IntentRouter 経由の統合パス無し |
| fail-closed 時の安全な戻り先が未契約 | **HIT** | gate に policy 段も fail-closed UX 契約も未定義 |

→ Supervisor へ **A-2（Policy primary）vs 観測のみ Open** の比較を提出（本末尾）。

---

## 共通：IntentRouter 到達の反証（Evaluator）

| 主張 | 結果 |
| --- | --- |
| `primary=Security` で prescription UX | **偽**。`_dispatch_security` → `match_input_block` 系のみ |
| `primary=Security` で controlled/illegal 拒否 UX | **偽**。拒否は `inappropriate_drug_block_route`（triage follow-up） |
| `primary=Security` で medical examination 境界 | **偽かつ禁止**。境界は `chat_symptom_route` / counseling 系 |
| SessionOps を eligibility で閉じれば UX 到達 | **偽**。eligibility 閉じ ≠ handler UX |
| Jev が規制判断する | **偽**。Jev は対象外にするだけ |

---

## 表1 — prescription（[Worker A](bf04625f-338f-4afc-b9dd-b4aafc55b02c) 突合）

| 項目 | 内容 | 確度 |
| --- | --- | --- |
| detector | markers: `処方して`/`処方してください`/`処方箋`/`処方薬をください`；LLM `inappropriate_request/prescription`；`detect_inappropriate_request`（**keyword fast-path 無し**） | confirmed |
| typed PolicyDecision | `prescription` | proposed |
| current entrypoint | `chat_triage_follow_ups`（Other）→ counseling；backup `chat_category_route` | confirmed |
| proposed route mapping (A-1) | gate → ??? → 上記 | **missing path** |
| dispatcher/handler | IntentRouter: **なし**。`map_triage_to_route(Other)→Concierge` でも処方専用写像なし | confirmed |
| final UX | LLM counseling（`counseling_prompts` prescription 枝）。**定型拒否テンプレ無し**（exam/illegal と非対称） | confirmed |
| fail-closed | SessionOps: marker 時 fail-closed。UX: detect miss / follow-ups 例外は **fail-open** | confirmed |
| ResponseTuple | follow-ups: `(({status, message_count}, 200), True)`；category: counseling payload dict | confirmed |
| session mutation | `inappropriate_requests`；`start_counseling_mode`（prescription は True）；messages；DB | confirmed |
| observability | `counseling_inappropriate_prescription`；`log_counseling_response` | confirmed |
| test coverage | eligibility matrix のみ強；**E2E「処方して」→ counseling テキストは欠落** | confirmed / gap |
| A-1 で実現可能か | **No** | confirmed |
| residual | marker 外処方表現（例: マンジャロ）× SessionOps → probe 迂回 **inferred gap** | inferred |

## 表2 — controlled / illegal（[Worker B](4ed8eb30-32f4-4e60-81a4-f01d3d9f2cd8) 突合）

| 項目 | 内容 | 確度 |
| --- | --- | --- |
| detector | `detect_illegal_or_controlled_drug`（illegal 先）；OTC 不眠 skip；triage step-0 Other+sub；`resolve_illegal_or_controlled_type` | confirmed |
| typed PolicyDecision | `controlled_or_illegal`（内部 illegal\|controlled） | proposed |
| current entrypoint | follow-ups → `try_inappropriate_drug_block_response`；orchestrator 再ブロック | confirmed |
| proposed route mapping (A-1) | gate → drug block | **missing** |
| dispatcher/handler | **Security ではない**。flags=`controlled_drug_routing`；UX=`inappropriate_drug_block_route` | confirmed |
| final UX | `generate_illegal_drug_rejection_message` + critical notice | confirmed |
| fail-closed | 政策陽性時 SessionOps 抑止。非 hit / OTC skip は pass-through | confirmed |
| ResponseTuple | `Optional[Tuple[dict,int]]` → `({status, message_count}, 200)` | confirmed |
| session mutation | messages；`inappropriate_requests`+`blocked`；`illegal_drug_block`；DB | confirmed |
| observability | `inappropriate_drug_{illegal\|controlled}`；async `route_kind=illegal_drug` | confirmed |
| test coverage | drug_block / controlled_drug_routing / orchestrator subtype；gate 統合なし | confirmed |
| A-1 で実現可能か | **No** | confirmed |
| residual | Security `アヘン` 短文 notice は **別 UX**（本テンプレ非到達） | confirmed |

## 表3 — medical examination（[Worker C](acc4f6f1-1215-43f4-a397-d5f8ba57b289) 突合）

| 項目 | 内容 | 確度 |
| --- | --- | --- |
| detector | exact（stage0）；contained（policy/SessionOps のみ）；resolve は exact\|triage **のみ（contained 非使用）** | confirmed |
| typed PolicyDecision | `medical_examination` | proposed |
| current entrypoint | Other counseling → boundary；Physical `run_symptom_recommendation` ガード；Concierge chitchat resolve | confirmed |
| proposed route mapping (A-1) | gate → boundary（**非 Security**） | **missing** |
| dispatcher/handler | IntentRouter Security **不可**。gate 専用 RouteDecision **未配線** | confirmed |
| final UX | `generate_medical_examination_boundary_message`（定型） | confirmed |
| fail-closed | contained 例外→SessionOps 抑止。LLM FN→Physical 継続＋ガード依存 | confirmed |
| ResponseTuple | `({status, message_count}, 200)` 等 | confirmed |
| session mutation | messages；Other 経路は `inappropriate_requests`；**counseling_mode は開始しない** | confirmed |
| observability | 推奨スキップ log；専用 metrics counter は見当たらず | confirmed / inferred absence |
| test coverage | medical_examination_request / BR-H01 / eligibility；gate→UX なし | confirmed |
| A-1 で実現可能か | **No** | confirmed |
| residual | contained で probe 閉じ ≠ boundary UX 保証；shadow は Emergency 写像（本番 Security ではない） | confirmed |

---

## Worker 突合後の追加 residual（A-1/A-2 どちらでも別管理）

| ID | 内容 | 単位 |
| --- | --- | --- |
| R2-gap-Rx-marker | 処方 marker 集合 ⊂ LLM 処方表現 → SessionOps 迂回余地 | medical / policy |
| R2-gap-exam-asymmetry | contained→policy と resolve→UX の非対称 | medical |
| R2-gap-Rx-E2E | 処方 counseling E2E テスト欠落 | test |
| R2-gap-gate-dispatch | 三者とも gate→既存 UX **missing**（停止の主因） | H03/H05 |

停止判定は Worker 突合後も **変更なし（A-1 停止維持）**。

---

## A-2 vs 観測のみ Open（Supervisor 提出）

| 案 | 内容 | 利点 | 代償 |
| --- | --- | --- | --- |
| **A-2** | `PrimaryRoute` に `Policy` を追加し `_dispatch_policy` で typed sub → drug block / counseling prescription / exam boundary | gate→UX を嘘なく配線；Security 母集団汚染回避 | 広い契約変更；A-code 再審査；**製品安全合格にはならない**；上記 residual は別途 |
| **観測のみ Open（既定）** | H03/H05 Open。eligibility 閉じ＋orchestrator UX 現状維持。Gate B Hard No-Go | 偽 Security / 偽装 primary なし | gate primary ギャップ残；H05 未証明 |

**推奨:** runtime 実装せず **観測のみ Open**。A-2 は明示契約承認後のみ。

## H04

変更なし。fixture/金ラベルを実装に合わせない。

## 並列 Workers（完了・突合済）

- [Worker A prescription](bf04625f-338f-4afc-b9dd-b4aafc55b02c)
- [Worker B controlled](4ed8eb30-32f4-4e60-81a4-f01d3d9f2cd8)
- [Worker C medical examination](acc4f6f1-1215-43f4-a397-d5f8ba57b289)
