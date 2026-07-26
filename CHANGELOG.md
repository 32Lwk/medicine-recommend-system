# 開発履歴・更新日誌

**最終更新日: 2026年7月26日**（セッション内ブランドピン・技術 Q&A 根拠強化）

---

## 2026-07-26 — セッション内ブランドピン・技術 Q&A 文脈／根拠強化

### 概要

AWS ログ解析で顕在化した **(1) 比較 Q&A の製品ライン揺れ** と **(2) 技術質問が更新履歴・誤構成に引きずられる問題** を、フレーズ列挙ではなく **セッション文脈 + IntentRouter 優先 + SSOT/RAG 根拠** で改善。

### Medicine QA — セッション内ブランドピン

| 項目 | 内容 |
|------|------|
| 新規 | `src/services/medicine_qa_session_pins.py` — `qa_brand_pins` を session / user_attributes に保持 |
| 解決 | `resolve_brand_hints_in_query(..., session=)` がピン優先。明示製品名のみ上書き |
| 配線 | `chat_with_medicine_context` / `chat_medicine_qa_html` / followup が session を渡す |
| 照合 | 全角／半角英数 fold（`ロキソニンＳ`↔`ロキソニンS`, `パイロンＰＬ`↔`パイロンPL`） |

**効果**: 「バファリン」比較の再質問で A ↔ プレミアムが入れ替わる揺れを抑制。

### Concierge 技術 Q&A — sticky 回避と根拠

| 問題 | 対応 |
|------|------|
| IntentRouter は `architecture` なのに sticky follow-up が `doc_changelog` / `app_about` を優先 | `resolve_concierge_intent` で **router_dispatch を sticky より先に採用** |
| changelog 後の独立質問が継続扱い／同一話題の深掘りまで切れる | `suggest_meta_intent_family` で話題ファミリー単位に判定。同一ファミリー深掘りは sticky、異ファミリーは topic break。汎用「もっと詳しく」はファミリー未定で prior 継承 |
| 日常口語・英語混じり・会話シミュレーションで意図取りこぼし | 症状クラス／年齢ライフステージ／併用・外観の一般化。会話フィラーを薬剤エンティティ誤認しないよう `_is_drug_like_token` を拒否寄りに。layer1 でメタ topic break を medicine_qa より優先（AWS/GCP「違い」誤爆防止） |
| 非 deep で ops ドキュメント未注入 → 運用事実の推測回答 | architecture は **常に technical + ops SSOT**。AWS/GCP 等の運用質問を deep 相当に |
| Local RAG の技術コーパス不足 | ops（LOCAL_RAG / GCP ADR / Cloud Run LLM env 等）+ `docs/dev` を index。architecture pool に `local/dev/` 追加 |

### テスト

- `tests/services/test_medicine_qa_session_pins.py`
- `tests/routing/test_meta_topic_break_flexible.py`
- 既存 parity / brand resolve / medicine_qa_routing

### 検証メモ（ローカル）

```
比較「違い」→ medicine_qa / 眠気 → medicine_side_effect_qa（layer1）
同一セッションでバファリン代表製品がピン固定
eval_medicine_qa_robustness（everyday+context+conversation_sim+meta）153/153
eval_medicine_qa_e2e（local KB）19/19
meta topic everyday pytest + follow-up / brand pin
※ ライブ GPT 会話は OPENAI_API_KEY がある環境で --with-gpt-conversation
```

---

## 2026-07-26 — Medicine QA 製品画像・比較セクション UI

### 概要

医薬品相談（`medicine_qa`）の **製品比較・選び方・パッケージ画像** 表示を Sage Terrace UI で統一。ストリーミング経路でも画像 HTML を付与し、LLM の「見せられない」回答をサーバー生成文案に置き換える。

### 比較・選び方セクション（`medicine_qa_routing.py`）

| 改善 | 内容 |
|------|------|
| HTML 構造化 | `_qa_product_line_html` — 製品名と「：」が改行で分断されない `ui-qa-product-line` |
| NSAIDs 括弧 | 製品比較から `（NSAIDs…）` 表記を削除（用途は `_short_medicine_use_hint` で簡潔化） |
| 選び方 | `_pick_hint_for_medicine` — ロキソプロフェン＝効き目重視、イブプロフェン＝マイルド |
| focus 排他 | `product_image` intent 時は `comparison` を付けない（画像質問に比較セクションが混入しない） |

### 製品画像（`medicine_qa_images.py`）

| 項目 | 内容 |
|------|------|
| UI | 推奨カルーセル同型の `ui-med-image--card` + Noimage（`medicine-noimage-hero.png` / `onerror`） |
| レイアウト | グリッド（1 製品 max 240px / 2 製品 2 列）— `sage_terrace.css` / `shell.css` |
| 回答文案 | `build_product_image_answer_text` — LLM 出力に依存せずサーバー統一生成 |
| 未準備 | 「見せられない」ではなく **「まだ準備できていません」** + 成分・用途 1 文 |
| 一部のみ準備済 | 製品名を明示（例: 「ロキソニンSを表示しました。イブはまだ準備できていません。」） |
| 3 製品以上混在 | 「A、B、Cのうち、A、Bを表示しました。Cは…」形式 |
| 準備判定 | `medicine_has_ready_image` — `otc_image_versions.json` 登録 or 管理外 https |

### ストリーミング配線（`medicine_response_builder.py`）

- `_finalize_structured_qa_response` — JSON / SSE ストリーム両経路で `attach_product_images_to_response` + 統一 answer
- `_apply_product_image_answer` — `product_image` focus 時は常に `build_product_image_answer_text` を適用
- 画像 intent 用 answer プロンプト — 「見せられない」禁止・準備中表現を指示

### テスト

```bash
.venv/bin/pytest tests/routing/test_medicine_qa_sections.py \
  tests/services/test_medicine_qa_images.py \
  tests/services/test_medicine_image_urls.py -q
```

詳細: [`docs/dev/MEDICINE_QA_ROUTING.md`](docs/dev/MEDICINE_QA_ROUTING.md)（製品画像セクション）

### OTC 画像 manifest（同期作業）

- `data/otc_image_versions.json` — CDN キャッシュバスティング用 slug 追加
- `scripts/sync_top50_otc_images.py` / `scripts/sync_otc_images_retry.py` / `scripts/otc_image_multi_source.py`
- 成果物: `log/analysis/otc_image_sync_bulk/`

---

## 2026年7月26日 — Medicine QA ロバストネス・Local RAG・文脈 routing

### 概要

医薬品 Q&A の **日常口語・方言・指示語 follow-up・複合 intent** に耐える routing を一般化。Local RAG（BM25 + 文脈 query）と multi-focus retrieve を統合し、**固定 eval 43/43・GPT 会話 + LLM stress 含む 75 問中 74+ PASS** を達成。

### Medicine QA routing（`medicine_qa_routing.py`）

| 領域 | 内容 |
|------|------|
| エンティティ解決 | 通称・略称・成分・履歴・推奨を `_resolve_medicine_entities` で統合 |
| 比較 intent | 現発話ベースの `_distinct_brand_count`（履歴 2 剤による指示語 follow-up 誤比較を防止） |
| 併用 intent | アルコール（ワイン/ビール等）+ 文脈 suitability（`_has_interaction_intent`） |
| 用法 intent | 頻度・「どのくらい」+ 指示語 follow-up（副作用因果「飲むと眠い」と分離） |
| 年齢 / ドーピング | 履歴 slot（小学 N 年 / マラソン）+ 可否確認 |
| 効き目+副作用 | 推奨文脈の複合質問 → unified `medicine_qa` |
| 情報質問 gate | focus 特定 + 文脈 slot で entity なしも通過（指示語のみ・履歴なしは clarify 維持） |
| LLM 補完 | `medicine_qa_focus_llm.py` — `MEDICINE_QA_FOCUS_LLM=1` 時、rule が `general` のみなら LLM で focus 推定 |

**ハイブリッド arbitration**（変更なしの原則）: 単独副作用 → `medicine_side_effect_qa` / 複合・比較・写真等 → `medicine_qa`

詳細: [`docs/dev/MEDICINE_QA_ROUTING.md`](docs/dev/MEDICINE_QA_ROUTING.md)

### Local RAG（Phase A–C）

| コンポーネント | 役割 |
|----------------|------|
| `local_rag_retrieve.py` | BM25 + 任意 hybrid embed retrieve |
| `local_rag_context.py` | 会話履歴から substance / query rewrite |
| `local_rag_query.py` | 口語正規化・カテゴリ推論（文脈 weight） |
| `local_rag_router.py` | QA focus → RAG category 橋渡し、multi-doc |
| `bedrock_kb_retrieve.py` | provider 切替 + `qa_focuses` KB 注入 |

**GO 条件（2026-07-26 検証）**

| 評価 | 結果 |
|------|------|
| Medicine KB local | 20/20 |
| paraphrase | 19/19 |
| diverse + context | 52/52 |
| broad | 28/28 |
| Medicine QA E2E | 19/19 |
| **Robustness 固定** | **43/43** |
| **Robustness + GPT + LLM stress** | **74/75 (98.7%)** |
| routing pytest | 180 passed |
| retrieve P95 | 286ms |

詳細: [`docs/ops/LOCAL_RAG.md`](docs/ops/LOCAL_RAG.md) / `log/analysis/verify_medicine_qa_rag_20260726.md`

### 新規 eval / fixture

| スクリプト | 内容 |
|------------|------|
| `scripts/eval_medicine_qa_robustness.py` | 日常表現 31 + 文脈 12 + 任意 GPT 会話 + `--with-llm-stress` |
| `scripts/eval_medicine_qa_e2e.py` | Medicine QA 配線 E2E 19 問 |
| `scripts/eval_local_rag_*.py` | paraphrase / diverse / broad / e2e |
| `scripts/run_local_rag_eval.sh` | 一括 eval（CodeBuild 連携） |

Fixtures: `tests/fixtures/medicine_qa_everyday_eval.yaml`, `medicine_qa_gpt_conversation.yaml`, `local_rag_*`

### UI / 配線

- `medicine_qa_html.py` / `chat_medicine_qa_html.py` — 製品写真・multi-focus セクション
- `flex_messages.py` — LINE Flex QA hero
- `dispatcher.py` / `chat_post_pipeline.py` — session 文脈付き focus 推定

---

## 2026年7月26日 — PMDA OTC Cloud 完走・KB re-ingest・orphans 分析クローズ

### 概要

Cloud Agent（`cursor/pmda-otc-live-fetch-07ea`）で **OTC 7,495 品目の PMDA live 完走**（~14.5h）を main にマージ。続けて **C-3（S3 sync → Bedrock re-ingest → eval）** を実施。orphans 1,240 件の分析を記録し **受け入れクローズ**。

### PMDA OTC Cloud live（Phase 2）

| 指標 | 値 |
|------|-----|
| otc pending | **0**（done 6,011 / orphans 1,240 / 82.9%） |
| CSV | **7,495 行保持**（PMDA 優先 merge） |
| HTTP | 13,929 / errors 0 / ~14.5h |
| Cloud GO/NO-GO | GO（403/429=0） |
| pytest | pmda 13 + golden 45 passed |

**新規スクリプト**: `run_live_fetch_otc_cloud.py`, `archive_otc_pmda_applied.py`, `test_pmda_otc_parse.py`

**95% ヒット率**: 未達（PMDA 未掲載品 ~17%）。orphans は baseline CSV 100% 保持 → **再 fetch 不要**と判定。

詳細: [`docs/ops/PMDA_DATA_IMPORT.md`](docs/ops/PMDA_DATA_IMPORT.md) / `log/analysis/pmda_cloud_otc_complete_20260725.json`

### orphans 1,240 — クローズ

| 項目 | 内容 |
|------|------|
| 判定 | **closed_accepted** |
| 主因 | PMDA 未掲載 / 短ブランド名 / 正規化不足（205 件） |
| カテゴリ偏り | なし（~15–20%/カテゴリ） |

`log/analysis/pmda_otc_orphans_analysis_20260726.json`

### C-3 Medicine KB 反映

| 指標 | 値 |
|------|-----|
| ingestion | **GYSI8GXCRO** COMPLETE（failed 0） |
| modified docs | 19,921 |
| eval pass_all | **65%**（13/20）— 目標 80% **未達** |
| eval score_pass | 70% |
| 相互作用 eval | **5/5** 維持 |

OTC bulk 更新後、usage / sideeffect / doping / age 系 retrieval が低下。データ正本・ingestion は成功。eval 改善は follow-up。

`log/analysis/medicine_kb_pmda_reflect_20260726.json` / `medicine_kb_pmda_eval_20260726.json`

### Phase 1 正本（ix/se reparse）— 引き続き有効

| CSV | 合計 | PMDA | 品質 |
|-----|------|------|------|
| interactions | 180 | 107 | 100% OK |
| side_effects | 271 | 237 | 100% OK |

---

## 2026年7月25日 — SSE 副作用 Q&A 表示復旧・医薬品比較 Q&A・CodeBuild post_deploy 高速化

### 概要

AWS ステージングで **「ロキソニンって眠くなる？」** 等の副作用 Q&A がバックエンド正常完了後も **処理バブル（AI分析中）のまま** になる不具合を修正。あわせて **医薬品比較 Q&A ルーティング**・**ブランド通称レジストリ**・**副作用 UI**、および CodeBuild **post_build 高速化（精度維持）** を反映。

### SSE `done` — 副作用 Q&A UI 表示復旧（commit `39d4d39`）

| 症状 | 原因 | 修正 |
|------|------|------|
| 処理バブルが消えず bot 返信なし | `finalize_medicine_qa_response` が DB 保存後 `del session["messages"]` | 保存後 **DB から in-memory を再同期** |
| SSE `done` に `bot_message: null` | `chat_stream.py` が空 in-memory から `done` 組み立て | `_messages_for_sse_done()` で **DB フォールバック** |

**経路**: `medicine_side_effect_qa` は `qa_delta` 非対応のため **`done` イベント依存**（`qa_delta` がある経路は従来どおり）。

| ファイル | 変更 |
|----------|------|
| `src/handlers/chat/chat_medicine_qa_html.py` | DB 保存後 `session["messages"]` 同期 |
| `src/handlers/chat/chat_stream.py` | `_messages_for_sse_done()` |
| `tests/chat/test_chat_stream_api.py` | SSE done + DB フォールバック |
| `tests/integration/test_medicine_qa_flow.py` | 副作用 Q&A フロー |

**検証**: AWS ログ解析（`log/analysis/2026-07-25_downloaded-aws-logs-*.md`）でバックエンド応答正常を確認後、ステージング再現 → 修正。

### 医薬品 Q&A ルーティング（比較 vs 副作用）（commit `cdad315`）

| 問題 | 原因 | 修正 |
|------|------|------|
| 比較質問 → 副作用 CSV ダンプ | `is_medicine_side_effect_question` の演算子優先順位バグ（`?` 末尾 + 薬名 → 副作用判定） | 厳密判定へ委譲（`medicine_qa_routing.py`） |
| 比較質問 → 汎用補足テンプレ | `_build_structured_qa_from_stream` が固定テンプレを注入 | `build_focused_qa_sections` + `prune_qa_response` |
| 「イブ」→ ケイブク | 製品名 **部分一致**（`in`） | **先頭一致** + ブランドレジストリ |

**新 sub_route**: `medicine_qa` — LLM ベース `chat_with_medicine_context`（推奨履歴なし可）

**主要ファイル**:

| ファイル | 役割 |
|----------|------|
| `src/services/medicine_qa_routing.py` | 副作用 vs 情報質問の切り分け、補足焦点推定 |
| `src/services/medicine_brand_resolve.py` | `BRAND_RESOLVE_RULES` レジストリ（通称 → 代表製品） |
| `src/dialogue/routing/unified_router.py` | Layer1: `medicine_qa` / `medicine_side_effect_qa` |
| `src/handlers/chat/chat_post_pipeline.py` | early route: 比較 → `medicine_qa` |
| `src/core/medicine/medicine_response_builder.py` | CSV 検出 → LLM 文脈、ブランド解決統合 |

**テスト**: `tests/routing/test_medicine_qa_routing.py`, `test_medicine_qa_sections.py`, `tests/services/test_medicine_brand_resolve.py`, `tests/dialogue/routing/test_unified_router_medicine_qa.py`

### ブランド通称レジストリ（`BRAND_RESOLVE_RULES`）

11 ブランド / 12 ヒントを登録。`context_signals._MEDICINE_BRAND_HINTS` はレジストリから自動生成。

| 通称 | 代表製品（例） | 備考 |
|------|----------------|------|
| イブ / アドビル | イブ | 成分: イブプロフェン |
| ロキソニン | ロキソニンＳ | preferred 順でフラッグシップ選択 |
| PL | パイロンＰＬ錠 | `product_name_contains` |
| ペタミン | カロナールＡ | CSV 未掲載時の成分フォールバック |

詳細: [`docs/dev/MEDICINE_BRAND_RESOLVE.md`](docs/dev/MEDICINE_BRAND_RESOLVE.md)

### 副作用 Q&A UI

| 項目 | 内容 |
|------|------|
| `src/services/side_effect_display.py` | PMDA/CSV 副作用原文 → チップ・折りたたみ HTML |
| `static/css/sage_terrace.css` | `.ui-side-effect-*` スタイル |
| `static/js/ui/ui_strings.js` | 副作用バッジ i18n |
| `src/services/status_diagnosis_builder.py` | `build_side_effect_qa_from_chat_response`、QA 補足の焦点タイトル |

### AWS CodeBuild post_deploy 高速化（精度維持）

| 変更 | 内容 |
|------|------|
| `buildspec.yml` | post_build を `scripts/codebuild-post-deploy.sh` に委譲 |
| `scripts/lib/codebuild_deploy_paths.py` | git diff / CodePipeline 前回 commit / GitHub compare → 変更パス分類 |
| `scripts/wait-staging-health-commit.sh` | `/health` で **live commit** 待ち（`services-stable` より早く正確） |
| `scripts/codebuild-post-deploy.sh` | 条件付き static/KB sync + **並列** SSOT + **毎回フル smoke** |
| `scripts/aws-staging-smoke.sh` | `SKIP_HEALTH_WAIT=1`（二重待ち回避、commit 再確認あり） |
| `scripts/setup-aws-codepipeline.sh` | Source `CODEBUILD_CLONE_REF`（git diff 用） |
| `tests/ops/test_codebuild_deploy_paths.py` | パス分類 10 件 |
| `docs/ops/AWS_CODEPIPELINE.md` | 高速 post_build・フォールバック方針 |

**精度維持の原則**: 変更ファイルが特定できない場合は **従来どおり全 sync**。smoke / SSOT 検証は **毎回実行**。

**目安**: backend のみ push 時 ~11 分 → **~6〜7 分**（static/KB sync スキップ時）

**残作業（AWS）**: Pipeline Source を `CODEBUILD_CLONE_REF` に更新（admin `iam:PassRole`）。未更新時は GitHub compare → 不明なら全 sync フォールバック。

---

## 2026年7月25日 — NLU/ルーティング統合（Unified Pipeline）・副作用 QA・AWS ログ分析

### 概要

AWS ステージングログで特定した **Concierge follow-up 乖離**（`doc_changelog` 固定）と **ロキソニン副作用 QA の誤 escalation** を、Intent Router v2 有効時に **一括 ON** する 3 層ルーティングで修正。あわせて **AWS CloudWatch ログ分析パイプライン**（GCP 相当）を追加し、ゴールデン 6 セッションを local-v2-chat-test で再検証（**8/8 自動合格**）。

### ルーティング改善（Intent Router v2 サブフラグ一括 ON）

| フラグ | 用途 |
|--------|------|
| `ROUTING_UNIFIED_PIPELINE` | Layer1 シグナル + follow-up LLM + legacy router の統合（`RoutingDecision.execution_lock`） |
| `ROUTING_MEDICINE_SIDE_EFFECT_QA` | 「A って眠い？」等の副作用 QA 専用 route（症状 escalation へ入れない） |
| `ROUTING_FOLLOWUP_LLM` | 曖昧短文 follow-up の LLM 判定 |
| `PERF_META_SAFETY_SHORTPATH` | meta 経路の safety_gate 短縮 |
| `ROUTING_MEDICINE_SIDE_EFFECT_KB` | CSV 未ヒット時 Bedrock KB 補完 |

**主要ファイル**: `src/dialogue/routing/unified_router.py`, `routing_decision.py`, `follow_up_llm.py`, `src/handlers/chat/medicine_side_effect_handlers.py`, `src/services/concierge_execution_sync.py`

**観測性**: `dialogue_route_execution` 構造化ログ、`side_effect_qa_mishandled` ヒューリスティック（AWS/GCP 解析共通）

### バグ修正（副作用 QA）

- `finalize_medicine_qa_response`: DB 保存後に session cookie から `messages` を削除する際、`mark_pipeline_turn_bot_appended` を呼び **pipeline end guard の誤 `system_error` を防止**
- `main._enrich_v2_test_chat_body`: v2 テスト UA 向け POST 応答に **DB フォールバック付き `latest_bot`** を同梱

### AWS ログ分析基盤

| 種別 | パス |
|------|------|
| エクスポート/解析 | `src/analysis/aws_log_export.py`, `aws_cloudwatch_log_parser.py` |
| CLI | `scripts/export_aws_logs.py`, `analyze_aws_logs.py`, `prepare_aws_log_analysis.py` |
| スキル | `.cursor/skills/aws-log-analysis/SKILL.md` |
| 統合レポート | `log/analysis/2026-07-25_downloaded-aws-logs-*.md` |

### ゴールデン再検証（local-v2-chat-test）

| シナリオ | セッション末尾 | 結果 |
|----------|----------------|------|
| about / architecture / AWS-GCP（changelog 後） | …8283 | PASS（`concierge_app_about` / `concierge_architecture`、changelog 繰り返しなし） |
| ロキソニン副作用 QA | …3443 / …2059 | PASS（`sage_qa`、睡眠改善 escalation なし） |
| 回帰 good | …6483 / …2070 / …1951 | PASS |

フィクスチャ: `tests/fixtures/v2_golden_aws_6_sessions.yaml`  
実行: `python scripts/local_v2_chat_test_runner.py --scenarios-path tests/fixtures/v2_golden_aws_6_sessions.yaml --report-suffix golden-aws-6-final`

---

## 2026年7月25日 — OTC 画像（トキワ公式）・推奨除外・TTS/UI・静的アセット

### 概要

マツキヨ未掲載の **トキワイブプロエースＡ** を常盤薬品公式画像で R2 に配置。**イブプロフェン錠200S / 200SC** は OTC CSV に残しつつ推奨候補から除外（EC 未掲載・画像なし・ジェネリック名で購入特定が困難なため）。あわせて Sage UI の **CHANGELOG 表示・TTS（Polly SSML / Web Speech）** と **localhost 限定の `/static/` 配信**を改善。

### OTC 商品画像 — 上位50品目一括同期（推奨ログ + Amazon 定番 → R2）

推奨ログ頻度上位と Amazon 健康・パーソナルケア定番 OTC を統合した **50 品目**のパッケージ画像を R2 に配置。**2026-07-25 時点で 50/50 CDN 確認済み**（`https://images.yutok.dev/otc/{slug}.webp`）。

| 項目 | 値 |
|------|-----|
| 選定 | 推奨ログ TOP（`recommendation_detail_log.jsonl` 等）+ Amazon 定番（イブ・バファリン・パブロン・ルル等） |
| マツキヨ | 掲載あり → `sync_otc_images_from_matsukiyo` 経由 / 未掲載 → 公式 or 薬局 EC フォールバック |
| 審査 | 解像度・ファイルサイズ・製品名一致（`verify_image_match`、スコア ≥55） |
| スクリプト | `scripts/sync_top50_otc_images.py` |
| 計画・成果物 | `log/analysis/otc_image_sync_top50/top50_plan.json` / `top50_results.json` / `results_batch*.json` |

```bash
# 計画に基づき未取得分を取得・審査・アップロード（.env の R2_* 必須）
.venv/bin/python scripts/sync_top50_otc_images.py --batch 0 --upload

# バッチ分割（12件ずつ）
.venv/bin/python scripts/sync_top50_otc_images.py --batch 1 --batch-size 12 --upload

# バッチ結果の統合サマリー
.venv/bin/python scripts/sync_top50_otc_images.py --merge-only
```

**ソース内訳（50品）**:

| 区分 | 件数 | 主な取得元 |
|------|------|------------|
| 推奨ログ頻出（マツキヨ掲載） | 15 | マツキヨココカラ online |
| Amazon 定番 OTC | 11 | メーカー公式（SSP microcms、Lion AEM、大正 catalog 等） |
| 推奨ログ頻出（マツキヨ未掲載） | 24 | 公式（all-p.co.jp 等）+ 楽天薬局 CDN（`shop.r10s.jp`）+ Yahoo ショッピング |

審査で却下された画像は `static/otc/review_rejected/{slug}.webp` に退避（今回 **review_rejected 0 件**）。

