# Cycle R3 — Option A-3 Typed Policy Enforcement Layer（設計のみ）

- Date: 2026-09-22
- Scope: **設計・調査のみ**。runtime / H04 / commit / push / live **禁止**
- A-1: **Rejected / Stop 確定**
- A-2 Policy primary: **保留**（本 R3 停止時のみ再比較）
- A-3: **設計開始**

## 状態

| 項目 | 状態 |
| --- | --- |
| Gate A-code | 再審査待ち |
| Gate A-accuracy | Not Passed |
| Gate B | Hard No-Go |
| live | Blocked |
| product safety | 未合格 |

テスト合格・detector hit・設計 Closed ≠ 製品安全合格。

---

## 1. Architecture Decision Record — A-2 vs A-3

### Context

prescription / controlled_or_illegal / medical_examination は、Physical や Counseling と競合する **primary intent ではない**。  
通常ルート実行前に適用する **横断的 policy constraint** である。

### Decision (Supervisor)

| Option | 状態 | 理由 |
| --- | --- | --- |
| A-1（既存 primary へ写像） | **Rejected** | gate→UX 欠落；Security/偽装 primary が必要 |
| A-2（`PrimaryRoute=Policy`） | **保留** | 「何を求めているか」と「実行を許可するか」を同軸に混ぜ、長期責務境界を悪化 |
| A-3（typed PolicyEnforcement 層） | **設計中** | `RouteDecision` と `PolicyDecision` を分離 |

### Consequences

- `PolicyDecision` を `RouteDecision.primary_route` へ **変換しない**
- medical examination を Security へ **載せない**
- Unknown / Concierge / Physical へ **偽装しない**
- Jev は分類候補のみ；policy 判断に関与しない

### 独立 residual（H03/H05 Closed 根拠に含めない）

- 処方 marker ⊂ LLM 表現差
- contained ≠ resolve 非対称
- 処方 E2E 欠落

---

## 2. 概念モデルと処理順序

```text
RouteDecision     = ユーザー意図の分類
PolicyDecision    = 実行可否・境界案内・安全上の制約
PolicyEnforcementResult = continue | terminal_response | safe_fallback
```

```text
1. Emergency / Crisis
2. Security input block
3. collect typed policy signals
4. resolve PolicyDecision
5. enforce policy
     - terminal_response → 既存 router dispatch を行わない
     - continue → 通常 RouteDecision を dispatch
     - detector/adapter/unknown → SessionOps へ落とさず safe_fallback
6. SessionOps を含む通常 route dispatch
7. Jev = 分類候補のみ（policy 判断に関与しない）
```

### 呼出順序図（目標 vs 現状）

```text
【目標 A-3】
  Safety(pre) → Safety(full)/Crisis/Emergency
    → collect policy signals → resolve PolicyDecision → enforce
         ├ terminal / safe_fallback → HTTP return（dispatch/Jev/recommend 禁止）
         └ continue → SessionOps / IntentRouter dispatch / orchestrator
              → Jev eligibility（分類候補のみ）

【現状 pipeline（要約）】  ※ chat_post_pipeline
  SessionOps admin_probe          ← safety より前（緊張）
  Safety pre
  SessionOps fast
  triage
  SessionOps triage
  Safety full
  triage_follow_ups               ← 現行 policy UX の主座（二重実行源）
  medicine_qa early …
  try_agent_dispatch              ← 挿入案 A
  orchestrator                    ← 挿入案 C（drug block 再実行あり）
```

現状と目標の差分は **(a) SessionOps≺Safety** と **(b) policy UX が follow-ups/orchestrator に分散** の二点。  
A-3 は「薄い enforce フック」だけでは目標順序を満たせない（§4）。

---

## 3. Typed dataclass / protocol 案（未実装）

```python
# 設計草案 — コード追加禁止（R3）

PolicyKind = Literal[
    "prescription",
    "controlled_or_illegal",
    "medical_examination",
]

PolicyAction = Literal[
    "block",
    "boundary_guidance",
    "safe_clarification",
    "continue",
]

@dataclass(frozen=True)
class PolicyDecision:
    kind: PolicyKind
    action: PolicyAction
    detector_source: str          # e.g. "pre_route_markers" | "triage_subcategory" | "keyword"
    confidence: float
    reason_code: str
    evaluation_complete: bool
    # controlled のみ subtype: "illegal" | "controlled" | None
    subtype: str | None = None

@dataclass(frozen=True)
class PolicyEnforcementResult:
    handled: bool                 # True = terminal or safe_fallback consumed
    response: dict | None         # HTTP body when handled
    status_code: int | None
    policy_kind: PolicyKind | None
    action: PolicyAction | None
    fallback_reason: str | None   # detector_error | adapter_error | unknown_kind | ...
    observability_fields: dict    # policy_kind, policy_action, detector_source, handled, fallback_reason
```

