# Jev Phase 1 Local Shadow — Supervisor Review Report

- 作成日: 2026-09-21
- 役割: Phase 0–1 local shadow 実装の監修レビュー
- 対象スコープ: local 実装・unit / integration 配線（dev shadow / primary / staging は対象外）
- 参照契約: `JEV_PHASE0_CONTRACT_FREEZE_20260921.md`、Plan invariants（PRIMARY ignore / `TYPESAFE` fallback 禁止 / `baseline_triage_hint` 禁止 / 高リスク非格下げ / SessionOps 非 primary / shadow JSONL / timeout 3.5s / 429・5xx 1 retry）
- テスト前提: Jev suite unit **111 passed**（報告時点）。expanded fixture は **draft labels**（Gate B 医療安全レビュー未承認）

---

## 1. 総合判定（Gate A local）

### **Go（条件付き）— Gate A local 実装検証は通過可**

Phase 1 の最重要不変条件である「実行 route は常に legacy」「PRIMARY を構造的に無視」「禁止 payload / secret fallback なし」「本線非伝播」は、実装と integration test で確認できた。default OFF 時の挙動差・例外漏れ・禁止データ混入といった Gate A No-Go 条件に該当する欠陥は見つからない。

ただし次は **精度検証（Gate A 後半〜Gate B）** であり、本判定は「local shadow コードを本番経路に載せないまま精度評価へ進めてよい」まで。**dev shadow 有効化は No-Go**（医療ラベル未承認・live 再評価未実施・`recent_context`/`recent_turns` 不一致）。

| ゲート | 判定 | 一言 |
| --- | --- | --- |
| Gate A local 実装検証 | **Go（条件付き）** | 構造・配線・unit は十分。残差は観測品質・命名整合・deterministic signal 未配線 |
| Gate A → 精度検証 | **Ready with caveats** | live 再評価は production state キー（`recent_turns`）で再実施必須 |
| Gate B dev shadow | **No-Go** | expanded fixture 医療レビュー未承認、dev secret/観測運用未確認 |
| Gate C+ / primary / staging | **No-Go** | 意図的未着手 |

---

## 2. 並列エージェント成果の評価表

| 成果領域 | 品質 | 契約遵守 | 残課題 | 評点 |
| --- | --- | --- | --- | --- |
| **Decisions** (`jev_decisions.py`) | Choice/Noul 分離、`primary_confidence` / `selected_sub_confidence`、未知 enum・範囲外 → invalid、Security→Emergency の Noul 優先、deterministic override API あり。DTO は `JevShadowDecision`（`RouteDecision` に混ぜない）で正しい | `minimal` 固定、`baseline_triage_hint` 非関与、高リスク deterministic override 設計は契約どおり | production shadow から `deterministic_signals` 未接続（下記 §5）。SessionOps は Choice 対象だが Phase 1 では実行に使われず許容。`disagreement` 分類は metrics 側 | **A-** |
| **Client** (`jev_client.py`) | transport 純度が高い。例外を本線に漏らさない。ログに body / Authorization を出さない | **`JEV_API_KEY` のみ**（`TYPESAFE_API_KEY` 参照なし）。timeout 既定 3.5s、429/5xx のみ最大 1 retry、timeout/4xx/network は非 retry | eval スクリプト側は依然 `TYPESAFE` fallback あり（本番コード外だが運用混乱リスク）。resolved_version は取るが metrics への常時露出は薄い | **A** |
| **Metrics + Router adapter** (`jev_metrics.py` / `jev_router.py`) | JSONL `log/jev_intent_router_shadow.jsonl`、fail-open、shape-only state、cost `$0.042/MTok`、matched primary/sub/safety、queue 上限・async worker・session 非 mutate | allowlist state、禁止キー assert/strip、SID は `trace_hash` のみ、raw answers 拒否 | `disagreement_class` / `openai_cost_saved` 分離は Phase 1 では `legacy_saved_calls=0` 固定で未実測。async race で executed join が legacy フォールバックしうる（Phase 1 では実質同値）。`medicine_qa_focus` を router から渡していない | **A- / B+** |
| **Docs / Fixture** (Phase0 freeze + expanded YAML) | Phase0 凍結表は実装と整合。expanded YAML は Gate B 想定ケースを網羅的に「器」として用意 | draft / medical review pending が明示されているのは正しい | **ラベル未承認のまま CI hard-fail にすると危険**。eval スクリプトの state キー名が本番と不一致（§3 / §5） | **B（器として Go、精度判定材料としては No-Go）** |

