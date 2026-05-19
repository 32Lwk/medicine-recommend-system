# 開発履歴・更新日誌

**最終更新日: 2026年5月19日**（管理画面レスポンシブ・ヘッダー狭幅対応）

本ドキュメントは、チャット型医薬品相談ツールの開発・更新の記録です。プロジェクトの概要・セットアップ・使い方は [README.md](README.md) を参照してください。アーキテクチャ正本は [docs/ARCHITECTURE_MULTI_AGENT.md](docs/ARCHITECTURE_MULTI_AGENT.md)。

---

## 2026年5月19日（続）— 管理画面レスポンシブ・ヘッダー狭幅対応

### 概要

- **ヘッダー狭幅（≤1100px）**: システム操作ボタン（AI管理・セッション管理等）と AI 状態バッジをアイコンのみ表示。`aria-label` / `title` で状態を伝達。
- **タブレット幅の再定義**: JS の `isTablet()` を 481–1024px、`isDesktop()` を 1025px 以上に変更。769–1024px では中央チャット列を非表示にし左（セッション）＋右（キュー・AI）の 2 カラムに。
- **グリッド overflow 修正**: `minmax(0, …)` と `min-width: 0` で 3 カラム時の横はみ出しを防止。左右ペインの一覧は flex で残り高さをスクロール領域に。
- **空状態アイコン**: Font Awesome を `fa-regular` から `fa-solid` に統一（inbox / users / file-lines）。
- **スクロールバー**: ヘッダー操作行に `app-scrollbar` を付与（プロジェクト共通の緑細スクロールバー）。

### `static/css/admin_chat.css`

- **`.app-container` / `main`**: `max-width: 100%`・`min-width: 0` を追加し親からのはみ出しを抑制。
- **ヘッダー**: `.brand-section` に `min-width: 0`。`.header-system-controls` を `flex-wrap: nowrap` + 横スクロール（`overflow-x: auto`）。ボタンに `flex-shrink: 0`。
- **`@media (max-width: 1100px)`**: `.header-control-btn > span` と `#ai-status-text` を非表示。パディング・ギャップを縮小。
- **グリッド**: `grid-template-columns: minmax(0, 320px) 4px minmax(0, 1fr) 4px minmax(0, 320px)` に変更。
- **`#left-panel` / `#right-panel`**: `min-width: 0`・`min-height: 0`。`#session-list`・`#manual-reply-queue` を flex 子として `max-height: none` で可変高スクロール。
- **`#right-panel`**: `.ai-management-body` クラスでアコーディオン内余白を整理。`#ai-status-info` の下マージンを CSS 側に移動。
- **`@media (min-width: 769px) and (max-width: 1024px)`**: 中央パネル・左リサイザー・中央リサイザーを非表示、2 カラムグリッド。
- **モバイル（≤768px）**: 右ペイン `.info-section` の flex 化、セッション一覧・手動返信キューの固定 `max-height: 300px` を廃止。

### `static/js/admin_chat.js`

- **`refreshAIStatus()`**: バッジ更新時に `aria-label`・`title` を ON/OFF 文言で同期。アイコンに `aria-hidden="true"`。
- **`isTablet()` / `isDesktop()`**: ブレークポイントを 768px から 1024px に拡張。
- **`toggleMobileElements()`**: タブレット幅では中央パネルを `display: none`、デスクトップのみ flex 表示。
- **空状態**: `renderQueue`・`loadUserAttributes`・`renderSessionList`・`refreshSessionManagement` のアイコンを `fa-solid` に変更。

### `templates/admin_chat.html`

- **ヘッダー**: `.header-system-controls` に `app-scrollbar` を追加。初期 AI バッジに `aria-label` / `title`。
- **右ペイン AI 管理**: インライン `style` を `.ai-management-body` に置換。手動返信キュー空状態のアイコンを `fa-solid` に。

---

## 2026年5月19日 — セッション増殖対策・管理画面整理

### 概要

- **遅延 persist**: `GET /api/sessions` では DB 行を作成しない。初回メッセージ・属性保存・restore 等の意味あるイベントでのみ `ensure_session_persisted`。
- **アクティビティ維持**: `PATCH /api/sessions/activity`（DB 行がある場合のみ `last_activity` 更新）。フロントの 2 分ポーリングを GET から PATCH に変更。
- **クリーンアップ**: 起動時に空セッション一括 purge。30 分経過の空セッションを定期削除。手動返信キュー・`crisis_detected` は除外。
- **管理 API 認証**: `/api/main_sessions`・`/api/main_manual_reply_queue`・`/api/main_ai_control`・`/api/admin/sessions` に管理者認証を必須化。`get_sid` を除去。
- **管理 UI**: 左ペインはデフォルトで会話ありのみ（`meaningful_only`）。空セッション表示トグル・空一括削除ボタン。401 時はトースト表示。
- **利用者 Cookie**: `sid` に 7 日 `max_age`。`localStorage` に sid フォールバック（共有端末では新規セッション推奨）。
- **セッション再利用**: 同一 IP+UA・30 分以内の既存会話ありセッションへ Cookie を再設定。

---

## 2026年5月17日 — ルーティング刷新・ConciergeAgent・ConfidenceGate・処理進捗 UI 拡充

### 概要

- **ルーティング一本化**: LLM トリアージを主軸に、キーワード誤爆（「教えて」等）を抑制。`chat_post_pipeline` からオーケストレーター前の Concierge 先行呼び出しを削除し、`Other` は `ChatOrchestrator` → Concierge → 店舗の順で処理。
- **ConciergeAgent（新規）**: 挨拶・感謝・できること・アーキテクチャ説明・ドキュメント参照・軽い雑談・Physical ハンドオフ。ナレッジは `concierge_knowledge.ja.json`、ドキュメント要約は `concierge_docs.py`。
- **ConfidenceGate**: 閾値 `0.75`。低信頼時は `explain` モデルで再トリアージ → セッション 1 回まで確認質問 → 仍あいまいなら Concierge フォールバック。
- **トリアージ履歴**: 直近 5 件を `llm_triage` / `TriageAgent` に常時付与。キャッシュキーに履歴ダイジェストを含める。
- **初回薬探索**: コールドスタートで「教えて」「おすすめ」等は Ask ではなく Physical 推奨へ（`medicine_discovery_routing.py`）。
- **処理進捗 UI**: ユーザー向け非技術ラベル約 50 種（`processing_user_labels.py`）、エージェント名表示（`processing_agent_display.py`）、医薬品 Q&A / 推奨の `detail_code` 細分化。
- **フロント**: チャット全体のスクロール構造修正（`html/body` 固定・入力欄 sticky）、シーズン装飾レイヤー、Concierge ステータスカード、SSE 推奨 UI の改善。
- **店舗案内**: 施設・場所の文脈判定強化、Concierge への委譲条件、キーワードプローブ統合。
- **`LLM_AGENT_ENABLED`**: コード既定を `true` に変更。

### ルーティング・ConfidenceGate

- **`config/routing_config.py`（新規）**: `TRIAGE_CONFIDENCE_THRESHOLD`（既定 `0.75`）、`TRIAGE_HISTORY_MESSAGES`（既定 `5`）。
- **`src/services/confidence_gate.py`（新規）**: `apply_confidence_gate` — 無意味入力検出、再トリアージ、確認質問 1 回、Concierge フォールバック。
- **`src/services/triage_history.py`（新規）**: 直近メッセージ抽出・トリアージ用履歴ブロック整形。
- **`src/services/routing_context.py`（新規）**: `sync_routing_context` — 履歴ダイジェスト・ゲート状態をセッションに同期。
- **`src/services/input_routing.py`（新規）**: `is_greeting_only_message` 等、挨拶・入力正規化の一本化。
- **`src/services/routing_keyword_policy.py`（新規）**: トリアージ結果へのキーワード候補付与（監査・デバッグ用）。
- **`src/services/routing_validator.py`（新規）**: 緊急・違法薬物・店舗のクリティカル路で `model_role=validator` 非同期監査（`log/routing_validator.jsonl`）。
- **`src/services/meta_triage.py`（新規）**: Other 向けメタ意図 LLM 分類（`model_role=concierge`）、LRU 風キャッシュ。
- **`chat_post_pipeline.py`**: トリアージ → ConfidenceGate → オーケストレーター → カテゴリルートの順序確定。Concierge 先行削除。
- **`chat_confidence_route.py`**: `apply_confidence_gate` への委譲ラッパに整理。
- **`llm_triage.py` / `triage_agent.py`**: 履歴付きプロンプト、キャッシュキーに履歴ダイジェスト、`triage_cache` 無効化フック。
- **`chat_session_route.py`**: 眠気/不眠の Emotional 上書きを `confidence < 0.75` または Physical|Ask + 睡眠キーワード時のみに限定。

### ConciergeAgent

- **`src/agents/concierge_agent.py`（新規）**: 意図解決・ペイロード生成・オフトピック管理・Physical ハンドオフ。
- **`src/handlers/chat/chat_concierge_route.py`（新規）**: `try_concierge_response` — 早期 Concierge 応答・DB 同期・重複抑止。
- **`src/services/concierge_orchestrator.py`（新規）**: `enrich_other_concierge_intent` — 完全一致（挨拶/感謝）→ メタ LLM の 2 段階。
- **`src/services/concierge_intent.py`（新規）**: 完全一致ゲート、医薬品相談キーワード除外、オフトピックリセット判定。
- **`src/services/concierge_keyword_probe.py`（新規）**: 雑談系キーワード候補プローブ。
- **`src/services/concierge_templates.py`（新規）**: 挨拶・感謝・リダイレクト・capabilities / architecture カード HTML。
- **`src/services/concierge_llm.py`（新規）**: 雑談向け短応答 LLM（ポリシースニペット付与）。
- **`src/content/concierge_knowledge.ja.json`（新規）**: アプリ概要・エージェント一覧・制限事項・ハンドオフ文言。
- **`src/content/concierge_knowledge.py` / `concierge_docs.py`（新規）**: ナレッジ読込・`docs/` 参照ドキュメント要約（プライバシー・利用規約等）。
- **`chat_orchestrator.py`**: `Other` で `_enrich_concierge_intent` → `_route_concierge` → 未処理時 `_route_store`。Ask コールドスタートを Physical 推奨へ昇格。
- **`chat_greeting_route.py`**: Concierge 委譲ラッパに変更（後方互換維持）。
- **`agents/protocols.py`**: Concierge 関連プロトコル拡張。

### 質問ルート・医薬品 Q&A・薬探索

- **`src/services/medicine_discovery_routing.py`（新規）**: 初回セッションの薬探索 vs 追質問 Q&A 切り分け。スポーツ・ドーピング文脈キーワード。
- **`chat_question_route.py`**: 大規模整理 — トリアージ `Ask`/`Physical` 優先、`_execute_medicine_qa_flow`、薬探索→推奨の分岐を `medicine_discovery_routing` に委譲。
- **`chat_medicine_qa_html.py`**: `run_medicine_question_qa` に Q&A 実行を集約。CLEAR QUESTION・属性更新後・トリアージ Ask 直行を統合。
- **`medicine_qa_html.py` / `chat_response_service.py`**: Q&A HTML 生成・応答整形の共通化強化。
- **`medicine_response_builder.py`**: 構造化 Q&A ストリーム、用途ヒント、Physical ハンドオフヒント、処理 `detail_code` 連携。
- **`explanation_generator.py` / `medicine_logic.py`**: 推奨・説明フローとの連携調整。

### 店舗案内・その他ルート

- **`store_inquiry_handler.py`**: 施設・場所の空間文脈（`has_facilities_spatial_context` 等）、Concierge 委譲（`should_defer_store_to_concierge`）、キーワードプローブ、在庫・遺失物・免税等の分類強化。
- **`chat_store_inquiry.py`**: ルーティングコンテキスト・ConfidenceGate 連携。
- **`chat_other_counseling_route.py` / `counseling_generator.py`**: カウンセリング生成・ルート整理。
- **`chat_ask_route.py`**: Ask ルート拡張。
- **`emergency_dispatch.py`**: RoutingValidator 非同期監査フック。

### 処理進捗 UI

- **`processing_user_labels.py`（新規）**: flow/step/detail_code ごとのユーザー向け日本語ラベル（約 50 種）。
- **`processing_agent_display.py`（新規）**: 担当エージェント名の日本語表示マッピング。
- **`processing_mark.py`（新規）**: ステップマーク用ユーティリティ。
- **`processing_flows.py`**: `concierge` / `medicine_qa` / `confidence_check` 等フロー追加、閾値表示 0.75 に更新。
- **`processing_status.py`**: `detail_label`・エージェント名・ユーザーラベルの SSE/GET 反映。
- **`static/js/processing_status.js`**: 新ラベル・エージェント表示のフロント反映。

### LLM 設定

- **`config/llm_config.py`**: `model_role=concierge` / `validator` を追加（legacy: `gpt-4o-mini`、gpt5: `gpt-5.4-mini`）。
- **`config/llm_flags.py`**: `LLM_AGENT_ENABLED` 既定 `true`。
- **`.env.example`**: `TRIAGE_CONFIDENCE_THRESHOLD` / `TRIAGE_HISTORY_MESSAGES` を追記。

### フロントエンド

- **`templates/index.html`**: `html/body` を `overflow: hidden` + flex 化しチャット領域のみスクロール。シーズン装飾を `.season-decoration-layer`（sticky・入力欄上）に移動。ヘッダーブランド構造追加。
- **`static/css/main.css`**: レイアウト・Concierge カード・ステータスカード・モバイル対応の大幅更新。
- **`static/css/scrollbar.css`**: 新スクロール領域セレクタ追加。
- **`static/js/main.js`**: Concierge 応答表示、SSE 推奨 UI、メッセージ重複抑止、スクロール挙動修正。
- **`static/js/chat_sse.js`**: ストリームイベント連携の微調整。

### セッション・チャット基盤

- **`session_manager.py`**: Concierge 重複応答検出（`has_recent_concierge_reply_for_user` 等）、メッセージマージ改善。
- **`chat_stream.py` / `sse_events.py`**: ストリーム完了・イベント拡張。
- **`chat_recommendation_flow.py`**: 推奨フローと処理ステップ連携。
- **`text_formatter.py`**: 整形ユーティリティ拡張。
- **`user_attribute_registration.py`**: 属性登録後のルーティング連携。
- **`triage_analytics.py`**: 閾値を `routing_config` から取得。
- **`main.py`**: 起動・ルーティング関連の微調整。

### ドキュメント

- **`docs/ROUTING_ARCHITECTURE_AUDIT.md`（新規）**: A0 環境調査・パイプライン early return 図・confidence 0.75 統合一覧・E3 管理画面スモーク手順。
- **`docs/ARCHITECTURE_MULTI_AGENT.md`**: ConciergeAgent をエージェント一覧に追加。

### 回帰テスト（新規・更新）

| テスト | 内容 |
|--------|------|
| `test_confidence_gate.py` | 再トリアージ・確認質問・Concierge フォールバック |
| `test_meta_triage.py` | メタ意図 LLM 分類・キャッシュ |
| `test_routing_context.py` | RoutingContext 同期 |
| `test_routing_keyword_policy.py` | キーワード候補付与 |
| `test_routing_golden.py` | ゴールデンルーティング（`fixtures/routing_golden.jsonl`） |
| `test_concierge_agent.py` / `test_concierge_route.py` | Concierge 応答・ルート |
| `test_concierge_orchestrator.py` | Other 意図付与 |
| `test_concierge_intent.py` / `test_concierge_intent_extended.py` | 意図分類・除外 |
| `test_concierge_templates.py` / `test_concierge_card_snapshots.py` | テンプレート・カード HTML |
| `test_concierge_docs.py` / `test_concierge_knowledge_sync.py` | ドキュメント・ナレッジ同期 |
| `test_concierge_acceptance.py` | 受け入れシナリオ |
| `test_medicine_qa_flow.py` | 医薬品 Q&A フロー |
| `test_question_route_agent.py` | エージェント ON 時の質問ルート |
| `test_sports_medicine_routing.py` | スポーツ・ドーピング文脈 |
| `test_store_facilities_context.py` | 店舗施設・場所文脈 |
| `test_processing_user_labels.py` / `test_processing_agent_display.py` | 進捗ラベル・エージェント表示 |
| `test_safe_format_qa_html.py` | Q&A HTML エスケープ |
| `test_rule_based_import.py` | ルールベース import 安全性 |
| `test_chat_post_pipeline.py` / `test_chat_stream_api.py` | パイプライン・ストリーム API |
| `test_chat_greeting_route.py` | 挨拶 → Concierge 委譲 |
| `test_processing_status_detail.py` / `test_session_message_merge.py` / `test_user_message_dedup.py` | 進捗 detail・マージ・重複抑止 |
| `test_llm_phase1.py` | フラグ既定変更に追随 |

### 環境変数（`config/routing_config.py`・`.env.example`）

- `TRIAGE_CONFIDENCE_THRESHOLD`（既定 `0.75`）
- `TRIAGE_HISTORY_MESSAGES`（既定 `5`）

---

## 2026年5月16日（続2）— マルチエージェント本格化・Emergency 統合・トリアージキャッシュ・処理進捗 UI

### 概要

- **エージェントカナリア廃止**: `LLM_AGENT_ENABLED` をキルスイッチとし、ON 時は全セッションが `ChatOrchestrator` 経路（OFF は従来経路のみ）。`LLM_AGENT_CANARY_PERCENT` / `is_agent_session_eligible` を削除。
- **Emergency 統合ディスパッチ**: `store_incident` / `medical_self` / `crisis_language` の 3 サブタイプ分類、優先度タグ、手動キュー登録、SMTP 緊急メール通知、OTC ハードロック／ソフトバナー方針を一本化。
- **トリアージ LRU キャッシュ**: 正規化テキスト + 属性ダイジェストのプロセス内キャッシュ（`TRIAGE_CACHE_*`）。
- **SSE 2 段階推奨**: `cards` 先行 → `explanations` 追送 → `bot_followup`（`explanations_ready`）でクライアントが messages 再取得。
- **処理進捗 UI 刷新**: フロー別ステップ定義（`processing_flows.py`）、`detail_code` / エージェント名表示、処理中バブル内アドバイスプレビュー。
- **チャット重複実行防止**: セッション単位 inflight ロック（JSON POST / SSE ワーカー共有）と専用 `chat_worker` スレッドプール。
- **挨拶の早期応答**: LLM カウンセリングより前に `chat_greeting_route` で定型返信。
- **開発サーバー安定化**: Windows での uvicorn reload 既定 OFF、`reload_dirs` / `reload_excludes` で log・キャッシュ監視を除外。

### ドキュメント

- **`docs/ARCHITECTURE_MULTI_AGENT.md`（新規）**: 9 エージェント役割、Emergency シーケンス、SSE イベント一覧、トリアージキャッシュ、管理画面・緊急メールの正本。
- **`docs/ADMIN_PII_PLAYBOOK.md`（新規）**: 管理画面の PII 運用（自動マスクなし、一覧 120 / 詳細 800 文字抜粋、エスカレーション優先度）。
- **`README.md`**: CHANGELOG とアーキテクチャ正本ドキュメントの相互リンクを明記。
- **`docs/CLOUD_RUN_LLM_ENV.md`**: エージェント全量・トリアージキャッシュ・緊急メール変数を追記。

### 機能フラグ・環境変数（`config/llm_flags.py`・`.env.example`）

- **`LLM_AGENT_ENABLED`**: 既定 `true`（全セッションエージェント経路）。`LLM_AGENT_CANARY_PERCENT` を削除。
- **`LLM_CANARY_PERCENT`**: レガシー LLM 経路用のみ（既定 `0`）。
- **`TRIAGE_CACHE_MAX_ENTRIES` / `TRIAGE_CACHE_TTL_SEC`**: トリアージキャッシュ（既定 256 件 / 600 秒）。
- **`ADMIN_LIST_SNIPPET_MAX_CHARS` / `ADMIN_DETAIL_USER_MESSAGE_MAX_CHARS`**: 管理画面抜粋長（120 / 800）。
- **`EMERGENCY_EMAIL_ENABLED`**: 緊急検出時の SMTP 通知（既定 `true`）。

### Emergency フロー（`src/agents/emergency_classifier.py`・`src/handlers/chat/emergency_dispatch.py`）

- **`classify_emergency()`**: サブタイプと `priority_tag`（`critical_crisis` > `critical_medical` > `store_high` > `store_low`）を決定。
- **`dispatch_emergency()`**: 店舗インシデントカード or メディカル HTML（119 明示）、300 秒デデュープ、手動キュー `enqueue`。
- **`medical_emergency_templates.py`（新規）**: メディカル緊急・クライシス向け HTML テンプレート。`medical_emergency_otc_locked`（ハード）/ `store_incident_soft_banner`（ソフト）。
- **`emergency_notify.py` / `email_notifier.py`（新規）**: キュー登録時に `budget_guard.get_alert_email` 宛て通知。`smtp_not_configured` 等を `notification_status` に記録。
- **`chat_emergency_handler.py`**: ロジックを `emergency_dispatch` へ集約（重複分岐削減）。

### トリアージ・NLU・オーケストレーション

- **`src/services/triage_cache.py`（新規）**: canonical 正規化 + SHA256 キー、LRU・TTL、短文本・低信頼度の skip 行列、ヒット率メトリクス。
- **`src/handlers/chat/nlu_resolve.py`（新規）**: `resolve_nlu_for_recommendation` — エージェント ON 時は `NLUAgent`、OFF 時は `hybrid_nlu_extraction`。
- **`nlu_agent.py`**: 属性抽出の拡張・処理ステップ `detail_code=nlu` 連携。
- **`chat_orchestrator.py` / `orchestrator_route_result.py`（新規）**: ルート結果型の整理、Emergency / Physical / Ask 等の handoff 統合。
- **`chat_greeting_route.py`（新規）**: 純粋挨拶の早期定型応答・再送抑止。
- **`chat_confidence_route.py` / `chat_symptom_route.py` / `chat_other_counseling_route.py`**: `set_processing_flow` 連携・エージェント経路整理。

### SSE・推奨フロー・フロント

- **`sse_emit.py`**: `emit_explanations`・`emit_bot_followup`・ストリーム状態クリア（`clear_session_stream_state`）。`cards` ペイロード拡張を維持。
- **`chat_recommendation_flow.py` / `medicine_response_builder.py`**: カード先行 → `ExplanationAgent` 並列生成 → SSE `explanations` → `bot_followup`。
- **`chat_stream.py`**: `chat_worker.submit_chat_job`・`chat_inflight`・`persist_session_from_chat_state` 連携。
- **`static/js/main.js`**: `explanations` イベントでカード内推奨理由を逐次更新、`bot_followup` で messages 再取得、ストリーミング推奨 UI の統合維持。
- **`static/js/chat_sse.js`**: 不要コード整理。

### 処理進捗 UI（`processing_flows.py`・`processing_status.py`・`processing_status.js`）

- **フロー定義**: `greeting` / `physical` / `emergency` / `ask_qa` / `confidence_check` 等、ステップ順と weight。
- **`mark_processing_step`**: `detail_code`・`detail_label`・担当エージェント名（日本語）を SSE `status` / GET `/api/processing_status` に反映。
- **`append_advice_preview`**: 処理中バブル内へアドバイス断片のプレビュー表示。
- **各ルート**: トリアージ後に `set_processing_flow(flow_for_triage_category(...))` を設定。

### チャット基盤・セッション・DB

- **`chat_inflight.py`（新規）**: `try_begin_chat_job` / `end_chat_job`（TTL 120 秒）— 同一 sid の並行 POST を 409 相当で拒否。
- **`chat_worker.py`（新規）**: `ThreadPoolExecutor(max_workers=1)` — Starlette スレッドプール枯渇防止。
- **`session_manager.py`**: `persist_session_from_chat_state` — SSE 完了後の DB 永続化。
- **`database.py`**: 接続不可時のフォールバック・エラーハンドリング強化。
- **`main.py`**: `get_sid` / `new_session` を async 化。新規セッション時に SSE ストリーム状態をクリア。

### 管理画面

- **`admin_snippet.py`（新規）**: `truncate_user_text`（list / detail モード）。
- **`static/js/admin_chat.js` / `templates/admin_chat.html`**: `priority_tag` バッジ、緊急サブタイプ表示、抜粋長制限、通知ステータス表示。
- **`medicine_qa_html.py`（新規）**: 医薬品 Q&A 応答 HTML 生成の共通化。

### ルールベース・予算・その他

- **`rule_based_recommendation.py`**: DataFrame キャッシュ（`test_rule_based_cached_df`）。
- **`budget_guard.py`**: アラートメール取得の整理。
- **`app.py`**: `UVICORN_RELOAD` 明示時のみ reload。`reload_dirs` は `src` / `config` / `templates` / `static`、`log`・`__pycache__`・`.pytest_cache` を除外。

### 回帰テスト（新規・更新）

| テスト | 内容 |
|--------|------|
| `test_emergency_dispatch.py` | `dispatch_emergency` の店舗／メディカル分岐 |
| `test_emergency_flow_matrix.py` | サブタイプ・優先度・OTC ロック行列 |
| `test_emergency_notify.py` | 緊急メール通知の有効／無効・SMTP 未設定 |
| `test_triage_cache_matrix.py` / `test_triage_cache_ttl.py` | キャッシュ hit/skip/TTL |
| `test_chat_inflight.py` | 同一 sid 重複ジョブ拒否 |
| `test_chat_greeting_route.py` | 挨拶早期応答 |
| `test_nlu_resolve.py` | エージェント ON/OFF の NLU 解決 |
| `test_processing_flows.py` / `test_processing_status_detail.py` | フロー定義・detail 表示 |
| `test_chat_post_agent_rollout.py` / `test_llm_flags_agent.py` | カナリア廃止後のフラグ挙動 |
| `test_database_unavailable.py` | DB 接続不可時の挙動 |
| `test_chat_orchestrator.py` / `test_sse_emit.py` | オーケストレータ・SSE explanations |
| `test_session_message_merge.py` | セッションメッセージマージ |

---

## 2026年5月16日（続）— スクロールバー統一・SSE 推奨 UI・ステータスカード・診断名分離

### 概要

- スクロールバー定義を **`static/css/scrollbar.css`** に一元化し、メイン・管理・About・デバッグ画面から重複 `::-webkit-scrollbar` を削除。
- **SSE ストリーミング**の推奨表示を、簡易リストから **本番と同等の `recommendation-result` レイアウト**（アドバイス＋医薬品カード・スコア・注意書き）へ統合。
- **診断名検出**と **推奨結果オブジェクト**の `diagnosis` フィールド衝突を解消（`diagnosis_type` 分離・`isDiagnosisPayload` 判定）。
- **ステータスカード**（診断名通知・エラー UI）の二重スタイル・HTML エスケープ表示を修正。
- **遅延通知ボタン**を処理中バブル内スロットへ移設。属性・ユーザー情報モーダルのスクロール構造を改善。

### スクロールバー統一

- **`static/css/scrollbar.css`（新規）**: 緑・細（7px）・角丸の共通スタイル。Firefox `scrollbar-color` / WebKit `::-webkit-scrollbar*` を 4 セレクタグループで定義。`.app-scrollbar` クラスと既知 UI セレクタ（`.chat-messages`・モーダルフォーム・オンボーディング等）に適用。
- **`docs/SCROLLBAR_STYLE.md`（新規）**: デザイン仕様・読み込み方法・新規スクロール領域の追加手順・禁止事項。
- **`.cursor/rules/scrollbar.mdc`（新規）**: Cursor 向け必須ルール（新規スクロール領域は `app-scrollbar`、他 CSS に `::-webkit-scrollbar` を書かない）。
- **`static/css/main.css` / `admin_chat.css` / `about.css`**: 先頭で `@import url('scrollbar.css')`。各ファイル内の重複スクロールバー定義を削除。
- **`templates/debug_index.html`**: `scrollbar.css` を `<link>` で読み込み。メッセージ履歴に `app-scrollbar` を付与。
- **`static/js/admin_chat.js`**: 医薬品チャット JSON 詳細表示に `app-scrollbar` を付与。
- **管理画面モバイルキュー**: 非表示だった `mobile-queue-slider` のスクロールバーを共通スタイルに復帰。

### SSE ストリーミング UI（`static/js/main.js`・`sse_emit.py`）

- **`emit_cards`（`sse_emit.py`）**: 効能の 80 文字切り詰めを廃止。`explanation`・`display_score` / `relative_score` / `score`・`score_level`・`completeness_penalty`・`age_restriction`・`risk_warning`・`low_score_warning`・`medicine_type` を SSE `cards` ペイロードに追加。
- **フロント**: `streaming-advice` / `streaming-cards` の二重バブルを **`streaming-recommendation`** 1 本に統合。`ensureStreamingRecommendationResult` で本番同等の HTML 骨格（アドバイス枠・推奨医薬品枠）を構築。
- **`buildStreamingMedicineItemHtml`**: ランク・メーカー・最適度・推奨理由・外用薬補助注記・年齢制限・リスク警告・低スコア警告・効能を逐次描画。
- **`appendAdviceDelta` / `renderStreamingMedicineCards`**: 同一バブル内でアドバイス追記と医薬品一覧更新。プレースホルダ（「医薬品を選定しています…」）を CSS で表示。

### ステータスカード・メッセージ表示（`html_formatter.py`・`main.js`・`main.css`）

- **`format_status_card`**: ルート要素から `chat-response` クラスを除去（ステータスカード専用スタイルと推奨結果 `.chat-response` の衝突回避）。
- **`main.js`**: `isStatusCardHtml`・`wrapBotStatusCardHtml`・`looksLikeHtmlContent` を追加。履歴復元・新規メッセージでステータスカードを `message-content--status-card` でラップ。
- **`main.css`**: `.message.bot .message-content--status-card` と `.chat-status-card` の余白・背景を調整。旧メッセージ互換用 `.chat-status-card.chat-response` リセットを追加。

