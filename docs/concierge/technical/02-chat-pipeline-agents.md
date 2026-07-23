# 会話パイプラインとエージェント構成

## Chat Pipeline v2（本番デフォルト ON）

- **フラグ**: `CHAT_PIPELINE_V2` / `INTENT_ROUTER_PRIMARY` / `LEGACY_FALLBACK_TRIM` — env 未設定で ON（pytest 時のみ OFF）
- **入口**: `src/handlers/chat/chat_post_pipeline.py` → triage → orchestrator → 各 handler
- **IntentRouter**: `src/dialogue/routing/intent_router_llm.py` — LLM 構造化出力 + legacy triage ヒント
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

## 市販薬推奨（ルールベース）

- **コア**: `src/core/rule_based_recommendation.py` + `data/` CSV
- **スコア**: 症状適合・年齢制限・相互作用・競技ドーピング（`RECO_SPORTS_DOPING_FILTER`）等
- **LLM の役割**: トリアージ・説明文生成・Concierge — **薬名の最終選定は LLM ではない**

## Concierge の技術質問応答

- **intent**: `architecture`（仕組み・インフラ・API/SSE・マルチエージェント）
- **参照**: `docs/concierge/technical/*.md` + `concierge_knowledge.ja.json` +（AWS 時）Bedrock KB retrieve
- **更新履歴**: `doc_changelog` — `CHANGELOG.md` ダイジェスト（`static/changelog-digest.json`）
- **深掘り**: 「詳しく」「デプロイ」「クロスクラウド」等で拡張参照＋長文回答モード

## SSE（Server-Sent Events）

- ストリーミング応答で処理ステータス（マスコットアニメーション）を段階表示
- 実装: `src/services/sse_emit.py` 等 — 一方向サーバー→クライアント配信

## 多言語

- UI 言語切替 + 非日本語入力時の応答翻訳
- GCP: DeepL / AWS: Amazon Translate（`TRANSLATION_PROVIDER`）
