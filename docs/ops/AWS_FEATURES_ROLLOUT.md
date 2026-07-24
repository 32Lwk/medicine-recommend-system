# AWS 機能ロールアウト（env ゲート）

GCP 本番 `medicine.yutok.dev` は **env 未設定 = 現状維持**（DeepL / OpenAI / Web Speech）。  
AWS ステージング `aws.medicine.yutok.dev` の ECS タスク定義のみで以下を設定する。

正本: [config/aws_features.py](../../config/aws_features.py)

## 環境変数一覧

| 変数 | GCP 既定 | AWS ステージング例 |
|------|----------|-------------------|
| `TRANSLATION_PROVIDER` | （未設定→deepl） | `translate` |
| `CONCIERGE_RAG_PROVIDER` | `local` | `bedrock_kb`（Phase 3） |
| `MEDICINE_RAG_PROVIDER` | `local` | `bedrock_kb`（Ask / Explanation RAG） |
| `BEDROCK_KB_ID` | 未設定 | Concierge Managed KB `2CNAGQ2V4P` |
| `BEDROCK_MEDICINE_KB_ID` | 未設定 | 医薬品 Managed KB `30BCEJCJHA` |
| `BEDROCK_KB_SEARCH_MODE` | `managed` | 旧 Customer-managed のみ `vector` |
| `TTS_PROVIDER` | `webspeech` | `polly`（Phase 2b） |
| `COMPREHEND_MEDICAL_ENABLED` | false | `true`（Phase 3） |
| `MEDICINE_IMAGE_CDN_BASE` | （任意）共通可 | `https://images.yutok.dev/otc/`（**GCP 本番も cloudbuild.yaml で設定**） |
| `STATIC_CDN_BASE_URL` | 未設定 | CloudFront URL（Phase 1） |
| `APP_ENV` | 未設定（本番相当） | dev 検証時 `development`（[set-dev-app-env.sh](../../scripts/set-dev-app-env.sh)） |
| `LOCAL_STATIC_ASSETS` | 未設定 | `1` で全ホスト `/static/` 強制（通常は不要） |
| `REDIS_URL` | 未設定 | ElastiCache（Phase 4） |
| `PERSONALIZE_CAMPAIGN_ARN` | 未設定 | Phase 4 |
| `PERSONALIZE_TRACKING_ID` | 未設定 | Phase 4（put_events 用） |

## ECS Secrets 投入

```bash
# AWS_PROFILE は scripts/lib/aws_common.sh で medicine-recommend-dev が既定
cp .env.example .env   # AWS 向け値を記入
./scripts/setup-aws-ecs-secrets.sh .env
```

## ロールバック

ECS タスク定義から AWS 向け env を削除するか、明示的に:

```
TRANSLATION_PROVIDER=deepl
CONCIERGE_RAG_PROVIDER=local
MEDICINE_RAG_PROVIDER=local
TTS_PROVIDER=webspeech
COMPREHEND_MEDICAL_ENABLED=false
```

→ `./scripts/tune-aws-ecs-performance.sh` 同様に `force-new-deployment`。

## 静的アセット CDN と localhost

`config/static_assets.py` + [config/aws_features.py](../../config/aws_features.py):

| 条件 | JS/CSS の URL |
|------|----------------|
| リクエスト Host が `localhost` / `127.0.0.1` | アプリ同梱 **`/static/`**（middleware が `prefer_local_static` を設定） |
| `LOCAL_STATIC_ASSETS=1` | 全ホストで `/static/` |
| 上記以外（`aws.medicine.yutok.dev` 含む） | **`STATIC_CDN_BASE_URL`**（CloudFront） |

**注意**: `APP_ENV=development` だけでは CDN バイパスしない。dev ホストでも CloudFront を使い、localhost 開発時のみ最新 JS を即反映する。

## dev 環境の APP_ENV 統一

Concierge の技術参照や UI の `data-env` 表示を dev 向けに揃える:

```bash
./scripts/set-dev-app-env.sh       # AWS ECS + GCP Cloud Run
./scripts/set-dev-app-env.sh aws   # AWS のみ
```

AWS 単体: `APP_ENV=development ./scripts/update-aws-express-env.sh`

## Admin IAM

初回セットアップ用ポリシー: [AWS_IAM_ADMIN_POLICY.json](./AWS_IAM_ADMIN_POLICY.json)

**日常運用プロファイル** `medicine-recommend-dev` 向け:

| 操作 | 可否 |
|------|------|
| WAF / CloudFront / S3 / ElastiCache / Personalize 作成 | 可 |
| ECS Express env 更新（`update-aws-express-env.sh`） | 可 |
| ECS `register-task-definition`（PassRole） | **不可** — Express 更新スクリプトを使用 |
| IAM `CreateRole`（Bedrock KB ロール） | **不可** — Admin で事前作成 or ポリシー追加 |

Phase 1 スクリプト: [AWS_INFRA.md](./AWS_INFRA.md)

## 関連

- 検証チェックリスト: [AWS_STAGING_CHECKLIST.md](./AWS_STAGING_CHECKLIST.md)
- CodePipeline: [AWS_CODEPIPELINE.md](./AWS_CODEPIPELINE.md)
- R2 画像: [CLOUDFLARE_R2_IMAGES.md](./CLOUDFLARE_R2_IMAGES.md)
- 計画: [.cursor/plans/aws_cloudflare_一括改善_afd2b593.plan.md](../../.cursor/plans/aws_cloudflare_一括改善_afd2b593.plan.md)
