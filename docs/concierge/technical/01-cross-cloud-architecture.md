# クロスクラウド構成 — medicine-recommend

> インフラ・環境構成の SSOT。Concierge RAG 索引は [12-technical-faq-rag.md](12-technical-faq-rag.md)、横断 FAQ は [../rag/technical-infra-rag.md](../rag/technical-infra-rag.md)。

## 本ツールの位置づけ

- **用途**: 一般用医薬品（市販薬）の症状相談チャット（β版・限定試験運用）
- **医療機関ではない**: 診断・処方は行わない。市販薬候補は **ルールベーススコアリング** で選定し、LLM が薬名を自由創作しない
- **マルチエージェント**: TriageAgent → PhysicalOrchestrator / ConciergeAgent / StoreInquiryAgent 等が IntentRouter と orchestrator で振り分け

### 例外・境界・よくある誤解

- **誤解**: 「AWS 版と GCP 版で別アプリ」→ **同一リポジトリ・同一 Docker イメージ**。クラウド固有の差分はホスティングと機能フラグ（翻訳/TTS/RAG プロバイダ）のみ
- **境界**: 症状・薬選びは PhysicalOrchestrator、技術・規約・挨拶は ConciergeAgent — インフラ構成と混同しない（[10-agent-routing-rationale.md](10-agent-routing-rationale.md)）
- **β表記**: 限定試験運用中であり、医療機関・診断サービスではない点を常に明示する

---

## Q: 本番とステージングでクラウドが分かれている理由は

<!-- rag-keywords: クロスクラウド GCP AWS 本番 ステージング 分けた 理由 なぜ 構成 -->

**回答要点**

- **What**: 本番 = GCP Cloud Run（`medicine.yutok.dev`）、ステージング = AWS ECS Express（`aws.medicine.yutok.dev`）
- **Why**: 本番の安定性（DeepL / Google Cloud TTS / Local RAG）を保ちつつ、AWS ネイティブ機能（Amazon Translate / Polly / Bedrock Managed KB / ElastiCache / Personalize）を安全に試験するため
- **共通**: 医薬品画像 CDN（Cloudflare R2 / `images.yutok.dev`）は両環境で同一 URL
- **原則**: GCP 本番・dev では AWS 専用機能を **有効にしない**（[08-technical-decisions.md](08-technical-decisions.md)、[docs/ops/GCP_RAG_MIGRATION_ADR.md](../../ops/GCP_RAG_MIGRATION_ADR.md) Option C）
- **関連**: [03-deployment-operations.md](03-deployment-operations.md)、[12-technical-faq-rag.md](12-technical-faq-rag.md)

### 例外・境界・よくある誤解

- **誤解**: 「ステージング = 開発者だけ」→ ステージング URL は **公開 Web** として動作し、本番と別 DB・別ログを持つ独立環境
- **誤解**: 「GCP dev と AWS ステージングが同じ役割」→ GCP dev（`medicine-recommend-dev`）は Cloud Run 上の **GCP 系 dev**、AWS ステージングは **AWS 機能試験専用**
- **境界**: 本番障害時に AWS ステージングへ切り替える **自動フェイルオーバーはない** — 意図的な分離

---

## 環境一覧（2026-07 時点）

| 環境 | URL | ホスティング | 主な AI / 翻訳 / TTS |
|------|-----|-------------|----------------------|
| **GCP 本番** | medicine.yutok.dev | Google Cloud Run | OpenAI（生成）/ DeepL（翻訳）/ Google Cloud Text-to-Speech（TTS） |
| **GCP dev** | medicine-recommend-dev（Cloud Run） | Google Cloud Run | 本番と同様（Google Cloud TTS） |
| **AWS ステージング** | aws.medicine.yutok.dev | ECS Express Gateway + ALB + WAF | OpenAI（生成）/ Amazon Translate / Amazon Polly |
| **LINE** | LINE Messaging API | GCP Cloud Run 上（本番と同一アプリ） | 上記 GCP 本番と同じ |
| **画像 CDN** | images.yutok.dev/otc/ | **Cloudflare R2**（GCP/AWS 共通） | — |

**原則**: GCP 本番・dev は AWS 専用機能（Translate / Polly / Bedrock KB 等）を **有効にしない**（DeepL / Cloud Text-to-Speech / ローカル参照 RAG）。AWS ステージングのみ Translate / Polly / Bedrock Managed KB / Redis / Personalize を **試験可能**。

