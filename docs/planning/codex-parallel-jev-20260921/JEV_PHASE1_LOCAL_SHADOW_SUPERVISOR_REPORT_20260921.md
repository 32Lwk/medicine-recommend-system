# Jev Phase 1 Local Shadow — Supervisor Review Report

> ## ERRATUM（2026-09-22 Agent G）
>
> 本書作成時点の「live 未実施」は **歴史記述**。現行は live `012129` 実行済だが Gate A-accuracy は引き続き **Not Passed**（`JEV_GATE_A_ACCURACY_VERDICT_20260922.md`）。Gate B / primary / staging / prod = Hard No-Go。Focus 本配線 = No-Go。


- 作成日: 2026-09-21
- 最終更新: 2026-09-21（実装フォローアップ反映後のドキュメント整合監査）
- 役割: Phase 0–1 local shadow 実装の監修レビュー
- 対象スコープ: local 実装・unit / integration 配線（dev shadow / primary / staging は対象外）
- 参照契約: `JEV_PHASE0_CONTRACT_FREEZE_20260921.md`、Plan invariants（PRIMARY ignore / `TYPESAFE` fallback 禁止 / `baseline_triage_hint` 禁止 / 高リスク非格下げ / SessionOps 非 primary / shadow JSONL / timeout 3.5s / 429・5xx 1 retry）
- テスト前提: Jev suite unit **111 passed**（報告時点）。expanded fixture は **draft labels**（Gate B 医療安全レビュー未承認）

---

## 1. 総合判定（Gate A local）

### Gate A-code: **Passed（構造のみ）** — Gate A-accuracy: **Not Passed**

「実行 route は常に legacy」「PRIMARY を構造的に無視」「禁止 payload / secret fallback なし」「本線非伝播」は実装と integration で確認できた。**これはコード契約の合格であり、精度ゲートの合格ではない。**

| ゲート | 判定 | 辛口一言 |
| --- | --- | --- |
| Gate A-code（local 構造・配線・unit） | **Passed** | 不変条件とフォローアップ配線は揃った。これだけで「精度 OK」と呼ぶな |
| Gate A-accuracy（live / production state） | **Not Passed** | live `012129` 実行済・CI/コスト未達（`JEV_GATE_A_ACCURACY_VERDICT_20260922.md`）。pilot は smoke のみ |
| Gate B（dev shadow） | **Hard No-Go** | 医療ラベル未承認・A-accuracy 未達・dev 運用未確認。unit 緑や pilot 100% で入場するな |
| Gate C+ / primary / staging | **Hard No-Go** | 意図的未着手。議論すら時期尚早 |

**禁止表現（本レポート以降）:** 「Gate A Go（条件付き）」を精度合格と読み替えること。Gate A は **code / accuracy の二層**に分割して報告する。

---

## 2. 並列エージェント成果の評価表

| 成果領域 | 品質 | 契約遵守 | 残課題 | 評点 |
| --- | --- | --- | --- | --- |
| **Decisions** (`jev_decisions.py`) | Choice/Noul 分離、confidence 分離、未知 enum → invalid、deterministic override API あり。DTO は `JevShadowDecision` | `minimal` 固定、hint 非関与 | SessionOps は Choice 対象だが Phase 1 実行未使用で許容 | **A-** |
| **Client** (`jev_client.py`) | transport 純度高、本線非伝播、secret 非ログ | **`JEV_API_KEY` のみ**。timeout 3.5s、429/5xx 1 retry | eval スクリプトに `TYPESAFE` fallback 残存（本番外）。resolved_version の metrics 露出は薄い | **A** |
| **Metrics + Router adapter** | JSONL path、fail-open、allowlist、`deterministic_signals` **配線済**、corr lifecycle **clear 済**、`recent_turns`+`recent_context` alias | 禁止キー strip、SID は `trace_hash` のみ | `medicine_qa_focus` は builder 引数あるが **router から未注入**。cost 分離は `legacy_saved_calls=0` 固定で未実測 | **A-** |
| **Docs / Fixture** | Phase0 凍結は実装と概ね整合（本監査で追記） | draft / medical review pending 明示は正しい | **ラベル未承認のまま CI hard-fail 禁止**。Test Plan §8.4 の「dev shadow まで」は誤記だった（修正対象） | **B** |

---

## 3. 統合配線の監修結果（router / dispatcher / pipeline）

### 3.1 `resolve_route()` — PRIMARY ignore（検証済み）

- `is_jev_intent_router_primary_enabled()` は本番 path で未使用。return は常に `legacy`。
- integration: `test_resolve_route_primary_flag_true_still_returns_legacy`。
- **結論: PRIMARY true でも Jev を返さない — OK。**

