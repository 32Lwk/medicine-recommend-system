# 用語リサーチ — Meta KB 執筆用（R0・内部）

> 公開 SSOT: `09-glossary.md`（ユーザー向け要約）。本ファイルは網羅リスト。

## A. アーキテクチャ・インフラ

| 用語 | 説明 | SSOT |
|------|------|------|
| Cloud Run | GCP 本番 HTTP サービス | 01-cross-cloud |
| ECS Fargate | AWS ステージングコンテナ | 01-cross-cloud |
| Express Gateway | ECS 向け HTTP 入口 | 01-cross-cloud |
| Neon | サーバーレス PostgreSQL | 04-data-security |
| Cloudflare R2 | 医薬品画像 CDN ストレージ | 01-cross-cloud |
| CloudFront | AWS static アセット CDN | 03-deployment |
| ElastiCache Serverless | AWS セッションキャッシュ | 01-cross-cloud |
| ALB + WAF | AWS L7 ロードバランサ + WAF | 03-deployment |
| CodePipeline / CodeBuild | AWS CI/CD | 03-deployment |
| GitHub origin / GitLab mirror | 正本 + バックアップ | 08-technical-decisions |

## B. 会話・エージェント

| 用語 | 説明 | SSOT |
|------|------|------|
| Chat Pipeline v2 | 本番会話パイプライン | 02-chat-pipeline |
| IntentRouter | Physical/Concierge/Store 振分 | 10-agent-routing |
| TriageAgent | 入力分類 | 02-chat-pipeline |
| PhysicalOrchestrator | 症状解析・市販薬推奨 | 02-chat-pipeline |
| ConciergeAgent | メタ FAQ・挨拶 | 02-chat-pipeline |
| SessionAgent | セッション操作 | 02-chat-pipeline |
| StoreOrchestrator | 店舗検索（将来） | 02-chat-pipeline |
| SSE | Server-Sent Events ストリーミング | 02-chat-pipeline |
| meta_triage | Concierge メタ意図 LLM 分類 | 10-agent-routing |

## C. 推奨・データ

| 用語 | 説明 | SSOT |
|------|------|------|
| ルールベース推奨 | CSV+スコアで候補選定 | 02-chat-pipeline |
| OTC | Over-The-Counter 市販薬 | 09-glossary |
| PMDA / #7119 | 医薬品相談窓口 | public/医薬品相談先 |
| Comprehend Medical | AWS 医療 NLP（ステージング） | 01-cross-cloud |
| Personalize | 推奨ランキング補助（AWS） | 01-cross-cloud |

## D. RAG・ナレッジ

| 用語 | 説明 | SSOT |
|------|------|------|
| Local RAG | BM25+embedding ローカル検索 | ops/LOCAL_RAG |
| Bedrock KB | AWS マネージド KB | ops/LOCAL_RAG |
| concierge_knowledge.ja.json | アプリ概要 SSOT JSON | content/ |
| changelog digest | CHANGELOG 要約（RAG 除外） | content/changelog-digest |
| SSOT | Single Source of Truth | 08-technical-decisions |
| doc_type | public doc 分類タグ | local_rag_index |

## E. 翻訳・TTS・UI

| 用語 | 説明 | SSOT |
|------|------|------|
| Sage Terrace | チャット UI デザイン体系 | 09-glossary |
| DeepL | GCP 本番翻訳 | 01-cross-cloud |
| Amazon Translate | AWS 翻訳 | 01-cross-cloud |
| Google Cloud TTS | GCP 読み上げ | 01-cross-cloud |
| Amazon Polly | AWS 読み上げ | 01-cross-cloud |
| concierge_i18n | メタ回答翻訳 | services/ |

## F. 法務・公開 doc

| 用語 | 説明 | SSOT |
|------|------|------|
| β版 / 試験運用 | 限定公開フェーズ | 11-app-mission |
| 免責事項 | 非診断・参考案内 | public/免責 |
| プライバシーポリシー | 個人情報取扱 | public/プライバシー |
| セルフメディケーション | 開発目的キーワード | 11-app-mission |
| generate_doc_answer_text | 法務 doc 全文参照回答 | concierge_agent |

## G. 観測・運用

| 用語 | 説明 | SSOT |
|------|------|------|
| Cloud Logging | GCP ログ | 07-observability |
| CloudWatch | AWS ログ | 07-observability |
| /health | ヘルスチェック | 07-observability |
| LINE Webhook | LINE Messaging 連携 | 06-line-gcp-path |

## H. フラグ・設定（回答では env 名を開示しない）

| 内部概念 | ユーザー向け言い換え |
|----------|---------------------|
| CHAT_PIPELINE_V2 | 新しい会話パイプライン |
| ROUTING_CONCIERGE_INTENT | 技術 FAQ の意図ルーティング |
| CONCIERGE_RAG_PROVIDER | ナレッジ検索方式（Local / Bedrock） |

（計 52 語 — 追加は 09-glossary と同期）
