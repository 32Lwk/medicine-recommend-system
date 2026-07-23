# AWS ステージング検証チェックリスト

`aws.medicine.yutok.dev` 向け。GCP 本番 `medicine.yutok.dev` への影響がないことを必ず確認する。

## 前提（IAM 解除後）

- [x] `aws sts get-caller-identity --profile medicine-recommend-dev` が成功
- [ ] Admin に **GUI で必要な最大権限**を付与（任意 — Bedrock KB 初回は `AWS_PROFILE=admin` 推奨）
- [ ] `medicine-recommend-dev` に [AWS_IAM_MEDICINE_RECOMMEND_DEV_EXTRA.json](./AWS_IAM_MEDICINE_RECOMMEND_DEV_EXTRA.json) をアタッチ（`iam:CreateRole` / Bedrock KB CLI 用）
- [ ] Git Bash 利用時は [AWS_INFRA.md](./AWS_INFRA.md) の MSYS 注意を確認

## Secrets Manager（ECS Express）

```bash
./scripts/setup-aws-express-secrets.sh .env
```

| 確認 | 期待 |
|------|------|
| `primaryContainer.secrets` | OPENAI / DATABASE / SECRET_KEY / R2 / DEEPL / LINE 等 |
| 平文 env | 上記キーが **environment から除去** |
| `/health` | `200`（シークレット注入後も） |

## Phase 1 — インフラ

```bash
export AWS_PROFILE=medicine-recommend-dev
./scripts/setup-aws-infra.sh
```

| 確認 | コマンド / 期待 |
|------|----------------|
| CloudWatch Log Group | `/ecs/medicine-recommend` が存在 |
| ECS awslogs | タスク定義に `awslogs-group` が設定 |
| WAF | ALB に Web ACL アタッチ（Rate limit + CommonRuleSet） |
| CloudFront | `scripts/.aws-static-cdn-url` に URL が出力 |
| static S3 | `medicine-recommend-static-<account>/static/` に同期 |

ECS env 反映:

```bash
# ECS Express（推奨 — medicine-recommend-dev プロファイル）
STATIC_CDN_BASE_URL=$(cat scripts/.aws-static-cdn-url)
STATIC_CDN_BASE_URL=$STATIC_CDN_BASE_URL ./scripts/update-aws-express-env.sh

# Classic ECS + Secrets Manager（iam:PassRole 要）
./scripts/setup-aws-ecs-secrets.sh .env
```

| 確認 | 期待 |
|------|------|
| `/health` | `200` |
| static CSS | DevTools で CloudFront URL から読み込み（`STATIC_CDN_BASE_URL` 設定時） |

CodePipeline で static 同期する場合:

- [ ] CodeBuild env `SYNC_STATIC_TO_S3=true`
- [ ] CodeBuild ロールに S3 + `cloudfront:CreateInvalidation`

## Phase 2 — Translate / Polly / R2 画像

`.env` / ECS env（AWS のみ）:

```
TRANSLATION_PROVIDER=translate
TTS_PROVIDER=polly
MEDICINE_IMAGE_CDN_BASE=https://images.yutok.dev/otc/
```

| 確認 | 期待 |
|------|------|
| 英語 UI 翻訳 | Amazon Translate 経由（ログに Translate 完了） |
| TTS | `POST /api/tts` が 200 + audio/mpeg（Polly ON 時） |
| OTC 画像 | `https://images.yutok.dev/otc/{id}.webp` が 200（オブジェクトあり） |
| 404 画像 | プレースホルダー表示（`onerror`） |

## Phase 3 — Bedrock KB + Comprehend

```bash
# 1. OpenSearch コレクション + network/data policy
AWS_PROFILE=admin ./scripts/setup-aws-opensearch-kb-collection.sh
./scripts/update-aoss-kb-network-policy.sh   # bedrock.amazonaws.com（401 対策）

# 2. vector index（opensearch-py 要）
py -3.11 -m pip install opensearch-py
AWS_PROFILE=admin py -3.11 scripts/create_aoss_vector_index.py

# 3. KB 作成 + ingestion
AWS_PROFILE=admin ./scripts/create-aws-bedrock-kb.sh
AWS_PROFILE=admin ./scripts/sync-aws-bedrock-kb-ingestion.sh   # 429 時は数分後に再実行

./scripts/sync-concierge-kb-to-s3.sh
```

ECS env（反映済み 2026-07-23）:

```
CONCIERGE_RAG_PROVIDER=bedrock_kb
BEDROCK_KB_ID=4PEWLBZGTH
COMPREHEND_MEDICAL_ENABLED=true
```

| 確認 | 期待 |
|------|------|
| Concierge meta 質問 | KB 引用付き回答（architecture / app_about 等） |
| 公式 doc 回答 | **md のみ**（privacy/terms に KB 混ぜない） |
| Web 症状 NLU | structured log に `comprehend_medical` |
| LINE セッション | Comprehend **未使用** |

## Phase 4 — Redis + Personalize

```bash
./scripts/setup-aws-elasticache.sh
./scripts/setup-aws-personalize.sh
```

ECS env:

```
REDIS_URL=rediss://...
PERSONALIZE_CAMPAIGN_ARN=...
PERSONALIZE_TRACKING_ID=...
```

| 確認 | 期待 |
|------|------|
| Translate 2 回目 | Redis 有効時に高速化 |
| Personalize | キャンペーン ACTIVE 後に順序変化（冷スタート時はルール順） |

## GCP 本番回帰（env 未設定のまま）

| 確認 | 期待 |
|------|------|
| `/health` | 変化なし |
| 翻訳 | DeepL（Translate ログなし） |
| TTS | Web Speech API |
| Concierge | ローカル KB / md のみ |
| LINE Webhook | 既存挙動 |

## ロールバック

[AWS_FEATURES_ROLLOUT.md](./AWS_FEATURES_ROLLOUT.md) のロールバック env を ECS に設定 → `force-new-deployment`。

```
TRANSLATION_PROVIDER=deepl
CONCIERGE_RAG_PROVIDER=local
TTS_PROVIDER=webspeech
COMPREHEND_MEDICAL_ENABLED=false
# REDIS_URL / PERSONALIZE_* / BEDROCK_KB_ID / STATIC_CDN_BASE_URL を削除
```

## 既知のブロッカー（2026-07-23）

| 項目 | 状態 |
|------|------|
| Admin IAM セルフロックアウト | WAF / CloudFront 作成不可。ポリシー適用後に再実行 |
| Bedrock KB | OpenSearch Serverless コレクション要。`OPENSEARCH_COLLECTION_ARN` 未設定時は手動 |
| Personalize キャンペーン | 学習データ + solution version 作成後に ACTIVE |