### 3.2 Shadow schedule / deterministic_signals（**実装済・追記反映後**）

- shadow ON 時のみ `build_jev_router_state` → `schedule_jev_shadow`。
- `triage_result` は state builder で **明示 discard**（`baseline_triage_hint` 禁止）。
- **`deterministic_signals`:** `router._deterministic_signals_from_context(legacy, triage)` から schedule に渡す。高リスク陽性の **shadow 比較用**。実行 decision は不変。
- Phase 1 の「実行非変更」には無害。Phase 2 二重ゲートの **観測側準備は揃った**（実行側は未実装）。

### 3.3 Session key: `_jev_shadow_correlation_id`（**clear 実装済**）

| 項目 | 内容 |
| --- | --- |
| 書き込み | `resolve_route` で schedule 成功時のみ set |
| clear | shadow OFF / schedule 失敗・スキップ時に `pop`；`dispatcher` の `notify_executed_decision` 後に `pop` |
| 許容性 | join 用のみ。`_routing_decision` / `_intent_router_shadow` への Jev 書き込みなし |
| 残リスク | dispatch スキップ経路では notify されない → executed は legacy 相当（Phase 1 許容）。session 永続化対象に入ると相関が残りうる（運用確認は Gate B） |

### 3.4 `dispatcher.notify_executed_decision`

- Jev decision を読まず、実行 decision のみ registry へ。fail-open。notify 後 corr clear。

### 3.5 `chat_post_pipeline` 二重起動抑止

- `JEV_INTENT_ROUTER_SHADOW` ON 時は既存 v2 `schedule_shadow_observation` を起動しない。**妥当。**

### 3.6 Flags / runtime

| Getter | 既定 | 所見 |
| --- | ---: | --- |
| `is_jev_enabled` | false | kill switch。v2 unset=ON と逆で正しい |
| `is_jev_intent_router_shadow_enabled` | enabled ∧ shadow | 二重 AND |
| `is_jev_intent_router_primary_enabled` | enabled ∧ primary | Phase 1 未使用（正しい） |
| `jev_timeout_sec` | 3.5 | 契約一致 |
| floor / high / noul | 0.70 / 0.85 / 0.75 | 観測用。primary 判定未使用 |

### 3.7 `recent_turns` / `recent_context`（**alias 実装済**）

| 経路 | キー |
| --- | --- |
| production `build_jev_router_state` | **`recent_turns`（契約名）+ `recent_context`（同一 list の alias）** |
| `scripts/eval_jev_intent_router_10.py` | 現状も `recent_context` のみ構築 |

**現状:** production は両キーを出すため、eval が `recent_context` を読んでも形状は整合する。  
**負債:** eval スクリプトが契約名 `recent_turns` をまだ書いていない。live 再評価レポートには **両キー存在 / 契約名優先** を明記し、いずれ eval 側も `recent_turns` を正とするよう揃えること。  
**禁止:** 「キー不一致だから Gate B 入場不可」を **現コード状態**の主因にすること（フォローアップ前の診断の残り）。Gate B Hard No-Go の主因は **医療ラベル未承認と Gate A-accuracy Not Passed**。

---

## 4. Gate A チェックリスト（辛口）

| # | 項目 | 結果 | 根拠 |
| --- | ---: | --- | --- |
| A1 | M0 設計凍結 | **passed** | Phase0 freeze と実装一致 |
| A2 | unit / mock green | **passed** | 111 passed（報告前提） |
| A3 | default OFF で legacy 同一 | **passed** | schedule なし、return identity |
| A4 | 障害時も実行不変 | **passed** | 常に legacy return；fail-open |
| A5 | 禁止データ非混入 | **passed（unit）** | contract + deny-list。本番ログ監査は **未** → Gate B |
| A6 | PRIMARY ignore | **passed** | 構造 + integration |
| A7 | 高リスク既存陽性の実行非格下げ | **passed（Phase 1）** | 実行が Jev でない。shadow DTO 側は `deterministic_signals` **配線済** |
| A8 | SessionOps non-primary | **passed（Phase 1）** | primary path 未実装 |
| A9 | shadow log path | **passed（schema 最低限）** | path OK。`disagreement_class` / OpenAI saved 分離は **partial** |
| A10 | expanded fixture | **not a Gate A pass criterion** | 器のみ・draft。**精度合格材料に使うな** |
| A11 | live 精度 / perf（production state） | **done / Not Passed** | live `012129` 実行済だが Gate A-accuracy **Not Passed**（CI/コスト）。Gate A を閉じるな |

