# Cycle R5 — Pre-implementation Contract Freeze（コード変更禁止）

- Date: 2026-09-22
- R4 D2 Design Go: **Accept**
- D 全面後置: Reject 維持
- A-1 Rejected / A-2 保留 / A-3/D2 本線
- **Implementation: Stop 維持**
- runtime / H04 / commit / push / live: **禁止**

## 状態

| 項目 | 状態 |
| --- | --- |
| Gate A-code | 再審査待ち |
| Gate A-accuracy | Not Passed |
| Gate B | Hard No-Go |
| live | Blocked |
| product safety | 未合格 |
| Design Freeze | **未完了**（人間医療・UX レビュー未了） |
| Implementation | **Stop** |

---

## 1. D2-a vs D2-b — 採用決定

### コード追跡結果（推測禁止）

`run_safety_gate_pre`（`src/agents/safety_gate.py:34-60`）は **ローカルかつ副作用なしではない**。

| 呼び出し | 副作用 | 外部通信 |
| --- | --- | --- |
| `validate_and_block_input` | messages append、DB `save_session_to_db`、crisis queue、processing_status clear | DB I/O；LLM なし（confirmed: `chat_input_validator.py`） |
| `handle_diagnosis_if_detected`（phase pre） | medical_history / messages / DB | DB I/O |
| `handle_inappropriate_message_if_detected` | messages / DB | DB I/O |

よって **D2-a（lightweight Safety pre → snapshot）は「既存 Safety pre」を使う限り不適合**。  
「lightweight」を別関数として新設するなら D2-a' になり、まだ存在しない。

### 決定: **D2-b**

```text
raw user text
  → canonical_normalize（副作用なし・危険語/policy marker を消さない）
  → TurnSignalSnapshot.collect（detector 一回）
  → pure SessionOps（条件付き）
  → Safety pre/full（既存・副作用あり・terminal block 可）
  → triage
  → PolicyDecision resolve（additive merge のみ）
  → Policy enforcement
  → terminal HTTP or continue dispatch
```

| 確認項目 | 契約 |
| --- | --- |
| normalization ≠ security sanitization | `canonical_normalize` は Unicode/空白のみ。block/redact/攻撃除去をしない |
| 危険語・policy marker を消さない | strip は両端と内部連続空白の圧縮のみ；部分文字列削除禁止 |
| 判定対象の追跡 | snapshot に `normalized_text_fingerprint` + `norm_algo_version`；**本文はログに複製しない** |
| fingerprint のみ保存 | SHA-256 of `norm_algo_version || "\\0" || normalized_utf8`；raw/medical 全文は observability 禁止 |
| pure SessionOps → LLM/Jev 非送信 | 早期 return で triage/Jev 未到達（D2 と同型） |
| prompt injection / 危険混在 → SessionOps 不到達 | preflight の `security_blocked` / `deterministic_high_risk` / `policy_block` / `!evaluation_complete` で pure 不成立 |

### Exact pipeline sequence（D2-b freeze）

```text
1. receive raw text
2. canonical_normalize(raw) → norm_text   # no I/O, no session write
3. snapshot = collect_pre_route_signals(norm_text)  # once; freeze
4. if pure_session_ops(snapshot): SessionOps handler → HTTP return
5. else: continue without SessionOps mutation
6. run_safety_gate_pre (may mutate/block) using norm_text / raw per existing API
7. … existing mid pipeline (fast SessionOps only if still pure? → NO: mid-pipeline SessionOps は snapshot 再評価のみ、条件不変なら許可は admin 済み時のみ。D2-b では early 以外の SessionOps は「snapshot 条件を再確認し、pure なら実行／否则 skip」)
8. triage (LLM)
9. safety full
10. PolicyDecision = resolve(snapshot.with_additive(triage_bag))
11. enforce → terminal | continue
12. continue → dispatch / orchestrator
13. Jev eligibility consumes same snapshot（再 collect 禁止）
```

**Mid-pipeline SessionOps（fast/triage phase）:**  
snapshot 条件が pure のときのみ実行可。条件が incomplete/policy/high-risk なら **すべて skip**（削除 mutation 禁止）。early で既に return していない場合の二重 SessionOps は、同一 turn_id で SessionOps 成功済みなら idempotent skip。

---

## 2. TurnSignalSnapshot SSOT 契約