---

## 3. 統合配線の監修結果（router / dispatcher / pipeline）

### 3.1 `resolve_route()` — PRIMARY ignore（検証済み）

```58:94:src/dialogue/routing/router.py
def resolve_route(...) -> RouteDecision:
    legacy = resolve_route_unified_or_legacy(...)
    correlation_id = _maybe_schedule_jev_shadow(...)
    ...
    # Phase 1 invariant: never return a Jev decision (PRIMARY flag ignored).
    return legacy
```

- `is_jev_intent_router_primary_enabled()` は **本番 path で一度も呼ばれない**（getter 予約のみ）。PRIMARY=true でも return は常に `legacy`。
- integration: `test_resolve_route_primary_flag_true_still_returns_legacy` が構造保証。
- **結論: 「PRIMARY true でも Jev を返さない」は満たす。**

### 3.2 Shadow schedule 配線

- shadow ON 時のみ `build_jev_router_state` → `schedule_jev_shadow`。
- `triage_result` は state builder に渡すが **明示 discard**（`baseline_triage_hint` 禁止）。
- **未配線:** `deterministic_signals` を router が渡していない → SafetyGate / known_attack / medical_examination の deterministic override は production shadow では動かない。Phase 1 の「実行非変更」には無害。比較ログは **純 Jev 意見**になり、Phase 2 二重ゲート準備としては未完。

### 3.3 Session key: `_jev_shadow_correlation_id`

| 項目 | 内容 |
| --- | --- |
| 書き込み元 | `router.resolve_route` のみ（routing decision ではない） |
| 読み取り | `dispatcher.try_agent_dispatch` → `notify_executed_decision` |
| 許容性 | Phase 1 の join 用として **許容**。`_routing_decision` / `_intent_router_shadow` への Jev 書き込みは無い |
| リスク | (1) schedule 失敗時に **旧 corr を clear しない** → 次 dispatch が stale join する可能性。(2) async shadow が notify 前に完了すると executed は legacy フォールバック（Phase 1 では executed≈legacy のため実害小）。(3) session 永続化対象に入るとログ相関がセッション寿命に残る |
| 推奨 | Gate B 前に「schedule 失敗/スキップ時は pop」「dispatch 後または record 後に clear」を検討 |

### 3.4 `dispatcher.notify_executed_decision`

- Jev decision を読まず、実行 decision のみ registry へ。fail-open。設計意図どおり。
- dispatch スキップ経路では notify されない → shadow 記録の executed は legacy 相当。Phase 1 監視上は許容。

### 3.5 `chat_post_pipeline` shadow 二重起動抑止

- `JEV_INTENT_ROUTER_SHADOW` ON 時は既存 IntentRouter v2 `schedule_shadow_observation` を起動しない。
- **妥当。** OFF 時は従来 shadow 継続。Jev と v2 shadow の同時起動による `resolve_route` 再入・session 競合を避けている。

### 3.6 Flags / runtime config

| Getter | 既定 | 所見 |
| --- | --- | --- |
| `is_jev_enabled` | false | kill switch。v2 unset=ON と逆で正しい |
| `is_jev_intent_router_shadow_enabled` | enabled ∧ shadow | 二重 AND |
| `is_jev_intent_router_primary_enabled` | enabled ∧ primary | Phase 1 未使用（正しい） |
| `jev_timeout_sec` | 3.5（0.5–30 clamp） | 契約一致 |
| `jev_model` | `jev-latest` | 契約一致 |
| floor / high / noul | 0.70 / 0.85 / 0.75 | Phase 1 は観測用。primary 判定には未使用 |

### 3.7 `recent_turns` vs `recent_context`（重要）