**Gate A-code:** Passed。  
**Gate A-accuracy:** **Not Passed。Gate A 全体を「完了」と呼ぶな。**

---

## 5. 問題リスト（フォローアップ後）

### 5.1 修正済み（実装反映済 — ドキュメントも本版で同期）

1. PRIMARY 構造的 ignore。
2. `JEV_API_KEY` のみ。
3. `baseline_triage_hint` 非送信。
4. timeout 3.5s / 429・5xx 1 retry。
5. shadow JSONL fail-open。
6. v2 shadow 二重起動抑止。
7. confidence 分離。
8. **`recent_turns` + `recent_context` alias。**
9. **`deterministic_signals` を router から配線。**
10. **`_jev_shadow_correlation_id` の schedule 失敗時 / notify 後 clear。**

### 5.2 未修正・要注意（残債）

| ID | 深刻度 | 内容 | 推奨タイミング |
| --- | --- | --- | --- |
| R1′ | Low | eval スクリプトが契約名 `recent_turns` を未使用（alias で実害小） | live 再評価前に契約名へ寄せる |
| R4 | Medium | `medicine_qa_focus` が router → builder 未注入 | follow-up 品質観測前 |
| R5 | Low | 禁止キー検査が `assert`（`-O` 無効化） | 本番は明示 raise/log |
| R6 | Med（Gate C） | `disagreement_class` / OpenAI saved cost 分離未実測 | canary コストゲート前 |
| R7 | **High（Gate B）** | expanded fixture draft — **医療レビュー必須** | Gate B 入場条件 |
| R8 | Low | eval の `TYPESAFE_API_KEY` fallback 残存 | 運用 docs で本番契約を再強調 |
| R9 | **High（Gate A-acc）** | live `012129` 実行済・**Not Passed**（CI/コスト） | Gate A 精度クローズ条件 |

### 5.3 旧レポートのドリフト（監査で是正）

初版 §3.2 / §3.3 / §3.7 / §5.2 R1–R3 の「未配線・キー不一致・clear 欠如」は **フォローアップ実装前の診断**。現コードと矛盾するため本版で置換した。追記セクションだけ直して本体を残すのはドキュメント負債だった。

---

## 6. 意図的にやっていないこと

| 項目 | 状態 | 理由 |
| --- | --- | --- |
| dev shadow 有効化 | 未実施 | Gate B Hard No-Go |
| PRIMARY 実装 / 有効化 | 未実施 | Phase 2 |
| staging / production | 未実施 | 別承認 |
| SessionOps Jev primary | 対象外 | fast-path 維持 |
| `with_baseline_triage` 復活 | 禁止 | Phase0 棄却 |
| expanded CI hard-fail | 禁止 | draft labels |
| 本番ログサンプリング監査 | 未実施 | local unit 外 |
| OpenAI cost 70% 実測 | 未実施 | primary 後 |

---

## 7. 次アクション

### 7.1 Gate A-accuracy（必須・**Not Passed** — live `012129`）

1. local flags ON で shadow JSONL 数件書き、禁止フィールド目視。
2. production 契約（`recent_turns` 優先）で pilot live 再評価（repeat≥3）。接続失敗は accuracy 分母から除外。
3. pilot 100% を **Gate B 入場条件にしない**。

### 7.2 Gate B prep（全部揃うまで Hard No-Go）

1. expanded fixture **医療安全レビュー承認**。
2. FN=0・joint accuracy の採点定義 freeze。
3. `medicine_qa_focus` 注入方針の決定（入れるなら session 既存値のみ）。
4. dev: `JEV_API_KEY`、ログ権限、rollback（`JEV_ENABLED=false`）。
5. 上記 + Gate A-accuracy 完了後にのみ dev shadow 検討。

### 7.3 やらないこと

- PRIMARY canary、staging、SessionOps primary、hint 復活。

---

## 付録: Plan invariants 照合

| Invariant | 結果 |
| --- | --- |
| Phase 1 always returns legacy | **OK** |
| PRIMARY ignored | **OK** |
| no `TYPESAFE_API_KEY` fallback（本番 client） | **OK** |
| `baseline_triage_hint` forbidden | **OK** |
| Emergency/Security not downgradable（実行） | **OK**。shadow DTO は signals **配線済** |
| SessionOps not primary | **OK**（Phase 1） |
| shadow log path | **OK** |
| timeout 3.5s / retry 429・5xx once | **OK** |
| `recent_turns` contract + eval alias | **OK**（実装） |
| corr clear on fail / after notify | **OK** |

---

*Supervisor: Phase 0–1 local shadow code review — 2026-09-21（docs drift audit sync）*
