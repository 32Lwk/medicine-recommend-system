# インフラ・デプロイ・監視 — RAG 横断 FAQ

> 01 / 03 / 07 を横断する **インフラ・デプロイ・ヘルス・CI/CD** 専用 RAG SSOT。  
> 各セクションは **想定質問 + キーワード + 回答要点**。利用者向け回答では設定変数名を出さない。  
> 詳細 SSOT: [01-cross-cloud-architecture.md](../technical/01-cross-cloud-architecture.md)、[03-deployment-operations.md](../technical/03-deployment-operations.md)、[07-observability-ops.md](../technical/07-observability-ops.md)

---

## Q: 本番 URL とステージング URL は何か

<!-- rag-keywords: URL 本番 ステージング medicine.yutok.dev aws.medicine.yutok.dev アドレス -->

**回答要点**

- **GCP 本番**: `https://medicine.yutok.dev` — Cloud Run、DeepL + Google TTS + Local RAG
- **AWS ステージング**: `https://aws.medicine.yutok.dev` — ECS Express、Translate + Polly + Bedrock KB 試験
- **GCP dev**: Cloud Run サービス `medicine-recommend-dev`（本番と同系統設定）
- **画像 CDN**: `https://images.yutok.dev/otc/` — 両環境共通（Cloudflare R2）
- **LINE**: 本番 GCP アプリと同一（Webhook は GCP Cloud Run）
- **関連**: [01-cross-cloud-architecture.md](../technical/01-cross-cloud-architecture.md)

---

## Q: なぜ GCP 本番と AWS ステージングに分かれているか

<!-- rag-keywords: クロスクラウド 分離 理由 GCP AWS 本番 ステージング -->

**回答要点**

- **Why**: 本番安定（DeepL / Google TTS / Local RAG）と AWS ネイティブ試験（Translate / Polly / Bedrock KB / ElastiCache）の両立
- **同一コードベース**: Docker イメージは共通。差分はホスティングと機能プロバイダ設定のみ
- **データ分離**: DB・ログは環境ごとに完全別。混在しない
- **ADR**: GCP 本番 Bedrock 切替は Option C で保留（[docs/ops/GCP_RAG_MIGRATION_ADR.md](../../ops/GCP_RAG_MIGRATION_ADR.md)）
- **関連**: [08-technical-decisions.md](../technical/08-technical-decisions.md)

---

## Q: GitHub push から AWS ステージング反映までの流れ

<!-- rag-keywords: デプロイ 流れ CodePipeline CodeBuild ECS push main 反映 時間 -->

**回答要点**

- **Source**: GitHub `main` → CodeStar Connection → CodePipeline `medicine-recommend-main`
- **Build**: CodeBuild — Docker build → ECR push → ECS force redeploy
- **post_build**: commit 待ち → 条件付き static/KB sync → SSOT 検証 → smoke
- **目安**: backend のみ変更 ~5 分で反映、Pipeline 完了 ~7 分（2026-07 高速化後）
- **確認**: `/health` の `git_commit`
- **関連**: [03-deployment-operations.md](../technical/03-deployment-operations.md)

---

## Q: GCP 本番へのデプロイはどうトリガーされるか

<!-- rag-keywords: GCP Cloud Run デプロイ Cloud Build トリガー GitHub -->

**回答要点**

- **トリガー**: GitHub `main` push → `cloudbuild.yaml` → Cloud Run
- **正本**: GitHub `32Lwk/medicine-recommend-system` — GitLab push だけでは走らない
- **確認**: `/health` の `git_commit`、Cloud Run revision
- **設定**: AWS 専用機能は本番 Cloud Run に **含めない**
- **関連**: [03-deployment-operations.md](../technical/03-deployment-operations.md)

---

## Q: デプロイが反映されたか commit で確認する方法

<!-- rag-keywords: git_commit 確認 反映 デプロイ revision health -->

**回答要点**

