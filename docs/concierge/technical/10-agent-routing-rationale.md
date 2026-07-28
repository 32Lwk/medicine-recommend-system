# Concierge エージェント分岐 — 設計意図（Concierge SSOT）

## なぜマルチエージェントか

- **What**: Triage → 専門エージェント（Physical / Concierge / Ask / Store 等）へ振り分け
- **Why**: 症状相談・技術 FAQ・店舗案内・医薬品 Q&A で必要な根拠とトーンが異なるため
- **Trade-off**: ルーティング誤りのリスク → IntentRouter + 決定論ゲート + execution_lock で緩和
- **現状**: Chat Pipeline v2 + `IntentRouter` + unified routing が本番デフォルト

## 主要エージェント

| エージェント | 役割 |
|-------------|------|
| TriageAgent | 入力分類・振り分け |
| PhysicalOrchestrator | 症状→ルールベース市販薬推奨 |
| ConciergeAgent | 挨拶・技術/アプリ FAQ・更新履歴 |
| AskAgent | 推奨後の医薬品 Q&A |
| StoreInquiryAgent | 店舗・遺失物 |
| ExplanationAgent | 推奨理由の説明 |

## Q: マルチエージェントの全体像

<!-- rag-keywords: マルチエージェント 詳細 IntentRouter TriageAgent PhysicalOrchestrator ConciergeAgent dispatcher -->

**回答要点**

- **IntentRouter**: LLM + 決定論ゲートで Physical / Concierge / Store / Emotional 等に振り分け
- **AgentDispatcher**: Router 決定を triage category に写像し各 handler へ委譲（`src/dialogue/dispatcher.py`）
- **PhysicalOrchestrator**: 症状 NLU → ルールベース市販薬推奨（CSV スコア）
- **ConciergeAgent**: 挨拶・技術 FAQ・アプリ説明・更新履歴（Local RAG + SSOT）
- **ChatOrchestrator**: dispatch 未解決時の legacy fallback

## Q: Medicine QA と Concierge の境界

<!-- rag-keywords: Medicine QA Concierge 境界 症状 インフラ 比較 副作用 推奨後 -->

**回答要点**

- **症状入力・市販薬候補** → Physical / `rule_based_recommend`
- **医薬品比較・説明・選び方・成分・用法**（副作用が主題でない）→ Physical / `medicine_qa`
- **副作用・眠気・併用注意** → Physical / `medicine_side_effect_qa`（症状 reco に入れない）
- **推奨後の「この薬について」** → Physical / `medicine_followup_qa`（推奨履歴前提）
- **インフラ・規約・アプリ概要・更新履歴** → Concierge / `architecture`・`doc_*` 等
- **誤爆防止**: 「AWS と GCP の違い」は Concierge。「ロキソニンとイブの違い」は medicine_qa

## Q: follow-up と topic break の設計

<!-- rag-keywords: follow-up topic break sticky meta ファミリー changelog architecture 深掘り -->

**回答要点**

- **sticky 継続**: 同一 meta ファミリー（`suggest_meta_intent_family`）の深掘りは prior intent 継続
- **topic break**: 異ファミリー（changelog → architecture 等）は `layer1_topic_break` で新 intent
- **曖昧短発話**: 「詳しく」「もっと」→ Layer3 follow-up LLM または rule fallback
- **汎用「もっと詳しく」**: ファミリー未定時は prior 継承（changelog への誤ピンを防止）
- **優先順位**: `router_dispatch`（IntentRouter 明示決定）> sticky follow-up > Concierge regex 継続

## Q: medicine_qa と medicine_side_effect_qa の使い分け

<!-- rag-keywords: medicine_qa medicine_side_effect_qa 副作用 比較 選び方 違い 厳密 -->

**回答要点**

- **medicine_side_effect_qa**: 副作用・眠気・「〜て平気？」が主題。CSV → KB 補完
- **medicine_qa**: 比較・選び方・成分・用法・画像・複合 intent（副作用+写真等）
- **判定**: `is_strict_medicine_side_effect_question` で比較質問の副作用誤ルーティングを防止
- **execution_lock**: unified routing Layer1 で即決し、症状 reco や Concierge へ流れない

## Q: ルーティング誤り・低信頼時の挙動

<!-- rag-keywords: ルーティング 誤り 低信頼 clarification Unknown fallback shadow regression -->

**回答要点**