| 項目 | 固定値 |
| --- | --- |
| 作成者 | `chat_post_pipeline`（または専用 `preflight.collect_turn_signals`）が **turn 開始時に一度だけ** |
| 格納先 | **request-local** `PipelineRequestContext.signal_snapshot`（正本）。session 永続化しない |
| immutable | `frozen=True` dataclass；更新は `with_additive(...)` が **新インスタンス**を返すのみ |
| turn_id | pipeline 入口で `uuid4()`（または既存 trace_id があればそれを turn_id に採用し、無ければ生成） |
| correlation_id | 既存 Jev/shadow correlation と共用可；無ければ turn_id と同一 |
| fingerprint | `sha256(f"{NORM_ALGO_VERSION}\0{normalized_utf8}")` hex；対象は **canonical_normalize 後文字列のみ** |
| NORM_ALGO_VERSION | `"canon-v1"`（NFC + strip + 内部空白 `\s+`→単一 SP；部分削除なし） |
| consumer | (1) pure SessionOps 判定 (2) Policy resolve (3) Jev eligibility (4) observability（fingerprint/flags のみ） |
| additive merge API | `snapshot.with_additive(bag: Mapping) -> TurnSignalSnapshot` — OR 昇格のみ（§R4） |
| detector_errors | `PreRouteSignals.detector_errors: tuple[str,...]` を保持；merge で **追記のみ**（削除禁止） |
| observability 許可 | `turn_id`, `correlation_id`, `fingerprint`, bool flags, `detector_errors` codes, `evaluation_complete`, `session_operation` **intent 名のみ** |
| observability 禁止 | raw text, normalized full text, medical verbatim, PII |

### 原則の区別

| 操作 | 許可 |
| --- | --- |
| preflight detector **再実行** | **禁止** |
| triage bag **加算** | **許可**（false→true のみ） |
| true→false | **禁止** |
| `evaluation_complete False→True` | **禁止** |
| consumer 独自 signal 再構築 | **禁止** |

---

## 3. session_operation 競合規則（確定）

**方針:** preflight で明示検出した intent を **固定**。後段 triage は SessionOps intent を **書き換えない**。破壊性自動昇格（特に delete）**禁止**。

| 遷移 | 規則 |
| --- | --- |
| None → intent | preflight のみ許可 |
| status → summarize | **禁止**（固定） |
| summarize → delete | **禁止** |
| delete → 別 intent | **禁止** |
| keyword vs triage | **keyword/preflight 勝ち**；triage の session_admin 示唆は intent を変更しない（観測ログのみ可） |
| delete 実行 | 既存 **確認フロー**（pending_memory_delete 等）必須；自動昇格で削除確定しない |

`with_additive` は **policy/safety フラグのみ**対象。`session_operation` フィールドは additive API の対象外（書き込み禁止）。

---

## 4. Mutation transaction 契約（確定）

**採用方式: Memory checkpoint + apply + DB save + 失敗時 memory rollback**  
（「未コミット応答のみ」は採用しない — 部分 append が見える窓を残すため。）

### 段階

```text
A. content 生成（adapter・純関数）
B. mutation plan 作成（構造体のみ）
C. validation（plan 整合・idempotency）
D. checkpoint = copy 対象キー
E. apply plan → memory session
F. DB save
G. success → terminal response
   fail  → restore checkpoint → safe_fallback（mutation なし主張が真実）
```

### 対象キー（checkpoint）

`messages`, `inappropriate_requests`, `counseling_mode`, `illegal_drug_block` / 関連 flag, `pending_memory_delete`（policy では通常触らない）, `modified`

### 失敗・原子性

| 項目 | 契約 |
| --- | --- |
| DB 失敗 | memory を checkpoint へ **必ず戻す**；HTTP は safe_fallback；「履歴変更なし」表示可 |
| user/bot 片方だけ | plan は対で適用；途中例外は rollback |
| inappropriate_requests | bot と同一トランザクション |
| counseling_mode | prescription のみ；apply 内で原子的 set |
| illegal_drug_block | controlled のみ；同上 |
| retry / 重複 | 下記 idempotency |

### Idempotency

| 項目 | 契約 |
| --- | --- |
| key | `(turn_id, policy_kind)` を request-local `enforcement_receipt` に保存 |
| 同一 key 再進入 | memory/DB 再変更せず、**初回 terminal body を再返却**（receipt に status/body 要約） |
| 次ターン | 新 turn_id；旧 receipt 無効 |
| session 永続に key を残す場合 | `(turn_id, kind)` 必須；turn_id 不一致は無視 |

---

## 5. Content-only adapter 契約

各 adapter 戻り値（のみ）:

```text
AdapterResult:
  content: str | structured notice payload
  status_proposal: StatusDiagnosis fields（任意）
  mutation_plan: MutationPlan   # appends/flags の宣言的記述
  observability: dict
```

### 禁止（adapter 内）

session append / DB save / counseling_mode 変更 / routing / Jev / network side effect（**処方 LLM 呼び出しは「content 生成のための許可された例外」だが session に触らない**）

### prescription LLM

| 事象 | 契約 |
| --- | --- |
| timeout / 空 / 例外 | → enforce が **safe_fallback**（E1 系）；MutationPlan 空 |
| 成功 | content + plan のみ；**LLM 出力を PolicyKind/判定根拠にしない**（判定は snapshot） |

---

## 6. safe_fallback 文言 — Freeze 候補レビュー packet

### 6.1 候補

