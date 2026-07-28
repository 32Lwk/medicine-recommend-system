# Chat Pipeline v2 と機能フラグ

> ユーザー向け Concierge 回答では **環境変数名を出さない**。「本番では v2 パイプラインが既定で有効」等と述べる。

## 本番デフォルト ON（2026-07 以降）

| フラグ | 意味 |
|--------|------|
| `CHAT_PIPELINE_V2` | v2 POST パイプライン |
| `CHAT_PIPELINE_V2_INTENT_ROUTER` | IntentRouter 全体 |
| `CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY` | IntentRouter を主経路（legacy triage より LLM/gate 優先） |
| `CHAT_PIPELINE_V2_INTENT_ROUTER_DISPATCH` | shadow ではなく dispatcher 本線 dispatch |
| `CHAT_PIPELINE_V2_INTENT_ROUTER_LLM` | structured LLM ルーティング（OFF 時 gate/triage のみ） |
| `CHAT_PIPELINE_V2_LEGACY_FALLBACK_TRIM` | dispatch 成功後の二重 legacy 実行を抑制 |
| `CHAT_PIPELINE_V2_DENYLIST` | 一致 sid を v2 から除外（カナリアロールバック） |

env 未設定 = ON（pytest 実行中のみ OFF）。明示 `false` でロールバック。

## Unified Routing 関連（v2 + IntentRouter ON 時 既定 ON）

| フラグ | 意味 |
|--------|------|
| `ROUTING_UNIFIED_PIPELINE` | Layer1–3 unified routing + `execution_lock` |
| `ROUTING_MEDICINE_SIDE_EFFECT_QA` | 副作用 QA 専用 early route |
| `ROUTING_MEDICINE_SIDE_EFFECT_KB` | CSV 未ヒット時 KB 補完 |
| `ROUTING_FOLLOWUP_LLM` | 曖昧 follow-up の LLM 判定 |
| `PERF_META_SAFETY_SHORTPATH` | meta 経路 safety_gate 短縮 |

## 推奨品質フラグ（RECO_*）

| フラグ | 内容 |
|--------|------|
| `RECO_AGE_POLICY_V2` | 年齢未入力時の推奨ポリシー |
| `RECO_COLD_NLU_V2` | 風邪 NLU・症状チップ |
| `RECO_SPORTS_DOPING_FILTER` | 競技・ドーピング配慮 |

本番・dev とも env 未設定 = ON。

## AWS ステージング専用（GCP 本番に注入しない）

`config/aws_features.py` 参照:

- 翻訳: Amazon Translate（AWS）/ DeepL（GCP 本番既定）
- TTS: Amazon Polly（AWS）/ Google Cloud Text-to-Speech（GCP 本番・dev 既定）/ Web Speech（ローカル開発既定）
- Concierge RAG: Bedrock KB（ingestion は Support 待ちの場合あり）
- 画像 CDN: `images.yutok.dev`（GCP も cloudbuild で同 URL 可）

## Q: 本番で Chat Pipeline v2 は有効か

<!-- rag-keywords: Chat Pipeline v2 本番 デフォルト ON 有効 ロールバック -->

**回答要点**

- **What**: Web / LINE 共通の v2 POST パイプラインが本番・dev とも **環境変数未設定で ON**
- **Why**: IntentRouter + unified routing によるルーティング精度向上とレガシー分岐縮小
- **ロールバック**: 運用チームが v2 または特定 sid を denylist で除外可能（pytest 中は自動 OFF）
- **ユーザー向け**: 「現在の本番チャットは v2 パイプラインが既定で動作しています」と説明（フラグ名は出さない）

## Q: IntentRouter の shadow と dispatch の違い

<!-- rag-keywords: IntentRouter shadow dispatch PRIMARY LLM gate triage 観測 -->

**回答要点**

- **shadow のみ**: Router 決定を `dialogue_state.routing` / `_intent_router_shadow` に記録するが、ChatOrchestrator が従来 dispatch
- **dispatch ON**: `try_agent_dispatch` が Router 決定に基づき handler へ直接委譲（Physical / Concierge / Store 等）
- **PRIMARY ON**: gate/LLM 決定が legacy triage より優先（confidence 比較で最良を採用）
- **LLM OFF**: gate + triage マップのみ（structured JSON ルーティング無効）
- **観測**: `scripts/measure_intent_router_shadow.py`、`dialogue_route_dispatch` ログ

## Q: LEGACY_FALLBACK_TRIM は何をするか

<!-- rag-keywords: LEGACY_FALLBACK_TRIM 二重 triage orchestrator fallback dispatch 成功 -->

**回答要点**