- **公開 API**: `GET /health` → `git_commit` が push した hash と一致
- **AWS 自動**: CodeBuild `wait-staging-health-commit.sh` が同一確認
- **CANARY 中**: 短時間 commit が混在する場合あり — 再確認で安定化を待つ
- **利用者向け**: commit は公開情報として回答可（[00-disclosure-policy.md](../technical/00-disclosure-policy.md)）
- **関連**: [07-observability-ops.md](../technical/07-observability-ops.md)

---

## Q: `/health` と `/health/aws` の違い

<!-- rag-keywords: health health/aws ヘルスチェック 違い 機能 確認 -->

**回答要点**

- **`/health`**: 全環境共通。`status` + `git_commit` のみ。DB/LLM 非依存の軽量プローブ
- **`/health/aws`**: AWS ステージング向け機能確認 — 翻訳/TTS/KB/CDN の **利用有無**（シークレット非含有）
- **用途**: ALB/Cloud Run probe、デプロイ確認、CodeBuild smoke
- **注意**: 正しいパスは `/health` — `/helth` typo は 404
- **関連**: [07-observability-ops.md](../technical/07-observability-ops.md)

---

## Q: CodePipeline の smoke テストは何を検証するか

<!-- rag-keywords: smoke テスト Translate Polly CloudFront commit 自動 検証 -->

**回答要点**

- **毎回実行**: `scripts/aws-staging-smoke.sh`（post_build）
- **項目**: commit 一致、Amazon Translate 疎通、Polly TTS、CloudFront CSS 取得
- **失敗時**: 多くは ECS task role の IAM 不足 — デプロイ自体は成功していることが多い
- **strict 未設定**: Pipeline 警告のみ（advisory）
- **関連**: [07-observability-ops.md](../technical/07-observability-ops.md)

---

## Q: ログはどこで見られるか

<!-- rag-keywords: ログ CloudWatch Cloud Logging 確認 障害 調査 -->

**回答要点**

- **GCP 本番**: Cloud Logging
- **AWS ECS**: CloudWatch `/ecs/medicine-recommend`
- **CodeBuild**: CloudWatch `/aws/codebuild/medicine-recommend-build`
- **開発分析**: リポジトリ `log/`（JSONL・Markdown）
- **AWS 分析手順**: [docs/ops/AWS_LOG_ANALYSIS.md](../../ops/AWS_LOG_ANALYSIS.md)
- **関連**: [04-data-security.md](../technical/04-data-security.md)

---

## Q: GitHub と GitLab どちらが正本か

<!-- rag-keywords: GitHub GitLab 正本 ミラー origin CI デプロイ -->

**回答要点**

- **正本**: GitHub — PR / CI / GCP 本番 / AWS CodePipeline
- **ミラー**: GitLab — バックアップ・GitHub 障害時フェイルオーバー
- **必須 push**: `origin main`（GitHub）
- **GitLab CI**: 存在するが GitHub 復旧後 **停止**（デプロイには不要）
- **関連**: [docs/ops/GITLAB_TEMPORARY_MIGRATION.md](../../ops/GITLAB_TEMPORARY_MIGRATION.md)

---

## Q: AWS ステージングの WAF と CDN 構成

<!-- rag-keywords: WAF CloudFront S3 CDN static セキュリティ Rate limit -->

**回答要点**

- **WAF**: ALB に Web ACL — Rate limit（2000/5分/IP）+ AWS CommonRuleSet
- **static CDN**: S3 + CloudFront — JS/CSS は CloudFront URL から配信
- **同期**: CodeBuild post_build で `static/` 変更時に S3 sync + invalidation
- **localhost**: アプリ同梱 `/static/`（CDN バイパス）。dev ホスト名だけではバイパスにならない
- **関連**: [docs/ops/AWS_INFRA.md](../../ops/AWS_INFRA.md)

---

## Q: 医薬品画像 CDN（R2）の仕組み

<!-- rag-keywords: R2 Cloudflare 画像 OTC images.yutok.dev CDN 共通 -->

**回答要点**