| 経路 | キー名 |
| --- | --- |
| production `build_jev_router_state` / questions 文言 | **`recent_turns`** |
| `scripts/eval_jev_intent_router_10.py`（pilot 評価） | **`recent_context`** |

pilot 30/30 の数値は **eval スクリプトの state 形状**に紐づく。local shadow 実装は契約どおり `recent_turns`。**live 再評価を eval スクリプトのまま回すと、本番 shadow と入力契約が不一致**になりうる。Gate B 前に eval / fixture / production を `recent_turns` に揃えること。

---

## 4. Gate A チェックリスト

| # | 項目 | 結果 | 根拠 |
| --- | ---: | --- | --- |
| A1 | M0 設計凍結（adapter / state / flags / secret / timeout） | **passed** | Phase0 freeze と実装が一致。`TYPESAFE` fallback なし、`minimal` のみ |
| A2 | unit / mock CI green | **passed** | Jev suite 111 passed（報告前提） |
| A3 | flag default OFF で legacy 同一 | **passed** | shadow OFF で schedule なし、return legacy identity |
| A4 | 障害注入で legacy fallback（実行不変） | **passed** | 常に legacy return；client fail でも session dispatch key 非 mutate |
| A5 | 禁止データが state / ログに含まれない | **passed（unit 範囲）** | contract test + metrics deny-list。本番長時間ログのサンプリング監査は未実施 → Gate B |
| A6 | PRIMARY true でも Jev 非 return | **passed** | 構造 + integration |
| A7 | Emergency/Security 既存陽性の Jev 格下げで実行変更なし | **passed（Phase 1）** | 実行が Jev でないため格下げ不可。shadow DTO 側の deterministic 二重ゲートは **partial**（未配線） |
| A8 | SessionOps を Jev primary にしない | **passed（Phase 1）** | primary path 自体が未実装。fast-path 維持 |
| A9 | shadow log path / schema 最低限 | **passed** | `jev_intent_router_shadow.jsonl`。plan 全文フィールド（`disagreement_class` 等）は **partial** |
| A10 | expanded safety fixture | **partial** | 器あり・**draft labels**・医療レビュー未。Gate A 精度の十分条件にしない |
| A11 | live 精度 / perf 再評価（production state） | **failed / not done** | Gate A 後半〜Gate B。`recent_turns` 整合後に再実施 |

**Gate A local 実装:** 実質 **passed**。  
**Gate A 精度クローズ:** **未完**（意図的）。

---

## 5. 発見した問題と修正済み項目

### 5.1 修正済み（実装に織り込み済みで良好）

1. Phase 1 で PRIMARY を読まず常に legacy return（構造的 ignore）。
2. `JEV_API_KEY` のみ。client に `TYPESAFE_API_KEY` fallback なし。
3. `baseline_triage_hint` 非送信（builder discard + strip + tests）。
4. timeout 3.5s、429/5xx のみ 1 retry。
5. shadow JSONL fail-open、生 SID / raw answers / key 拒否。
6. Jev ON 時の v2 shadow 二重起動抑止。
7. Session の routing/dispatch キーへ Jev を書かない。
8. confidence を primary / selected_sub に分離（Store Noul で primary_confidence 流用しない）。

### 5.2 未修正・要注意（Gate A Go は阻害しないが記録）

| ID | 深刻度 | 内容 | 推奨タイミング |
| --- | --- | --- | --- |
| R1 | **High（Gate B）** | eval `recent_context` vs prod `recent_turns` | live 再評価前に統一 |
| R2 | Medium | router が `deterministic_signals` 未渡し | Phase 2 primary 前。shadow 比較を「純 Jev」とするなら文書化して明示 |
| R3 | Medium | `_jev_shadow_correlation_id` の clear 欠如 / stale join | Gate B 観測精度前 |
| R4 | Low–Med | `medicine_qa_focus` 未注入 | follow-up 品質観測前 |
| R5 | Low | `assert` で禁止キー検査（`-O` で無効化） | 本番は raise/log の明示チェック推奨 |
| R6 | Low | plan の `disagreement_class` / OpenAI saved cost 分離が未完 | canary コストゲート前 |
| R7 | Info | expanded fixture draft — **Gate B 医療レビュー必須** | Gate B 入場条件 |
| R8 | Info | eval スクリプトの `TYPESAFE_API_KEY` fallback 残存 | 運用ドキュメントで「本番は JEV_API_KEY のみ」を再強調 |