### 例外・境界・よくある誤解

- **誤解**: 「LINE は AWS でも動く」→ LINE Webhook は **GCP Cloud Run のみ**（[06-line-gcp-path.md](06-line-gcp-path.md)）
- **境界**: R2 画像 URL は共通だが、**チャット DB・実行ログは環境ごとに完全分離**（[04-data-security.md](04-data-security.md)）
- **例外**: ローカル開発（`localhost`）はどちらのクラウドにも属さず、アプリ同梱の静的ファイルと Docker Postgres を使用

---

## Q: GCP と AWS で翻訳・読み上げサービスが違う理由

<!-- rag-keywords: 翻訳 DeepL Amazon Translate TTS Polly Google Cloud Text-to-Speech 違う 理由 -->

**回答要点**

- **GCP 本番 / dev**: 翻訳 = DeepL（既存契約・品質）、読み上げ = Google Cloud Text-to-Speech
- **AWS ステージング**: 翻訳 = Amazon Translate、読み上げ = Amazon Polly
- **Why**: 各クラウドのネイティブサービスで統合試験し、本番の DeepL / Google TTS 安定性を維持
- **障害時**: GCP 本番は読み上げをブラウザ Web Speech API に戻せる（運用手順は [03-deployment-operations.md](03-deployment-operations.md) ロールバック節）
- **関連**: [docs/ops/AWS_FEATURES_ROLLOUT.md](../../ops/AWS_FEATURES_ROLLOUT.md)

### 例外・境界・よくある誤解

- **誤解**: 「Translate の方が DeepL より本番向き」→ 本番は **意図的に DeepL 固定**。Translate は AWS 試験用
- **境界**: 翻訳/TTS プロバイダは **サーバー側設定** — 利用者が UI から切り替えるものではない
- **例外**: `localhost` 開発時は CDN をバイパスし、アプリ同梱 `/static/` を配信（dev ホスト名だけでは CDN バイパスにならない）

---

## 翻訳・TTS（環境別）

| 環境 | 翻訳 | 読み上げ（TTS） |
|------|------|----------------|
| GCP 本番 | DeepL | Google Cloud Text-to-Speech |
| GCP dev | DeepL | Google Cloud Text-to-Speech |
| AWS ステージング | Amazon Translate | Amazon Polly |
| ローカル | DeepL（キー設定時） | Web Speech API または Google TTS |

**Why 分離**: 各クラウドのネイティブサービスで試験しつつ本番安定を確保。詳細は [docs/ops/CLOUD_RUN_LLM_ENV.md](../../ops/CLOUD_RUN_LLM_ENV.md)。

---

## Q: チャットリクエストはアプリ内でどう処理されるか

<!-- rag-keywords: リクエスト フロー IntentRouter PhysicalOrchestrator ConciergeAgent パイプライン -->

**回答要点**

- **入口**: ブラウザまたは LINE → FastAPI（`main.py`）→ Chat Pipeline v2（`chat_post_pipeline.py`）
- **分類**: IntentRouter（LLM 構造化 + 決定論ゲート）が Physical / Concierge / Store / Emotional 等に振り分け
- **Physical 経路**: 症状 NLU → ルールベース CSV スコアリング → sage_reco カード（LLM は薬名を決定しない）
- **Concierge 経路**: 挨拶・技術 FAQ・更新履歴 — 本 SSOT 群と Local RAG / Bedrock KB を参照
- **永続化**: セッション・メッセージ → PostgreSQL（本番 Neon / ローカル Docker Postgres）
- **UI**: Sage Terrace（`static/css/sage_terrace.css` + status カード）
- **関連**: [02-chat-pipeline-agents.md](02-chat-pipeline-agents.md)、[10-agent-routing-rationale.md](10-agent-routing-rationale.md)

### 例外・境界・よくある誤解

- **誤解**: 「Concierge が薬を推奨する」→ 症状・市販薬相談は **必ず Physical 経路**。Concierge は案内・FAQ のみ
- **境界**: Chat Pipeline v2 が本番デフォルト。レガシー分岐は縮小中（[05-chat-pipeline-v2-flags.md](05-chat-pipeline-v2-flags.md)）
- **例外**: LINE は Web と同一パイプラインだが、Flex 文字数上限で長文は Web 誘導（[06-line-gcp-path.md](06-line-gcp-path.md)）