**禁止:** `PolicyDecision` → `RouteDecision(primary_route=...)` の変換ヘルパーを設けない。

---

## 4. 挿入候補 3 案 + 目標整合案

調査根拠: [挿入位置 explore](61b850a0-6824-4f03-8e7e-27f181ba1028) + pipeline 読取。

| 案 | 位置 | Safety 後 | SessionOps 迂回 | follow-ups 二重 | dispatch 停止 | Jev/recommend | legacy 影響 | Rollback |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **A** | `try_agent_dispatch` 直前 | Yes | **残**（早期 SessionOps 済） | **高** | Yes | medicine early 済 / Jev 未なら止可 | IntentRouter ON 時のみ | 低〜中 |
| **B** | dispatcher `_DISPATCH_TABLE` 前 | Yes | **残** | **高** | 部分（inventory/Jev 後） | Jev 既 schedule 多い | dispatch 有効時のみ | 低 |
| **C** | Orchestrator 入口 | Yes | **残** | **高** | **No**（dispatch 後） | 残存しうる | coverage 最小 | 最低 |

### 推奨（設計）

| 順位 | 案 | 判定 |
| --- | --- | --- |
| — | A/B/C 単独 | **目標順序未達**（SessionOps≺Policy、二重 UX） |
| **推奨** | **D（目標整合）** | `run_safety_gate(full)` 直後に enforce を置き、`run_triage_follow_ups` の policy 枝（prescription/controlled/exam）を **吸収または排他**。早期 SessionOps は **別 prerequisite**（probe を Safety/Policy 後へ） |

**D は Supervisor 指定の 3 案外**だが、A-3 の定義（Policy ≻ SessionOps）を満たすには必須に近い。  
R3 では D を「A-3 本線設計」、A/B/C を「限定的フック（不十分）」と記録する。

---

## 5. 既存 handler adapter 表

| PolicyKind | 現行 UX 入口 | Content 生成（mutation 少） | Full handler（mutation 多） | Adapter 方針 |
| --- | --- | --- | --- | --- |
| prescription | `chat_triage_follow_ups` / `chat_category_route` → counseling | `generate_counseling_response(symptom_type=inappropriate_request/prescription)` | follow-ups 全体（append / counseling_mode / inappropriate_requests / DB） | **content-only** 呼び出し + enforce が単一 mutation owner |
| controlled_or_illegal | `try_inappropriate_drug_block_response` | `generate_illegal_drug_rejection_message` + `build_notice_status` | 同関数が append/messages/DB | template+status を adapter；**full handler をそのまま呼ばない**（二重更新） |
| medical_examination | follow-ups / `chat_symptom_route` ガード / chitchat | `generate_medical_examination_boundary_message()` | 各入口が messages append | template adapter；Physical ガードと enforce を排他 |

### Adapter が triage 分類を偽装せず呼べるか

| 確認 | 結果 |
| --- | --- |
| illegal/controlled 定型文 | **可**（template は request_type のみ） |
| medical examination 定型文 | **可**（引数なし template） |
| prescription counseling | **条件付き可** — LLM 呼び出しは triage subtype 文字列に依存するが、Other/subcategory を捏造せず `PolicyDecision.kind` から `inappropriate_request/prescription` を **明示マップ**すれば偽装ではない。信頼ソースは PolicyDecision |
| `try_inappropriate_drug_block_response` 丸ごと | **不可（安全再利用）** — session/DB を内包；enforce と二重 |

**R3 判定:** content adapter 経路は設計可能。full handler 直呼びは停止条件「mutation 分離不能」に抵触しうる → **直呼び禁止**を契約化。

---

## 6. Session mutation 表（一元化契約）

