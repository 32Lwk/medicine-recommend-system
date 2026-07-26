# Chat Pipeline v2

**ブランチ**: `feature/chat-pipeline-v2`  
**フラグ**: 本番・dev とも **env 未設定で v2 + PRIMARY + TRIM すべて ON**（pytest 中のみ OFF）。ロールバックは `CHAT_PIPELINE_V2=false` 等。

### 一括 ON（追加 env 不要）

| 環境 | 設定 |
|------|------|
| ローカル / GCP dev / GCP 本番 / AWS | 特になし（`CHAT_PIPELINE_V2` 未設定 = 全セッション v2） |
| 明示 OFF | `CHAT_PIPELINE_V2=false` または `CHAT_PIPELINE_V2_DENYLIST=<sid>` |

### 環境変数一覧

| 環境変数 | 用途 |
|---------|------|
| `CHAT_PIPELINE_V2` | グローバル ON/OFF。未設定時 ON（pytest 除く） |
| `CHAT_PIPELINE_V2_DENYLIST` | 一致 sid を v2 から除外（ロールバック） |
| `CHAT_PIPELINE_V2_INTENT_ROUTER` | 既定 ON。`false` で router 全体 OFF |
| `CHAT_PIPELINE_V2_INTENT_ROUTER_DISPATCH` | 既定 ON。`false` で shadow のみ（旧 orchestrator dispatch） |
| `CHAT_PIPELINE_V2_INTENT_ROUTER_LLM` | 既定 ON。`false` で gate/triage のみ |
| `ROUTING_UNIFIED_PIPELINE` | v2 + Intent Router ON 時 **既定 ON**。Concierge follow-up の execution_lock |
| `ROUTING_MEDICINE_SIDE_EFFECT_QA` | 同上。**副作用 QA** 専用 early route |
| `ROUTING_FOLLOWUP_LLM` | 同上。曖昧 follow-up の LLM 判定 |
| `PERF_META_SAFETY_SHORTPATH` | 同上。meta 経路 safety_gate 短縮 |
| `ROUTING_MEDICINE_SIDE_EFFECT_KB` | 同上。CSV 未ヒット時 KB 補完 |

### Unified Routing（2026-07-25）

Intent Router が正しい `sub_route` を返しても実行層（Concierge regex / dispatcher ゲート）で上書きされていた問題を、`RoutingDecision.execution_lock` と `unified_router.py`（Layer1 シグナル → follow-up LLM → legacy）で解消。

| sub_route | 実行 |
|-----------|------|
| `medicine_side_effect_qa` | `handle_medicine_side_effect_qa`（CSV → KB、症状 reco へ入れない） |
| `medicine_qa` | `handle_medicine_information_qa` → `chat_with_medicine_context`（比較・説明・選び方。LLM + ブランド解決 CSV 文脈） |
| Concierge meta follow-up | `concierge_app_about` / `concierge_architecture` 等（changelog 固定を禁止） |

**医薬品比較 Q&A（2026-07-25 追記）**: 「ロキソニンとイブの違い」等は `medicine_qa` へ。副作用判定の誤ルーティングを `medicine_qa_routing.is_strict_medicine_side_effect_question` で防止。通称解決は [`MEDICINE_BRAND_RESOLVE.md`](MEDICINE_BRAND_RESOLVE.md)。

**日常口語・文脈 routing（2026-07-26 追記）**: 指示語 follow-up・アルコール併用・年齢/ドーピング slot・効き目+副作用複合を `infer_medicine_qa_focuses` で一般化。eval は [`MEDICINE_QA_ROUTING.md`](MEDICINE_QA_ROUTING.md) 参照。

**製品画像・比較 UI（2026-07-26 追記）**: パッケージ画像は SSE/JSON 両経路で `product_images_html` を付与。比較・選び方セクションは `ui-qa-product-line` HTML。画像未準備時は「まだ準備できていません」+ 成分 1 文（サーバー生成）。[`MEDICINE_QA_ROUTING.md`](MEDICINE_QA_ROUTING.md) 参照。

**SSE `done` と副作用 Q&A（2026-07-25）**: `handle_medicine_side_effect_qa` 完了後、`finalize_medicine_qa_response` が DB に保存した bot メッセージを SSE `done.bot_message` に載せる。in-memory `session["messages"]` が空の場合は `chat_stream._messages_for_sse_done()` が DB から復元。処理バブル残留（「AI分析中」のまま）を防止。

**ゴールデン再検証**: `tests/fixtures/v2_golden_aws_6_sessions.yaml` + `--scenarios-path`（AWS staging 6 セッション由来）

**観測**: `dialogue_route_execution` ログ、`log/analysis/*_local_v2_chat_test_golden-aws-6-final.md`