| ID | 文言 | 種別 |
| --- | --- | --- |
| **SF-E1** | title: `一時的なエラーが発生しました`<br>message: `処理中に問題が発生しました。しばらく時間をおいてからもう一度お試しください。`<br>hints: `もう一度お試しください` / `問題が続く場合は薬剤師にご相談ください`<br>出典: `build_system_error_status` | **既存** |
| **SF-E1-NM** | SF-E1 message 末尾に追加:<br>`今回の操作では履歴や記録内容は変更されていません。` | **新規**（要承認） |

### 6.2 使用条件

| fallback_reason | 文言 | 「変更されていません」 |
| --- | --- | --- |
| detector_error / adapter_error / incomplete_evaluation / unknown_kind / empty_content | SF-E1 または SF-E1-NM | **NM は mutation 未開始（checkpoint 前）または rollback 成功後のみ** |
| 部分 mutation 後に rollback 失敗 | SF-E1 **のみ**（未変更を主張しない）+ 内部アラート | NM **禁止** |

### 6.3 流用禁止

救急 HTML / 違法薬物長短テンプレ / 診察境界テンプレ → fallback 禁止（R4 敵対レビュー維持）。

### 6.4 「薬剤師に相談」適合性

全 failure mode で **許容**（臨床断定なし・救急非示唆）。危機併存は上位 Safety が先。AI 敵対レビューは R4 で実施済み。

### 6.5 人間レビュー欄（未完了）

| 欄 | 値 |
| --- | --- |
| 担当（薬剤師/医療安全） | **未記入** |
| 日付 | **未記入** |
| 判定 | **未実施** |
| 対象文言 | SF-E1 / SF-E1-NM |
| 文言 SHA-256（固定時に記入） | SF-E1 既存コード準拠；NM は承認後に計算 |
| プロダクト/UX レビュー | **未実施** |
| 日本語誤認・断定リスク | **未実施** |

**人間レビュー完了まで Implementation Stop 解除不可。**

---

## 7. Feature flag OFF 互換

| Flag | OFF 時 |
| --- | --- |
| `POLICY_ENFORCEMENT_D2=0`（仮名） | 現行 follow-ups / orch / probe 内 collect のまま |
| snapshot 未導入 | consumer は現行 API にフォールバック（実装時に両立期間を Unit A で限定） |

---

## 8. Units A–F 依存 DAG

```text
A snapshot 受け渡し
 ├── B policy 型・resolve
 │    └── D enforcement/mutation owner
 │         ├── E legacy 排他
 │         └── F test/observability
 └── C content-only adapters ──┘（C は A と並行可、D が B+C 待ち）
```

文言 freeze（人間レビュー）は **D の前提ゲート**（未完了なら D 実装禁止）。

---

## 9. R5 必須成果物チェック

| 成果物 | 状態 |
| --- | --- |
| D2-a / D2-b 比較と採用 | **Done — D2-b** |
| exact pipeline sequence | **Done** |
| snapshot SSOT | **Done** |
| session_operation 競合 | **Done — 固定・delete 昇格禁止** |
| mutation transaction | **Done — checkpoint+rollback** |
| idempotency | **Done — turn_id+kind receipt** |
| safe_fallback レビュー packet | **Done（候補）** |
| human medical review 欄 | **空 — 未完了** |
| product/UX review | **未完了** |
| DAG / flag 互換 | **Done** |
| R6 Go/Stop | 下記 |

---

## 10. Design Freeze / R6 Implementation 判定

### Design Freeze Go に必要な項目

| 条件 | 状態 |
| --- | --- |
| preflight 対象テキスト確定 | **Go**（canonical_normalize 後 = D2-b） |
| detector 一回化契約 | **Go** |
| delete intent 上書き禁止 | **Go** |
| transaction 方式確定 | **Go**（checkpoint+rollback） |
| idempotency 確定 | **Go** |
| safe_fallback 文言固定 | **未**（候補のみ） |
| human medical review 完了 | **未** |
| product/UX review 完了 | **未** |

### 判定

| レイヤ | 結果 |
| --- | --- |
| **Engineering contract freeze** | **Conditional Go**（技術契約は固定） |
| **Design Freeze Go（Supervisor 定義全文）** | **Not Yet** — 文言レビュー未完 |
| **R6 Implementation** | **Stop 維持** |

独立 residual（処方 marker 差 / contained≠resolve / 処方 E2E）: **Open 維持**。H03/H05 Closed 根拠に含めない。

---

## 11. PDCA R5

| 段 | 内容 |
| --- | --- |
| Plan | Contract freeze 項目 R5 |
| Do | Safety pre 副作用コード追跡；本文書 |
| Check | D2-a 不適を evidenced；D2-b 採用 |
| Act | 人間医療・UX レビュー待ち。コード変更なし |

---

## 参照

- R4 D2: `JEV_BR_H03_H05_OPTION_A3_R4_D2_DESIGN_20260922.md`
- `run_safety_gate_pre` / `validate_and_block_input` / diagnosis & inappropriate handlers（副作用）