### 診断名検出・メッセージスキーマ

- **`chat_diagnosis_handler.py` / `chat_recommendation_flow.py`**: ボット応答の診断名種別を `diagnosis: None` + **`diagnosis_type`** に分離（フロントの `message.diagnosis` オブジェクト判定と衝突しないよう）。
- **`main.js`**: `isDiagnosisPayload()` — `diagnosis` がオブジェクトのときのみ推奨結果 UI を適用。
- **`config/dialect_dictionary.py`**: 感情ネガティブ語に「酷い」「くるしい」を追加。
- **診断ロジック**: 「花粉症が酷いです。」のように **疾患名＋重症度** の入力は `diagnosis_only` ではなくカウンセリング経路へ（`test_032_hay_fever_with_severity_kurai`）。

### 遅延通知 UI（処理中バブル内）

- **`templates/index.html`**: フォーム・モーダル直下の固定 `#slowRequestBtn` を削除。
- **`main.js` / `processing_status.js`**: `processing-slow-request-slot` を処理中バブル末尾に生成。8 秒経過でスロット表示・アイコン付きボタンを動的生成・`attachSlowRequestButtonToTypingIndicator` で typing 表示と同期。
- **`main.css`**: `.processing-slow-request-slot` のフェードイン、緑系ボタンスタイル（送信済みはグレーアウト）。

### モーダル・レイアウト

- **`#userInfoModal` / `#attributeModal`**: オーバーレイ中央配置、`modal-content` は `overflow: hidden` + flex、**`#userInfoForm` / `#attributeForm` のみ** `overflow-y: auto`（ヘッダー固定・角丸崩れ防止）。モバイル余白・ヘッダーサイズを調整。
- **`templates/index.html`**: モーダル inline `overflow-y` を削除し CSS に委譲。キャッシュバスター `?v=20260516-slow-in-bubble`。

### その他

- **`main.py`**: `merge_session_messages` を import（セッションメッセージマージ利用）。

### 回帰テスト（更新）

| テスト | 内容 |
|--------|------|
| `test_sse_emit.py` | `emit_cards` の拡張フィールド（`explanation`・`display_score` 等） |
| `test_html_formatter.py` | ステータスカードに `chat-response` が付かないこと |
| `test_diagnosis_detection.py` | 花粉症＋「酷い」→ カウンセリング経路（`test_032`） |

---

## 2026年5月16日 — GPT-5 完全移行 + 9エージェント + SSE + チャット基盤リファクタ

### 概要

- **`LLM_MODEL_PROFILE=gpt5`** を既定とし、トリアージ・NLU・説明・カウンセリングを **9 エージェント経路**に集約（`LLM_AGENT_ENABLED` + カナリア対象セッション）。
- **`chat_handler.py`** の巨大 POST 処理を **`chat_post_pipeline` ほか分割モジュール**へ移し、**`ChatOrchestrator`** がトリアージ後の Physical / Emotional / Ask / Other を一点集約。
- **`POST /api/chat/stream`** による **SSE ストリーミング**（`cards` → `advice_delta` → `done`、Last-Event-ID 再接続）。
- **統一エラー UI**・**開発用 7 パターンのエラー UI プレビュー**・セッション保存ログ改善・観測用トレース／日次 Markdown ログを追加。

### LLM 設定・機能フラグ（`config/`）

- **`llm_config.py`**: ロール別モデル名（`OPENAI_MODEL_TRIAGE` / `NLU` / `EXPLAIN` / `COUNSEL`）、`OPENAI_USE_RESPONSES_API`、本番/ステージング API キー分離。
- **`llm_canary.py`**: 新規 sid のみ gpt5 プロファイルへ段階切替（`effective_model_profile`）。
- **`app_config.py`**: `APP_ENV` に応じた開発ログ・Markdown ログの有効化。
- **`.env.example`**: 上記変数・開発用エラートリガー・`DEV_MARKDOWN_LOG_*` のテンプレートを追記。
- **`docs/CLOUD_RUN_LLM_ENV.md`**: Cloud Run 向け環境変数を gpt5 / エージェント / SSE 前提に更新。

### OpenAI 呼び出し（`src/core/llm_client.py`）

- **Responses API** と Chat Completions の単一ラッパを拡張（同期・非同期・ストリーミング）。
- **ストリーミングアドバイス**: `stream_advice` コールバック経由で `advice_delta` を SSE に投入。
- レイテンシ・トークン計測、`budget_guard` / `llm_metrics` 連携を維持。

### 9 エージェント（`src/agents/`）

| エージェント | 役割 |
|-------------|------|
| `triage_agent` | カテゴリ分類・handoff 解決 |
| `safety_gate` | LLM 前の決定的安全チェック（緊急・不適切・グレーゾーン判定） |
| `moderation_agent` | グレーゾーンの LLM モデレーション |
| `nlu_agent` | 症状・属性の構造化抽出 |
| `physical_orchestrator` | ルールベース推奨ツール呼び出し |
| `ask_agent` | 医薬品 Q&A |
| `counseling_manager` | 感情・メンタル系カウンセリング |
| `explanation_agent` | 推奨理由の並列説明生成 |
| `store_inquiry_agent` | 店舗・営業時間等の問い合わせ |

- **新規**: `safety_gate.py` / `moderation_agent.py` / `nlu_agent.py` / `store_inquiry_agent.py`
- **`protocols.py`**: `HandoffResult`・ツール ACL 型を拡張。
- **`explanation_agent.py`**: 推奨カード説明の並列生成に対応。

### チャット POST 分割・オーケストレーション（`src/handlers/`）

- **`chat_handler.py`**: POST 本体を **`run_chat_post_pipeline`** へ委譲（約 2,000 行削減）。
- **新規ルートモジュール**:
  - **`chat/chat_post_pipeline.py`**: POST 全ステップのオーケストレーション（`ChatPostContext`）。
  - **`chat/chat_post_init.py`**: 空メッセージ・入力パース。
  - **`chat/chat_preprocess_route.py`**: 前処理・トリアージ・SafetyGate・Moderation。
  - **`chat/chat_session_route.py`**: メッセージ追記・感情キーワード・チャット終了・管理画面同期。
  - **`chat/chat_llm_gate.py`**: 予算ブロック・LLM プロファイル解決。
  - **`chat/chat_inappropriate_route.py`**: 不適切リクエスト経路。
  - **`chat/chat_dev_triggers.py`**: 開発用エラー UI トリガー（7 パターン）。
- **`chat_orchestrator.py`（新規）**: `ChatOrchestrator` — トリアージ後の handoff を一点集約。`try_orchestrator_route` で既存ルートと接続。
- **`chat_pipeline.py`**: エージェント経路とレガシー経路の切替・重複 triage 回避。
- **`docs/AGENT_DEDUP_AUDIT.md`（新規）**: 1 POST あたり `llm_triage` / `run_triage_agent` は原則 1 回にする監査メモ。

### SSE ストリーミング

- **`main.py`**: **`POST /api/chat/stream`** — `text/event-stream`、`Last-Event-ID` ヘッダ対応。
- **`chat_stream.py`（新規）**: `handle_chat_post` をワーカースレッドで実行しつつイベント配信。
- **`sse_events.py`（新規）**: SSE イベント名・ペイロード型の定義。
- **`sse_emit.py`（新規）**: `StreamSink`・ContextVar・セッション単位リングバッファ（TTL 120s / 最大 512 件）。
- **`static/js/chat_sse.js`（新規）**: `ChatSSE.submitStream` — 再接続・`advice_delta` / `cards` / `done` ハンドラ。
- **`static/js/main.js`**: `CHAT_USE_SSE` 時はストリーム POST を優先。`streaming-advice` / `streaming-cards` DOM を逐次更新。

### 安全・危機検知

- **`src/core/crisis_detection.py`**: SafetyGate 連携・グレーゾーン表現の調整。
- **`chat_triage.py` / `llm_triage.py`**: エージェント経路・キャッシュ TTL・トリアージ呼び出し回数の最適化。

### セッション・DB・フィードバック

- **`session_manager.py`**: DB 未設定時の WARNING 抑制、`GET /api/sessions` ポーリング時の保存間引き、メッセージマージ改善。
- **`database.py`**: `resolve_database_url()`（`POSTGRES_*` からの組み立て）。
- **`feedback_store.py`（新規）**: `DATABASE_URL` 未設定時の開発用フィードバック（`log/feedback_dev.jsonl`）。
- **`main.py`**: **`POST /api/slow-request-notify`** — 遅延通知（ログ + 任意 SMTP）。`slow_request_notify.py`（新規）。

### 統一エラー UI・開発プレビュー

- **`html_formatter.py`**: `chat-status-card` 系（診断名通知・エスカレーション・システムエラー等）とフィードバックのカード内フッター化。
- **`static/css/main.css` / `static/js/main.js`**: `showErrorMessage` / `showWarningMessage`、ユーザー向け文言変換、成功時のエラーカード自動削除、「もう一度試す」再送。
- **開発用トリガー 7 件**: 下記「開発用エラー UI プレビュー」参照。`docs/DEV_ERROR_UI_PREVIEW.md`（新規）。

### 観測・開発ログ

- **`agent_trace.py`（新規）**: エージェント handoff / ステップの JSONL（`log/agent_trace.jsonl`）。
- **`daily_markdown_log.py`（新規）**: 開発環境の日次 Markdown（`log/log/yyyy-mm-dd-n.md`）、非同期書き込み。推薦スコアリング DEBUG は除外可能。

### 処理進捗・その他サービス

- **`processing_status.py`**: SSE 中の `advice_preview` 追記、ステップラベル調整。
- **`chat_response_service.py`**: ストリーム完了時のレスポンス整形。
- **`counseling_llm.py` / `counseling_processor.py`**: `llm_client` 経由・エージェント handoff 連携。

### フロントエンド

- **`templates/index.html`**: `chat_sse.js` 読込、`CHAT_USE_SSE` フラグ。
- **`static/js/processing_status.js`**: SSE 併用時の進捗表示調整。
- **`static/js/admin_chat.js` / `templates/admin_chat.html`**: 管理画面の微調整。

### 回帰テスト（新規・更新）

| テスト | 内容 |
|--------|------|
| `test_chat_orchestrator.py` | Orchestrator handoff・経路分岐 |
| `test_chat_post_pipeline.py` | POST パイプライン統合 |
| `test_chat_preprocess_route.py` | 前処理・SafetyGate |
| `test_chat_inappropriate_route.py` | 不適切リクエスト |
| `test_chat_triage_agent_path.py` | エージェント triage 経路 |
| `test_chat_stream_api.py` | SSE API 契約 |
| `test_sse_emit.py` | リングバッファ・再接続 |
| `test_safety_gate.py` / `test_moderation_agent.py` | 安全・モデレーション |
| `test_nlu_agent.py` / `test_store_inquiry_agent.py` | NLU・店舗 |
| `test_explanation_agent_parallel.py` | 説明の並列生成 |
| `test_agent_trace.py` / `test_daily_markdown_log.py` | 観測ログ |
| `test_llm_canary_profile.py` / `test_llm_stream.py` | カナリア・ストリーム |
| `test_triage_cache_ttl.py` / `test_triage_call_count.py` | triage 最適化 |
| `test_tool_acl.py` | ツール ACL |
| `test_chat_dev_triggers.py` | 開発用エラー UI |
| `test_html_formatter.py` | ステータスカード HTML |
| `test_session_manager_db_fallback.py` / `test_session_message_merge.py` | セッション |
| `test_slow_request_notify.py` / `test_feedback_dev_fallback.py` | 遅延通知・フィードバック |
| `test_chat_confidence_route.py` / `test_chat_store_inquiry.py` / `test_crisis_detection.py` | 既存経路の回帰 |
| `test_llm_phase1.py`（更新） | `llm_client` 拡張 |

### README

- [開発用エラー UI プレビュー（7パターン）](docs/DEV_ERROR_UI_PREVIEW.md) へのリンクを追加。

---

## 開発用エラー UI プレビュー（7パターン・すべて実装済み）

**`APP_ENV=development` のときのみ有効。** 本番ではトリガー語を送っても通常メッセージとして処理されます。  
詳細・環境変数・使い方: **[docs/DEV_ERROR_UI_PREVIEW.md](docs/DEV_ERROR_UI_PREVIEW.md)**

| # | トリガー（完全一致で送信） | 種類 | 表示 |
|---|---------------------------|------|------|
| 01 | `mrcdev00000000000001` | クライアント・エラー | 赤カード（`showErrorMessage`） |
| 02 | `mrcdev00000000000002` | クライアント・警告 | 赤枠・セキュリティ（`showWarningMessage`） |
| 03 | `mrcdev00000000000003` | HTTP 500 | 通信エラー系カード（fetch 失敗扱い） |
| 04 | `mrcdev00000000000004` | HTML・システム | 赤 `chat-status-card`（サーバー生成） |
| 05 | `mrcdev00000000000005` | HTML・注意 | 黄 `chat-status-card` + フィードバック |
| 06 | `mrcdev00000000000006` | HTML・通知 | 青（診断名検出風） |
| 07 | `mrcdev00000000000007` | HTML・重要 | 赤・critical（エスカレーション風） |

実装: `src/handlers/chat/chat_dev_triggers.py` / テスト: `tests/test_chat_dev_triggers.py`  
POST 入口: `chat_post_pipeline.run_chat_post_pipeline` で `try_dev_error_trigger` を評価。

---

**2026年5月15日の更新（LLM 段階移行・エージェント・処理進捗・管理画面）:**

- **LLM 設定・機能フラグ（`config/`）**
  - **`llm_config.py`**: 本番/ステージング API キー分離、`LLM_MODEL_PROFILE`（`legacy` / `gpt5`）、用途別モデル名、`OPENAI_USE_RESPONSES_API`、月額・セッション予算の既定値。
  - **`llm_flags.py`**: `LLM_AGENT_ENABLED`・`LLM_AGENT_CANARY_PERCENT`・`LLM_GPT_RECOMMEND_FALLBACK`（本番既定 OFF）・`LLM_CANARY_PERCENT` と、セッション ID ハッシュによるカナリア判定。
  - **`llm_canary.py` / `llm_runtime.py`**: 新規 sid のみ gpt5 プロファイルへ段階切替。
  - **`.env.example`**: 上記変数のテンプレートを追加。
- **OpenAI 呼び出しの統一（Phase 2）**
  - **`src/core/llm_client.py`（新規）**: Chat Completions / Responses API の単一ラッパ。同期・非同期、レイテンシ・トークン計測、予算チェック、`llm_metrics` / `budget_guard` 連携。
  - **`src/core/openai_client.py`** および **`llm_triage`・カウンセリング・NLU・説明生成** 等: `chat.completions` 直呼びを廃止し `llm_client` 経由に集約。
  - **`src/core/i18n_prompts.py`（新規）**: 多言語プロンプト断片の共通化。
- **予算・計測（Phase 0）**
  - **`src/services/budget_guard.py`（新規）**: 月額 `OPENAI_MONTHLY_BUDGET_JPY` の hard_stop、セッションコストアラート（SMTP 任意）、管理用文言の DB 保持。
  - **`src/services/llm_metrics.py`（新規）**: セッション単位の LLM 呼び出し回数・コスト・レイテンシ集計。
  - **`scripts/baseline_llm_metrics.py`（新規）**: P50/P95・セッションコストのベースライン記録用 CLI。
  - **`main.py`**: **`GET/POST /admin/llm_settings`** — 予算到達時メッセージ・アラートメールの設定 UI。
- **エージェント経路（Phase 3）**
  - **`src/agents/`（新規）**: `triage_agent`・`physical_orchestrator`・`ask_agent`・`explanation_agent`・`counseling_manager`、`protocols`（Handoff）、`tools/recommendation_tool`（ルールベース推奨のみをツール化。GPT による OTC 選定はしない）。
  - **`src/handlers/chat_pipeline.py`（新規）**: `LLM_AGENT_ENABLED` かつカナリア対象 sid のとき、トリアージ後の Emotional / Physical 等をエージェントへ委譲。
  - **`src/handlers/chat_handler.py`**: 巨大分岐を **`chat_*_route.py`** へ分割（`chat_category_route`・`chat_physical_route`・`chat_symptom_route`・`chat_emotional_route`・`chat_ask_route`・`chat_confidence_route`・`chat_recommendation_followup`・`chat_medicine_qa_html` 等）。オーケストレーション層として大幅スリム化。
  - **`src/services/counseling/counseling_llm.py`（新規）**: カウンセリング LLM 呼び出しの分離。
- **チャット処理進捗 UI**
  - **`src/services/processing_status.py`（新規）**: 14 ステップの加重進捗（インメモリ即時更新 + DB デバウンス書き込み）。日本語・英語・韓国語・中国語ラベル。
  - **`main.py`**: **`GET /api/processing-status`**（`sid` または管理者セッション指定）。
  - **`static/js/processing_status.js`（新規）**: ユーザー/管理チャットでのポーリングとバッジ表示。医療用語は翻訳せず日本語のまま表示。
  - **`templates/index.html` / `admin_chat.html`**: 進捗スクリプト読込。キャッシュバスター `?v=20260515-i18n`。
  - **各ハンドラ**: `mark_processing_step` をトリアージ・診断・緊急・店舗・推奨・翻訳などの節目で呼び出し。
- **管理画面認証・DB**
  - **`src/services/admin_auth.py`（新規）**: Cookie ベース管理認証（Basic 認証が使えないブラウザ向け）。`templates/admin_login.html` と **`main.py`** のログイン POST。
  - **`src/services/database.py`**: `global_state`（月次コスト・LLM 管理設定）、`update_processing_status_only` 等を拡張。
  - **`src/services/session_manager.py`**: 処理進捗・エージェント handoff メタデータの永続化対応。
- **回帰テスト・フィクスチャ**
  - **`tests/test_llm_phase0.py`–`test_llm_phase3.py`**: フラグ既定値・モデルプロファイル・`llm_client`・エージェント handoff・カナリア。
  - **`tests/test_golden_regression.py`**: **`tests/fixtures/golden/sample_cases.jsonl`**（40 件: Physical 16 / Emotional 10 / Ask 6 / Emergency 4 / Other 4）のスキーマ・オフライン triage 検証。
  - **`tests/test_safety_regression.py`**: **`tests/fixtures/safety/red_team.jsonl`**（50 件）— 緊急 handoff・推奨ツールがランキング以外を返さないこと。
  - **`tests/test_processing_status.py` / `test_processing_status_api.py`**: 進捗サービスと API 契約。
  - **`tests/test_chat_category_routes.py` / `test_chat_emotional_route.py` / `test_user_message_dedup.py`**: ルート分割後の振る舞い。
  - **`scripts/golden_regression_cli.py`（新規）**: ゴールデンケースの CLI 実行。
- **ドキュメント（`docs/`）**
  - **`CLOUD_RUN_LLM_ENV.md`**: Cloud Run 向け環境変数一覧（本番 `medicine-recommend` / dev `medicine-recommend-dev`）。
  - **`LLM_ROLLBACK.md`**: 本番切り戻し手順（`LLM_MODEL_PROFILE=legacy` 等）。
  - **`PHASE_EXIT_CHECKLISTS.md`**: Phase 0–3 の出口チェックリスト（薬剤師レビュー用）。
  - **`SDK_SPIKE.md`**: Responses API / SDK 調査メモ。
- **フロントエンド（追記）**
  - **`static/css/main.css` / `static/js/main.js`**: 処理進捗バッジ・多言語ステップ表示のスタイルと連携。
  - **`static/css/admin_chat.css` / `static/js/admin_chat.js`**: 管理画面での進捗表示・セッション操作の調整。

---

**2026年5月14日の更新（オンボーディング・季節粒子・CHANGELOG 追記）:**

- **`templates/index.html`**
  - **`main.css` / `main.js` のキャッシュバスター**を `?v=20260514-7` に更新。
  - **オンボーディング DOM**: `#onboarding-container` 内を **`div.onboarding-body`** で包み、**`div.onboarding-top-row`** に **`#onboarding-active-visual`**（アクティブスライドのビジュアル用ホルダー）と **スキップボタン**を横並び配置。スライド本体・インジケータは `onboarding-body` 内の縦フローに整理。
- **`static/js/main.js`**
  - **オンボーディング文言（日・英・韓・中）**: 開発環境系スライドで **バッジのみを `subtitle`** にし、長文は **`body` の段落**へ移動。改善リストの **`items` に `itemsChecklist: true`** を付与し、**完了済みスタイル付きチェックリスト**（例: **Flask→FastAPI 大規模移行**を `defaultChecked`）を表示。
  - **`createOnboardingDetailsMarkup`**: `itemsChecklist` 時は **読み取り専用チェックリスト**（`onboarding-checklist-readonly`）を生成。文字列／`{ text, defaultChecked }` 形式の **項目正規化**（`normalizeOnboardingDetailItem`）に対応。
  - **免責・プライバシー**: `policyKey` のみの詳細から **`description` 行を削除**（重複説明の整理）。
  - **翻訳の説明**: 旧「自動翻訳はβで停止」表記をやめ、**ユーザー文が非日本語と判定されたときに AI 返信が自動翻訳される**旨と、**左上の言語切替は主に UI 文言**である旨を各言語で追記。
  - **ビジュアル同期**: **`syncOnboardingActiveVisual`** で `#onboarding-active-visual` にアクティブスライドの **`visual` / `visualAlt`** を反映。`renderOnboardingSlides` / `goToOnboardingSlide` から呼び出し。
  - **モーダル高さ**: **`ResizeObserver`** で `#onboarding-container` の高さ変化を監視し、**`--onb-modal-height`** を同期（詳細エリアの `max-height` 計算用）。**`syncOnboardingDetailsDenseClass`** で `<details>` が複数開いたとき **`.onboarding-details-dense`** を付与。
  - **季節粒子（`createSeasonalParticles`）**: 水平ドリフトに **`driftScale = clamp(0.72, 1.12, min(vw, vh) / 720)`** を乗算し、**ビューポート短辺に応じた揺れ幅**に調整。**`MutationObserver`** では **`updateSnowContainerHeight` のみ**実行し、チャット DOM 更新のたびの **粒子 `innerHTML` 全消しを避けてちらつきを抑制**（**2026/5/11** に入っていた「Observer で粒子をデバウンス再生成」から方針変更。**リサイズ**時の再生成デバウンスは従来どおり）。
- **`static/css/main.css`**
  - **`.onboarding-body` / `.onboarding-top-row` / `.onboarding-active-visual`** ほか、**モーダル内 flex・スクロール領域**の整理。**`#onboarding-container .onboarding-body .slide-indicator`** の余白・背景でフッター帯を明確化。
  - **WebKit スクロールバー**（`::-webkit-scrollbar-*`）のトラック／サムの角・**`padding-box` クリップ**で操作性を調整。
  - **`.onboarding-checklist` 系**（マーカー・`.is-done`）と、**`.onboarding-details-dense`** 時の **`.onboarding-details-content` の `max-height`**（ビューポート別メディアクエリ含む）を追加・調整。
- **CHANGELOG 追記（本節）**: 直前まで本文に含めていなかった **`7e022c6`（2026/5/12）** の内容を以下に整理。
  - **`feat(ui): パーティクルをビューポートに応じてスケール`**: **`.snow-container`** に **vmin / clamp ベースの `font-size` と落下マージン用 CSS 変数**。季節パーティクルの **横揺れを画面短辺に比例**。**`static/js/easter-eggs.js`**: 花火・粒子などの **px 系サイズ／ドリフトを `eggParticleScale` で補正**。

---

**2026年5月12日の更新（不要コード・資産の整理）:**

- **`scripts/`**: 移行・抽出用の **`extract_*` / `remove_*` / `build_api_routes.py` / 一時 `tmp_*`** を削除し、行事装飾生成の **`gen_event_decoration_pngs.py` のみ**残した。
- **`static/img/particles/`**: 未参照の **`hanami copy/`** を削除。敬老粒子 **`carnation-particle-soft.png.png`** を **`carnation-particle-soft.png`** にリネーム（`PARTICLE_PROFILES` と一致）。
- **`src/core/season_manager.py`**: 実ファイルのない **`winter` 結晶・`summer` 波**のスプライト参照をやめ、**`IMAGE_ALT_MAPPING`** からも該当キーを削除。`summer` / `autumn` の空 **`images`** を **`{}`** に整理。
- **`src/core/medicine_logic.py`**: コメントアウトされていた import 行と余分なコメント行を削除。
- **`docs/PARTICLE_SPRITE_INVENTORY.md` / `docs/PARTICLE_AI_SPRITES.md`**: 上記スプライト方針に合わせて表を更新。
- **Flask 完全撤去（FastAPI 統一）**
  - **コード削除**: `admin_app.py` / `debug_app.py` / `app_flask_legacy.py` / `src/routes/*` / `src/handlers/error_handlers.py` を削除し、FastAPI（`main.py`）のみを前提とした構成に整理。
  - **依存関係**: `requirements.txt` と `config/requirements.txt` から **Flask / Werkzeug / flask-cors** を削除。
  - **ドキュメント更新**: `README.md`・`docs/*` のローカル起動手順から **Flask レガシー起動**の記述を削除し、FastAPI 前提に統一。

---

**2026年5月11日の更新（季節パーティクル・シーズン判定）:**

- **`src/core/season_manager.py`**: **`is_in_period`** を修正し、**同年で複数月にまたがる期間**（例: 6/1〜8/31、3/1〜5/31）の**中間月**が正しくマッチするようにした（従来は端の2ヶ月のみ判定されていた）。**バレンタイン**を **2/10〜2/18** に拡張。**七夕・敬老・ハロウィン・七五三**の `SEASON_CONFIG` と **`priority_seasons`** を追加。チャット用 **`PARTICLE_PROFILES`** と **`get_particle_profile`**（バレンタイン当日 high・8月のみ summer high・`None` 時は暦月フォールバック）を追加。
- **`main.py` / `src/routes/main_routes.py` / `src/handlers/error_handlers.py`**: `index.html` 向けに **`particle_profile_json`** を渡す。
- **`templates/index.html`**: `#particle-profile` の JSON 埋め込み、**`particlefall`** 用 critical CSS、**`snowfall` 終端**を **`--snow-container-height`** 基準に変更。
- **`static/js/main.js`**: **`createSeasonalParticles`**（プロファイル読込・`prefers-reduced-motion` 非表示・密度・角度・ドリフト・色・任意スプライト）に置換。
- **`static/css/main.css`**: **`.particle-orbit` / `.snowflake-inner` / `particlefall`** を追加。
- **`docs/PARTICLE_COLOR_POLICY.md`（新規）**: 粒子色（#000 禁止・暗色回避）とチャット背景は変更しない旨を記載。
- **`tests/test_season_manager_particles.py`（新規）**: 境界日・密度・優先順のユニットテスト。
- **追記（同一リリース作業内）**: `static/img/particles/` に **淡色スプライト PNG**（バレンタイン・ハロウィン）を追加し、`PARTICLE_PROFILES` の **`sprites`（weight 付き）** と連携。**`docs/PARTICLE_CONTRAST_VERIFICATION.md`・`PARTICLE_DECORATION_OK_NG.md`・`PARTICLE_AI_SPRITES.md`・`STATIC_SEASON_ASSETS.md`** を追加。pytest に **輝度スナップショット・行事日パラメータ・スプライト実在・アセット無しの admin テンプレ**を追加。`main.js` に **重み付きスプライト選択**と **`sanitizeParticleColor`**。`main.css` の **`#snowContainer` / `.snow-container`** に粒子用 **CSS 変数**とスプライト用 **filter** を定義。
- **追記**: 七夕・敬老・ハロウィン・七五三の **左右装飾**を `static/img/events/<行事>/` の淡色 PNG に切替（`scripts/gen_event_decoration_pngs.py`）。`index.html` critical の **`.snow-container`** を **`main.css` と同じ高さ変数**に揃えた。pytest に **`is_in_period` 全期間境界**・**チャット背景固定**・**#c0c0c0 対比コントラスト比スナップショット**・**admin_chat.js 非粒子**を追加。`main.js` の **MutationObserver** から **季節粒子をデバウンス再生成**（500ms）するよう接続。

---

**2026年5月11日の更新（`app.py` FastAPI 既定化・UI／文言・DB 起動ログ）:**

- **`app.py`**: 既定起動を **uvicorn + `main:app`（FastAPI）** に変更。`OPEN_BROWSER`・`ASGI_HOST` 対応、ポート競合時の代替ポート、`FLASK_LEGACY=1` 時は `app_flask_legacy` 経由で Flask 開発サーバ。
- **`app_flask_legacy.py`（新規）**: 従来の Flask アプリ組み立て・Blueprint 登録を分離。Blueprint 比較・検証専用。
- **`README.md` / `docs/FASTAPI_ARCHITECTURE.md`**: 上記エントリ構成に合わせてローカル手順とレガシー起動方法を更新。
- **`main.py`**: 起動時 `init_database()` の成否ログを **`database.init_database` 側に集約**（重複 warning の整理）。
- **`src/services/database.py`**: `startup_skip_reason` と **`_log_database_startup_outcome`** により、未設定 URL・ドライバ未導入・接続失敗・初期化失敗を**理由別に info/warning** で出し分け。psycopg2 未導入時のログレベルを整理。
- **`requirements.txt`**: `psycopg2-binary` を **2.9.12** に更新。
- **`templates/index.html`**: 情報モーダル **`#back-button` をヘッダー左**へ移動（一覧時は非表示）。閉じるボタンを `type="button"` に。
- **`static/css/main.css`**: `#infoModal` ヘッダーを **グリッド**（戻る／タイトル左寄せ／閉じる）、**`.info-modal-back-btn`** の見た目。オンボーディング **ステップ2・3 のスポットライト**（`--onb-spot-*`）、**`.onboarding-links` / `.onboarding-link-btn` のコンパクト化**。**`.info-section strong`** を **本文色継承**（緑太字の羅列を抑制）。
- **`static/js/main.js`**
  - **オンボーディング**: ステップ2・3 で **スポットライト座標更新**・**該当ボタンの pointer-events 有効化**、`resize` 購読。1枚目を **本番停止・GCP 開発環境・改善リスト（`details` + `items`）・リンク** に更新（多言語）。補足文・長い箇条書きの整理。
  - **情報モーダル（アプリ概要等）**: **運営者「基本情報」ブロック削除**（app-overview / operator・4言語）。**開発環境・使用ツール** を **FastAPI / MeCab / OpenAI API 表記**、**GCP（Cloud Run）+ Gunicorn UvicornWorker**、**CI/CD を Cloud Build** に更新。**Render 表記を削除**。Flask 補足・技術欄の Flask 注記を削除。**`createOnboardingDetailsMarkup`** に **`items` 配列**対応。