---

## リクエストの流れ（Web チャット）

1. ブラウザ → FastAPI POST `/` または Chat Pipeline v2 経路
2. **IntentRouter** が Other / Physical / Concierge / Store 等に分類
3. **PhysicalOrchestrator**: 症状 NLU → ルールベース推奨（CSV スコア）→ sage_reco カード
4. **ConciergeAgent**: 挨拶・技術 FAQ・更新履歴・オペレーター案内（本ドキュメント群を参照）
5. セッション・ログ: PostgreSQL + Cloud Logging / CloudWatch
6. 応答 UI: Sage Terrace

---

## Q: LINE はどのクラウドで動作するか

<!-- rag-keywords: LINE Webhook GCP Cloud Run AWS どこ ホスティング Messaging API -->

**回答要点**

- **What**: LINE Messaging API Webhook → **GCP Cloud Run** 上の `medicine.yutok.dev` と **同一アプリ**
- **Why**: 本番利用者（LINE）の安定性を GCP 本番に集約。AWS ステージングは Web 試験専用
- **処理**: 署名検証 → 非同期 `handle_chat_post_async` → Chat Pipeline v2 / Concierge / Physical（Web と同一経路）
- **画像**: OTC 画像 URL のみ Cloudflare R2 共通（`images.yutok.dev/otc/`）
- **関連**: [06-line-gcp-path.md](06-line-gcp-path.md)

### 例外・境界・よくある誤解

- **誤解**: 「LINE だけ AWS Translate を使う」→ LINE も **DeepL + GCP 本番設定** を継承
- **境界**: AWS ステージング URL を LINE Webhook に設定しない運用（本番 GCP のみ）

---

## Q: AWS ステージングで追加試験できるコンポーネントは何か

<!-- rag-keywords: AWS ステージング Bedrock KB CloudFront ElastiCache Personalize Comprehend WAF -->

**回答要点**

- **静的 CDN**: S3 + CloudFront — push 毎 CodeBuild で `static/` 同期（[docs/ops/AWS_INFRA.md](../../ops/AWS_INFRA.md)）
- **Concierge / Medicine RAG**: Bedrock Managed KB（Concierge `2CNAGQ2V4P`、Medicine `30BCEJCJHA`）— GCP 本番は Local RAG 維持（ADR Option C）
- **キャッシュ**: ElastiCache Serverless（Translate / KB retrieve キャッシュ）
- **NLU 補助（任意）**: Amazon Comprehend Medical — 症状エンティティ抽出
- **レコメンド試験（任意）**: Amazon Personalize
- **セキュリティ**: WAF（Rate limit + CommonRuleSet）→ ALB
- **CI/CD**: GitHub main → CodeStar Connection → CodeBuild → ECR → ECS force redeploy → smoke
- **関連**: [03-deployment-operations.md](03-deployment-operations.md)、[docs/ops/AWS_BEDROCK_KB.md](../../ops/AWS_BEDROCK_KB.md)

### 例外・境界・よくある誤解

- **誤解**: 「AWS ステージング = 常に Bedrock KB」→ コード既定は **Local RAG**。Bedrock KB は ECS Express 設定で **試験 ON** にした場合（Express env 更新スクリプトの既定は Bedrock KB 向け）
- **誤解**: 「Bedrock KB が本番にもすぐ入る」→ [docs/ops/GCP_RAG_MIGRATION_ADR.md](../../ops/GCP_RAG_MIGRATION_ADR.md) Option C により **GCP 本番 Bedrock 切替は保留**
- **境界**: 旧 Customer-managed KB `4PEWLBZGTH` は **非推奨**（Titan Embed 429 問題）

---

## AWS ステージング追加コンポーネント

