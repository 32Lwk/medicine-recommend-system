# パイプライン・ルーティング — RAG 統合 FAQ（Concierge SSOT）

> エージェント分岐・SSE・ルーティング例外の **retrieve 専用 SSOT**。各セクションは想定質問 + キーワード + 回答要点。
> ユーザー向け回答では **環境変数名を出さない**。

## Q: Chat Pipeline v2 とは何か

<!-- rag-keywords: Chat Pipeline v2 とは パイプライン v2 概要 統一 -->

**回答要点**

- Web / LINE 共通の統一チャット POST パイプライン（`chat_post_pipeline.py`）
- triage → IntentRouter / unified routing → dispatcher → 各 handler の一経路化
- 本番・dev とも **既定で有効**（テスト実行時のみ OFF）
- レガシー ChatOrchestrator は dispatch 未解決時の fallback として残存

## Q: IntentRouter は何をするか

<!-- rag-keywords: IntentRouter 役割 LLM gate triage 振り分け -->

**回答要点**

- ユーザー発話を Physical / Concierge / Store / Counseling / SessionOps 等に振り分け
- 決定論 gate（緊急・副作用・メタ topic break）+ structured LLM + legacy triage ヒント
- confidence 最大の候補を採用（PRIMARY 有効時は gate/LLM が triage より優先）
- 決定は `dialogue_state.routing` と session の `_routing_decision` に記録

## Q: Unified Routing（3 層）の仕組み

<!-- rag-keywords: Unified Routing layer1 layer2 layer3 execution_lock unified_router -->

**回答要点**

- **Layer1**: 副作用 QA / medicine_qa / メタ topic break / changelog 継続を決定論で即決
- **Layer2**: legacy route + gate + LLM。曖昧でなければここで確定
- **Layer3**: 短い曖昧 follow-up を LLM または rule で prior 継続 / topic break 判定
- **execution_lock**: Router 決定を実行層（Concierge regex 等）で上書きしない

## Q: マルチエージェントの各エージェントの役割

<!-- rag-keywords: エージェント 役割 TriageAgent Physical Concierge Ask Store Counseling Emergency -->

**回答要点**

- **TriageAgent**: 入力分類の入口（category / subcategory）
- **PhysicalOrchestrator**: 症状 NLU → ルールベース市販薬推奨（CSV スコア）
- **ConciergeAgent**: 挨拶・技術 FAQ・アプリ説明・更新履歴（RAG + SSOT）
- **AskAgent / medicine_followup_qa**: 推奨後の医薬品 Q&A
- **StoreInquiryAgent**: 店舗・遺失物案内
- **CounselingManager**: 心理カウンセリング
- **EmergencyRouter**: 緊急受診案内（gate 即決）

## Q: Medicine QA と Concierge の境界はどこか

<!-- rag-keywords: Medicine QA Concierge 境界 症状 インフラ 比較 副作用 -->

**回答要点**

- **症状・市販薬候補** → Physical（ルールベース推奨）
- **医薬品比較・説明・選び方** → medicine_qa（LLM + ブランド CSV）
- **副作用・眠気** → medicine_side_effect_qa（CSV → KB）
- **推奨後の薬 Q&A** → medicine_followup_qa
- **インフラ・規約・アプリ・更新履歴** → Concierge（architecture / doc_*）
- 「ロキソニンとイブ」= medicine_qa、「AWS と GCP」= Concierge architecture

## Q: medicine_qa と medicine_side_effect_qa の違い

<!-- rag-keywords: medicine_qa medicine_side_effect_qa 副作用 比較 選び方 厳密判定 -->

**回答要点**

- **medicine_side_effect_qa**: 副作用・眠気・併用リスクが主題。症状 reco に入れない
- **medicine_qa**: 比較・選び方・成分・用法・画像。副作用+写真等の複合 intent もこちら
- **厳密判定**: `is_strict_medicine_side_effect_question` で比較質問の副作用誤判定を防止
- unified Layer1 で execution_lock 付き即決

## Q: follow-up（深掘り）はどう継続されるか

<!-- rag-keywords: follow-up 深掘り sticky 継続 もっと詳しく 詳しく prior intent -->

**回答要点**

- 短い曖昧発話（「詳しく」「もっと」等）→ Layer3 follow-up LLM または rule fallback
- 同一 meta ファミリー（changelog 深掘り等）→ prior intent sticky 継続
- ファミリー未定の「もっと詳しく」→ prior 継承（changelog への誤ピン防止）
- architecture follow-up: greeting 禁止、技術語彙または前ターン topic 参照必須