- **低 confidence**: guard が `clarification` を設定 → dispatch スキップ → 確認メッセージ
- **Unknown**: dispatch スキップ → ChatOrchestrator legacy 経路
- **handler None**: orchestrator fallback（`handler_fallback`）。TRIM ON でも許可
- **shadow regression**: triage 期待と Router 不一致を観測。gate_improvement / exempt は意図的改善
- **correction**: ユーザー訂正入力で新 route 再実行（1 POST = 1 実行）

## Q: なぜ Concierge に技術 FAQ を集約するか

<!-- rag-keywords: Concierge 技術 FAQ architecture なぜ 分離 Physical 混在 -->

**回答要点**

- **Why**: インフラ・デプロイ・API/SSE・マルチエージェント説明は RAG + SSOT 参照が必要で、症状 reco トーンと異なる
- **What**: `architecture` intent で `docs/concierge/technical/` + Local RAG を retrieve
- **Trade-off**: 「AWS と GCP」等の比較語が medicine_qa と競合 → layer1 topic break で解決
- **深掘り KPI**: greeting 禁止、技術語彙または前ターン topic 参照必須

### 例外・境界（詳細）

<!-- rag-keywords: 例外 境界 発熱 Store QA gate execution_lock counseling follow-up -->

**Physical vs Concierge（典型パターン）**

| 入力例 | 期待 route | 落とし穴 |
|--------|-----------|---------|
| 「頭痛い」 | Physical / rule_based_recommend | — |
| 「ロキソニンとイブの違い」 | medicine_qa | 副作用 QA や Concierge へ誤ルーティング |
| 「ロキソニン眠くなる？」 | medicine_side_effect_qa | 睡眠障害 escalation へ入れない |
| 「このアプリの仕組みは？」 | Concierge / architecture | Physical へ入れない |
| 「先週の更新内容は？」→「技術面を詳しく」 | Concierge / architecture（topic break 可） | changelog 固定継続を禁止 |
| 「AWS と GCP の違い」（メタ文脈後） | Concierge / architecture | medicine_qa 比較へ誤爆 |
| 推奨後「さっきの薬の飲み方」 | medicine_followup_qa | 推奨履歴なし指示語のみ → clarify |

**follow-up 境界**

- prior=architecture + 「もっと詳しく」→ architecture 継続（sticky）
- prior=doc_changelog + 「デプロイの話」→ topic break → architecture
- prior なし + 短い「詳しく」→ follow-up LLM が prior 推定。rule fallback は prior intent を sub_route に反映
- counseling 文脈フォローアップ（期間・状況回答）: Router=Counseling、triage=Ask/Physical は shadow exempt

**Store / Emergency / SessionOps 境界**

- 発熱コンテキスト中の Store → guard が fever_flow へ上書き
- Emergency gate は confidence 1.0 で即決
- SessionOps（delete/summarize/status）は triage Other + session_admin から Router 独立判定可

### 例外処理（IntentRouter 誤判定・実行層フォールバック）

<!-- rag-keywords: IntentRouter 誤判定 execution_lock QA gate dispatcher 上書き 防止 -->

**execution_lock による上書き防止**

- unified routing が `execution_lock=True` を付与した決定は `_routing_execution_lock` として session に記録
- Concierge regex や meta triage が Router 決定を上書きしない（2026-07 以前の問題を解消）
- dispatch ログの `dialogue_route_execution` で dispatch_sub_route と resolved intent の mismatch を観測

**QA gate による Concierge 切替**

- Physical dispatch 内で `resolve_medicine_qa_route` が CONCIERGE を返した場合、Concierge handler へ切替
- 例: 医薬品名を含むが実質アプリ/規約質問の境界ケース

**dispatch 失敗時の段階的 fallback**

1. `try_agent_dispatch` → handler 実行
2. None / clarification / Unknown → orchestrator
3. orchestrator 未解決 → category 別 legacy（店舗・Other 等）
4. 終端 guard → `system_error`（無応答防止）

**LLM Router 不可時**

- follow-up LLM 失敗 → `_rule_based_follow_up`（prior 継続 / topic break rule）
- IntentRouter LLM OFF → gate + triage マップのみ
- OPENAI 未設定 → LLM 依存 reply ブロック + Sage 障害カード

**観測と改善サイクル**

- shadow mismatch: regression / gate_improvement / exempt 分類（`shadow_mismatch.py`）
- eval: `tests/fixtures/concierge_intent_routing.yaml`、`concierge_boundary.yaml`、v2 golden 6 sessions
- ログ: `dialogue_route_dispatch`、`dialogue_route_execution`、`legacy_fallback_*`