| フィールド | prescription | controlled/illegal | medical_examination | Owner（A-3 目標） |
| --- | --- | --- | --- | --- |
| `messages` user append | follow-ups が実施 | `append_user` フラグ | 経路依存 | **enforce のみ 1 回** |
| `messages` bot append | counseling bot | drug block | boundary bot | **enforce のみ 1 回** |
| `inappropriate_requests[]` | Yes | Yes + `blocked` | Other 経路のみ（Physical ガードは無し） | **enforce で正規化**（全 kind で一貫） |
| `counseling_mode` | start=True | False | False | prescription のみ；二重 start 禁止 |
| DB `save_session_to_db` | Yes | Yes | 経路依存 | **enforce 終端で 1 回** |
| `illegal_drug_block` flag | — | Yes | — | enforce |

**二重更新防止:** terminal 後は follow-ups policy 枝・orchestrator drug block・Physical exam ガードを **skip フラグ**（例: `session["_policy_enforced_turn"]=kind`）で抑止。

---

## 7. Failure matrix（fail-closed 具体化）

「上位 Safety に委ねる」だけでは不十分。R3 契約案:

| 失敗モード | PolicyAction / Result | HTTP body 契約 | SessionOps | dispatch / Jev / recommend |
| --- | --- | --- | --- | --- |
| detector exception | `safe_fallback` / `fallback_reason=detector_error` | `200` + 固定セーフ文言（相談継続不可・店舗/救急案内の汎用 notice）※文面は既存 notice 部品から選定し **新捏造禁止なら既存 critical notice 再利用** | **禁止** | **禁止** |
| adapter exception | `safe_fallback` / `adapter_error` | 同上 | 禁止 | 禁止 |
| `evaluation_complete=False` | `safe_fallback` / `incomplete_evaluation` | 同上 | 禁止 | 禁止 |
| unknown `PolicyKind` | `safe_fallback` / `unknown_kind` | 同上 | 禁止 | 禁止 |
| kind 解決したが content 空 | `safe_fallback` / `empty_content` | 同上 | 禁止 | 禁止 |
| 信号なし | `continue` | — | 通常 | 通常 |
| kind=prescription, action=boundary_guidance | `terminal_response` | counseling envelope | 禁止 | 禁止 |
| kind=controlled_or_illegal, action=block | `terminal_response` | drug rejection notice | 禁止 | 禁止 |
| kind=medical_examination, action=boundary_guidance | `terminal_response` | exam boundary template | 禁止 | 禁止 |

**確定残:** 汎用 safe notice の **既存文面 ID**（新規コピー禁止方針なら inventory から選定）— 実装前に 1 文言を契約固定。未固定のまま実装に入ると停止条件「fail-closed response を定義できない」に該当。

---

## 8. Observability（共通）

必須フィールド（Security accuracy 母集団に **混入させない**）:

```text
policy_kind, policy_action, detector_source, handled,
fallback_reason, evaluation_complete, subtype?
```

| 置き場 | 方針 |
| --- | --- |
| 構造化ログ / counseling_detail | policy_* 名前空間 |
| Jev shadow | eligibility 閉じのみ；policy 件数を Security 指標へ入れない |
| Gate B | H04 分離維持；本 R3 で fixture 変更しない |

---

## 9. 必須統合テスト一覧（実装時・未作成）

| # | ケース | 期待 |
| --- | --- | --- |
| 1 | prescription × SessionOps | SessionOps mutation なし；terminal UX 1 回 |
| 2 | controlled/illegal × SessionOps | 同上 + drug block UX |
| 3 | medical_examination × SessionOps | Security にならない；boundary UX |
| 4 | known_attack × SessionOps | Security ≻ Policy |
| 5 | aggressive × SessionOps | Security ≻ Policy |
| 6 | crisis/emergency 競合 | Emergency ≻ Policy |
| 7 | counseling active 競合 | 既存 S1-G06 を壊さない；Policy ≻ SessionOps |
| 8 | detector 例外 | safe_fallback；SessionOps/dispatch/Jev/recommend なし |
| 9 | policy → 最終 UX | adapter content + 単一 mutation |
| 10 | Security 母集団非混入 | policy 事例が Security accuracy 集計に入らない |
| 11 | terminal 後 | follow-ups / orch drug / recommend / duplicate append なし |
| 12 | continue パス | 通常 RouteDecision dispatch のみ |

---

## 10. 変更対象ファイル候補（実装時・未着手）