## Q: topic break（話題転換）はどう検出するか

<!-- rag-keywords: topic break 話題転換 meta ファミリー changelog architecture AWS GCP -->

**回答要点**

- `is_explicit_new_meta_topic` + `suggest_meta_intent_family` で異ファミリー検出
- 例: doc_changelog 深掘り中に「デプロイの話」→ architecture へ topic break
- layer1 でメタ topic break を medicine_qa（「違い」比較誤爆）より **先に** 判定
- **`router_dispatch` は sticky follow-up より優先** — IntentRouter 明示決定が最優先

## Q: ルーティング低信頼時はどうなるか

<!-- rag-keywords: 低信頼 clarification confidence 閾値 guard 確認メッセージ -->

**回答要点**

- confidence が閾値未満 → guard が `sub_route=clarification` を設定
- clarification は dispatch スキップ → 段階的確認メッセージ（progressive clarification）
- gate 即決定（高信頼・`resolved_by=gate`）は clarification に落とさない
- clarify ループ超過 → Sage 障害カード相当へエスケープ

## Q: IntentRouter が誤った場合の fallback

<!-- rag-keywords: ルーティング 誤り fallback orchestrator handler None Unknown shadow -->

**回答要点**

- **handler 未対応 / None**: ChatOrchestrator へ fallback（`handler_fallback`）
- **Unknown route**: dispatch スキップ → legacy orchestrator 経路を許可
- **clarification**: dispatch スキップ → confidence gate / orchestrator
- **shadow 観測**: triage 期待 vs Router 決定の mismatch を regression / gate_improvement / exempt に分類
- **correction 入力**: 直前 bot を無効化せず新 route で上書き（1 POST = 1 実行）

## Q: execution_lock は何を防ぐか

<!-- rag-keywords: execution_lock 上書き 防止 Concierge regex dispatcher ゲート -->

**回答要点**

- IntentRouter が正しい `sub_route` を返しても、実行層で上書きされていた問題を解消（2026-07）
- execution_lock 付き決定: medicine_side_effect_qa、medicine_qa、メタ topic break、changelog 継続等
- session の `_routing_execution_lock` と dispatch ログで観測
- OFF 時（unified routing 無効）は従来どおり regex / gate が上書きしうる

## Q: SSE（Server-Sent Events）の仕組み

<!-- rag-keywords: SSE ストリーミング done bot_message マスコット アニメーション -->

**回答要点**

- 一方向サーバー→クライアントで処理ステータスを段階表示（マスコットアニメーション）
- 実装: `sse_emit.py` + `chat_stream.py`
- **`done` イベント**に `bot_message` を含む — クライアント即描画
- 新規ターン開始時は前ターン cached done を破棄（ハング防止）

## Q: 副作用 Q&A と SSE done の関係

<!-- rag-keywords: 副作用 Q&A SSE done qa_delta DB フォールバック 処理バブル -->

**回答要点**

- `medicine_side_effect_qa` は **`qa_delta` 非対応** — 最終回答は **`done` 必須**
- `finalize_medicine_qa_response` が DB 保存後、in-memory `messages` を同期
- in-memory が空 → `_messages_for_sse_done` が DB から bot メッセージを復元
- 目的: 「AI分析中」処理バブル残留の防止

## Q: 製品画像・比較 UI の SSE/JSON 配信

<!-- rag-keywords: 製品画像 product_images_html 比較 UI qa-product-line 未準備 -->

**回答要点**

- パッケージ画像は SSE / JSON 両経路で `product_images_html` を付与
- 比較・選び方セクションは `ui-qa-product-line` HTML
- 画像未準備時: 「まだ準備できていません」+ 成分 1 文（サーバー生成）
- セッション内ブランドピン（`qa_brand_pins`）で比較再質問の代表製品揺れを抑制

## Q: 発熱コンテキスト中の Store 誤ルーティング

<!-- rag-keywords: 発熱 fever Store guard 上書き fever_flow -->

**回答要点**

- 発熱シグナル or セッション fever コンテキスト中に Store が選ばれた場合
- post-route guard が **Physical / fever_flow** へ上書き（confidence 引き上げ）
- shadow 観測では triage Other + Router Physical を exempt（意図的改善）扱い可

## Q: QA gate による Concierge への切替

<!-- rag-keywords: QA gate resolve_medicine_qa_route Concierge 切替 Physical dispatch -->

**回答要点**

