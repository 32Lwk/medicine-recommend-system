# 用語集 — Concierge 技術 FAQ（ユーザー向け SSOT）

| 用語 | 本プロジェクトでの意味 |
|------|------------------------|
| **SSE** | Server-Sent Events。回答生成を段階的にブラウザへ配信する仕組み |
| **IntentRouter** | ユーザー発話を Physical / Concierge / Store 等に振り分ける LLM+ルールの入口 |
| **Chat Pipeline v2** | 本番デフォルトの会話処理パイプライン（triage → orchestrator → handler） |
| **TriageAgent** | 入力を分類し適切な担当へ渡すエージェント |
| **PhysicalOrchestrator** | 症状解析とルールベース市販薬推奨を行うエージェント |
| **ConciergeAgent** | 挨拶・技術 FAQ・アプリ説明・更新履歴案内 |
| **Local RAG** | リポジトリ内ドキュメントから BM25+embedding で関連段落を検索 |
| **ハイブリッド RAG** | BM25（キーワード）と embedding（意味類似）を合成した retrieve |
| **Bedrock KB** | AWS マネージドナレッジベース（ステージング比較用。本番 GCP は Local RAG） |
| **クロスクラウド** | GCP 本番と AWS ステージングで役割分担した構成 |
| **Cloud Run** | GCP 本番の HTTP ホスティング（medicine.yutok.dev） |
| **ECS Fargate** | AWS ステージングのコンテナ実行基盤 |
| **Express Gateway** | AWS ステージングの ECS 向け HTTP 入口（ALB + WAF 配下） |
| **Neon** | サーバーレス PostgreSQL。本番のセッション・メッセージ履歴保存 |
| **Cloudflare R2** | 医薬品画像 CDN（images.yutok.dev/otc/）のオブジェクトストレージ |
| **CloudFront** | AWS ステージングの static アセット（JS/CSS）CDN |
| **ElastiCache Serverless** | AWS ステージングの Redis キャッシュ（Translate / retrieve 等） |
| **ルールベース推奨** | CSV とスコアリングで市販薬候補を選定（LLM は薬名を決めない） |
| **OTC** | Over-The-Counter。一般用医薬品（市販薬） |
| **Comprehend Medical** | AWS 医療 NLP。症状・薬剤エンティティ抽出（ステージング任意） |
| **Personalize** | AWS 推奨ランキング補助。表示順 rerank・イベント蓄積（ステージング） |
| **DeepL** | GCP 本番の翻訳サービス |
| **Amazon Translate** | AWS ステージングの翻訳サービス |
| **Google Cloud TTS** | GCP 本番の読み上げ（Text-to-Speech） |
| **Amazon Polly** | AWS ステージングの読み上げ |
| **Sage Terrace** | 本アプリのチャット UI デザイン体系 |
| **β版** | 限定試験運用版。専門関係者向けフィードバック収集が目的 |
| **SSOT** | Single Source of Truth。技術 FAQ の唯一の根拠ドキュメント |
| **direct intent** | 法務 doc 等を RAG 経由せず md 全文参照する意図分類 |
| **doc_changelog** | 更新履歴 digest を参照する Concierge 意図 |
| **GitHub origin** | 正本リポジトリ（PR / CI / デプロイ） |
| **GitLab mirror** | バックアップミラー（障害時フェイルオーバー用） |
| **PMDA / #7119** | 医薬品に関する相談窓口（公開 doc 参照） |
| **セルフメディケーション** | 開発目的キーワード。市販薬の自己選択支援 |
| **/health** | 稼働状態・git_commit を返す公開ヘルスチェック |
| **meta_triage** | Concierge 向けメタ意図（技術 FAQ / 挨拶 / 更新履歴等）の LLM 分類 |

詳細リサーチ: `research/glossary-research.md`