| Wave 1a 実装済み | `DialogueContext` / `ContextProvider` / `SessionOps` / `ResponseEnvelope` / pipeline hook / Web SSE・LINE 配信アダプタ |
| Wave 1b shadow | `src/dialogue/routing/` gate → LLM map → guards。`dialogue_state.routing` に記録のみ |
| Wave 1b dispatch | `src/dialogue/dispatcher.py` — `try_agent_dispatch` が legacy handler へ委譲。未対応は ChatOrchestrator へ |
| Wave 1b LLM | `intent_router_llm.py` — structured JSON（`docs/schemas/intent_router_v1.json`）。OFF 時 triage マップのみ |
| Wave 2 移行 | `sync_legacy.py` — counseling / handoff / pending の dual-write（v2 ON 時） |
| Wave 2 Concierge | `concierge_context.py` — `dialogue_state.concierge` 優先の last_intent 解決 |
| Wave 2 履歴 | `history.py` — v2 時 ContextProvider 窓（triage / concierge / counseling） |

---

## 目的

Web / LINE 共通チャット基盤の **決定権分散**（SessionAgent×2、SafetyGate×2、meta_triage、legacy fallback 競合）と **履歴注入の散在** を解消する。OTC 推奨本体は **rule_based 維持**（ハイブリッド方針）。

正解源: [`CHAT_ROUTE_EXPECTATIONS.md`](CHAT_ROUTE_EXPECTATIONS.md) + [`tests/fixtures/expected_v2_diff.yaml`](../../tests/fixtures/expected_v2_diff.yaml)（旧 pipeline 一致は副次）。

---

## パッケージ境界

| パス | 責務 | Wave |
|------|------|------|
| `src/dialogue/` | DialogueContext、ContextProvider、SessionOps、ResponseEnvelope、Pipeline v2 hook | 1a–1b |
| `src/core/` | rule_based 推奨、medicine_logic、スコアリング CSV | 変更最小 |
| `src/agents/` | 各 Agent 実装（ContextBundle 受け取りへ段階移行） | 2–3 |
| `src/handlers/chat/` | エントリ（`chat_post_pipeline`）。v2 ON 時のみ `dialogue` へ委譲 | 1a |

**禁止**: `src/dialogue/` から `medicine_logic` の推奨スコアリングを直接呼ばない（Physical Agent 経由）。

---

## フェーズ概要

```
Pre-P0 (v2 ブランチ先頭, 3–5 営業日)
  → dev 手動デプロイ + LINE QA 10 項目 (48h SLA)
Wave 0 (3–4 週): 仕様・シナリオ・schema・ベースライン
Wave 1a: DialogueContext + ContextProvider + SessionOps + Envelope（category routing は旧 100%）
Wave 1b: 2 段 IntentRouter (gate → LLM)
Wave 2–4: Agent 適応、legacy 削除、観測性統一
```

**CCR ブロッカー**: [`CONCIERGE_CONTEXT_ROUTING_PLAN`](../planning/CONCIERGE_CONTEXT_ROUTING_PLAN_2026-06-27.md) の `concierge_state` 永続化が main/dev マージ完了まで **Wave 1a 開始不可**。

**Pre-P0 ゲート**: [`PRE_P0_LINE_QA_10.md`](../ops/PRE_P0_LINE_QA_10.md) 全 Pass まで Wave 0 本実装（1a コード）着手停止。

---

## Wave 1a スコープ境界（生命線）

### 変更してよいもの

- `src/dialogue/context.py` — load/save、dual-write
- `src/dialogue/context_provider.py` — agent_kind 別履歴窓
- `src/dialogue/session_ops.py` — delete / summarize / status（SessionAgent から移行）
- `src/dialogue/envelope.py` — `delivery_mode`: `sync` | `sse_phased` | `line_chunked`
- `src/handlers/chat/chat_pipeline_end_guard.py` — fail-loud 連動（Pre-P0 後）
- `chat_post_pipeline.py` — **SessionOps 差し替え hook のみ**（v2 フラグ ON 時）

### 変更禁止（Wave 1b まで CI fail: `w1a-scope-creep-lint`）

- `chat_triage.py` / `meta_triage.py` / category 分岐
- `ChatOrchestrator` の dispatch 表
- `concierge_enrich` の独立経路
- legacy fallback の削除（Wave 3）

### 正直な期待値

| 領域 | Wave 1a 完了時 | 改善時期 |
|------|---------------|---------|
| SessionOps / status / delete | 改善 | 1a |
| response_missing / end_guard | 改善（Pre-P0 + 1a） | Pre-P0〜1a |
| Physical / fever routing | 旧 pipeline 維持 | 1b |
| Counseling / Emotional 文脈 | **弱いまま正常** | Wave 2 |
| architecture follow-up | CCR 依存、部分改善 | CCR + 2 |

