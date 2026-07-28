# 会話パイプラインとエージェント構成

## Chat Pipeline v2（本番デフォルト ON）

- **フラグ**: v2 パイプライン・IntentRouter 主経路・レガシー fallback 抑制 — 環境変数未設定で ON（pytest 時のみ OFF）
- **入口**: `src/handlers/chat/chat_post_pipeline.py` → triage → IntentRouter / unified routing → dispatcher → 各 handler
- **IntentRouter**: `src/dialogue/routing/intent_router_llm.py` — LLM 構造化出力 + legacy triage ヒント
- **Unified Routing**: `src/dialogue/routing/unified_router.py` — Layer1 決定論 → Layer2 legacy/gate/LLM → Layer3 follow-up LLM
- **ゲート**: `src/dialogue/routing/gate.py` — 緊急・カウンセリング・店舗等の決定論ルート

## エージェント一覧（Concierge 参照 SSOT）

| エージェント | 役割 |
|-------------|------|
| TriageAgent | 入力分類・振り分け |
| PhysicalOrchestrator | 症状解析・ルールベース市販薬推奨 |
| ConciergeAgent | 挨拶・技術/更新 FAQ・アプリ説明 |
| AskAgent | 推奨後の医薬品 Q&A |
| StoreInquiryAgent | 店舗・遺失物案内 |
| CounselingManager | 心理カウンセリング |
| EmergencyRouter | 緊急受診案内 |
| ExplanationAgent | 推奨理由の説明 |

## Q: Chat Pipeline v2 を採用している理由

<!-- rag-keywords: Chat Pipeline v2 採用 理由 IntentRouter orchestrator なぜ 統一パイプライン -->

**回答要点**

- **What**: triage → IntentRouter / unified routing → dispatcher → handler の統一パイプライン（`chat_post_pipeline.py`）
- **Why**: IntentRouter + 決定論ゲート + エージェント orchestrator を一経路に集約し、レガシー分岐・二重 triage を縮小
- **Trade-off**: ルーティング誤りリスクは execution_lock・gate・guard で緩和。移行期は shadow 観測を併用
- **詳細設計**: `docs/dev/CHAT_PIPELINE_V2.md`

## Q: チャット POST の処理順序はどうなっているか

<!-- rag-keywords: chat_post_pipeline 処理順序 triage IntentRouter dispatcher orchestrator 入口 -->

**回答要点**

- **What**: `run_chat_post_pipeline` が 1 HTTP POST = 1 パイプライン実行を保証（再帰 dispatch 禁止）
- **流れ**: メッセージ解析 → LLM 予算チェック → triage → routing context 同期 → SessionOps 早期 → medicine context 早期 → IntentRouter dispatch → confidence gate → ChatOrchestrator fallback
- **dispatch 成功時**: `_router_dispatch_handled_turn` が立ち、レガシー fallback trim が二重実行を抑制
- **dispatch 未解決時**: clarification / Unknown / handler None は orchestrator へフォールバック許可
- **終端**: `finalize_pipeline_response`（fail loud）で無応答を `system_error` カード化

## Q: IntentRouter と Unified Routing の役割

<!-- rag-keywords: IntentRouter Unified Routing layer1 layer2 layer3 execution_lock gate LLM -->

**回答要点**

- **Layer1（決定論）**: 副作用 QA / medicine_qa / メタ topic break / changelog 継続を `execution_lock=True` で即決
- **Layer2（legacy + gate + LLM）**: `resolve_legacy_route` → gate 高信頼 → triage マップ → structured LLM。`pick_best_route_decision` で confidence 最大を採用
- **Layer3（follow-up）**: 短い曖昧フォローアップ（「詳しく」「もっと」等）を rule または LLM で prior 継続 / topic break 判定
- **execution_lock**: Router が返した `sub_route` を Concierge regex や dispatcher ゲートで上書きしない（2026-07 unified routing）
- **観測**: `dialogue_route_dispatch` / `dialogue_route_execution` ログ、`dialogue_state.routing`

## Q: 市販薬推奨はなぜルールベースか

<!-- rag-keywords: ルールベース 市販薬 推奨 PhysicalOrchestrator CSV スコア LLM 選ばない -->

**回答要点**

- **What**: `src/core/rule_based_recommendation.py` + `data/` CSV によるスコアリング
- **Why**: LLM による薬名 hallucination 防止、説明可能性・薬事的妥当性の確保
- **スコア要素**: 症状適合・年齢制限・相互作用・競技ドーピング配慮等
- **LLM の役割**: triage・説明文・Concierge — **薬名の最終選定は LLM ではない**

## Q: Concierge の技術質問応答の仕組み

<!-- rag-keywords: Concierge 技術 FAQ architecture RAG Local RAG Bedrock KB 深掘り -->

**回答要点**

- **intent**: `architecture`（仕組み・インフラ・API/SSE・マルチエージェント）
- **参照**: `docs/concierge/technical/*.md` + `concierge_knowledge.ja.json` + Local RAG（GCP/AWS 共通）。AWS ステージングは Bedrock KB 試験可
- **architecture 深掘り**: technical + ops SSOT を常時注入（運用事実の推測回答を抑制）
- **更新履歴**: `doc_changelog` — `CHANGELOG.md` ダイジェスト（`static/changelog-digest.json`）
- **深掘りキーワード**: 「詳しく」「デプロイ」「クロスクラウド」等で拡張参照＋長文回答モード