| ファイル | 役割 |
| --- | --- |
| `src/dialogue/routing/policy_types.py`（新） | PolicyDecision / EnforcementResult |
| `src/dialogue/routing/policy_resolve.py`（新） | signals → PolicyDecision |
| `src/dialogue/routing/policy_enforce.py`（新） | enforce + mutation owner |
| `src/dialogue/routing/policy_adapters.py`（新） | content-only adapters |
| `src/handlers/chat/chat_post_pipeline.py` | 挿入 D + 早期 SessionOps 順序（prerequisite） |
| `src/handlers/chat/chat_triage_follow_ups.py` | policy 枝を enforce へ委譲 / 排他 |
| `src/handlers/chat_orchestrator.py` | drug block 二重実行抑止 |
| `src/handlers/chat/chat_symptom_route.py` | exam ガードと enforce 排他 |
| metrics/log helpers | policy_* フィールド |
| テスト一式 | §9 |

**触らない（R3）:** H04 fixture、危機医療 BR、`PrimaryRoute` enum、live flags。

---

## 11. Rollback 境界

1. feature flag `POLICY_ENFORCEMENT_V1=0` で enforce スキップ → 現行 follow-ups 動作
2. 新モジュール削除で pipeline フックのみ戻す
3. SessionOps 順序変更は **別 rollback 単位**（依存を混ぜない）

---

## 12. Gate A-code 再審査範囲（実装時）

| 領域 | 再審査 |
| --- | --- |
| IntentRouter / dispatcher 契約 | Yes（dispatch 前 terminal） |
| SessionOps 順序 | Yes（prerequisite 実施時） |
| triage follow-ups 責務 | Yes |
| PrimaryRoute enum | **No**（A-3 では追加しない） |
| Jev schema | No（policy 非関与） |
| Security accuracy 母集団定義 | Yes（非混入） |
| Gate B / H04 | **再審査するが変更は別承認** |

---

## 13. R3 停止条件判定

| 停止条件 | 判定 | メモ |
| --- | --- | --- |
| adapter が既存 handler へ安全到達できない | **回避可（条件付き）** | full handler 直呼びは不可；template/content adapter は可 |
| response と session mutation を分離できない | **現状 handler は分離不足** → 設計で enforce 所有を強制すれば **継続可** | 実装が full handler 依存なら Stop |
| dispatcher 前に terminal を返す正式契約がない | **de-facto は follow-ups**；typed 契約は未整備 | 案 D で正式化可能 |
| enforcement と orchestrator 二重実行 | **現状リスク高** | 排他フラグ必須；無ければ Stop |
| fail-closed response を定義できない | **文言 ID 未固定** | 固定前に実装禁止；固定できなければ Stop |

### R3 結論（設計）

- **A-3 設計は Conditional Continue**（コード変更なしで文書完了）。
- **実装着手条件:** (1) 挿入 D 採用、(2) content-only adapter、(3) mutation 一元化 + 二重実行抑止、(4) safe_fallback 文言 ID 固定、(5) 早期 SessionOps≺Policy の prerequisite 可否を Supervisor が承認。
- prerequisite (5) が拒否され、かつ A/B/C のみで進める場合 → **停止条件 HIT** → A-2 を次善として再比較（下記）。

### A-2 再比較が必要になった場合の影響範囲（列挙のみ・未実施）

| 領域 | 影響 |
| --- | --- |
| `PrimaryRoute` / LLM schema / IntentRouter prompts | Policy 追加 |
| dispatcher `_DISPATCH_TABLE` | `_dispatch_policy` |
| 評価器 / shadow mismatch / metrics | primary 集合変更 |
| fixture / Gate B | H04 別承認でも整合確認 |
| 後方互換 | 旧 Concierge/Other 写像 |

A-2 でも「intent と permission の混同」コストは残る（ADR）。

---

## 14. PDCA R3

| 段 | 内容 |
| --- | --- |
| Plan | A-3 モデル固定；A/B/C 比較；adapter/mutation/fail-closed |
| Do | 本設計文書のみ（コード変更なし） |
| Check | 挿入 A/B/C は目標順序未達；D+prerequisite が必要 |
| Act | Supervisor へ D 採用可否・SessionOps 順序 prerequisite・safe notice 文言固定を確認待ち。実装・H04・commit 禁止維持 |

---

## 参照

- A-1 R2 inventory: `JEV_BR_H03_H05_OPTION_A1_R2_INVENTORY_20260922.md`
- A-1/A 設計: `JEV_BR_H03_H05_OPTION_A_DESIGN_20260922.md`
- Workers A/B/C（R2）: 前サイクル