- **`static/css/main.css`（追記・同日）**: オンボーディング **`<details>` 内スクロール**（`.onboarding-details-content`）の **最大高さを縮小**（ビューポート別に `min(…px, …vh)` を調整）、**`scrollbar-gutter: stable`**・**`overscroll-behavior: contain`**・**`-webkit-overflow-scrolling: touch`**・**`overflow-x: hidden`** でスクロール挙動を整理。説明文用 **`.onboarding-details-desc`**。`.onboarding-visual` / `.onboarding-title` の余白、**アクティブスライド**の **`.onboarding-details` の `min-height` / `flex-shrink`** でレイアウトのはみ出しを抑制。
- **`static/js/main.js`（追記・同日）**: **`createOnboardingDetailsMarkup`** で `detail.description` を **`<p class="onboarding-details-desc">`** とし、**`.onboarding-details-content` 内**（箇条書き・ポリシー本文と同じスクロール領域）に **先頭で結合**。`<summary>` 直下に裸の説明を置かない構造に変更。

---

**2026年5月10日の更新（プロキシ配下のクライアント IP・favicon・リポジトリ運用）:**

- **`src/utils/chat_http_context.py`**: `resolve_client_ip` / `_first_forwarded_client_ip` を追加し、**`X-Forwarded-For` の先頭**（カンマ区切りの第1要素）を優先してクライアント IP を決定（Render / nginx 等のリバースプロキシ経由を想定。未設定時は `remote_addr` / `request.client.host` にフォールバック）。`ChatClientInfo.from_flask_request` および `from_starlette_request` で Flask と FastAPI（Starlette）の双方から**同一ルール**で組み立て。
- **`src/routes/main_routes.py`**: `index` で `ChatClientInfo.from_flask_request` を**一度だけ**呼び出し、GET（既存セッション検索・アクセス解析など）と POST（`handle_chat_post`）で **`chat_client` を共有**。GET と POST で IP の解釈が食い違わないようにした。`new_session` の `client_ip` / `user_agent` 記録も同ファクトリに統一。
- **`main.py`**: チャット POST の JSON 応答生成（`_post_chat_json_response`）で、単独の `request.client.host` 参照から **`ChatClientInfo.from_starlette_request(request)`** へ切り替え。
- **`static/favicon.ico.png`**: ブランド用アイコンを差し替え、**ファイルサイズを約 2.5MB から約 62KB へ削減**（`GET /favicon.ico` の配信・HTML の `link rel="icon"` は従来どおり）。
- **その他（同コミットに含まれる随伴変更）**: `start.sh` の ASGI 非互換ワーカー補正 `case` の**重複を整理**、`render.yaml` の `GUNICORN_WORKER_CLASS` 周りコメントを補足、`Dockerfile`・`main.py`（付随する本番・ルート周りの調整）、`static/js/main.js`・`templates/index.html` の小修正。
- **GitHub ブランチ整理**: マージ済みのローカル作業ブランチを削除。リモートの **`cursor/*`・`codex/*` 作業ブランチを削除**し、運用上は **`main` のみ**とした（コミット履歴は `main` に保持）。

---

**2026年5月9日の追記（Flask → FastAPI 移行状況の棚卸し・完了内容）:**

- **結論**: 本番運用経路としての Flask から FastAPI への移行は完了。`start.sh` / Render 起動は `gunicorn` + `uvicorn.workers.UvicornWorker` + `main:app` を前提とし、ユーザー向け UI・チャット POST・主要 API・管理画面・フィードバック API は FastAPI 側で提供する。
- **補足（2026年5月12日追記）**: Flask 依存（コード・依存関係）は完全撤去済み。以後は FastAPI（`main.py`）のみを前提とする。
- **完了内容**
  - **本番エントリの切替**: 本番起動を WSGI/Flask ではなく ASGI/FastAPI の `main:app` に統一。WSGI worker 誤設定時は `start.sh` で ASGI 互換 worker に補正する。
  - **主要ルートの移植**: `/`、`/test/`、`/api/*`、`/admin`、`/admin/*`、フィードバック系 API、セッション操作、管理者返信、AI 制御、ログ・パフォーマンス取得などを FastAPI 実装へ集約。
  - **チャット処理のフレームワーク分離**: `handle_chat_post` は Flask の `request` / `jsonify` に依存せず、`message`、`ChatClientInfo`、`RequestSafeSession`、`sid`、monitor を受け取り、`tuple[dict, int]` を返す形に統一。
  - **セッション方針の整理**: Flask 署名セッションから `sid` Cookie + DB 正の管理へ移行し、FastAPI 側で Cookie 属性を `get_session_config()` に合わせて設定。
  - **CORS・静的ファイル・テンプレート互換**: `CORSMiddleware`、`StaticFiles`、`Jinja2Templates` を利用し、既存テンプレートの `url_for('static', filename=...)` 互換も維持。
  - **エラー応答の整備**: 404 / 422 / 500 の HTML・JSON 応答を FastAPI 側で定義し、POST や JSON リクエストでは JSON 500 を返すよう整理。
  - **デプロイ設定の更新**: Render 設定と README の本番起動案内を FastAPI / ASGI 前提に更新。
  - **契約テストの追加**: `tests/test_fastapi_contract.py` で FastAPI ルートの status、content-type、主要 JSON キー、管理画面認証、チャット POST などを確認できるようにした。
- **苦労した点**
  - **Flask のリクエスト文脈依存の除去**: 既存処理が `request`、`session`、`jsonify`、Blueprint に広く依存していたため、チャット処理を HTTP 層から切り離し、FastAPI とレガシー Flask の両方から扱える戻り値へ揃える必要があった。
  - **セッション移行の互換性**: Flask 署名セッションをそのまま継続せず `sid` Cookie + DB 正へ寄せたため、既存の会話履歴・属性復元・管理画面表示と矛盾しないように初期化・復元順序を慎重に調整した。
  - **JSON / FormData の差異**: Flask の `request.form` / `request.json` と FastAPI の `Form(...)` / `await request.json()` の違いにより、チャット POST、管理 API、不正 JSON、空 payload の扱いを個別に揃える必要があった。
  - **末尾スラッシュとリダイレクト**: POST で 307/308 が発生すると FormData 再送事故につながるため、`redirect_slashes=False` とルート定義の粒度を確認しながら移植した。
  - **本番 worker の罠**: FastAPI は ASGI アプリのため、従来の sync/gevent など WSGI worker では 500 になり得る。起動スクリプト側で誤設定を補正する必要があった。
- **「完全移行」の定義整理**: 当時は「本番移行完了」と「Flask 完全撤去は未完了」を分けて記録していたが、現在は Flask 完全撤去も完了した。

---

**2026年5月9日の更新（Flask → FastAPI 一括移行・挙動互換）:**

- **ASGI エントリ `main.py`（新規）**
  - FastAPI 単体で `/`・`/test/`・`/api/*`・`/admin*`・フィードバック API を提供（Flask へのマウント・フォールバックなし）。
  - `FastAPI(redirect_slashes=False)` により、`POST /`・`POST /test/`・`/api/*` で **307/308 リダイレクトを発生させない**（FormData 再送事故の防止）。
  - **CORS**: `config/app_config.get_cors_config()` を `CORSMiddleware` に反映（`allow_credentials`・`origins` 等、`credentials: 'include'` 互換）。
  - **静的ファイル**: `StaticFiles` で `/static` を配信。
  - **Jinja2**: `Jinja2Templates` + グローバル `url_for('static', filename=...)` 互換（既存 `templates/*.html` の `url_for` を維持）。
  - **セッション**: Flask 署名セッションは継続しない。**`sid` Cookie + DB 正**（`src/services/session_manager.py` / `database.py`）。Cookie 属性は `get_session_config()` の `SESSION_COOKIE_SECURE` / `SAMESITE` / `HTTPONLY` を `set_cookie` に反映。Cookie 名は環境変数 `SID_COOKIE_NAME`（既定 `sid`）。
  - **チャット POST**: FormData `message` を `handle_chat_post` に**直接**渡し、戻り値 `tuple[dict, int]` を `JSONResponse` で返す（当初の Flask `test_request_context` 互換層は**撤去**済み。詳細は下記「FastAPI 仕上げ」節）。
  - **ルート実装（Flask 対応表どおり）**
    - UI: `GET/POST /`・`GET/POST /test/`、`POST /clear`・`/new_session` と `/test/clear`・`/test/new_session`（204 / JSON 形は従来互換）、`GET /favicon.ico`（`static/favicon.ico.png` を `image/png` で配信、無い場合 204）、`GET /sitemap.xml`（`application/xml; charset=utf-8`、`PUBLIC_SITE_URL`）。
    - API: `GET/POST /api/sessions`、`/api/status`・`performance`・`logs`、`/api/all_sessions`（**JSON 配列**、Flask `jsonify(result)` 互換）、`session_stats`、`debug_manual_replies`、`ai_control`・`manual_reply_queue`（GET/POST）、`main_sessions`・`main_manual_reply_queue`・`main_ai_control`、`manual_reply_message`、`request_admin`、`admin_mode`、`user_attributes`、`set_language`、`translate`。
    - フィードバック: `POST /api/submit_feedback`（必須項目・**60秒レート制限（sid 単位）**・本文長上限・DB 不可時 500）、`GET /api/get_feedback_reports`、`POST /api/resolve_feedback/{id}`・`delete_feedback/{id}`。
    - 管理: `GET /admin`（**HTTP Basic**・401 + `WWW-Authenticate`）、`GET /admin/system_status`・`access_stats`・`performance_stats`・`browser_distribution`・`os_distribution`・`device_distribution`・`realtime_monitoring`・`export_monitoring_data`、`POST /admin/ai_control`・`admin/medicine_chat`、`POST /clear_logs`（DB なし時 `clear_sessions_fallback`・`log/recommendation_log.jsonl` 切り捨て、Flask 同等）、`GET/DELETE/PUT /api/admin/sessions*`・`POST /api/admin/send_message`。`GET /api/admin/sessions` で `cleanup_old_sessions`（現行 sid 除外）を呼び出し。
  - **JSON 入力の堅牢化**: `_read_json_dict` および `submit_feedback` の `JSONDecodeError` 捕捉で不正 JSON を **400** に（ASGI 未処理例外によるプロセス終了の防止）。
  - **例外ハンドラ**: 404 は `index.html` を **404** で返却（Flask 404 ハンドラに近い）。422 は JSON `detail`。その他未処理例外は `POST` または `Content-Type: application/json` なら JSON 500（`error` / `response` / 非本番時 `error_type`）、それ以外は簡易 HTML 500。`StarletteHTTPException` が汎用ハンドラに入った場合は HTTP 用ハンドラへ委譲。
- **依存関係（`requirements.txt`）**
  - 追加: `fastapi`、`uvicorn[standard]`、`python-multipart`、`jinja2`、`pytest`（契約テスト用）。既存 Flask 系は参照・比較用に残存しうる。
- **起動（`start.sh`）**
  - `GUNICORN_WORKER_CLASS` 既定を `uvicorn.workers.UvicornWorker` に変更。アプリを **`main:app`** に変更。既定 `PORT` を 8000 に（Cloud Run は引き続き `PORT` 注入でバインド）。
- **ドキュメント（新規・計画の成果物）**
  - `docs/ROUTE_SPEC.md`: 全ルートの仕様表（メソッド・入出力・ガード・根拠ファイル）。
  - `docs/FASTAPI_ARCHITECTURE.md`: モジュール境界・CORS/Cookie・エラー方針・デプロイ。
  - `docs/SMOKE_MANUAL.md`: 手動スモークチェックリスト。
- **自動テスト（新規）**
  - `tests/test_fastapi_contract.py`: `TestClient` による Status / Content-Type / 主要キー / `APP_BASE_PATH` / チャット POST JSON / 管理・周辺 API の最小回帰（`pytest` 実行）。
- **補足**
  - レガシー `app.py`（Flask）・`src/routes/*` はリポジトリに残り、挙動比較・ドメインロジックの参照に利用可能。本番起動スクリプトは ASGI（`main:app`）を前提。

**2026年5月9日の更新（FastAPI 仕上げ・Flask 依存整理・チャットコアのフレームワーク分離）:**

- **目的**: 本番 ASGI 経路（`main:app`）から Flask/Werkzeug のリクエスト文脈への依存を除き、チャットの戻り値を **`tuple[dict, int]`** に統一。FastAPI は `JSONResponse`、レガシー Flask ルートは `jsonify(body), code` に**変換のみ**残す。
- **`src/utils/chat_http_context.py`（新規）**: `ChatClientInfo`（`client_ip`・`user_agent`）を定義。`handle_chat_post` および `src/handlers/chat/*` に渡し、ハンドラ内の `request.remote_addr` / `User-Agent` 直接参照を廃止。
- **`src/utils/request_safe_session.py`**: Flask `has_request_context()` 直結をやめ、**内部 `dict` + `modified`** のミュータブルセッション実装に一本化。ファイル先頭コメントで、Flask 利用時はアプリ側で `flask.session` と同期する旨を記載。
- **`app.py`（レガシー）**: `before_request` で `dict(flask.session)` から `RequestSafeSession` を生成し `g.safe_session_work`・`extensions['safe_session']` に設定。`after_request` で `modified` 時に `flask.session` へキーごと書き戻し。先頭 docstring で**本番は `main:app`・当エントリはローカル比較用**と明記。
- **`src/handlers/chat_handler.py`**: シグネチャを `handle_chat_post(session, client_info: ChatClientInfo, message: str, sid, monitor)` に確定。`jsonify`・`from flask`・`request.*` を除去。`src/core/medicine_logic` のクライアントは **`openai_client`** として import（引数名と HTTP クライアント情報の衝突回避）。
- **`src/handlers/chat/*.py`**: `jsonify` をすべて `(dict, HTTPステータス)` に置換。`from flask` を除去。引数に `ChatClientInfo`（`client` 等）を受け取るよう連鎖的に整理（例: `chat_store_inquiry.py` の docstring を現行戻り値に合わせて更新）。
- **`main.py`**: 仮想 Flask アプリ・`test_request_context`・`flask_request` 橋を**削除**。`_prime_safe_session_for_chat` で `RequestSafeSession` を用意し、`_post_chat_json_response` 内で `handle_chat_post` を呼び **`JSONResponse(content=body, status_code=status_code)`** を返す。Cookie `sid`・`get_session_config` 整合は維持。
- **`src/routes/main_routes.py`**: POST で `request.form.get('message')` と `ChatClientInfo(...)` を組み立て、`body, code = handle_chat_post(session, client_info, message, sid, monitor)` のあと **`return jsonify(body), code`**。
- **`src/handlers/error_handlers.py`**: `register_error_handlers(app, version)` 形式に整理。404/502/500 で Flask セッション等を参照する既存方針を維持（FastAPI の例外処理は `main.py` 側）。
- **ドキュメント**: `README.md` のクイックスタートで本番は `./start.sh` / `gunicorn main:app`、`python app.py` はレガシーと明記。`docs/FASTAPI_ARCHITECTURE.md` を「直接 `handle_chat_post`」の現行構成に合わせて更新。
- **依存関係**: `requirements.txt` の **Flask / flask-cors は削除せず維持**（`app.py`・`src/routes/*`・`admin_app.py`・`debug_app.py`・`scripts/*` 等）。`src/core/` は本リファクタの対象外（未変更）。
- **テスト**: `tests/` は `app:app` 直起動に依存しない構成のまま。`pytest` 全件（`tests/test_fastapi_contract.py` のチャット POST・管理・周辺 API を含む）で回帰確認。
- **実装メモ（内部計画との差分）**: セッション同期は計画案の「POST 入り口のみコピー／書き戻し」ではなく、**`app.py` の `before_request` / `after_request` でリクエスト単位同期**とした（GET で `extensions['safe_session']` を使う既存フローとの整合優先）。

**2026年5月9日の更新（favicon）:**

- **アセット**: `static/favicon.ico.png` を追加（相談用吹き出し＋カプセルのブランドアイコン）。
- **配信**: `GET /favicon.ico` を FastAPI（`main.py` の `FileResponse`）および Flask（`src/routes/main_routes.py` の `send_from_directory`）の双方で `image/png` として返却。ファイルが無い環境では従来どおり **204**（空応答）。
- **HTML**: `templates/index.html`・`templates/admin_chat.html` の `<head>` に `<link rel="icon" href="{{ url_for('static', filename='favicon.ico.png') }}" type="image/png">` を追加（`/static/...` 直リンクと併用可能）。
- **ドキュメント・テスト**: `docs/ROUTE_SPEC.md`・`docs/SMOKE_MANUAL.md` を更新。`tests/test_fastapi_contract.py` の `test_favicon_png` で 200・`Content-Type`・ボディサイズを検証。

---

**2026年2月12日の更新（改善計画の実装）:**

- **「15歳以上以上」の重複表現を修正**: `chat_recommendation_flow.py` の usage_notes パース処理で、年齢制限が「15歳以上」などの場合に「15歳以上以上の方が対象です。」と重複表示されていた問題を修正。`re.search(r'(\d+)歳以上')` で数値を抽出し、「〇歳以上の方が対象です。」と正しく表示するように変更。
- **カロナールA・タイレノールAの効能データを修正**: `otc_medicine_data.csv` で、カロナールＡ・タイレノールＡの効能が「生理痛」のみとなっていた問題を修正。`summarized_efficacy_data.csv` に合わせて「頭痛・月経痛（生理痛）・歯痛・抜歯後の疼痛・咽喉痛・腰痛・関節痛・神経痛・筋肉痛・肩こり痛・耳痛・打撲痛」などの包括的な効能に更新。これにより、頭痛・発熱時の推奨精度が向上。
- **イブプロフェン200S/200SCの同一成分重複を回避**: `ingredient_diversity.py` に `_is_ibuprofen_only_group` 関数を追加し、fallback 追加時にイブプロフェン系の同一成分チェックを実施。イブプロフェン錠200S とイブプロフェン錠200SC が2位・3位に並ばないように改善。
- **HTMLタイポ検索手順のドキュメント化**: `docs/改善計画.md` に HTML タイポ検索手順セクションを追加。`conteent`、`classs=`、`ddiv` などの typo パターンと検索対象ディレクトリ、grep 例を記載。
- **医薬品名の半角統一機能追加**: `scoring_utils.py` に `normalize_medicine_name_to_hankaku` 関数を追加。数字・アルファベットを半角に統一し、比較・検索時に使用。`MAJOR_ANALGESIC_MEDICINES` との比較時に半角正規化を適用（`candidate_scoring.py`、`final_score_calculator.py`、`rule_based_recommendation.py`、`recommendation_finalizer.py`、`ingredient_diversity.py` を更新）。これにより、全角・半角混在の医薬品名でも正しくマッチングされるように改善。

---

**2026年2月11日の更新（クラウド移行）:**