## Q: SSE（Server-Sent Events）の仕組み

<!-- rag-keywords: SSE Server-Sent Events ストリーミング done bot_message qa_delta 副作用 -->

**回答要点**

- **What**: 一方向サーバー→クライアント配信で処理ステータス（マスコットアニメーション）を段階表示
- **実装**: `src/services/sse_emit.py`、`src/handlers/chat_stream.py`
- **`done` イベント**: `bot_message` を含む。クライアントは `renderDonePayloadImmediately` で即描画
- **副作用 Q&A**: `medicine_side_effect_qa` は `qa_delta` 非対応のため **`done` 必須**。DB 保存後 in-memory `messages` を同期し、空時は DB フォールバック（`_messages_for_sse_done`）
- **製品画像**: SSE/JSON 両経路で `product_images_html` を付与。未準備時は「まだ準備できていません」+ 成分 1 文
- **推奨フロー**: Sage UI は最終 `diagnosis` 一括描画のため途中 SSE（`cards` / `reco_detail`）をスキップ可能

## Q: 多言語対応の概要

<!-- rag-keywords: 多言語 翻訳 DeepL Amazon Translate UI 言語 -->

**回答要点**

- UI 言語切替 + 非日本語入力時の応答翻訳
- GCP 本番: DeepL / AWS ステージング: Amazon Translate（各クラウドのネイティブサービス）
- TTS: GCP = Google Cloud Text-to-Speech、AWS = Amazon Polly、ローカル = Web Speech

### 例外・境界（ルーティング）

<!-- rag-keywords: 境界 Medicine QA Concierge follow-up topic break 副作用 比較 -->

**Medicine QA vs Concierge**

| ユーザー意図 | 経路 | 備考 |
|-------------|------|------|
| 症状・市販薬候補 | Physical / `rule_based_recommend` | ルールベース推奨 |
| 医薬品比較・説明・選び方（副作用が主題でない） | Physical / `medicine_qa` | LLM + ブランド解決 CSV。症状 reco に入れない |
| 副作用・眠気・「〜て平気？」 | Physical / `medicine_side_effect_qa` | CSV → KB 補完。症状 reco に入れない |
| 推奨後の「この薬について」 | Physical / `medicine_followup_qa` | 推奨履歴が前提 |
| インフラ・規約・アプリ概要 | Concierge / `architecture` 等 | technical SSOT + RAG |
| 「ロキソニンとイブの違い」 | `medicine_qa`（Concierge ではない） | `is_strict_medicine_side_effect_question` で副作用誤判定を防止 |
| 「AWS と GCP の違い」（メタ文脈） | Concierge / `architecture` | layer1 topic break が medicine_qa より優先 |

**follow-up（同一話題継続）**

- 短い曖昧発話（24 文字以下等）→ Layer3 follow-up LLM または rule fallback
- 同一 meta ファミリー（changelog 深掘り等）→ sticky 継続（`doc_changelog` 固定を禁止しないが prior 尊重）
- 「もっと詳しく」等ファミリー未定 → prior intent 継承（誤って changelog にピンしない）
- architecture follow-up KPI: greeting 禁止、技術語彙 1 つ以上または前ターン topic 明示参照

**topic break（話題転換）**

- `is_explicit_new_meta_topic` + `suggest_meta_intent_family` で異ファミリー検出（例: changelog → AWS/GCP 構成）
- layer1 でメタ topic break を `medicine_qa`（「違い」比較誤爆）より先に判定
- **`router_dispatch` は sticky follow-up より優先** — IntentRouter 明示決定が regex 継続を上書き

### 例外処理（ルーティング誤り・低信頼）

<!-- rag-keywords: ルーティング 誤り 低信頼 clarification guard fallback shadow mismatch -->

**IntentRouter が誤った場合**

- **dispatch 成功**: 決定 route の handler が実行。execution_lock 付き決定は実行層上書きを抑制
- **handler が None / 未対応 sub_route**: ChatOrchestrator へフォールバック（`_legacy_fallback_allow_reason`: `handler_fallback`）
- **shadow 観測**: triage 期待 route と Router 決定の mismatch を `classify_shadow_mismatch` で regression / gate_improvement / exempt に分類
- **gate 改善**: triage=Other だが gate が Physical/Store を選ぶケースは意図的改善として exempt 扱い可

**低 confidence**

- `apply_post_route_guards`: confidence が閾値未満 → `sub_route=clarification`（gate 即決定は除外）
- clarification は dispatch スキップ → orchestrator / confidence gate へ
- `check_triage_confidence`: 段階的 clarify メッセージ。ループ超過時は Sage 障害カード相当へエスケープ

**Unknown / 判断不能**

- `primary_route=Unknown` → dispatch スキップ、legacy orchestrator 経路を許可
- LLM 利用不可（OPENAI 未設定等）→ `llm_unavailable` Sage 障害カード。LLM 依存 reply をブロック

**パイプライン無応答**

- `finalize_pipeline_response` → `system_error` カード（fail loud）。処理バブル残留を防止

**発熱コンテキスト特例**

- 発熱中の Store ルート → guard が `Physical/fever_flow` へ上書き
- fever + triage Other → Physical への gate 改善は shadow exempt