---

## dual-write 読取優先順位

DialogueContext 合成ビュー（Wave 1a）:

1. `session.dialogue_state`（v2 正）
2. `session.concierge_state`（CCR 移行中）
3. レガシー: `pending_memory_delete`, `counseling_mode`, `handoff_*` 等

書込: v2 フィールド + レガシー mirror（移行期のみ）。owner 表は [`CHAT_ROUTE_EXPECTATIONS.md`](CHAT_ROUTE_EXPECTATIONS.md) §移行。

---

## ContextProvider override（default 8 ターン）

| agent_kind | max_turns | 備考 |
|------------|-----------|------|
| default | 8 | 一般 |
| session_ops | 6 | 操作意図は直近で足りる |
| physical | 12 | 症状ヒアリング |
| counseling | 10 | Wave 2 で 20 へ拡張検討 |
| concierge | 8 | redirect / architecture |
| emergency | 4 | 最小遅延 |
| store | 6 | 店舗意図は短窓 |
| emotional | 10 | Wave 2 で強化 |

---

## correction 再実行契約

- **1 HTTP POST = 1 パイプライン実行**（再帰 dispatch 禁止）
- correction 入力時: 直前 bot 応答を **無効化せず**、新 route で上書き応答を返す
- Agent 別: Physical → 推奨再計算、SessionOps → 意図再分類、Concierge → topic 維持

---

## follow-up 内容 KPI（Wave 0 仕様）

architecture 系 follow-up（例: 「技術面を詳しく」）:

- greeting 禁止（「こんにちは」単独応答は Fail）
- 技術語彙 1 つ以上（スタック / API / インフラ等）または前ターン topic 明示参照

---

## ベースライン（Wave 0 計測）

**ソース**: `log/analysis/2026-06-28_downloaded-logs-20260626-20260627-20260627-162735.md`（medicine-recommend-dev, ~31h）

| KPI | 値 | 備考 |
|-----|-----|------|
| counseling_detail 出力率 | **0%**（36/36 turns response_missing） | 最大リスク |
| end_guard redirect 補完 | 要再計測（script） | Pre-P0 で fail-loud 化 |
| fast-path 比率 | 要 `measure_pipeline_baseline.py` | triage スキップ集計 |
| LINE reply_fallback_push | 9 件 / 期間 | token 失効 |
| 最遅 POST | 49.4s（`頭痛い`） | rule_based + explanation 直列 |
| session_admin handoff 失敗 | T9/T21 等 | Pre-P0 + 1a 対象 |

再計測: `python scripts/measure_pipeline_baseline.py --log-dir log/analysis/downloaded-logs-20260626-20260627-20260627-162735`

IntentRouter shadow/dispatch: `python scripts/measure_intent_router_shadow.py --json`

dev カナリア（PowerShell）: `. .\scripts\dev_v2_flags.ps1 -Sid "line:YOUR_USER_ID"`（shadow のみ）  
本線 dispatch: `-Dispatch` / Stage B LLM: `-Llm`  
契約テスト: `.\scripts\verify_chat_pipeline_v2.ps1`  
Cloud Run env 例: [`scripts/cloudrun_v2_env.example`](../scripts/cloudrun_v2_env.example)

---

## LINE_IMPROVEMENT 統合

[`LINE_IMPROVEMENT_PLAN_2026-06-27.md`](../planning/LINE_IMPROVEMENT_PLAN_2026-06-27.md) の P0-2〜6 + P1-3,6,7 は **v2 Pre-P0 に統合**。**別 MR 禁止**。

---

## 関連ドキュメント

- [CHAT_ROUTE_EXPECTATIONS.md](CHAT_ROUTE_EXPECTATIONS.md) — 決定権マトリクス・期待 route
- [ROUTE_SPEC.md](ROUTE_SPEC.md) — HTTP API 仕様
- [ARCHITECTURE_MULTI_AGENT.md](ARCHITECTURE_MULTI_AGENT.md) — 現行 Agent 構成
- [schemas/dialogue_context_v1.json](../schemas/dialogue_context_v1.json) — DialogueContext schema
- [tests/fixtures/route_spec_scenarios.yaml](../../tests/fixtures/route_spec_scenarios.yaml) — 30+ シナリオ

---

## スケジュール（確定）

- Pre-P0: **3–5 営業日**
- Wave 0: **3–4 週**
- 全体: 工数 **13–18 週**、カレンダー **約 4–5 ヶ月**
- Wave 1a 完了時 **1b ゲートレビュー**必須