- Physical dispatch 内で `resolve_medicine_qa_route` が CONCIERGE を返す場合あり
- 医薬品名を含むが実質アプリ/規約/メタ質問の境界ケース
- `concierge_intent_source=qa_gate:*` として triage に記録
- execution_lock 無しでも QA gate は dispatch 実行時の安全弁として機能

## Q: 障害時 UX（LLM 不可・無応答）

<!-- rag-keywords: 障害 llm_unavailable system_error fail loud OPENAI Sage カード -->

**回答要点**

- **LLM 利用不可**（OPENAI 未設定等）: Sage 障害カード。LLM 依存 reply をブロック
- **clarification ループ超過**: 障害カード相当へエスケープ
- **パイプライン無応答**: `finalize_pipeline_response` → `system_error` カード（fail loud）
- ユーザー向け回答に env 名や Secrets 名は出さない

## Q: ルーティング観測と eval の場所

<!-- rag-keywords: 観測 eval dialogue_route shadow mismatch golden テスト fixture -->

**回答要点**

- ログ: `dialogue_route_dispatch`、`dialogue_route_execution`、`legacy_fallback_*`
- shadow: `scripts/measure_intent_router_shadow.py` — mismatch_kind 分類
- eval fixture: `concierge_intent_routing.yaml`、`concierge_boundary.yaml`、v2 golden 6 sessions
- 詳細設計: `docs/dev/CHAT_PIPELINE_V2.md`、`MEDICINE_QA_ROUTING.md`

## Q: 本番 v2 ロールバックの考え方

<!-- rag-keywords: ロールバック v2 OFF denylist カナリア 切り戻し -->

**回答要点**

- 運用チームが v2 全体または特定 sid を denylist で除外可能
- Router dispatch OFF → shadow 観測のみ（orchestrator 従来 dispatch）
- unified OFF → execution_lock なし（段階的切り戻し）
- ユーザー向け: 「障害時は運用チームがパイプライン設定を切り戻します」（フラグ名は出さない）

## Q: なぜ LLM で市販薬を選ばないのか（ルーティング文脈）

<!-- rag-keywords: LLM 市販薬 選ばない Physical ルールベース ルーティング medicine_qa 分離 -->

**回答要点**

- 症状 reco（rule_based_recommend）と medicine_qa（情報質問）は Router で **明示分離**
- 比較・副作用質問を症状 reco に入れないことで、LLM 創作薬名リスクを Physical 推奨本体から隔離
- medicine_qa もブランド CSV 文脈 + 構造化回答。最終 reco スコアリングは CSV 正本
- 関連: `08-technical-decisions.md`、`02-chat-pipeline-agents.md`

## Q: 市販薬候補が 0 件（no_candidates）のときどう答えるか

<!-- rag-keywords: no_candidates 候補なし 見つかりません physical_no_recommendation 該当する医薬品 -->

**回答要点**

- **What**: ルールベーススコアリングで CSV 候補 0 件 → `physical_no_recommendation`（Physical ルート維持）
- **Why**: エラー表示だけでは route が unknown になり、ユーザーに文脈のない拒否に見える
- **本文**: `physical_no_reco_guidance` が皮膚・耳鼻等のカテゴリ別に受診目安・追加質問を提示（**追加 LLM なし**）
- **NLU 前置**: `refine_nlu_symptoms_from_context` で「炎症」等の汎用 NLU を原文から補正し、0 件率を下げる
- **Trade-off**: 候補 0 でも Physical として丁寧に案内。実推奨リストはスコアリング改善で別途向上

**この場合は別 doc を参照**

- SSOT → `docs/dev/PHYSICAL_SYMPTOM_E2E.md`
- パイプライン → `docs/dev/CHAT_PIPELINE_V2.md`

## Q: 短文症状（蕁麻疹・耳が痛い等）のルーティング

<!-- rag-keywords: 短文 症状 Physical triage 蕁麻疹 耳が痛い refine NLU -->

**回答要点**

- **Tier1 fast-path**: コールドスタート・≤80 文字・明示症状で LLM triage をスキップ可能
- **Override**: Concierge greeting 誤判定時 `apply_explicit_symptom_triage_override` で Physical へ
- **NLU 補正**: ユーザー原文から canonical 症状（耳の痛み・じんましん等）をルールで追加
- **同義語**: スコアリングで 蕁麻疹 ↔ じんましん ↔ 発疹 を展開
- **検証**: `v2_tier1_short_symptom.yaml` + physical YAML 10（2026-08-08: 13/13 PASS）

**答えないこと**

- 個別テスト用フレーズのハードコード一覧（実装はパターン一般化）