- **URL**: `https://images.yutok.dev/otc/{slug}.webp`
- **Why 共通**: GCP/AWS で同一 OTC 画像 URL — 推奨カード UI 統一
- **同期**: `scripts/sync_otc_images_from_matsukiyo.py` 等
- **注意**: R2 = 医薬品画像、S3/CloudFront = アプリ JS/CSS — **別ストレージ**
- **関連**: [docs/ops/CLOUDFLARE_R2_IMAGES.md](../../ops/CLOUDFLARE_R2_IMAGES.md)

---

## Q: Bedrock Knowledge Base の二系統（Concierge / Medicine）

<!-- rag-keywords: Bedrock KB Dual Concierge Medicine Managed KB ID -->

**回答要点**

- **Concierge** `2CNAGQ2V4P`: 技術 FAQ・運用 SSOT
- **Medicine** `30BCEJCJHA`: Ask / Explanation RAG
- **GCP 本番**: Local RAG 維持（Bedrock 本番切替保留）
- **AWS staging**: Bedrock 試験可能。ingestion は S3 sync → 非同期 job
- **旧 KB** `4PEWLBZGTH`: 非推奨
- **関連**: [03-deployment-operations.md](../technical/03-deployment-operations.md)

---

## Q: Local RAG と Bedrock KB の使い分け

<!-- rag-keywords: Local RAG Bedrock 使い分け GCP AWS 既定 BM25 embedding -->

**回答要点**

- **Local RAG**: リポジトリ内文書を BM25 + embedding ハイブリッド — **コード既定**
- **GCP 本番**: 常に Local RAG
- **AWS staging**: Local RAG または Bedrock Managed KB
- **Why Local**: OpenSearch OCU 回避、クロスクラウド同一実装、本番リスク最小
- **RAG の役割**: 説明・Q&A のみ — 薬の推奨順位はルールベース（変更しない）
- **関連**: [docs/ops/LOCAL_RAG.md](../../ops/LOCAL_RAG.md)

---

## Q: デプロイ失敗・機能障害時のロールバック

<!-- rag-keywords: ロールバック 復旧 戻す redeploy 障害 -->

**回答要点**

- **AWS 機能 OFF**: 翻訳 DeepL、TTS Web Speech、RAG Local に戻して ECS redeploy
- **GCP TTS 障害**: 読み上げを Web Speech API に戻して Cloud Run redeploy
- **イメージ**: ECR / Cloud Run の前 revision を redeploy
- **KB 障害**: Local RAG がフォールバック — 推奨機能は継続
- **関連**: [03-deployment-operations.md](../technical/03-deployment-operations.md)

---

## Q: LINE はどのインフラで動くか

<!-- rag-keywords: LINE Webhook GCP Cloud Run AWS ホスティング Messaging -->

**回答要点**

- **ホスティング**: GCP Cloud Run（`medicine.yutok.dev` と同一アプリ）
- **AWS ステージング**: Web 試験専用 — LINE Webhook は設定しない
- **処理**: Web と同一 Chat Pipeline v2 / Concierge / Physical
- **翻訳**: LINE も DeepL（GCP 本番設定）
- **関連**: [06-line-gcp-path.md](../technical/06-line-gcp-path.md)

---

## Q: チャットデータと DB は環境ごとに分かれているか

<!-- rag-keywords: データベース PostgreSQL Neon 分離 GCP AWS セッション -->

**回答要点**

- **GCP 本番**: Neon PostgreSQL
- **AWS ステージング**: 別 PostgreSQL インスタンス
- **混在なし**: クロスクラウドで DB 共有しない
- **ログも別**: Cloud Logging vs CloudWatch
- **共通**: OTC 画像 CDN URL のみ
- **関連**: [04-data-security.md](../technical/04-data-security.md)

---

## Q: PMDA データ更新から KB 反映まで

<!-- rag-keywords: PMDA CSV 更新 KB sync ingestion medicine データ -->

**回答要点**