- **static/**: S3 + CloudFront CDN — push 毎 CodeBuild で同期（変更検知時のみ最適化可）
- **Concierge RAG**: Local RAG（コード既定）または Bedrock Managed KB `2CNAGQ2V4P`（ステージング試験）
- **Medicine RAG**: Local RAG または Bedrock Managed KB `30BCEJCJHA`（Ask / Explanation 層）
- **キャッシュ**: ElastiCache Serverless（Translate / retrieve キャッシュ）
- **NLU 補助（任意）**: Amazon Comprehend Medical
- **CI/CD**: GitHub main → CodeStar Connection → CodeBuild（`buildspec.yml`）→ ECR → ECS force redeploy → smoke（Translate / Polly / health）
- **Secrets**: AWS Secrets Manager → ECS Express `primaryContainer.secrets`

---

## Q: 医薬品画像 CDN はなぜ GCP/AWS 共通か

<!-- rag-keywords: 画像 CDN Cloudflare R2 images.yutok.dev 共通 OTC 医薬品 -->

**回答要点**

- **What**: `https://images.yutok.dev/otc/{slug}.webp` — Cloudflare R2 上の WebP 画像
- **Why**: クラウドをまたいで同一 OTC 画像 URL を使い、推奨カード UI を統一。R2 は GCP/AWS どちらからも HTTP で参照可能
- **同期**: `scripts/sync_otc_images_from_matsukiyo.py` 等で R2 へ一括アップロード
- **アプリ**: `src/services/medicine_image_urls.py` + カード `onerror` プレースホルダー
- **関連**: [docs/ops/CLOUDFLARE_R2_IMAGES.md](../../ops/CLOUDFLARE_R2_IMAGES.md)、[03-deployment-operations.md](03-deployment-operations.md)

### 例外・境界・よくある誤解

- **誤解**: 「画像も AWS S3」→ 医薬品画像は **R2 専用**。AWS S3/CloudFront は **JS/CSS 静的アセット**用
- **境界**: 画像 CDN だけがクロスクラウド共通 — **チャットデータは共有しない**

---

## Q: データはどこに保存されるか

<!-- rag-keywords: データ 保存 PostgreSQL Neon CloudWatch Cloud Logging ログ セッション -->

**回答要点**

- **チャット**: PostgreSQL（本番 Neon / AWS ステージングは別インスタンス / ローカル Docker Postgres）
- **実行ログ**: Cloud Logging（GCP）/ CloudWatch Logs `/ecs/medicine-recommend`（AWS）
- **分析用**: リポジトリ `log/`（開発・検証用 JSONL — 本番利用者データはマスク方針に従う）
- **OTC マスタ**: `data/` CSV（推奨時に参照、KB ビルドにも同期可）
- **Secrets**: GCP Secret Manager / AWS Secrets Manager — 利用者回答には **設定名を出さない**
- **関連**: [04-data-security.md](04-data-security.md)、[07-observability-ops.md](07-observability-ops.md)

### 例外・境界・よくある誤解

- **誤解**: 「GCP と AWS で同じ DB」→ **完全に別インスタンス**。データ混在なし
- **境界**: `/health` は DB 非依存の軽量プローブ（起動確認用）。DB 接続状態は別エンドポイント（管理画面等）

---

## データの保存先

| 種別 | GCP 本番 | AWS ステージング | ローカル |
|------|----------|------------------|----------|
| チャットセッション | Neon PostgreSQL | 別 PostgreSQL | Docker Postgres |
| 実行ログ | Cloud Logging | CloudWatch `/ecs/medicine-recommend` | `log/` |
| OTC マスタ | `data/` CSV | 同一 CSV（イメージ同梱） | 同一 |
| 医薬品画像 | R2 CDN | R2 CDN | R2 CDN |

---

## 関連ドキュメント（リポジトリ内）

- [02-chat-pipeline-agents.md](02-chat-pipeline-agents.md) — パイプライン・エージェント
- [03-deployment-operations.md](03-deployment-operations.md) — デプロイ・CI/CD
- [04-data-security.md](04-data-security.md) — セキュリティ境界
- [06-line-gcp-path.md](06-line-gcp-path.md) — LINE 経路
- [07-observability-ops.md](07-observability-ops.md) — ヘルス・ログ
- [08-technical-decisions.md](08-technical-decisions.md) — 技術選定 Why
- [../rag/technical-infra-rag.md](../rag/technical-infra-rag.md) — インフラ横断 FAQ
- `docs/ops/AWS_FEATURES_ROLLOUT.md` — 機能ゲート一覧（運用者向け）
- `docs/ops/AWS_INFRA.md` — WAF / CloudFront / S3
- `docs/ops/AWS_CODEPIPELINE.md` — デプロイパイプライン
- `docs/ops/LOCAL_RAG.md` — Local RAG 運用
- `CHANGELOG.md` — 機能追加履歴