- **What**: dispatch が `_router_dispatch_handled_turn` を立てた後、orchestrator / category 分岐等の legacy 再実行をスキップ
- **Why**: v2 + PRIMARY 有効時の二重 handler 実行・競合応答を防止
- **例外（trim しない）**: Unknown route、clarification、handler None（未対応 sub_route）、Router 決定なし
- **観測**: `legacy_fallback_trimmed` / `legacy_fallback_allowed` ログ（reason 付き）

## Q: Unified Routing（execution_lock）の意味

<!-- rag-keywords: ROUTING_UNIFIED_PIPELINE execution_lock unified router layer1 topic break -->

**回答要点**

- **What**: `unified_router.py` が Layer1 決定論 → Layer2 gate/LLM → Layer3 follow-up を単一 `RoutingDecision` に集約
- **execution_lock**: Router が正しい `sub_route` を返した後、Concierge regex や dispatcher ゲートで上書きしない
- **対象例**: `medicine_side_effect_qa`、`medicine_qa`、メタ topic break、changelog 継続
- **OFF 時**: 従来 `resolve_legacy_route` のみ（execution_lock なし）

## Q: 推奨品質フラグ（RECO_*）の概要

<!-- rag-keywords: RECO_AGE_POLICY RECO_COLD_NLU RECO_SPORTS_DOPING 推奨 品質 フラグ -->

**回答要点**

- **What**: 市販薬推奨の NLU・年齢ポリシー・ドーピング配慮を段階的に強化する機能群
- **本番**: env 未設定 = すべて ON
- **ユーザー向け**: 「推奨エンジンは年齢・風邪症状・競技配慮などのポリシーを組み込んでいます」（個別フラグ名は出さない）

## Q: 障害時のユーザー体験（LLM 不可・無応答）

<!-- rag-keywords: 障害 llm_unavailable system_error OPENAI 未設定 fail loud clarification -->

**回答要点**

- **OPENAI 未設定 / LLM 利用不可**: Sage 障害カード（`llm_unavailable`）。LLM 依存 reply をブロック
- **低信頼 clarification ループ超過**: 段階的 clarify の上限到達後、障害カード相当へエスケープ
- **パイプライン無応答**: `finalize_pipeline_response` が `system_error` カードを返す（fail loud）
- **SSE 副作用 Q&A**: `done.bot_message` 必須。DB フォールバックで処理バブル残留を防止

### 例外・境界（フラグとルーティングの相互作用）

<!-- rag-keywords: フラグ 境界 dispatch OFF unified OFF follow-up LLM 副作用 QA -->

| 状態 | 挙動 |
|------|------|
| v2 OFF | 従来 SessionAgent + ChatOrchestrator。IntentRouter 無効 |
| Router OFF | triage + orchestrator のみ。shadow 記録なし |
| dispatch OFF | shadow 記録のみ。orchestrator が従来 dispatch |
| PRIMARY OFF | legacy triage と Router 候補の confidence 最大（従来互換） |
| LLM OFF | gate + triage マップ。曖昧 follow-up は rule fallback のみ |
| unified OFF | execution_lock なし。legacy_router + gate のみ |
| follow-up LLM OFF | Layer3 は `_rule_based_follow_up` のみ |
| 副作用 QA OFF | `medicine_side_effect_qa` early route 無効。一般 Physical へ |

**Medicine QA vs Concierge（フラグ観点）**

- 副作用 QA / medicine_qa は unified ON 時 Layer1 で execution_lock 付き即決
- QA gate（`resolve_medicine_qa_route`）が CONCIERGE を返した場合、Physical dispatch 内で Concierge へ切替可
- meta safety shortpath ON 時、Concierge meta 経路の safety_gate を短縮（latency 改善）

**follow-up / topic break（フラグ観点）**

- `ROUTING_FOLLOWUP_LLM` ON: 曖昧短発話を LLM 再判定。OFF 時は rule のみ（LLM 不可時も rule fallback）
- topic break は Layer1 が unified ON なら execution_lock。OFF でも gate が高信頼なら PRIMARY で採用可

### 例外処理（低信頼・誤ルーティング・フォールバック）

<!-- rag-keywords: 低信頼 clarification guard triage confidence threshold handler_fallback -->

**低 confidence 時**

- Router/guard が `sub_route=clarification` を設定 → dispatch スキップ
- `check_triage_confidence` が段階的確認メッセージを返す（progressive clarification ON 時は tier 昇格）
- gate 即決定（confidence ≥ 閾値、`resolved_by=gate`）は clarification に落とさない

**IntentRouter 誤判定時**

- dispatch handler が None → orchestrator fallback（TRIM OFF または `handler_fallback` reason）
- shadow mismatch が regression → 観測ログ。gate_improvement は意図的改善として扱う
- correction 入力: 直前 bot を無効化せず新 route で上書き応答（1 POST = 1 実行）

**denylist / カナリア**

- sid が v2 denylist 一致 → 当該セッションのみ v2 OFF（本番切り戻し用）
- PRIMARY denylist で sid 単位の PRIMARY OFF も可能
