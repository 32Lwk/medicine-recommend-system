# クロスクラウド構成 — medicine-recommend

## 本ツールの位置づけ

- **用途**: 一般用医薬品（市販薬）の症状相談チャット（β版・限定試験運用）
- **医療機関ではない**: 診断・処方は行わない。市販薬候補は **ルールベーススコアリング** で選定し、LLM が薬名を自由創作しない
- **マルチエージェント**: TriageAgent → PhysicalOrchestrator / ConciergeAgent / StoreInquiryAgent 等が IntentRouter と orchestrator で振り分け

## 環境一覧（2026-07 時点）

| 環境 | URL | ホスティング | 主な AI/翻訳/TTS |
|------|-----|-------------|------------------|
| **GCP 本番** | medicine.yutok.dev | Google Cloud Run | OpenAI（生成）/ DeepL（翻訳）/ Google Cloud Text-to-Speech（TTS） |
| **GCP dev** | medicine-recommend-dev（Cloud Run） | Google Cloud Run | 本番と同様（`TTS_PROVIDER=google`） |
| **AWS ステージング** | aws.medicine.yutok.dev | ECS Express Gateway + ALB + WAF | OpenAI（生成）/ Amazon Translate / Amazon Polly |
| **LINE** | LINE Messaging API | GCP Cloud Run 上（本番と同一アプリ） | 上記 GCP 本番と同じ |
| **画像 CDN** | images.yutok.dev/otc/ | **Cloudflare R2**（GCP/AWS 共通） | — |

**原則**: GCP 本番・dev は AWS 専用機能（Translate / Polly / Bedrock KB 等）を **有効にしない**（DeepL / Cloud Text-to-Speech / ローカル参照）。AWS ステージングのみ Translate / Polly / Bedrock KB / Redis / Personalize を利用。

## リクエストの流れ（Web チャット）

1. ブラウザ → FastAPI（`main.py`）POST `/` または Chat Pipeline v2 経路
2. **IntentRouter**（LLM + 決定論ゲート）が Other / Physical / Concierge / Store 等に分類
3. **PhysicalOrchestrator**: 症状 NLU → ルールベース推奨（CSV スコア）→ sage_reco カード
4. **ConciergeAgent**: 挨拶・技術 FAQ・更新履歴・オペレーター案内（本ドキュメント群を参照）
5. セッション・ログ: PostgreSQL（本番 Neon / ローカル Docker Postgres）
6. 応答 UI: Sage Terrace（`static/css/sage_terrace.css` + status カード）

## AWS ステージング追加コンポーネント

- **static/**: S3 + CloudFront CDN — push 毎 CodeBuild で同期
- **Concierge RAG**: Bedrock Knowledge Base — `docs/concierge/` 等を S3 経由で ingestion（準備中の場合あり）
- **キャッシュ**: ElastiCache Serverless（Translate / KB retrieve）
- **NLU 補助（任意）**: Amazon Comprehend Medical — 症状エンティティ抽出（NLU 補助・ログ分析）
- **CI/CD**: GitHub main → CodeStar Connection → CodeBuild（`buildspec.yml`）→ ECR → ECS force redeploy → smoke（Translate/Polly/health）
- **Secrets**: Secrets Manager → ECS Express `primaryContainer.secrets`

## データの保存先

- チャットセッション・メッセージ履歴: PostgreSQL
- 実行ログ: Cloud Logging（GCP）/ CloudWatch Logs `/ecs/medicine-recommend`（AWS）
- 分析用 JSONL: リポジトリ `log/`（開発・検証用）
- OTC 医薬品マスタ: `data/` CSV（推奨時に参照、KB にも同期可）

## 関連ドキュメント（リポジトリ内）

- `docs/ops/AWS_FEATURES_ROLLOUT.md` — env ゲート一覧
- `docs/ops/AWS_INFRA.md` — WAF / CloudFront / S3
- `docs/ops/AWS_CODEPIPELINE.md` — デプロイパイプライン
- `CHANGELOG.md` — 機能追加履歴（Concierge doc_changelog が要約表示）