詳細: [docs/ops/CLOUDFLARE_R2_IMAGES.md](docs/ops/CLOUDFLARE_R2_IMAGES.md#上位50品目一括同期)

### OTC 商品画像 — トキワイブプロエースＡ（公式ソース → R2）

| 項目 | 値 |
|------|-----|
| ソース | `https://www.tokiwayakuhin.co.jp/img/goods/L/H177300.jpg` |
| R2 キー | `otc/トキワイブプロエースA.webp` |
| 公開 URL | `https://images.yutok.dev/otc/トキワイブプロエースA.webp` |
| マツキヨ | 未掲載（JAN `4987156250120` でもヒットなし） |

手動アップロード例:

```bash
py -3.11 scripts/upload_r2_otc_image.py トキワイブプロエースA \
  log/analysis/otc_image_candidates/トキワイブプロエースA_tokiwa_L.jpg
```

### 推奨除外 — イブプロフェン錠200S / 200SC

**方針**: `data/otc_medicine_data.csv` からは**削除しない**（JAPIC/KEGG 上は実在する正本データ）。**ルールベース推奨の候補プールのみ除外**。

| 製品 | 除外理由 | 代替推奨 |
|------|----------|----------|
| イブプロフェン錠２００Ｓ（奥田製薬） | ジェネリック名・EC 未掲載・画像なし | トキワイブプロエースＡ、イブ/EVE 系 |
| イブプロフェン錠２００ＳＣ（セントラル製薬） | 同上 | 同上 |

**実装**:

| ファイル | 内容 |
|----------|------|
| `src/core/recommendation_constants.py` | `RECOMMENDATION_EXCLUDED_PRODUCTS` リスト追加 |
| `src/core/medicine_classifiers.py` | `is_recommendation_excluded_product()` |
| `src/core/candidate_scoring.py` | `get_candidate_medicines()` の `append_candidate` で除外 |
| `src/core/rule_based_recommendation.py` | 候補フィルタ段でも二重除外 |
| `tests/core/test_recommendation_excluded_products.py` | 除外・類似品非除外のテスト |

詳細: [docs/ops/RECOMMENDATION_PRODUCT_FILTERS.md](docs/ops/RECOMMENDATION_PRODUCT_FILTERS.md)

### UI / TTS / CHANGELOG 表示（commit `ff956ac`）

| ファイル | 内容 |
|----------|------|
| `src/content/changelog_digest.py` | ユーザー向け文言サニタイズ・前向きリライト強化 |
| `static/js/ui/status_renderer.js` | ステータス/更新履歴バブルの表示改善 |
| `static/js/ui/tts_builder.js` | バブル単位 TTS テキスト構築 |
| `static/js/ui/recommendation_renderer.js` | 推奨カード読み上げ連携 |
| `src/services/polly_ssml.py`（新規） | Polly 向け SSML（句読・日付見出しに `<break>`） |
| `src/services/polly_tts.py` | SSML 合成パス追加（`POLLY_SSML` で OFF 可） |
| `static/css/sage_terrace.css` / `main.css` | 音声ボタン SVG・レイアウト調整 |

### 静的アセット — localhost のみ `/static/` 優先

**問題**: `APP_ENV=development` の dev 環境全体で CloudFront ではなくローカル `/static/` を使うと、`aws.medicine.yutok.dev` 等でも CDN がバイパスされ古い JS が読み込まれる。

**修正** (`config/static_assets.py`):

- **localhost / 127.0.0.1 リクエスト時のみ** middleware が `prefer_local_static` を立て、CDN の代わりに `/static/` を返す
- `LOCAL_STATIC_ASSETS=1` 環境変数でも強制可能
- dev ホスト（`aws.medicine.yutok.dev`）は **CloudFront を継続利用**

**テスト**: `tests/config/test_aws_features.py` — development + 非 loopback で CDN URL を返すケース追加

### AWS / GCP dev — `APP_ENV=development` 統一

| ファイル | 内容 |
|----------|------|
| `scripts/set-dev-app-env.sh`（新規） | AWS ECS Express + GCP Cloud Run の `APP_ENV` を一括 `development` に |
| `scripts/update-aws-express-env.sh` | `APP_ENV` を merge キーに追加 |
| `scripts/setup-aws-ecs-secrets.sh` 等 | 未設定時デフォルトを `development` に |

```bash
./scripts/set-dev-app-env.sh          # AWS + GCP
./scripts/set-dev-app-env.sh aws      # AWS のみ
```

### ドキュメント

- **`docs/ops/CLOUDFLARE_R2_IMAGES.md`**: マツキヨ未掲載品の公式ソース手動アップロード手順、**上位50一括同期**手順
- **`docs/ops/RECOMMENDATION_PRODUCT_FILTERS.md`（新規）**: 推奨除外リストの運用
- **`docs/ops/AWS_FEATURES_ROLLOUT.md`**: localhost 静的アセット・`APP_ENV` dev 手順追記

### 今後の改善候補（未実装）

- イブプロフェン錠200S のパッケージ画像（JAN 判明時 or ユーザー提供素材）
- `RECOMMENDATION_EXCLUDED_PRODUCTS` の設定ファイル化（CSV / YAML）
- 上位50以外の推奨頻度品目の継続同期（`sync_otc_images_from_matsukiyo --limit 200` の定期実行）

---

## 2026年7月24日 — PMDA 正本 → Medicine KB 反映（§17 フィルタ・reflect 実行）

### 概要

§11 副作用パーサーに **§17 臨床成績** 終端を追加し、品質フィルタ **`section17_leak`** で混入行を reject。正本 CSV を再生成後 **`scripts/reflect_medicine_kb.sh`** で Medicine Managed KB へ反映。**ingestion job `OG6SSAO4QN` COMPLETE**、eval **相互作用 5/5**。

### §17 品質改善

| 項目 | 修正前 | 修正後 |
|------|--------|--------|
| side_effects PMDA 行 | 238 | **237** |
| side_effects CSV 合計 | 272 | **271**（手動 34 + PMDA 237） |
| §17 末尾混入行 | ~6 行 | **0** |

**変更**: `http_client.py`（`_SECTION11_END` + 要約時 §17 切り捨て）、`quality_filter.py`（`section17_leak`）

### KB 反映（job `OG6SSAO4QN`）

| 指標 | 値 |
|------|-----|
| scanned | 19,952 |
| modified | 19,859 |
| new | 87 |
| deleted | 318 |
| failed | 1（`side_effects/グリチルレチン酸.md` — CSV 除外済み stale メタデータ） |

**eval**（`log/analysis/medicine_kb_pmda_eval_20260724.json`）: pass_all **75%**（15/20）/ score_pass **85%** / 相互作用 **5/5**

```bash
AWS_PROFILE=admin AWS_REGION=ap-northeast-1 ./scripts/reflect_medicine_kb.sh
```

成果物: `log/analysis/medicine_kb_pmda_reflect_20260724.json`, `pmda_reparse_from_raw_20260724.json`

---

## 2026年7月24日 — Step 5-F 完了（CodePipeline KB 検証）

### 概要

Dual KB RAG Phase 5 の最終検証。**ingestion failed=0**、Medicine / Concierge eval が CI 閾値を満たし、CodePipeline 上の KB sync も成功。

### ingestion（COMPLETE / failed=0）

| KB | Job ID | modified | new |
|----|--------|----------|-----|
| Concierge `2CNAGQ2V4P` | `GZJ6TQG4Y0` | 19,873 | 305 |
| Medicine `30BCEJCJHA` | `K7WQ4I4IZE` | 19,873 | 305 |

metadata boolean → string 修正後、product 7,494 件の failed は **解消済み**。

### eval（Step 5-F-2）

| 対象 | 結果 | 閾値 |
|------|------|------|
| Medicine raw | **16/20（80%）** | ≥80% ✅ |
| Medicine runtime | **17/20（85%）** | — |
| 相互作用 | **5/5** | hard gate ✅ |
| Concierge | **9/10（90%）** | ≥80% ✅ |

成果物: `log/analysis/medicine_kb_step5f_20260724.json`, `concierge_kb_step5f_20260724.json`, `codebuild_kb_step5f_complete_20260724.json`

残 NG（任意改善）: `usage-water-amount`, `doping-pseudoephedrine`, `doping-competition-category`, `age-under-15`, Concierge `changelog-phase-q4`

### CodePipeline / CodeBuild

| 項目 | 状態 |
|------|------|
| `SYNC_KB_TO_S3` | **`true`**（CodeBuild env） |
| `KB_INGESTION_ON_PUSH` | **`true`** |
| `RUN_KB_EVAL` | `false`（ingestion 安定後に週次化可） |
| Pipeline `14791919` | **Succeeded** — CloudWatch に `All KB sources synced.` |

**CodeBuild 修正**（`scripts/sync-all-kb-to-s3.sh`）:

- pyenv 回避 → `/usr/bin/python3.11` + `ensurepip` + `pip install pandas`
- PATH 制限時に **`aws` CLI を `/usr/local/bin` から復元**（132643c で aws 不在により sync 失敗していた問題を 138c0ff で修正）

**IAM**: `scripts/setup-aws-codebuild-kb-role.sh` — `StartIngestionJob` + S3 KB bucket

### 新規スクリプト

| ファイル | 用途 |
|----------|------|
| `scripts/reflect_medicine_kb.sh` | PMDA 正本 CSV → build → S3 sync → ingestion 待機 → eval の一括反映 |

---

## 2026年7月24日 — CHANGELOG ダイジェスト・ステータス UI 改善

### 概要

Concierge / ステータスパネルの「最近の更新」表示を、開発者向けノイズを減らしユーザー向け文言に整える。

### 変更

| ファイル | 内容 |
|----------|------|
| `src/content/changelog_digest.py` | PMDA / KB / eval 系の infra ノイズ除外、positive rewrite ルール追加、箇条書き上限 72 字 |
| `static/js/ui/status_renderer.js` | `＋` プレフィックス廃止 → ドット箇条書き |
| `static/css/sage_terrace.css` | `.ui-status-update-item` をミニマルなドット + テキストレイアウトに |
| `src/agents/concierge_agent.py` | コンパクト表示時の release / item 数を 2 件に抑制 |
| `tests/content/test_changelog_*.py` | 上記に合わせて更新 |

`scripts/write_changelog_digest.py` → `static/changelog-digest.json` を再生成し Concierge KB / S3 に同梱。

---

## 2026年7月24日 — PMDA 正本再生成（raw HTML 永続化・パーサー修正・品質フィルタ）

### 概要

PMDA live fetch で取得した **添付文書 HTML を `data/pmda/raw/` に永続化**し、パーサー根本原因（§マーカー空白不一致・全文フォールバック・merge バグ）を修正。**680 件 raw から正本 CSV を再生成**。方針は **live のみ（catalog expansion 復元なし）**。手動 curated 行（出典空欄）は保持。

### 品質（修正前 git HEAD → 再パース後）

| 指標 | interactions (PMDA) | side_effects (PMDA) |
|------|---------------------|---------------------|
| 行数 | 156 → **107** | 372 → **237** |
| 品質フィルタ OK 率 | 37.8% → **100%** | 1.3% → **100%** |
| HTML ボイラープレート | 多数 → **0** | 177 行 → **0** |
| CSV 合計 | 233 → **180**（手動 73 + PMDA 107） | 414 → **271**（手動 34 + PMDA 237） |

### パーサー修正（`scripts/pmda/http_client.py`）

- §10/§11 マーカーの **空白対応**（`10.2 併用注意` vs 旧 `10.2併用注意`）
- PMDA ページ **ボイラープレート除去**（JavaScript 案内・ヘッダー等）
- セクション未検出時の **全文フォールバック廃止**（空文字返却）
- §11 終端に **`17. 臨床成績` / `18. 薬効`** を追加（後半: §17 要約切り捨て + `section17_leak` フィルタ）
- interactions: partner 周辺 **最大 500 字**の §10 由来説明
- side_effects: **§11 要約**（最大 800 字・句点境界で切り詰め）

### 新規スクリプト・モジュール

| ファイル | 用途 |
|----------|------|
| `scripts/pmda/raw_store.py` | 成分別 raw JSON 保存・`index.json` 更新 |
| `scripts/pmda/reparse_from_raw.py` | raw 680 件 → staging → CSV merge（`--dry-run` 可） |
| `scripts/pmda/quality_filter.py` | merge 前ノイズ reject（HTML/§18/短すぎ等） |
| `scripts/pmda/requeue_missing_raw.py` | raw 未保存の done 成分を pending に戻す |
| `scripts/eval_pmda_bedrock.py` | 改善・正本の Bedrock 独立評価（任意） |
| `tests/scripts/test_pmda_parser.py` | §抽出・品質フィルタの単体テスト |
| `tests/scripts/test_pmda_raw_store.py` | raw 保存の単体テスト |

### merge バグ修正（`scripts/pmda/merge_into_csv.py`）

- `live_replace=True` 時、**旧 PMDA 行が残り続ける** OR 条件バグを修正
- 正しい挙動: **手動行（出典空欄）のみ保持 + 新 PMDA 行で全置換**

### raw 正本（`data/pmda/raw/`）

```
data/pmda/raw/
  index.json              # by_ingredient → ファイル名マップ（680 件）
  ingredients/{hash}.json # detail_html, section10/11 テキスト, fetched_at
```

- **680 ファイル**（`detail_html` あり 484 / `empty_section` 196）
- fetch 時 `fetch_ingredient_live.py` が `save_ingredient_raw()` を呼び出し
- **再パースは `detail_html` から**（保存済み `section10_text` は使わない）

### 再パース手順

```bash
# staging + validate のみ
.venv/bin/python scripts/pmda/reparse_from_raw.py --dry-run

# バックアップ → CSV merge（live_replace）
.venv/bin/python scripts/pmda/reparse_from_raw.py

pytest tests/scripts/test_pmda_parser.py tests/scripts/test_pmda_raw_store.py -q
```

### 方針変更

- **catalog expansion（~2,869 行テンプレート）は復元しない** — RAG/KB 上の情報価値が低く、重複テンプレが多数
- **live + raw 再パース** が正本の唯一の再生成経路
- purge → KB 前の残課題: interactions **複数薬剤混在**（~27/107）— 次イテレーションで §10 表行単位パース
- ~~side_effects §17 臨床成績混入~~ → **§17 終端 + section17_leak で解消**（2026-07-24 後半）

### ドキュメント

- **`docs/ops/PMDA_DATA_IMPORT.md`**: raw 永続化・reparse・品質ゲート・正本評価を追記
- **`data/DATA_CATALOG.md`**: `pmda/raw/` を追記

### 成果物（`log/analysis/`）

- `pmda_canonical_eval_report.json` — before/after 品質メトリクス
- `pmda_bedrock_eval.json` — Bedrock 評価（クォータ時は error 記録）
- `bedrock_eval_samples.json` — 評価用サンプル行

---

## 2026年7月24日 — Dual KB RAG Phase 1.5–5（ingestion 修正・パイプライン・Ask sanitize）

### 概要

AWS ステージング Managed KB（Concierge `2CNAGQ2V4P` / Medicine `30BCEJCJHA`）の RAG 品質向上と運用自動化の骨格を実装。**Medicine eval: raw 80%（16/20）/ runtime 85%（17/20）、相互作用 5/5 hard gate**。ingestion **failed 7,494 → 0**（metadata boolean → string 修正）。

### Phase 1.5 — Medicine KB 品質パッチ

**新規 / 更新**: **`scripts/build_medicine_kb_documents.py`**

- 7,494 製品 MD + interactions / side_effects / kanpo / efficacy
- **トピックガイド**: `medicine/topics/`（服用間隔・年齢制限・NSAID 高齢者）
- **ドーピングガイド**: `medicine/doping/pseudoephedrine.md`
- product MD 固定見出し（用法・用量 / 年齢制限 / ドーピング）
- metadata **全値 string 化**（Bedrock ingestion 要件）
- raw CSV は S3 非 sync（`sync-medicine-kb-to-s3.sh --exclude raw/*`）

### Phase 5 — CodePipeline KB 自動化（Step 5-F 完了）

**新規**: **`scripts/sync-all-kb-to-s3.sh`**, **`scripts/start-managed-kb-ingestion.sh`**, **`scripts/setup-aws-codebuild-kb-role.sh`**, **`scripts/reflect_medicine_kb.sh`**

**更新**: **`buildspec.yml`** — post_build に KB sync / ingestion / eval フック（env は CodeBuild プロジェクト側で設定。buildspec 内定義は console を上書きするため **削除済み**）

**CodeBuild env（2026-07-24 時点）**:

| 変数 | 値 | 備考 |
|------|-----|------|
| `SYNC_KB_TO_S3` | **`true`** | Step 5-F で有効化・Pipeline 検証済 |
| `KB_INGESTION_ON_PUSH` | **`true`** | 非同期起動（進行中 job があると ConflictException — 正常） |
| `RUN_KB_EVAL` | `false` | 週次 or 手動パイプライン推奨 |
| `KB_EVAL_STRICT` | `false` | — |

**eval スクリプト**: **`scripts/eval_medicine_kb.py`**（`--mode both`, `--min-pass-pct`, `--min-interaction-pass`）、**`scripts/eval_concierge_kb.py`**

**fixture**: **`tests/fixtures/medicine_kb_eval.yaml`**（20 問）、**`tests/fixtures/concierge_kb_eval.yaml`**（10 問）

### RAG 配線（Phase 2–4 分）

- **`src/services/bedrock_kb_retrieve.py`**: `build_medicine_retrieval_query()` / `build_concierge_retrieval_query()` 拡張
- **`src/core/medicine/medicine_response_builder.py`**: KB augment + **Ask sanitize**
- **`src/core/explanation_generator.py`**: Explanation KB citation（方式 A）
- **`src/agents/concierge_agent.py`**: Managed KB 接続
- **`src/services/concierge_output_sanitize.py`**: `sanitize_medicine_ask_output()`

### ドキュメント

- **`docs/ops/AWS_BEDROCK_KB.md`**: raw 除外・ingestion トラブルシュート（boolean metadata）
- **`docs/ops/AWS_CODEPIPELINE.md`**: KB env 段階ロールアウト・IAM 要件
- **`docs/ops/AWS_STAGING_CHECKLIST.md`**: Phase 5 KB 自動化チェック
- **`docs/ops/GCP_RAG_MIGRATION_ADR.md`**: Option C 推奨（staging Bedrock / GCP 本番レガシー）

### eval 成果物（`log/analysis/`）

| ファイル | 結果 |
|----------|------|
| `medicine_kb_step5f_20260724.json` | raw 16/20、runtime 17/20、相互作用 5/5 |
| `concierge_kb_step5f_20260724.json` | 9/10（90%） |
| `codebuild_kb_step5f_complete_20260724.json` | Step 5-F サマリ |
| `medicine_kb_after_ingestion_fix_20260724.json` | metadata 修正後 eval |
| `concierge_kb_baseline_20260724.json` | 9/10（90%） |
| `ingestion_failure_summary.md` | failed 7,494 原因と修正 |

### 運用メモ

- push 毎 ingestion は **コスト増** — 運用負荷が高い場合は `KB_INGESTION_ON_PUSH=false` + 手動 `reflect_medicine_kb.sh` も可
- 推奨順位（`physical_orchestrator.py`）は **変更なし**

---

## 2026年7月24日 — PMDA データ取り込み拡張（live fetch・CSV merge）

### 概要

PMDA 公的情報（市販薬検索・添付文書 §10 相互作用・§11 副作用）を `data/*.csv` 正本へ取り込むパイプラインを拡張。**初版は catalog expansion を正本としたが、2026-07-24 夜の正本再生成以降は live + raw 再パースが正本**（catalog 復元なし）。CodePipeline / AWS IP からの live fetch は **禁止**（ローカル回線のみ）。

### パイプライン

**`scripts/pmda/`** — fetch / normalize / validate / merge / queue

| スクリプト | 用途 |
|-----------|------|
| `run_pmda_import.py` | dry-run / merge 実行 |
| `fetch_interactions.py` / `fetch_side_effects.py` | §10 / §11 live fetch |
| `fetch_ingredient_live.py` | 成分単位 live 連続 fetch |
| `run_live_fetch_local.py` | ローカル完走用（§10+§11 統合） |
| `start_local_fetch.sh` / `watch_progress.py` | 起動・進捗監視 |

### live fetch ポリシー

- リクエスト間隔 **2.5–5.0 秒**、1 セッション **30 件**上限
- 403 / 429×3 / empty HTML×3 で abort → **24h クールダウン**
- GO/NO-GO: `fetch_interactions.py --live --limit 5`

### データ更新

- **`data/medicine_interactions.csv`** / **`data/medicine_side_effects.csv`**: PMDA 出典行の merge
- **`data/ingredient_dictionary.json`**: PMDA import 由来の成分同義語拡張
- **`data/pmda/manifest.json`**: import メタ・クールダウン
- **`data/pmda/staging/`**: 手動フォールバック用 staging JSON

### ドキュメント・テスト

- **`docs/ops/PMDA_DATA_IMPORT.md`**: 運用手順・robots 調査・abort 時フォールバック
- **`data/DATA_CATALOG.md`**: PMDA ソース追記
- **`tests/scripts/test_pmda_import.py`**: import / normalize / merge テスト拡張

### 成果物（`log/analysis/pmda_*`）

import / diff / local fetch 実行ログを追跡（プロジェクト方針）。

---

## 2026年7月24日 — OTC 商品画像 R2 一括同期・ローカル export

### 概要

推奨ログ頻度上位の OTC 医薬品について、**マツキヨココカラ online** から商品画像を取得し **Cloudflare R2**（`https://images.yutok.dev/otc/`）へ一括アップロードするパイプラインを追加。初回実行で **71 / 200 件** を R2 に配置（ログ推奨 117 件のうち **41 件**）。UI は `MEDICINE_IMAGE_CDN_BASE` 経由で **アップロード済み品目のパッケージ画像** を表示（未配置は従来どおりプレースホルダー）。

### 一括同期スクリプト（マツキヨ → R2）

**新規**: **`scripts/sync_otc_images_from_matsukiyo.py`**

- 推奨ログ（`recommendation_detail_log.jsonl` / `recommendation_log.jsonl` / `counseling_detail_log.jsonl`）から推奨頻度を集計
- 上位 117 品目を優先し、不足分を `data/otc_medicine_data.csv` で 200 件まで補完
- マツキヨ検索: セッション Cookie 取得後 `search_keyword` パラメータで `/store/catalogsearch/result/` を検索（`?q=` は不可）
- 商品ページ（JAN）から `_01_` パック画像を取得 → WebP 変換 → R2 `otc/{slug}.webp` へ PUT
- スラッグは **`src/services/medicine_image_urls.py`** の `slugify_product_name()` と同一規則
- フラグ: `--dry-run` / `--upload` / `--resume` / `--limit` / `--delay` / `--local-dir` / `--no-local`
- 成果物: `log/analysis/otc_image_sync/manifest.json` / `candidates.csv` / `run.log`

**初回実行結果（2026-07-24）**:

| 指標 | 件数 |
|------|------|
| 処理対象 | 200 |
| R2 アップロード成功 | **71** |
| マツキヨ未ヒット | 129 |
| エラー | 0 |
| ログ推奨 117 件のうち成功 | **41** |

CDN 確認例: `https://images.yutok.dev/otc/カロナールA.webp` → HTTP 200

### ローカル export

**新規**: **`scripts/export_otc_images_local.py`**

- `manifest.json` の `uploaded` 行を CDN から **`static/otc/{slug}.webp`** へ一括ダウンロード
- `static/otc/index.json` にファイル一覧を出力
- 同期スクリプト `--upload` 時も `--local-dir static/otc`（既定）で同時保存可能

**オフライン確認（任意）**:

```bash
MEDICINE_IMAGE_CDN_BASE=http://127.0.0.1:5000/static/otc/
```

### UI 連携

- ローカル `.env` / GCP 本番（`cloudbuild.yaml`）/ AWS ステージングは **`MEDICINE_IMAGE_CDN_BASE=https://images.yutok.dev/otc/`** 設定済み
- **`src/services/recommendation_client_payload.py`** → `enrich_medicine_image_url()` が API ペイロードに `image_url` を付与
- フロント: **`static/js/ui/medicine_mapper.js`** / **`medicine_card.js`** — 404 時 `onerror` でプレースホルダー

### R2 無料枠

- 71 枚 WebP 合計 **約 5.7 MB**（200 枚でも ~50 MB 想定）
- Cloudflare R2 無料枠: **10 GB ストレージ** / egress 無料 → **十分余裕**

### ドキュメント・Git 管理

- **`docs/ops/CLOUDFLARE_R2_IMAGES.md`**: 一括同期・ローカル export・オフライン env の手順を追記
- **`.gitignore`**: `static/otc/*.webp` / `static/otc/index.json` を生成物として除外（`static/otc/.gitkeep` のみ追跡）

### 今後の改善候補（未実装）

- `--log-only`（ログ推奨品目のみ対象）
- `data/otc_image_jan_overrides.csv` による JAN 手動上書き
- マッチ品質レビュー（例: タイレノールＡ → ＡS バリアント等）
- マツキヨ未掲載品（トキワイブプロエースＡ 等）の別ソース検討 → **2026-07-25 トキワ公式画像を R2 配置済み**（[CHANGELOG 2026-07-25](../CHANGELOG.md)）

---

## 2026年7月23日 — Concierge 更新履歴 UI・CodePipeline 自動デプロイ修正（夜）

### 概要

**ブランチ `main`** に、(1) Concierge **更新履歴カード**のユーザー向け表示改善（「次に試すこと」ラベル誤用・箇条書き途中切れ・開発者向け env 文言）、(2) Sage Web で **推奨バブルを diagnosis 一括描画**する際の途中 SSE スキップ、(3) GitHub push 後の **CodePipeline が post_build で毎回 Failed** していた問題の修正を反映（commits `c45fe51` / `170e807` / `7b15881`）。ステージング ALB には **ECS タスクロール**（Translate / Polly / Bedrock KB）を admin 手動適用済み（タスク定義 `default-medicine-recommend:18`）。

### Concierge — 更新履歴・補足カード UI

**原因**: (1) 更新履歴・技術 FAQ の参照ヒントが「**次に試すこと**」ラベルで表示されていた。(2) `changelog_digest.py` が CHANGELOG 行を **72 文字で切り詰め**、`.env` / `CodeBuild` 等の開発者向け文言がそのまま UI に出ていた。(3) overlap カードの見出しが **18 文字上限**で `AWS/Cloudflare ステ…` のように省略されていた。

**修正**:

- **`src/content/changelog_digest.py`**: ユーザー向け **「＋」前向き箇条書き**に変換。env / ファイルパス / Secrets 等をフィルタ。見出しを `2026年7月23日（体験の向上）` 形式に短縮化
- **`static/js/ui/status_renderer.js`**: メタカードのヒントを **「補足」フットノート**表示に変更。更新項目を **＋マーク付きカード**で折り返し全文表示
- **`static/css/sage_terrace.css`**: `.ui-status-footnote` / `.ui-status-update-item` スタイル追加
- **`static/js/ui/ui_strings.js`**: `statusFootnoteLabel`（補足）を ja/en/ko/zh に追加
- **`src/agents/concierge_agent.py`**: 更新履歴ヒントを「公開されている更新記録をもとに…」に変更。architecture 深掘り時の Bedrock KB 案内を柔らかい文言に。導入文 LLM プロンプトに env 禁止・前向きトーンを追記
- **`tests/content/test_changelog_user_display.py`**: 前向き表示・env 非含有のテスト追加

### Sage Web — 推奨バブル一括描画と SSE

**原因**: Sage UI では最終 `diagnosis` で推奨バブルを一括描画するが、途中の SSE（`cards` / `reco_detail`）も処理して二重描画・ちらつきの原因になっていた。

**修正**:

- **`static/js/main.js`**: `shouldBulkRenderSageReco()` を追加。Sage 時は途中 SSE をスキップ
- **`src/handlers/chat/chat_recommendation_flow.py`**: `should_skip_reco_progressive_sse()` で Web Sage 経路の `emit_cards` / `emit_reco_detail` を抑制
- **`src/services/recommendation_client_payload.py`**: スキップ判定ヘルパー追加
- **`tests/handlers/chat/test_recommendation_sse_order.py`**, **`tests/services/test_recommendation_client_payload.py`**: 一括描画時の SSE 順序テスト更新

### AWS CodePipeline — post_build 連続 Failed の修正

**原因（CloudWatch `/aws/codebuild/medicine-recommend-build` 確認）**:

1. **`scripts/lib/aws_common.sh`** が CodeBuild でも `AWS_PROFILE=medicine-recommend-dev` を設定 → `sync-static-to-s3.sh` が `The config profile (medicine-recommend-dev) could not be found` で **exit 255**
2. ECS **taskRoleArn** が `ecsTaskExecutionRole` のまま → Translate / Polly API が AccessDenied → `POST /api/smoke/aws-translate` が `empty_or_unchanged`（502）→ smoke 失敗で Pipeline 全体 Failed
3. GitHub Webhook / CodeStar Connection は **正常**（`AVAILABLE`）。「ビルドが走らない」のではなく **走るが post_build で落ちていた**

**修正（リポジトリ）**:

- **`scripts/lib/aws_common.sh`**: `CODEBUILD_BUILD_ID` / ECS タスクロール環境では `AWS_PROFILE` を付けない
- **`buildspec.yml`**: smoke 失敗時は **警告のみ**（`SMOKE_STRICT=true` 時のみ fail）。デプロイ・static 同期成功後に smoke が落ちても Pipeline を緑にできる
- **`scripts/setup-aws-ecs-task-role.sh`（新規）**: `medicine-recommend-ecs-task-role` に Translate / Polly / Bedrock KB / Comprehend 権限を付与しタスク定義を更新
- **`main.py`**: `/api/smoke/aws-translate` が `_translate_with_aws` を直接呼び IAM エラーを `detail` に返す
- **`docs/ops/AWS_CODEPIPELINE.md`**: トラブルシュート（profile エラー・smoke 失敗・task role）を追記

**インフラ（手動・admin、2026-07-23 夜）**:

- IAM ロール **`medicine-recommend-ecs-task-role`** 作成 + inline policy 付与
- ECS タスク定義 **`default-medicine-recommend:18`** に `taskRoleArn` 設定・サービス再デプロイ
- Pipeline 実行 **`7b15881`**: Source / Build **Succeeded**。`/health` git_commit 一致・Translate smoke `ok: true` を確認

### デプロイ

- **main push → CodePipeline** で `aws.medicine.yutok.dev` へ自動反映（復旧済み）
- 新環境では `./scripts/setup-aws-ecs-task-role.sh`（admin IAM）を初回のみ実行

---

## 2026年7月23日 — 技術カード・AWS 医薬品相談エラー・プロンプト改善（夕）

### 概要

AWS ステージング（`aws.medicine.yutok.dev`）で、(1) **Concierge 技術カード**の本文が質問に答えず「補足」セクションに正答が入る、(2) **医薬品相談**（例: 「頭痛が痛い」）が成功後も **一時的なエラー** カードになる、という 2 件を修正。あわせて LLM プロンプトの **特定トピック過剰指定** をやめ、ユーザー意図に沿う **汎用方針** に統一した。

### Concierge — 技術カード本文と「補足」のズレ

**原因**: `structure_concierge_meta_display(deep=True)` が GCP/AWS/CodePipeline 等を含む段落をセクションへ移し、マルチエージェント等の一般論だけがカード本文（intro）に残っていた。

**修正**:

- **`src/services/concierge_templates.py`**: `_rebalance_architecture_deep_display()` を追加。質問意図に合うセクション内容を本文へ昇格し、一般論は「このサービスの概要」/「その他」へ退避。`user_text` を display 整形に渡す
- **`static/js/ui/status_renderer.js`**: 技術セクションのバッジ（GCP / AWS / デプロイ）を改善
- **`src/agents/concierge_agent.py`**: architecture 深掘りプロンプトを **【ユーザーの質問】の主題に直接答える** 汎用方針に変更（GCP/CodePipeline 等の例示を削除）
- **`src/content/concierge_tech_reference.py`**: 参照ブロック指示を「質問の主題優先」に統一
- **`src/dialogue/routing/intent_router_llm.py`**: 技術ルート判定文言を汎用化
- **`tests/concierge/test_concierge_templates.py`**: GCP/AWS・CodePipeline の display リバランステスト追加

### AWS ステージング — 医薬品相談が「一時的なエラー」になる重大バグ

**原因（CloudWatch 確認）**: ルールベース推奨は **約 36〜52 秒で成功** していたが、Web の Cookie 肥大化対策で DB 保存後に `session['messages']` を削除 → **`finalize_pipeline_response`（end_guard）** が bot 未追加と誤判定し、成功レスポンスの上に `system_error` カードを追加していた。

**修正**:

- **`src/handlers/chat/chat_pipeline_end_guard.py`**: `mark_pipeline_turn_bot_appended()` / `_turn_produced_bot_reply()` を追加。DB 保存後に messages を消す経路でも end_guard が成功を認識
- **`src/handlers/chat/chat_recommendation_flow.py`**, **`src/services/chat_response_service.py`**, **`src/handlers/chat/chat_question_route.py`**: messages 削除前にフラグを設定
- **`tests/handlers/test_chat_pipeline_end_guard_fail_loud.py`**: Web cookie slimming シナリオのテスト追加

### AWS インフラ — ALB idle timeout（504 対策）

**原因**: ECS Express Gateway ALB の idle timeout が **60 秒** のため、推奨フロー（60 秒超）で **504** が発生しうる（Gunicorn は 300 秒設定済み）。

**修正**:

- **ステージング ALB**: `idle_timeout.timeout_seconds` を **300 秒** に変更済み（2026-07-23 手動反映）
- **`scripts/tune-aws-ecs-performance.sh`**: 上記 ALB 調整ステップをワンショットスクリプトに追加

### 検証・運用

- **`scripts/concierge_staging_chat_probe.py`（新規）**: ステージング混合シナリオ簡易プローブ（挨拶 / 症状 / 技術 FAQ / 更新履歴 / redirect 等）

### デプロイ

- 本修正は **main push → CodePipeline** 後に `aws.medicine.yutok.dev` へ反映。ALB timeout のみ先行反映済み。

---

## 2026年7月23日 — AWS/Cloudflare ステージング展開・CI 自動化・Concierge 改善

### 概要

**ブランチ `main`** に、GCP 本番（`medicine.yutok.dev`）を変更せず **AWS ステージング**（`aws.medicine.yutok.dev`）で Translate / Polly / Bedrock KB(RAG) / Comprehend Medical / ElastiCache / Personalize / CloudFront static CDN / Cloudflare R2 画像を env ゲート付きで一括導入（commit `74b7fde`）。あわせて CodeBuild で push 毎の **static S3 同期 + CloudFront invalidation + Translate/Polly smoke** を自動化し、Concierge の **更新履歴（doc_changelog）表示不足** と **AWS 環境での技術質問が GCP 前提で答える問題** を修正した。

### AWS / Cloudflare 機能フラグ（GCP 本番は未設定 = レガシー維持）

- **`config/aws_features.py`（新規）**: `TRANSLATION_PROVIDER`（deepl | translate）、`TTS_PROVIDER`（webspeech | polly）、`CONCIERGE_RAG_PROVIDER`（local | bedrock_kb）、`COMPREHEND_MEDICAL_ENABLED`、`REDIS_URL`、`PERSONALIZE_*`、`MEDICINE_IMAGE_CDN_BASE`、`STATIC_CDN_BASE_URL`、`BEDROCK_KB_ID` を集約。`is_aws_staging_site()` / `is_concierge_technical_reference_enabled()` を追加
- **`.env.example`**: AWS ステージング向け env 例を追記
- **`docs/ops/AWS_FEATURES_ROLLOUT.md`（新規）**: ロールアウト方針・env 一覧
- **`docs/medicine.md`**: Bedrock KB / AWS ステージング構成の説明を更新

### Phase 1 — インフラ（WAF / CloudFront / CloudWatch）

- **`scripts/setup-aws-infra.sh`（新規）**: Phase 1 一括（CloudWatch / WAF / CloudFront）
- **`scripts/setup-aws-waf.sh`（新規）**: ALB 向け WAF（Rate limit + AWSManagedRulesCommonRuleSet）
- **`scripts/setup-aws-cloudfront.sh`（新規）**: S3 オリジン + CloudFront 配信（`STATIC_CDN_BASE_URL`）
- **`scripts/setup-aws-cloudwatch.sh`（新規）**: Log Group `/ecs/medicine-recommend` + アラーム雛形
- **`scripts/sync-static-to-s3.sh`（新規）**: `static/` → S3 + 任意 CloudFront invalidation
- **`scripts/lib/aws_common.sh`（新規）**: AWS CLI 共通（プロファイル `medicine-recommend-dev` 既定、Git Bash MSYS 対策）
- **`docs/ops/AWS_INFRA.md`（新規）**: 構成・手順

### Phase 2 — Translate / Polly / Cloudflare R2 画像

- **`src/core/translation_service.py`**: `TRANSLATION_PROVIDER=translate` 時 Amazon Translate + Redis/メモリキャッシュ
- **`src/services/polly_tts.py`（新規）**: Amazon Polly MP3 合成
- **`main.py`**: `POST /api/tts`（Polly ON 時）、`GET /health/aws`（機能フラグ smoke 用）、`POST /api/smoke/aws-translate`（CI smoke 用）
- **`static/js/main.js`**: `TTS_PROVIDER=polly` 時 `/api/tts` 経由の読み上げ
- **`templates/index.html`**: `window.__TTS_PROVIDER__` を注入
- **`src/services/medicine_image_urls.py`（新規）**: `MEDICINE_IMAGE_CDN_BASE`（R2/CDN）URL 解決
- **`static/js/ui/medicine_mapper.js` / `medicine_card.js` / `src/handlers/line/flex_messages.py`**: 画像 URL 統一 + `onerror` プレースホルダー
- **`scripts/upload-r2-otc-image.sh` / `upload_r2_otc_image.py`（新規）**: R2 へ OTC 画像アップロード
- **`docs/ops/CLOUDFLARE_R2_IMAGES.md`（新規）**: R2 + `images.yutok.dev` 運用

### Phase 3 — Bedrock KB + Comprehend Medical

- **`scripts/setup-aws-bedrock-kb.sh` / `create-aws-bedrock-kb.sh` / `sync-concierge-kb-to-s3.sh` / `sync-aws-bedrock-kb-ingestion.sh` / `start_bedrock_kb_ingestion.py`（新規）**: KB 作成・S3 同期・ingestion（Titan Embed 429 時は指数バックオフ）
- **`scripts/setup-aws-opensearch-kb-collection.sh` / `setup-aws-aoss-vector-index.sh` / `create_aoss_vector_index.py` / `update-aoss-kb-*-policy.sh`（新規）**: OpenSearch Serverless コレクション + ベクトル index + network/data policy
- **`src/services/bedrock_kb_retrieve.py`（新規）**: Bedrock KB retrieve + Redis キャッシュ + Concierge 参照ブロック追記
- **`src/agents/concierge_agent.py`**: `augment_reference_with_kb()` で architecture 等に KB チャンク注入
- **`src/services/comprehend_medical.py`（新規）**: Comprehend Medical エンティティ抽出（NLU 補助・ログ分析）
- **`src/handlers/chat/nlu_resolve.py`**: Comprehend Medical オプション統合
- **`scripts/analyze_comprehend_logs.py`（新規）**: ログから Medical エンティティ集計
- **`scripts/test_bedrock_titan_embed.py` / `test_bedrock_claude_invoke.py` / `test_bedrock_embed_models.py`（新規）**: Bedrock 事前確認
- **`docs/ops/AWS_BEDROCK_KB.md` / `AWS_BEDROCK_QUOTAS.md`（新規）**: KB 運用・429/Support ケース ID 一覧

### Phase 4 — ElastiCache + Personalize

- **`scripts/setup-aws-elasticache.sh`（新規）**: ElastiCache Serverless + `REDIS_URL`
- **`src/services/redis_cache.py`（新規）**: Translate / KB retrieve キャッシュ
- **`scripts/setup-aws-personalize.sh`（新規）**: Dataset group + event tracker（campaign はイベント蓄積後）
- **`src/services/personalize_ranker.py`（新規）**: Personalize ランキング補助（Web AWS のみ）
- **`src/handlers/chat/chat_recommendation_flow.py` / `recommendation_diagnosis_builder.py`**: Personalize フック
- **`docs/ops/AWS_PERSONALIZE.md`（新規）**

### ECS Express / Secrets / env 反映

- **`scripts/setup-aws-express-secrets.sh`（新規）**: Secrets Manager 移行（7 件 `primaryContainer.secrets`）。`APP_ENV=production` / `PUBLIC_SITE_URL=https://aws.medicine.yutok.dev` 既定
- **`scripts/update-aws-express-env.sh`（新規）**: Express タスク env 一括更新（PassRole 不要）
- **`scripts/setup-aws-ecs-secrets.sh`**: AWS feature flags + `STATIC_CDN_BASE_URL` 対応
- **`docs/ops/AWS_IAM_MEDICINE_RECOMMEND_DEV_EXTRA.json` / `AWS_IAM_ADMIN_POLICY.json`（新規）**: IAM ポリシー例

### CodeBuild / CodePipeline 自動化（本エントリ追加分）

- **`buildspec.yml`**: 既定 `SYNC_STATIC_TO_S3=true`。ECS `services-stable` 待ち後 `sync-static-to-s3.sh --invalidate` → **`scripts/aws-staging-smoke.sh`**（Translate / Polly / CDN / health）
- **`scripts/aws-staging-smoke.sh`（新規）**: デプロイ commit 一致待ち + `/health/aws` + smoke API 検証
- **`scripts/setup-aws-codepipeline.sh`**: CodeBuild env（`SYNC_STATIC_TO_S3` / `AWS_STAGING_URL`）+ CloudFront invalidation IAM
- **CodeBuild live 更新**: 環境変数・IAM を AWS アカウントに反映済み

### Concierge — 更新履歴・技術回答（AWS ステージング修正）

**原因**: (1) `static/changelog-digest.json` / Docker 焼き込み digest のハイライト上限 8 件で **7/22 以降の変更が UI に出にくい**。(2) AWS ステージングは `APP_ENV=production` のため **技術詳細参照が development 限定**で、architecture 回答が **Cloud Run/Neon 前提**のまま。(3) Bedrock KB ingestion 未完了時は RAG 空だが、ローカル参照に AWS 構成が無かった。

**修正**:

- **`src/content/changelog_digest.py`**: ハイライト上限 24、`release_user_facing_items()` で概要+ハイライトをユーザー向けに統合、`build_changelog_ui_sections` の表示件数拡大
- **`src/agents/concierge_agent.py`**: `doc_changelog` で digest 6 件参照・UI 3〜4 セクション表示。`is_concierge_technical_reference_enabled()` で AWS ステージングでも API/SSE/ルールベース詳細を参照に含める。**AWS ステージング専用参照ブロック**（ECS / Translate / Polly / Bedrock KB / R2 / Redis / GCP 本番との差分）を architecture に追加
- **`scripts/write_changelog_digest.py`**: ビルド時 digest 再生成（既存 Dockerfile フロー）

### Concierge — Amazon Q 型 技術 FAQ（Phase Q1）

- **`docs/concierge/technical/`（新規）**: クロスクラウド構成・パイプライン・デプロイ SSOT + [00-disclosure-policy.md](docs/concierge/technical/00-disclosure-policy.md)（公開情報 OK / 深掘りは聞かれたとき / env メタ禁止）
- **`docs/concierge/technical/04–07`（追記）**: データ保存・v2 フラグ・LINE/GCP 経路・監視運用 SSOT
- **`src/content/concierge_tech_reference.py`（新規）**: ローカル tech 参照 + `wants_technical_deep_dive()` + architecture 深掘り（medium ~1500 字）
- **`src/content/concierge_runtime_reference.py`（新規）**: `/health` 相当の公開デプロイ情報をプロンプト注入（env 名はユーザー出力に出さない）
- **`src/services/concierge_i18n.py`（新規）**: Concierge 応答を問い合わせ言語へ Translate/DeepL
- **`src/handlers/chat/chat_concierge_route.py`**: セッション言語更新 + i18n 適用
- **`src/services/concierge_templates.py`**: LINE Flex 文字数切り詰め + Web 誘導
- **`src/services/concierge_intent.py`**: 技術 FAQ プローブ拡張（doc_changelog / LINE / Chat Pipeline / CDN / 監視）
- **`.cursor/plans/concierge_amazon_q_technical_faq.plan.md`（新規）**: 改善計画（Bedrock KB は Support 解消後）
- **`scripts/sync-concierge-kb-to-s3.sh`**: technical + ops + CHANGELOG を KB ソースに同期
- **`tests/fixtures/concierge_technical_faq.yaml`**: 技術 FAQ **40 問** contract セット
- **`scripts/concierge-technical-faq-contract.sh`（新規）**: Support 不要の contract テスト（55 件）
- **`scripts/verify-concierge-ssot.sh`（新規）**: 技術 SSOT 整合性チェック（CodeBuild post_build 常時）
- **`scripts/concierge-staging-smoke.sh`（新規）**: staging HTTP smoke（/health/aws・changelog-digest CDN）
- **`docs/concierge/technical/README.md`（新規）**: SSOT 索引
- **`static/changelog-digest.json`**: Phase Q1–Q4 追記反映で再生成

### Concierge — Amazon Q 型 技術 FAQ（Phase Q4）

- **`src/services/concierge_channel.py`（新規）**: LINE 非 deep 時の概要制限 + 「詳しく」誘導ヒント
- **`src/services/bedrock_kb_retrieve.py`**: KB 空時ログ（ingestion 待ち — ローカル SSOT フォールバック明示）

- **`src/services/concierge_output_sanitize.py`（新規）**: env 名・内部パス・メタ文言の出力サニタイズ + 症状混入時の一行導線
- **`src/services/concierge_templates.py`**: 深掘り architecture を GCP/AWS/デプロイ等の **多セクション Sage カード** に分割
- **`src/agents/concierge_agent.py`**: サニタイズ適用、深掘り時 `参照: 公開技術ドキュメント`、doc_changelog に `参照: 更新履歴`
- **`tests/services/test_concierge_output_sanitize.py`（新規）**: サニタイズ・深掘りセクションのテスト

### テスト

- **`tests/config/test_aws_features.py`**: AWS フラグ + staging 判定
- **`tests/content/test_concierge_tech_reference.py`**, **`tests/content/test_concierge_runtime_reference.py`**, **`tests/concierge/test_technical_faq_contract.py`**, **`tests/services/test_concierge_i18n.py`**, **`tests/services/test_concierge_output_sanitize.py`**, **`tests/services/test_concierge_channel.py`**, **`tests/scripts/test_verify_concierge_ssot.py`**
- **`tests/core/test_translation_service_aws.py`**, **`tests/api/test_tts_api.py`**, **`tests/services/test_bedrock_kb_retrieve.py`**, **`tests/services/test_comprehend_medical.py`**, **`tests/services/test_medicine_image_urls.py`**, **`tests/services/test_personalize_ranker.py`**, **`tests/services/test_redis_cache.py`**, **`tests/scripts/test_analyze_comprehend_logs.py`**

### 運用メモ / 既知ブロッカー

- **Bedrock Titan Embed v2 429**: on-demand クォータ未 provisioning。Support ケース **178479394100149** / **178479739800503** / **178479235800574**（アサイン待ち）。詳細は `docs/ops/AWS_BEDROCK_QUOTAS.md`
- **KB ingestion**: クォータ解消後 `scripts/sync-aws-bedrock-kb-ingestion.sh 4PEWLBZGTH`
- **Personalize campaign**: イベント蓄積後に作成（意図的保留）
- **GCP 本番**: `cloudbuild.yaml` は `GIT_COMMIT` / `MEDICINE_IMAGE_CDN_BASE` のみ — AWS フラグは注入しない

---

## 2026年7月22日 — Chat Pipeline v2 本番デフォルト ON・障害 UX・AWS CodePipeline / ECS

### 概要

**ブランチ `main`** に、Chat Pipeline v2 / IntentRouter PRIMARY / レガシー経路 TRIM を本番・dev とも env 未設定で **一括 ON** に変更。OPENAI 未設定・パイプライン無応答時の Sage 障害カード UX を v2 経路でも復元。あわせて GitHub main push → CodeBuild → ECR → ECS Express（`aws.medicine.yutok.dev`）の CI/CD を追加し、デプロイ・ビルドの遅延要因を調査・改善した。

### Chat Pipeline v2 — 本番デフォルト ON

- **`config/llm_flags.py`**: `CHAT_PIPELINE_V2` / `INTENT_ROUTER_PRIMARY` / `LEGACY_FALLBACK_TRIM` を本番・dev で env 未設定 = ON。pytest 実行中のみ OFF（既存テストの決定論を維持）。明示 `false` のみロールバック
- **ALLOWLIST 削除**: `CHAT_PIPELINE_V2_ALLOWLIST` / `PRIMARY_ALLOWLIST` を削除。`DENYLIST` のみセッション単位ロールバック用に残存
- **`docs/dev/CHAT_PIPELINE_V2.md`**, **`.env.example`**, **`scripts/cloudrun_v2_env.example`**, **`scripts/verify_v2_canary_flags.py`**: カナリア env 不要・本番一括 ON の運用に合わせて更新

### 障害 UX（v2 経路）

- **`src/services/llm_unavailability.py`**: `is_openai_configured()` / `is_llm_configuration_error_text()` を追加。インフラ系 triage 判定を拡張。`try_respond_when_openai_unconfigured()` で早期 Sage カード返却
- **`src/handlers/chat/chat_post_pipeline.py`**: POST 直後の OPENAI 未設定ガード
- **`src/handlers/chat/chat_symptom_route.py`**: レガシー `{"error": True}` JSON を廃止 → Sage カード（`llm_unavailable` / `system_error` の使い分け）
- **`src/handlers/chat/chat_pipeline_end_guard.py`**: パイプライン終了時に bot 応答が無い場合、`system_error` Sage カードを自動追加（fail loud）
- **方針**: インフラ障害 = `llm_unavailable`、その他 = `system_error`。`LLM_AGENT_ENABLED` は固定 ON 想定だが env は緊急キルスイッチとして残す

### テスト

- **`tests/dialogue/test_v2_flags.py`**, **`tests/dialogue/test_v2_primary_canary_flags.py`**: 本番デフォルト ON・ALLOWLIST 削除に合わせて更新
- **`tests/handlers/test_chat_pipeline_end_guard_fail_loud.py`**, **`tests/services/test_llm_unavailability_guard.py`**: 早期 LLM ガード・end guard のテスト追加
- **`tests/contract/test_route_spec_expectations.py`**: ルート期待値を更新

### AWS CodePipeline / ECS Express デプロイ

- **`buildspec.yml`（新規）**: GitHub main → CodeBuild（linux/amd64 Docker build → ECR push → `ecs update-service --force-new-deployment`）。ビルド失敗時は ECS デプロイをスキップ
- **`scripts/setup-aws-codepipeline.sh`（新規）**: Pipeline `medicine-recommend-main`、CodeBuild `medicine-recommend-build`、CodeStar Connection、IAM ロールの初回セットアップ
- **`scripts/deploy-aws-ecs.sh`（新規）**: Pipeline なしの手動ビルド・プッシュ・再デプロイ
- **`scripts/setup-aws-ecs-secrets.sh`（新規）**: `.env` から Secrets Manager（OPENAI / DATABASE_URL / SECRET_KEY 等）を投入し、タスク定義を更新して再デプロイ
- **`docs/ops/AWS_CODEPIPELINE.md`（新規）**: 構成・初回 OAuth・手動実行・トラブルシュート
- **`Dockerfile`**: CodeBuild の Docker Hub 429 回避のため `public.ecr.aws/docker/library/python:3.11-slim` ベースイメージに変更（commit `3357e54`）
- **本番 URL**: `https://aws.medicine.yutok.dev/health`（`git_commit` でデプロイ revision を確認）

### ECS パフォーマンス調査・改善

**症状**: GitHub push から `aws.medicine.yutok.dev` へ反映されるまで **6〜8 分**程度かかる。

| 要因 | 詳細 | 実施した改善 |
|------|------|-------------|
| CANARY デプロイ | ECS Express Gateway は **ROLLING 不可**。既定 `bakeTimeInMinutes=3` + `canaryBakeTimeInMinutes=3` | bake 時間を **0 分**に短縮（`scripts/tune-aws-ecs-performance.sh`） |
| CodeBuild | `BUILD_GENERAL1_SMALL`、キャッシュ無効 → ビルド ~2 分/回 | **LOCAL_DOCKER_LAYER_CACHE** 有効化。`buildspec.yml` / `deploy-aws-ecs.sh` で **BuildKit + `--cache-from ECR:latest`** |
| ランタイム同時処理 | タスク定義 `GUNICORN_WORKERS=1`（512 CPU / 1024 MiB） | **`GUNICORN_WORKERS=2`** に更新（`setup-aws-ecs-secrets.sh` / tune スクリプト） |
| ウォーム `/health` | 50〜150 ms — ALB・タスク自体は問題なし | ユーザー体感の遅延は主に **デプロイ待ち** と **ビルド** |
| Secrets 未設定 | `DATABASE_URL` 無し → セッション未永続化、UI「AI分析中」停滞 | **`setup-aws-ecs-secrets.sh`** でユーザー投入（エージェント側では未実施） |

- **`scripts/tune-aws-ecs-performance.sh`（新規）**: CANARY bake 短縮・GUNICORN ワーカー数・CodeBuild キャッシュを一括適用

### 運用メモ

- **Secrets 投入**（ユーザー側）: `cp .env.example .env` → `OPENAI_API_KEY` / `DATABASE_URL` / `SECRET_KEY` を記入 → `./scripts/setup-aws-ecs-secrets.sh .env`
- **SECRET_KEY**: 管理画面 Cookie HMAC 署名用（`src/services/admin_auth.py`）。Flask セッション用ではない
- **GCP 本番**（`medicine.yutok.dev`）は従来どおり Cloud Run。AWS はステージング / デモ用途

---

## 2026年7月4日 — 風邪＋水泳推奨改善・RECO_* 本番一括展開

### 概要

「風邪ですが、水泳大会なので使える薬を教えて」のような初回相談が `no_recommendation` に落ちる問題を修正。直接原因だった年齢未入力時の chat 側フィルタ（15歳以上薬 3 件 → 0 件）と、`no_candidates` / `escalation_required` より前に実行される早期 empty fallback を解消し、`sage_reco` で候補を表示するようにした。

あわせて、`RECO_AGE_POLICY_V2` / `RECO_COLD_NLU_V2` / `RECO_SPORTS_DOPING_FILTER` は本番カナリア用 env を不要化し、本番・dev とも env 未設定で一括 ON に変更。明示 `false` のみ個別ロールバックとして扱う。pytest 実行中は未設定時 OFF を維持し、既存テストの決定論を保つ。

### Phase 1 — 年齢未入力時の推奨ポリシー

- **`config/llm_flags.py`**: `RECO_*` 専用の `_reco_rollout_flag()` を追加。本番・dev は未設定で ON、pytest は未設定で OFF、明示 `false` でロールバック可能
- **`src/handlers/chat/chat_recommendation_flow.py`**: `RECO_AGE_POLICY_V2` ON 時は `_filter_medicines_when_age_unknown()` が 12歳以上表記薬を除外せずそのまま返す。小児文脈（例: 5歳の子供）は `pediatric_age_required` の確認導線を維持
- **`src/handlers/chat/chat_recommendation_flow.py`**: 早期 `_build_empty_recommendation_fallback()` を status 分岐後へ移動。`status=no_candidates` は `no_candidates` エラー UI、`escalation_required` は受診・薬剤師相談 UI に到達
- **`src/core/recommendation/age_policy.py`**: `build_age_unknown_warnings()` / `apply_age_unknown_policy_to_result()` を追加。年齢未入力かつ 12歳以上制限薬が含まれる場合、`age_policy_notice` と `restricted_medicines` を生成し、`usage_notes` に警告を前置
- **`src/services/recommendation_diagnosis_builder.py` / `src/schemas/recommendation_diagnosis_v1.py`**: `age_policy_notice` を `DiagnosisV1` に反映し、制限薬名を admin ブロックへ保持
- **`static/js/ui/recommendation_renderer.js` / `static/js/ui/medicine_mapper.js` / `static/js/ui/medicine_card.js` / `static/js/main.js`**: `sage_reco` 上部の年齢未確認バナーと各薬カードの年齢制限表示を整備
- **`src/handlers/line/line_web_handoff.py`**: LINE Web handoff 時にも `age_policy_notice` を保持
- **ログ**: `pipeline_perf` に `reco_age_policy_v2`、`pre_age_filter_count`、`post_age_filter_count`、`empty_fallback_trigger` を記録

### Phase 2 — 風邪 NLU・症状チップ・インフル誤検知抑制

- **`src/core/recommendation/cold_symptom_expansion.py`**: 「風邪」入力に対して発熱、咳、のどの痛み、鼻水、鼻づまり、頭痛、関節痛をルール展開。症状 0–1 件で曖昧な場合は展開せず症状チップへ誘導
- **`src/services/medicine_context_routing.py`**: `cold_symptom_chip_prompt` ルートを追加。`cold_vague_only` は症状チップ、`cold_cold_swim_meet` は `cold_start_recommend` を維持
- **`src/handlers/chat/medicine_context_handlers.py` / `src/dialogue/dispatcher.py` / `src/handlers/chat/chat_post_pipeline.py` / `src/handlers/chat/chat_symptom_route.py` / `src/handlers/chat/chat_recommendation_flow.py`**: 症状チップハンドラと各入口の接続を追加。Web クリック後は `_pending_cold_symptoms` / `_awaiting_cold_symptoms` で次ターンを「風邪で{症状}」としてマージ
- **`src/schemas/status_diagnosis_v1.py` / `static/js/ui/status_renderer.js` / `static/css/sage_terrace.css` / `static/js/main.js`**: `suggested_symptoms` と `data-postback-text` ボタンを追加し、Web チップ UI を表示
- **`src/handlers/line/flex_messages.py`**: `cold_symptom_chip_prompt` に LINE `quickReply` を付与し、Web と LINE の parity を確保
- **`src/core/recommendation/final_score_calculator.py`**: 「風邪」文脈で風邪薬系、のど・鼻の外用候補にスコアボーナスを付与（閾値は変更なし）
- **`src/core/influenza_detector.py`**: インフル疑い判定に高熱必須条件を追加し、誤検知を抑制
- **`src/core/recommendation/medicine_type_resolver.py`**: 風邪薬 hint を小関数に抽出し、推奨タイプ解決をテスト可能にした

### Phase 3 — 競技・ドーピング配慮

- **`src/core/rule_based_recommendation.py`**: 競技文脈かつ `RECO_SPORTS_DOPING_FILTER` ON の場合、推奨候補から `doping_prohibited == "禁止物質あり"` を除外。除外後 0 件なら `escalation_required` として医師・薬剤師相談へ誘導
- **`src/services/medicine_discovery_routing.py`**: 競技文脈キーワードに「水泳」「泳ぐ」「プール」「競泳」を追加
- **`src/core/explanation_generator.py` / `src/services/chat_response_service.py`**: 競技・大会前後の使用可否、ドーピング規定への配慮を説明文に必ず含める指示を追加

### 運用・環境変数

- **`scripts/cloudrun_v2_env.example`**: 風邪水泳推奨改善 Phase 1–3 は本番・dev とも未設定で ON と明記。問題時のみ `RECO_AGE_POLICY_V2=false`、`RECO_COLD_NLU_V2=false`、`RECO_SPORTS_DOPING_FILTER=false` で個別ロールバック
- 本番カナリア用の `RECO_* = true` 設定は不要。一括デプロイで全セッションに適用

### テスト・検証

- **`tests/config/test_llm_flags.py`**: RECO_* の pytest 既定 OFF、dev / production 既定 ON、明示 false ロールバックを検証
- **`tests/handlers/test_reco_age_policy_v2.py`**: cold swim 相当、年齢フィルタ ON/OFF、小児文脈、`no_candidates` fallback 順序、症状チップ応答マージを検証
- **`tests/core/test_age_policy.py` / `tests/services/test_recommendation_diagnosis_builder.py`**: 年齢未確認警告、`restricted_medicines`、`DiagnosisV1` 反映を検証
- **`tests/core/test_cold_symptom_expansion.py` / `tests/core/test_influenza_detector.py` / `tests/core/test_medicine_type_resolver.py` / `tests/core/test_sports_doping_filter.py`**: Phase 2–3 の個別ロジックを検証
- **`tests/routing/test_medicine_context_routing_matrix.py`**: ルーティングマトリクスを更新
- **Live 統合**: `scripts/test_medicine_context_live.py` で 10/10 PASS。`cold_start_cold_swim` は `render=sage_reco`
- **レポート**: `log/analysis/2026-07-04T021159Z_medicine_context_live.json`
- **CI 修正**: `medicine_context` gate を発熱・緊急判定の後へ移動し、`guards` が `fever_flow` を上書きしないよう修正（IntentRouter contract / gate テスト）

---

## 2026年7月3日 — CHANGELOG Concierge・app_about ガード・UI 改善

### 概要

**ブランチ `main`** に、CHANGELOG 要約を Concierge で回答する `doc_changelog` intent、IntentRouter の `app_about` 誤ルーティング補正、処理中ステータスマスコットの段階別アニメーション、チャットビューポートとシーズン装飾のレイヤー修正、オンボーディングスライドの文言刷新を実装。

### CHANGELOG 要約と doc_changelog Concierge

- **`src/content/changelog_digest.py`（新規）**: `CHANGELOG.md` から直近リリースの概要・ハイライトを抽出。`static/build-meta.json` のデプロイ反映情報と結合して LLM プロンプト用参照ブロックを生成
- **`src/agents/concierge_agent.py`**: `doc_changelog` intent で CHANGELOG 要約を参照回答（推測・補完禁止の専用プロンプト）
- **`src/content/concierge_docs.py`**: `doc_changelog` を doc intent 集合に追加
- **`src/services/concierge_intent.py`**: `doc_changelog` intent とキーワードプローブ（「最近の更新」「CHANGELOG」等）
- **`src/services/meta_triage.py`**: meta triage プロンプトに `doc_changelog` を追加
- **`src/agents/emergency_classifier.py` / `src/handlers/line/line_delivery.py`**: 非緊急・遅延 Concierge intent リストに `doc_changelog` を追加
- **`tests/content/test_changelog_digest.py`（新規）**

### IntentRouter app_about ガード

- **`src/dialogue/routing/intent_router_llm.py`**: プロンプトに `app_about` / `doc_changelog` の判定ガイドを追加。legacy triage の `concierge_intent` をヒントに含める。`maybe_correct_concierge_app_about_route()` — LLM が本サービスの自己紹介依頼を `chitchat` 等に誤判定した場合のみ `app_about` へ補正
- **`src/dialogue/routing/intent_router.py`**: route 決定後に app_about ガードを適用
- **`src/services/concierge_intent.py`**: `probe_service_app_about_request()` / `is_excluded_service_app_about_request()` — ユーザー自身の自己紹介・他アプリ紹介依頼を除外
- **`tests/dialogue/routing/test_intent_router_llm.py`**: app_about 補正・除外ケースのテスト追加
- **`tests/concierge/test_concierge_intent_extended.py`**: app_about 除外・doc_changelog プローブのテスト追加

### 処理中ステータス — マスコット段階別アニメーション

- **`static/js/processing_status.js`**: パイプライン step / detail_code からマスコット mood を細分化（`idle` / `peek` / `think` / `scan` / `focus` / `spark` / `alert` / `compose` / `calm`）
- **`static/css/main.css`**: 目のみのマスコット + 頭上バブル（`?` `!` `…`）の段階別 CSS アニメーション。`prefers-reduced-motion` 対応

### チャットビューポート・シーズン装飾

- **`templates/index.html`**: `.chat-messages-viewport` ラッパーを追加。シーズン装飾をビューポート下端に固定（メッセージスクロールと独立）
- **`static/css/main.css` / `static/css/sage_terrace.css`**: 背景を viewport に移し `.chat-messages` は透明化。装飾レイヤの z-index・パディング調整

### オンボーディング文言刷新

- **`static/js/main.js`**: 全言語（ja / en / ko / zh）のオンボーディングスライドを「完了した改善」と「開発中・今後の予定」に分割。GitLab 一時移行の説明を dev スライドの footnote に移動。チェックリスト項目を現状に合わせて更新
- **`static/css/main.css`**: `.onboarding-footnote`（`<details>` 折りたたみ）スタイル追加

### テスト

- `tests/content/test_changelog_digest.py`（新規）
- `tests/dialogue/routing/test_intent_router_llm.py` / `tests/concierge/test_concierge_intent_extended.py` 更新

---

## 2026年7月3日 — ローカル DB 分離・セキュリティ入力ブロック・店舗案内・管理画面刷新

### 概要

**ブランチ `feature/chat-pipeline-v2`** に、ローカル開発用 Docker Postgres の自動起動、Neon dev との DB 分離、入力ブロックのカテゴリ別応答、店舗・施設案内の精度改善、管理画面（admin_chat）の Sage Terrace UI 刷新を実装。

| 関連ドキュメント | 用途 |
|-----------------|------|
| [LOCAL_DOCKER_DB.md](docs/dev/LOCAL_DOCKER_DB.md) | ローカル Docker Postgres / Neon dev 分離手順 |
| [SCROLLBAR_STYLE.md](docs/ui/SCROLLBAR_STYLE.md) | 管理画面スクロール領域（`app-scrollbar`） |

### ローカル Docker Postgres / Neon dev 分離

- **`docker-compose.yml`（新規）**: Postgres 16、`medicine_recommend` DB、healthcheck、永続ボリューム
- **`src/utils/local_docker_db.py`（新規）**: `DATABASE_URL` が localhost のとき `docker compose up -d` と接続待ち（`LOCAL_DOCKER_DB_AUTO=1` 既定、`LOCAL_DOCKER_DB_WAIT_SEC=60`）
- **`app.py`**: 起動前に `_prepare_local_database()` を呼び出し
- **`src/services/database.py`**: ローカル host 向け `sslmode=disable` 自動付与、`channel_binding=require` 除去、pooler 警告を localhost では抑制
- **`scripts/migrate_dev_neon_selective.py`（新規）**: v2 テストセッション除外のうえ `line:*` 実データ + feedback 等を Neon dev へ選別移行
- **`.env.example`**: ローカル Docker / Neon dev 接続例、`LOCAL_DOCKER_DB_*` 変数
- **`.gitignore`**: `tmp_db_migration/` を追加
- **`tests/utils/test_local_docker_db.py`（新規）**

### 入力ブロック — カテゴリ別応答とカウンセリング bypass

- **`src/security/input_block_responses.py`（新規）**: `threat_abuse` / `sexual_content` / `solicitation` / `illegal_drugs` / `system_abuse` のカテゴリ分類と応答文言。性被害相談キーワードはカウンセリングへ bypass
- **`src/security/aggressive_input.py`**: 判定ロジックを `input_block_responses.match_input_block` に委譲
- **`src/handlers/chat/chat_input_validator.py` / `chat_inappropriate_route.py`**: カテゴリ別 title / variant / kind でブロック応答。ブロック user メッセージに `original_content` / `admin_only` / `blocked_input` を付与
- **`src/services/session_manager.py`**: `filter_messages_for_user_api()` — ユーザー API では `original_content` 等を除去しプレースホルダのみ返却
- **`main.py`**: `api_sessions_get` / `api_sessions_restore` で user API フィルタ適用
- **`src/handlers/line/line_web_handoff.py`**: handoff 正規化後も user API フィルタ
- **`static/js/main.js`**: 新 kind（`inappropriate_sexual` 等）を SECURITY_NOTICE に追加。user メッセージ畳み込みを uuid / message_id / pending_turn_id キーに変更
- **`src/handlers/line/line_feedback.py`**: 不適切入力 kind ではフィードバック UI を非表示
- **`src/analysis/session_conversation_analysis.py`**: セキュリティ応答 route_kind を挨拶誤判定から除外
- **`tests/security/test_input_block_responses.py`（新規）**、既存 aggressive / inappropriate / llm_security テスト更新

### 店舗・施設問い合わせ改善

- **`src/services/store_facility_index.py`（新規）**: `store_inquiry_keyword_catalog.json` から施設・外部チェーン・小売チェーンの正規化インデックス。商品照合から施設名を分離
- **`data/store_inquiry_keyword_catalog.json`**: `external_retail_chains` / `retail_store_chains` セクション追加（マツキヨ・ドンキ・百貨店・家電量販等）
- **`src/services/store_inquiry_handler.py`**: 店内外デュアル案内（`_compose_dual_location_guidance`）、施設名ラベル解決、一般「薬局＋近く」問い合わせの external_chain 検出拡張
- **`src/services/store_product_index.py`**: 施設トークン除外で商品誤マッチ防止
- **`data/store_products.json`**: カテゴリに空 `brands: []` フィールドを正規化追加
- **`tests/services/test_store_facility_index.py`（新規）**、store inquiry routing テスト更新

### 管理画面（admin_chat）Sage Terrace UI 刷新

- **`templates/admin_chat.html`**: `sage_terrace.css` 適用、`data-ui-variant="sage"`。ヘッダーをアイコンボタン群に再構成。セッション管理モーダル・ログクリア確認モーダル追加。チャットメッセージ複数選択削除 UI
- **`static/css/admin_chat.css`**: Sage Terrace トークン準拠の全面スタイル刷新（レイアウト・モーダル・セッションカード・チャットバブル）
- **`static/css/scrollbar.css`**: `#session-management-list` 等の新スクロール領域を `app-scrollbar` グループに追加
- **`static/js/admin_chat.js`**: セッション管理（`openSessionManagement`）、ログクリアモーダル、ブロック入力の `original_content` を管理者向け表示、メッセージ選択削除、UI 操作の aria 改善

### 運用・調査まわり

- **`src/services/pipeline_perf.py`**: `capture_pipeline_perf_investigation_snapshot()` — 遅延調査用に進行中パイプライン計測を非破壊取得
- **`src/services/slow_request_notify.py`**: セッション調査スナップショット + pipeline perf を Resend 通知に同梱
- **`main.py` `api_slow_request_notify`**: 上記スナップショットを渡すよう拡張
- **`main.py` `/clear_logs`**: **全セッション DB 削除を廃止**（network_logs + recommendation_log.jsonl のみクリア）
- **`tests/api/test_session_message_merge.py`**: user API フィルタ・ブロックメッセージのテスト追加

### テスト

- 新規・更新テスト **31+ passed**（`test_input_block_responses` / `test_local_docker_db` / `test_store_facility_index` / `test_session_message_merge`）

---

## 2026年7月3日 — Phase 4（4a–4b）IntentRouter primary 化・dev 展開

### 概要

**ブランチ `feature/chat-pipeline-v2`** に Phase 4a（dispatch handler 追撃・shadow mismatch 分類）および Phase 4b（Router PRIMARY / orch-trim / shadow exempt / LEGACY_FALLBACK_TRIM）を実装。**`config/llm_flags.py` の `_ux_rollout_flag`** により、`APP_ENV=development` のみで v2 / PRIMARY / TRIM / Phase 2–4b UX 十二種が env 未設定でも自動 ON（`LATENCY_*` は対象外・既定 OFF のまま）。本番は env 明示 ON + ALLOWLIST 限定（カナリア 1 は **dev 24h Go 待ち**）。

| 関連ドキュメント | 用途 |
|-----------------|------|
| [PHASE4B_ROUTER_PRIMARY_MIGRATION.md](docs/dev/PHASE4B_ROUTER_PRIMARY_MIGRATION.md) | 4b 設計・決定権マップ・Go/No-Go |
| [PHASE4B_DEV_ROLLOUT_AND_CANARY1_INSTRUCTIONS.md](docs/dev/PHASE4B_DEV_ROLLOUT_AND_CANARY1_INSTRUCTIONS.md) | dev 一括展開・本番カナリア手順 |
| [.cursor/plans/ux品質改善計画v2_7fab4ed6.plan.md](.cursor/plans/ux品質改善計画v2_7fab4ed6.plan.md) | Phase 4 進捗（p4-unify は pending） |

### Phase 4a — dispatch handler 追撃・shadow mismatch 分類

- **`src/dialogue/dispatcher.py`**: SessionOps / Concierge / Store / Physical 等の dispatch handler 拡充。`handler None` を 0 件に是正
- **`src/dialogue/routing/shadow_mismatch.py`（新規）**: `regression` / `gate_improvement` / `exempt` 分類。counseling follow-up（`2週間くらいです` 等）の exempt 再分類
- **`src/dialogue/routing/shadow.py` / `metrics.py`**: `mismatch_kind` 出力、`shadow_regression` / `shadow_exempt` KPI
- **`src/utils/structured_logger.py`**: `emit_dialogue_route_shadow` に `mismatch_kind`
- **`scripts/measure_intent_router_shadow.py` / `local_v2_chat_test_runner.py`**: IntentRouter KPI セクション、`--failed-only` / `--resume` / checkpoint
- **`tests/dialogue/test_dispatcher_handlers.py`**, **`tests/dialogue/routing/test_shadow_mismatch.py`**, **`tests/scripts/test_local_v2_chat_test_metrics.py`**

**検証**（`log/analysis/2026-07-02_local_v2_chat_test_p4a-dispatch-final`）: 自動合格 **105/105**、dispatch_success **100%**（112/112）、shadow_regression **0.85%**（1/117）、handler None **0**。

### Phase 4b — Router PRIMARY / orch-trim / LEGACY_TRIM

| 環境変数 | 既定（本番） | dev 自動 ON | 効果 |
|---------|-------------|------------|------|
| `CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY` | OFF | ✅ | IntentRouter LLM decision を triage map より優先 |
| `CHAT_PIPELINE_V2_LEGACY_FALLBACK_TRIM` | OFF | ✅ | PRIMARY ON 時、dispatch 成功後の legacy 再実行を defensive bypass |
| Phase 2 四種 + Phase 3 八種 | OFF | ✅ | `_ux_rollout_flag` 経由（violence guard / session_ops 等） |

**主要変更**

- **`config/llm_flags.py`**: `_ux_rollout_flag()` — 開発ランタイム（`APP_ENV=development`）で UX 十二種 + PRIMARY/TRIM を自動 ON。`LATENCY_*` は従来どおり明示 ON のみ
- **`src/dialogue/routing/intent_router.py` / `intent_router_llm.py`**: PRIMARY 切替（triage map 降格）
- **`src/handlers/chat_orchestrator.py`**: dispatch 成功 route では meta_triage / SessionAgent / Concierge / Store 再判定をスキップ（orch-trim）
- **`src/handlers/chat/chat_post_pipeline.py`**: LEGACY_FALLBACK_TRIM 観測ログ
- **`src/services/concierge_orchestrator.py` / `store_inquiry_handler.py` / `session_ops.py`**: `_intent_router_dispatch` 連携
- **`scripts/verify_v2_canary_flags.py`（新規）**: dev auto-on / 本番 ALLOWLIST パターン検証
- **`scripts/canary_sim_smoke.py`（新規）**: 固定 sid 手動スモーク
- **`scripts/cloudrun_v2_env.example`**: 本番カナリア用 env 一覧更新
- **`tests/config/test_ux_rollout_flags_dev.py`**, **`tests/dialogue/test_v2_primary_canary_flags.py`**, **`tests/handlers/test_orchestrator_primary_locked.py`**, **`tests/handlers/test_legacy_fallback_trim.py`**

### p4b-5c-dev — dev Cloud Run コード反映

- **背景**: dev は env 手動投入済み（rev `00142-ln2`）だがコードは `37da58c` 相当で Phase 4b 実装未反映
- **`APP_ENV` タイポ `developmen` 修正**（`development` に統一）
- 冗長 env（PRIMARY / TRIM / Phase 3 八種 / Phase 2 四種）を **削除可能**（コード自動 ON で代替）
- 監視 t0 をコード反映時刻に **リセット**（`log/analysis/2026-07-03_dev_p4b-rollout_monitoring.json`）

### 検証結果（ローカル v2 統合テスト）

| レポート | PRIMARY | TRIM | 自動合格 | dispatch | 備考 |
|---------|---------|------|---------|----------|------|
| `p4a-dispatch-final` | OFF | OFF | **105/105** | 100% | 4a rebaseline |
| `p4b4-primary-full` | ON | OFF | **104/105** | 100% | followup-07 rule 揺れ 1 件 |
| `p4b5a-legacy-trim-full` | ON | ON | **104/105** | 100% | followup-04 Sage 揺れ（trim 非起因） |
| dev sim | — | — | **FLAGS_OK** | — | `verify_v2_canary_flags.py`（APP_ENV=development のみ） |

**本番カナリア 1**: 未実施（dev 24h KPI Go 待ち）。sim スモーク `p4b5b-canary-sim-smoke` は **3/3 OK**。

### テスト

- `tests/config/test_ux_rollout_flags_dev.py` — dev 自動 ON 十二種
- `tests/dialogue/test_v2_primary_canary_flags.py` — 本番 ALLOWLIST パターン
- `tests/dialogue/test_v2_flags.py` + `tests/dialogue/` + `tests/concierge/` — **351 passed**（コミット前）

### ログ・分析成果物

- **`log/analysis/`**: `p4a-dispatch-final` / `p4a-gate*` / `p4b2`〜`p4b5a` / `p3-followup-hotfix*` / `dev_p4b-rollout_monitoring`
- **`log/raw/archive/2026-07-02_pre-p4a2-dispatch/`**: dispatch/shadow ログアーカイブ

### 継続課題

- **p4-unify**: legacy 物理削除・本番全面展開（plan 上は pending）
- **e2e p95 < 5s**: Phase 1/1b レイテンシ（4b スコープ外）
- **concierge-followup-04/07**: Sage / rule キーワード揺れ（既知・未対応）

---

## 2026年7月2日 — UX 品質改善計画 v2（Phase 0–3）

### 概要

**ブランチ `feature/chat-pipeline-v2`** に、[UX品質改善計画 v2](.cursor/plans/ux品質改善計画v2_7fab4ed6.plan.md) に基づく Phase 0〜3 を実装。ベースライン評価（`log/analysis/2026-07-01_local_v2_chat_test_post-quality-fix-full.md`、自動合格 **77/105**）から、計測基盤整備・レイテンシ最適化（フラグゲート）・安全トーン是正・ルーティング/内容精度改善を段階投入。**Phase 0–3 の機能フラグは本番・未設定時 OFF**（明示有効化しない限り post-p0 と同一挙動）。**Phase 4** は 7/3 エントリ参照（4a–4b 着手済み・dev では `APP_ENV=development` で自動 ON）。

| Git コミット | 内容 |
|-------------|------|
| `b424bef` | Phase 0: 計測基盤・`_kind_route` 是正・LLM-as-judge |
| `f44ec32` | Phase 1: LLM 層レイテンシ最適化フラグ・p1 A/B レポート |
| `e4c5519` | Phase 1b–3: rb 計測分離・安全・ルーティング/内容・待機 UX |

| 関連ドキュメント | 用途 |
|-----------------|------|
| [.cursor/plans/ux品質改善計画v2_7fab4ed6.plan.md](.cursor/plans/ux品質改善計画v2_7fab4ed6.plan.md) | Phase 0–4 計画・KPI・検証結果 |
| [CHAT_PIPELINE_V2.md](docs/dev/CHAT_PIPELINE_V2.md) | v2 技術仕様 |
| [.cursor/skills/local-v2-chat-test/SKILL.md](.cursor/skills/local-v2-chat-test/SKILL.md) | ローカル v2 テスト手順 |

### Phase 0 — 計測基盤・テスト評価是正

- **`src/utils/structured_logger.py`**: `emit_pipeline_perf()` — `log/pipeline_perf_log.jsonl` へ構造化永続化（`total_ms` / `breakdown` / `llm.llm_calls` path 別 latency）
- **`src/services/pipeline_perf.py`**: `log_pipeline_perf()` から JSONL sink を呼び出し（app.log の `PIPELINE_PERF` と併用）
- **`scripts/measure_pipeline_baseline.py`**: `measure_pipeline_perf()` — total p50/p95/max、LLM path 別呼び出し回数・latency 内訳、`breakdown_steps_avg_ms`
- **`scripts/local_v2_chat_test_runner.py`**:
  - `_kind_route()` を **kind 優先判定**に是正（本文「市販薬」ヒューリスティックによる Concierge/Security/Store 誤判定を解消）
  - レポートに **レイテンシ KPI**（e2e p50/p95、pipeline phase 内訳）セクション追加
  - **`--judge`**: LLM-as-judge による内容品質スコア（意図充足・トーン・安全・総合 0–5）
- **`tests/scripts/test_local_v2_kind_route.py`（新規）**: kind 優先・回帰テスト

**効果（オフライン再採点）**: 前回フルスイート JSON を新 `_kind_route` で再評価 → 自動合格 **77→97**（+20、退行 0）。残 REVIEW 8 件は実アプリ側課題（Phase 3 対象）。

### Phase 1 — LLM 層レイテンシ最適化（フラグゲート、既定 OFF）

**`config/llm_flags.py` / `config/llm_config.py`** に Phase 1 フラグ 4 種を追加:

| 環境変数 | 既定 | 効果 |
|---------|------|------|
| `LATENCY_TRIAGE_SINGLE_CALL` | OFF | トリアージ stage1+2 を 1 回 structured call に統合 |
| `LATENCY_EXPLAIN_FAST_LOWRISK` | OFF | 低リスク症状の説明生成を高速モデルへ |
| `LATENCY_EXPLAIN_CACHE` | OFF | 使用上の注意 batch の結果キャッシュ |
| `LATENCY_RECO_PARALLEL` | OFF | 使用上の注意 / 個別アドバイス LLM の並列化 |

- **`src/services/llm_triage.py`**: `LATENCY_TRIAGE_SINGLE_CALL` 時の単一 structured call 経路
- **`src/core/explanation_generator.py`**: 高速モデル切替・キャッシュキー（リスク属性込み）
- **`src/handlers/chat/chat_recommendation_flow.py`**: 並列化フック・翻訳スキップ連携
- **`tests/services/test_p1_latency.py`（新規）**: フラグ OFF/ON の分岐テスト

**A/B 結果**（`log/analysis/2026-07-02_local_v2_chat_test_p1-baseline-off` / `p1-after-on`）: 説明生成 p50 **9,174→3,388ms（-63%）**、Other 系トリアージ **2→1 呼び出し（-44%）**、ルーティング正当性維持（physical 18/18、concierge 12/12）。**e2e p95 は 43,873→40,123ms で KPI <5s 未達**。

### Phase 1b — rule_based 区間計測分離・LLM 境界・スコア並列化

**`config/llm_flags.py`** に Phase 1b フラグ 3 種（既定 OFF）:

| 環境変数 | 既定 | 効果 |
|---------|------|------|
| `LATENCY_EXPLAIN_BATCH_STABILIZE` | OFF | 説明 batch の empty completion 対策（max_tokens 増・リトライ） |
| `LATENCY_RB_LLM_EXTERNAL` | OFF | missing_info / 説明生成 LLM を rb 外（chat flow）へ移動 |
| `LATENCY_SCORE_PARALLEL` | OFF | quick / detailed スコアリングの ThreadPool 並列化 |

- **`src/core/rule_based_recommendation.py`**: `_mark_rb_pipeline_step()` — `rb_missing_info_done` / `rb_scoring_only_done` / `rb_explain_batch_done` のサブステップ計測。`defer_explanation_llm`・並列スコアリング
- **`src/core/explanation_generator.py`**: batch 安定化（MR-C）
- **`src/handlers/chat/chat_recommendation_flow.py`**: MR-D `_apply_external_rb_llm_layers()`、花粉症併用注意マージ、戻り値インターフェース維持
- **`tests/config/test_phase1b_llm_flags.py`（新規）**

**A/B 結果**（physical 18 セッション × 3 ラン、`log/analysis/2026-07-02_local_v2_chat_test_p1b-*`）: 自動合格 **18/18・退行 0**。`rule_based_start`→`rule_based_scoring_only_done` p50 **20,944→2,640ms（-87%、MR-D）**。説明 batch p50 **8,825→3,218ms**。**e2e p95 は 40,932〜57,719ms で KPI <5s 未達**（Phase 1/1b 継続課題）。

### Phase 1 — 待機 UX（部分回答なし）

- **`src/handlers/chat/chat_recommendation_flow.py`**: `mark_processing_step` — `symptom_check` / `candidate_match` 段階通知
- **`static/js/processing_status.js`**: 段階ラベル追加、Sage Terrace トーンの控えめ CSS マスコット（`--symptom` / `--match` / `--notes`）
- **`static/css/main.css`**: bob アニメーション（医療信頼感を損なわない範囲）

### Phase 2 — 安全・トーン事故の是正（フラグゲート、既定 OFF）

**`config/llm_flags.py`** に Phase 2 フラグ 5 種:

| 環境変数 | 既定 | 効果 |
|---------|------|------|
| `SAFETY_VIOLENCE_CONTEXT_GUARD` | OFF | 「喧嘩」等曖昧語の文脈ガード（心理相談→緊急誤検知を抑制） |
| `SAFETY_EMERGENCY_CHANNEL_SPLIT` | OFF | Web/LINE=公的窓口、キオスク=スタッフ文言の出し分け |
| `EMERGENCY_KIOSK_MODE` | OFF | 店頭キオスクデプロイ判定 |
| `UX_COUNSELING_CONTEXT_MAINTAIN` | OFF | counseling モード中の期間/状況フォローアップ維持 |
| `UX_COUNSELING_TONE_VARIETY` | OFF | 定型句反復抑制・応答バリエーション |

- **`src/services/store_emergency_handler.py`**: violence 文脈ガード（`_violence_ambiguous_terms` / `_violence_strong_signals` / `_is_counseling_violence_context`）
- **`src/handlers/chat/emergency_dispatch.py`**: チャネル別緊急メッセージ組み立て
- **`src/handlers/chat/chat_counseling_flow.py` / `chat_other_counseling_route.py`**: counseling 文脈維持フック
- **`src/services/counseling/counseling_generator.py` / `counseling_prompts.py` / `counseling_processor.py`**: トーン多様化
- **`tests/services/test_store_emergency_violence_guard.py`（新規）**
- **`tests/services/test_store_emergency_channel_split.py`（新規）**
- **`tests/services/test_counseling_context_maintain.py`（新規）**
- **`tests/services/test_counseling_tone_variety.py`（新規）**

**検証**（`log/analysis/2026-07-02_local_v2_chat_test_p2-violence-guard`）: counseling_context **13/13** 自動合格（「友人と喧嘩」→暴力緊急の誤検知なし）。

### Phase 3 — ルーティング・内容精度（フラグ 8 種、すべて既定 OFF）

| 環境変数 | 既定 | 効果 |
|---------|------|------|
| `ROUTING_CONCIERGE_INTENT` | OFF | API/SSE/rule_based 等の技術系 meta 意図プローブ拡張（dev のみ技術詳細開示） |
| `ROUTING_CONCIERGE_FOLLOWUP` | OFF | Concierge フォローアップ文脈継承（gate / orchestrator） |
| `ROUTING_STORE_PROCUREMENT` | OFF | 「OTCを買える店」「市販薬の購入先」等の Store ルーティング補完 |
| `RECO_LOW_RISK_HEADACHE` | OFF | 頻出・低リスク単独頭痛の OTC 解熱鎮痛薬提示（めまい等は保留維持） |
| `UX_CORRECTION_DELETE_CANCEL` | OFF | 削除確認待ちからのキャンセル→`memory_delete_cancelled` 明示応答 |
| `UX_SESSION_OPS_REAL_DATA` | OFF | SessionOps 質問種別ごとの実データ応答（status/記録/要約の出し分け） |
| `UX_PROGRESSIVE_CLARIFICATION` | OFF | 曖昧入力連続時の段階的 clarification 文案 |
| `UX_RECO_DEDUP` | OFF | マルチターン同一推奨抑制＋終了意図検出 |

**ルーティング・Concierge**

- **`src/services/concierge_intent.py`**: 技術系 `_META_PROBE_RULES` 拡張、`APP_ENV` ゲート付き技術詳細開示
- **`src/content/concierge_knowledge.ja.json` / `concierge_knowledge.py`**: `technical_details` セクション（dev + フラグ ON 時のみ参照）
- **`src/services/concierge_agent_history.py` / `concierge_orchestrator.py` / `concierge_agent.py`**: フォローアップ intent 継承
- **`src/dialogue/routing/gate.py`**: Store 購入先・Concierge follow-up の gate 補完
- **`src/services/counseling_triage.py` / `store_inquiry_handler.py`**: `_PROCUREMENT_HINTS`・OTC 購入先 fast-path

**内容精度・SessionOps・訂正**

- **`src/core/recommendation/low_risk_symptoms.py`（新規）**: 低リスク頭痛の判定ヘルパ
- **`src/core/rule_based_recommendation.py` / `recommendation_finalizer.py` / `recommendation_constants.py`**: 頭痛 no_recommendation 是正
- **`src/dialogue/session_ops.py` / `status_diagnosis_builder.py` / `session_agent.py`**: SessionOps 実データ化（status / records / summary / history）
- **`main.py`**: `dialogue_state`・`clarification_text_counts` のセッション引き継ぎ
- **`src/handlers/chat/llm_pipeline_guard.py` / `confidence_gate.py`**: progressive clarification 連携
- **`src/handlers/chat/reco_dedup.py`（新規）**: 推奨重複抑制・終了意図検出
- **`src/handlers/chat/chat_recommendation_followup.py`**: reco dedup フック

### Phase 3 — テスト（新規）

| テスト | 内容 |
|--------|------|
| `tests/services/test_concierge_intent_technical.py` | 技術系 meta 意図・dev 開示ゲート |
| `tests/services/test_concierge_followup_routing.py` | Concierge フォローアップ文脈 |
| `tests/services/test_store_procurement_routing.py` | Store 購入先ルーティング |
| `tests/core/test_low_risk_headache_reco.py` | 低リスク頭痛推奨 |
| `tests/dialogue/test_correction_delete_cancel_4a.py` | 削除キャンセル明示応答 |
| `tests/dialogue/test_session_ops_real_data_4b.py` | SessionOps 実データ |
| `tests/handlers/test_progressive_clarification_4c.py` | 段階的 clarification |
| `tests/handlers/test_reco_dedup_4d.py` | 推奨重複抑制 |
| `tests/services/test_session_ops_status_builders.py` | status ビルダー |
| `tests/dialogue/routing/test_gate.py` | gate 拡張（Store/Concierge follow-up） |

### 検証結果（ローカル v2 統合テスト）

| レポート | シナリオ | 自動合格 | 備考 |
|---------|---------|---------|------|
| `2026-07-01_..._post-quality-fix-full` | 105 | **77/105** | Phase 0 前ベースライン |
| `2026-07-02_..._p1-baseline-off` / `p1-after-on` | physical+concierge 等 | 18/18, 12/12 | LLM 層 A/B |
| `2026-07-02_..._p1b-baseline-off` / `p1b-after-all-on` | physical 18 | **18/18** | rb 区間分離 A/B |
| `2026-07-02_..._p2-violence-guard` | counseling 13 | **13/13** | 暴力誤検知ガード |
| **`2026-07-02_..._p3-full`** | **105** | **103/105** | Phase 3 フルスイート（要確認 2: concierge_followup 6/8） |

**KPI サマリ**

- 自動合格: 77/105 → **103/105**（p3-full）
- concierge: 2/12 → **12/12**、store: 3/8 → **8/8**、correction: 8/10 → **10/10**
- **e2e p95**: p3-full で **46,532ms**（目標 <5s **未達** — Phase 1/1b レイテンシ継続課題）
- 内容品質（`--judge`）: レポートに overall / 意図充足 / トーン / 安全スコアを記録

### ログ・分析成果物（2026-07-02）

- **`log/pipeline_perf_log.jsonl`**: 構造化パイプライン計測（rb サブステップ・LLM path 内訳）
- **`log/analysis/`**: `p1-baseline-off` / `p1-after-on` / `p1b-*` / `p2-violence-guard` / **`p3-full`**（JSON/MD/simulation_eval/session_ids）
- **`log/log/`**: `2026-07-02-1.md`〜`2026-07-02-3.md` 日次ログ

### 未着手・継続課題（7/2 時点）

- **Phase 4**: → **7/3 エントリで 4a–4b 着手済み**（p4-unify / legacy 物理削除は pending）
- **e2e p95 < 5s**: triage / NLU / 説明 / 個別アドバイス等の合成遅延。rb 内 LLM は MR-D で分離済み
- **concierge_followup**: p3-full で 6/8 → hotfix で -02/-03 解消（7/2 後半）

---

## 2026年7月1日 — UX 品質改善・v2 統合テスト基盤・ルーティング強化

### 概要

**ブランチ `feature/chat-pipeline-v2`** に、会話品質評価（`log/analysis/2026-07-01_local_v2_chat_test_post-quality-fix-full.md`）で判明した Concierge 意図分類・Store 購入先・SessionOps・推奨フォローアップの弱点を修正。あわせて **ローカル v2 統合テストランナー**（100 YAML シナリオ + GPT ペルソナ）と **Admin v2 テストセッション分離** を整備。

| 関連ドキュメント | 用途 |
|-----------------|------|
| [CHAT_PIPELINE_V2.md](docs/dev/CHAT_PIPELINE_V2.md) | v2 技術仕様 |
| [.cursor/skills/local-v2-chat-test/SKILL.md](.cursor/skills/local-v2-chat-test/SKILL.md) | ローカル v2 テスト手順 |
| [DEV_ERROR_UI_PREVIEW.md](docs/ops/DEV_ERROR_UI_PREVIEW.md) | LLM 障害 UI プレビュー |

### Wave A — IntentRouter gate 拡張・ルーティング精度

- **`src/dialogue/routing/gate.py`**: Stage A 決定論ゲートを大幅拡張
  - 医療緊急・感情カウンセリング・薬局位置意図のキーワードヒント
  - `_resolve_concierge_follow_up` — Concierge 技術質問のフォローアップ文脈継続
  - `_resolve_correction_route` — 訂正意図の gate 即決
  - `_has_pharmacy_location_intent` — OTC 購入先・薬局案内の補完判定
  - カウンセリング/Physical ライフスタイルのフォローアップ回答検出
- **`src/services/concierge_intent.py`**: `_META_PROBE_RULES` に `rule_based`・データ保存・Sage Terrace 等を追加。医薬品相談誤分類の除外ルール強化
- **`src/content/concierge_knowledge.ja.json`**: アーキテクチャ・rule_based・データ保存のナレッジ補完
- **`src/services/store_inquiry_handler.py`**: 医薬品購入先 fast-path・`store_locator` diagnosis kind の整備
- **`src/services/llm_triage.py`**: Concierge/SessionOps/Store の stage1–2 スキップ fast-path。`FIRST_STAGE_TRIAGE_PROMPT` に Store/Concierge 例示追加
- **`src/handlers/chat/chat_concierge_route.py`**: meta probe 連携の改善
- **`src/handlers/chat/chat_emotional_route.py`**: 感情ルートの gate 連携調整
- **`src/dialogue/routing/guards.py`**: fever/store/confidence ガードの微調整

### Wave B — パイプライン順序・障害耐性・エコー検知

- **`src/handlers/chat/chat_post_pipeline.py`**: パイプライン順序再編
  - SessionOps admin probe を LLM 前に早期実行
  - エコー検知（`chat_echo_guard`）を security 直後に挿入
  - IntentRouter dispatch を confidence_gate 前に移動（clarification ループ短絡のため）
- **`src/handlers/chat/chat_echo_guard.py`（新規）**: ボット発話のユーザー入力への混入（エコー）検知・応答
- **`src/handlers/chat/llm_pipeline_guard.py`（新規）**: LLM インフラ障害・clarification ループの単一短絡入口
- **`src/services/llm_unavailability.py`（新規）**: OpenAI quota/429 検知、セッション degraded フラグ、error カード通知
- **`src/services/confidence_gate.py`**: LLM 障害時の clarification 抑制・pipeline guard 連携
- **`src/services/status_diagnosis_builder.py`**: `build_llm_unavailable_status` 追加
- **`src/services/reco_error_messages.py`**: LLM 障害向けメッセージ追加
- **`static/js/main.js`**: インフラ通知 bot をターン完了判定から除外（`isInfraNoticeBotMessage`）、SSE 同期改善
- **`docs/ops/DEV_ERROR_UI_PREVIEW.md`**: LLM 障害 UI の dev プレビュー手順追記

### SessionOps・推奨・カウンセリング品質

- **`src/dialogue/session_ops.py`**: Web でも delete フロー完備（確認→実行→キャンセル）。`dialogue_state` / DB クリア連携
- **`src/agents/session_agent.py`**: SessionOps 品質改善（status 語彙・delete 連携）
- **`src/handlers/chat/chat_recommendation_followup.py`**: 直近推奨後の曖昧入力を再スコアリングせず **推奨要約モード**（`recommendation_summary`）へ
- **`src/handlers/chat/chat_recommendation_flow.py`**: 小児文脈で年齢未確認時は推奨前に年齢確認（`pediatric_age_required`）
- **`src/services/counseling_followup.py`**: 同一フォローアップ質問の重複抑制（`filter_duplicate_counseling_questions`）
- **`src/core/explanation_generator.py`**: 説明文生成の品質調整
- **`src/utils/symptom_helpers.py`（新規）**: 症状名正規化ユーティリティ
- **`src/utils/input_helpers.py`**: 訂正・入力ヘルパー拡張

### v2 ローカル統合テスト基盤

- **`scripts/local_v2_chat_test_runner.py`（新規）**: HTTP 経由の v2 統合テスト（YAML 100 シナリオ、GPT ペルソナ、意図評価、レポート出力）
- **`tests/fixtures/v2_local_chat_scenarios.yaml`（新規）**: session_ops / physical / store / concierge / security 等 100 シナリオ
- **`tests/fixtures/v2_gpt_personas.yaml`（新規）**: GPT ユーザーシミュレータ用ペルソナ
- **`scripts/analyze_dev_logs.py`（新規）**: dev ログ分析
- **`scripts/build_session_transcript_report.py`（新規）**: セッショントランスクリプトレポート生成
- **`scripts/merge_dev_log_report.py`（新規）**: dev ログレポートマージ
- **`.cursor/skills/local-v2-chat-test/`（新規）**: ローカル v2 テストスキル（SKILL / reference / evaluation）
- **`main.py`**:
  - v2 テスト UA（`local-v2-chat-test`）でセッションに `v2_local_test` / `v2_test_scenario` タグ
  - POST `/chat` 応答に `latest_bot` 同梱（SSE 待機不要化）
  - v2 テストセッションは `new_session` 時に旧セッション削除をスキップ
  - Admin API に `v2_local_test` / `v2_test_scenario` フィールド追加
- **`src/services/session_manager.py`**: `is_v2_local_test_session` ガード
- **`src/services/database.py`**: v2 テストセッションのクリーンアップ保護
- **`static/js/admin_chat.js` / `static/css/admin_chat.css` / `templates/admin_chat.html`**: Admin「v2テストのみ」フィルタ・バッジ表示

### 分析・観測・その他

- **`src/analysis/gcp_cloud_run_log_parser.py`**: ログパーサ拡張（dialogue_route / counseling_detail 連携）
- **`src/analysis/session_conversation_analysis.py`**: セッション会話分析の symptom 正規化連携
- **`scripts/measure_intent_router_shadow.py` / `measure_pipeline_baseline.py`**: v2 テスト連携フラグ
- **`src/security/security_validator.py`**: セキュリティ検証の調整
- **`src/handlers/line/flex_messages.py` / `line_message_handler.py`**: LINE Flex・ハンドラ微調整
- **`src/handlers/chat/chat_dev_triggers.py`**: dev トリガー拡張
- **`src/handlers/chat/chat_pipeline_end_guard.py`**: end_guard の調整
- **`src/handlers/chat/chat_session_route.py`**: セッションルート調整
- **`src/services/chat_response_service.py`**: 応答サービス微調整
- **`src/services/counseling/counseling_processor.py`**: カウンセリング処理調整
- **`src/agents/ask_agent.py` / `emergency_classifier.py` / `memory_delete_agent.py`**: エージェント微調整
- **`src/dialogue/dispatcher.py`**: dispatcher ログ・委譲調整

### テスト（新規・拡張）

| テスト | 内容 |
|--------|------|
| `tests/handlers/test_chat_echo_guard.py` | エコー検知 |
| `tests/handlers/test_llm_pipeline_guard.py` | LLM 短絡・clarification ループ |
| `tests/routing/test_llm_unavailability.py` | LLM 障害検知・通知 |
| `tests/handlers/test_pediatric_safety.py` | 小児年齢確認 |
| `tests/services/test_counseling_followup_dedup.py` | カウンセリング質問重複抑制 |
| `tests/services/test_concierge_intent_probe.py` | meta probe 意図 |
| `tests/services/test_store_diagnosis_kind.py` | store diagnosis kind |
| `tests/services/test_database_cleanup_v2_guard.py` | v2 テストセッション DB 保護 |
| `tests/agents/test_session_ops_quality.py` | SessionOps 品質 |
| `tests/llm/test_llm_triage_stage2_store_skip.py` | Store stage2 スキップ |
| `tests/utils/test_symptom_helpers.py` | 症状正規化 |
| `tests/dialogue/routing/test_gate.py` | gate 拡張シナリオ |
| `tests/dialogue/routing/test_guards.py` | guards 拡張 |
| `tests/dialogue/test_session_ops.py` | Web delete |
| `tests/line/test_line_flex_messages.py` | Flex メッセージ |
| `tests/routing/test_confidence_gate.py` | confidence gate |
| `tests/routing/test_triage_cache_ttl.py` | triage キャッシュ |
| `tests/chat/test_chat_dev_triggers.py` | dev トリガー |
| `tests/analysis/test_session_conversation_analysis.py` | セッション分析 |

### 検証結果（ローカル v2 統合テスト）

- **フルスイート**（`2026-07-01_local_v2_chat_test_post-quality-fix-full`）: 105 セッション / 138 ターン、自動合格 **77** / 要確認 **28**
- カテゴリ別: session_ops **12/12**、emergency **8/8**、counseling_context **13/13**、physical_fever **10/10**
- 改善余地: concierge **2/12**、concierge_followup **1/8**、store **3/8**（次イテレーション対象）
- IntentRouter shadow mismatch rate: **8.47%**（118 shadow / 10 mismatch）

### ログ・分析成果物

- **`log/analysis/`**: 2026-06-29〜07-01 の v2 統合テストレポート（JSON/MD）、GCP dev ログ分析（`2026-06-30-dev-9-11/`）、シミュレーション評価
- **`log/log/`**: 日次マークダウンログ（2026-06-29〜07-01）
- 各種 JSONL（`dialogue_route_*`、`counseling_detail`、`triage_analytics` 等）を同期

---

## 2026年6月28日 — Chat Pipeline v2（Wave 0–4 コード実装）

### 概要

**ブランチ `feature/chat-pipeline-v2`** に Web / LINE 共通チャット基盤 v2 を実装。決定権分散（SessionAgent 多重呼び出し・legacy fallback 競合）と履歴注入の散在を `src/dialogue/` へ集約。OTC 推奨本体は **rule_based 維持**。**本番は OFF**、**dev（`APP_ENV=development`）は v2 全機能が一括 ON**。

**実装計画**: [docs/planning/CHAT_PIPELINE_V2_PLAN.md](docs/planning/CHAT_PIPELINE_V2_PLAN.md)（49/54 todo 完了、残 5 件は人手ゲート）

| 関連ドキュメント | 用途 |
|-----------------|------|
| [CHAT_PIPELINE_V2.md](docs/dev/CHAT_PIPELINE_V2.md) | 技術仕様・フラグ・ベースライン |
| [CHAT_ROUTE_EXPECTATIONS.md](docs/dev/CHAT_ROUTE_EXPECTATIONS.md) | ルート期待値・決定権マトリクス |
| [PRE_P0_LINE_QA_10.md](docs/ops/PRE_P0_LINE_QA_10.md) | dev 手動 QA 10 項目 |
| [ARCHITECTURE_MULTI_AGENT.md](docs/dev/ARCHITECTURE_MULTI_AGENT.md) | v2 アーキテクチャ図（追記） |

### Pre-P0（LINE 改善 P0–P2 → v2 統合）

- **`session_agent.py`**: delete 強制上書き削除、`pending_memory_delete` 中 Physical/Emergency 自動キャンセル、status 語彙拡張、Quick Reply 削除/キャンセル統一、`is_pending_delete_cancel` 公開
- **`chat_pipeline_end_guard.py`**: fail-loud（`response_missing` 時 redirect 補完しない）
- **`gate.py`**: pending delete キャンセル → `SessionOps/pending_clear` 即決
- **`counseling_triage.py` / LINE ルート**: 発熱→店舗禁止ゲート、aggressive_input 監査、フィードバック期限切れ B+D
- **`docs/ops/PRE_P0_LINE_QA_10.md`（新規）**: 10 項目 QA チェックリスト

### Wave 0 — 仕様・シナリオ・スキーマ

- **`docs/dev/ROUTE_SPEC.md`**: 決定権マトリクス・期待 route 表
- **`docs/dev/CHAT_PIPELINE_V2.md`（新規）**: v2 技術仕様・パッケージ境界・ベースライン数値
- **`docs/schemas/dialogue_state_v1.json`（新規）**: DialogueContext JSON Schema v1
- **`docs/schemas/intent_router_v1.json`（新規）**: IntentRouter structured output schema
- **`tests/fixtures/route_spec_scenarios.yaml` / `expected_v2_diff.yaml`（新規）**: 契約シナリオ・breaking change 列挙
- **`scripts/measure_pipeline_baseline.py`（新規）**: response_missing / end_guard / fast-path 集計

### Wave 1a — DialogueContext / SessionOps / Envelope

- **`src/dialogue/`（新規パッケージ）**:
  - `context.py` — load/save、合成ビュー、dual-write
  - `context_provider.py` — agent_kind 別履歴窓（default 8 / physical 12 等）
  - `session_ops.py` — delete / summarize / status（SessionAgent から移行）
  - `envelope.py` — `delivery_mode`: sync | sse_phased | line_chunked
  - `pipeline.py` — v2 hook（SessionOps + end_guard のみ）
  - `adapters/web_sse.py` / `adapters/line_delivery.py` — 配信アダプタ
- **`config/llm_flags.py`**: `CHAT_PIPELINE_V2` + ALLOWLIST / DENYLIST per-session ロールバック
- **`scripts/check_w1a_scope.py`（新規）**: Wave 1a 境界違反 CI lint
- **`scripts/dev_v2_flags.ps1` / `scripts/cloudrun_v2_env.example`（新規）**: dev カナリア用

### Wave 1b — IntentRouter + AgentDispatcher

- **`src/dialogue/routing/`（新規）**:
  - `gate.py` — Stage A 決定論ゲート（pending delete、症状、店舗等）
  - `intent_router_llm.py` — Stage B structured LLM（`CHAT_PIPELINE_V2_INTENT_ROUTER_LLM`）
  - `guards.py` — Stage C fever/store/confidence<0.75 clarification（Physical 明示症状時は clarification スキップ）
  - `shadow.py` — shadow ログ + `dialogue_flags`（fever_context / pending_cancelled_by_physical）
  - `metrics.py` — legacy 併存 route 一致率
- **`src/dialogue/dispatcher.py`**: `try_agent_dispatch` — legacy handler へ委譲、dispatch ログに `dialogue_flags`
- **`chat_orchestrator.py`**: v2 dispatch ON 時 `_try_session_agent` スキップ
- **`scripts/measure_intent_router_shadow.py`（新規）**: shadow ログ集計

### Wave 2 — 履歴統合・correction・counseling

- **`src/dialogue/history.py`**: `resolve_*_with_fallback` 系（emergency / emotional / physical / counseling / concierge）
- **`src/dialogue/sync_legacy.py`**: dual-write、`mark_correction_in_dialogue_state`
- **`src/dialogue/concierge_context.py`**: `dialogue_state.concierge` 優先 last_intent
- **`input_helpers.py`**: `detect_correction_intent`（訂正パターン検出）
- **`counseling_generator.py`**: `_ensure_user_turn_at_end` — LLM 直前に現ターン user 注入
- 履歴 fallback 統合: `line_memory_context.py`, `routing_context.py`, `chat_response_service.py`, `nlu_resolve.py`, `chat_recommendation_flow.py`, `line_web_handoff.py`, `chat_triage.py`, `chat_emotional_route.py`, `chat_post_pipeline.py`

### Wave 3 — legacy 整理

- **`chat_post_pipeline.py`**: v2 ON 時 `_run_legacy_other_pre_orchestrator` ガード
- SessionAgent pipeline 三重呼び出し削除（orchestrator + dispatcher 連携）

### Wave 4 — 観測性・KPI

- **`scripts/kpi_dashboard_v2.py`（新規）**: shadow / dispatch / counseling_detail 集計ダッシュボード
- **`src/analysis/intent_router_log_analysis.py`（新規）**: `dialogue_flags` 集計拡張
- **`structured_logger.py`**: `emit_dialogue_route_dispatch` に `dialogue_flags` 追加
- **`docs/dev/ARCHITECTURE_MULTI_AGENT.md`**: v2 Mermaid フロー図・環境変数表

### CI / 検証

- **`.gitlab-ci.yml`（新規）**: `verify_chat_pipeline_v2.ps1` 契約スイート
- **`scripts/verify_chat_pipeline_v2.ps1`（新規）**: v2 コアテスト一括実行（152 passed）

### テスト（新規・拡張）

| テスト | 内容 |
|--------|------|
| `tests/dialogue/` | context / envelope / session_ops / routing / correction |
| `tests/contract/test_intent_router_scenarios.py` | ROUTE_SPEC 契約シナリオ |
| `tests/contract/test_route_spec_expectations.py` | 期待 route 検証 |
| `tests/handlers/test_chat_pipeline_end_guard_fail_loud.py` | end_guard fail-loud |
| `tests/services/test_line_memory_context_v2.py` | v2 履歴委譲 |
| `tests/services/test_chat_response_service_v2.py` | v2 履歴統合 |
| `tests/utils/test_correction_detection.py` | 訂正検出 |
| `tests/services/test_counseling_generator_user_inject.py` | user ターン注入 |
| `tests/analysis/test_intent_router_log_analysis.py` | dialogue_flags 集計 |


### 環境変数 — dev 一括 ON（2026-06-28 追記）

ローカル / GCP dev で **段階フラグ・ALLOWLIST 不要** に v2 全機能を使えるよう `config/llm_flags.py` を変更。

| 環境 | 設定 |
|------|------|
| **ローカル** | `.env` の `APP_ENV=development` のみ（`.env.example` 既定） |
| **GCP dev** | Cloud Run に `APP_ENV=development` |
| **明示 ON** | `CHAT_PIPELINE_V2=true` 1 変数（IntentRouter / dispatch / LLM までカスケード ON） |
| **本番** | `APP_ENV=production` + 未設定 = **OFF**（従来どおり） |

- **`config/llm_flags.py`**: `CHAT_PIPELINE_V2=true` 時、サブフラグ未設定 = router / dispatch / LLM すべて ON。development ランタイムでは `CHAT_PIPELINE_V2` 未設定でも v2 全機能有効
- **`.env.example`**: v2 フラグの dev 向け説明を追記
- **`scripts/dev_v2_flags.ps1`**: 簡素化（`CHAT_PIPELINE_V2=true` のみ、`-Off` で明示 OFF）
- **`scripts/cloudrun_v2_env.example`**: `APP_ENV=development` 中心に整理
- **`docs/dev/CHAT_PIPELINE_V2.md` / `CHAT_PIPELINE_V2_PLAN.md`**: 一括 ON 手順を更新
- **`tests/dialogue/test_v2_flags.py`**: dev 自動 ON・カスケード・opt-out テスト追加

### 残タスク（人手ゲート — 5 件）

1. CCR `concierge_state` 永続化を main/dev にマージ（Wave 1a ブロッカー）
2. Pre-P0: 48h 以内 dev 手動デプロイ + LINE QA 10 項目全合格
3. Wave 0 レビュー承認（ROUTE_SPEC + diff + baseline + schema）
4. Wave 1a dev 手動 QA + ゲートレビュー
5. Wave 4: dev v2 デフォルト ON + 2 週 soak

---

## 2026年6月27日（後半） — 管理 API 認証・LINE 二重配信防止・医薬品購入先ルーティング・レッドチーム

### 概要

ローカルレッドチーム（148 ケース）で判明した **管理 JSON API 無認証露出** を `admin_json_auth` Depends により一括修正。**LINE Webhook 重複**による二重 Push を DB 去重・reply token 失効検知・progressive 配信ロジックで抑止。

**医薬品購入先・入手要求**（「処方箋なしの購入先」「処方箋の購入先」等）を店舗案内 fast-path へ振り分け、Concierge structural greeting 誤分類と不適切カウンセリング経路を回避。**`scripts/local_red_team_runner.py`** でオフライン／HTTP 混在のセキュリティ回帰を自動化。

### 管理 API 認証統一（レッドチーム P0）

- **`main.py`**: `admin_json_auth` Depends を新設し、管理系 JSON エンドポイント（`/admin/*`・`/api/status`・`/api/performance`・フィードバック CRUD 等）に一括適用
- **`static/js/admin_chat.js`**: 監視・LLM 設定・フィードバック・手動返信等の fetch を `adminFetchOptions()` 経由に統一
- **`tests/api/test_fastapi_contract.py`**: 未認証 401 / cookie 認証 200 の契約テストを追加

### LINE Webhook 去重・二重配信防止

- **`database.py`**: `line_webhook_dedup` テーブルと `try_claim_line_webhook_event`（Cloud Run 複数インスタンス向け TTL claim）
- **`line_dedup.py`**: DB claim をファイル去重の前段に追加
- **`line_reply.py`**: reply token 400 失効時に `reply_token_unavailable` を設定
- **`line_delivery.py`**: reply token 不可時は Push フォールバックをスキップ（二重配信防止）
- **`line_progressive_delivery.py`**: carousel Push 済み時は full bundle 再送を抑止。未送信時は reply_token 付き一括配信
- **`line_message_handler.py`**: pipeline 後 redirect を `deliver_line_messages` 経由に統一

### 医薬品購入先ルーティング

- **`counseling_triage.py`**: `classify_medicine_procurement_route` / `detect_prescription_procurement_request` — OTC（`otc_store`）と処方箋（`pharmacy_prescription`）を分岐
- **`store_inquiry_handler.py`**: `generate_medicine_procurement_response` と fast-path / 詳細分類での `_resolve_procurement_store_response`
- **`concierge_intent.py`**: 購入先要求を structural greeting から除外。`_is_medicine_consultation` に「処方箋」「処方」「購入先」「入手」を追加
- **`config/keywords.py`**: 単独「処方」を `TREATMENT_KEYWORDS` から除外（購入先 fast-path との競合回避）

### セキュリティ・その他

- **`security_validator.py`**: `DANGER_PATTERNS` の不正正規表現（`+` 連結）を修正

### ローカルレッドチーム

- **`scripts/local_red_team_runner.py`（新規）**: known_attack / PI プローブ / 暴言 / マルチターン / red_team.jsonl 等 148 ケースをローカル FastAPI へ投入
- **`log/analysis/local_red_team_2026-06-27.md` / `.json`**: 実行結果（known_attack 30/30 ブロック、管理 API 露出を修正前に記録）

### テスト

| テスト | 内容 |
|--------|------|
| `test_prescription_procurement_guard.py`（新規） | 購入先分類・店舗案内 fast-path・Concierge 誤分類防止 |
| `test_fastapi_contract.py` | 管理 API 401/200 契約 |
| `test_line_dedup.py` | DB 去重 duplicate 検出 |
| `test_line_delivery.py` | reply token 不可時 Push スキップ |
| `test_line_progressive_delivery.py` | carousel 済み full bundle 再送抑止 |

---

## 2026年6月27日 — SessionAgent・LINE QA（P0–P2）・Concierge 文脈ルーティング・GCP ログ分析強化

### 概要

GCP ログ分析（2026-06-25〜26）と開発 QA に基づき、**SessionAgent** でセッション統合・管理画面ルーティング・メモリ削除を集約し、**LINE 改善計画 P0–P2**（ルーティング修正・`counseling_detail` 全経路・攻撃入力・フィードバック期限・トリアージ短絡・pipeline_perf 警告）を実装した。

続けて **Concierge 文脈ルーティング（CCR-P0〜P2）** により、architecture / doc_* / session_ops 等のメタ会話で「詳しく」「もっと」等のフォローアップが **greeting 誤分類** されないよう、prior intent 推定・structural greeting ガード・meta LLM スキップ条件を強化。**`concierge_state` の DB 同期**と **`concierge_intent_source` の counseling_detail 記録**でログ分析と dev QA の追跡性を向上。

**GCP ログ分析パイプライン**は `counseling_detail`・`conversation_history`・`chat_flow` の 3 ソースマージ、**trace-only セッション**出力、`response_missing` 明示、品質メトリクス拡張、レポートテンプレート／skill 手順の更新を行った。

### SessionAgent と LINE QA（P0–P2）

- **`session_agent.py`（新規）**: セッション状態・削除・要約・統合ステータスを SessionAgent に集約。Concierge / 管理画面 / LINE から `classify_session_intent` 経由でルーティング
- **`memory_delete_agent.py`**: SessionAgent 連携にリファクタ
- **`status_diagnosis_builder.py`**: 統合セッション診断・Concierge カード向け表示を拡張
- **`sage_message_plain.py`（新規）**: Flex / HTML 応答のプレーンテキスト化（ログ・分析用）
- **`chat_pipeline_end_guard.py` / `chat_post_pipeline.py`**: 全経路で `counseling_detail` 非同期出力のカバレッジ拡大
- **`chat_input_validator.py` / `known_attack_rules.py`**: 攻撃・挑発入力のパイプライン到達抑止を追加
- **`line_feedback.py`**: フィードバック postback の期限切れ処理
- **`line_flex_messages.py` / `line_menu_actions.py` / `line_quick_actions.py`**: Sage マーカー・メニュー整合
- **`llm_triage.py`**: stage2 スキップ条件（短絡）の調整
- **`pipeline_perf.py`**: 遅延・欠損 sid 等の警告ログ
- **`docs/planning/LINE_IMPROVEMENT_PLAN_2026-06-27.md`（新規）**: P0–P3 タスク一覧と受け入れ基準

### Concierge 文脈ルーティング（CCR）

- **`concierge_agent_history.py`**: `doc_*` / `session_ops` をメタフォローアップ対象に追加。`resolve_prior_meta_intent`（`concierge_state.last_intent` 優先）、`should_block_structural_greeting`、`infer_lost_context_follow_up_intent`、`is_session_ops_bot_message`
- **`concierge_orchestrator.py`**: `session` 引数、`prior_intent_follow_up` / `lost_context_follow_up`、session_ops 時の `session_intent` 付与（`_apply_follow_up_intent`）
- **`concierge_intent.py`**: `infer_structural_concierge_intent` に prior intent / 履歴ガード
- **`meta_triage.py`**: フォローアップ維持のプロンプト追記。フォローアップ文・直前メタ意図時は meta LLM スキップしない
- **`concierge_agent.py`**: orchestrator へ `session` / `routing_ctx` を渡し、フォローアップ解決を state 優先に統一
- **`chat_concierge_route.py`**: `_sync_session_db` で `concierge_state` / `last_triage_result` を永続化。Concierge ログに `concierge_intent_source`
- **`chat_orchestrator.py` / `chat_post_pipeline.py`**: `enrich_other_concierge_intent` に `session` を渡す
- **`counseling_logger.py` / `structured_logger.py`**: `routing_meta`（intent / source / llm_used）を `counseling_detail_log.jsonl` に出力
- **`docs/planning/CONCIERGE_CONTEXT_ROUTING_PLAN_2026-06-27.md`（新規）**: 意思決定・フロー・CCR タスク定義

### GCP ログ分析（セッション復元・品質）

- **`session_conversation_analysis.py`**: 3 ソースマージ（`counseling_detail` / 埋め込み `conversation_history` / `chat_flow`）。trace-only セッション、`turn_source`・`response_missing`、`meta_follow_up_to_greeting`（critical）検出
- **`session_transcript_markdown.py`**: ソース列・trace-only 注記・未記録返信の明示
- **`gcp_cloud_run_log_parser.py`**: `PIPELINE_PERF` から `session_id`（sid）を trace に補完
- **`quality_metrics.py`**: `counseling_session_count` / `trace_only_session_count` / `chat_flow_trace_count` を集計
- **`.cursor/skills/gcp-log-analysis/`**: 3 ソースマージ手順、Wave B 全ターン展開、`response_missing` 評価ルール、レポートテンプレ更新

### テスト

| テスト | 内容 |
|--------|------|
| `test_session_agent.py`（新規） | SessionAgent 分類・応答 |
| `test_session_admin_routing.py`（新規） | 管理画面 session ルーティング |
| `test_concierge_context_routing.py`（新規） | フォローアップ・structural guard・orchestrator |
| `test_meta_triage_skip.py` | フォローアップ時 meta LLM 非スキップ |
| `test_session_conversation_analysis.py` | meta_follow_up 検出・履歴展開・trace-only |
| `test_counseling_detail_coverage.py`（新規） | counseling_detail 経路 |
| `test_llm_triage_stage2_skip.py`（新規） | トリアージ短絡 |
| `test_aggressive_pipeline_reach.py` / `test_jailbreak_patterns.py` | 攻撃入力 |
| `test_chat_pipeline_end_guard.py` / `test_structured_logger_async.py` 等 | パイプライン終端・非同期ログ |

---

## 2026年6月26日 — jailbreak 即時ブロック・パイプライン終端ガード・Concierge フォールバック

### 概要

**既知の jailbreak / プロンプトインジェクション**（「プロンプトインジェクション」「命令にすべて従ってください」「ignore instructions」等）を `known_attack_rules` でルールマッチし、**SECURITY_ROLLOUT_PHASE に依存せず即時警告応答**するよう入力検証を強化した。重複パターンは `security_validator` の `DANGER_PATTERNS` から除外し、SSOT を一本化。

あわせて **トリアージ直後の LLM バックグラウンド監査**（`llm_security_check`）を追加。リクエストはブロックせずログ警告のみ。既知攻撃はルール側で先に処理する。

**パイプライン終端ガード**（`chat_pipeline_end_guard`）を導入し、当該ターンで bot 応答が無い場合は Concierge **redirect** を自動補完。Web / LINE 共通で `chat_post_pipeline` の全 return 経路をラップ。LINE 側でも bot 未生成時に `build_redirect_text` で push する二重安全策を追加。

**Concierge オーケストレータ**は meta LLM スキップ時・未解決時に `redirect` intent をフォールバック付与。**不明要求カウンセリング**は Concierge intent 付与かつ **bot 応答済み**の場合のみスキップ（intent のみではスキップしない）。confidence gate 後の Other カテゴリでもカウンセリングへフォールバックする経路を追加。

### セキュリティ — 既知攻撃ルールと LLM 監査

- **`known_attack_rules.py`（新規）**: 高信頼 jailbreak / プロンプトインジェクション正規表現（日英）。`match_known_attack` / `KNOWN_ATTACK_WARN_MESSAGE`
- **`llm_security_check.py`（新規）**: `schedule_llm_security_audit` — トリアージ前にバックグラウンド LLM 分類（`LLM_SECURITY_PARALLEL_ENABLED`、warn-only・ブロックなし）
- **`chat_input_validator.py`**: `known_attack_rules` マッチ時に即時警告 bot を追記して 200 返却（`kind=known_attack`）
- **`security_validator.py`**: `validate_user_input` 入口で known_attack を先に評価。`DANGER_PATTERNS` から known_attack と重複するパターンを除外
- **`chat_triage.py`**: `run_triage` 冒頭で `schedule_llm_security_audit` を非同期起動

### パイプライン終端ガードと LINE 配信

- **`chat_pipeline_end_guard.py`（新規）**: `finalize_pipeline_response` / `append_redirect_bot_response` — bot 未追記ターンに redirect を補完（`pipeline_end_guard: redirect`）
- **`chat_post_pipeline.py`**: 全早期 return を `_guard_return` でラップ。confidence gate 後 Other で `run_other_unknown_counseling` フォールバックを追加
- **`line_session.py`**: `count_bot_messages_in_session`（新規）
- **`line_message_handler.py`**: パイプライン前後の bot 数比較。未生成時は `build_redirect_text` で push（従来の `GENERIC_SAFE_TEXT` を置換）
- **`line_admin_manual_reply.py`**: LINE push 可否判定を `get_line_channel_access_token()` に統一

### Concierge オーケストレータとカウンセリング境界

- **`concierge_orchestrator.py`**: `general_other` で meta LLM スキップ時 → `redirect` / `general_other_fallback`。meta 未解決時 → `redirect` / `meta_unresolved_fallback`
- **`chat_other_counseling_route.py`**: `_concierge_answered_current_turn`（新規）— intent 付与かつ当該ターン bot 応答済みの場合のみカウンセリングをスキップ

### フロントエンド — ブロック user DOM 安定化

- **`static/js/main.js`**: ブロック確定後も `chatPendingTurnId` 消失・キー不一致で楽観 user を拾う `findOptimisticUserNodeForBlockedTurn`。セッション上ブロック user が1件のとき DOM 重複を畳む `collapseDuplicateBlockedUserDomNodes`。同期時のブロックプレースホルダ重複 append を抑止

### テスト

| テスト | 内容 |
|--------|------|
| `test_jailbreak_patterns.py`（新規） | 既知攻撃ルール・validator スコアリング |
| `test_llm_security_check.py`（新規） | LLM 監査・即時ブロック・warn-only 非ブロック・ブロック user プレースホルダ追記 |
| `test_chat_post_pipeline.py` | 終端ガード redirect 補完 |
| `test_concierge_acceptance.py` | Concierge bot 有無によるカウンセリングスキップ・プロンプトインジェクション redirect |
| `test_meta_triage_skip.py` | general_other / meta 未解決時の redirect フォールバック |
| `test_line_message_handler.py` | パイプライン後 bot 追記のモック整合 |

---

## 2026年6月25日 — GCP ログ解析・LINE 絵文字/スタンプ・Concierge メタ質問 LLM 化・法令コンプライアンス・免責改定

### 概要

本番 GCP ログの分析結果に基づき、**import 欠落**（`counseling_processor` → `generate_counseling_response`）や**ルーティングミス**（OTC/市販薬の用語定義質問が医薬品相談に誤分類）を修正した。Concierge の **capabilities / architecture / app_about** メタ質問を固定カードから**会話履歴付き LLM 応答**に刷新し、カウンセリング中のメタ質問は Concierge に委譲する。**カウンセリング詳細ログ**（`counseling_detail_log.jsonl`）へ `conversation_history` を記録するようチャット全ルートを統一。あわせて **GCP Cloud Logging エクスポートの決定的前処理パイプライン**（パーサー・セッション会話分析・CLI・skill）を新設し、**セッション別 Markdown トランスクリプト**と**マルチタスク並列解析**ワークフローを追加した。

LINE 向けには **絵文字のみ入力**をトリアージ前に処理するルート（侮辱絵文字は長めの自己紹介、それ以外は軽量 LLM 5 分類 → Concierge/Emotional）と、**公式スタンプの挨拶・感謝をテキストに変換**して既存フローへ渡す処理を実装。画像・音声など非テキストは種別ごとの案内文で応答する。

運用面では **`GET /health` 起動プローブ**でデプロイ直後の 503 を抑止し、フロントのセッション同期間隔を **30 秒**に変更した。

**午後の追記:** ローカル最新以降の **GCP ログ差分エクスポート**（`prepare_gcp_log_analysis.py`）と、emoji / Concierge / LINE 経路の **counseling_detail 記録漏れ**を補完。Concierge の**挨拶・感謝の口調ミラーリング**と**挑発的短呼びかけ**（「おい」「ねえ」等）のサニタイズ、**architecture メタ質問**の動的カード表示と担当ロスター分離を実装。**薬機法・景表法**など法令コンプライアンス質問を `doc_terms` へルーティングし、利用規約**第3条**に医薬品関連法令への配慮を統合した。

### GCP ログ解析基盤（新規）

- **`gcp_cloud_run_log_parser.py`（新規）**: `downloaded-logs-*.json` を `LogEntry` に読み込み、HTTP エラー・パイプライン性能・LLM コスト・LINE webhook・チャットフロー trace・Neon DB・デプロイリビジョン・ユーザー会話などをセクション JSON に分割
- **`session_conversation_analysis.py`（新規）**: カウンセリング詳細ログと trace を突合し、ターン単位の issue 検出・セッション grade・intent mismatch・会話履歴再構成
- **`medicine_recommendation_log_extractor.py`（新規）**: Physical / 薬推奨パイプラインイベント（症状検出・推奨医薬品・agent_step handoff）の抽出
- **`quality_metrics.py`（新規）**: 解析バンドルから会話品質・HTTP エラー集計メトリクスを生成
- **`scripts/analyze_gcp_logs.py`（新規）**: CLI。`log/analysis/<stem>/manifest.json` と `sections/*.json` を出力
- **`.cursor/skills/gcp-log-analysis/SKILL.md`（新規）**: エクスポート JSON → CLI 抽出 → セクション並列 LLM 解釈 → Markdown レポートのワークフロー
- **`session_transcript_markdown.py`（新規）**: セッション会話を送受信時刻・E2E/フェーズ別処理時間付き Markdown に整形。CLI バンドル出力時に `sessions/*.md` を自動生成
- **`session_conversation_analysis.py`（拡張）**: trace 突合を「ユーザー送信時刻 ≥ trace 開始」の前方一致に修正。ターンに `timing`（`build_turn_timing`）と `enrich_routing_from_trace` を付与
- **`gcp_cloud_run_log_parser.py`（拡張）**: `write_session_transcripts` 連携。`manifest.json` に `session_transcripts` パスを記録
- **`.cursor/skills/gcp-log-analysis/references/multitask-orchestration.md`（新規）**: Wave A（固定 4 セクション）+ Wave B（セッション単位）の Task 並列起動手順
- **`references/report-template.md`（更新）**: セッショントランスクリプト参照・マルチタスク下書きマージ形式を追記

### LINE 絵文字ルート（トリアージ前）

- **`chat_emoji_route.py`（新規）**: `try_emoji_pre_triage_route` — LINE セッション限定、`run_triage` 直前に挿入
  - 侮辱絵文字（テキスト併記含む）→ `build_emoji_soft_intro_text`（侮辱への言及なし・concierge_knowledge SSOT 由来の長め自己紹介）
  - 絵文字のみ → 軽量 LLM 5 分類（`greeting` / `thanks` / `emotional` / `offensive` / `unknown`）
  - `greeting`・`thanks` → Concierge、`emotional` → Emotional ルート、`unknown` → テキスト入力を促す中立応答
- **`emoji_intent.py`（新規）**: `classify_emoji_intent_llm` / `build_emoji_soft_intro_text` / `build_emoji_unknown_ack_text`
- **`emoji_input.py`（新規）**: `is_emoji_only_message` / `contains_offensive_emoji` / `extract_emojis`（Unicode 絵文字検出）
- **`chat_post_pipeline.py`**: `before_emoji_route` 計測付きで絵文字ルートをトリアージ前に実行
- **`concierge_intent.py`**: `infer_structural_concierge_intent` が絵文字のみ入力を構造 intent から除外（LLM 分類との二重判定防止）
- **`config/llm_config.py`**: `emoji_intent` ロール（`gpt-4o-mini`、タイムアウト 8 秒）を追加

### LINE スタンプ・非テキストメッセージ

- **`line_non_text.py`（新規）**: スタンプ・画像・音声・動画・ファイル・位置情報の案内とスタンプ解釈
  - `try_resolve_sticker_as_text`: 挨拶・感謝スタンプを合成テキストへ変換し既存テキストフローへ渡す
  - `build_non_text_reply`: メッセージ種別ごとの未対応案内文
  - `keywords` / `classify_concierge_intent` / 正規表現による greeting・thanks 判定
- **`data/line_official_sticker_intents.json`（新規）**: 公式スタンプ `packageId`/`stickerId` → 合成テキストマップ。`variant_groups` で多言語パックの index 展開
- **`line_message_handler.py`**: スタンプは解釈成功時に `_process_text_message` へ委譲。未登録スタンプは `STICKER_UNSUPPORTED_REPLY`。その他非テキストは種別別案内

### Concierge メタ質問の LLM 化とルーティング修正

- **`concierge_agent.py`**
  - `generate_meta_concierge_text` / `_invoke_meta_concierge_llm`（新規）: `capabilities`・`architecture`・`app_about` を履歴・文脈ブロック付き LLM で回答。フォールバックは従来カード
  - `resolve_concierge_intent`: 店舗ゲート・オーケストレータを**医薬品相談判定より先**に評価（OTC 用語質問の誤除外を防止）
- **`concierge_intent.py`**
  - `CONCIERGE_META_INTENTS` / `triage_has_concierge_meta_intent` / `should_exit_counseling_for_concierge`（新規）
  - `_is_medicine_term_definition`（新規）: 「OTCって何？」「市販薬とは」等を医薬品相談から除外
  - メタ probe に OTC/市販薬用語定義・「誰が回答したか」パターンを追加
- **`chat_concierge_route.py`**
  - メタ intent 応答を LLM 経由に切替
  - `_concierge_already_answered_user`（新規）: 同一挨拶の二重 POST を抑止（duplicate_skip 廃止方針との両立）
  - Concierge ログに `conversation_history` を付与

### カウンセリング中のメタ質問委譲と詳細ログ履歴

- **`chat_counseling_flow.py`**: `should_exit_counseling_for_concierge` でカウンセリングモードを終了し Concierge に委譲
- **`counseling_processor.py`**: 欠落していた `generate_counseling_response` の import を追加（本番 `NameError` 修正）
- **会話履歴ログ統一**（`conversation_history=None` → 実履歴）:
  - `chat_counseling_flow.py`, `chat_emotional_route.py`, `chat_category_route.py`, `chat_other_counseling_route.py`, `chat_triage_follow_ups.py`, `chat_pollen_consultation_route.py`, `chat_concierge_route.py`
  - `get_counseling_conversation_history`（`line_memory_context`）経由で取得

### 防御的ガード・管理 API

- **`medicine_data.py`**: `get_medicines_by_type(None)` / 空文字で空リストを返すガード（CSV 全件マッチ防止）
- **`main.py`**
  - `GET /health`（新規）: Cloud Run 起動プローブ用の軽量エンドポイント（`status`・`git_commit`）
  - `api_admin_sessions`: `resolve_session_line_context` / `format_admin_timestamp_iso` の import をループ外へ移動

### Cloud Run デプロイ・運用

- **`cloudbuild.yaml`**: `--startup-probe=httpGet.path=/health,httpGet.port=8080,...` を追加（最大約 120 秒まで起動待ち）
- **`docs/ops/CLOUD_RUN_LLM_ENV.md`**: 起動プローブ設定の記載を追加

### GCP ログ差分取得とカウンセリング詳細ログの網羅（追記）

- **`scripts/export_gcp_logs.py`（新規）**: `gcloud logging read` で Cloud Run ログを `log/raw/downloaded-logs-*.json` にエクスポート。`--since-last-local` でローカル最新カバレッジ以降のみ取得
- **`scripts/prepare_gcp_log_analysis.py`（新規）**: 差分エクスポート → `analyze_gcp_logs.py` まで一括実行。`status: ready / no_gap / empty / dry_run` を返す
- **`gcp_log_export.py` / `gcp_log_local_state.py`（新規）**: エクスポート状態（`log/raw/export_state.json`）と `metadata.json` の `time_range.end` から baseline を解決
- **`.cursor/skills/gcp-log-analysis/`**: Step 0 差分取得手順・multitask 起動フレーズを追記
- **`structured_logger.py`**: Cloud Logging の行分割を避けるため **compact 1 行 JSON** 出力に変更
- **`gcp_cloud_run_log_parser.py`**: `conversation_history` 内のネスト `{` / `}` でブロックが途中分割されないよう **brace depth 追跡**。compact 1 行 JSON も同一関数で解析
- **`counseling_logger.py`**
  - `mark_counseling_detail_logged` / `was_counseling_detail_logged`: 同一ターン二重記録抑止
  - `maybe_log_line_turn_counseling_detail`: LINE 配信直前フォールバック（emoji 短応答等の未記録経路を補完）
  - `resolve_bot_message_plain_text`: Flex / HTML からログ用プレーンテキスト抽出
- **`chat_emoji_route.py` / `chat_concierge_route.py` / `line_message_handler.py`**: 上記 counseling_detail 記録を各経路に接続

### Concierge 挨拶・感謝・メタ表示の品質改善（追記）

- **`concierge_agent.py`**
  - **挨拶**: ユーザー口調へのミラーリング強化。挑発的短呼びかけ（「おい」「ねえ」「もしもし」等）の**口調真似を検出・除去**し、リトライヒントで LLM に再生成を促す
  - **感謝**: `generate_thanks_text`（新規）— 会話履歴・文脈付き LLM 応答。フォールバックは `build_thanks_text`
  - **メタ質問**: `format_meta_concierge_context_block`（新規）— who-is-answering / multi-agent / architecture 向け文脈メモ
  - **ドキュメント回答**: 要点 5〜8 項目の箇条書き化。全文写し出し禁止。ℹ️ から全文確認できる旨を末尾に案内
- **`concierge_agent_history.py`（新規）**: Concierge 専用履歴ブロック整形、`resolve_last_responding_agent`、`is_who_is_answering_question`、`is_multi_agent_concept_question`、`is_architecture_explanation_question`、`is_agent_roster_question`
- **`concierge_templates.py`**: `structure_concierge_meta_display` / `split_dynamic_body_paragraphs` / `build_dynamic_concierge_line_flex` — LLM 本文を段落・箇条書きに構造化。`build_agent_roster_items` / `merge_agent_roster_section` で担当一覧カードを分離表示
- **`emoji_intent.py`**: 侮辱・挑発絵文字向け `generate_offensive_emoji_response_llm`（新規）。複数フォールバック文
- **`chat_emoji_route.py`**: offensive 絵文字を LLM 寄り添い応答へ。counseling_detail ログ付与
- **`static/css/sage_terrace.css`**: メタ status カードの段落・箇条書きスタイル
- **`static/js/ui/status_renderer.js`**: `content_format: status_card` の動的セクション描画対応

### architecture メタ質問の役割一覧カード（追記）

- **`concierge_agent.py`**: `is_agent_roster_question` 時のみ `merge_agent_roster_section` で「担当の役割」カードを付与。LLM 本文は導入 2〜4 文に制限し、エージェント一覧の箇条書き埋め込みを禁止
- **`is_architecture_explanation_question`**: マルチエージェントの意味・仕組み説明と、構成・役割一覧質問を分離

### 法令・コンプライアンス質問のルーティングと免責改定（追記）

- **`concierge_intent.py`**
  - `is_legal_compliance_meta_question`（新規）: 薬機法・景表法・「違法じゃない？」等を検出
  - `_is_medicine_consultation` から除外し、`probe_meta_concierge_intent` → `doc_terms` へルーティング
  - `should_exit_counseling_for_concierge` でカウンセリング中の法令質問を Concierge に委譲
  - `_META_PROBE_RULES` に薬機法・景表法・プラポリ・利用規約パターンを優先追加
- **`meta_triage.py`**: `doc_terms` / `doc_privacy` のプロンプト例に法令遵守・薬機法質問を明記
- **`concierge_agent.py`**: 法令コンプライアンス質問時は「合法」「問題ない」と断言しない追加要件。OTC 参考案内・β版の位置づけを説明
- **`docs/public/免責事項・利用規約.md`**: 第3条を「免責事項および医薬品関連法令への配慮」に改題（改定履歴 2026-06-25 追記）
- **`about_modal_html.json`**: 第3条の日英韓中 4 言語 HTML を同期更新
- **`static/js/main.js`**: 情報モーダル内の第3条を 4 言語で同期（薬機法・景表法・ルールベース選定・AI 生成・β版免責）
- **`templates/index.html`**: 非 Sage UI の情報一覧に「利用規約・免責」リスト項目を追加

### フロントエンド

- **`static/js/main.js`**: セッション定期同期の `setInterval` を 10 秒 → **30 秒**に変更（API 負荷軽減）
- **`static/js/main.js`**: Sage Terrace 情報モーダルのリスト項目タイトル・説明を `sageModal` マップで上書き（`site-about` / `app-overview` / `disclaimer` 等）

### テスト

| テスト | 内容 |
|--------|------|
| `test_gcp_cloud_run_log_parser.py`（新規） | ログ読込・セクション抽出・バンドル書き出し |
| `test_gcp_log_analysis_incremental.py`（新規） | 増分解析・マニフェスト整合 |
| `test_session_conversation_analysis.py`（新規） | ターン issue 検出・セッション grade・intent mismatch |
| `test_counseling_processor_import.py`（新規） | `generate_counseling_response` import 解決 |
| `test_medicine_data_guard.py`（新規） | `get_medicines_by_type` の None/空文字ガード |
| `test_concierge_intent_extended.py`（新規） | OTC 用語・メタ質問・医薬品相談境界 |
| `test_concierge_route.py` | メタ intent の LLM 応答・二重 POST 抑止 |
| `test_concierge_acceptance.py` / `test_concierge_agent.py` | メタ LLM 化・ルーティング順序に合わせて更新 |
| `test_hospital_identity_question.py` / `test_chat_greeting_route.py` | 委譲・挨拶境界の調整 |
| `test_fastapi_contract.py` | `GET /health` の契約テスト |
| `test_session_transcript_markdown.py`（新規） | フェーズ breakdown 要約・ターン timing・Markdown トランスクリプト |
| `test_chat_emoji_route.py`（新規） | 侮辱絵文字・絵文字のみ unknown・greeting→Concierge・非 LINE スキップ |
| `test_emoji_intent.py`（新規） | JSON パース・soft intro・unknown ack・LLM 分類 |
| `test_emoji_input.py`（新規） | 絵文字のみ判定・侮辱絵文字検出 |
| `test_line_non_text.py`（新規） | 非テキスト案内・スタンプ keywords/公式マップ/variant 展開・dispatch 統合 |
| `test_gcp_log_local_state.py`（新規） | baseline 解決・export_state 読み書き |
| `test_export_gcp_logs.py`（新規） | 差分エクスポート CLI・filter 生成 |
| `test_counseling_delivery_log.py`（新規） | LINE 配信フォールバック・二重記録抑止 |
| `test_structured_logger.py`（新規） | compact JSON 1 行出力 |
| `test_gcp_cloud_run_log_parser.py` | ネスト conversation_history・compact JSON 解析 |
| `test_concierge_agent_history.py`（新規） | who-is-answering・roster・architecture 判定 |
| `test_concierge_meta_display.py`（新規） | 動的メタ表示・inline bullet 抽出・roster マージ |
| `test_concierge_agent.py` | 挑発呼びかけサニタイズ・感謝 LLM・roster カード付与 |
| `test_emoji_intent.py` | offensive フォールバック全件・LLM 応答 |
| `test_chat_emoji_route.py` | counseling_detail ログ・offensive LLM 経路 |
| `test_line_flex_status_spec.py` | 動的 status カード Flex 仕様 |
| `test_legal_compliance_routing.py`（新規） | 薬機法→doc_terms・医薬品相談除外・カウンセリング委譲 |
| `test_concierge_intent_extended.py` / `test_concierge_route.py` | 法令質問ルーティング・doc_terms ペイロード |

---

## 2026年6月24日 — Concierge 挨拶強化・攻撃的入力境界・LLM 生入力・チャット UI 同期

### 概要

Concierge の**挨拶・雑談 LLM** を会話履歴・文脈メモ付きに刷新し、同一挨拶の連続送信でも毎回異なる応答を返すよう変更した（重複スキップを撤廃）。**攻撃的・脅迫的入力**（「殺すぞ」等）を `aggressive_input.py` に集約し、カウンセリング開始ではなく統一境界案内を返す。LLM プロンプトには正規化前の**生ユーザー入力**（`resolve_llm_user_text`）を渡すようパイプライン全体を統一。フロントエンドでは**セキュリティ案内 bot の DOM 描画**と**進行中ターンの session 同期**を改善。Sage Terrace UI の**フォントサイズ変数**と挨拶コピーの「市販薬」表記を整備した。

### 攻撃的入力検出と境界応答

- **`aggressive_input.py`（新規）**: 絶対ブロック・数字隠語・脅迫表現（「殺すぞ」等）・不適切キーワードの単一 SSOT。症状文内スラング（「頭痛が殺す」）は除外
- **`chat_inappropriate_route.py`**: カウンセリング開始を廃止し `build_notice_bot`（`kind=aggressive_input`, `variant=security`）で統一案内文を返却。`processing_status` をクリア
- **`chat_input_validator.py`**: 絶対ブロック時も `AGGRESSIVE_INPUT_NOTICE_MESSAGE` と `variant=security` を使用（既存連携）
- **`concierge_intent.py`**: 短い攻撃的入力を structural greeting から除外

### Concierge 挨拶・雑談 LLM 強化

- **`concierge_agent.py`**
  - `format_concierge_context_block` / `format_concierge_history_block`（新規）: 同一挨拶回数・話題・直前 bot 返答をプロンプトに注入
  - `count_same_greeting_exchange_rounds` / `infer_is_first_greeting_contact`（新規）: 初回のみ窓口説明、連続挨拶では再来訪表現を抑制
  - `_GREETING_SYSTEM_PROMPT` / `_CHITCHAT_SYSTEM_PROMPT`: ミラーリング・傾聴・「市販薬」表記（OTC 禁止）・yes/no 性質確認は挨拶では答えない等の要件
  - `generate_greeting_text` / `generate_chitchat_text`: 履歴 10 件 + 文脈ブロック付き LLM 呼び出し
  - `resolve_concierge_intent`: `llm_user_text` 引数で enrich 時に生入力を使用
- **`chat_concierge_route.py`**
  - `try_concierge_duplicate_skip` と `has_recent_concierge_reply_for_user` による重複スキップを**撤廃** — 同一挨拶でも LLM が毎回応答
  - ルーティングは `sanitized_message`、LLM は `resolve_llm_user_text(user_message)` を分離
- **`session_manager.py`**: `has_recent_concierge_reply_for_user` を削除
- **`concierge_knowledge.ja.json`**: `policy_snippet` を市販薬表記・挨拶時の医療機関否定禁止に更新
- **`chat_response_service.py`**: 挨拶プール・時間帯挨拶の文言を「市販薬の相談窓口」に統一。「めE」「めE」プレフィックス対応を追加

### LLM 生ユーザー入力（resolve_llm_user_text）

- **`input_helpers.py`**: `resolve_llm_user_text(original_user_message, user_message, *fallbacks)` — 正規化前を LLM に優先渡し
- **`chat_post_pipeline.py`**: `ChatPostContext.llm_user_text` プロパティを追加
- **適用箇所**: `chat_orchestrator.py`, `chat_concierge_route.py`, `chat_ask_route.py`, `chat_recommendation_flow.py`, `rule_based_recommendation.py`（`select_symptoms_via_gpt`）, `confidence_gate.py`（低確信確認メッセージの引用）

### トリアージ履歴・パイプライン

- **`triage_history.py`**: `format_triage_history_block` で `compress_message_for_llm` を使用（Sage マーカー展開）
- **`chat_pipeline.py`**: `run_triage` の引数名を `user_message` に整理

### フロントエンド（チャット UI 同期・セキュリティ案内）

- **`static/js/main.js`**
  - `ensureSecurityNoticeTurnInDom` / `isSecurityNoticeBotMessage`（新規）: ブロック・攻撃的入力 bot を DOM に確実に描画
  - `mergeInFlightPendingUser` / `shouldBlockSessionSync`: 進行中ターンの user を session マージ結果に保持
  - `isBlockedTurnCompleteInSlice` / `findPriorBotForUserText`: ブロックターン・重複 user の完了判定を改善
  - 送信完了判定でセキュリティ案内 bot の可視性を考慮
- **`static/css/sage_terrace.css` / `main.css`**: `--sage-chat-copy-fs` / `--sage-chat-copy-lh` 変数でチャット本文・設定プレビューのフォントサイズを `--font-size-base` に連動。設定モーダルの size 別 CSS を簡素化。開発バッジを黄色に変更
- **`static/css/ui_shell_components.css`**: シェルコンポーネントのスタイル調整

### テスト

| テスト | 内容 |
|--------|------|
| `test_aggressive_input.py`（新規） | 脅迫検出・症状スラング除外・absolute block と inappropriate ルートの分離・境界案内 bot |
| `test_resolve_llm_user_text.py`（新規） | 生入力優先・フォールバック |
| `test_concierge_agent.py` | 挨拶文脈ブロック・同一挨拶回数・LLM プロンプト要件・フォールバック禁止語 |
| `test_concierge_route.py` | 同一挨拶の即時再送でも Concierge が応答（duplicate_skip 廃止） |
| `test_chat_inappropriate_route.py` | 攻撃的入力境界案内への変更 |
| `test_user_message_dedup.py` | `has_recent_concierge_reply_for_user` 関連テスト削除 |

### その他

- **`.cursor/skills/medicine-about-redesign/SKILL.md`**: Sage Terrace リデザイン skill の更新

---

## 2026年6月23日 — 医療行為依頼境界・サービス本人確認質問・店舗案内ルーティング強化

### 概要

ユーザーが**本チャットへの診察・診断依頼**をした場合に OTC 相談ツールの境界を明示するルートを追加した。あわせて **「病院ですか？」「ここはクリニック？」** など本サービスの性質を問う質問が挨拶・店舗案内に誤ルーティングされないよう修正し、**トイレ施設案内とトイレットペーパー等の商品問い合わせの区別**、**店舗 fast-path の詳細分類**、**在庫・周辺施設応答テンプレの改善**を行った。

### 医療行為依頼（診察・診断）の検出と境界応答

- **`medical_examination_request.py`（新規）**: 単独フレーズ完全一致 fast-path（`診察してください` 等）、LLM フラグ `medical_examination_request`、subcategory からの種別解決
- **`llm_triage.py`**
  - 第一段階プロンプトに `medical_examination_request` フラグを追加（症状＋依頼の複合文も Other へ）
  - 第二段階に `inappropriate_request/medical_examination` を追加（21 種類）
  - fast-path: 単独フレーズ完全一致、サービス本人確認質問、第一段階 LLM フラグ
- **`counseling_triage.py`**: `resolve_medical_examination_request_type` を不適切要求検出の先頭で呼び出し
- **`counseling_templates.py`**: `MEDICAL_EXAMINATION_BOUNDARY` 静的境界メッセージ（LLM 不使用）
- **`counseling_generator.py`**: `medical_examination` 種別で境界メッセージを返却
- **`chat_symptom_route.py`**: 医療行為依頼時は推奨フローをスキップし境界応答
- **`chat_triage_follow_ups.py`**: Other カテゴリ全体で不適切要求検出を実行（subcategory 限定を撤廃）
- **`controlled_drug_routing.py`**: `medical_examination` はカウンセリングのみ（属性収集なし）
- **`concierge_agent.py`**: chitchat 経路でも医療行為依頼を境界メッセージへ

### サービス本人確認質問（app_about）

- **`concierge_intent.py`**
  - `looks_like_user_question` / `looks_like_service_identity_question`（新規）: 「病院ですか？」は該当、「病院はどこ？」は非該当
  - `infer_structural_concierge_intent`: 質問形式・店舗用語（うんこ/用を足 等）を greeting から除外
- **`meta_triage.py`**: プロンプトに `get_service_identity_block()` を注入、`app_about` の定義を拡張、質問形式は meta LLM スキップ対象外
- **`routing_context.py` / `store_inquiry_handler.py` / `llm_triage.py`**: サービス本人確認質問を店舗ゲートから除外
- **`concierge_knowledge.ja.json`**: `service_nature` / `explicitly_not` を追加、`policy_snippet` を医療機関否定を明示する内容に更新
- **`concierge_knowledge.py`**: `get_service_identity_block()`（SSOT）を追加
- **`concierge_templates.py` / `status_diagnosis_builder.py`**: app_about カード・ステータスに性質・否定文を表示

### 店舗案内ルーティング・応答テンプレ

- **`store_inquiry_handler.py`**
  - `_is_toilet_product_query` / `_is_toilet_facility_request`（新規）: トイレットペーパー等の商品と施設案内を区別
  - `_resolve_detailed_store_response`（新規）: fast-path でも在庫・周辺施設の詳細分類を適用
  - `generate_inventory_inquiry_response`: 商品名を冒頭に簡潔表示、カテゴリ階層は「売場の目安」に
  - `generate_facilities_inquiry_response`: 施設名を見出し・本文に反映
- **`input_helpers.py`**: トイレ施設需要を症状入力から除外

### テスト

| テスト | 内容 |
|--------|------|
| `test_medical_examination_request.py` | 完全一致 fast-path、複合文は LLM 委譲、境界メッセージ |
| `test_service_identity_question.py` | 本人確認質問の検出・店舗ゲート拒否・llm_triage fast-path |
| `test_hospital_identity_question.py` | app_about ルーティング・カード内容・meta プロンプト |
| `test_store_inquiry_response_routing.py` | fast-path 詳細分類、トイレ施設 vs 商品、うんこ→店舗案内 |
| `test_meta_triage_skip.py` | 質問形式は structural greeting 対象外 |
| `test_status_diagnosis_builder.py` | 在庫ステータス・app_about 表示の更新 |

---

## 2026年6月23日 — 症状文の在庫誤検出修正・Cloud Build・GitHub/GitLab 運用ドキュメント

### 概要

「39度の熱があります」など**症状文が店舗在庫照会に誤ルーティング**される問題を修正した。あわせて **Cloud Build の bash ローカル変数エスケープ**、**条件付き import によるシャドウ解消**、**GitHub アカウント停止インシデント記録**、**GitLab 一時運用ルール**を追加した。

### 店舗在庫ルーティング（誤検出防止）

- **`store_inquiry_handler.py`**
  - `_matches_inventory_keyword`（新規）: 短い曖昧語（`あります` / `どこ` / `場所は` / `取り扱い`）は全文一致のみ。`あります` は `があります`（症状）への部分一致を除外
  - `_should_skip_inventory_for_medical_triage`（新規）: Physical/Ask 高確信トリアージで店舗在庫の明示語がなければ在庫ゲートを通さない
  - `_has_explicit_store_stock_intent`: `has_medicine_discovery_intent` 分岐を削除し、明示的な在庫語（在庫・取り寄せ・売り場等）の有無のみで判定
  - `detect_inventory_inquiry`: 上記ヘルパー経由のキーワード照合に変更
- **`data/store_inquiry_keyword_catalog.json`**: カタログから曖昧キーワード `あります` / `どこ` / `場所は` を削除（コード側で厳格照合）

### チャットパイプライン

- **`chat_post_pipeline.py`**: `memory_delete` 分岐内の `sync_messages_to_db_for_admin` 条件付き import を削除（モジュール先頭 import のシャドウを解消）

### Cloud Build / デプロイ

- **`cloudbuild.yaml`**
  - bash ローカル変数 `COMMIT_DATE` / `IMAGE` を `$$` でエスケープ（Cloud Build 置換変数との衝突防止）
  - コメントを「GitHub push」から「Git push」に汎用化

### 運用ドキュメント（GitHub 停止 / GitLab 移行）

- **`docs/ops/GITHUB_ACCOUNT_SUSPENSION_2026-06.md`（新規・拡充）**: アカウント停止インシデントの時系列・証跡・GitLab 移行手順
- **`.cursor/rules/git-remote.mdc`（新規）**: 停止期間中のプライマリリモートを GitLab に固定するエージェント向けルール
- **`.cursor/rules/onboarding-last-updated.mdc`**: プッシュ前チェックリストを GitLab 向けに更新
- **`scripts/update_issues_changelog_philosophy.sh`（新規）**: issue / CHANGELOG 思想反映用スクリプト

### テスト

| テスト | 内容 |
|--------|------|
| `test_store_inventory_scan_gate.py` | 発熱症状文が在庫照会にならないこと、`あります` と `があります` の区別 |
| `test_medical_store_priority.py` | 発熱症状で医療ルート優先・店舗意図なし |
| `test_chat_post_pipeline.py` | 条件付き import がパイプライン内に残っていないこと |

---

## 2026年6月22日 — LINE 長期記憶・管理画面パネル・パイプライン計測強化・プライバシーポリシー改定

### 概要

LINE 連携ユーザー向けの**長期記憶システム**（永続プロファイル + 相談エピソード要約 + ユーザー/管理者による削除 + アーカイブからのバックフィル）を新設し、トリアージ・カウンセリング・医薬品 Q&A・Web 引き継ぎへ記憶コンテキストを注入した。あわせて **sid キー方式のパイプライン性能計測**（ワーカースレッド対応・LLM 呼び出し集約）、**管理画面の長期記憶タブ**、**LINE Flex の Sage マーカー復元**、**オンボーディング UI 改善**、**プライバシーポリシー改定**を含む。

### LINE ユーザー長期記憶

- **`line_user_memory.py`（新規）**: LINE セッション（`line:{userId}`）および Web 引き継ぎ先への記憶オーナー解決、プロファイルマージ/永続化、エピソード要約 upsert、全件/部分削除、管理画面向け `load_line_memory_bundle`
- **`line_memory_config.py`（新規）**: `LINE_MEMORY_RECENT_TURNS`（既定 5）、`LINE_MEMORY_SUMMARY_MAX`（既定 5）
- **`line_memory_context.py`（新規）**: LLM 向け会話圧縮（`sage_reco`/`sage_status`/`sage_qa` マーカー展開）、長期記憶ブロック生成、カウンセリング用履歴（system メッセージとして記憶注入）
- **`line_memory_jobs.py`（新規）**: デーモンスレッドで非同期実行 — プロファイル永続化、エピソード要約、引き継ぎ writeback、推奨完了時の要約スケジュール
- **`line_memory_backfill.py`（新規）**: `message_archive` からプロファイル LLM 抽出 + エピソード分割（`sage_reco` 区切り）+ 要約生成

**新規エージェント**

| エージェント | 役割 |
|-------------|------|
| `ProfileMemoryAgent` | セッション属性を `line_user_profile` へマージ保存 |
| `EpisodeSummaryAgent` | 相談ログから JSON 要約（症状・推奨薬・key_facts 等）を `consultation_summaries` に追加 |
| `MemoryDeleteAgent` | 「記憶を消して」等の削除意図をルール/LLM で分類し、全件/部分/要約のみ削除 |

**統合ポイント**

- `chat_post_pipeline.py`: セキュリティゲート後にプロファイル適用 → 記憶削除ハンドラ（同期）
- `session_manager.py`: セッション永続化後にプロファイル非同期反映
- `async_attribute_extractor.py`: 属性抽出完了時に LINE プロファイルへ writeback
- `line_session.py`: `prime_line_session` でプロファイル適用; `clear_line_session_state` で LINE セッション終了時に要約生成 + プロファイル保存
- `chat_recommendation_flow.py`: 推奨完了時に `maybe_schedule_line_episode_summary`
- `line_web_handoff.py`: 引き継ぎ snapshot/Web セッションに `line_user_profile` / `consultation_summaries` を載せ、`user_attributes` をマージ

### パイプライン性能計測（`pipeline_perf.py`）

- contextvars 単一バケット → **sid キー + スレッドセーフ辞書**（`_PerfBucket`）へ刷新
- `bind_pipeline_perf` / `activate_pipeline_perf` で LINE ワーカースレッド境界を越えた計測を統合
- LLM 呼び出し・コストをバケット内に集約（`append_llm_call_to_bucket` 等）
- `llm_metrics.py` がバケット優先で read/write
- 計測ステップ追加: `post_start`, `before/after_get_session_db`, `before_triage_duplicate`, `after_triage`, `safety_gate_done`, `confidence_gate_done`, `before_orchestrator`, オーケストレーター内 `orch_*`, コンシェルジュ `concierge_*`, `meta_triage_*`
- `line_message_handler.py`: LINE 処理開始時に `bind_pipeline_perf(sid=..., channel="line")`
- `chat_handler.py`: `ensure_pipeline_perf_started(..., sid=sid)`

### 管理画面（長期記憶パネル）

**API（`main.py`）**

- セッション行に `client_ip`, `user_agent`, `handoff_from_line`, `is_line_session` / `is_line_handoff` / `is_line_related`, `line_memory_owner_sid`, `line_memory` を追加
- `meaningful_only` フィルタを `is_line_related` ベースに拡張（LINE 引き継ぎ Web セッションも表示対象）
- 新規 API:
  - `POST /api/admin/sessions/{id}/line_memory/backfill` — アーカイブから記憶生成（`force` 対応）
  - `POST /api/admin/sessions/{id}/line_memory/delete` — scope: `all` / `summaries_only` / `profile_partial`
- `_resolve_git_repo_url()` 追加（`GIT_REPO_URL` 環境変数、既定 GitHub URL）
- インデックステンプレートへ `gitRepoUrl` を注入（コミットリンク用）

**フロント（`admin_chat.html` / `admin_chat.js` / `admin_chat.css`）**

- 右パネルを **コントロール / 長期記憶** タブ化
- 長期記憶パネル: プロファイル・要約の閲覧、チェックボックス選択削除、全削除、アーカイブから生成/再生成
- ヘッダーに脳アイコン（`focusLineMemoryPanel`）
- セッション一覧に LINE 関連バッジ（`is_line_related`, `is_line_handoff`, 記憶オーナー参照）
- `client_ip` 表示

### チャットオーケストレーション / トリアージ

- `chat_triage.py`: `merge_profile_into_user_info` + `build_long_term_memory_block` をトリアージエージェントへ渡す
- `triage_agent.py` / `llm_triage.py`: `long_term_memory_block` 引数、プロンプトに長期記憶セクション注入
- `triage_cache.py` / `triage_history.py`: `memory_digest` をキャッシュキーに追加（記憶変更でキャッシュ無効化）
- `confidence_gate.py`: キャッシュ無効化ロジックを `_invalidate_triage_cache` に集約、memory_digest 対応
- カウンセリング系ルート（`chat_counseling_flow`, `chat_emotional_route`, `chat_inappropriate_route`, `chat_other_counseling_route`, `chat_category_route`, `counseling_mode_handler`）が `get_counseling_conversation_history` を使用
- `chat_post_pipeline.py` コンシェルジュ前処理でも記憶 aware 履歴を使用
- `chat_response_service.py` / `medicine_response_builder.py`: 医薬品 Q&A に長期記憶ブロック注入
- `counseling_format.py`: `system` ロールの履歴フォーマット対応

### LINE セッション / Flex メッセージ

- `resolve_session_line_context()` — 管理画面用 LINE コンテキスト解決
- `flex_messages.py`:
  - Sage コンテンツマーカー（`sage_reco`/`sage_status`/`sage_qa`）保存時、`diagnosis` からプレーンテキスト/Flex を復元
  - `_try_sage_diagnosis_status_flex` — status/qa 診断を Flex 化
  - 挨拶・カウンセリング・危機対応等でマーカー文字列が LINE に露出しないよう修正

### 法務ドキュメント

- **`docs/public/プライバシーポリシー.md`（2026-06-22 改定）**
  - 収集情報にアレルギー・併用薬、LINE 連携情報（ハッシュ化 ID、要約、長期保存、引き継ぎトークン）を追記
  - 利用目的に LINE 継続相談・Web 引き継ぎを追加
  - 第5条: 長期記憶の保持期間・削除請求方法を明記
  - 第7条: チャット内削除依頼、不具合報告フォーム URL 追加
  - 制定日・改定履歴ブロック追加
- **`docs/public/免責事項・利用規約.md`**: 制定日・改定履歴（初版）追加
- **`.cursor/rules/public-legal-docs.mdc`（新規）**: 公開規約の日付表記ルール

### フロントエンド（Sage Terrace / main.js）

- **Git コミットリンク**: `gitRepoUrl` + `gitCommitShort` からオンボーディングにコミットハッシュリンク表示
- **オンボーディング UI**: `--onb-details-max-height`（モーダル高 30%）、details 開閉時の高さ同期、フッター固定シャドウ、スクロール余白調整（`main.css` / `sage_terrace.css`）
- `handoffFinalizeTypingIndicator` — 引き継ぎ完了時のタイピング表示

### その他

- `session_lifecycle.py`: ライフサイクルラベル `line_memory_deleted`, `line_memory_backfilled`
- `src/agents/__init__.py`: 3 エージェント（ProfileMemory / EpisodeSummary / MemoryDelete）を export

### 新規ファイル（主要）

| パス | 用途 |
|------|------|
| `config/line_memory_config.py` | 環境変数設定 |
| `src/services/line_user_memory.py` | 長期記憶永続化コア |
| `src/services/line_memory_context.py` | LLM プロンプト整形 |
| `src/services/line_memory_jobs.py` | 非同期ジョブ |
| `src/services/line_memory_backfill.py` | アーカイブバックフィル |
| `src/agents/profile_memory_agent.py` | プロファイル永続化 |
| `src/agents/episode_summary_agent.py` | エピソード要約 |
| `src/agents/memory_delete_agent.py` | 記憶削除 |

### テスト

| テスト | 内容 |
|--------|------|
| `test_line_user_memory.py`（新規） | オーナー解決、マージ、永続化、削除意図、圧縮、memory_digest、upsert |
| `test_line_memory_backfill.py`（新規） | エピソード分割、バックフィル、プロファイル/要約生成 |
| `test_pipeline_perf.py`（新規） | ワーカースレッド跨ぎ計測、バケット非リセット |
| `test_line_flex_messages.py` | Sage マーカー → diagnosis メッセージ復元 |
| `test_line_session_ids.py` | `resolve_session_line_context` 3 パターン |
| `test_line_session_policy.py` | LINE クリア時プロファイル保持 + 非同期ジョブ mock |
| `test_line_session_prime.py` | 起動時プロファイル適用（DB 再読込なし） |
| `test_fastapi_contract.py` | `gitRepoUrl`、handoff セッションの meaningful_only |
| `test_triage_cache_matrix.py` | memory_digest によるキー差分 |

---

## 2026年6月22日 — 管理画面 AI 制御修正・ライセンス改定・運用ドキュメント

### 概要

管理画面で **AI 自動応答を ON にしても OFF 表示に戻る**不具合を修正した。ソースコードのライセンスを **MIT から PolyForm Noncommercial License 1.0.0** へ移行し、公開ドキュメントとアプリ内表示を同期した。LINE 長期記憶の**運用ガイド**と issue レポート形式を追加した。

### 管理画面 AI 自動応答

- **`session_manager.py`**: DB 保存失敗後に古い DB 値でメモリが上書きされていた問題を修正。ON 操作直後に OFF 表示になる不具合を解消
- **`admin_chat.js`**: 制御 API 呼び出しを統一
- **`test_session_manager_db_fallback.py`（新規）**: DB フォールバック時の AI モード保持を検証

### ライセンス（PolyForm Noncommercial 1.0.0）

- **`LICENSE`**: MIT から PolyForm Noncommercial License 1.0.0 へ移行
- **`README.md`**, **`docs/public/`** 各種公開文書, **`about_modal_html.json`**, **`main.js`**: ライセンス表記・免責文言を同期
- **`test_ask_agent.py`**: `AskAgent` の引数順序回帰テストを追加

### 運用ドキュメント

- **`docs/ops/LINE_LONG_TERM_MEMORY.md`（新規）**: LINE 長期記憶の運用ガイド（Webhook・アーキテクチャ・PII playbook から相互リンク）
- **`docs/planning/ISSUE_REPORT_FORMAT.md`（新規）**: issue レポート形式のテンプレート
- 記憶関連モジュール（`line_user_memory.py` 等）の docstring に ops doc 参照を追記

---

## 2026年6月22日 — LINE→Web 引き継ぎ Sage 統合・diagnosis 永続化分離

### 概要

LINE 会話を Web（Sage Terrace）へ引き継ぐ経路を **Diagnosis v1 + マーカー描画**と整合させた。LINE セッションでも bot メッセージを Sage diagnosis で永続化し、引き継ぎ時に legacy HTML を `sage_reco` / `sage_status` / `sage_qa` へ正規化。個別アドバイスは LINE 本番では生成せず引き継ぎ時に補完。`/resume` では Sage UI クッキーを自動設定し、フロントは引き継ぎセッションの legacy 履歴を Sage 描画へアップグレードする。あわせてモバイル向け文字サイズ段階を 1 段階縮小。

### LINE→Web 引き継ぎ

- **`line_web_handoff.py`（大幅拡張）**
  - `normalize_handoff_messages`: legacy HTML / 生 diagnosis を Sage マーカー + diagnosis v1 へ変換（推奨・エスカレーション・店舗案内・Q&A）
  - `_line_handoff_messages`: `message_archive` + 現行 `messages` を統合して全履歴を引き継ぎ
  - `redeem_handoff_token`: `detailed_diagnosis` をスナップショットに含める
  - `create_web_session_from_handoff`: 正規化済みメッセージ・`handoff_from_line`・`ui_variant: sage` を Web セッションへ保存
  - 引き継ぎ時 `_maybe_enrich_personalized_advice`: LINE でスキップした個別アドバイスを diagnosis に補完
  - フィードバック状態（`show_feedback` 等）を diagnosis へマージ
- **`main.py`**
  - `/resume/{token}`: `ui_variant=sage` クッキーを付与
  - `GET /api/sessions`: レスポンスに `handoff_from_line` を追加

### Diagnosis 永続化の分離（Web 描画 vs 保存）

- **`recommendation_client_payload.py`**
  - `use_sage_web_ui`: Web Sage 描画専用（LINE セッション ID は除外、従来どおり）
  - **`use_sage_diagnosis_storage`（新規）**: bot メッセージを Sage diagnosis + マーカーで DB 永続化するか（Web Sage **および** LINE セッション = 引き継ぎ用）
- **`sage_bot_response.py`**: `build_bot_response` を `use_sage_diagnosis_storage` 経由に変更（LINE でも Sage マーカー保存）
- **`chat_recommendation_flow.py`**
  - diagnosis 生成・保存を `use_sage_diagnosis_storage` に統一
  - 個別アドバイス: Web のみ即時生成、LINE は `personalized_advice_skipped_line` を記録し引き継ぎ時に生成
  - `emit_reco_detail`（SSE）は Web Sage のみ（LINE は Flex 配信のため除外）
  - Sage マーカー重複検出: 同一マーカーは `timestamp` 一致時のみ重複とみなす

### フロントエンド（Sage Terrace / main.js）

- **LINE 引き継ぎ描画**
  - `syncSessionHandoffContext` / `isLineHandoffSession`: `handoff_from_line` をセッション・メッセージから解決
  - `upgradeHandoffLegacyMessage` / `upgradeHandoffLegacyMessages`: 引き継ぎセッションで legacy diagnosis を Sage render へアップグレードし DOM を再マウント
  - セッション復元・`renderChatMessages` 経路でアップグレードを適用
- **文字サイズ（モバイル）**
  - 768px 以下は各段階をデスクトップより 1 段階小さく適用（`FONT_SIZE_MOBILE`）
  - ビューポート変更時に `matchMedia` で再適用
  - `main.css` / `sage_terrace.css`: メッセージバブル・設定プレビューを `--font-size-base` / `--sage-chat-copy-fs` ベースに統一、モバイル用メディアクエリ追加
  - Sage 初回挨拶: `#initial-examples` のスタイル調整

### テスト

| テスト | 内容 |
|--------|------|
| `test_line_web_handoff.py` | 正規化（推奨・status・Q&A・legacy HTML）、archive 引き継ぎ、personalized_advice 補完、Sage Flex、`/resume` クッキー |
| `test_recommendation_client_payload.py` | `use_sage_web_ui` / `use_sage_diagnosis_storage` の LINE・Web 分岐 |
| `test_sage_bot_response.py` | LINE sid で Sage マーカー応答 |
| `test_fastapi_contract.py` | `/api/sessions` の `handoff_from_line` |
| `test_recommendation_sse_order.py` | LINE は personalized_advice スキップ |
| `test_chat_orchestrator.py` 等 | モックを `use_sage_diagnosis_storage` に更新 |

---

## 2026年6月21日 — Diagnosis v1 / Sage UI Big Bang 移行・開発プレビュー 16 パターン

### 概要

Web チャットの応答を **HTML 一括描画から Diagnosis v1 構造化ペイロード + マーカー描画**へ全面移行した（Big Bang）。`sage_reco` / `sage_status` / `sage_qa` の 3 系統で推奨・ステータス・Q&A を統一し、SSE 順序（cards → advice → done → reco_detail）と i18n・TTS・管理画面表示を diagnosis 経由に接続した。開発用 UI プレビューは **7 件から 16 件**に拡張（`mrcdev00000000000001`〜`16`）。店舗案内キーワードカタログ、LINE リッチメニュー、曖昧心臓症状・規制薬物ルーティング等のバックエンド強化を含む。

### Diagnosis v1 スキーマ・ビルダー

- **`src/schemas/recommendation_diagnosis_v1.py` / `status_diagnosis_v1.py`（新規）**: Pydantic 正本。`render`・`usage_sections`・`error`・`admin`（ユーザー API から strip）等
- **`recommendation_diagnosis_builder.py` / `status_diagnosis_builder.py`（新規）**: 推奨・緊急・店舗・Q&A・カウンセリング・診断名通知等の diagnosis 生成。マーカー `sage_reco` / `sage_status` / `sage_qa`
- **`diagnosis_i18n.py`（新規）**: diagnosis フィールドの多言語バンドル
- **`sage_bot_response.py`（新規）**: Sage Web と legacy HTML の二重書き。`use_sage_web_ui` でマーカー + diagnosis を選択
- **`recommendation_client_payload.py`**: Sage Web 向け diagnosis パス（LINE 除外）
- **`reco_error_messages.py`（新規）**: 推奨エラー種別のユーザー向け文言
- **`docs/ui/DIAGNOSIS_V1.md`（新規）**: 契約・SSE 順序・legacy 読取専用方針

### チャット経路・オーケストレーション

- **`chat_recommendation_flow.py`**: 推奨フローを diagnosis v1 + SSE 中心に再構成（大幅リファクタ）
- **`chat_post_pipeline.py` / `chat_orchestrator.py`**: diagnosis 応答・曖昧心臓・ConfidenceGate 連携
- **`chat_ambiguous_heart_route.py`（新規）**: 「心が痛い」身体 vs 心理の確認カード
- **`controlled_drug_routing.py` / `inappropriate_drug_block_route.py`（新規）**: 規制薬物・不適切要求の即時ブロックと OTC 不眠文脈除外
- **`chat_symptom_route.py` / `chat_question_route.py` / `chat_counseling_flow.py` 等**: 各ルートを `build_bot_response` 経由の Sage 応答に統一
- **`chat_diagnosis_handler.py`**: diagnosis 通知・属性更新の status ビルダー接続
- **`confidence_policy.py`（新規）** + **`confidence_gate.py`**: ポリシー分離とゲート判定の整理

### 店舗案内

- **`data/store_inquiry_keyword_catalog.json`（新規）** + **`store_inquiry_keyword_catalog.py`（新規）**: 施設・在庫・遺失物等のキーワードカタログ
- **`store_inquiry_handler.py`**: 分類・再試行・施設文脈・テキストバリアント対応の大規模強化
- **`chat_store_inquiry.py`**: diagnosis ベース店舗 status 連携

### Concierge・トリアージ・入力

- **`concierge_agent.py` / `concierge_orchestrator.py` / `concierge_intent.py`**: Sage status 応答・意図解決の拡張
- **`llm_triage.py` / `meta_triage.py` / `triage_agent.py`**: 履歴・第二段階・緊急キーワード調整
- **`input_helpers.py` / `structured_logger.py`**: 正規化・ログフィールド拡充
- **`routing_keyword_policy.py`**: キーワード監査の更新

### LINE

- **`line_rich_menu.py` / `line_quick_actions.py` / `line_menu_actions.py`（新規）**: 3 分割リッチメニュー（Web 詳細・薬剤師相談・使い方）と postback 処理
- **`scripts/register_line_rich_menu.py`（新規）**: Messaging API 登録 CLI
- **`static/line/rich-menu-pattern-*.png`（新規）**: 4 種ビジュアルパターン
- **`flex_messages.py` / `line_i18n.py` / `line_message_handler.py`**: Flex・i18n・配信の diagnosis 対応

### フロントエンド（Sage Terrace）

- **`static/js/ui/status_renderer.js` / `tts_builder.js`（新規）**: status / Q&A 描画・音声読み上げを diagnosis から生成
- **`recommendation_renderer.js` / `main.js` / `processing_status.js`**: カルーセル・SSE 逐次描画・進捗 UI の diagnosis 対応（大規模更新）
- **`sage_terrace.css` / `ui_shell_components.css` / `shell.css`**: Sage カード・推奨・status レイアウト
- **`admin_chat.js` / `admin_chat.css`**: 管理画面の Sage バブル・スコアパネル
- **`ui_strings.js`**: diagnosis 関連 i18n 文言
- **`config/ui_config.py`**: デフォルト Sage、`LEGACY_UI_FALLBACK` / `?ui=legacy` で legacy 固定
- **`legacy/` / `static/legacy/`**: 退避 README と legacy HTML 参照

### 開発用 UI プレビュー（16 パターン）

**`APP_ENV=development` のみ。** トリガー語を **完全一致** で送信。詳細: [`docs/ops/DEV_ERROR_UI_PREVIEW.md`](docs/ops/DEV_ERROR_UI_PREVIEW.md)

| # | トリガー | 種類 | Sage 表示 |
|---|----------|------|-----------|
| 01 | `mrcdev00000000000001` | クライアント・エラー | 赤カード（`showErrorMessage`） |
| 02 | `mrcdev00000000000002` | クライアント・警告 | セキュリティ警告 |
| 03 | `mrcdev00000000000003` | HTTP 500 | 通信エラー系 |
| 04 | `mrcdev00000000000004` | システムエラー | `sage_status` error |
| 05 | `mrcdev00000000000005` | 候補なし | `sage_status` caution |
| 06 | `mrcdev00000000000006` | 診断名通知 | `sage_status` notice |
| 07 | `mrcdev00000000000007` | エスカレーション | `sage_status` critical |
| 08 | `mrcdev00000000000008` | 挨拶 | `sage_status` notice（FB なし） |
| 09 | `mrcdev00000000000009` | 店舗案内 | `sage_status` notice + FB |
| 10 | `mrcdev00000000000010` | 医薬品 Q&A | `sage_qa` |
| 11 | `mrcdev00000000000011` | 推奨成功 | `sage_reco` + カルーセル |
| 12 | `mrcdev00000000000012` | 推奨 0 件 | `sage_reco` + error |
| 13 | `mrcdev00000000000013` | 緊急 | `sage_status` critical |
| 14 | `mrcdev00000000000014` | 危機支援 | `sage_status` security |
| 15 | `mrcdev00000000000015` | カウンセリング | `sage_status` notice |
| 16 | `mrcdev00000000000016` | 医薬品種類不明 | `sage_status` caution |

04〜16 は diagnosis v1 + マーカーで描画。環境変数 `DEV_ERROR_TRIGGER_*`（01〜07）・`DEV_SAGE_TRIGGER_*`（08〜16）で上書き可能。  
実装: `chat_dev_triggers.py` / テスト: `tests/chat/test_chat_dev_triggers.py`

### API・セッション・ログ

- **`main.py`**: セッション diagnosis の admin フィールド除去、UI バリアント注入
- **`sse_events.py` / `sse_emit.py`**: reco_detail 等 SSE イベント拡張
- **`recommendation_logger.py`**: diagnosis_snapshot + plain summary ログ
- **`html_formatter.py`**: dual-write / legacy 参照用に残存

### ドキュメント・QA

- **`docs/ops/MANUAL_QA_SAGE_UI.md`（新規）**: Big Bang 後の手動 QA チェックリスト
- **`docs/ops/DEV_ERROR_UI_PREVIEW.md`**: 16 パターン一覧に更新

### 新規ファイル（主要）

| パス | 内容 |
|------|------|
| `src/schemas/` | Diagnosis v1 Pydantic 正本 |
| `src/services/recommendation_diagnosis_builder.py` | 推奨 diagnosis ビルダー |
| `src/services/status_diagnosis_builder.py` | ステータス diagnosis ビルダー |
| `src/services/sage_bot_response.py` | Sage / legacy 応答ヘルパー |
| `static/js/ui/status_renderer.js` | status / Q&A 描画 |
| `static/js/ui/tts_builder.js` | TTS テキスト生成 |
| `src/handlers/line/line_rich_menu.py` | LINE リッチメニュー |
| `data/store_inquiry_keyword_catalog.json` | 店舗案内キーワード |

### テスト（新規・更新）

| テスト | 内容 |
|--------|------|
| `test_recommendation_diagnosis_builder.py` / `test_status_diagnosis_builder.py` | diagnosis ビルダー |
| `test_diagnosis_i18n.py` / `test_sage_bot_response.py` | i18n・応答ヘルパー |
| `test_chat_dev_triggers.py` / `test_chat_stream_api.py` | 開発プレビュー 01〜16 |
| `test_ambiguous_heart_route.py` / `test_unrecognized_symptom_route.py` | 曖昧心臓・症状不明 |
| `test_controlled_drug_routing.py` / `test_inappropriate_drug_block_route.py` | 規制薬物ブロック |
| `test_store_inquiry_*.py` / `test_store_routing_matrix.py` | 店舗案内マトリクス |
| `test_line_rich_menu.py` / `test_sessions_diagnosis_sanitize.py` | LINE・API サニタイズ |
| `test_chat_orchestrator.py` | オーケストレーター回帰（大幅拡充） |
| `tests/schemas/` / `tests/services/counseling/` | スキーマ・カウンセリング |

---

## 2026年6月20日 — Sage 表示設定・カラーテーマ・セーフティレール応答レイアウト・オンボーディング改善

### 概要

Sage Terrace UI の **表示設定モーダル**をカード型 UI に再設計し、**10種のカラーテーマ**（薬局グリーン・オーシャン・ダーク等）を選べるようにした。あわせて **セーフティレール**を幅に応じたチップ省略表示（`+N`）へ変更し、**オンボーディング**に専用言語セレクターとデプロイ版コミットハッシュ表示を追加した。夏・秋の季節装飾画像を登録し、暦年全日の装飾ギャップ検出ユーティリティを追加した。

### Sage 表示設定・カラーテーマ

- **`color_presets.js`**（新規）: 10テーマの CSS 変数バンドル、`localStorage` 永続化、設定画面 HTML 生成
  - Sage（標準）・薬局グリーン（本番）・オーシャントラスト・ミントフレッシュ・温かみケア・ラベンダーケア・サンドナチュラル・クラシックグリーン・ミニマル・ダーク
- **`main.js`**: `buildSettingsPageHtml` / `bindSettingsPageEvents` — 文字サイズ・音声速度・カラー・季節装飾・パーティクルを統合。レガシー HTML 埋め込みを廃止
- **文字サイズ**: `data-font-size` 属性・`--ui-font-size`・`html` の `fontSize` を連動。プレビュー付きセグメントボタン（`is-active` / `aria-pressed`）
- **音声速度**: セグメントボタンで `aria-pressed` を同期
- **`ui_strings.js`**: 設定画面・カラーテーマ・セーフティレール短縮ラベル・ヘッダーフェーズ文言を ja / en / ko / zh に追加
- **`sage_terrace.css` / `main.css`**: 設定カード・カラーグリッド・Info モーダル一覧の固定配色、テーマ別アクセント色、ダーク／ミニマル向け調整

### セーフティレール応答レイアウト

- **`safety_rail.js`**: `ResizeObserver` + チップ幅計測で表示可能数を算出。はみ出しは `+N` チップ（`aria-label` 付き）
- 640px 未満で短縮ラベル（年齢未・服用薬未 等）、横スクロールを廃止
- フォントサイズ変更（`data-font-size`）時も再フロー
- **`shell.css` / `ui_shell_components.css` / `sage_terrace.css`**: compact レールの flex 配置・チップ最小フォント（`max(9px, …)`）・オーバーフローチップ用スタイル

### オンボーディング・言語切替

- **オンボーディング専用言語セレクター**（`#onboarding-language-selector`）をモーダル内に配置。チャット側セレクターとのハイライト競合を解消
- **`toggleOnboardingLanguageMenu`**: 複数 `.language-selector` 対応の開閉ロジック
- **コミットハッシュ表示**: `main.py` の `gitCommitShort` を `#app-runtime-config` 経由でオンボーディング最終更新日の横に表示
- **レイアウト圧縮**: モーダル最大幅 380px、タイトル・余白縮小、オーバーレイ `inset: 0`、ハイライト時の `scale` 変形を廃止
- **teardown 改善**: オンボーディング終了時に対象セレクタのみインラインスタイル解除、`clip-path` 等のオーバーレイスタイルをリセット

### ヘッダーフェーズ・シェル

- **`sage_shell.js`**: `refreshHeaderPhase` — 症状キャッシュ（`__lastHeaderSymptoms`）からフェーズ文言を復元。言語切替時にも再描画
- **`safety_rail.js`**: `updateHeaderPhase` を `ui_strings` の `headerPhaseSymptoms` に国際化

### 季節装飾（夏・秋）

- **`season_manager.py`**: `summer` / `autumn` に左右装飾 PNG を登録、`IMAGE_ALT_MAPPING` を拡充
- **`iter_configured_decoration_static_paths`**: 設定済み装飾パスの列挙
- **`find_calendar_decoration_gaps`**: 暦年で装飾が空の日を検出

### バックエンド・テンプレート

- **`main.py`**: `_resolve_git_commit_short` — 環境変数（`GIT_COMMIT` 等）→ `git rev-parse` の順で 7 桁コミットを解決し `runtime_client_config` に注入
- **`templates/index.html`**: `color_presets.js` 読み込み、キャッシュバスター更新、設定一覧の説明文を「文字サイズ・カラー・演出」に変更

### 新規ファイル

| パス | 内容 |
|------|------|
| `static/js/ui/color_presets.js` | Sage カラーテーマプリセット・設定 UI |

### 変更ファイル（主要）

| 領域 | ファイル |
|------|----------|
| 表示設定 | `static/js/main.js`, `static/js/ui/ui_strings.js`, `static/css/main.css`, `static/css/sage_terrace.css` |
| セーフティレール | `static/js/ui/safety_rail.js`, `UI/shared/shell.css`, `static/css/ui_shell_components.css` |
| オンボーディング | `templates/index.html`, `static/css/main.css` |
| シェル | `static/js/sage_shell.js` |
| 季節 | `src/core/season_manager.py` |
| API | `main.py` |
| テスト | `tests/api/test_fastapi_contract.py`, `tests/services/test_season_manager_particles.py` |

### テスト

- `test_get_root_injects_app_version_and_empty_base_path`: `gitCommitShort` の HTML 注入を検証
- `test_summer_and_autumn_decoration_images` / `test_all_configured_decoration_pngs_exist_on_disk` / `test_every_calendar_day_has_decoration_images`: 季節装飾の網羅性

---

## 2026年6月18日 — Sage 推奨カード強化・チャット描画安定化・フィードバックトレース

### 概要

Sage Terrace UI の **推奨カルーセル（Carousel Pro）** をレガシー HTML と同等の情報量まで拡張した。スコア内訳（副作用・相互作用リスク・未入力ペナルティ）、成分重複注意、DB 由来の成分・用法・注意書き、推奨理由リストをカード内に統合する。

あわせて **Web チャットのメッセージ描画・タイピング表示の競合**を修正し、管理画面の会話時系列表示と **フィードバック非同期保存＋トレースメタデータ**（処理遅延通知・LINE 評価）を追加した。

### Sage Terrace UI（推奨カード・カルーセル）

- **スコア表示強化**（`medicine_mapper.js` / `medicine_card.js` / `ui_strings.js`）:
  - 内訳に副作用リスク・相互作用リスクを追加（低いほど安全）
  - `completeness_penalty` による未入力ペナルティチップ（年齢未入力時など）
  - スコアリング tier（high / medium / low）でリング色分け
  - 年齢暫定評価ラベル・内訳ヒント文言（ja / en / ko / zh）
- **カード詳細**:
  - DB フィールド（成分・用法用量・使用上の注意）を Pro カードに表示
  - `reason` 文字列をアイコン付きリスト（✓ / ! / ·）へ整形
  - 折りたたみ時は内訳・DB 欄・理由リストを非表示
- **成分重複・服用注意**（`recommendation_renderer.js`）:
  - レガシー HTML から重複成分警告をパースし `ui-overlap-card`（danger / warn）で表示
  - レガシー折りたたみセクション（用法・禁忌等）をカード別・共通ブロックへマージ
- **スタイル**: `UI/shared/shell.css` / `static/css/ui_shell_components.css` / `sage_terrace.css` に overlap・reason・score-penalty 用クラスを追加
- **Sage ツールバー**: ゴミ箱ボタンを「履歴クリア」→「新セッション」に変更（`sage_shell.js` → `startNewSession` 委譲）
- **情報モーダル**: `display: flex` で中央配置を修正（`main.js`）

### Web チャット描画の安定化（`main.js`）

- **メッセージマージ**: 空 user バブル除去、`sessionStorage.lastUserMessage` による本文補完、サーバー確定済み user との重複排除（`sanitizeSessionMessages`）
- **DOM 照合**: 直近ターンの user / bot ノード判定を uuid なしケースでもテキスト一致で追跡（`getBotNodesAfterLastUserDom` 等）
- **タイピングインジケータ**: `scheduleTypingIndicatorRemoval` で bot 描画完了＋スクロール後に除去（先消しによる空白を防止）
- **SSE done 即時描画**: `renderDonePayloadImmediately` で `bot_message` を先行レンダリング
- **POST エラー抑制**: `awaitingPostResponse` 中は `shouldSuppressPostFetchError` が誤判定しないよう修正
- **処理遅延通知**: `client_context`（処理ステップ・経過秒数等）を `/api/slow_request_notify` へ送信

### バックエンド（SSE・推奨・スコアリング）

- **`processing_status.py`**: `status_sse_payload_for_session` — SSE status イベントの共通ペイロード整形（detail_code / flow_hint / slow_hint 等）
- **`chat_stream.py`**: リプレイ時は validate ステップを再送しない。初回接続時のみ enriched status を event_id=1 で送出
- **`sse_emit.py`**: アクティブ sink が無い場合 `get_active_session_sink` へフォールバック
- **`candidate_scoring.py`**: `_extract_usage_precautions` — 用法用量列から `＜` 以降または注意行を行数制限なく抽出
- **`chat_recommendation_flow.py`**: bot 応答に `timestamp` を付与

### フィードバックトレース・処理遅延の永続化

- **`feedback_trace.py`**（新規）: `build_feedback_trace` / `submit_feedback_async` — ThreadPoolExecutor で非同期保存。成功・失敗を `log/feedback_trace.jsonl` に記録（ユーザー操作はブロックしない）
- **`slow_request_notify.py`**: 遅延通知時に `report_type=slow_request` で DB へ非同期保存。処理状況・`client_context`・ユーザー名をメタデータに含める
- **`line_feedback.py`**: 同期 `submit_feedback_record` → 非同期 `submit_feedback_async` + トレースメタデータ。即時サンクス返信（重複時の 429 待ちを廃止）
- **`database.py`**: `feedback_reports.metadata` JSONB 列をマイグレーション追加
- **`feedback_submit.py` / `feedback_store.py`**: `metadata` 引数を通過

### 管理画面（`admin_chat.js` / `admin_chat.css`）

- **会話表示**: `normalizeAdminMessagesForDisplay` — timestamp 補間による時系列ソート（サーバー側 `sort_messages_chronologically` と同等ロジック）
- **user メッセージ**: `content` / `message` / `text` / `user_message` から本文抽出。空の場合は「(メッセージ本文なし)」
- **不具合報告一覧**: `slow_request`・`processing_timeout`・ポジティブ評価を表示対象に追加。`metadata` トレースをモーダルで閲覧可能
- **LINE セッション**: `fetchAdminSessionMessages` で `/api/main_session` を個別取得

### セッション・薬剤師要請

- **`session_lifecycle.py`**: `sort_messages_chronologically`、アーカイブマージ時の richer メッセージ優先（`_prefer_richer_message`）
- **`session_manager.py`**: LINE セッション統合で DB（古い）→ メモリ（新しい）の順でアーカイブへマージ
- **`clear_admin_request_state`**: 履歴クリア時に `admin_request` フラグ・手動返信キューを解除（`main.py` `/clear`）
- **`api_request_admin` / 手動返信**: メッセージに `timestamp`・`uuid` を付与

### 新規ファイル

| パス | 内容 |
|------|------|
| `src/services/feedback_trace.py` | フィードバック非同期保存・JSONL トレース |
| `tests/services/test_feedback_trace.py` | トレース構築・非同期保存テスト |

### 変更ファイル（主要）

| パス | 内容 |
|------|------|
| `static/js/main.js` | メッセージマージ・タイピング・done 即時描画・遅延通知 context |
| `static/js/ui/*.js` | カード・マッパー・レンダラ・文言の Sage 推奨 UI 拡張 |
| `static/js/admin_chat.js` | 時系列ソート・フィードバック一覧拡張 |
| `static/js/sage_shell.js` | 新セッションボタン委譲 |
| `UI/shared/shell.css` / `shell.js` | プロトタイプ用スコア・overlap スタイル |
| `src/services/session_lifecycle.py` | 時系列ソート・リッチマージ |
| `src/services/slow_request_notify.py` | DB 永続化・処理状況付き通知 |
| `src/handlers/line/line_feedback.py` | 非同期フィードバック |
| `templates/index.html` | キャッシュバスター・Sage ボタンラベル |

### テスト

- `tests/api/test_fastapi_contract.py` — `/clear` で admin_request・手動返信キュー解除
- `tests/line/test_line_feedback.py` — 非同期 submit へ更新
- `tests/line/test_line_profile_lifecycle.py` — メッセージ時系列ソート
- `tests/services/test_slow_request_notify.py` — メタデータ付き非同期保存
- `tests/services/test_feedback_trace.py` — トレース・非同期保存

### オンボーディング（追記）

- **開発中チェックリスト**: 「現在開発中の主な内容」で実装済み 5 項目に完了チェックを追加（UI・導線の最適化、カルーセル型 UI、LINE 連携、画像、セキュリティ）。日・英・韓・中の production / development スライドと最終更新日（2026-06-18）を同期。

---

## 2026年6月17日 — Sage Terrace UI 段階移行と LINE→Web 引き継ぎ

### 概要

6月16日のロールバック後、**本番チャットへ 54 Sage Terrace UI を段階的に導入**する方針で再実装した。レガシー UI はデフォルトのまま維持し、`?ui=sage`・Cookie・環境変数 `UI_SAGE_TERRACE_ENABLED` で Sage バリアントを切り替える。**既存 DOM ID・`main.js` フックは温存**し、Sage 時のみ追加ヘッダー・安全レール・Carousel Pro 推奨描画を有効化する。

あわせて **LINE 推奨完了後に Web へ会話を引き継ぐ**ワンタイムトークン（30分・1回限り）と `/resume/{token}` ルートを追加した。

### UI バリアント（段階公開）

| 段階 | 内容 |
|------|------|
| 1 | 開発環境で `UI_SAGE_TERRACE_ENABLED=true` |
| 2 | 本番で `?ui=sage` ベータ（Cookie 7日保持） |
| 3 | 本番で `UI_SAGE_TERRACE_ENABLED=true` |
| 4 | legacy コードパス削除（将来） |

**解決優先順位**: クエリ `?ui=sage\|legacy`（別名 `54` / `sage-terrace` / `classic` 可）→ Cookie `ui_variant` → 環境変数 → `legacy`。本番で Flag OFF でもクエリ・Cookie による QA 上書きを許可。

### Sage Terrace UI（Web）

- **デュアルシェル**: `templates/index.html` に `data-ui-variant` を付与。Sage 時は Toolbar ヘッダー（`ui-header--toolbar`）、コンパクト入力バー（`ui-input-bar`）、`#safetyRailMount` を追加し、レガシー `.chat-header` は CSS で非表示（DOM・JS フックは維持）。
- **スタイル**: `static/css/ui_shell_components.css`（`UI/shared/shell.css` 由来）＋ `static/css/sage_terrace.css`（Sage テーマ変数・オーバーライド）。`scrollbar.css` 経由でスクロールバー統一。
- **クライアント描画モジュール**（`static/js/ui/`）:
  - `ui_strings.js` — Sage 向け UI 文言
  - `medicine_mapper.js` — 推奨 JSON の正規化
  - `medicine_card.js` — 医薬品カード HTML
  - `carousel.js` — Carousel Pro
  - `recommendation_renderer.js` — `diagnosis` / SSE から推奨ブロック描画
  - `safety_rail.js` — コンパクト安全レール
- **`sage_shell.js`**: Toolbar ボタンをレガシー操作へ委譲、安全レール初期化、Sage 専用 body クラス付与。
- **`main.js`**: `isSageUi()` 分岐で推奨メッセージの Carousel 昇格、SSE `cards` イベント連携、設定モーダルに季節装飾・パーティクル ON/OFF、オンボーディングの Sage 向けハイライト対象変更。

### バックエンド（推奨・SSE）

- **`recommendation_client_payload.py`**: `is_sage_web_ui()` / `enrich_recommended_medicines()` — 症状・スコア内訳・画像 URL を SSE / `diagnosis` 用に補完。
- **`chat_recommendation_flow.py`**: Sage Web 時はサーバー側 HTML カード生成をスキップし、`data-sage-client-render="1"` プレースホルダのみ出力（二重表示防止）。
- **`sse_emit.py`**: `emit_cards` に `image_url`・`symptoms`・`score_breakdown` を追加。

### LINE → Web 引き継ぎ

- **`line_web_handoff.py`**: メモリ内ワンタイムトークン（TTL 30分・1回限り）。LINE セッションの messages / user_attributes / 言語を Web 新規セッションへコピー（`handoff_from_line` 記録）。
- **`GET /resume/{token}`**: トークン検証 → 新 `sid` Cookie 設定 → `/` へリダイレクト。失効時は 410 HTML。
- **`flex_messages.py`**: LINE 推奨成功時、3通目に「ブラウザで続ける」Flex（URI ボタン）を付与。
- **`line_i18n.py`**: `web_continue_*` 文言を ja / en / ko / zh に追加。

### その他

- **`main.py`**: インデックス描画で `ui_variant` 解決・Cookie 設定、`runtime_client_config_json` に `uiVariant` を含める。SSE 用 `_prime_safe_session_for_chat` にも `ui_variant` を反映。
- **`api_sessions_post`**: セッション POST 時に既存 `messages` を上書きしないよう修正（空配列での消去を防止）。

### 新規ファイル

| パス | 内容 |
|------|------|
| `config/ui_config.py` | UI バリアント解決・Cookie 名・段階公開コメント |
| `src/services/recommendation_client_payload.py` | Sage 判定・推奨 dict 補完 |
| `src/handlers/line/line_web_handoff.py` | LINE→Web ワンタイムトークン |
| `static/css/ui_shell_components.css` | 共有シェルコンポーネント CSS |
| `static/css/sage_terrace.css` | Sage Terrace テーマ・本番オーバーライド |
| `static/js/sage_shell.js` | Sage Toolbar・安全レール起動 |
| `static/js/ui/*.js` | Carousel・カード・安全レール等（6 ファイル） |
| `tests/config/test_ui_config.py` | バリアント解決テスト |
| `tests/services/test_recommendation_client_payload.py` | ペイロード補完テスト |
| `tests/line/test_line_web_handoff.py` | 引き継ぎ・Flex・`/resume` テスト |

### 変更ファイル

| パス | 内容 |
|------|------|
| `main.py` | UI バリアント・`/resume/{token}`・セッション POST 修正 |
| `templates/index.html` | Sage / legacy デュアルマークアップ・条件付き CSS/JS |
| `static/js/main.js` | Sage 分岐・推奨描画・設定 UI |
| `static/css/main.css` | Sage 時レガシーヘッダー非表示等 |
| `src/handlers/chat/chat_recommendation_flow.py` | Sage クライアント描画プレースホルダ |
| `src/handlers/chat_stream.py` | ストリーム開始時 `ui_variant` 注入 |
| `src/services/sse_emit.py` | cards ペイロード拡張 |
| `src/handlers/line/flex_messages.py` | Web 続行 Flex・3通目追加 |
| `src/handlers/line/line_i18n.py` | 引き継ぎ文言 i18n |
| `tests/api/test_fastapi_contract.py` | `?ui=sage` / `?ui=legacy` 契約テスト |

### 利用方法（開発・QA）

```text
# Sage UI を試す（本番 Flag OFF でも可）
https://<host>/?ui=sage

# レガシーに戻す
https://<host>/?ui=legacy

# 環境変数で全体 ON
UI_SAGE_TERRACE_ENABLED=true
```

### 6月16日試行との違い

- **全置換ではなくデュアルパス**: レガシーがデフォルト。Sage はフラグ／クエリで明示的に有効化。
- **サーバー HTML カードとクライアント Carousel の分離**: Sage 時はプレースホルダ＋クライアント描画で二重表示を回避。
- **Toolbar はレガシー操作への薄いラッパー**: `clearChat` 等の既存関数を再利用。

---

## 2026年6月16日 — 本番チャット 54 Sage Terrace UI 移行の試行とロールバック

### 概要

本番チャット（`templates/index.html` / `static/js/main.js` 等）へ **54 Sage Terrace** プロトタイプの UI（Toolbar ヘッダー・コンパクト安全レール・Carousel Pro 推奨・テーマ設定など）を移行する計画に沿って実装を進めたが、ヘッダー表示崩れ・入力バー非応答・送信ボタン押下時のレイアウト破損などが発生した。**本番反映は見送り、当該セッション内の変更はすべてロールバック**し、`origin/main` 時点の本番 UI に戻した。

> **現在の本番チャット UI は移行前の状態のまま。** 以下は試行時に行った作業の記録である。

### 計画の要点（ユーザー確認済み）

| 項目 | 内容 |
|------|------|
| 範囲 | チャット画面全体（ヘッダー・安全レール・メッセージ・推奨・入力・モーダル） |
| リセット | 「会話をリセット」1 ボタン + 確認ダイアログ |
| テーマ | CSS 変数ベース。Sage Terrace / Classic Green のプリセット切替（設定画面） |
| 装飾 | 季節画像・パーティクルは設定 ON/OFF、**初期 OFF** |
| 推奨カード | `message.diagnosis` JSON からクライアントで Carousel Pro 描画 |
| 方針 | `UIShell.mount()` 全置換はせず、既存 ID・JS フックを維持 |

### 試行時に追加したファイル（ロールバックで削除済み）

| パス | 内容 |
|------|------|
| `static/css/chat-shell.css` | 54 由来の Toolbar・安全レール・吹き出し・Carousel・入力バー等のスタイル |
| `static/js/display_preferences.js` | テーマプリセット・季節装飾・パーティクルの `localStorage` 管理 |
| `static/js/safety_rail.js` | コンパクト安全レール（`#sessionSafetyRail`）の描画 |
| `static/js/recommendation_cards.js` | `diagnosis` JSON から Carousel Pro HTML を生成 |

### 試行時に変更したファイル（ロールバックで復元済み）

| パス | 内容 |
|------|------|
| `templates/index.html` | `ui-header--toolbar` ヘッダー、コンパクト入力バー、新 CSS/JS 読み込み、挨拶吹き出し |
| `static/js/main.js` | リセット統合、Carousel 描画、設定 UI 拡張、ストリーミング昇格、送信ボタン状態管理 |
| `static/css/main.css` | レガシー `.chat-header` との競合整理 |
| `static/css/scrollbar.css` | カルーセル・安全レール・モーダル body への `app-scrollbar` 追加 |
| `static/js/easter-eggs.js` | パーティクル表示を `displayPrefs.particleEffects` と連動 |
| `src/handlers/chat/chat_recommendation_flow.py` | 推奨 medicine HTML の二重表示防止（プレースホルダ化） |
| `UI/README.md`, `UI/index.html`, `UI/shared/shell.css`, `UI/shared/shell.js` | プロトタイプ側の調整（本番移行作業に伴う変更） |

### 試行時に追加した UI プロトタイプ（ロールバックで削除済み）

`UI/patterns/39-symptom-wizard.html` ～ `56-noir-apothecary.html`（計 18 ファイル）

### 発生した不具合と対処（試行中）

1. **`chat-shell.css` の構文エラー**  
   `.ui-header--session` / `.ui-input-bar` / `.ui-textarea:focus` の閉じ括弧 `}` 欠落により、後続スタイルが無効化。ヘッダー 2 行化・入力バー非応答の一因となった。

2. **ヘッダー（`ui-header--toolbar`）のレイアウト崩れ**  
   `main.css` のレガシーグリッド（`header-lang` 等）と新エリア名（`lang` / `brand` / `toolbar`）の不一致。`grid-area` の `!important` 上書きで暫定対応。

3. **入力バー（`ui-input-bar--compact`）が反応しない**  
   上記 CSS 破損に加え、装飾レイヤーとの `z-index` / `pointer-events` の調整が必要だった。

4. **送信ボタン（`.ui-send`）押下時のレイアウト破損**  
   マイクと共通の `width: 38px` 指定と、送信中の `innerHTML = '⏳ 処理中...'` によりテキストがはみ出し。`setSubmitButtonBusy()` と送信ボタン専用 CSS で暫定対応。

### ロールバック

- `git restore` により変更済み追跡ファイルを `HEAD`（`7bd2e44`）に復元。
- 上記新規ファイル・`UI/patterns/39`～`56` を削除。
- **コミット・プッシュ対象のコード変更はなし**（本エントリと `CHANGELOG.md` のみをリポジトリに反映）。

### 今後の再着手時の注意

- `chat-shell.css` 抽出時は **括弧の整合**を必ず検証すること（`node` 等で brace balance チェック推奨）。
- 送信ボタンはマイクと **サイズ指定を分離**し、送信中ラベルは短い文言 + CSS クラスで表現すること。
- 本番移行は **フェーズごとにブラウザ QA** 後にマージする運用が安全。

---

## 2026年6月15日 — LINE 二重返信防止・Reply API 優先配信

### 概要

- **Webhook 去重のワーカー間共有**: `line_dedup.py` をファイルマーカー（`O_EXCL`）方式に拡張。Gunicorn 複数ワーカー・LINE Webhook リトライ時の同一イベント二重処理を防止。去重キーは `webhookEventId` → `message.id` → `replyToken` の優先順。
- **統一配信ロジック（Reply 優先）**: `line_delivery.py` を新設。イベント `timestamp` から 22 秒以内なら Reply API を先に試行し、失効時のみ Push へフォールバック。同一処理内の二重配信は `LineDeliveryContext.delivered` で抑止。
- **段階配信の二重 Push 修正**: `deliver_final_line_messages` で Reply 失敗後の Push 成功時に full bundle を再送していたバグを修正。フォールバック時は `reply_token=None` + `force_delivery=True` で 1 回のみ配信。
- **即時応答の Reply 優先化**: follow / グループ非対応 / 非テキスト応答も `deliver_line_messages` 経由に統一（Reply 失敗時 Push フォールバック）。
- **イベント timestamp の配信コンテキスト連携**: `_process_text_message` が Webhook イベントの `timestamp` を `LineDeliveryContext` に渡し、reply token 有効判定に利用。

### 新規ファイル

| パス | 内容 |
|------|------|
| `src/handlers/line/line_delivery.py` | Reply 優先・二重送信防止の統一配信 |
| `tests/line/test_line_dedup.py` | 去重キー抽出・ファイル去重 |
| `tests/line/test_line_delivery.py` | Reply 優先・Push フォールバック・重複抑止 |

### 変更ファイル

| パス | 内容 |
|------|------|
| `src/handlers/line/line_dedup.py` | ワーカー間ファイル去重・`extract_webhook_dedup_key` |
| `src/handlers/line/line_message_handler.py` | 統一配信・timestamp 連携・即時応答 Reply 優先 |
| `src/handlers/line/line_progressive_delivery.py` | 二重 Push 修正・`delivered` / `event_timestamp_ms` |
| `src/handlers/line/line_webhook.py` | 去重キー抽出の利用 |
| `tests/line/test_line_message_handler.py` | イベント timestamp 付きテスト |
| `tests/line/test_line_progressive_delivery.py` | Push 後 full bundle 非送信の回帰 |
| `tests/line/test_line_webhook.py` | `LINE_LOCK_DIR` 分離 |

---

## 2026年6月15日 — LINE フィードバック永続化・管理画面手動返信 Push・評価 postback 重複抑制

### 概要

- **LINE 評価 pending の DB 永続化**: `sessions.line_feedback_pending`（JSONB）カラムを追加。`database.py` に `get_line_feedback_pending` / `set_line_feedback_pending` を実装。`line_feedback.py` はメモリ + 専用カラムへの保存に変更し、評価コンテキスト登録時のフルセッション `save_session_to_db` を廃止。
- **pending 読込の多段フォールバック**: プロセス内メモリ → セッションメモリ → DB の順で pending を復元。チャット終了時は `clear_line_feedback_pending` でメモリ・DB 双方をクリア。
- **Quick Reply displayText 重複抑制**: postback の `displayText`（「役に立った」等）が message イベントとして再送されるケースを `is_line_feedback_display_text` で検出し、通常メッセージ処理をスキップ。
- **同一 Webhook 内の postback 優先**: `process_line_events` で postback を message より先に処理。評価 postback と直後の displayText echo の競合を防止。
- **期限切れ評価 postback のサイレント処理**: pending コンテキストが無い postback は reply せずログのみ（ユーザーへの不要なエラー返信を排除）。
- **管理画面手動返信の LINE Push**: `line_admin_manual_reply.py` を新設。`POST /api/main/manual_reply_queue`（action=reply）で LINE セッションへ `push_messages` によるテキスト Push。Web セッションは従来どおり DB 保存のみ。`line_pushed` / `line_error` を API レスポンスに含める。
- **`user_id_from_line_sid`**: `line:{userId}` 形式から LINE userId を抽出するヘルパーを `line_session.py` に追加。
- **LINE テキスト処理後の status クリア**: `_process_text_message` 終了時に `clear_processing_status(sid)` を呼び、処理中表示の残留を防止。
- **管理画面 UI**: `admin_chat.js` の手動返信通知を拡張。LINE Push 成功・失敗・トークン未設定を warning / success で区別表示。

### 新規ファイル

| パス | 内容 |
|------|------|
| `src/handlers/line/line_admin_manual_reply.py` | 管理画面手動返信の DB 保存 + LINE Push |
| `tests/line/test_line_admin_manual_reply.py` | LINE Push / Web スキップ / トークン未設定 |
| `tests/line/test_line_session_ids.py` | `user_id_from_line_sid` |

### 変更ファイル

| パス | 内容 |
|------|------|
| `src/services/database.py` | `line_feedback_pending` カラム・get/set |
| `src/handlers/line/line_feedback.py` | DB 永続化・displayText 判定・サイレント postback |
| `src/handlers/line/line_message_handler.py` | postback 優先・displayText 無視・status クリア |
| `src/handlers/line/line_session.py` | `user_id_from_line_sid` |
| `src/handlers/chat/chat_session_route.py` | 終了時 `clear_line_feedback_pending` |
| `main.py` | 手動返信 API → `apply_admin_manual_reply` |
| `static/js/admin_chat.js` | 手動返信の LINE Push 結果通知 |
| `tests/line/test_line_feedback.py` | DB 永続化・displayText・期限切れ postback |
| `tests/line/test_line_message_handler.py` | displayText 無視・postback 優先順 |

---

## 2026年6月13日 — LINE/Web 返信速度改善（第2弾）・DB 監視・運用ドキュメント

### 概要

- **挨拶・メタ質問の第一段階トリアージ LLM 省略**: `llm_triage.py` で `_concierge_fast_path_hint`（exact_match / keyword_probe）に該当する入力は第一段階 LLM を呼ばず Other + `concierge_intent` を即返却。「こんにちは」で LLM 0 回・`check_llm_allowed` も未呼び出し。
- **`check_llm_allowed` リクエスト内キャッシュ**: `budget_guard.py` に ContextVar キャッシュを追加。`chat_handler.py` の POST 開始時に `reset_budget_check_cache()` を呼び、同一リクエスト内の重複 DB 参照を防止。
- **LINE Concierge 保存のメモリ優先**: `chat_concierge_route.py` の `_sync_session_db` は LINE sid 時 `touch_session_in_memory` + `maybe_persist_session_activity`（throttle）のみ。DB 読込待ちを排除。
- **`save_session_to_db` の可用性判定**: `session_manager.py` で `db.connection or db.connection_pool` ではなく `db.is_available()` を使用。接続プール存在のみで保存を試みず、不良時の再接続ループを回避。
- **LINE persist の force / throttle 分離**: `persist_session_from_chat_state(..., force_persist=)` を追加。ターン終了（`persist_line_session`）は `force_persist=True` で即時永続化、途中更新は throttle。`concierge_state` / `counseling_mode` / `last_triage_result` 等も payload に含める。
- **`prime_line_session` 状態復元拡張**: メモリ上の `concierge_state`・`counseling_mode`・`last_triage_result` / `_last_triage_result` をセッションへ復元。
- **重複 LINE Webhook の job lock 先行**: `line_message_handler.py` で job lock 取得成功後にのみ `begin_line_loading`。重複イベントは loading / パイプラインを走らせない。
- **carousel Push 3 秒タイムアウト**: `line_progressive_delivery.py` の `CAROUSEL_FLUSH_TIMEOUT_SEC=3.0`。タイムアウト・失敗時は `carousel_failed=True` とし最終 reply に carousel を含める。
- **httpx クライアント再利用**: `line_reply.py` の `acquire_thread_http_client()`（thread-local keepalive）。`line_message_handler.py` はイベント処理ごとの `AsyncClient` 生成を廃止。
- **async パイプライン executor**: `chat_post_pipeline_async` を `asyncio.to_thread` から `get_chat_executor()`（max_workers=2）へ変更。
- **PIPELINE_PERF マーク追加**: LINE handler に `line_loading_start` / `line_reply_done` を記録。
- **管理画面 DB 状態表示**: `database.py` の `get_database_status()` / `validate_database_url_config()`（Neon pooler 警告・sslmode）。`GET /admin/system_status` の `database` フィールドと `admin_chat.js` 監視モーダルに表示。起動時 `init_database()` 後に `is_db_persist_enabled()` を呼び persist 可否を確定。
- **運用ドキュメント**: `CLOUD_RUN_LLM_ENV.md` / `LINE_WEBHOOK_SETUP.md` に Cloud Run `min-instances=1` 等のコールドスタート対策を追記。手動ベンチ手順を `LINE_SPEED_BENCH.md` に新設。`SMOKE_MANUAL.md` の system_status 項目に `database` フィールドを明記。

### 新規ファイル

| パス | 内容 |
|------|------|
| `docs/ops/LINE_SPEED_BENCH.md` | LINE 応答速度ベンチ（挨拶 <1秒・症状 4〜6秒）手順 |
| `tests/services/test_budget_guard_cache.py` | `check_llm_allowed` ContextVar キャッシュ |
| `tests/services/test_database_status.py` | `get_database_status` / pooler 警告 |
| `tests/line/test_line_session_prime.py` | `prime_line_session` の Concierge/triage 復元 |

### 変更ファイル

| パス | 内容 |
|------|------|
| `src/services/llm_triage.py` | 第一段階 LLM 省略（fast path hint） |
| `src/services/budget_guard.py` | ContextVar キャッシュ・`reset_budget_check_cache` |
| `src/handlers/chat_handler.py` | POST 開始時キャッシュリセット |
| `src/handlers/chat/chat_concierge_route.py` | LINE `_sync_session_db` メモリ + throttle |
| `src/handlers/chat/chat_post_pipeline.py` | `get_chat_executor` 経由 async 実行 |
| `src/services/chat_worker.py` | executor max_workers=2 |
| `src/services/session_manager.py` | `is_available()`・`force_persist` |
| `src/handlers/line/line_message_handler.py` | job lock 先行・loading 順序・PIPELINE_PERF |
| `src/handlers/line/line_progressive_delivery.py` | carousel 3 秒タイムアウト |
| `src/handlers/line/line_reply.py` | thread-local httpx 再利用 |
| `src/handlers/line/line_session.py` | prime 復元拡張・`force_persist=True` |
| `src/services/database.py` | `get_database_status` / URL 検証 |
| `main.py` | 起動時 persist 判定・system_status に database |
| `static/js/admin_chat.js` | DB 状態パネル |
| `docs/ops/CLOUD_RUN_LLM_ENV.md` | min-instances・pooler 推奨 |
| `docs/ops/LINE_WEBHOOK_SETUP.md` | コールドスタート対策 |
| `docs/ops/SMOKE_MANUAL.md` | system_status database フィールド |
| `tests/llm/test_llm_triage_stage2_skip.py` | 挨拶 LLM 0 回アサート |
| `tests/line/test_line_message_handler.py` | job lock / loading 順序 |
| `tests/line/test_line_progressive_delivery.py` | carousel タイムアウト |
| `tests/line/test_line_session_persist.py` | force_persist・DB 不可時非ブロック |
| `tests/api/test_fastapi_contract.py` | system_status database 契約 |

---

## 2026年6月13日 — LINE/Web 返信速度改善・loading 即時表示

### 概要

- **NLU ∥ 症状分類の並列化**: `recommendation_llm_batch.py` で `resolve_nlu_for_recommendation` と `analyze_symptoms_and_medicine_type` を ThreadPoolExecutor（max_workers=2）で同時実行。`chat_recommendation_flow.py` の旧 Step1/Step3 単体 LLM を batch 呼び出しに統合。
- **usage_notes 並列生成**: 添付文書フォールバックの LLM 呼び出しを max_workers=3 で並列化。HTML 結合順序は従来どおり。
- **Web SSE カード先行**: rule_based 成功・medicines ありの直後に `emit_cards`。説明文・パーソナライズアドバイスより先にカードを表示。
- **LINE 段階配信（Physical のみ）**: `line_progressive_delivery.py` で Push carousel → Reply（advice + feedback）。carousel 失敗時は従来どおり一括 Flex 2 通。Physical 以外・Emotional/Ask/Other は従来フロー。
- **LINE パーソナライズアドバイス省略**: `is_line_session_id` 時は `generate_personalized_advice` をスキップ（carousel に説明含むため）。
- **LINE 属性-only DB throttle**: `persist_session_attributes_only()` で LINE 属性更新は `maybe_persist_session_activity`、Web は即時 save。推奨完了時のフル persist は従来どおり。
- **async パイプライン**: `handle_chat_post_async` / `run_chat_post_pipeline_async` / `recommendation_llm_batch_async.py` を追加。LINE handler は async 直呼び、Web SSE は `asyncio.to_thread` で後方互換。
- **PIPELINE_PERF 計測**: `pipeline_perf.py` で主要ステップの壁時計をログ出力（Web handler / LINE handler 終了時）。
- **Golden 回帰**: `tests/fixtures/golden/recommendation_physical.jsonl` と `test_golden_regression.py` を拡張。
- **loading 即時表示**: `begin_line_loading()` をハンドラ先頭で await し、セッション DB 読込・言語判定・ job lock 取得より前に `loading/start` を送信。keepalive は初回送信後 50 秒間隔で再発火。
- **LINE prime/setup の DB 読込スキップ**（追記 `884074d` 以降）: `prime_line_session` / `setup_llm_request` は LINE sid でメモリのみ参照。DB 接続不良時の再接続待ちでパイプラインが数十秒停止するのを防止。
- **LINE `get_session_from_db` メモリ専用**（`80e60bb` 以降）: Concierge 保存等パイプライン全体の LINE 読込で DB に触れない。`_db_persist_enabled is False` 時は Web も読込スキップ。
- **DB 再接続 fail-fast**（`0764fa5` 以降）: 接続テスト失敗・再接続失敗後はプールを破棄し `get_connection` を即 `None`。`check_llm_allowed` / `get_global_state` による数十秒ブロックを防止。パイプライン早期ステップに `PIPELINE_PERF` マーク追加。

### 新規ファイル

| パス | 内容 |
|------|------|
| `src/handlers/chat/recommendation_llm_batch.py` | NLU ∥ 症状分類・usage_notes 並列 |
| `src/handlers/chat/recommendation_llm_batch_async.py` | async 版 batch |
| `src/handlers/line/line_progressive_delivery.py` | LINE Push1 + Reply1 段階配信 |
| `src/services/pipeline_perf.py` | PIPELINE_PERF タイマー |
| `tests/agents/test_recommendation_llm_batch.py` | batch 並列・フォールバックテスト |
| `tests/agents/test_recommendation_llm_batch_async.py` | async batch テスト |
| `tests/line/test_line_progressive_delivery.py` | 段階配信ユニットテスト |
| `tests/handlers/chat/test_recommendation_sse_order.py` | SSE カード先行順序テスト |
| `tests/fixtures/golden/recommendation_physical.jsonl` | Physical 推奨 golden |
| `tests/services/test_persist_session_attributes.py` | 属性-only persist テスト |

### 変更ファイル

| パス | 内容 |
|------|------|
| `src/handlers/chat/chat_recommendation_flow.py` | batch 接続・SSE 順序・LINE hook・属性 persist helper |
| `src/handlers/chat/chat_post_pipeline.py` | async エントリ |
| `src/handlers/chat_handler.py` | `handle_chat_post_async` |
| `src/handlers/chat_stream.py` | async パイプライン呼び出し |
| `src/handlers/line/line_message_handler.py` | async パイプライン・段階配信・loading 即時 dispatch |
| `src/handlers/line/line_loading.py` | `begin_line_loading` / `end_line_loading` |
| `src/services/session_manager.py` | `persist_session_attributes_only` |
| `docs/ops/LINE_WEBHOOK_SETUP.md` | 段階配信・PIPELINE_PERF・Push クォータ追記 |
| `tests/integration/test_golden_regression.py` | golden 拡張 |
| `tests/line/test_line_message_handler.py` | progressive / loading テスト更新 |

---

## 2026年6月13日 — Artifact Registry クリーンアップポリシー対象リポジトリ修正

### 概要

- **デフォルトリポジトリ名の修正**: `set_artifact_registry_cleanup_policy.sh` の `REPOSITORY` 既定値を `medicine-recommend` から `cloud-run-source-deploy` に変更。Cloud Run 継続的デプロイが実際に push する Artifact Registry リポジトリに合わせ、クリーンアップポリシー（最新 5 イメージ保持・24 時間超の古いバージョン削除）が正しい対象へ適用されるようにした。
- **運用コメント追加**: リポジトリ名は GCP コンソールまたはビルドログで確認する旨をスクリプト内に記載。

### 変更ファイル

| パス | 内容 |
|------|------|
| `scripts/gcp/set_artifact_registry_cleanup_policy.sh` | `REPOSITORY` 既定値を `cloud-run-source-deploy` に変更・コメント追加 |

---

## 2026年6月11日 — トリアージ第二段階省略・LINE loading keepalive・緊急判定改善

### 概要

- **第二段階トリアージ省略**: `llm_triage` で Other かつ confidence ≥ 0.85 のとき、挨拶・メタ質問をキーワードプローブで判定し第二段階 LLM をスキップ。`concierge_intent` / `concierge_intent_source` をトリアージ結果に付与。パイプライン先頭の `try_concierge_pre_triage` は廃止し、トリアージ内で統合。
- **緊急判定の誤検知防止**: `emergency_classifier` が Concierge 意図（挨拶・メタ質問等）と `greeting` / `thanks` を緊急候補から除外。
- **Concierge 重複 enrich 防止**: トリアージ結果に `concierge_intent` が既にある場合、`enrich_other_concierge_intent` をスキップ。履歴は `get_recent_messages` で取得。
- **LINE loading keepalive**: `line_loading.py` で 50 秒ごとに `loading/start` を再発火（API 上限 60 秒対策）。パイプライン完了後にキャンセル。
- **LINE 配信**: 処理完了後も `reply_token` を `_deliver_line_messages` に渡し Reply 優先配信を復活。
- **LINE パイプライン高速化**: `line:` sid では `session_data_for_ai` の DB 読み込みをスキップ。

### 新規ファイル

| パス | 内容 |
|------|------|
| `src/handlers/line/line_loading.py` | loading animation の keepalive（50 秒間隔） |
| `tests/test_line_loading.py` | keepalive テスト |
| `tests/test_llm_triage_stage2_skip.py` | 第二段階省略・曖昧 Other は stage2 実行のテスト |

### 変更ファイル

| パス | 内容 |
|------|------|
| `src/services/llm_triage.py` | `_concierge_fast_path_hint`・stage2 スキップ条件 |
| `src/agents/emergency_classifier.py` | Concierge 意図・挨拶の緊急候補除外 |
| `src/agents/concierge_agent.py` | 既存 `concierge_intent` 時の enrich スキップ |
| `src/handlers/chat/chat_concierge_route.py` | `try_concierge_pre_triage` 削除・`get_recent_messages` |
| `src/handlers/chat/chat_post_pipeline.py` | 先行 Concierge ルート削除・LINE DB 読み込みスキップ |
| `src/handlers/line/line_message_handler.py` | loading keepalive・reply_token 復活 |
| `tests/test_concierge_route.py` | 廃止した pre_triage テスト削除 |

---

## 2026年6月11日 — Concierge 先行ルート・LINE セッション整理・フィードバック安定化

### 概要

- **Concierge 先行ルート（トリアージ省略）**: 挨拶・感謝・メタ質問（「あなたについて」「何ができる？」等）をキーワードプローブで判定し、LLM トリアージ前に `try_concierge_pre_triage` で Concierge へ直行。LINE の応答遅延を短縮。
- **キーワードプローブ**: `probe_meta_concierge_intent` / `resolve_pre_triage_concierge_intent` を追加。`concierge_orchestrator` でもプローブを優先し、`chitchat` / `redirect` / `none` は非同期検証をスキップ。
- **LINE セッション上限**: `trim_line_session_messages` で会話履歴を最大 **24 件**に抑制（`prime_line_session` / `persist_line_session` 時）。プロンプト肥大化を防止。
- **LINE チャット終了**: `clear_line_session_state` で会話・カウンセリング・一時フラグをリセット。`line:` sid の終了時は DB から `line_feedback_pending` も削除。
- **フィードバック pending 安定化**: メモリ優先ストア（TTL **24 時間**）を追加。DB 未接続・不整合時も postback を受け付け。

### 新規ファイル

| パス | 内容 |
|------|------|
| `tests/test_line_session_policy.py` | trim・クリア・LINE 終了時の DB 保存テスト |

### 変更ファイル

| パス | 内容 |
|------|------|
| `src/services/concierge_intent.py` | `probe_meta_concierge_intent`・`resolve_pre_triage_concierge_intent`・メタ意図ルール |
| `src/handlers/chat/chat_concierge_route.py` | `try_concierge_pre_triage` |
| `src/handlers/chat/chat_post_pipeline.py` | トリアージ前に先行 Concierge ルートを挿入 |
| `src/services/concierge_orchestrator.py` | キーワードプローブ優先・検証スキップ条件 |
| `src/handlers/line/line_session.py` | `trim_line_session_messages`・`clear_line_session_state`・`is_line_session_id` |
| `src/handlers/chat/chat_session_route.py` | LINE 終了時の履歴クリア・pending 削除 |
| `src/handlers/line/line_feedback.py` | メモリ pending・TTL 24h |
| `tests/test_concierge_intent_extended.py` | プローブ・先行ルートテスト |
| `tests/test_concierge_route.py` | `try_concierge_pre_triage` テスト |
| `tests/test_line_feedback.py` | DB 不整合時の pending 生存テスト |

---

## 2026年6月11日 — LINE status Flex 再導入・Concierge `line_flex` スペック

### 概要

- **status Flex 復帰**: 危機・緊急・エスカレーション・追加質問・薬剤師フォールバックは再びパステル調 **status Flex bubble**（1 件）で配信。挨拶・雑談・カウンセリング・Concierge の短文（`greeting` / `chitchat` / `redirect` 等）は**テキスト**のまま。
- **構造化スペック**: `flex_status_spec.py` で `line_flex` 辞書または Web `status_card` HTML を解析し、タイトル・本文・ヒントを Flex へ反映。明示 `line_flex` が HTML より優先。
- **Concierge 連携**: capabilities / architecture / app_about / operator カードに `build_concierge_*_line_flex()` を追加。`chat_concierge_route` が bot メッセージへ `line_flex` を伝播。LINE で Web と同じカスタムヘッダー（例: 「このツールについて」）を表示。
- **Simulator fixture**: `status_*.json` を Flex bubble 形式に戻し、エクスポートスクリプトは `contents` を出力。

### 新規ファイル

| パス | 内容 |
|------|------|
| `src/handlers/line/flex_status_spec.py` | `line_flex` 正規化・status_card HTML パーサ・`resolve_status_flex_spec` |
| `tests/test_line_flex_status_spec.py` | スペック解決・Concierge タイトル一致テスト |

### 変更ファイル

| パス | 内容 |
|------|------|
| `src/handlers/line/flex_messages.py` | `_plain_text_line_messages` / `_try_resolved_status_flex`・status Flex 再構築 |
| `src/services/concierge_templates.py` | `build_concierge_*_line_flex()` 4 種 |
| `src/agents/concierge_agent.py` | payload に `line_flex` 付与 |
| `src/handlers/chat/chat_concierge_route.py` | bot メッセージへ `line_flex` 保存 |
| `scripts/export_line_flex_simulator_samples.py` | status 出力を `contents` に |
| `tests/fixtures/line_flex_simulator/status_*.json` | Flex bubble 形式に更新 |
| `tests/test_line_flex_messages.py` / `test_line_dev_triggers.py` | status Flex・挨拶テキストの期待値更新 |

---

## 2026年6月11日 — 方言前処理撤廃・LINE 応答遅延対策

### 概要

- **方言変換**: ルールベース方言辞書の前処理初期化をスキップし初回応答を高速化。理解・口調は NLU / カウンセリング LLM プロンプトへ委譲（`i18n_prompts.py` に方言指示追加）。
- **LINE job lock**: `line_job_lock.py` で sid 単位の排他（Linux: fcntl ファイルロック、Windows: スレッドロック）。Gunicorn 複数ワーカー間の二重処理を防止。
- **配信**: Push のみに統一し replyToken 失効を回避（`line_processing_reply` の通常待機文言を削除）。

### 新規ファイル

| パス | 内容 |
|------|------|
| `src/handlers/line/line_job_lock.py` | LINE 処理排他ロック |
| `tests/test_line_job_lock.py` | ロックテスト |
| `tests/test_i18n_dialect_prompts.py` | 方言プロンプトテスト |

### 変更ファイル

| パス | 内容 |
|------|------|
| `src/handlers/chat/chat_preprocess_route.py` | 方言辞書前処理を削除 |
| `src/core/nlu_service.py` / `counseling_llm.py` | 方言理解を LLM 側へ |
| `src/handlers/line/line_message_handler.py` | job lock 連携・Push 配信 |
| `src/services/chat_response_service.py` | 応答生成まわり調整 |
| `tests/test_chat_preprocess_route.py` 他 | 前処理変更に合わせて更新 |

---

## 2026年6月11日 — LINE フィードバック・loading UX・応答形式の整理

### 概要

- **Quick Reply フィードバック**: 推奨応答の最後のメッセージに 👍/👎 を付与。postback で Web の `POST /api/submit_feedback` と同じ DB（開発時は dev フォールバック）へ保存。60 秒 dedupe・有効期限 1 時間。
- **loading animation**: 処理開始時の「確認中」テキスト Reply を廃止し、LINE Messaging API `chat/loading/start` で標準の「…」表示（`LINE_LOADING_SECONDS`、5〜60 秒・既定 60）。二重送信時のみ多言語の待機テキスト。
- **応答形式**: 危機・エスカレーション・追加質問・一般案内は status Flex から**テキストメッセージ**へ変更（5000 文字分割）。推奨成功時のみ advice + carousel の Flex 2 件。医薬品 hero は常時表示（No Image プレースホルダー、`PUBLIC_SITE_URL` 未設定時は `https://medicine.yutok.dev`）。
- **配信改善**: 1 リクエスト最大 5 件まとめて Reply/Push。先頭チャンクは Reply、続きは Push。失敗時は altText / 本文でテキストフォールバック。
- **フィードバック共通化**: `src/services/feedback_submit.py` に保存ロジックを集約。`main.py` の `/api/submit_feedback` も同モジュール経由。

### 新規ファイル

| パス | 内容 |
|------|------|
| `src/handlers/line/line_feedback.py` | Quick Reply 生成・postback 処理・セッション pending 管理 |
| `src/handlers/line/line_processing_reply.py` | 二重送信時の待機文言（i18n） |
| `src/services/feedback_submit.py` | Web / LINE 共通のフィードバック保存・dedupe |
| `tests/test_line_feedback.py` | フィードバック Quick Reply / postback テスト |
| `tests/test_line_processing_reply.py` | loading API・待機文言テスト |

### 変更ファイル

| パス | 内容 |
|------|------|
| `src/handlers/line/flex_messages.py` | 非推奨系をテキスト化。hero 常時付与。`LINE_TEXT_MAX=5000` 分割 |
| `src/handlers/line/line_message_handler.py` | loading・`_deliver_line_messages`・postback・Reply 優先配信 |
| `src/handlers/line/line_reply.py` | `start_loading_animation` / `LINE_LOADING_SECONDS` |
| `src/handlers/line/line_i18n.py` | フィードバック・`processing_busy` 文言（ja/en） |
| `main.py` | `submit_feedback_record` へ委譲 |
| `.env.example` | `LINE_LOADING_SECONDS` コメント |
| `scripts/export_line_flex_simulator_samples.py` | status 系 fixture をテキストメッセージ形式に更新 |
| `tests/fixtures/line_flex_simulator/status_*.json` | Flex bubble → text メッセージ |
| `tests/test_line_flex_messages.py` 他 | 上記仕様変更に合わせて更新 |

### 環境変数

| 変数 | 用途 |
|------|------|
| `LINE_LOADING_SECONDS` | loading animation 表示秒数（5〜60、5 秒刻み、既定 60） |
| `PUBLIC_SITE_URL` | No Image hero のベース URL（未設定時は本番 URL を使用） |

---

## 2026年6月11日 — LINE Flex 拡張・Webhook 安定性・開発プレビュー

### 概要

- **Flex デザイン**: パステル調の status / advice / carousel bubble。`static/line/medicine-noimage-hero.png` プレースホルダー hero。`docs/未踏/docs/line.json`・`line_advice.json` を参照してレイアウト整備。
- **Webhook 安定性**: Gunicorn タイムアウト回避のためイベント処理を専用スレッド＋スレッド内 `httpx.AsyncClient` で実行。Push 失敗時のテキストフォールバック・`resolve_latest_bot_message` による bot メッセージ解決を改善。
- **開発プレビュー**: `line_dev_triggers.py` で特定文字列送信時に Flex/テキストサンプルを Push（本番無効）。`scripts/export_line_flex_simulator_samples.py` で Flex Simulator 用 JSON を一括出力。`docs/DEV_LINE_FLEX_PREVIEW.md` 追加。

### 新規ファイル

| パス | 内容 |
|------|------|
| `src/handlers/line/line_dev_triggers.py` | 開発専用 Flex プレビュートリガー |
| `scripts/export_line_flex_simulator_samples.py` | Simulator 用 fixture エクスポート |
| `static/line/medicine-noimage-hero.png` | 医薬品 No Image hero |
| `docs/DEV_LINE_FLEX_PREVIEW.md` | dev トリガー一覧・手順 |
| `tests/fixtures/line_flex_simulator/*.json` | success / status 各種サンプル |
| `tests/test_line_dev_triggers.py` | dev トリガーテスト |
| `tests/test_line_session.py` | セッション解決テスト |

### 変更ファイル

| パス | 内容 |
|------|------|
| `src/handlers/line/flex_messages.py` | status bubble・hero 解決・advice/carousel 拡張 |
| `src/handlers/line/line_message_handler.py` | dev プレビュー連携・配信ヘルパー |
| `src/handlers/line/line_session.py` | `resolve_latest_bot_message` |
| `src/handlers/line/line_webhook.py` | バックグラウンドスレッド実行 |
| `config/line_config.py` | dev トリガー用設定 |
| `start.sh` | Gunicorn タイムアウト調整 |
| `docs/LINE_WEBHOOK_SETUP.md` / `docs/CLOUD_RUN_LLM_ENV.md` | 運用追記 |

---

## 2026年6月10日 — LINE Flex Message E2E

### 概要

- **Webhook → 推奨パイプライン → Flex Push**: 1:1 テキストを既存 `handle_chat_post` に渡し、結果を Flex Message（アドバイス bubble + 医薬品 carousel 最大3件）で Push。即時 Reply は「症状を確認しています。少々お待ちください。」のみ。
- **セッション**: sid は `line:{userId}` 形式。DB からメッセージ履歴を復元し、パイプライン完了後に最新 bot メッセージを DB から取得して Flex 化（Cookie 肥大化対策後も正しく動作）。
- **安全性**: 危機・緊急・エスカレーション（`escalation_required` / `no_candidates` / `error` / `blocked`）は Flex ではなくテキスト Push。既存 `manual_reply_queue`・管理画面エスカレーションは維持。
- **重複防止**: `webhookEventId` をメモリ内 TTL（120秒）で去重。同一 sid の並行処理は `chat_inflight.is_chat_job_in_flight` で検知し待機テキストを返す。
- **イベント種別**: `follow` はウェルカム Reply、`unfollow` はログのみ、グループチャット・非テキスト（スタンプ・画像）は案内テキストで応答。

### 新規ファイル

| パス | 内容 |
|------|------|
| `src/handlers/line/flex_messages.py` | Flex JSON ビルダー（純関数）。HTML bot メッセージをパースしアドバイス bubble + 医薬品 carousel を生成。hero 画像は v1 省略。ja/en/ko/zh UI 文言対応 |
| `src/handlers/line/line_i18n.py` | Flex UI 文言 i18n（ランク・スコア・カルーセル alt 等） |
| `src/handlers/line/line_reply.py` | LINE Reply / Push API クライアント（httpx）。lifespan 注入クライアント優先、未注入時は一時クライアント |
| `src/handlers/line/line_session.py` | `line:{userId}` sid 生成、DB 復元・永続化、`get_latest_bot_message` |
| `src/handlers/line/line_dedup.py` | `webhookEventId` メモリ内去重（TTL 120秒） |
| `src/handlers/line/line_message_handler.py` | イベント処理本体。Reply → `handle_chat_post`（`asyncio.to_thread`）→ Push。エラー時は安全テキスト + alert_email 通知 |
| `scripts/line_push_preview.py` | Webhook 不要の Push プレビュー（`--dry-run` / `--user-id` / `--symptom`） |
| `tests/fixtures/line_flex_success.json` | Flex 成功応答のゴールデンフィクスチャ |
| `tests/test_line_flex_messages.py` | Flex ビルダー単体テスト |
| `tests/test_line_message_handler.py` | メッセージハンドラ統合テスト |
| `tests/test_line_reply.py` | Reply/Push API クライアントテスト |

### 変更ファイル

| パス | 内容 |
|------|------|
| `main.py` | FastAPI `lifespan` で `httpx.AsyncClient` を生成し `line_reply.set_http_client` に注入 |
| `config/line_config.py` | `LINE_PUSH_TO_USER_ID` 追加（プレビュースクリプト用） |
| `.env.example` | `LINE_CHANNEL_ACCESS_TOKEN`・`LINE_PUSH_TO_USER_ID` のコメント整備 |
| `src/handlers/line/__init__.py` | モジュール説明を Webhook + Reply/Push + Flex に更新 |
| `src/handlers/line/line_webhook.py` | 署名検証後即 200、イベントは `asyncio.create_task` でバックグラウンド処理。去重・token 未設定警告 |
| `src/services/chat_inflight.py` | `is_chat_job_in_flight(sid)` 追加（LINE 並行メッセージ制御） |
| `tests/test_line_webhook.py` | バックグラウンドスケジュールのテスト追加 |

### ドキュメント

| パス | 内容 |
|------|------|
| `docs/LINE_WEBHOOK_SETUP.md` | 「未実装」記述を削除。Flex・Reply/Push・ローカル確認手順・Cloud Run 運用注意を追記 |
| `docs/ROUTE_SPEC.md` | `POST /line/webhook` のシーケンス・HTTP ステータス・環境変数表を追記 |
| `docs/ADMIN_PII_PLAYBOOK.md` | LINE セッション ID（`line:Uxxxxxxxx`）の扱いを追記 |
| `docs/ARCHITECTURE_MULTI_AGENT.md` | LINE 経由相談の sid 形式と管理画面参照を追記 |

### 環境変数

| 変数 | 用途 |
|------|------|
| `LINE_CHANNEL_SECRET` | Webhook 署名検証（必須） |
| `LINE_CHANNEL_ACCESS_TOKEN` | Reply / Push API（返信時必須） |
| `LINE_WEBHOOK_ENABLED` | `true` で `POST /line/webhook` 有効化 |
| `LINE_PUSH_TO_USER_ID` | `scripts/line_push_preview.py` 用（Webhook では未使用） |
| `DATABASE_URL` | セッション永続化（推奨） |

---

本ドキュメントは、チャット型医薬品相談ツールの開発・更新の記録です。プロジェクトの概要・セットアップ・使い方は [README.md](README.md) を参照してください。アーキテクチャ正本は [docs/ARCHITECTURE_MULTI_AGENT.md](docs/ARCHITECTURE_MULTI_AGENT.md)。

---

## 2026年6月2日 — ユーザー嗜好 LLM 統合（GPT 並列 NLU）

### 概要

- **症状 NLU と嗜好 GPT を並列実行**: `resolve_nlu_for_recommendation` で `hybrid_nlu_extraction`（症状）と `extract_preferences_with_gpt`（薬選びの希望）を `ThreadPoolExecutor` で同時実行。壁時計は max(症状, 嗜好)。マージ後の `nlu_result`（`symptoms` + `user_preferences`）を NLU キャッシュに保存。
- **安全キーワードと LLM の役割分離**: 一般嗜好キーワードのルール直判定を廃止。GPT はカタログ参照語で嗜好を分類（confidence 付き）。**運転・車** 等の `safety_hard_keywords` のみマージ時に強制（`avoid_drowsiness` 等、source=`safety`）。
- **閾値**: スコア加点・減点は confidence **≥ 0.5**。成分・血管収縮点鼻クラスの**スコア前除外**は **≥ 0.8**（`preference_candidate_filter`）。
- **口渇**: 症状辞書の「口渇」は主訴のまま。`avoid_dry_mouth`（口渇の少ない薬がいい）は **GPT のみ**（旧キーワード連動は削除）。
- **推奨 API**: 返却 JSON に `user_preferences_summary`（各フィールド・confidence・`sources`）を追加。エンドユーザー HTML には未表示（API / 将来 admin 用）。
- **症状 GPT 多言語化**: `extract_symptoms_with_gpt` が en/ko/zh 入力を受け付け、`symptoms[].name` は常に `symptom_dictionary.json` の日本語 canonical に正規化。
- **環境変数**: `PREFERENCE_NLU_TIMEOUT_SEC`（既定 **8** 秒）。嗜好 GPT 失敗時は症状 NLU を継続し安全キーワードのみマージ（リトライなし）。機能フラグによるロールバックは設けず開発環境へ一括反映。

### 新規ファイル

| パス | 内容 |
|------|------|
| `data/user_preference_keyword_catalog.json` | 全領域の嗜好フィールド・GPT 参照語・安全強制語・`risk_exclude_rules`・`ingredient_groups` |
| `src/core/preference_nlu.py` | `extract_preferences_with_gpt`（`response_format=json_object`、ja/en/ko/zh プロンプト） |
| `src/core/preference_merge.py` | `merge_user_preferences` / `apply_safety_preference_overrides` / `build_user_preferences_summary` / `preference_field_confidence` |
| `src/core/recommendation/preference_candidate_filter.py` | confidence ≥ 0.8 で第1世代抗ヒスタミン・血管収縮点鼻・点鼻複合などを候補から除外（ステロイド点鼻は残す） |
| `docs/MANUAL_QA_PREFERENCES.md` | 手動 QA チェックリスト（GC-PREF-001〜004、英語入力） |
| `docs/PREFERENCE_NLU_DEV_REVIEW.md` | カタログ・除外ルールの開発レビュー用チェックリスト |
| `.cursor/skills/.../golden-cases-preferences.md` | Golden `GC-PREF-*`（運転+花粉、口渇、点鼻回避、other_info） |

### 変更ファイル（コア）

| モジュール | 内容 |
|-----------|------|
| `src/handlers/chat/nlu_resolve.py` | 並列 NLU の単一入口。マージ後キャッシュ。エージェント ON 時は症状側を `run_nlu_agent` |
| `src/core/nlu_service.py` | `hybrid_nlu_extraction(..., use_cache=)`。`extract_symptoms_with_gpt` 多言語プロンプト。GPT 呼び出し前に `detect_language` |
| `src/core/user_detection.py` | `extract_user_preferences` は **`nlu_result.user_preferences` 優先**。未設定時は `merge_user_preferences({}, text)`（安全語のみ）。長大な一般嗜好キーワードロジックを削除 |
| `src/core/rule_based_recommendation.py` | `precomputed_nlu` 優先で二重 NLU 回避。候補取得直後に `filter_candidates_by_preferences`。`user_preferences_summary` を返却 |
| `src/core/dictionary_loader.py` | `load_preference_keyword_catalog()` |
| `src/security/json_validator.py` | `preference_analysis` スキーマ追加 |
| `src/core/recommendation/life_stage_preference.py` | `apply_user_preference_bonus` で全フィールドに `preference_field_confidence` 重み（漢方希望含む） |
| `src/core/recommendation/pollen_rhinitis_scoring.py` | 眠気・口渇・点鼻・服用回数の boost/penalty を confidence 重み付け |
| `src/core/recommendation/final_score_calculator.py` | DEBUG 時 `score_breakdown.preference_sources`（llm / safety 由来） |
| `src/handlers/chat/chat_recommendation_flow.py` | 推奨前の誤った嗜好再抽出を削除。`user_info` / 再構築に `other_info` を伝播。`precomputed_nlu` で rule_based 呼び出し |

### UI

| ファイル | 内容 |
|---------|------|
| `static/js/main.js` | 属性モーダル `submitAttributes` 送信時に `/api/sessions` へ `user_attributes.other_info`（年齢・性別・アレルギー等と併せ）を POST 永続。`userInfoModal` の `user_other_info` 保存経路は既存 |

### データ・ドキュメント

- **`data/DATA_CATALOG.md`**: `user_preference_keyword_catalog.json` を追記。
- **`docs/ARCHITECTURE_MULTI_AGENT.md`**: NLUAgent = 症状 + 嗜好並列。嗜好 NLU セクション・手動 QA / レビュー doc へのリンク。
- **`.cursor/skills/.../golden-cases-index.md`**: `golden-cases-preferences.md` を索引に追加。

### テスト（新規・更新）

| ファイル | 内容 |
|---------|------|
| `tests/test_preference_merge.py` | 安全強制・confidence 閾値・漢方競合・候補除外 |
| `tests/test_preference_candidate_filter.py` | 0.8 未満は除外しない・点鼻回避でステロイド残存 |
| `tests/test_preference_catalog_loader.py` | カタログ読み込み・キャッシュ |
| `tests/test_preference_nlu.py` | GPT mock・ko/zh テンプレート |
| `tests/test_nlu_resolve_parallel.py` | 並列マージ・キャッシュ・GPT 失敗時 safety のみ |
| `tests/test_symptom_nlu_i18n.py` | 英語プロンプト・canonical 症状名 |
| `tests/test_pollen_rhinitis_scoring.py` | 嗜好テストを `nlu_result.user_preferences` mock に移行 |
| `tests/test_comprehensive_integration.py` | `test_extract_user_preferences_kampo` を nlu mock 方式に更新 |

### 設計上の注意（運用）

| 項目 | 内容 |
|------|------|
| 属性 vs 嗜好 | 年齢・妊娠・授乳・アレルギーは従来どおり `attribute_extractor` / モーダル。薬選びの希望のみ嗜好 NLU |
| 服用回数 | `prefer_fewer_daily_doses` / `preferred_max_daily_doses` は**除外せず**加点・減点のみ |
| 点鼻回避 | 血管収縮点鼻・点鼻複合のみスコア前除外。ステロイド点鼻は花粉推奨と両立 |
| 漢方競合 | `prefers_not_kampo` が `prefers_kampo` より優先 |
| 二重 NLU | チャットフローは `resolve_nlu` → `precomputed_nlu` で rule_based に渡す |

---

## 2026年6月2日 — 花粉症・アレルギー性鼻炎の推奨強化・LLM 既定 gpt5

### 概要

- **花粉症／アレルギー性鼻炎のルールベース推奨を大幅強化**: 風邪薬・総合感冒薬の混入を抑制し、製品クラス（第2世代内服・ステロイド点鼻・血管収縮点鼻など）と症状プロファイル・ユーザー嗜好に応じたスコア調整を追加。
- **併用注意の自動生成**: top3 に血管収縮点鼻の重複・抗ヒスタミン内服の重複などがある場合、用法注意 HTML を付与。
- **ユーザー嗜好の拡張**: 眠気回避・口渇回避・服用回数・点鼻希望／回避をチャット文と属性モーダル「その他」から検出しスコアに反映。
- **LLM 既定プロファイルを gpt5 に変更**: 環境変数未設定時は `gpt5`（従来は `legacy`）。ロールバックは `LLM_MODEL_PROFILE=legacy`。
- **オンボーディング文言**: GPT-5 系モデル・ChatOrchestrator 利用を反映（カナリア表現を整理）。

### 花粉症・アレルギー性鼻炎（新規・拡充）

| モジュール | 内容 |
|-----------|------|
| `src/core/recommendation/pollen_rhinitis_scoring.py`（新規） | 製品分類（`oral_2nd_gen` / `nasal_vasoconstrictor` 等）、症状プロファイル、嗜好反映、`pollen_boost` / `pollen_penalty`、血管収縮点鼻の用法警告 |
| `src/core/recommendation/pollen_combination_advice.py`（新規） | top3 併用時の注意文（血管収縮点鼻×2、抗ヒスタミン内服×2、第1/2世代併用など） |
| `src/core/candidate_scoring.py` | `is_pollen_rhinitis_focus()` — 感染兆候で花粉文脈解除。花粉寄り相談では風邪薬カテゴリ除外・抗アレルギー薬追加・候補フィルタ |
| `src/core/recommendation/final_score_calculator.py` | 花粉文脈で総合感冒薬ボーナス抑制（-0.50）、`pollen_boost` / `pollen_penalty` を最終スコアに合算 |
| `src/core/recommendation/ingredient_diversity.py` | 目のかゆみあり花粉相談で top3 に目薬スロット確保（`_ensure_pollen_eye_drop_slot`） |
| `src/core/rule_based_recommendation.py` | `user_preferences` を候補取得・スコアに渡す。推奨後に併用注意を `usage_notes` に追記 |
| `src/core/explanation_generator.py` | 血管収縮点鼻成分の短期連用警告を用法ノートに付与 |
| `src/core/user_detection.py` | `preference_context_text()` — メッセージ + `other_info` を結合。眠気・口渇・点鼻・服用回数の嗜好キーワード |
| `src/handlers/chat/chat_recommendation_flow.py` | `user_info` に属性モーダル `other_info` を渡す |
| `data/symptom_dictionary.json` | 「口渇」エントリ追加（NLU・嗜好検出の補助） |

### LLM 設定

- **`config/llm_config.py` / `llm_canary.py` / `llm_flags.py`**: `LLM_MODEL_PROFILE` 未設定時の既定を **`gpt5`** に変更。
- **`.env.example`**: プロファイル・ロール別モデルはコメント例に整理（コード既定 gpt5 を明記）。
- **`docs/CLOUD_RUN_LLM_ENV.md`**, **`docs/ROUTING_ARCHITECTURE_AUDIT.md`**: 本番の既定プロファイル表記を更新。
- **`src/services/llm_metrics.py`**: フォールバックプロファイルを `gpt5` に。
- **`tests/test_llm_canary_profile.py`**, **`tests/test_llm_phase0.py`**: 既定 gpt5 に合わせて期待値を更新。

### UI・ドキュメント・テスト

- **`templates/index.html`**: 属性・ユーザー情報の「その他」プレースホルダを花粉嗜好例（眠気・1日1回・点鼻・口渇）に変更。
- **`static/js/main.js`**: オンボーディングの完了項目文言を GPT-5 系・ChatOrchestrator に更新（日・英・韓・中）。
- **`.cursor/skills/.../golden-cases-cold.md`**: 風邪型ゴールデンケースの微修正。
- **`tests/test_pollen_rhinitis_scoring.py`**, **`tests/test_pollen_rhinitis_recommendation.py`**（新規）: 分類・嗜好・併用注意・統合推奨の回帰テスト。

### 運用上の注意

- **LLM を legacy に戻す場合**: Cloud Run / ローカルで `LLM_MODEL_PROFILE=legacy` を明示設定。
- **花粉症と風邪の切り分け**: のど痛み・発熱など感染兆候がある入力では `is_pollen_rhinitis_focus` が false になり、従来の風邪薬ルートに戻る。

---

## 2026年5月21日 — `/about` 刷新（セージ調パンフレット風・技術構成図・4言語）

### 概要

- **`/about` トップを全面リデザイン**: アプリアイコン（`favicon.ico.png`）とパンフレット（`static/pamphlet_C_16x9/`）に合わせたソフトセージ調のエディトリアルレイアウト。文言は HTML / i18n のみ（画像は文字なしのイラスト）。
- **4言語 i18n**: `src/content/about_i18n.py` で日本語・英語・韓国語・中国語のヒーロー・課題・特徴・使い方・技術・CTA 等を一元管理。
- **技術構成図（skillicons + ブランド PNG）**: LAPRAS / skillicons 風のブロック図を `templates/about/_tech_diagram.html` で表示。運用・CI/CD、フロントエンド、バックエンド、外部 API、マルチエージェント、データベースの関係を SVG コネクタで接続。
- **UI 簡素化**: ヒーローの研究βバッジ・スクロールヒントを削除。課題・特徴カードの装飾画像を削除し、特徴は縦 4 行グリッド。skillicons 下部の一覧バナーを削除。
- **タイポグラフィ**: `/about` 全体を **BIZ UDPGothic**（`main.css` の `--font-sans`）に統一。
- **開発時の注意**: ポート競合で別ポート起動時、`app.py` が古いプロセス残存の WARN を出力。`/about` のルート変更は uvicorn reload 対象に `about_i18n.py` を追加。

### 技術構成図のブロック構成

| ブロック | 内容 | 接続 |
|---------|------|------|
| 運用・CI/CD | GitHub, GCP, Git, Linux（skillicons.dev） | バックエンドへ矢印なし（独立表示） |
| フロントエンド | HTML, CSS, JavaScript | → バックエンド |
| バックエンド | Python, Flask, Docker | → 外部 API、↓ データベース |
| 外部 API | OpenAI, DeepL（ローカル PNG） | ↓ マルチエージェント |
| マルチエージェント | Python + OpenAI（`docs/ARCHITECTURE_MULTI_AGENT.md` 準拠の注記） | 外部 API の下段 |
| データベース | Neon, PostgreSQL（ローカル PNG） | バックエンド真下 |

- **skillicons.dev**: `openai` / `deepl` / `neon` は単体アイコンが空になるため、ブランドは `static/img/about/generated/tech/icon-*.png` を使用。
- **Neon アイコン**: 黒余白対策のため CSS でパディングを調整。

### `src/content/about_i18n.py`（新規・拡充）

- **`get_about_bundle(page_id, lang)`**: ページ別の翻訳バンドル（index / info / privacy / terms / policies / usage / faq / consultation）。
- **`build_tech_diagram(lang)`**: 構成図のラベル・ボックス・アイコン定義・SVG コネクタ座標・`aria-label`。
- **`about_nav_entries` / `about_lang_switch_rows` / `about_shell_labels` / `about_subpage_links`**: ナビ・言語切替・シェル文言。
- 課題・特徴から `image` / `alt` キーを削除（テキストのみ）。

### `main.py`

- **`/about` 系ルート**: FastAPI で index / サブページ / `/test/about` ミラーを提供。アクセス分析に `about_get` を記録。
- **`_render_about_page`**: index では常に `hero-pharmacy-chat.png` と `build_tech_diagram(lang)` を注入。
- **Jinja グローバル**: `build_tech_diagram` をテンプレートから参照可能に登録。

### `templates/about/`

- **`base_about.html`**: 共通シェル（ヘッダー・言語切替・`about.css` / `scrollbar.css` 経由のスクロール）。
- **`index.html`**: ヒーロー・課題・特徴・使い方・ハイブリッド説明・技術（`_tech_diagram.html` include）・CTA。ヒーロー `about-hero__badge`（研究β版）は表示しない。
- **`_tech_diagram.html`**: skillicons + ブランド PNG + SVG 矢印の構成図パーシャル。

### `static/css/about.css`（新規）

- セージ調カラー変数・エディトリアルヒーロー・カード・技術図グリッド（3×3 + コネクタ SVG）。
- `body.about-page` / `.about-root` で BIZ UDPGothic、`@import` で `scrollbar.css`（`.about-scroll.app-scrollbar`）。
- 削除済みスタイル: スクロールヒント、skillicons バナー、課題/特徴カード画像用レイアウト。

### `static/img/about/`（新規アセット）

- **`generated/`**: ヒーロー・背景パターン・チャット UI モック・課題イラスト（about 本文からは未参照のものあり）・`tech-architecture.png` 等。
- **`generated/tech/`**: OpenAI / DeepL / Neon の PNG、補助 SVG（Flask / GCP / GitHub 等）。
- **`icons/icon-stack-python.svg`**, **`demo-ipad-product.png`**, **`tech-stack-export.html`**: 静的プレビュー・デモ用。

### `app.py`

- ポート自動切替時に、古い uvicorn が残っていると `/about` が古い表示になる旨を WARN ログ出力。
- reload 監視に `src/content/about_i18n.py` を追加。

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

## 開発用 UI プレビュー（16パターン・すべて実装済み）

**`APP_ENV=development` のときのみ有効。** 本番ではトリガー語を送っても通常メッセージとして処理されます。  
詳細・環境変数・使い方: **[docs/ops/DEV_ERROR_UI_PREVIEW.md](docs/ops/DEV_ERROR_UI_PREVIEW.md)**

| # | トリガー（完全一致で送信） | 種類 | 表示 |
|---|---------------------------|------|------|
| 01 | `mrcdev00000000000001` | クライアント・エラー | 赤カード（`showErrorMessage`） |
| 02 | `mrcdev00000000000002` | クライアント・警告 | 赤枠・セキュリティ（`showWarningMessage`） |
| 03 | `mrcdev00000000000003` | HTTP 500 | 通信エラー系カード（fetch 失敗扱い） |
| 04 | `mrcdev00000000000004` | システムエラー | `sage_status` error |
| 05 | `mrcdev00000000000005` | 候補なし | `sage_status` caution |
| 06 | `mrcdev00000000000006` | 診断名通知 | `sage_status` notice |
| 07 | `mrcdev00000000000007` | エスカレーション | `sage_status` critical |
| 08 | `mrcdev00000000000008` | 挨拶 | `sage_status` notice（FB なし） |
| 09 | `mrcdev00000000000009` | 店舗案内 | `sage_status` notice + FB |
| 10 | `mrcdev00000000000010` | 医薬品 Q&A | `sage_qa` |
| 11 | `mrcdev00000000000011` | 推奨成功 | `sage_reco` + カルーセル |
| 12 | `mrcdev00000000000012` | 推奨 0 件 | `sage_reco` + error |
| 13 | `mrcdev00000000000013` | 緊急 | `sage_status` critical |
| 14 | `mrcdev00000000000014` | 危機支援 | `sage_status` security |
| 15 | `mrcdev00000000000015` | カウンセリング | `sage_status` notice |
| 16 | `mrcdev00000000000016` | 医薬品種類不明 | `sage_status` caution |

実装: `src/handlers/chat/chat_dev_triggers.py` / テスト: `tests/chat/test_chat_dev_triggers.py`  
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