- **正本**: `data/otc_medicine_data.csv` 等
- **live fetch**: ローカル回線のみ（CI では実行しない）
- **KB 反映**: `reflect_medicine_kb.sh` または build → S3 sync → ingestion
- **推奨順位**: CSV 更新 → PhysicalOrchestrator。KB は説明層
- **関連**: [docs/ops/PMDA_DATA_IMPORT.md](../../ops/PMDA_DATA_IMPORT.md)

---

## Q: Concierge 技術 SSOT の検証とメンテナンス

<!-- rag-keywords: SSOT verify contract 技術 FAQ メンテナンス 更新 -->

**回答要点**

- **検証**: `verify-concierge-ssot.sh`、`concierge-technical-faq-contract.sh`（40 項目）
- **CodeBuild**: post_build で SSOT 検証を並列実行
- **更新タイミング**: インフラ変更 → 該当 `.md` + `docs/ops/` 同時更新
- **Local RAG**: SSOT Markdown 更新はリポジトリ直読みで即反映。Bedrock KB は S3 sync + ingestion 待ち
- **関連**: [docs/ops/CONCIERGE_TECH_FAQ_MAINTENANCE.md](../../ops/CONCIERGE_TECH_FAQ_MAINTENANCE.md)

---

## Q: AWS ステージングの既知ブロッカーと監視注意

<!-- rag-keywords: ブロッカー 429 Titan Embed helth typo startup probe smoke FAIL -->

**回答要点**

| 事象 | 影響 | 対処 |
|------|------|------|
| Bedrock ingestion Titan Embed 429 | KB 取り込みのみ | Support クォータ。Local RAG 継続 |
| `/helth` typo | 外部モニタ 404 | `/health` に修正 |
| GCP startup probe 失敗 | 新 revision 拒否 | probe と `/health` 設計確認 |
| smoke FAIL | Pipeline 警告 | task role IAM。デプロイは成功のことが多い |

- **関連**: [07-observability-ops.md](../technical/07-observability-ops.md)

---

## Q: 手動で AWS ステージングにデプロイする方法

<!-- rag-keywords: 手動 デプロイ AWS ECS deploy-aws-ecs 更新 -->

**回答要点**

- **Pipeline なし**: `scripts/deploy-aws-ecs.sh`
- **設定更新**: `scripts/update-aws-express-env.sh`（PassRole 不要）
- **Secrets**: `scripts/setup-aws-express-secrets.sh .env`
- **Pipeline 手動起動**: `aws codepipeline start-pipeline-execution --name medicine-recommend-main`
- **プロファイル**: `medicine-recommend-dev`（`aws_common.sh` 既定）
- **関連**: [docs/ops/AWS_CODEPIPELINE.md](../../ops/AWS_CODEPIPELINE.md)

---

## Q: GCP と AWS で翻訳・読み上げが違う理由（利用者向け）

<!-- rag-keywords: 翻訳 読み上げ DeepL Translate Polly Google TTS 環境 違い -->

**回答要点**

- **GCP 本番**: DeepL 翻訳 + Google Cloud Text-to-Speech
- **AWS ステージング**: Amazon Translate + Amazon Polly
- **Why**: 各クラウドのネイティブサービスで試験し、本番品質を維持
- **利用者**: プロバイダ名を聞かれたら上記を説明。設定変数名は出さない
- **関連**: [01-cross-cloud-architecture.md](../technical/01-cross-cloud-architecture.md)

---

## 索引（SSOT ファイル）

| トピック | 正本 |
|----------|------|
| 環境構成・クロスクラウド | [01-cross-cloud-architecture.md](../technical/01-cross-cloud-architecture.md) |
| CI/CD・KB・ロールバック | [03-deployment-operations.md](../technical/03-deployment-operations.md) |
| ヘルス・ログ・smoke | [07-observability-ops.md](../technical/07-observability-ops.md) |
| 技術選定 Why | [08-technical-decisions.md](../technical/08-technical-decisions.md) |
| 横断 Why FAQ | [12-technical-faq-rag.md](../technical/12-technical-faq-rag.md) |