### 5.3 本レビューでコード修正は行っていない

監修レポートのみ。上記 R1–R8 は次アクション候補。

---

## 6. 意図的にやっていないこと

| 項目 | 状態 | 理由 |
| --- | --- | --- |
| dev 環境での shadow 有効化 | 未実施 | Gate B 条件未充足（医療ラベル・secret・観測運用） |
| `JEV_INTENT_ROUTER_PRIMARY` 実装 / 有効化 | 未実施 | Phase 2。Phase 1 は構造的に無視 |
| staging / production 接続 | 未実施 | 別承認が必要 |
| SessionOps の Jev primary 化 | 対象外 | 現行 fast-path 維持 |
| `with_baseline_triage` / hint 再導入 | 禁止 | Phase0 で棄却済み |
| expanded fixture の CI hard-fail 化 | 未実施 | draft labels |
| 本番ログ実サンプリング監査 | 未実施 | local unit 範囲外 |
| OpenAI IntentRouter cost 70% 削減の実測 | 未実施 | primary 運用後 |

---

## 7. 次アクション

### 7.1 すぐ（Gate A 精度 / live 再評価）

1. **eval / fixture / production の state キーを `recent_turns` に統一**し、`scripts/eval_jev_intent_router_10.py` を本番契約に合わせて再実行（repeat≥3）。
2. pilot 10 +（可能なら）draft expanded を **参考値**として再計測。ラベル未承認の hard gate はかけない。
3. shadow JSONL を local flags ON で数件書き、禁止フィールド混入の目視確認。

### 7.2 Gate B prep

1. expanded fixture の **医療安全レビュー承認**（Emergency ± / Security / medical_examination / multi-intent / follow-up）。
2. FN=0・joint accuracy の採点定義を freeze。
3. `deterministic_signals` 配線方針を文書化（shadow は純 Jev のままか、二重ゲート済みラベルにするか）。
4. `_jev_shadow_correlation_id` の lifecycle（clear）を実装。
5. dev: `JEV_API_KEY`、ログ保持・閲覧権限、rollback（`JEV_ENABLED=false`）手順。
6. 上記完了後にのみ **dev shadow** を検討（本レポート時点は **No-Go**）。

### 7.3 やらないこと（再確認）

- PRIMARY canary、staging、SessionOps primary、hint 復活は次フェーズ以降。

---

## 付録: Plan invariants 照合（要約）

| Invariant | 結果 |
| --- | --- |
| Phase 1 always returns legacy | **OK** |
| PRIMARY ignored | **OK**（未参照） |
| no `TYPESAFE_API_KEY` fallback（本番 client） | **OK** |
| `baseline_triage_hint` forbidden | **OK** |
| Emergency/Security not downgradable（実行） | **OK**（非実行）。DTO 二重ゲートは **partial** |
| SessionOps not primary | **OK**（Phase 1） |
| shadow log path | **OK** (`jev_intent_router_shadow.jsonl`) |
| timeout 3.5s | **OK** |
| retry 429/5xx once | **OK** |

---

## 追記（実装側フォローアップ・同日）

監修指摘を受けて以下を反映済み:

1. state に `recent_turns`（契約名）と `recent_context`（pilot eval 互換 alias）を併記
2. `resolve_route` から `deterministic_signals` を legacy/triage 由来で配線（高リスク陽性の shadow 比較用。実行は不変）
3. `_jev_shadow_correlation_id` を schedule 失敗時に pop、dispatcher notify 後に pop

これにより命名差・deterministic 未配線・corr clear の残差は解消。Gate B / live 再評価 / 医療ラベル承認は引き続き未着手。

---

*Supervisor: Phase 0–1 local shadow code review — 2026-09-21*