- **GCP Cloud Run への移行**: Render から GCP Cloud Run へ移行。GitHub 連携による継続的デプロイ（push で自動ビルド・デプロイ）を実現。Dockerfile を新規作成し、コンテナ化。移行期間は **2日**。
- **Neon PostgreSQL への移行**: Cloud SQL から Neon（サーバーレス PostgreSQL）へ移行。コストを大幅に削減し、スケールゼロ・従量課金で運用。
- **本番 URL**: [https://medicine-recommend-340042923793.asia-northeast1.run.app/](https://medicine-recommend-340042923793.asia-northeast1.run.app/)。詳細は [☁️ クラウド移行・本番環境](#-クラウド移行本番環境2026年2月) を参照。

---

**2026年2月9日の更新:**

- **不適切入力のブロックとUI表示の改善**: 絶対ブロック・セキュリティブロック時に、従来の `error: true` レスポンスではフロントが何も表示しなかった問題を解消。ブロック時もセッションに「（この入力はブロックされました）」＋案内メッセージを追加し、**DB（またはメモリ）に永続化**して `status: 'ok'` と `message_count` で返すように変更。これにより GET /api/sessions でメッセージが取得され、UI に案内が表示される。
- **ブロック時の永続化**: `chat_input_validator.py` に `_persist_block_messages_to_db(session, request, sid)` を追加。絶対ブロック・セキュリティブロック・高リスク警告のいずれでも、Flask session に追加したメッセージを `save_session_to_db` で保存するようにした。
- **不適切ワードの拡張**: `config/keywords.py` の `INAPPROPRIATE_MESSAGE_KEYWORDS` を拡張。**スカトロ**に加え、**パパ活**（ぱぱかつ、ぱぱ活、逆援助、sugar daddy / sugar baby）、**おっぱぶ**（オッパブ、おっぱいぶ）、**ナンパ・出会い系**、**ロリコン・ショタコン**、**ビッチ・ヤリマン・種付け**、**オーラル**などを追加し、多様な不適切表現に対応。
- **セキュリティブロック以外はユーザーフレンドリーなプレーンテキスト**: 絶対ブロック時の案内文を「ご入力いただいた内容にはお答えできかねます。お体の不調やお薬のご相談がありましたら、お気軽にメッセージをお送りください。」に変更（プレーンテキスト・ユーザーフレンドリー）。
- **UI に元入力を表示（正規化でひらがなにならないように）**: `basic_normalize_text()` によりカタカナ→ひらがな変換した結果がそのまま UI に表示されていた問題を修正。ユーザー発言としてセッションに追加する際は **正規化前の元入力**（`original_user_message` / `user_message`）を使用するように変更。`chat_handler.py`（Other ブロック）と `chat_triage_follow_ups.py`（医薬的予防・不適切要求の 2 箇所）で対応。

---

**2026年2月8日の更新（SRP改善計画の全Phase完了）:**

- **app.py のスリム化**: アプリ作成・設定（CORS・セッション・DB初期化）・エラーハンドラー登録・Blueprint の import/register・起動処理のみに限定（**約89行**）。ビュー定義はすべて各ルートモジュールに移管。
- **ルートの責務分離**: `main_routes.py` / `admin_routes.py` / `api_routes.py` / **`feedback_routes.py`** でビューを自モジュール内に定義し、`create_*_routes()` は引数なしで Blueprint を返す形に統一。登録は `app.register_blueprint(create_feedback_routes())` 等。
- **rule_based_recommendation の分割**: 定数は `recommendation_constants.py` へ。新規 `src/core/recommendation/` に `life_stage_preference.py`・`symptom_pattern_matcher.py`・`recommendation_finalizer.py`・`recommendation_scoring.py`・`ingredient_diversity.py`・`final_score_calculator.py` を配置。`rule_based_recommendation.py` はオーケストレーションと re-export のみ（約1,580行）。
- **medicine_logic の分割**: `src/core/openai_client.py` で OpenAI クライアント初期化を集約。新規 `src/core/medicine/` に `medicine_recommendation_gpt.py`・`medicine_response_builder.py` を配置。`medicine_logic.py` はエントリポイントと re-export のみ（約215行）。
- **counseling_response の分割**: 新規 `src/services/counseling/` にテンプレート・ログ・プロンプト・生成・質問・満足度・要約・話題転換・モード制御・プロセッサを配置。`counseling_response.py` はファサード（re-export 維持、約104行）。
- **chat_handler の分割**: 新規 `src/handlers/chat/` に `chat_input_validator.py`（入力検証・ブロック・危機検出・ブロック時のDB保存）・`chat_response_builder.py`・`chat_triage.py`・`chat_counseling_flow.py`・`chat_recommendation_flow.py`・`chat_manual_reply.py`・`chat_emergency_handler.py`・`chat_diagnosis_handler.py`・`chat_store_inquiry.py`・`chat_triage_follow_ups.py` を配置。`chat_handler.py` はオーケストレーション（約2,641行）。
- **scripts と src の役割**: **scripts/** は開発補助（現状は行事装飾 PNG 生成の **`gen_event_decoration_pngs.py`** のみ）。**src/** はアプリケーション本体（core・handlers・routes・services・utils・security・analysis）。実行時は src のみが import される。
- **妊娠・授乳時レッドフラッグ**のエスカレーション表示を `format_escalation_display` で統一。**エラー表示**をユーザーフレンドリーに改善（技術的エラー内容を非表示、再試行案内を表示）。

---

**2026年2月7日の更新:** 候補医薬品のキー正規化モジュール（candidate_normalizer.py）を新規作成。スコアリングの統合テスト失敗7件を解消（アセトアミノフェン・NSAIDs推奨）。カロナール・タイレノール・ロキソニン系を生理痛専用医薬品の除外から例外として追加。SRPを順守し、性能への影響を最小限に抑えた実装。

---

**2026年1月16日の更新:** オンボーディングUIの改善：スクロール対応・レスポンシブ対応の強化・イースターエッグ機能の説明スライド追加（多言語対応：日本語・英語・韓国語・中国語）・アプリケーション資料へのリンクスライド追加（β版のみ表示）・β版判定ロジックの実装・バレンタインシーズン対応UI機能の追加：2月14日に自動的にバレンタイン装飾を表示する機能・節分シーズン対応UI機能の追加：2月1日～2月3日に節分装飾を表示する機能・冬の一般シーズン対応UI機能の追加：1月8日～1月31日、2月4日～2月13日、2月15日～2月28日に冬装飾を表示する機能・緊急避妊薬対応機能の追加：性被害を含む緊急避妊薬に関する質問への適切な対応・72時間以内の服用の重要性を強調・対面診療とオンライン診療の案内・心理的サポートと警察への相談の案内・マークダウン記号の削除による応答の改善・重複メッセージの防止・表記ゆれへの対応（「避妊出来なかった」など）・単一症状時の3つの医薬品推奨保証機能：効能効果に症状が含まれている候補を優先的に追加するロジック・除外ロジックをスキップして強制的に追加する処理・`ensure_ingredient_diversity`関数の改善・スコアリングシステムの根本的改善：主要解熱鎮痛薬のボーナス強化（カロナールA/タイレノールA: 0.6→0.8、ロキソニンS: 0.4→0.6、ロキソニンS外用薬: 0.6→0.8）・単一症状に対する総合感冒薬のペナルティ強化（0.0→-0.7）・主要解熱鎮痛薬の基本スコア底上げ（0.55）・調整スコア上限の引き上げ（主要解熱鎮痛薬: 0.6→0.8）・単一症状時の総合感冒薬の基本スコア減少（-0.1）・単一症状スコアリング改善：同義語マッピング拡張（「たん」「痰」の状態表現対応）・誤検知防止機能（ブラックリストによる局所判定）・効能特異性スコア底上げ（0.5）・症状特異性ペナルティ緩和（効能特異性0.5以上でペナルティなし）・去痰成分ボーナス（西洋薬0.15・漢方薬0.10）・鎮咳成分ペナルティ・浮動小数点比較改善（イプシロン比較）・キャッシュ機能・エラーハンドリング強化・総合風邪薬推奨ロジックの大幅改善：総合風邪薬ボーナスの強化（0.9）・2位選定時のロジック改善（総合風邪薬以外の内服薬を優先）・効能特異性フィルタリングの強化・栄養補給・滋養強壮薬の除外・小児専用製品のフィルタリング改善・効能データの修正・UI/UX大幅改善：高齢者向けアクセシビリティ機能・セクション折りたたみ機能・音声読み上げ機能・文字サイズ調整機能・WCAG AA準拠のコントラスト改善・キーボード操作対応・フォーカスリング強化・UDフォント対応・方言対応機能の実装・謹賀新年縦書きアニメーション追加・緊急事案検出の誤検知防止機能・ユーザーメッセージ重複表示の修正・症状検出の改善・カウンセリングフロー返信の改善・診断名検出機能の大幅改善・イースターエッグ機能の大幅拡張・成分重複チェック機能・曖昧入力検出の改善・総合感冒薬推奨ロジックの強化・カテゴリ多様性の確保・アドバイス生成の改善・管理画面UI改善・薬剤師要請機能の改善・README完全化：環境変数一覧・APIエンドポイント一覧・トラブルシューティングの拡充）

---

<div align="center">

# 🎊 2026年、明けましておめでとうございます 🎊

**新年あけましておめでとうございます。**  
2026年も、チャット型医薬品相談ツールの開発・改善にご協力いただいたすべての皆様に、心より感謝申し上げます。

**本年もどうぞよろしくお願いいたします。** 🙏✨

</div>


---

### 🚀 2026年への展望と抱負

<div align="center">

**より安全で使いやすいシステムを目指して、継続的な改善を行ってまいります。**

</div>

#### 🎯 2026年の抱負

**物理学科としての目標：**
- **🔬 物理学的思考の応用**: 統計力学や情報理論の知識を活用し、より精密な医薬品推奨アルゴリズムの開発
- **📊 データ分析の深化**: 量子統計や確率論の観点から、ユーザーデータの分析精度を向上
- **⚛️ システムの最適化**: 熱力学のエントロピー概念を応用し、システムの効率性と安定性を追求

**本アプリケーションの目標：**
- **♿ アクセシビリティの徹底**: WCAG AAA準拠を目指し、すべてのユーザーが使いやすいシステムを実現
- **🌍 多様性への対応**: より多くの言語・文化・身体特性に対応した包括的なシステムの構築
- **🤖 AI精度の向上**: より適切な医薬品推奨の実現と、ユーザーの健康状態に応じたパーソナライズドな推奨
- **🔒 安全性の強化**: 継続的なセキュリティ対策と、医療情報の適切な取り扱い
- **📱 ユーザー体験の革新**: より直感的で使いやすいUI/UXと、高齢者を含むすべてのユーザーへの配慮

| 領域 | 方向性 |
|:---|:---|
| **🔬 機能の拡充** | より多くの症状パターンへの対応、アルゴリズム改善 |
| **🤖 AI精度の向上** | より適切な医薬品推奨の実現、統計力学的手法や潜在空間の活用を検討中 |
| **💫 ユーザー体験** | より直感的で使いやすいUI/UX、アクセシビリティの徹底 |
| **🛡️ 安全性** | 継続的なセキュリティ対策の実施、医療情報の適切な取り扱い |
| **♿ アクセシビリティ** | WCAG AAA準拠を目指し、すべてのユーザーが使いやすいシステムを実現 |

<div align="center">

---

**2026年も、より良いシステムを目指して邁進してまいります。**  
**皆様、本年もどうぞよろしくお願いいたします。** 🙏✨

---

</div>

---

## 📅 一年間の軌跡

<div align="center">

**2025年は、本システムにとって急速な成長と進化の年となりました。**

*GitHubのコミット履歴によると、**10月から12月にかけて367コミット**を実施し、ほぼ毎日機能追加・改善を行いました。*

</div>

---

### 🎨 **October 2025** | 基盤構築とUI/UX改善

<div align="right">

*205 commits*

</div>

| 領域 | 実装内容 |
|:---|:---|
| **🌍 多言語対応** | 日本語・英語・中国語・韓国語への対応を開始 |
| **🔍 症状検出** | 包括的な症状キーワードの追加と医薬品タイプ分類の精度向上 |
| **🎨 UI/UX** | ユーザー情報モーダル、オンボーディングガイド、FAQセクションの実装 |
| **⚙️ 管理者機能** | フィードバック機能、セッション管理、詳細症状情報の表示 |
| **🔒 安全性** | 症状検出ロジックの改善とエラーハンドリングの強化 |

---

### 🚀 **November 2025** | パフォーマンス最適化と基盤の確立

<div align="right">

*51 commits*

</div>

| 日付 | 実装内容 |
|:---|:---|
| **11/2** | ハイブリッド推奨システム：ルールベースとAIの融合による高精度な推奨を実現 |
| **11/4-5** | マルチインスタンス対応：PostgreSQLベースのセッション管理システムを実装 |
| **11/5** | パフォーマンス最適化：二段階スコアリングによる高速化、ChatGPT API呼び出しの統合（**約67%削減**） |
| **11/5** | 管理者機能の強化：手動返信キュー、セッション管理、統計表示機能の実装 |
| **11/22** | 漢方薬推奨アルゴリズム：34種類の漢方薬に対する詳細なルールを統合 |

---

### ⚡ **December 2025** | 機能の爆発的拡張

<div align="right">

*111 commits*

</div>

#### 🎯 主要機能の実装タイムライン

```
12/5  → 部位特異的製品の検出とChatGPTによる質問生成機能
12/11 → 多言語対応の高速化：DeepL APIへの移行（翻訳速度 10-20倍高速化）
12/16 → LLMトリアージ機能：5つのカテゴリへの自動分類とconfidenceスコアによる判定
12/16 → カウンセリング機能：感情的症状への共感的な対応と会話履歴を活用した文脈理解
12/25 → シーズン対応UI：クリスマス・正月仕様の自動切り替えと年度ごとの干支画像表示
12/26 → イースターエッグ機能：13種類の特別イベント対応
12/27 → 診断名検出機能：約170項目の診断名を検出し、適切な医師相談を推奨
12/29 → 店舗案内機能：在庫確認、遺失物、トイレ案内など2,362件の商品データベースに対応
12/29 → 緊急事案検出機能：火災、医療緊急、不審者などの自動検出と誤検知防止
12/31 → 方言対応機能：全国の方言（関西弁、東北弁、九州弁、名古屋弁、和歌山弁など）を標準語に変換し、症状を正確に抽出
12/31 → 成分重複チェック機能：30種類のリスク成分を検出し、過剰摂取リスクを防止
12/31 → 「謹賀新年」縦書きアニメーション：新年・大晦日に美しい縦書きアニメーションを表示
```

---

### 🎯 主な成果

<div align="center">

| 指標 | 実績 |
|:---|:---|
| **📊 開発規模** | 10月から12月にかけて**367コミット**、ほぼ毎日機能追加・改善を実施 |
| **🌍 対応言語** | 4言語（日本語・英語・中国語・韓国語）をDeepL APIで高速翻訳 |
| **🔒 安全性** | **850以上の攻撃パターン**に対する多層防御、診断名検出による適切な受診勧告 |
| **⚡ パフォーマンス** | API呼び出し回数を**約67%削減**、翻訳速度を**10-20倍高速化** |
| **✨ ユーザー体験** | 13種類の特別イベント対応、美しいアニメーション効果、シーズン対応UI |

</div>


🎄 **メリークリスマス！🎄**  
サンタからのクリスマスプレゼントとして、シーズン対応UIシステムを実装しました！🎁✨ 
- **自動シーズン切り替え**: 12月26日以降は自動的に正月仕様に切り替わります
- **年度ごとの干支画像**: 2026年以降は、その年度の干支画像を自動表示します
- **拡張性の高い設計**: 将来的に春・夏・秋のシーズンにも簡単に対応できます
- **雪のアニメーション改善**: スクロールしても途切れることなく、美しい雪が降り続きます。チャットメッセージの邪魔にならないように、メッセージの下に表示されるようになりました。

素敵なクリスマスと良いお年をお過ごしください！🎅🎁🎊

## 📁 フォルダ構造の整理（2025年12月21日）

プロジェクトの可読性とメンテナンス性を向上させるため、フォルダ構造を整理しました：

### 実施した整理内容

1. **設定ファイル** → `config/` フォルダ
   - `gunicorn_config.py`
   - `requirements.txt` (デプロイ用にルートにもコピーを保持)
   - `runtime.txt` (デプロイ用にルートにもコピーを保持)

2. **ドキュメントファイル** → `docs/` フォルダ
   - 技術ドキュメント（ASYNC_IMPLEMENTATION_GUIDE.md、C_OPTIMIZATION_ANALYSIS.md など）
   - 日本語ドキュメント（アプリ概要.md、プライバシーポリシー.md など）

3. **データファイル（CSV）** → `data/` フォルダ
   - すべてのCSVファイルを`data/`フォルダに移動
   - `medicine_logic.py`と`scoring_utils.py`のパス参照を更新

4. **ログファイル** → `log/` フォルダ
   - `app.log`のパス参照を`log/app.log`に更新（次回起動時から適用）

5. **テスト・スクリプトの配置**
   - **テストファイル** → `tests/` フォルダ（`test_comprehensive_integration.py` 等のテストスイート）
   - **開発用スクリプト** → `scripts/` フォルダ（**2026年5月現在**: 行事装飾 PNG 用の `gen_event_decoration_pngs.py` のみ。過去の Flask 移行用 `extract_*` / `remove_*` は整理済み）

### 効果
- プロジェクト構造の明確化
- ファイル検索の容易化
- メンテナンス性の向上
- デプロイ時の設定ファイル管理の簡素化

**scripts/ と src/ の違い（2026年2月8日、2026年5月12日追記）:**  
- **src/** はアプリケーション本体で、実行時に `app.py` 等から import される（core・handlers・routes・services・utils・security・analysis）。  
- **scripts/** は開発補助用で通常のアプリ起動では読み込まれない（移行完了後は **`gen_event_decoration_pngs.py`** のみを維持）。


---

## 📝 最近の更新履歴

### 2026年2月9日（不適切ワード対応・ブロック時のUI/DB改善・元入力表示）
- **不適切入力のブロックとUI表示の改善**
  - 絶対ブロック・セキュリティブロック時に、従来の `error: true` レスポンスではフロントが何も表示しなかった問題を解消。ブロック時もセッションに「（この入力はブロックされました）」＋案内メッセージを追加し、**DB（またはメモリ）に永続化**して `status: 'ok'` と `message_count` で返すように変更（`chat_input_validator.py` に `_persist_block_messages_to_db` を追加）。
  - これにより GET /api/sessions でメッセージが取得され、UI に案内が表示される。
- **不適切ワードの拡張**（`config/keywords.py`）
  - **スカトロ**に加え、**パパ活**（ぱぱかつ、ぱぱ活、逆援助、sugar daddy / sugar baby）、**おっぱぶ**（オッパブ、おっぱいぶ）、**ナンパ・出会い系**、**ロリコン・ショタコン**、**ビッチ・ヤリマン・種付け**、**オーラル**などを `INAPPROPRIATE_MESSAGE_KEYWORDS` に追加。
- **セキュリティブロック以外はユーザーフレンドリーなプレーンテキスト**
  - 絶対ブロック時の案内文を「ご入力いただいた内容にはお答えできかねます。お体の不調やお薬のご相談がありましたら、お気軽にメッセージをお送りください。」に変更。
- **UI に元入力を表示（正規化でひらがなにならないように）**
  - `basic_normalize_text()` によりカタカナ→ひらがな変換した結果がそのまま UI に表示されていた問題を修正。ユーザー発言としてセッションに追加する際は **正規化前の元入力**（`original_user_message` / `user_message`）を使用するように変更（`chat_handler.py` の Other ブロック、`chat_triage_follow_ups.py` の医薬的予防・不適切要求の 2 箇所）。

### 2026年2月8日（SRPリファクタリング・chat_handler移行・エラー表示改善）
- **SRP改善計画に基づく大規模リファクタリング完了**
  - **Phase 1（重複排除）**: app.pyのグローバル状態・セッション・ログ・入力判定を session_manager、request_logger、input_helpers、chat_response_service からの import に置換
  - **Phase 2（app.py責務分離）**: RequestSafeSession→`src/utils/request_safe_session.py`、port_utils→`src/utils/port_utils.py`、エラーハンドラー→`src/handlers/error_handlers.py`、Blueprint分割（main/admin/api/feedback）、チャットPOST処理→`src/handlers/chat_handler.py`（handle_chat_post）に移行
  - **Phase 3（candidate_scoring分割）**: medicine_classifiers、ingredient_utils、score_calculators、influenza_detector を新規作成・分割
  - **Phase 4（medicine_logic軽量化）**: text_formatter、generate_usage_notes→explanation_generator へ移管
  - **Phase 5（rule_based/counseling分割）**: kampo_logic（漢方証判定）、counseling_triage（相談トリアージ）、counseling_followup（フォローアップ質問）を新規作成・分割
- **chat_handlerへの不足インポート追加**: is_symptom_input、is_ambiguous_input、detect_language、select_symptoms_via_gpt、analyze_symptoms_and_medicine_type、rule_based_medicine_recommendation、log_medicine_logic_call、log_network_request、check_missing_attributes、generate_personalized_advice
- **妊娠・授乳時レッドフラッグ表示の改善**: 簡潔なメッセージから format_escalation_display による詳細HTML表示に統一
- **エラー時のUIメッセージ改善**: 技術的エラー内容（NameError等）を非表示にし、ユーザーフレンドリーな再試行案内を表示

### 2026年2月7日（候補医薬品キー正規化・主要解熱鎮痛薬推奨テスト修正）
- **候補医薬品のキー正規化モジュールの新規作成（SRP遵守）**
  - **`src/utils/candidate_normalizer.py`**: CSV由来の候補（製品名・成分・効能効果など日本語キー）をスコアリングロジック用の英語キー（product_name・ingredients・efficacyなど）に正規化する専用モジュールを追加
    - `normalize_candidate_for_scoring()`: 日本語キーから英語キーへのエイリアスを in-place で追加
    - 単一責務（キー名マッピングのみ担当）で設計
  - **`src/core/rule_based_recommendation.py`**: `calculate_final_score` 冒頭で `normalize_candidate_for_scoring()` を呼び出し、テスト・本番の両方で候補のキー形式を統一
- **主要解熱鎮痛薬の生理痛専用医薬品除外ルールの例外追加**
  - **カロナール・タイレノールの例外**: CSVの効能が「生理痛」のみでも、頭痛・発熱では一般用解熱鎮痛薬として推奨（アセトアミノフェン含有の一般医薬品として扱う）
  - **ロキソニン系の例外**: 同様に、頭痛・筋肉痛・発熱では一般用NSAIDsとして推奨（ロキソプロフェン含有のロキソニン製品として扱う）
  - **背景**: カロナールＡ・タイレノールＡ・ロキソニンＳ等は CSV で効能が「生理痛」のみと登録されているが、実際は頭痛・発熱・筋肉痛など幅広く使用される一般解熱鎮痛薬であるため
- **統合テストの修正**
  - **`test_inflammatory_pain_nsaids_preference`**: 乗り物酔い専用医薬品（セイブ等）を除外し、ロキソニン・イブプロフェン錠・トキワイブ等の一般解熱鎮痛NSAIDを優先して検証するよう改善
- **効果**: 統合テスト7件の失敗を解消（test_headache_acetaminophen_preference、test_inflammatory_pain_nsaids_preference、test_major_analgesics_recommended、test_roxonin_calonel_recommendation、test_stomach_concern_acetaminophen）。本アプリケーションへの性能への影響は最低限（正規化は候補ごとに1回の軽量なdict更新のみ）

### 2026年1月16日
- **オンボーディングUIの改善**
  - **スクロール対応の強化**: オンボーディングモーダルにスクロール機能を追加し、コンテンツが多い場合でも快適に閲覧可能に
    - モーダル全体に`max-height: 90vh`と`overflow-y: auto`を設定
    - スライドコンテンツに`flex: 1`と`min-height: 0`を設定し、適切なスクロール動作を実現
    - 詳細セクション（`.onboarding-details-content`）にスクロールバーのスタイリングを追加（薄いグリーンのスクロールバー）
  - **レスポンシブ対応の改善**: モバイル・タブレット・デスクトップで適切に表示されるよう改善
    - モバイル（768px以下）: `max-height: 85vh`、詳細セクション`max-height: min(200px, 35vh)`
    - タブレット（480px以下）: `max-height: 80vh`、詳細セクション`max-height: min(180px, 30vh)`
    - Flexboxレイアウトを活用し、コンテンツが適切に配置されるよう改善
  - **リンクボタンのスタイル追加**: アプリケーション資料へのリンクボタンに専用スタイルを実装
    - 青色のボタン（`#2196F3`）で、ホバー時に色が濃くなる（`#1976D2`）
    - ホバー時に軽く浮き上がるアニメーション効果
    - フォーカスリングを追加し、キーボード操作時の視認性を向上
    - レスポンシブ対応（モバイルではパディングとフォントサイズを調整）
- **イースターエッグ機能の説明スライド追加**
  - **多言語対応**: 日本語・英語・韓国語・中国語の4言語に対応
  - **説明内容**:
    - イースターエッグ機能の概要説明
    - 感謝メッセージ（「ありがとう」など）でパーティクル効果が表示される機能
    - 画面変形（「回転」「揺れる」などのキーワード）機能
    - 絵文字のみの送信時の特別な効果
    - 季節イベント対応（新年、クリスマスなど）の説明
  - **実装ファイル**: `static/js/main.js`（各言語のオンボーディングスライドデータに追加）
- **アプリケーション資料へのリンクスライド追加**
  - **β版のみ表示**: `isBetaOnly: true`フラグにより、β版の場合のみ表示されるスライドを実装
  - **リンク内容**:
    - 技術的資料（Google Driveへのリンク、URLは後で設定）
    - パワーポイント（Google Driveへのリンク、URLは後で設定）
    - 質疑応答（Google Driveへのリンク、URLは後で設定）
    - プロトタイプ（Marvel）: `https://marvelapp.com/prototype/350fehf6`
  - **多言語対応**: 日本語・英語・韓国語・中国語の4言語に対応
  - **アクセシビリティ**: 各リンクに適切な`aria-label`を設定
  - **実装ファイル**: `static/js/main.js`（各言語のオンボーディングスライドデータに追加）
- **β版判定ロジックの実装**
  - **判定方法**: ページタイトルに「β版」または「Beta」が含まれているかで判定
    - 日本語タイトルの場合: 「β版」を含むかチェック
    - 英語タイトルの場合: 「Beta」を含むかチェック
    - 翻訳データからも判定可能（`translations[currentLanguage].title`をチェック）
  - **フィルタリング機能**: β版でない場合は`isBetaOnly: true`のスライドを非表示
  - **スライド数の動的調整**: フィルタリング後のスライド数に基づいて、スライドナビゲーションを適切に動作
  - **実装ファイル**: `static/js/main.js`（`showOnboardingModal`関数内に実装）
- **効果**: オンボーディング体験が大幅に改善され、ユーザーがアプリケーションの機能をより理解しやすくなった。特に、イースターエッグ機能や資料へのアクセス方法が明確になり、ユーザーエンゲージメントが向上

### 2026年1月14日
- **シーズン対応UI機能の拡張（バレンタイン・節分・冬の一般シーズン対応）**
  - **バレンタインシーズン対応UI機能の追加**: 2月14日に自動的にバレンタイン装飾を表示する機能を実装
    - **右側画像**: choco.png（チョコレート）、heart.png（ハート）、loveletter.png（ラブレター）からセッションごとにランダム選択
    - **左側画像**: lgbt.png、lgbt2.png、student.png、valentine.pngから重み付きランダム選択（均等な出現率）
    - **セッション固定**: ランダム画像はセッションごとに固定され、セッション内で一貫性を保持
    - **多様性への配慮**: LGBT関連画像を含む多様なバレンタイン装飾を提供し、すべてのユーザーに配慮した設計
    - **実装ファイル**: `season_manager.py`（SEASON_CONFIGに`valentine`エントリを追加）、`static/img/winter/valentine/`（バレンタイン画像）
  - **節分シーズン対応UI機能の追加**: 2月1日～2月3日に自動的に節分装飾を表示する機能を実装
    - **右側画像**: oni.png（鬼）を表示
    - **左側画像**: mame.png（豆）、ehoumaki.png（恵方巻）、kanabou.png（金棒）からセッションごとにランダム選択
    - **セッション固定**: ランダム画像はセッションごとに固定され、セッション内で一貫性を保持
    - **実装ファイル**: `season_manager.py`（SEASON_CONFIGに`setubun`エントリを追加）、`static/img/winter/setubun/`（節分画像）
  - **冬の一般シーズン対応UI機能の追加**: 1月8日～1月31日、2月4日～2月13日、2月15日～2月28日に自動的に冬の一般シーズン装飾を表示する機能を実装
    - **右側画像**: wintertree.png（冬の木）、winter_snow.png（雪景色）からセッションごとにランダム選択
    - **左側画像**: snowman.png（雪だるま）、can_coffee.png（温かいコーヒー）からセッションごとにランダム選択
    - **セッション固定**: ランダム画像はセッションごとに固定され、セッション内で一貫性を保持
    - **実装ファイル**: `season_manager.py`（SEASON_CONFIGに`winter`エントリを追加）、`static/img/winter/general/`（冬の一般画像）
  - **シーズン管理システムの拡張**: 既存のクリスマス・正月シーズンに加え、節分・バレンタイン・冬の一般シーズンに対応
    - **優先順位の実装**: イベント日が重複する可能性があるため、優先順位の高い順にチェック（クリスマス > 正月 > バレンタイン > 節分 > 冬の一般 > 春 > 夏 > 秋）
    - **画像のalt属性マッピング**: アクセシビリティ向上のため、すべての画像に適切なalt属性を設定
    - **重み付きランダム選択**: バレンタインの左側画像など、重み付きランダム選択に対応
    - **効果**: 季節感のあるUIでユーザー体験が向上し、多様なイベントに対応した装飾により、より親しみやすいシステムになった

### 2026年1月13日
- **緊急避妊薬対応機能の追加**
  - **性被害を含む緊急避妊薬に関する質問への適切な対応**: レイプ・強姦・性被害などのキーワードを検出し、専用のプロンプトで応答
  - **72時間以内の服用の重要性を強調**: 緊急避妊薬の有効性と時間制約を明確に説明
  - **対面診療とオンライン診療の案内**: 2019年より可能になったオンライン診療を含む2つの取得方法を案内
  - **心理的サポートと警察への相談の案内**: 性暴力被害者支援センターや警察への相談を案内
  - **マークダウン記号の削除**: 応答生成時に`**`、`*`、`__`、`_`などのマークダウン記号を削除し、通常のテキストで返信
  - **重複メッセージの防止**: `counseling_summary`で`counseling_response`と`content`の両方がある場合、`counseling_response`のみを返すように改善
  - **表記ゆれへの対応**: 「避妊出来なかった」「避妊出来ません」などの表記ゆれに対応

### 2026年1月3日（スコアリングシステムの根本的改善）
- **主要解熱鎮痛薬のボーナス強化**
  - **カロナールA/タイレノールA**: ボーナス +0.8（改善前: +0.6）
    - 頭痛・発熱に対する第一選択として推奨
    - 胃腸への負担が少なく、安全性が高い
  - **ロキソニンS（頭痛・発熱）**: ボーナス +0.6（改善前: +0.4）
    - 頭痛・発熱に対して効果的
  - **ロキソニンS（筋肉痛・内服）**: ボーナス +0.6（改善前: +0.5）
    - 抗炎症作用があり、筋肉痛に効果的
  - **ロキソニンS外用薬（筋肉痛）**: ボーナス +0.8（改善前: +0.6）
    - テープ・パップ・ゲル剤などの外用薬を優先
    - 局所的な作用で、全身的な副作用リスクが低い
    - 胃腸への負担がない
- **主要解熱鎮痛薬の基本スコア底上げ**
  - 基本スコアが0.55未満の場合、0.55に底上げ
  - これにより、主要解熱鎮痛薬がより適切に推奨される
- **調整スコア上限の引き上げ**
  - 主要解熱鎮痛薬の調整スコア上限を0.8に引き上げ（改善前: 0.6）
  - 強化されたボーナスが適切に反映される
- **単一症状に対する総合感冒薬のペナルティ強化**
  - 単一症状の場合、総合感冒薬に-0.7のペナルティを適用（改善前: ボーナス0.0、ペナルティなし）
  - 基本スコアも-0.1減少
  - これにより、単一症状時には特化した解熱鎮痛薬が優先的に推奨される
- **症状カテゴリ間優先表の更新**
  - **発熱**: 総合風邪薬へのペナルティを-0.3から-0.5に強化
  - **頭痛**: 総合風邪薬へのペナルティを-0.2から-0.5に強化
  - **筋肉痛**: 新規追加、総合風邪薬に-0.5のペナルティ、外用薬（皮膚）に+0.2のボーナス

### 2026年1月2日（単一症状スコアリング改善）
- **同義語マッピングの拡張**
  - **「たん」「痰」の同義語拡張**: 名詞だけでなく、状態表現も含む包括的な同義語マッピングを実装
    - 基本表現: 「たん」「痰」「タン」「たんが出る」「痰が出る」「喀痰」「咳痰」
    - 状態表現: 「からむ」「絡む」「のどにからむ」「喉に絡む」「ゼロゼロ」「ゼーゼー」「切れにくい」
    - これにより、ユーザーの様々な表現パターンに対応し、症状を正確に抽出
- **誤検知防止機能の実装**
  - **ブラックリストによる局所判定**: 「たん」が「簡単」「負担」「短期間」などの単語の一部として誤検知されることを防止
    - ブラックリスト: 「簡単」「負担」「短期間」「ビタン」「タンパク質」「担当」「単独」「単純」「短縮」など
    - 座標計算による局所判定: 見つかった「たん」の出現位置周辺のみをチェックし、テキスト全体ではなく局所的に判定
    - これにより、「小粒で簡単に飲み込める錠剤です。のどの痛み、たん、せきに効きます。」のような場合でも、効能として書かれている「たん」を正しく認識
- **効能特異性スコア計算の改善**
  - **0.5への底上げ**: 効能テキストに症状が含まれている場合、効能特異性スコアを最低0.5に保証
    - 単純包含チェックと単語境界チェックの両方を使用して正確性を確保
    - ブラックリストチェックにより誤検知を防止
- **症状特異性ペナルティの緩和**
  - **効能特異性0.5以上でペナルティなし**: 効能に症状が明記されている場合（効能特異性 >= 0.5）、症状カテゴリ間優先表のペナルティと複合薬ペナルティを適用しない
    - 効能に症状が含まれているということは、その医薬品が症状に対して適切であることを示しているため
    - これにより、適切な医薬品のスコアが向上し、最適度スコアがより正確に反映される（約54% → 約65%）
- **去痰成分ボーナスの実装**
  - **西洋薬の去痰成分**: カルボシステイン、ブロムヘキシン、アンブロキソール、グアヤコールスルホン酸カリウムなど → ボーナス+0.15
  - **漢方薬の去痰成分**: 麦門冬湯（バクモンドウ）、清肺湯、五虎湯、竹茹温胆湯、半夏厚朴湯など → ボーナス+0.10
  - **鎮咳成分との併用時**: 強力な鎮咳成分（ジヒドロコデイン、コデイン、デキストロメトルファン、ノスカピン）が含まれている場合、ボーナスを-0.05減
  - **薬学的安全性**: 「たん」を出したい時、強力な咳止め成分が入っていると咳反射が抑制されて逆にたんが出せなくなるリスクを考慮
- **技術的改善**
  - **浮動小数点比較の改善**: `efficacy_specificity == 0.0`のような直接比較を避け、イプシロン比較（`< 0.0001`）を使用して計算誤差による意図しない挙動を防止
  - **キャッシュ機能**: 同義語マッピングとブラックリストのキャッシュを実装し、パフォーマンスを向上
  - **エラーハンドリング強化**: 各関数に`try-except`ブロックを追加し、エラー時は安全側に倒す（デフォルト値を返す）
  - **デバッグログ**: DEBUGモード時のみ詳細ログを出力し、本番環境でのパフォーマンスへの影響を最小化
- **症状抽出リストの拡張**
  - `select_symptoms_via_gpt`関数の症状リストに「たん」「痰」「せき」を追加し、より正確な症状抽出を実現
- **テストケースの追加**
  - `tests/test_scoring_utils.py`を新規作成し、包括的なテストケースを実装（12個のテストケース、すべてパス）
    - 同義語マッピングのテスト
    - 効能特異性スコア底上げのテスト
    - ブラックリスト誤検知防止のテスト
    - 局所判定のテスト
    - 単語境界チェックのテスト
    - 浮動小数点比較のテスト
    - 去痰成分ボーナスのテスト
    - 鎮咳成分ペナルティのテスト
    - 漢方薬の去痰成分ボーナスのテスト
    - エラーハンドリングのテスト
    - パフォーマンステスト
    - 統合テスト

### 2026年1月1日（元旦）
- **UI/UX大幅改善：高齢者向けアクセシビリティ機能の実装**
  - **セクション折りたたみ機能**: 推奨結果の各セクションを折りたたみ可能にし、情報の優先順位を明確化
    - 重要な情報（個別アドバイス、推奨医薬品、使用上の注意、治療中の方へ）はデフォルトで展開
    - 補足情報（曖昧入力警告、詳細症状分析）は折りたたみ可能
    - 各医薬品セクション内の「【使ってはいけない人】」「【服用時の注意】」も折りたたみ可能
    - モダンでシンプルなデザイン（点線ボーダー、中程度の影、角丸、テーマカラーボタン）
    - ボタンにはテキストラベルとアイコンを併記し、高齢者にも分かりやすく
    - イベントリスナーの重複追加を防止し、動作の軽量化を実現
  
  - **音声読み上げ機能**: Web Speech APIを使用した全文読み上げ機能
    - 推奨結果の下部にメインボタンを配置（チャットメッセージエリアを小さくしない設計）
    - 再生/停止のトグル機能
    - 進行状況表示（プログレスバーとパーセンテージ）
    - 読み上げ速度の調整機能
  
  - **文字サイズ調整機能**: 4段階の文字サイズ調整（小・標準・大・特大、最大150%）
    - CSS変数を使用した動的なフォントサイズ制御
    - `rem`単位による`padding`と`margin`の自動スケーリング
    - フォントサイズに応じた`line-height`の動的調整
    - ユーザー設定の`localStorage`への保存
  
  - **視覚的階層の改善**:
    - 見出しサイズの拡大（h4: 20px、h5: 18px）
    - 行間と余白の拡大（`line-height: 1.8`、`margin: 30px`）
    - 警告の色分け（危険=赤、注意=黄/オレンジ、情報=青/緑）
    - WCAG AA準拠のコントラスト比（4.5:1以上）を確保
  
  - **キーボード操作対応**:
    - Tab順序の最適化
    - Enter/Spaceキーでの折りたたみ操作
    - フォーカスリングの視認性強化（`outline-offset`を使用）
    - 高コントラストモード対応
  
  - **UDフォント対応**: ユニバーサルデザインフォント（BIZ UDPGothic、Hiragino Kaku Gothic ProN、Yu Gothic）を優先
  - **WCAG AA準拠**: すべての色のコントラスト比を4.5:1以上に確保、ARIA属性の適切な使用、44px×44px以上のタッチターゲットサイズ

### 2025年12月31日（方言対応機能の実装・謹賀新年縦書きアニメーション追加・緊急事案検出の誤検知防止機能・ユーザーメッセージ重複表示の修正・症状検出の改善・カウンセリングフロー返信の改善・成分重複チェック機能・曖昧入力検出の改善・総合感冒薬推奨ロジックの強化・カテゴリ多様性の確保・アドバイス生成の改善・管理画面UI改善）

- **方言対応機能の実装**
  - **全国の方言を標準語に変換する機能を実装**: 関西弁、東北弁、九州弁、名古屋弁、和歌山弁など、主要な方言表現を標準語に変換し、症状を正確に抽出
    - **方言辞書の構築**: `config/dialect_dictionary.py`に100件以上の方言表現を定義
      - **疲労系（15件）**: えらい、しんどい、きつい、こわい、おぞい、なまら、だるか、ゆるくない、がっくりくる、へたる、てんご、よだきい、たいぎい、せつない、ぬくたい、ひどい、めんどい、ばてる、ふらふらする
      - **痛み・炎症・皮膚症状系（30件）**: にえる、かじる、いびる、はしる、ひりひりする、ずきずきする、ちくちくする、いがらっぽい、ひやこい、しゃっこい、かいい、はれぼったい、あおじ、くろにえ、ちみ切る、いもじ、おっきょい、ちんちん、ひりつく、うずく、ひりひり、しみる、じくじく、ぐちゅぐちゅ、ぱんぱん、じんじん、がんがん、しくしく、きりきり、いてぐい
      - **風邪・消化器・内臓系（25件）**: はなげを出す、おきやま、かぜひき、むかむかする、むかつく、えずく、くだる、ゆるい、はる、つまる、きばる、こみ上げる、むせる、ぜーぜー、いがいが、ひきつけ、のぼせる、おなかがおどる、いたむ、くだし、げりぴー、もたれる、胸がやける、つかえる、いがつく
      - **強度・頻度・状態表現（25件）**: めっちゃ、めっちゃめちゃ、でら、どえりゃあ、ばり、がばい、なまら、わっぜ、ごっつ、むっちゃ、えらい、ほんまに、だいぶ、そうとう、ようけ、ちょこっと、ちょびっと、ぼちぼち、ずっと、ときどき、しょっちゅう、いきなり、がんがん、びっしょり、からから
    - **非破壊的変換機能**: 方言を複数の症状候補に展開し、重み付きで症状を抽出
      - **重みの正規化**: 展開前の重みを保存し、展開後の重みの合計が1.0になるように正規化（症状過多判定のバイアスを排除）
      - **例**: 「にえる」（和歌山弁）→打ち身0.4、あざ0.4、筋肉痛0.2
    - **重症度タグの抽出**: 強調語から重症度（重度、やや重度、中等度、軽度、やや軽度）を自動抽出
      - **escalation_scoreの加算機能**: 複数の強調語が検出された場合、重み付き加算で緊急性を判定
        - 重度×2.0、やや重度×1.5、中等度×1.0、軽度×0.5、やや軽度×0.25
        - 閾値4.0（設定可能）を超えた場合は受診勧奨フラグを立てる
    - **パフォーマンス最適化**:
      - **Aho-Corasickアルゴリズム**: 多パターン同時照合によるO(n)の高速処理（pyahocorasickライブラリを使用、オプション）
      - **方言インデックス**: 入力テキストからマッチする可能性のある方言を絞り込んでから正規表現を適用
      - **グローバルリソースの初期化**: アプリ起動時に一度だけオートマトンとインデックスを構築し、リクエストごとの構築処理を回避
      - **re.Scannerによる一括スキャン**: 正規表現の高速化
    - **診断名のみ判定の改善**: `is_diagnosis_only`関数で、感情・状態に関する否定語（あかん、つらい、やばいなど）を含む場合は文字数に関わらず診断名のみと判定しない例外ルールを追加
    - **症状検出の改善**:
      - `comprehensive_symptom_list`に外傷関連症状（打ち身、打撲、あざ、青あざ、内出血、炎症）を追加
      - 前処理ロジックで「打ち身」「打撲」「あざ」「炎症」「にえる」などのキーワードを検出し、`inferred_symptoms`に追加
      - 和歌山弁の「にえる」は「打ち身」「打撲」「あざ」として推測
      - プロンプトに「打ち身になっている」「打撲になった」「あざができた」などの表現から症状を抽出する指示を追加
    - **実装ファイル**:
      - `config/dialect_dictionary.py`: 方言辞書の定義（896行）
      - `scoring_utils.py`: 方言変換関数（`convert_dialect_to_standard`、`basic_normalize_text`など）
      - `rule_based_recommendation.py`: 方言変換の統合
      - `medicine_logic.py`: 症状検出の改善（打ち身、打撲、あざ、炎症の追加）
      - `tests/test_dialect_conversion.py`: 方言変換のテスト（275行）
    - **効果**: 全国のユーザーが方言で症状を入力しても、正確に症状を抽出し、適切な医薬品を推奨可能に

- **「謹賀新年」縦書きアニメーション機能の追加**
  - **新年・大晦日イースターエッグの拡張**: 新年・大晦日のトリガーで、画面中央に「謹賀新年」を縦書きで4文字表示する美しいアニメーションを実装
    - **デザイン**: 明朝体フォント（Hiragino Mincho ProN、Yu Minchoなど）を使用した上品な縦書き表示
    - **グラデーション**: ゴールドから赤への美しいグラデーション（#d4af37 → #ffd700 → #c92a2a）
    - **アニメーション**: 0.3倍から1.15倍へ拡大し、バウンス効果で1.0倍に収まる滑らかなアニメーション（1.5秒）
    - **文字サイズ**: PC 7rem、タブレット 5rem、スマートフォン 4rem（パフォーマンス最適化済み）
    - **パフォーマンス最適化**: 
      - GPU加速（translate3d、translateZ(0)）による滑らかな描画
      - will-changeの最適化（アニメーション完了後に自動削除）
      - containプロパティによるレンダリング範囲の制限
      - backface-visibility: hiddenによる3D変換の最適化
      - text-shadowを4つから2つに削減、filter: drop-shadowを削除
    - **表示タイミング**: 新年・大晦日のトリガー時に、花火やパーティクル効果と同時に表示（5秒間）
    - **トリガーキーワードの追加**: 「あけおめことよろ」を新年トリガーに追加
    - **実装ファイル**: 
      - `static/js/easter-eggs.js`（showKeigaShinnen関数、triggerNewYear関数、triggerNewYearsEve関数）
      - `static/css/easter-eggs.css`（.keiga-shinnen-text、.keiga-char、アニメーション定義）

- **緊急事案検出の誤検知防止機能の実装**
  - **医療用語の除外**: 医療用語（症状名・疾患名）に含まれる「炎」を除外する機能を実装
    - 50以上の医療用語を定義（口内炎、胃炎、腸炎、結膜炎、咽頭炎、関節炎、皮膚炎など）
    - キーワードの前後30文字の文脈を確認し、医療用語が含まれている場合は除外
  - **一般的な表現の除外**: 火曜日、火を使う、煙草、鼻血、歯茎からの出血、生理の出血、血圧、血糖値などの一般的な表現を除外
  - **医療相談の文脈判定**: 医療相談を示す表現（症状、薬、相談、教えてなど）を検出し、医療相談の文脈では特定のキーワードを除外
    - 「血」「出血」「救急車」「119番」などは医療相談の文脈では除外
    - 「助けて」系は、相談の文脈（「相談」「教えて」「どうすれば」など）がある場合のみ除外
  - **文脈に基づく判定**: 
    - 「車を」「車が」が「救急車を」「救急車が」の一部として使われている場合は除外
    - 「血が出ている」系は、自分の症状として使われている場合は除外（「人」が含まれていない場合）
  - **効果**: 誤検知を大幅に削減し、UXを向上（医療相談の文脈では緊急事案として誤検出されない）

- **ユーザーメッセージの重複表示の修正**
  - **重複チェック機能の追加**: 診断名検出時とカウンセリングフローで、ユーザーメッセージが重複して追加される問題を修正
    - 診断名検出時にユーザーメッセージを追加した後、カウンセリングフローでは重複チェックを確実に機能させる
    - DB側でも重複チェックを実施し、確実に重複を防止
  - **効果**: ユーザー側のUIでメッセージが2重に表示される問題を解決

- **症状検出の改善**
  - **SYMPTOM_KEYWORDSの大幅拡充**: `config/keywords.py`の`SYMPTOM_KEYWORDS`に以下の症状を追加
    - 口腔系: 口内炎、口の痛み、歯痛、歯が痛い
    - 皮膚系: かゆみ、痒み、発疹、湿疹、蕁麻疹
    - 眼科系: 目の疲れ、目が疲れる、目のかゆみ、目がかゆい、目の充血
    - 耳鼻科系: 耳鳴り、耳の痛み、耳が痛い
    - 女性特有: 生理痛、月経痛、月経不順
    - その他: 吐き気、嘔吐、めまい、ふらつき、疲労感、倦怠感、だるさ
  - **効果**: より多くの症状を正確に検出し、適切なカウンセリング返信を提供

- **カウンセリングフローの返信の改善**
  - **general_symptomタイプの追加**: 症状が検出されている場合、`general_symptom`という新しいタイプを使用
    - 症状への理解を示す
    - 共感的なメッセージを提供
    - 市販薬の可能性を伝える
    - 必要に応じて医師への相談の重要性を伝える
    - 具体的なアドバイスを提供
  - **効果**: 症状が明確に報告されている場合、「不明確」という不適切な返信を避け、適切なアドバイスを提供

- **管理画面UI改善**
  - **緊急メッセージ表示の改善**: 緊急事案メッセージ（emergency-response-modern）と危機対応メッセージ（crisis_support）の表示スタイルを統一し、簡潔で読みやすい形式に変更
    - 緊急事案メッセージ: 「🚨 緊急事案」インジケーターと簡潔なヘッダーテキストを表示
    - 危機対応メッセージ: 「🚨 危機対応」インジケーターと簡潔なメッセージ内容を表示
    - HTMLがコードそのまま表示される問題を修正し、正しくレンダリングされるように改善（`static/js/main.js`、`static/js/admin_chat.js`）
  - **キューアイテムのUI統一**: 緊急事案キューアイテム（emergency-queue-item）と危機対応キューアイテム（crisis-queue-item）のスタイルを統一
    - パルスアニメーションを削除し、視覚的な混乱を防止（`static/css/admin_chat.css`）
    - 外枠の二重表示問題を修正（`.queue-accordion-item.crisis-queue-item .queue-accordion-header`のborderを削除）
    - ヘッダーのスタイルを統一（背景色: #ffebee、境界線スタイルを統一）
  - **バッジ表示の改善**: emergency-badgeとcrisis-badgeのスタイルを統一
    - 同じサイズ・形状でピカピカアニメーション（crisis-blink）を適用
    - バッジのデザインを統一（背景色: var(--color-danger)、padding: 4px var(--spacing-sm)、border-radius: var(--radius-full)、animation: crisis-blink 1s infinite）
    - インラインスタイルを削除し、CSSクラスを使用するように変更（`static/js/admin_chat.js`）
  - **アクティブセッション表示の改善**: アクティブセッションをキュー一覧から独立した項目として表示する代わりに、各キューアイテムの右上に緑色のマーク（12px × 12px）を表示
    - アクティブセッションかどうかを自動判定し、マークを表示（`currentSessionId`と`item.session_id`を比較）
    - 複数のアクティブセッションがある場合でも、各アイテムに個別にマークが表示される
    - マークのスタイル: 緑色（#28a745）、白色の境界線（2px solid white）、影付き（box-shadow: 0 2px 4px rgba(0,0,0,0.2)）で視認性を向上
    - z-index: 10を設定して、確実に表示されるように改善
    - `renderCurrentSession`関数を簡略化し、データ保持のみを行うように変更（`static/js/admin_chat.js`）

- **成分重複チェック機能の実装**
  - **リスク成分マスターの定義**: `RISK_INGREDIENTS_OVERLAP`辞書に30種類のリスク成分を定義
    - **鎮痛成分（Red）**: アセトアミノフェン、エテンザミド、イブプロフェン、アスピリン、ロキソプロフェン、イソプロピルアンチピリン、メフェナム酸
    - **抗ヒスタミン薬第一世代（Yellow）**: クロルフェニラミン、ジフェンヒドラミン、クレマスチン、プロメタジン
    - **鎮咳成分**: デキストロメトルファン（Yellow）、ジヒドロコデイン（Red）、コデイン（Red）
    - **その他**: カフェイン（Yellow）、プソイドエフェドリン（Red）、メチルエフェドリン（Yellow）、トラネキサム酸（Yellow）、ビタミンA/D（Yellow）、アルミニウム/マグネシウム（Yellow）、去痰成分（Yellow）、抗コリン成分（Red/Yellow）、鎮静成分（Red/Yellow）など
  - **集合演算による高速マッチング**: Pythonの`set`演算を使用して、効率的に成分重複を検出（`check_ingredient_overlap`関数）
  - **深刻度レベル別の警告システム**: 
    - **Red（重複禁止）**: 過剰摂取のリスクが明白な成分（例：アセトアミノフェン×2）
      - アイコン: 🚨、ボーダー色: #d32f2f（赤）、メッセージ: 「過剰摂取のリスクがあります。同時に服用しないでください」
    - **Yellow（注意）**: 副作用が強まる成分（例：抗ヒスタミン薬×2→強い眠気）
      - アイコン: ⚠️、ボーダー色: #f57c00（オレンジ）、メッセージ: 「同じ成分が含まれていますので、併用時は副作用にご注意ください」
    - **Blue（情報）**: 重複は問題ないが注意喚起が必要な成分
      - アイコン: ℹ️、ボーダー色: #1976d2（青）、メッセージ: 「同じ成分が含まれていますので、用法用量をご確認ください」
  - **最高深刻度の判定**: 複数の重複がある場合、最も深刻なレベル（Red > Yellow > Blue）を採用
  - **表示タイミング**: 医薬品推奨結果の表示時に、推奨リスト内の医薬品間の成分重複をチェック

- **曖昧入力検出の改善**
  - **改善された判定基準**: `is_ambiguous_input`関数を実装
    - **症状数の確認**: 抽出された症状数が3つ以上かチェック
    - **入力文字数の確認**: 入力文字数が短い場合（20文字未満）は曖昧と判定
    - **NLU判定の確認**: NLUの信頼度が低い場合（0.5未満）や「推論」された症状が多い場合は曖昧と判定
    - **明示的な症状キーワードの確認**: 具体的な症状を明示した場合は曖昧と判定しない
  - **警告メッセージの表示**: 曖昧な入力が検出された場合、推奨結果の最上部（「💡 あなたに合わせたアドバイス」の前）に警告メッセージを表示
    - 警告タイトル: 「症状が多い場合のご案内」
    - 警告内容: 「複数の症状が検出されました。より適切な医薬品を推奨するために、最も気になる症状や症状の詳細について教えていただけると助かります。」
    - スタイル: 青色の背景色とボーダーで表示（情報提供のトーン）

- **総合感冒薬推奨ロジックの強化**
  - **複数症状時のボーナス強化**: `SYMPTOM_PATTERN_OPTIMIZATION`辞書で「のど痛み+発熱」パターンの総合感冒薬ボーナスを+0.55以上に強化
  - **3症状以上で追加ボーナス**: `calculate_final_score`関数で3症状以上の場合、総合感冒薬に追加で+0.15のボーナスを付与
  - **効果**: 複数症状時に総合感冒薬が優先的に推奨され、より適切な医薬品選択が可能に

- **外用薬（のど）のスロット確保**
  - **スロット方式の実装**: `ensure_ingredient_diversity`関数で、のどの痛みがある場合に3位以内に外用薬を必ず1つ確保
  - **ペナルティの廃止**: 外用薬へのペナルティ（-0.30）を廃止し、スロット方式に変更
  - **補助療法としての説明**: 外用薬の推奨理由に「内服薬と併用して喉を直接ケアする補助的な製品」としての説明を追加
    - メッセージ: 「この外用薬は、内服薬と併用して使うことで、喉の痛みをより和らげることができます。」

- **カテゴリ多様性の確保**
  - **弱点補完ロジック**: `ensure_ingredient_diversity`関数で、最初の推奨医薬品の「弱点」を補うカテゴリを選択
    - 例: 総合感冒薬が1位の場合、2位は外用薬（のど）や漢方薬を優先的に選択
  - **症状に応じた優先順位**: 症状パターンに応じて最適なカテゴリの組み合わせを選択
  - **効果**: 複数症状時に2種類以上のカテゴリを確保し、より多様な推奨が可能に
- **単一症状時の3つの医薬品推奨保証機能（2026年1月3日追加）**
  - **効能効果に症状が含まれている候補を優先的に追加**: `ensure_ingredient_diversity`関数内で、`candidates`から追加の候補を取得する際に、効能効果に症状が含まれている候補を優先的に考慮
    - 優先度の高い候補（効能効果に症状が含まれている）とその他の候補を分けて処理
    - 優先度の高い候補から順に追加を試みる
    - 単一症状（発熱のみ、痰・たんのみなど）と複数症状の両方に対応
  - **除外ロジックをスキップして強制的に追加**: 除外ロジックで除外されても、効能効果に症状が含まれている候補は強制的に追加
    - 単一症状用と複数症状用の両方に適用
    - 「たんが絡みます」などの単一症状でも、効能効果に「たん」「痰」「去たん」「去痰」が含まれている候補を優先的に追加
  - **`filter_by_efficacy_symptom_match`の適用強化**: すべての再追加処理で`filter_by_efficacy_symptom_match`を適用し、不適切な候補を除外
  - **効果**: 単一症状でも常に3つの適切な医薬品が推奨され、ユーザーに選択肢を提供

- **アドバイス生成の改善**
  - **ユーザー入力文の組み込み**: `generate_personalized_advice`関数に`user_text`パラメータを追加
  - **プロンプトの改善**: ChatGPTにユーザーの入力文を使用して、なぜその医薬品が推奨されたのかの根拠を説明させる
  - **効果**: ユーザーの入力文に基づいた、より納得感の高いアドバイスを生成

- **イースターエッグ機能の大幅拡張（特別イベント系の追加）**
  - **13種類の特別イベントに対応**: 新年、誕生日、クリスマス、ハロウィン、バレンタイン、ホワイトデー、七夕、お盆、こどもの日、母の日、父の日、敬老の日、大晦日の13種類のイベントに対応
  - **新年イースターエッグ**: 「あけましておめでとう」「良いお年を」「謹賀新年」「ことより」「あけおめ」など、年賀状用語（賀正、迎春、初春）を含む多数のトリガーに対応。花火アニメーション + 新年パーティクル（🎊、🎉、🎈、✨、⭐、🌟、💫、🎁）が表示されます
  - **誕生日イースターエッグ**: 「誕生日」「お誕生日」「ハッピーバースデー」などに対応。ケーキや風船のパーティクル（🎂、🎁、🎈、🎉、🎊、✨、⭐、🌟、💫、🎀）が表示され、風船は上に、ケーキやプレゼントは下に落ちるアニメーション
  - **クリスマスイースターエッグ**: 「メリークリスマス」「クリスマス」「クリスマスイブ」などに対応。雪アニメーション + クリスマスパーティクル（🎄、🎅、🎁、⭐、🌟、✨、💫、🔔、❄️）が表示されます
  - **ハロウィンイースターエッグ**: 「ハッピーハロウィン」「ハロウィン」「トリックオアトリート」などに対応。ハロウィンパーティクル（🎃、👻、🦇、🕷️、🕸️、💀、☠️、🧙、🧛、🧟）が表示されます
  - **バレンタインイースターエッグ**: 「バレンタイン」「バレンタインデー」「ハッピーバレンタイン」などに対応。ハート系パーティクル（💝、💕、💖、💗、💓、💞、💟、❤️、💘、🌹）が表示されます
  - **ホワイトデーイースターエッグ**: 「ホワイトデー」「ハッピーホワイトデー」などに対応。ホワイトデーパーティクル（🤍、💝、🎁、💕、💖、💗、💓、💞、💟、❤️）が表示されます
  - **七夕イースターエッグ**: 「七夕」「たなばた」「七夕祭り」などに対応。星系パーティクル（🎋、⭐、🌟、✨、💫、🌠）が表示されます
  - **お盆イースターエッグ**: 「お盆」「お盆休み」などに対応。お盆パーティクル（🕯️、🏮、🎐、✨、💫）が表示されます
  - **こどもの日イースターエッグ**: 「こどもの日」「子供の日」などに対応。こどもの日パーティクル（🎏、🎎、🎌、🎊、🎉、🎈、🎁、✨、⭐、🌟）が表示されます
  - **母の日イースターエッグ**: 「母の日」「ハッピーマザーズデー」などに対応。花系パーティクル（💐、🌷、🌹、🌺、🌸、🌻、🌼、💕、💖、💗）が表示されます
  - **父の日イースターエッグ**: 「父の日」「ハッピーファザーズデー」などに対応。父の日パーティクル（👔、🎁、🍺、🍻、🎉、🎊、💝、💕、💖、💗）が表示されます
  - **敬老の日イースターエッグ**: 「敬老の日」などに対応。敬老の日パーティクル（👴、👵、🌻、🌷、🌹、💐、💝、💕、💖、💗）が表示されます
  - **大晦日イースターエッグ**: 「大晦日」「年越し」「良いお年を」などに対応。大晦日パーティクル（🎊、🎉、🎈、✨、⭐、🌟、💫、🎁）が表示されます。「謹賀新年」縦書きアニメーションも同時に表示されます
  - **トリガーキーワードの大幅拡充**: 各イベントに対して、敬語形・カジュアル形、ひらがな・カタカナ・漢字のバリエーション、英語のバリエーション（wishes、greetingsなど）、関連表現を含む多数のトリガーに対応
    - 新年: 「良いお年を」「よいおとしを」「謹賀新年」「きんがしんねん」「賀正」「迎春」「初春」「ことより」「あけおめ」など、年賀状用語を含む30以上のトリガー
    - 誕生日: 「誕生日」「お誕生日」「ハッピーバースデー」「ハッピーバースデイ」「happy birthday to you」「bday」など、20以上のトリガー
    - クリスマス: 「メリークリスマス」「クリスマスイブ」「ハッピークリスマス」「merry xmas」「happy holidays」「season's greetings」など、20以上のトリガー
    - ハロウィン: 「ハッピーハロウィン」「トリックオアトリート」「トリック・オア・トリート」「trick-or-treat」など、15以上のトリガー
    - その他のイベントも同様に多数のトリガーに対応
  - **各イベント専用のパーティクル効果**: イベントに応じた適切な絵文字を使用したパーティクル効果を実装
  - **お祝いメッセージ**: 各イベントに応じた適切なお祝いメッセージを表示（ランダムに3種類から選択）
  - **安全性の確保**: 医療用語が含まれる場合は通常の相談処理にフォールバック
  - **実装ファイル**: `static/js/easter-eggs.js`に`SPECIAL_EVENT_TRIGGERS`を追加し、各イベント用のアニメーション関数を実装

- **薬剤師要請機能の改善**
  - **AI自動応答OFFの確実な適用**: 薬剤師要請後、AI自動応答が確実にOFFになるように修正
    - **問題**: 薬剤師要請後もLLMトリアージが実行され、AI自動応答がONのままになっていた
    - **修正**: `ai_auto_reply`フラグのチェックをLLMトリアージの前に移動（`app.py`の1014行目の後）
    - **効果**: 薬剤師要請後は、LLMトリアージを実行せず、確実にAI自動応答がOFFになる
  - **手動返信待ちキューの重複防止**: 同じセッションが2つ表示される問題を修正
    - **問題**: 薬剤師要請時に`admin_request`がキューに追加され、その後ユーザーがメッセージを送信すると再度キューに追加されていた
    - **修正**: `ai_auto_reply`がOFFの時にキューに追加する前に、既存の`admin_request`をチェック（`app.py`の1084-1110行目）
    - **効果**: 既に`admin_request`がキューにある場合は、新しいメッセージを追加せずにスキップし、重複を防止
  - **確認メッセージの毎回送信**: 薬剤師要請中にユーザーがメッセージを送信するたびに確認メッセージを送信
    - **改善**: 薬剤師要請中（`admin_request`がTrue）は、ユーザーがメッセージを送信するたびに「メッセージを受け付けました。薬剤師が確認中です。しばらくお待ちください。」という確認メッセージを送信
    - **効果**: ユーザーに「メッセージが届いている」ことが明確に伝わり、待機中の不安を軽減
    - **実装**: `app.py`の1121-1175行目で、薬剤師要請中は毎回確認メッセージを送信するように変更

### 2025年12月30日（眠気と不眠の区別機能・眠気カウンセリングフロー・カフェイン剤推奨機能の改善・使用上の注意生成の改善・治療中キーワード検出機能）

- **治療中キーワード検出機能の実装**
  - **治療中キーワードの検出**: `config/keywords.py`の`TREATMENT_KEYWORDS`を使用して、ユーザー入力から治療中を示すキーワードを検出
    - キーワード例: 「薬を飲んでいる」「通院中」「治療中」「診療中」「処方薬」「高血圧です」「糖尿病です」「心臓病です」「緑内障です」など
  - **user_attributesへの設定**: 治療中キーワードが検出された場合、`user_attributes['treatment_mention']`を`True`に設定し、セッションとDBに保存
  - **警告メッセージの表示**: 治療中キーワードが検出された場合、推奨結果の冒頭（「💡 あなたに合わせたアドバイス」の前）に独立した警告用`<div>`を表示
    - 警告メッセージのタイトル: `⚠️ <strong>治療中の方へ</strong>`（HTML形式で太字化）
    - 警告メッセージの内容: 「現在治療中の疾患がある場合、市販薬の服用前に必ず主治医や薬剤師にご相談ください。」「治療中の方が市販薬を服用する場合、主疾患への重大な影響を与える可能性があります。」
    - 警告メッセージのスタイル: オレンジ系の背景色（`#fff3e0`）と左側に4pxのボーダー（`#ff9800`）で視覚的に強調
  - **表示位置の最適化**: 警告メッセージは`attribute_update_message`の後、`personalized_section`（「💡 あなたに合わせたアドバイス」）の前に配置され、ユーザーが最初に目にする位置に表示

- **警告メッセージ表示の改善**
  - **HTML形式での太字化**: 警告メッセージのタイトルをMarkdown形式（`**太字**`）からHTML形式（`<strong>太字</strong>`）に変更し、ブラウザで正しく太字表示されるように改善
  - **独立した警告セクション**: 警告メッセージを「💡 あなたに合わせたアドバイス」の前に独立した`<div>`として配置し、視認性を向上

- **ログ出力の最適化**
  - **不要なログの削減**: 複数症状ペナルティ適用時のログと`calculate_symptom_specificity_penalty`関数の最終結果ログをDEBUGレベルに変更し、通常運用時のログ出力を削減
  - **ログレベルの適切な設定**: 重要な情報のみINFOレベルで出力し、デバッグ用の詳細情報はDEBUGレベルで出力するように改善

- **眠気と不眠の区別機能の実装**
  - **症状の明確な区別**: 「眠気」（drowsiness）と「不眠」（insomnia）を別の症状として扱うように改善
  - **SYMPTOM_DICTIONARYへの追加**: 「眠気」エントリを追加し、同義語（「眠い」「寝てしまう」「だるい」「眠気が強い」など）を定義
  - **キーワードリストの拡充**: 「寝むたい」「寝たい」などのバリエーションを追加し、眠気関連キーワードの検出精度を向上
  - **LLMトリアージの改善**: トリアージプロンプトを更新し、「眠気」を`Physical (subcategory: drowsiness)`、「不眠」を`Emotional (subcategory: insomnia)`として分類

- **眠気カウンセリングフローの実装**
  - **カウンセリングフローへの自動リダイレクト**: 眠気関連キーワードが検出された場合、自動的にカウンセリングフローにリダイレクト（ステップ1.9で重複チェックの前に実行）
  - **専用プロンプトテンプレート**: 眠気カウンセリング用の専用プロンプトテンプレートを追加し、生活習慣改善と適切なカフェイン使用についてのアドバイスを提供
  - **フォローアップ質問の生成**: 眠気の原因を特定するための質問を自動生成
  - **医薬品推奨への移行**: カウンセリング中に「薬を教えて」「カフェイン剤を教えて」「しりたい」などの要求があった場合、カフェイン剤（眠気覚まし）の推奨フローに移行
  - **初期メッセージの送信**: カウンセリング開始時に「眠気で、推奨される医薬品を知りたい場合は教えて下さい。」というメッセージを自動送信

- **カフェイン剤推奨機能の改善**
  - **ビタミン剤配合カフェイン製剤の優先**: エスタロン、トメルミンなど、ビタミン剤が配合されたカフェイン製剤にボーナススコア（+0.2）を付与
  - **複数のカフェイン剤の推奨**: 単一のカフェイン剤だけでなく、複数のカフェイン剤（カーフェソフト錠、エスタロンモカ１２、エスタロンモカ内服液など）を推奨
  - **症状適合度の改善**: 「眠気」症状に対して、カフェイン剤の症状適合度を適切に評価

- **使用上の注意生成の改善**
  - **症状情報の追加**: `generate_usage_notes`関数に`symptoms`パラメータを追加し、ユーザーの症状情報をプロンプトに含めるように改善
  - **症状に合わせた注意事項**: 症状情報に基づいて、より適切な使用上の注意を生成
  - **カフェイン剤専用の注意事項**: カフェイン剤の場合、以下の詳細な注意事項を生成
    - 添付文書に記載された服用期間や用法・用量を守り、短期間の服用にとどめる
    - 1日の摂取量上限（健康な成人400mg、妊娠中200-300mg/日、授乳中200mg/日）
    - カフェイン含有飲料（コーヒー、お茶、エナジードリンクなど）との併用禁止
    - 就寝前の使用を避けること
    - 胃酸過多・胃潰瘍、心臓病の方は服用不可
    - 15歳未満の小児は市販薬として販売されていない
  - **不眠症関連の注意事項の除外**: カフェイン剤（眠気覚まし）の場合、不眠症向けの睡眠改善薬に関する注意事項（「睡眠改善薬は一時的な不眠にのみ効果があります」「不眠症と診断されている場合は医師にご相談ください」など）を除外
  - **禁忌事項の適切な表示**: カフェイン剤の場合、緑内障や前立腺肥大の禁忌事項は表示せず、胃酸過多・胃潰瘍、心臓病の方のみを「使ってはいけない人」に含める

- **安全性チェック機能の改善**
  - **症状に基づく条件分岐**: `check_sleep_medicine_safety`関数を改善し、症状が「不眠」の場合のみ不眠症関連のチェックを実行
  - **眠気のみの場合の処理**: 症状が「眠気」のみで「不眠」がない場合、不眠症関連のチェックをスキップし、アルコール併用警告のみを追加

- **処理順序の最適化**
  - **ステップ1.9の位置変更**: 眠気関連キーワードチェック（ステップ1.9）を重複チェックの前に移動し、カウンセリングフローへのリダイレクトを確実に実行
  - **重複チェックの改善**: 重複チェックでスキップされた場合でも、ログに記録するように改善

- **プロンプトエンジニアリングの改善**
  - **カフェイン剤専用のシステムメッセージ**: カフェイン剤の場合、不眠症向けの睡眠改善薬に関する注意事項を含めないようにシステムメッセージを調整
  - **キャッシュキーの改善**: 使用上の注意のキャッシュキーに症状情報とカフェイン含有情報を含め、症状に応じた適切な注意事項を生成

### 2025年12月29日（店舗案内機能の拡張・商品検出機能の改善・緊急事案検出機能の拡充）

- **緊急事案検出機能の拡充**
  - **キーワードリストの大幅拡充**: 各カテゴリのキーワードを大幅に拡充し、様々な表現パターン（過去形、現在進行形、丁寧語など）をカバー
    - **武器カテゴリ**: 一般的な刃物から現代兵器（ドローン、イージス艦、空母、大砲、サブマシンガン、AK-47、M16、M4、戦車、ミサイル、戦闘機、ヘリコプター、爆弾、爆発物、毒物、化学兵器、生物兵器、核兵器など）まで包括的なリストに拡充
    - **窃盗カテゴリ**: 基本的な窃盗表現から、スリ、ひったくり、置き引き、車上荒らし、自転車泥棒、バイク泥棒、車泥棒など様々な窃盗パターンをカバー
    - **不審者カテゴリ**: 不審な行動、尾行、つけられている、ストーカー、つきまとい、不審な車両など様々な表現を追加
    - **傷病人カテゴリ**: より多くの状態表現（大出血、重傷、軽傷、応急処置など）を追加
    - **暴力カテゴリ**: 傷害、殺人、脅迫などより多くの暴力関連表現を追加
    - **火災カテゴリ**: 延焼、全焼、半焼、焼失などより多くの火災関連表現を追加
    - **医療緊急カテゴリ**: 心臓発作、脳卒中、ショックなどより多くの医療緊急関連表現を追加
  - **ヘッダーメッセージの改善**: ユーザーの立場（情報提供者 vs 被害者・当事者）に応じた適切なメッセージを表示
    - **情報提供者向け（火災、武器、暴力、不審者）**: 「安全を最優先にしてください。」（ユーザーは目撃者・情報提供者）
    - **被害者・当事者向け（医療緊急、傷病人、窃盗、不明）**: 「お近くのスタッフにご連絡ください」（ユーザーが被害者または当事者の可能性）
    - 多言語対応（日本語、英語、韓国語、中国語）
  - **デバッグログの追加**: 検出開始、キーワード検出、検出結果の詳細ログを追加し、問題分析を容易に

- **店舗案内機能の拡張**
  - **商品検出機能の実装**: `classify_product_category`関数により、ユーザー入力から商品名やブランド名を自動検出
    - 大カテゴリ > サブカテゴリ > 商品名/ブランド名の3階層で分類
    - 商品が検出された場合、在庫確認応答にカテゴリ情報を表示（例：「ビューティ・トイレタリー > シャンプー > メリット」）
  - **在庫確認機能の改善**
    - 在庫確認キーワードに「どこ」「場所は」を追加（「歯ブラシはどこ？」「化粧水の場所は？」などに対応）
    - 商品名が検出され、かつ「場所」「どこ」キーワードが含まれる場合、在庫確認として優先的に処理
    - `process_detailed_classification`で在庫確認を最初にチェックし、商品名が検出された場合は優先的に在庫確認として処理
  - **商品リストデータの拡張**（`data/store_products.json`）
    - サブカテゴリ202、商品名2,362件、ブランド名880件に拡張
    - 7大カテゴリ（ビューティ・トイレタリー、スキンケア・メイク、カウンセリング化粧品、日用品・ペット、医療・介護、ベビー、食品）
    - 商品名とブランド名を分離して管理（商品名にはブランド名を含めず、検出精度向上）
  - **パス修正**: `store_inquiry_handler.py`の商品リスト読み込みパスを修正（`os.path.dirname(os.path.dirname(__file__))` → `os.path.dirname(__file__)`）

- **条件付きログ記録の実装（ログシステムの最適化）**
  - **条件付き会話履歴記録**: エラー時および不適切評価時のみ会話履歴（10件）をログに出力
    - **通常時**: 会話履歴なしでログを記録（データ量と処理時間を削減）
    - **エラー時**: 会話履歴を含むログを記録（問題分析のため）
    - **不適切評価時**: フィードバック送信時に会話履歴を含むログを自動出力（評価のため）
  - **structured_logger.pyの拡張**
    - `log_counseling_detail`: `conversation_history`パラメータをオプショナルに変更
    - `log_error_detail`: `conversation_history`パラメータを追加（エラー時に会話履歴を含められる）
  - **app.pyの修正**
    - エラーハンドラ（500エラー）: 会話履歴（最新10件）を取得して`log_error_detail`に渡す
    - `submit_feedback`: `report_type`が`'negative_feedback'`の場合、会話履歴を含むログを出力
    - 通常の`log_counseling_response`呼び出し: `conversation_history=None`に変更（約17箇所）
  - **counseling_response.pyの修正**
    - 通常の`log_counseling_response`呼び出し: `conversation_history=None`に変更（約14箇所）
    - エラー時のログ呼び出し: 会話履歴をそのまま渡す（`counseling_error`、`counseling_summary_error`、`counseling_response_error`）
  - **効果**
    - **データ量削減**: 通常時のログデータ量を約70-80%削減
    - **処理時間短縮**: 通常時のログ処理時間を約2-7ms短縮
    - **評価精度維持**: エラー時と不適切評価時には会話履歴が記録されるため、問題分析に必要な情報は保持
    - **Render環境での最適化**: 512MB RAM、0.5 CPU、2インスタンスの制約下でも効率的に動作

### 2025年12月28日
- **絶対評価ベースの僅差ロジック実装（スコアリングシステムの大幅改善）**
  - **original_rankの保存と復元**: ランキング保護のため、raw_scoreでソートした時点で各候補にoriginal_rankを保存し、すべての処理後も順序を復元
    - 正規化前、減点適用後、相対スコア計算後、成分多様性確保後、最終推奨前の各段階でoriginal_rankに基づいて順序を復元
    - 特殊なソートロジック（乗り物酔い薬、肩こり・筋肉痛）が適用された場合も、original_rankを更新してランキング保護を維持
  - **正規化プロセスの簡素化**: Min-Max正規化、重み付き線形変換、底上げロジックを削除し、raw_scoreをそのままfinal_scoreとして使用
    - 複雑な正規化処理を削除し、シンプルで透明性の高いスコアリングシステムに変更
    - raw_scoreが1.0を超える場合は1.0にクリップしてから表示スコアを計算
  - **calculate_display_score_absolute関数の実装**: 絶対評価ベースの表示用スコア計算関数を新規作成
    - 基本スコア: raw_score × 100（1.0を超える場合は1.0にクリップ）
    - ランク調整: 1位は0%、2位は-1.5%、3位は-3.0%のデクリメント
    - 不足情報による減点: 15%（completeness_penalty × 100）を適用
    - 計算式: `display_score = (base_score - rank_adjustment) × (1 - penalty/100)`
    - 表示精度: 小数点第1位で丸めて表示（例: 85.0%、67.4%、65.5%）
  - **特殊なソートロジックの復元**: 乗り物酔い薬と肩こり・筋肉痛の特殊なソートロジックを復元
    - 乗り物酔い薬: スコア差が0.1以内の場合、指定第2類医薬品を優先（順序変更時はoriginal_rankも更新）
    - 肩こり・筋肉痛: 最適解の外用薬（フェイタス、バンテリン、サロンパス）を優先（スコア差0.2以内、順序変更時はoriginal_rankも更新）
  - **不足情報による減点の適用方法変更**: final_scoreから直接減算する方式から、display_score計算時に適用する方式に変更
    - completeness_penaltyはscore_breakdownに保存され、display_score計算時にのみ適用
    - final_scoreには影響せず、表示上の信頼度のみを調整
  - **ランキング保護の徹底**: 現在の「完璧な推奨順序」を1ミリも崩さないよう、以下の3つの原則を実装
    - 減点の一様性: completeness_penaltyは全候補に対して定数として適用
    - 単調増加な写像: raw_scoreからdisplay_scoreへの変換は単調増加関数（絶対評価ベースの線形変換）
    - original_rankの優先: すべての処理後、original_rankに基づいて順序を復元
  - **効果**: 
    - スコアの僅差が実現され、1位と2位、2位と3位の差が適切に表示される（例: 85.0%、67.4%、65.5%）
    - 不足情報による減点が明確に表示され、ユーザーに情報の重要性を伝える
    - ランキング順序が完全に保護され、既存の「完璧な推奨順序」が維持される
    - スコア計算の透明性が向上し、デバッグや最適化が容易になった

### 2025年12月27日
- **診断名（疾患名）検出機能の大幅改善・実装**
  - **診断名リストの大幅拡充**: 市販薬では対応が難しい診断名を包括的に検出（約170項目に拡充）
    - 精神疾患（約60項目）: うつ病、統合失調症、双極性障害、パニック障害、PTSD、ADHD、自閉症スペクトラム、認知症、アルツハイマー病など
    - 悪性腫瘍（約30項目）: がん、癌、白血病、リンパ腫、各種臓器がんなど
    - 慢性疾患（約50項目）: 高血圧、糖尿病、リウマチ、膠原病、腎疾患、肝疾患、心疾患、呼吸器疾患など
    - その他の重篤な疾患（約30項目）: 感染症、循環器疾患、消化器疾患、皮膚疾患、眼科疾患、耳鼻咽喉科疾患、婦人科疾患、泌尿器疾患、整形外科疾患、アレルギー疾患、睡眠障害など
  - **文脈を考慮した検出ロジックの実装**: 既往歴・持病として言及された場合の誤検出を防止
    - 除外パターンの実装: 時間的表現（過去、以前、昔など）、他人・家族関係（知り合い、友人、家族など）、医学用語（既往症、持病、基礎疾患など）、逆接表現（ですが、がありますがなど）
    - 正規表現パターンマッチングによる既往歴表現の検出
    - 文脈チェック範囲の拡大（診断名の前後50文字をチェック）
  - **早期リターン処理によるAPIコスト削減**: 診断名検出時に通常の医薬品推奨フローをスキップし、ChatGPT API呼び出しを回避してコストを大幅削減
  - **診断名検出の優先実行（2025年12月27日追加）**: 
    - 診断名検出をステップ1.7（心臓緊急チェック後、不眠関連キーワードチェック前）で実行
    - 「不眠症」などの診断名がカウンセリングフローに流れることを防止
    - 診断名と症状（「不眠」など）を適切に区別し、診断名の場合は医師受診を勧告
    - 症状表現（「不眠」「眠れない」など）は従来通りカウンセリングフローで適切に対応
    - 不眠関連キーワードリストから「不眠症」を除外し、診断名検出機能で処理することで、診断名と症状を明確に区別
  - **診断名カテゴリ別の適切なメッセージ表示**: 精神疾患、悪性腫瘍、慢性疾患、その他の重篤な疾患に応じた医師相談推奨メッセージを表示

- **イースターエッグ機能の大幅改善**
  - **絵文字パーティクル効果の拡張**:
    - Unicode 16.0 / Emoji 16.1準拠のすべての絵文字に対応（😀😁😂などの表情、👿👹👺👽👻などのキャラクター、💘💓💕💖などのハートマークなど）
    - 絵文字の種類に応じた最適化（ハートマークはゆっくり上昇、顔文字は弾ける動き、キャラクターは大きく表示など）
    - 絵文字のみのメッセージを送信すると、ユーザーメッセージと適切な返信がチャットに表示される
  - **画面変形機能の大幅拡張**:
    - 新機能追加: 拡大・縮小（zoom）、反転（flip）、バウンス（bounce）、脈動（pulse）、光る（glow）の5つの新機能を追加
    - トリガーキーワードの大幅拡充: 命令形（〜しろ、〜して、〜してくださいなど）、演繹形（〜する、〜します、〜させるなど）、魔法使い・呪文系（〜の魔法、〜呪文など）を含む多数のキーワードに対応
    - 完全一致チェックの実装: 誤検知を防ぐため、正規化後のメッセージとトリガーリストを完全一致で比較
    - チャット表示: 画面変形機能のトリガーを送信すると、ユーザーメッセージと適切な返信がチャットに表示される
  - **アニメーション機能の改善**:
    - 雨と雪のアニメーションの存在感を大幅に向上
      - 雪: パーティクル数を大幅に増加（20-30 → 50-80）、フォントサイズを拡大（15-25px → 20-50px）、透明度を向上（0.7 → 0.85-1.0）、継続時間を延長（3秒 → 5秒）、個別アニメーションで動きを自然化
      - 雨: パーティクル数を大幅に増加（30-50 → 60-100）、太さを太く（2px → 2-4px）、長さを長く（20-50px → 30-70px）、透明度を向上（0.8 → 0.7-1.0）、継続時間を延長（2秒 → 4秒）、個別アニメーションで動きを自然化
    - アニメーション系のトリガーを送信すると、ユーザーメッセージと適切な返信がチャットに表示される
  - **ゲーム機能の改善**:
    - スネークゲームのトリガーを送信すると、ユーザーメッセージと適切な返信がチャットに表示される
  - **感謝メッセージの処理改善**:
    - 感謝メッセージは必ず通常の診断フローに流し、適切な医薬品推奨が行われる
  - **UI/UX改善**:
    - 返信メッセージの改行が正しく表示されるように改善（\nを<br>タグに変換）
    - イースターエッグ発動時に入力欄が確実にクリアされるように改善
  - **実装ファイル**:
    - `static/js/easter-eggs.js`: Unicode 16.0 / Emoji 16.1準拠の絵文字パーティクル効果、拡張された画面変形機能を含む

### 2025年12月26日
- **イースターエッグ機能の実装（面白機能追加）**
  - **感謝・ポジティブメッセージ対応**: 特定の感謝メッセージを送信すると、パーティクル効果（星や花びらが降るアニメーション）が表示されます
    - トリガーキーワード: 日本語（ありがとう、助かった、完治した、治った、良くなった、感謝、素晴らしい、最高、完璧など）、英語（thank you, thanks, helped, cured, healed, better, grateful, great, perfect, excellentなど）
    - 動作: 通常の相談処理は継続し、アニメーションのみを実行（モーダルは表示しない）
  - **画面変形機能**: 特定のキーワードで画面を変形させる機能（2025年12月27日に大幅拡張）
    - 回転（Rotate）: 「回転」「かいてん」「rotate」などで画面が360度回転
    - 傾き（Skew/Askew）: 「傾く」「かたむく」「askew」などで画面が傾く
    - 揺れ（Shake）: 「揺れる」「ゆれる」「shake」などで画面が揺れる
    - 拡大・縮小（Zoom）: 「拡大」「かくだい」「zoom」などで画面が拡大・縮小（2025年12月27日追加）
    - 反転（Flip）: 「反転」「はんてん」「flip」などで画面が反転（2025年12月27日追加）
    - バウンス（Bounce）: 「バウンス」「跳ねる」「はねる」「bounce」などで画面がバウンス（2025年12月27日追加）
    - 脈動（Pulse）: 「脈動」「みゃくどう」「pulse」などで画面が脈動（2025年12月27日追加）
    - 光る（Glow）: 「光る」「ひかる」「glow」などで画面が光る（2025年12月27日追加）
  - **ゲーム機能**: モーダルで遊べるミニゲーム
    - スネークゲーム: 「スネーク」「スネークゲーム」「snake」「snake game」でスネークゲームが起動
      - Canvas + requestAnimationFrameによる実装
      - ダブルバッファリングと解像度スケーリングによる最適化
      - Canvasサイズをグリッド（20px）に合わせて調整し、描画範囲と走行範囲を完全一致させる根本解決を実装
      - PC: 矢印キー操作、モバイル/タブレット: 画面上の矢印ボタン操作（デバイス検出による自動切り替え）
      - スコア表示（モーダルヘッダーに表示）、再戦機能（▶️ボタン）、ゲームオーバー時の再戦ボタン
      - スネークは画面中央からスタート、🍎を食べて成長する機能
    - 絵文字パーティクル効果: 絵文字のみのメッセージを送信すると、入力した絵文字を使用したパーティクル効果が表示されます（通常のチャット処理も継続）（2025年12月27日にUnicode 16.0 / Emoji 16.1準拠に拡張）
  - **アニメーション機能**: 特定のキーワードでアニメーションを表示（通常のチャット処理も継続）
    - 花火（Fireworks）: 「花火」「はなび」「fireworks」で花火アニメーション（Canvas + 軽量パーティクル）
    - 雪（Snow）: 「雪」「ゆき」「snow」で雪アニメーション（CSSアニメーション、既存の雪アニメーションを拡張）（2025年12月27日に存在感を大幅改善）
    - 雨（Rain）: 「雨」「あめ」「rain」で雨アニメーション（CSSアニメーション）（2025年12月27日に存在感を大幅改善）
  - **安全性の実装**: 医療相談の誤動作を防ぐための厳格なチェック機能
    - 医療用語チェック: 500語以上の医療用語を検出し、1語でも含まれている場合は通常処理にフォールバック
    - 否定語チェック: 「治っていない」「良くならない」などの否定表現を検出し、不適切な発動を防止
    - メッセージ正規化: 末尾の記号（感嘆符、句点など）を除去してから比較し、「ありがとうございます！」「ありがとう。」なども検出
    - 処理フロー: 正規化 → 医療用語/否定語チェック（早期リターン） → イースターエッグマッチング
  - **パフォーマンス最適化**: メイン機能への影響を最小限に
    - 動的インポート: ゲームロジックを動的にインポートし、必要な時のみ読み込む（`import('/static/js/games/snake.js')`など）
    - Canvas最適化: ダブルバッファリング、解像度スケーリング、グリッドサイズに合わせたCanvasサイズ調整
    - リソースクリーンアップ: アニメーション終了時にイベントリスナーやタイマーを適切にクリーンアップ
    - 早期リターン: 医療用語検出時は即座に通常処理にフォールバック
  - **アクセシビリティ対応**: すべてのユーザーが利用可能に
    - キーボードナビゲーション: Escapeキーでモーダルを閉じる、Tabキーでフォーカス移動
    - ARIA属性: モーダルに`role="dialog"`、`aria-modal="true"`、`aria-labelledby`を設定
    - prefers-reduced-motion対応: アニメーション無効化設定を尊重
    - モーダル外クリック: モーダル外をクリックしても閉じられる
  - **多言語対応**: 日本語・英語・韓国語・中国語に対応
    - 既存の`translations`オブジェクトを拡張し、イースターエッグ関連のメッセージも多言語化
  - **ログ記録**: イースターエッグ発動時のログを記録（デバッグ・分析用）
    - トリガー、メッセージ、処理時間を記録
    - エラー発生時も詳細なログを記録
  - **実装ファイル**:
    - `static/js/easter-eggs.js`: イースターエッグ検出・実行ロジック（絵文字パーティクル効果を含む）
    - `static/js/games/snake.js`: スネークゲーム実装（607行、Canvas最適化、デバイス検出、再戦機能）
    - `static/css/easter-eggs.css`: イースターエッグ専用CSS（画面変形、モーダル、アニメーション、アクセシビリティ対応）
    - `templates/index.html`: easter-eggs.jsとeaster-eggs.cssの読み込み
  - **効果**: ユーザー体験の向上とアプリの親しみやすさの向上、通常の医療相談機能への影響を最小限に抑えた安全な実装

- **ログ出力の最適化（パフォーマンス改善）**
  - **INFOレベルのログをDEBUGレベルに変更**: 本番環境でのパフォーマンス向上のため、詳細なログをDEBUGレベルに変更
    - 症状パターンマッチングのログをDEBUGレベルに変更（ループ内で大量に出力されていた問題を解決）
    - 候補抽出のログを集約（各medicine_typeごとのログを削除し、サマリー形式で1回だけ出力）
    - スコア計算の詳細ログ（Threshold Pass/Fail Detail、Sho Match Score）をDEBUGレベルに変更
    - ボーナス計算のログ（成分・バランス、飲みやすさ、随伴症状、ライフステージ、証）をDEBUGレベルに変更
    - 成分ベーススコアのログをDEBUGレベルに変更
    - 期待される医薬品の詳細ログを削減（優先確保の詳細ログをDEBUGレベルに変更、最終推奨に追加されるログは簡潔に）
  - **残した重要なログ（INFOレベル）**: 最低限の入力・出力と大雑把な計算過程の数（候補数、最終推奨数など）のみをINFOレベルで出力
    - 候補医薬品数（フィルタリング後）
    - 候補抽出完了のサマリー
    - 期待される医薬品を最終推奨に追加（簡潔版）
    - 禁忌事項の除外（WARNINGレベル）
  - **効果**: 
    - ログ出力による処理の重さを大幅に削減
    - INFOレベルのログは最低限の情報のみになり、可読性が向上
    - 詳細な計算過程はDEBUGモード時のみ出力され、本番環境でのパフォーマンスが向上
  - **実装ファイル**:
    - `rule_based_recommendation.py`: すべての詳細ログをDEBUGレベルに変更、候補抽出ログを集約

### 2025年12月25日（クリスマス・後半・シーズン対応UI実装🎁）
- **シーズン対応UIシステムの実装（クリスマスプレゼント🎁）**
  - **拡張性の高いシーズン管理システム**: クリスマス・正月仕様に加え、他のシーズン（春・夏・秋）にも対応する拡張性の高いシーズン管理システムを実装
    - **season_manager.pyモジュールの作成**: シーズン判定と画像パス生成を一元管理する新しいモジュールを追加
      - `get_current_season()`: 日時からシーズンタイプを自動判定（クリスマス・正月・春・夏・秋）
      - `get_zodiac_image()`: 年度から干支画像名を自動計算（2026年を基準とした12年周期の計算）
      - `get_season_images()`: シーズンに応じた画像パスリストを生成
      - `is_in_period()`: 日時が期間内か判定（月を跨ぐ期間にも対応）
    - **設定ベースのアーキテクチャ**: Python辞書（SEASON_CONFIG）でシーズン設定を管理し、保守管理が容易に
      - 新しいシーズンの追加は設定辞書にエントリを追加するだけ
      - 画像数の変更も柔軟に設定可能
      - 複数期間の定義に対応（例：正月は12月26日～12月31日と1月1日～1月7日）
  - **クリスマス・正月仕様の自動切り替え**: 12月26日以降は自動的に正月仕様に切り替わる機能を実装
    - **クリスマスシーズン（12月1日～12月25日）**: クリスマスツリーと雪だるまを表示
    - **正月シーズン（12月26日～1月7日）**: 年度に応じた干支画像と正月装飾を表示
      - 2025年: 右側にSneak.png（へび）、左側にEma.pngまたはKagami-mochi.pngをランダム表示
      - 2026年以降: 右側に年度に応じた干支画像（horse.png、Goat.pngなど）を自動表示
      - 左側画像はセッションごとにランダム選択され、セッション内で固定
  - **年度ごとの干支画像自動表示**: 2026年以降の正月装飾は、その年度の干支画像を自動表示
    - 2026年: horse.png（うま）
    - 2027年: Goat.png（ひつじ）
    - 2028年: Monkey.png（さる）
    - 以降、12年周期で自動計算
    - 2025年は特別にSneak.png（へび）を使用
  - **CSSクラスの汎用化**: 保守管理しやすいように、CSSクラスを汎用化
    - `.winter-decoration.christmas-tree` → `.season-decoration.position-right`に変更
    - `.winter-decoration.snowman` → `.season-decoration.position-left`に変更
    - シーズンに応じて画像パスを自動的に変更する仕組みを実装
    - 既存のスタイル（位置・サイズ・透明度など）は維持
  - **レスポンシブ対応**: モバイルデバイスでの装飾サイズを最適化
    - タブレット（768px以下）: 右側80px、左側70px
    - スマートフォン（480px以下）: 右側60px、左側50px
  - **キャッシュ対策**: 画像URLに日付ベースのバージョンクエリパラメータ（`?v=YYYYMMDD`）を追加
    - 画像の更新が確実に反映されるように改善
  - **実装ファイル**:
    - `season_manager.py`（新規作成）: シーズン管理ロジック
    - `app.py`: `season_manager`を使用するように修正、JSTタイムゾーン処理を追加
    - `templates/index.html`: 画像表示を動的に変更（`decoration_images`ループ）
    - `static/css/main.css`: CSSクラスを汎用化（`.season-decoration`）
    - `requirements.txt`: `pytz==2024.1`を追加
  - **拡張性の考慮**:
    - 新しいシーズン（春・夏・秋）の追加は`SEASON_CONFIG`にエントリを追加するだけ
    - 画像数の変更も各シーズンの`images`辞書で柔軟に設定可能
    - イベントベースの期間定義に対応
  - **効果**: 季節感のあるUIでユーザー体験が向上し、保守管理しやすい設定ベースのアーキテクチャにより、将来的な拡張が容易になった

### 2025年12月25日（クリスマス・後半）
- **雪のアニメーションの改善（クリスマスプレゼント🎁）**
  - **スクロール時のアニメーション切れ問題の修正**: チャットが増えてスクロール可能になった際に、雪のアニメーションが途中で切れてしまう問題を修正
    - 雪のコンテナの高さを、チャットメッセージの実際の高さ（`scrollHeight`）に基づいて動的に設定するように改善
    - CSS変数（`--snow-container-height`）を使用して、JavaScriptで動的に値を設定できるように変更
    - `@keyframes snowfall`のアニメーション終了位置を、固定の`100vh`ではなくCSS変数を使用するように変更
    - メッセージ追加時、スクロール時、リサイズ時に自動的に雪のコンテナの高さを更新する機能を実装
    - MutationObserverを使用して、DOM変更を監視し、自動的に高さを更新する機能を追加
    - 効果: チャットがスクロール可能になっても、雪のアニメーションが途切れずに続くようになった
  - **z-indexの調整による視認性向上**: チャットの視認性を下げないために、雪のアニメーションをチャットメッセージよりも下に描画するように改善
    - `.snow-container`の`z-index`を`0`から`-1`に変更し、チャットメッセージ（`z-index: 2`）の下に表示されるように修正
    - 効果: チャットメッセージの可読性が向上し、雪のアニメーションがメッセージを邪魔しないように改善
  - **実装ファイル**:
    - `static/css/main.css`: `.snow-container`のz-indexとCSS変数の追加、`@keyframes snowfall`の修正
    - `static/js/main.js`: `updateSnowContainerHeight()`関数の追加、`createSnowAnimation()`関数の改善、MutationObserverによる自動更新機能の追加
  - **効果**: クリスマスシーズンに美しい雪のアニメーションが、スクロール時も途切れることなく表示され、チャットメッセージの可読性も向上した

### 2025年12月25日
- **不眠カウンセリング中の期間・妊娠/授乳チェック機能の追加**
  - **期間チェック機能の実装**: 不眠カウンセリング中に、症状の期間が2週間（14日）を超えている場合、カウンセリングを中止して受診勧告を行う機能を実装
    - `collected_info`から期間情報を取得し、2週間を超えている場合は受診勧告を表示
    - ユーザー入力からも期間を抽出（「14日」「2,3日」「2週間」「14日ほどです」「ここ14日ほどです」などのパターンに対応）
    - 期間の文字列から日数を抽出し、14日を超えている場合は即座にカウンセリングを中止
    - 受診勧告メッセージには、期間の長さと慢性的な不眠の可能性について説明を追加
  - **妊娠/授乳チェック機能の実装**: 不眠カウンセリング中に、妊娠/授乳の情報が検出された場合、カウンセリングを中止して受診勧告を行う機能を実装
    - 妊娠関連キーワード（「妊娠」「妊娠中」「妊婦」「妊娠しています」「妊娠してます」「妊娠してる」「妊娠です」）を検出
    - 授乳関連キーワード（「授乳」「授乳中」「授乳しています」「授乳してます」「授乳してる」「母乳」「母乳育児」「授乳です」）を検出
    - 妊娠/授乳が検出された場合は即座にカウンセリングを中止し、市販の睡眠改善薬の使用を避けるべき旨を説明
    - 妊娠中は産婦人科やかかりつけの医師への相談を推奨、授乳中は小児科やかかりつけの医師への相談を推奨
  - **チェック順序の最適化**: 妊娠/授乳のチェックを期間のチェックより優先するように改善
    - 妊娠/授乳の情報が検出された場合、期間情報があっても妊娠/授乳のチェックが優先される
    - 効果: 「妊娠中です」という入力に対して、期間情報があっても妊娠/授乳のチェックが優先され、適切な受診勧告が表示される
  - **期間抽出の改善**: 期間抽出処理を改善し、様々なパターンに対応
    - 「14日ほどです」「ここ14日ほどです」のようなパターンにも対応
    - ユーザー入力に「日」や「週間」が含まれる場合、`collected_info`に期間情報があっても、最新の入力から期間を抽出してチェック
    - 週間の場合は日数に変換（例: 2週間 → 14日）して比較
  - **実装ファイル**:
    - `counseling_response.py`: 期間チェックと妊娠/授乳チェック機能の実装（`handle_user_input_in_counseling_mode`関数内）
  - **効果**: 不眠カウンセリング中に、慢性的な不眠（2週間以上）や妊娠/授乳中の場合は、適切にカウンセリングを中止し、医療機関への受診を推奨するようになった

### 2025年12月24日（後半）
- **不眠カウンセリングから薬推奨への切り替え機能の改善**
  - **薬を希望するキーワードリストの拡充**: 不眠カウンセリング中に薬を希望するキーワードを検出する機能を改善
    - 「教えて欲しい」「教えてください」「教えて下さい」「教えて」などのパターンを追加
    - 「知りたい」「知りたいです」「知りたいです。」「知りたい。」などのパターンを追加
    - 「推奨して」「推奨してください」「推奨して下さい」「推奨して欲しい」などのパターンを追加
    - 効果: 「一時的な不眠で推奨される医薬品を知りたい場合は教えて下さい」への返信（「教えて欲しい」「知りたい」など）が正しく検出されるように改善
  - **Physicalカテゴリへの切り替え処理の改善**: カウンセリングモードからPhysicalカテゴリに切り替えた場合の処理を改善
    - トリアージ結果をPhysicalカテゴリに設定（不眠の症状をPhysicalカテゴリとして処理）
    - カウンセリング処理をスキップして、通常フロー（薬推奨）に進む
    - トリアージ結果のreasoningに「不眠カウンセリングから薬推奨への切り替え」を設定
  - **Askカテゴリの検知スキップ機能の追加**: カウンセリングからPhysicalカテゴリに切り替えた場合、Askカテゴリの検知をスキップ
    - トリアージ結果がPhysicalカテゴリで、reasoningが「不眠カウンセリングから薬推奨への切り替え」の場合、Askカテゴリの検知をスキップ
    - 医薬品相談回答（Askカテゴリ）ではなく、薬推奨フローが実行されるように改善
    - 効果: 「薬を教えて下さい」と返信した場合、医薬品相談回答ではなく、不眠に対する薬推奨が実行される
  - **実装ファイル**:
    - `counseling_response.py`: 薬を希望するキーワードリストの拡充（`medicine_request_keywords`）
    - `app.py`: Physicalカテゴリへの切り替え処理とAskカテゴリの検知スキップ機能の実装
  - **効果**: 不眠カウンセリング中に薬を希望した場合、適切に薬推奨フローに切り替わり、医薬品相談回答にならないように改善

### 2025年12月24日
- **通知メッセージのスタイル統一と妊娠可能性表示の改善**
  - **通知メッセージのスタイル統一**: 情報登録通知メッセージと性別自動登録通知メッセージのスタイルを他のメッセージと統一
    - 背景色を`#d1ecf1`から`#f8f9fa`に変更
    - ボーダー色を`#bee5eb`から`#dee2e6`に変更
    - テキスト色を`#0c5460`から`#000`に変更
    - 「情報を修正」ボタンの背景色を`#0c5460`から`#17a2b8`に変更
    - HTMLエスケープ処理を追加し、セキュリティを強化
  - **妊娠可能性の表示改善**: 妊娠可能性が検出された場合（'high'または'low'）に「妊娠状態: 可能性あり」を通知メッセージに追加
    - `user_attributes.get('pregnancy_possible')`が'high'または'low'の場合に自動表示
    - ユーザーに妊娠可能性を明確に通知
  - **インデントエラーの修正**: 3359行目の`except`ブロックのインデントを修正し、構文エラーを解消
  - **効果**: 通知メッセージの視覚的一貫性が向上し、妊娠可能性の情報が適切に表示されるようになった

- **背景画像の配置改善（チャット入力欄の上に固定表示）**
  - **背景画像の固定表示機能**: クリスマスツリーと雪だるまの装飾画像をチャット入力欄（`div.chat-input`）の上に常に固定表示するように改善
    - **HTML構造の変更**: 画像を`chat-messages`内から`chat-container`直下に移動し、`chat-input`の上に配置できるように変更
    - **CSS位置調整**: `position: absolute`を使用し、`bottom: calc(91px + 20px)`で入力欄の高さ（91px）+ パディング（20px）の位置に固定
      - デスクトップ: `bottom: calc(91px + 20px)`
      - タブレット（768px以下）: `bottom: calc(80px + 10px)`
      - スマートフォン（480px以下）: `bottom: calc(80px + 8px)`
    - **z-indexの調整**: 画像の`z-index`を`998`から`1`に変更し、チャットメッセージ（`z-index: 2`）の下に表示されるように改善
      - チャットメッセージの邪魔にならないように背景として表示
      - `pointer-events: none`により、クリックは透過され操作を妨げない
    - **レスポンシブ対応**: 画面サイズに応じて画像の位置を自動調整
      - デスクトップ: クリスマスツリー（右20px）、雪だるま（左20px）
      - タブレット: クリスマスツリー（右10px）、雪だるま（左10px）
      - スマートフォン: クリスマスツリー（右5px）、雪だるま（左5px）
  - **実装ファイル**:
    - `templates/index.html`: 画像のHTML構造を`chat-container`直下に移動
    - `static/css/main.css`: 画像の位置とz-indexを調整（`.winter-decoration`クラス）
  - **効果**: 背景画像が常にチャット入力欄の上に表示され、スクロール時も位置が固定されるようになった。また、チャットメッセージの下に配置されることで、メッセージの可読性を損なわないように改善

### 2025年12月21日
- **UI/UX改善（チャットメッセージエリアの背景色変更）**
  - **チャットメッセージエリアの背景色変更**: `#chatMessages`の背景色を`rgb(245, 245, 245)`から`rgba(192, 192, 192, 1)`に変更
    - より視認性の高いグレー背景に変更し、メッセージの可読性を向上
    - `static/css/main.css`の`.chat-messages`クラスを更新
  - **効果**: チャットメッセージエリアの視認性が向上し、ユーザー体験が改善

- **季節・イベント対応UIの実装**
  - **冬仕様の装飾機能を追加**: クリスマスシーズンや冬期間に装飾を表示する機能を実装
    - **装飾画像**: クリスマスツリー（右下）と雪だるま（左下）をチャット画面に表示
      - 透明度0.7で設定し、メッセージの邪魔にならないように配慮
      - `pointer-events: none`でクリックを無効化し、操作を妨げない
      - GPU加速と画像レンダリング最適化を適用
    - **雪のアニメーション**: 雪の結晶が降るアニメーションを実装
      - 画面サイズに応じて雪の数を自動調整（最大30個）
      - 各雪の結晶はランダムな位置、速度、サイズ、横移動で降下
      - GPU加速と`will-change: transform`でパフォーマンス最適化
      - ウィンドウリサイズ時に自動で再生成（デバウンス処理）
    - **レスポンシブ対応**: モバイルデバイスでの装飾サイズを最適化
      - タブレット: クリスマスツリー80px、雪だるま70px
      - スマートフォン: クリスマスツリー60px、雪だるま50px
    - **実装ファイル**: 
      - `templates/index.html`: 装飾画像と雪コンテナのHTML構造
      - `static/css/main.css`: 装飾スタイルと雪アニメーションのCSS（`.winter-decoration`、`.snow-container`、`.snowflake`クラス）
      - `static/js/main.js`: 雪アニメーション生成ロジック（`createSnowAnimation`関数、`handleResize`関数）
  - **効果**: 季節感のあるUIでユーザー体験が向上し、アプリの親しみやすさが向上

- **管理者画面のモバイルレイアウト改善**
  - **`mobile-content-area`のサイズ調整**: `mobile-queue-slider`の下端までの高さに制限
    - `flex-shrink: 0`を設定し、JavaScriptで動的に高さを計算
    - `mobile-stats`と`mobile-queue-slider-container`の高さを合計して設定
  - **`panel-header`と`chat-messages`の配置改善**: `mobile-content-area`の下に`panel-header`、その下に`chat-messages`を配置
    - CSSの`order`プロパティを使用してレイアウト順序を制御
    - `center-panel`を`height: calc(100vh - 50px)`に設定し、`chat-messages`を画面下端まで伸ばす
  - **`mobile-queue-slider`の左端アイテム表示修正**: 左端のアイテムが見えない問題を修正
    - `justify-content: center`を`justify-content: flex-start`に変更
    - パディングを`padding: var(--spacing-xs) 60px var(--spacing-xs) var(--spacing-xs)`に調整
    - `scroll-snap-align: center`に戻し、スペーサー要素を追加して中央配置を実現
  - **`queue-slider-item`の循環機能実装**: スライダーが循環するように改善
    - 最後のアイテムを最初に、最初のアイテムを最後に複製
    - `scrollQueueSlider`と`handleSwipe`で複製に到達した際に実際のアイテムにジャンプ
    - すべての`scrollIntoView`呼び出しで`inline: 'center'`を使用
  - **モバイルチャットモーダルの余白削減**: メッセージの左右の余白を削減
    - `.mobile-chat-messages`のパディングを`var(--spacing-sm) var(--spacing-xs)`に削減
    - `.message-content`の`max-width`を`85%`に調整
    - ユーザーメッセージの左側、ボットメッセージの右側の余白を削減
  - **効果**: モバイルでの管理者画面の使いやすさが大幅に向上し、スライダーが循環動作するようになった
  - **モバイルチャット送信機能の修正**: モバイルチャットモーダルでメッセージ送信が失敗する問題を修正
    - `sendMobileChatMessage`関数で、`data.success || data.status === 'success'`の両方をチェックするように改善
    - HTTPエラーのチェック（`res.ok`）を追加
    - 成功時の通知メッセージを追加
    - エラーメッセージの詳細化（`data.message`も含める）
- **デスクトップ・タブレットレイアウトのアコーディオンメニューバグ修正**
  - **HTMLタグの削除機能を追加**: `stripHtml`関数を追加し、メッセージからHTMLタグを削除してテキストのみを抽出
  - **`renderCurrentSession`関数の改善**: 現在のセッション情報表示時にHTMLタグを削除し、すべての動的コンテンツに`escapeHtml`を適用
  - **`renderQueue`関数の改善**: キューアイテム表示時にHTMLタグを削除し、すべての動的コンテンツに`escapeHtml`を適用
  - **CSSの調整**: `queue-accordion-header`の`min-height`を`80px`から`60px`、`max-height`を`90px`から`70px`に削減し、`overflow: hidden`を追加
  - **効果**: アコーディオンヘッダーにHTMLタグや詳細情報が表示されなくなり、簡潔で見やすい表示に改善
- **スコアモーダルのモバイルレイアウト最適化**
  - **`score-item`のコンパクト化**: 無駄に大きい`score-item`を最適化
    - パディングを`var(--spacing-xs) var(--spacing-sm)`に削減
    - ギャップを`4px`に削減
    - スコアバーの高さを`10px`に削減
    - フォントサイズを調整（ラベル: 0.8rem、値: 0.75rem、重み表示: 0.7rem）
  - **要素の順序調整**: ラベル → 値 → バー → 重み表示の順に配置
  - **色分けの実装**: デスクトップと同様の色分けを実装
    - JavaScriptで各スコアアイテムに`data-score-type`属性を追加
    - CSSで`data-score-type`に基づいてボーダーカラーを設定
      - 症状適合度: `#4CAF50`（緑）
      - 効能特異性: `#2196F3`（青）
      - 年齢適合性: `#9C27B0`（紫）
      - 用法簡便性: `#FF9800`（オレンジ）
      - 副作用リスク: `#F44336`（赤）
      - 相互作用リスク: `#795548`（茶色）
  - **効果**: モバイルでのスコアモーダルの見やすさが向上し、デスクトップと同様の色分けで視認性が向上

### 2025年12月20日（後半）
- **管理者画面のレスポンシブ改善とエラーハンドリング強化**
  - **`manual-reply-queue`のレスポンシブ高さ調整**: 画面サイズに応じて`manual-reply-queue`の高さを自動調整
    - `max-height: 400px`を削除し、flexboxの`flex: 1`を使用して動的に高さを計算
    - `adjustManualReplyQueueHeight()`関数を追加し、右パネルの高さ、ヘッダー、アコーディオンの状態を考慮して高さを計算
    - アコーディオンメニューの開閉時に自動で高さを再調整
    - ウィンドウリサイズ時にも高さを再調整
    - キュー更新時にも高さを再調整
  - **`sendReply()`関数の名前衝突を解消**: 通常のチャット画面用とキューアイテム用の関数を分離
    - 通常のチャット画面用: `sendReplyFromChat()`に変更
    - キューアイテム用: `sendReplyFromQueue()`に変更
    - 「返信入力欄が見つかりません」エラーを修正
  - **`manualRefresh()`関数のエラーハンドリング改善**: より詳細なエラーメッセージを表示
    - HTTPステータスコードのチェックを追加
    - エラーの原因（キュー取得エラーまたはセッション取得エラー）とHTTPステータスコードを表示
  - **`total-sessions`要素の存在チェック追加**: 要素が存在しない場合のエラーを防止
    - `total-sessions`要素が見つからない場合は`session-count`要素を使用
    - すべての参照箇所で存在チェックを追加
  - **効果**: 管理者画面の使いやすさが向上し、エラーが発生しても原因が特定しやすくなった

### 2025年12月20日
- **管理者画面のモバイルレイアウト改善**
  - **余白の削減**: `mobile-content-area`と`center-panel`の間の無駄な余白を削除
    - `main`要素、`center-panel`、`mobile-content-area`に`gap: 0`、`margin: 0`、`padding: 0`を追加
    - モバイルレイアウトの視覚的な改善とスペース効率の向上
  - **横スライダーのモーダル表示修正**: 横スライダーのアイテムをタップしてもモーダルが表示されない問題を修正
    - `onclick`イベントに`event.stopPropagation()`を追加してイベント伝播を防止
    - `touch-action: manipulation`を追加してタッチ操作を改善
  - **モーダルの詳細情報表示機能の追加**: デスクトップレイアウトを参考に、モバイルモーダルに詳細情報を表示
    - セッションID、更新日時、メッセージ数、最新メッセージを表示
    - HTMLタグを削除してテキストのみを表示
    - 日時を日本語形式でフォーマット
    - `mobile-chat-title-wrapper`と`mobile-chat-details`を追加して詳細情報を構造化
    - モーダルヘッダーのデザインを改善（詳細情報を縦に配置）
  - **効果**: モバイルでの管理者画面の使いやすさが大幅に向上し、デスクトップと同様の詳細情報を確認可能に

### 2025年12月19日（後半）
- **解熱鎮痛薬・外用薬（のど）のスコアリング改善**
  - **「のど痛み+発熱」パターンでの解熱鎮痛薬・外用薬（のど）の優先度向上**: のどの痛みと発熱が同時に検出された場合、解熱鎮痛薬と外用薬（のど）を適切に推奨するように改善
    - **base_scoreの底上げ**: 解熱鎮痛薬と外用薬（のど）のbase_scoreを0.40に底上げ（従来は0.316程度）
    - **quick_scoreの改善**: `calculate_symptom_match_score`と`calculate_efficacy_specificity_score`で、解熱鎮痛薬は「発熱」「のどの痛み」「頭痛」に対して、外用薬（のど）は「のどの痛み」に対して、直接キーワードマッチングが失敗してもbase_score（0.45）を付与
    - **pattern_bonusの増加**: `calculate_quick_score`と`SYMPTOM_PATTERN_OPTIMIZATION`で、解熱鎮痛薬と外用薬（のど）のpattern_bonusを0.35から0.45に増加
    - **throat_bonusの増加**: `calculate_final_score`で、解熱鎮痛薬と外用薬（のど）のthroat_bonusを0.35から0.45に増加
    - **adjustment_scoreの上限引き上げ**: 解熱鎮痛薬と外用薬（のど）の`limited_throat_bonus`上限を0.40から0.50に、`scaled_adjustment`上限を0.25から0.30に引き上げ
    - **詳細スコアリングへの優先的追加**: 「のど痛み+発熱」パターン検出時、解熱鎮痛薬と外用薬（のど）をそれぞれ上位50件ずつ優先的に詳細スコアリング対象（500件）に追加
    - **効果**: 解熱鎮痛薬と外用薬（のど）が適切に推奨結果に含まれるようになり、のどの痛みと発熱がある場合の推奨精度が向上

- **ログ出力の最適化（本番環境対応）**
  - **INFOレベルのログをDEBUGレベルに変更**: 本番環境でのパフォーマンス向上のため、詳細なログをDEBUGレベルに変更
    - 症状判定ログ、年齢適合性スコア計算ログ、症状特異性ペナルティログ、解熱鎮痛薬・外用薬（のど）ボーナスログ、quick_score pattern_bonus適用ログ、「のど痛み+発熱」パターン検出ログなどをDEBUGレベルに変更
  - **詳細スコアリング結果の出力を最適化**: 上位10件のみ詳細ログ出力（DEBUGレベル）に変更
    - 従来: 解熱鎮痛薬と外用薬（のど）の全件（約100件）をINFOレベルで出力
    - 改善後: 上位10件のみ詳細ログ出力（DEBUGレベル）、サマリーログを追加
  - **サマリーログの追加**: 以下のサマリーログを追加（INFOレベルで出力）
    - 解熱鎮痛薬スコアリングサマリー: 件数、最高スコア、平均スコア
    - 外用薬（のど）スコアリングサマリー: 件数、最高スコア、平均スコア
    - 詳細スコアリング上位10件のサマリー
  - **期待される効果**: 
    - ログ出力の削減: 約100件の詳細ログ → 上位10件のみ（約90%削減）
    - 実行時間の短縮: 22.4秒 → 約15-18秒（約20-30%短縮を想定）
    - ログの可読性向上: サマリーログで全体像を把握しやすく、詳細ログはDEBUGレベルで必要時のみ確認可能

### 2025年12月19日
- **二日酔い推奨アルゴリズムの大幅改善**
  - **美容系L-システイン製品の完全除外**: 二日酔い推奨において、主効能が美容用途（しみ・そばかす・色素沈着など）のL-システイン製品を推奨対象から除外
    - 美容主体のブーストを0.25から0.10に大幅削減
    - `reserved_cysteine`優先枠から美容主体を完全除外（フォールバック機能を削除）
    - 効果: 二日酔い推奨として不適切な美容系L-システイン製品（例: DHCエルシスホワイト）が推奨されなくなる
  - **五苓散の優先度向上**: 二日酔い検出時に五苓散系医薬品を最優先で推奨
    - 頭痛が検出された場合: ブースト0.55（最優先）
    - 通常の場合: ブースト0.50
    - 五苓散重複防止の強化: 同一成分グループ（タクシャ、チョレイ、ブクリョウ）の検出により、複数の五苓散製品が推奨されることを防止
  - **生薬配合胃腸薬のブースト強化**: 二日酔いの吐き気・むかつきに対応する生薬配合胃腸薬の優先度を向上
    - 二日酔い専用効能（「二日酔のむかつき」「悪酔のむかつき」）: ブースト0.40
    - 一般的な生薬配合胃腸薬: ブースト0.28
  - **漢方薬ペナルティの無効化**: 二日酔い検出時は漢方薬に対する一般的なペナルティ（-0.2）を適用しない
    - 五苓散などの漢方薬が適切に評価されるように改善
  - **効能特異性スコアの改善**: 二日酔い症状と二日酔い効能が一致する場合、効能特異性スコアに0.95を付与
    - 二日酔い特化医薬品が適切に評価されるように改善
  - **症状辞書の拡充**: 「二日酔い」「だるさ」「むくみ」をSYMPTOM_DICTIONARYに追加
    - 「二日酔い」: 重み0.95、医薬品種類（抗アレルギー薬、胃腸薬、解熱鎮痛薬）
    - 「だるさ」: 重み0.7、医薬品種類（精神症状、胃腸薬、抗アレルギー薬）
    - 「むくみ」: 重み0.75、医薬品種類（抗アレルギー薬、胃腸薬）
  - **推奨構成の最適化**: 二日酔い推奨において、以下の構成を実現
    1. 五苓散（1製品のみ、頭痛・むくみ・だるさに最適）
    2. 生薬配合胃腸薬（二日酔のむかつき・悪酔のむかつきに対応）
    3. 非美容系L-システイン製品（二日酔い関連効能がある場合のみ）
  - **効果**: 二日酔い推奨の精度が大幅に向上し、適切な医薬品のみが推奨されるように改善

- **のど痛み+発熱時の風邪薬優先度向上（2025年12月19日追加）**
  - **のど特化風邪薬の優先推奨**: のどの痛みと発熱が同時に検出された場合、のどに特化した風邪薬（のどスプレー・トローチなど）を優先的に推奨
    - のど痛み+発熱パターン検出時にのど特化医薬品にボーナス+0.45を付与
    - 総合感冒薬と併用して、のど局所治療薬も推奨する構成を実現
    - 効果: のどの痛みと発熱がある場合、のどへの直接的なアプローチと全身的な治療の両方を提供

- **葛根湯に対する重症度ベースのペナルティ追加（2025年12月19日追加）**
  - **重症度に応じた評価**: 葛根湯は風邪の初期（悪寒・発熱の初期）に適しているため、症状の重症度に応じて適切に評価
    - 重症度が高い場合や風邪の進行期には適切なペナルティを適用
    - 効果: 風邪の進行段階に応じた適切な医薬品選択が可能に

### 2025年12月16日
- **LLMトリアージ機能の実装**
  - **事前トリアージ（振り分け）の導入**: ユーザー入力を5つのカテゴリ（Physical/Emotional/Emergency/Ask/Other）に自動分類
  - **confidenceスコアの実装**: 0.0-1.0の範囲で判定の確信度を表示し、0.7未満の場合はユーザーに確認を求める
  - **心臓緊急チェック（ステップ0）**: 「心臓」「動悸」「不整脈」を含む入力の最優先チェック機能を実装
  - **曖昧性の処理**: 「心が痛い」と「心臓が痛い」を明確に区別し、適切な処理フローに振り分け

- **比喩的表現検出と文脈考慮型緊急判定の改善（2025年12月16日追加）**
  - **比喩的表現検出機能の実装**: アニメ・小説のセリフ（「心臓を捧げよ」など）を検出し、緊急対応を回避
    - キーワードベース検出: `check_exclusion_patterns`関数にアニメセリフパターンを追加
    - LLMベース検出: `detect_metaphorical_expression`関数で会話履歴を考慮した比喩的表現の判定
    - ハイブリッド判定: キーワードで除外できない場合、LLMで判定し、両方の結果を統合
  - **会話履歴の活用**: セッションから直近20メッセージを取得し、文脈を推測
    - 直前のメッセージに恋愛関連キーワードがある場合、現在のメッセージも恋愛文脈として扱う
    - セッション全体の流れを考慮した判定
  - **動的閾値調整の実装**: 文脈タイプに応じて緊急度の閾値を動的に調整
    - 恋愛文脈: 0.7（より慎重に）
    - 比喩的表現: 0.8（非常に慎重に）
    - 緊張・不安: 0.65（やや慎重に）
    - 実際の緊急: 0.6（標準）
  - **共感的な返信メッセージの改善**: `generate_contextual_emergency_message`関数を共感的なトーンに調整
    - 恋愛文脈 + 身体的症状: 感情に寄り添いつつ、身体的症状が続く場合は医療受診を推奨
    - 比喩的表現検出時: 緊急対応を避け、軽い確認メッセージ（「もし実際に症状がある場合は...」）
  - **詳細なログ記録**: 判定プロセスの各ステップ（会話履歴の使用、比喩的表現検出結果、動的閾値の適用など）を詳細に記録
  - **TRIAGE_PROMPTの拡張**: 比喩的表現の検出ルールと会話履歴考慮の指示を追加

- **カウンセリング機能の実装**
  - **感情的症状への対応**: 緊張、不安、恋愛の悩みなどに対するカウンセリング的返信機能を実装
  - **共感的な返信生成**: ChatGPTを使用した200文字以内の返信を生成（2025年12月16日改善: 100文字から200文字に拡大）
  - **会話履歴の活用**: 直近10件の会話履歴を考慮した文脈理解による返信生成を実装（2025年12月16日追加）
  - **文脈理解の改善**: 「勉強中」のような短い入力も、会話履歴から質問への回答として適切に解釈する機能を実装（2025年12月16日改善）
  - **フォローアップ質問**: 症状の詳細を把握するための自然な質問を自動生成
  - **話題転換の自動検知**: カウンセリング中に新しい症状が検出された場合、自動的に話題を転換
    - 閾値調整: 関連性スコア0.5以上はカウンセリングの続きとして処理（2025年12月16日改善: 0.3から0.5に緩和）
  - **終了条件の判定**: ユーザーの意思表示、希死念慮検出、情報収集の停滞を検知して適切に終了
  - **セッション状態管理**: カウンセリングモード中は会話の継続性を維持
  - **返信内容のログ記録**: すべてのカウンセリング返信を`log/counseling_responses.jsonl`に記録する機能を実装（2025年12月16日追加）
    - 返信タイプ、カテゴリ、confidence、カウンセリングモード情報を含む

- **トリアージ分析ログの実装**
  - **トリアージ結果のログ保存**: ユーザー入力、判定カテゴリ、confidenceスコアを記録
  - **話題転換検知のログ**: 話題転換が検知された場合の詳細情報を記録
  - **confidenceスコアチェックのログ**: 閾値チェックの結果とユーザー応答を記録
  - **カウンセリング完了時のログ**: カウンセリングセッションの完了情報を記録
  - **改善ループの実現**: ログデータを分析することで、閾値の適切性を検証可能

- **UI/UX改善**
  - **ユーザーメッセージの表示修正**: 通常フローでユーザーの入力メッセージがUIに表示されるように修正
  - **カウンセリング応答の文字数制限**: ChatGPTのカウンセリング応答を200文字に制限（2025年12月16日改善: 100文字から200文字に拡大）

- **新規モジュールの追加**
  - `llm_triage.py`: LLMトリアージ機能を実装
  - `counseling_response.py`: カウンセリング応答機能を実装（2025年12月16日改善: 会話履歴活用とログ記録機能を追加）
  - `triage_analytics.py`: トリアージ分析ログ機能を実装

- **カウンセリング機能の改善（2025年12月16日）**
  - **返信文字数制限の拡大**: 100文字から200文字に変更し、より詳細な返信を可能に
  - **会話履歴の活用**: `generate_counseling_response`と`generate_counseling_summary`に会話履歴パラメータを追加
    - 直近10件の会話履歴をプロンプトに含め、文脈を考慮した返信を生成
  - **文脈理解の改善**: `process_counseling_answer`のプロンプトを改善し、「勉強中」のような短い入力も質問への回答として解釈
  - **話題転換検知の改善**: 関連性スコアの閾値を0.3から0.5に緩和し、カウンセリング中の質問への回答を誤検知しないように改善
  - **返信ログ記録機能**: `log_counseling_response`関数を追加し、すべてのカウンセリング返信を`log/counseling_responses.jsonl`に記録
    - 返信内容、返信タイプ、カテゴリ、confidence、カウンセリングモード情報を記録
    - エラー発生時もログ記録を試みる

- **危機キーワード検出機能の改善（2025年12月16日）**
  - **文脈考慮型の検出ロジック**: `detect_crisis_keywords`関数を改善し、身体的症状の文脈を考慮した検出を実装
    - 「苦しい」というキーワードが身体的症状の文脈（「胸が苦しい」「息が苦しい」など）でも誤検出されていた問題を修正
    - 身体的症状の文脈パターンを追加（「胸が苦しい」「息が苦しい」「呼吸が苦しい」など）
    - 恋愛文脈キーワード（「失恋」「好きな人」「恋愛」など）も検出し、誤検出を防止
    - 明示的な希死念慮の文脈（「生きるのが苦しい」「人生が苦しい」など）では引き続き検出
  - **効果**: 「失恋して胸が苦しい」のような身体的症状の文脈では、自殺対策リソースが誤って表示されなくなり、適切な医療相談フローに進むように改善

### 2025年12月12日（後半）
- **プロジェクトの整理とクリーンアップ**
  - **不要ファイルの削除**: 一時的な分析・評価ファイル、ベンチマーク関連ファイル、分析ドキュメント、一時的な出力ファイルを削除
    - 削除したファイル: `analyze_test_results.py`, `detailed_recommendation_evaluation.py`, `evaluate_final_improvements.py`, `evaluate_final_results.py`, `final_evaluation_summary.py`, `test_output.txt`
    - ベンチマーク関連: `benchmark_keyword_check.py`, `benchmark_translation.py`, `benchmark_*.json`, `BENCHMARK_README.md`, `run_benchmark.sh`
    - 分析ドキュメント: `IMPROVEMENT_ANALYSIS.md`, `KEYWORD_PERFORMANCE_ANALYSIS.md`, `MEDICAL_KEYWORD_ISSUE_ANALYSIS.md`, `SCORING_SYSTEM_DETAILED_ANALYSIS.md`, `SCORING_SYSTEM_ISSUES_ANALYSIS.md`, `TRANSLATION_RECOMMENDATION.md`, `log_analysis_2025-12-06.md`
    - その他: `get_recommended_medicines.py`, `mediscine_test.csv`, `recommended_medicines_detail.json`, `__pycache__/`ディレクトリ
  - **C_OPTIMIZATION_ANALYSIS.mdの復元**: Git履歴からC言語化による高速化分析ドキュメントを復元
  - **効果**: プロジェクト構造の整理とメンテナンス性の向上

### 2025年12月12日
- **特殊用途医薬品フィルタリングの強化**
  - **ホルモン剤・性器専用医薬品の除外機能を実装**: 一般的な症状には不適切な特殊用途医薬品を自動除外
    - ホルモン剤: テストステロン、エストロゲン、プロゲステロン、メチルテストステロン
    - 男性器専用: ペニス、陰茎、性器、オットピン、亀頭
    - 女性器専用: 膣、おりもの、デリケートゾーン
    - 特殊用途: 避妊、性感染症、更年期障害、ホルモン補充、性機能改善
  - **ユーザー症状との適合性チェック**: 性器、ホルモン、避妊、更年期、性機能、男性器、女性器、ペニス、陰茎などの症状がない場合は除外
  - **効果**: 一般的な症状（頭痛、発熱など）に対して、不適切な特殊用途医薬品が推奨されることを防止

- **推奨医薬品のスコアフィルタリングの改善**
  - **スコア0.0の候補を除外**: 最終スコアが0.0の医薬品を推奨候補から除外
  - **スコア0.3以上の候補を追加**: スコア0.0以外の候補が不足する場合、スコア0.3以上の候補を追加
  - **フォールバック機能**: フィルタリング後の候補が不足する場合、元の候補リストを使用
  - **効果**: 低品質な推奨を削減し、より適切な医薬品のみを推奨

- **症状マッチングアルゴリズムの改善**
  - **単語境界マッチングの実装**: 症状名が独立した単語として効能効果テキストに含まれるかをチェック
    - 例: 「頭痛」が「頭痛薬」に含まれる場合を正しく検出
    - 例: 「痛」が「頭痛」に部分的に含まれる場合を除外（誤検知防止）
  - **前後の文字チェック**: 症状名の前後が別の文字でないことを確認
  - **追加マッチングチェック**: 前後の文字列を含めたコンテキストで症状名が別の単語の一部でないことを確認
  - **効果**: 症状マッチングの精度が向上し、誤検知を削減

- **管理者画面の詳細診断情報表示の改善**
  - **detailed_diagnosisのDB保存機能**: 詳細診断情報をDBに保存し、ADMIN_SESSIONSから取得
  - **セッション保存時の同期**: メッセージ保存時、既存セッション更新時、新規セッション作成時にdetailed_diagnosisを同期
  - **セッション一覧APIの改善**: detailed_diagnosisをDBから取得し、ない場合はADMIN_SESSIONSから取得
  - **session_idの自動追加**: detailed_diagnosisにsession_idがない場合は自動追加
  - **効果**: 管理者画面で詳細診断情報が確実に表示され、デバッグやモニタリングが容易に

- **PostgreSQL接続の安定性向上（2025年12月11日のコミットから）**
  - **接続ステータス2（トランザクション中）を正常な状態として扱う**: 不要な接続ステータスチェックを削除し、SELECT 1の実行結果のみで接続有効性を判定
  - **無限再帰エラーの修正**: 再帰防止フラグを追加し、connect()メソッド内のget_connection()呼び出しを削除
  - **効果**: PostgreSQL接続の安定性が向上し、接続エラーが削減

### 2025年12月11日
- **翻訳機能の高速化と改善**
  - **DeepL APIへの移行**: ChatGPT APIからDeepL APIに翻訳機能を移行
    - 翻訳時間を約10-20倍高速化（5-10秒 → 0.3-0.5秒）
    - コストを約100倍削減
    - HTML構造を保護しながら翻訳（`tag_handling='html'`）
  - **言語検出の改善**: 中国語と日本語の区別を改善
    - 中国語のチェックを日本語より先に実行
    - ひらがな・カタカナが含まれている場合は日本語、漢字のみの場合は中国語として判定
    - 中国語入力（例：「我喉嚨痛同發燒。」）が正しく検出されるように修正
  - **翻訳処理の最適化とHTML構造の修正**: 
    - すべてのセクション（推奨医薬品、使用上の注意、医師の受診、質問）を追加してから一括翻訳するように改善
    - HTML構造が正しく保たれ、すべてのセクションが`<div class="recommendation-result">`内に含まれるように修正
    - 翻訳後にセクションが外に出る問題を解消
    - フィードバックボタンのテキストも翻訳対象に追加
  - **エラーハンドリングの強化**: 
    - DeepL APIのクォータ超過、認証エラーなどの適切なエラーハンドリング
    - 翻訳失敗時は元のテキストを返すフォールバック機能
  - **依存ライブラリの追加**:
    - `deepl==1.18.0`を`requirements.txt`に追加
    - `python-dotenv`の必要性を明確化（`.env`ファイルの読み込みに必須）

- **デバッグコードの整理**
  - `print`文を`logger`に置き換え
  - ログレベルの適切な分類（debug, info, warning, error）
  - `DEBUG_MODE`環境変数による詳細ログの制御

- **パフォーマンス最適化とキャッシュ機能の強化（2025年12月11日追加）**
  - **翻訳キャッシュ機能の実装**: 
    - DeepL APIへの翻訳リクエストをキャッシュし、同じテキストの再翻訳を高速化
    - グローバルキャッシュ（最大200件）を実装し、セッション間で翻訳結果を共有
    - LRU方式でキャッシュサイズを管理
  - **NLUキャッシュの改善**: 
    - セッションIDなしでもキャッシュ可能に改善（テキストハッシュベースの共有キャッシュ）
    - キャッシュサイズを50件から100件に拡大
    - セッション固有キャッシュと共有キャッシュの両方をサポート
  - **医薬品タイプキャッシュの追加**: 
    - 医薬品タイプ判定結果をキャッシュ（最大50件）
    - 同じ症状入力に対する医薬品タイプ判定を高速化
  - **PostgreSQL接続の改善**: 
    - SSL接続設定の自動化（`DATABASE_SSLMODE`環境変数で制御、デフォルト: `require`）
    - 接続タイムアウトを10秒から5秒に短縮
    - 再接続機能の実装（最大3回、指数バックオフ方式）
    - SSLエラーの検出と適切なエラーハンドリング
  - **デリケート部位キーワードの拡張**: 
    - 「膣」「外陰」「陰部」などのキーワードを追加し、デリケート部位専用製品の検出精度を向上

- **UI/UX改善（2025年12月11日追加）**
  - **フィードバックモーダルのサイズ最適化**: 
    - 縦方向の余白を最小限に調整し、コンテンツに応じた最小限のサイズに変更
    - デスクトップ・スマホ・小さなスマホの各画面サイズに対応した最適化
    - パディングとマージンを削減し、無駄な余白を排除

### 2025年12月5日（後半）
- **ChatGPTフォールバックの廃止とエラーハンドリングの強化**
  - **ChatGPTフォールバック機能の完全廃止**: ルールベース推奨失敗時にChatGPTにフォールバックする機能を削除
    - 不十分で不適切な回答が生成される問題を解決
    - ルールベース推奨の信頼性を向上
  - **詳細なエラーメッセージ表示**: ルールベース推奨失敗時に、失敗理由、推奨される対応、医師相談案内を含む詳細な情報ボックスを表示
    - エラータイプ別のメッセージ（no_candidates, rule_based_error, missing_critical_info, unknown_error）
    - 技術的な詳細情報も含めて表示
    - フィードバックボタンも追加
  - **医療関連キーワード検出の改善**: 「痒い」「痒」などのキーワードを追加し、「腕が痒いです」のような入力でも正常に検出可能に
  - **キーワード検出ロジックの最適化**: NLU結果を先に確認し、症状が検出されている場合はキーワードチェックをスキップ
    - 症状が検出されない場合のみキーワードチェックを実行
    - 誤検知を削減し、検出精度を向上
  - **エラーメッセージの詳細化**: すべてのエラーケースで具体的な失敗理由と推奨される対応を含む詳細なエラーメッセージを返すように改善
    - 空入力、3文字未満、繰り返し文字、キーワード未検出、症状未検出、候補医薬品なしの各ケースに対応

- **NLU信頼度スコア計算の最適化**
  - **部位情報の明確性による信頼度向上**: 部位情報（腕、足、手、目、鼻など）が検出された場合に0.1加点
  - **症状名の明確性による信頼度向上**: SYMPTOM_DICTIONARYに完全一致する症状がある場合、1つにつき0.05加点（最大0.15）
  - **入力テキストの詳細度による信頼度向上**: 15文字超で0.05、30文字超でさらに0.05加点
  - **症状の記述方法の明確性**: 「○○が△△」のような明確な記述パターンがある場合に0.03/パターン（最大0.1）加点
  - **重症度の改善**: 中等度でも症状が検出されたこと自体に0.05加点
  - **効果**: 単一症状でも適切な信頼度が得られ、より正確な推奨が可能に（例：「腕がかゆいです」で0.30→0.55以上に改善）

- **部位情報抽出機能の大幅拡張**
  - **部位検出範囲の拡大**: 頭皮、デリケート部位、のどに加えて、以下の部位を検出可能に
    - 腕（arm）: 腕、うで、上腕、前腕、二の腕、ひじ、肘
    - 足（leg）: 足、脚、あし、下肢、太もも、すね、ふくらはぎ、膝
    - 手（hand）: 手、て、手首、手のひら、指
    - 足首（foot）: 足首、くるぶし、足の裏、つま先、かかと
    - 目（eye）: 目、眼、まぶた、眼球
    - 鼻（nose）: 鼻、はな、鼻腔
    - 耳（ear）: 耳、みみ、耳たぶ
    - 口（mouth）: 口、くち、口腔、唇、歯、舌
    - 胸（chest）: 胸、胸部、乳房
    - お腹（stomach）: お腹、腹部、胃、みぞおち、へそ
    - 背中（back）: 背中、腰、腰部、背骨
    - 肩（shoulder）: 肩、かた、肩甲骨
    - 首（neck）: 首、くび、首筋
    - 顔（face）: 顔、かお、頬、あご、額
    - 皮膚（skin）: 皮膚、肌、はだ
  - **部位情報の返り値への追加**: `simple_pattern_matching_nlu`関数の返り値に`user_body_part`を追加

- **一般的な表現からの症状抽出機能の実装**
  - **プロンプトの改善**: 「風邪をひいています」のような一般的な表現からも、典型的な症状（頭痛、発熱、咳、鼻水、のどの痛みなど）を推測して抽出できるようにプロンプトを改善
  - **ルールベースの前処理**: 風邪、インフルエンザ、胃腸炎などのキーワードを検出した場合、典型的な症状を自動追加
    - 風邪関連: 頭痛、発熱、咳、鼻水、のどの痛み
    - インフルエンザ関連: 発熱、頭痛、関節痛、筋肉痛、悪寒
    - 胃腸炎関連: 腹痛、下痢、吐き気
  - **症状のマージ処理**: ChatGPTが「なし」と返答した場合でも、前処理で推測した症状があれば使用
  - **システムメッセージの改善**: 一般的な表現から症状を推測することを強調
  - **効果**: 「風邪をひいています」のような一般的な表現からも、適切な症状を抽出できるようになり、推奨精度が向上

### 2025年12月5日
- **部位特異的製品の検出機能を実装**
  - **部位キーワード辞書の追加**: デリケート部位・頭皮・のど専用製品を検出するためのキーワード辞書を実装
    - 製品名、効能効果、用法から部位特異性を自動検出
    - デリケート部位専用製品（カブレーナなど）を識別
    - 頭皮専用製品（フケ・スカルプ関連）を識別
    - のど専用製品（トローチなど）を識別
  - **部位マッチングスコアの実装**: ユーザーの症状部位と医薬品の対象部位が一致する場合にボーナス、不一致の場合にペナルティを適用
    - 部位一致: +1.0のボーナス
    - 部位不一致: -0.5のペナルティ（大幅減点）
    - 部位情報がない場合はペナルティなし
  - **ユーザー入力からの部位情報抽出**: ユーザーの入力テキストから部位情報を自動抽出
    - 「頭が痒い」→ 頭皮（scalp）として識別
    - 「デリケート部位」「おりもの」→ デリケート部位として識別
  - **効果**: 部位特異的製品（例: デリケート部位専用製品）が不適切な部位（例: 頭皮）に推奨されることを防止

- **ChatGPTによる症状詳細質問生成機能を実装**
  - **推奨前の質問生成**: 症状とユーザー情報のみを考慮して、推奨前に質問を生成
    - 基本情報（年齢、性別、妊娠状態、アレルギー、服用中薬、期間）に関する質問は生成しない
    - 症状の詳細（部位、原因、程度、経過など）に関する質問を生成
  - **質問の優先度付け**: ChatGPTが各質問に優先度（critical, important, optional）を自動付与
  - **質問数の制限なし**: ChatGPTが適切な数の質問を自動生成（通常3-5問程度）
  - **AMBIGUOUS_SYMPTOMS辞書の削除**: ルールベースの曖昧症状辞書を削除し、ChatGPTによる質問生成に統一
  - **既存入力欄の活用**: 追加質問への回答やその他の情報は、既存のメッセージ入力欄から送信可能
  - **効果**: より柔軟で文脈に応じた質問生成が可能になり、症状の詳細をより適切に把握

- **属性抽出処理の改善**
  - **薬に関する情報の除外**: 「服用している薬はありません」などの薬に関する情報を`other_info`に入れないように修正
    - 属性モーダルで「いいえ」を選択した際に送信される「他に服用している薬はありません」を確実に除外
    - 正規表現パターンを拡張して、様々な表現形式に対応
  - **管理者画面のUI改善**: `current_medications`が空の場合でも「なし」と表示されるように修正
    - 服薬有無の情報が適切に表示され、`other_info`に混入しないように改善

- **前回の症状メッセージ取得ロジックの改善**
  - 症状キーワードリストに「かゆい」「かゆみ」「痒い」「痒み」などを追加
  - 属性更新後の再推奨が正常に動作するように改善

- **スコア正規化アルゴリズムの大幅改善**
  - **Min-Max正規化の実装**: 詳細スコアリング対象全体の最大値・最小値を考慮した正規化を実装
    - 従来の固定閾値（0.7）方式から、動的なMin-Max正規化に変更
    - 全候補のraw_scoreの最大値・最小値を計算し、`(raw_score - min) / (max - min)`で正規化
    - 1.0を超えるスコアも正しく正規化され、上位の医薬品間の差が保持される
  - **正規化閾値の調整**: 0.7から0.5に変更し、より多くの候補を評価対象に
    - 0.5以下のスコアは0.0にマッピング（推奨対象外）
    - 0.5超のスコアをMin-Max正規化で0.0-1.0にマッピング
  - **非線形変換の適用**: 正規化後のスコアに平方根を適用し、上位の差を拡大
    - 高スコア領域での差が明確になり、最適な医薬品の選出が容易に
  - **正規化情報の追加**: 各候補に`normalization_info`（最小値・最大値・範囲）を追加
    - 管理者画面で正規化過程を可視化可能
  - **JavaScript側の対応**: 全ての表示箇所でMin-Max正規化を考慮したスコア計算を実装
    - `calculateNormalizedScore`関数をグローバル関数として定義
    - 正規化情報が存在する場合は既に正規化済みのスコアを使用
    - フォールバック: 旧方式（0.5基準の正規化）もサポート
  - **効果**: 上位の医薬品間のスコア差が明確になり、最適な医薬品の選出精度が向上

- **フォルダ構造の整理と最適化（2025年12月21日追加）**
  - **設定ファイルの整理**: `config/`フォルダを作成し、設定ファイルを集約
    - `gunicorn_config.py`、`requirements.txt`、`runtime.txt`を`config/`フォルダに移動
    - デプロイ時の互換性のため、`requirements.txt`と`runtime.txt`はルートにもコピーを保持
  - **データファイルの整理**: `data/`フォルダを作成し、すべてのCSVファイルを集約
    - `otc_medicine_data.csv`、`kanpo_medicine.csv`、`medicine_interactions.csv`、`medicine_side_effects.csv`、`summarized_efficacy_data.csv`を`data/`フォルダに移動
    - `medicine_logic.py`と`scoring_utils.py`のCSVパス参照を`data/`フォルダを参照するように更新
  - **ドキュメントの整理**: 技術ドキュメントと日本語ドキュメントを`docs/`フォルダに集約
    - `ASYNC_IMPLEMENTATION_GUIDE.md`、`ASYNC_QUICK_START.md`、`C_OPTIMIZATION_ANALYSIS.md`、`REGRESSION_TEST_GUIDE.md`、`SCALING_SETUP.md`、`SECURITY_IMPLEMENTATION.md`を移動
    - 日本語ドキュメント（アプリ概要.md、プライバシーポリシー.md など）も`docs/`フォルダに移動
  - **テスト・スクリプトの配置**: テストは`tests/`フォルダ（例: `test_comprehensive_integration.py`）、開発・リファクタ用スクリプトは`scripts/`フォルダに配置（2026年2月8日時点では`scripts/`に build_api_routes、extract_*、remove_* 等）
  - **ログファイルの整理**: `app.log`のパス参照を`log/app.log`に更新（次回起動時から適用）
  - **効果**: プロジェクト構造の明確化、ファイル検索の容易化、メンテナンス性の向上

### 2025年12月4日
- **管理者画面の詳細スコアモーダルの大幅拡張**
  - **全スコア要素の表示**: 基本6要素（症状適合度、効能特異性、年齢適合性、用法簡便性、副作用リスク、相互作用リスク）に加えて、ボーナス/ペナルティを含むすべてのスコア要素を表示
    - ボーナス: のどボーナス、症状特化型ブースト、アレルギーブースト
    - ペナルティ: 症状特異性ペナルティ、リスク成分ペナルティ、アレルギーペナルティ、漢方薬優先度調整
  - **計算過程の可視化**: スコア計算の全過程をステップバイステップで表示
    - 基本スコアの計算（重み付け適用）
    - 調整スコアの計算（ボーナス/ペナルティの合計）
    - 最終スコアの計算（正規化処理まで）
    - 各ステップで具体的な数値と計算式を表示
  - **中間スコアの表示**: デバッグ用の中間スコア（基本スコア、調整後基本スコア、調整スコア）を表示
  - **UI/UXの改善**:
    - モーダル幅を700px → 900pxに拡大
    - セクションごとの色分け（基本スコア: 青、ボーナス: 緑、ペナルティ: 赤、計算過程: 紫）
    - 視覚的なプログレスバーで各スコアを表示
    - 計算過程をコード風フォントで表示
    - グラデーション背景の総合スコア表示
  - **重み付け情報の表示**: 各基本要素の重み付けと重み付け適用後の値を表示
  - **効果**: 管理者がスコアの計算過程を完全に理解でき、デバッグやアルゴリズムの最適化が容易に

### 2025年12月3日
- **管理者画面の改善**
  - **ユーザー属性情報モーダルの表示修正**: モーダルが表示されない問題を修正し、確実に表示されるように改善
  - **ユーザー属性情報モーダルのデザイン更新**: 管理者画面のモダンなデザインに合わせて、ユーザー属性情報モーダルのデザインを全面刷新
    - グラデーション背景のヘッダー、アバター表示、カード型レイアウト、ホバーエフェクトなどを追加
    - CSS変数を使用した統一されたデザインシステムを適用
  - **AI自動応答OFF時のカスタムメッセージ設定機能**: ヘッダーのAI管理ボタンから、AI自動応答OFF時にユーザーに送信するカスタムメッセージを設定可能に
    - メッセージの保存・読み込み・リセット機能を実装
    - データベースまたはメモリ（フォールバック）に保存され、アプリ再起動後も保持（DB接続時）
  - **AI自動応答OFF時のメッセージ保存問題の修正**: メッセージ保存後にデフォルト値に戻る問題を修正
    - 保存直後（5秒以内）は`loadManualReplyMessage`による上書きを防止
    - `refreshAIStatus`によるメッセージフィールドの更新タイミングを調整
  - **AI自動応答OFFボタンのエラー修正**: 「エラー: 無効なモード」が発生する問題を修正
    - 重複した`setAIMode`関数を削除し、統一された実装（`/api/main_ai_control`を使用）に変更
    - `'on'`/`'off'`と`'auto'`/`'manual'`の両方に対応するように改善
  - **AI自動応答OFF時のユーザー返信機能の修正**: AI自動応答OFF時にユーザー側に返信が返ってこない問題を修正
    - 管理者モードでもカスタムメッセージを送信するように変更
    - ユーザーメッセージの直後にbotメッセージがない場合にカスタムメッセージを追加するロジックを実装
    - セッションとDBの同期処理を改善

- **構造化ログシステムの実装（2025年12月28日追加）**
  - **新しいログモジュール**: `structured_logger.py`を作成し、統一された構造化ログフォーマットを実装
  - **二重出力**: `app.log`（構造化テキスト）とJSONLファイル（機械読み取り可能）の両方に出力
  - **セッションIDとタイムスタンプ**: すべてのログエントリにセッションIDとISO形式のタイムスタンプを付与

- **医薬品推奨ログの大幅強化**
  - **完全なアプリケーション出力**: `bot_content`（完全なHTML形式）を記録
  - **詳細なNLU解析結果**: 抽出された症状、信頼度スコア、red_flags、性別検出、妊娠可能性などを記録
  - **全段階の候補数**: 初期検索後、スコアリング後、フィルタリング後の候補数を記録
  - **推奨医薬品の全スコア情報**: final_score, total_score, raw_score, display_score, score_breakdown内の全項目を記録
  - **翻訳後のテキスト**: 翻訳が実行された場合、翻訳後のテキストも記録
  - **ログの出力タイミング**: `app.py`で`bot_content`が完全に生成された後にログを記録し、実際にユーザーに表示された内容を正確に記録

- **カウンセリングログの強化**
  - **ユーザー入力と会話履歴の追加**: ユーザー入力全文と会話履歴（最新10件）を記録
  - **システム返信の全文記録**: システムの返信全文を記録し、カウンセリングの質を評価可能に

- **医薬品質疑応答ログの追加**
  - **新しいログ機能**: `log_medicine_question_detail`を実装
  - **ユーザーの質問全文とシステムの回答全文を記録**: 医薬品に関する質問と回答の完全な記録

- **翻訳ログの追加**
  - **新しいログ機能**: `log_translation_detail`を実装
  - **元のテキストと翻訳後のテキストを記録**: 翻訳処理の完全な記録（長いテキストの場合は最初の500文字）

- **エラーログの改善**
  - **500エラーハンドラーの改善**: `structured_logger.log_error_detail`を使用して詳細なエラーログを記録
  - **完全なスタックトレース**: エラー発生時の完全なスタックトレースを記録
  - **入力データとシステム状態**: エラー発生時の入力データとシステム状態を記録
  - **ユーザー表示メッセージ**: ユーザーに表示されたメッセージも記録

- **ログファイルの整理**
  - すべてのログファイルを`log/`ディレクトリに統一
  - JSONL形式で機械読み取り可能なログを出力

- **効果**
  - デバッグ: セッションIDで特定のセッションのログを追跡可能
  - 医薬品の適切性評価: NLU解析結果、候補数、全スコア情報を記録し、推奨ロジックの適切性を評価可能
  - カウンセリングの適切性評価: 会話履歴とユーザー入力・返信の全文を記録し、カウンセリングの質を評価可能
  - **注意**: 2025年12月29日に条件付きログ記録が実装され、通常時は会話履歴なしでログを記録するように最適化されました

### 2025年11月22日
- **漢方薬推奨アルゴリズムの大幅強化**
  - **若年層への「中年向け漢方」ペナルティ**: 40歳未満のユーザーに対して「中年以降」向け漢方にペナルティ（0.35）を適用
  - **当帰四逆加呉茱萸生姜湯の不適切推奨防止**: 冷え性の症状（冷え、手足、しもやけなど）がない場合、頭痛のみではペナルティ（0.4）を適用
  - **釣藤散の年齢ペナルティ強化**: 25歳女性の頭痛など、若年層への推奨を抑制（ペナルティ0.35）
  - **kanpo_medicine.csvのルール統合**: 34種類の漢方薬に対する詳細なルールを統合
    - 風邪・呼吸器系（6種類）: 葛根湯、麻黄湯、小青竜湯、麦門冬湯、五虎湯、参蘇飲
    - 消化器系（6種類）: 安中散、六君子湯、半夏瀉心湯、大建中湯、平胃散、五苓散
    - 婦人科・血の道症（5種類）: 当帰芍薬散、加味逍遙散、桂枝茯苓丸、桃核承気湯、当帰四逆加呉茱萸生姜湯
    - 精神・神経系（5種類）: 半夏厚朴湯、抑肝散、柴胡加竜骨牡蛎湯、酸棗仁湯、釣藤散
    - 痛み・こむらがえり・泌尿器（5種類）: 芍薬甘草湯、八味地黄丸、牛車腎気丸、猪苓湯、疎経活血湯
    - 皮膚（4種類）: 十味敗毒湯、防風通聖散、黄連解毒湯、消風散
    - その他（3種類）: 補中益気湯、十全大補湯、人参養栄湯
  - **漢方薬の証（Sho）解析の強化**: 効能効果テキストから「証」の条件、主要適応症状、条件付き症状を構造化して解析
  - **胃腸虚弱ユーザーへの安全装置**: 胃腸が弱いユーザーに対して実証向け漢方（体力充実、便秘前提）に強力なペナルティ（0.5）を適用

- **特化型ブースト値の調整**
  - 喉の痛み特化医薬品: ブースト値を0.30から0.35に微調整
  - 胃に優しい医薬品（女性の頭痛）: ブースト値を0.20から0.25に微調整

- **空入力のガード条件追加**
  - 空文字列・空白のみの入力に対してエラーメッセージを返す
  - 極端に短い文字列（3文字未満）のチェック
  - 繰り返し文字のみの入力の検出
  - 医療関連キーワードが含まれていない短い文字列のチェック

- **小児用医薬品フィルタリングの強化**
  - `PEDIATRIC_KEYWORDS`に「ドライシロップ」を追加
  - 大人（15歳以上）や年齢未入力の場合にシロップ系形状（シロップ、ドライシロップ）にペナルティ（-0.20）を適用
  - 小児向けキーワードが含まれていないシロップ剤も大人への推奨を抑制

- **テストケースの追加**
  - 若年層への中年向け漢方ペナルティのテスト
  - 空入力のガード条件のテスト（5種類）
  - 当帰四逆加呉茱萸生姜湯の不適切推奨防止のテスト
  - シロップ剤の大人への推奨抑制のテスト

### 2025年11月5日
- **パフォーマンス最適化の実装**
  - **二段階スコアリング**: 簡易スコア（症状・効能・年齢）で上位N×30件を選別し、詳細スコアリングは選別された候補のみに実行（処理時間を約70%削減、精度を維持）
  - **ChatGPT API呼び出しの統合**: 3件の医薬品をまとめて1回のAPI呼び出しで処理（API呼び出し回数を約67%削減）
  - **ログ出力の削減**: print文をloggerに置き換え、DEBUG_MODE環境変数でログレベルを制御
  - **レスポンス返却の最適化**: レスポンスを先に返却し、DB読み取りとログ出力は後で実行（ユーザー体験向上）
  - **タイムアウト設定の調整**: Gunicornタイムアウトを120秒から180秒に増加（処理時間を考慮）

- **セッション管理機能の追加**
  - /adminページに「📋 セッション管理」ボタンを追加
  - セッション一覧表示、検索、個別削除、全削除、編集機能を実装
  - セッション情報の詳細表示（ユーザー名、ID、アクティブ状態、メッセージ数、最終アクティビティ、IPアドレスなど）

- **テストスイートの作成**
  - 単体テスト（test_unit.py）: 17個のテストケース（100%成功）
  - 統合テスト（test_integration.py）: ユーザー側と管理者側の統合的な動作をテスト
  - 包括的デプロイテスト（test_comprehensive_deployment.py）: デプロイ前の包括的な動作確認
  - 全テスト実行スクリプト（test_run_all.py）を作成
  - データベースモックを使用したテスト環境を構築

- **エラー修正**
  - `UnboundLocalError: cannot access local variable 'datetime'` を修正（明示的なインポート追加）
  - JSONシリアライゼーションエラーを修正（Mockオブジェクトの検出と処理）
  - セッションデータのnullチェックを追加
  - セッションmodified属性の存在チェックを追加
  - `cleanup_expired_sessions`の戻り値チェックを追加

- **コード品質向上**
  - エラーハンドリングの強化
  - 型安全性の向上
  - テストカバレッジの向上

### 2025年11月4日
- **マルチインスタンス対応**
  - PostgreSQLベースのセッション管理を実装
  - グローバル状態の同期機能を追加
  - Render Manual Scaling対応（2-3台のインスタンスで同時接続15台に対応）
  - 自動フォールバック機能を実装

### 2025年11月2日
- **ハイブリッド推奨システムの更新**
  - ルールベース推奨の精度向上
  - AI推奨のフォールバック機能を改善
  - インフルエンザ検出機能の追加
  - 症状特異性ペナルティの実装
  - リスク成分フィルタリングの強化
  - 曖昧症状の質問生成機能の追加

- **UI/UX改善**
  - リソース分割による初期表示速度の改善
  - オンボーディングガイドの追加
  - 使い方ガイド・FAQの追加
  - レスポンシブデザインの改善
