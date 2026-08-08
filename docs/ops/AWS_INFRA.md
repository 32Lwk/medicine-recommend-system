# AWS Phase 1 インフラ（CloudWatch / CloudFront / Fargate Tunnel）

AWS ステージング `aws-medicine.yutok.dev` / `aws.medicine.yutok.dev` 向け。GCP 本番には **env を設定しない**。

> **2026-08-07**: ランタイム入口は **ECS Express + ALB + WAF** から **Fargate + Cloudflare Tunnel** に移行。WAF / ALB はステージング入口から **削除済**。詳細: [AWS_FARGATE_TUNNEL.md](./AWS_FARGATE_TUNNEL.md)

**CLI プロファイル**: 新アカウント作業は `AWS_PROFILE=default`（`620992446973`）。旧バックアップは `medicine-recommend-dev`（`290780119994`）。`scripts/lib/aws_common.sh` 参照。

## 一括セットアップ

```bash
# AWS_PROFILE の export は省略可（aws_common.sh 既定 = medicine-recommend-dev）
chmod +x scripts/setup-aws-infra.sh scripts/setup-aws-*.sh scripts/sync-static-to-s3.sh
./scripts/setup-aws-infra.sh
```

個別:

| スクリプト | 内容 |
|-----------|------|
| [setup-aws-cloudwatch.sh](../../scripts/setup-aws-cloudwatch.sh) | Log Group `/ecs/medicine-recommend`、ECS awslogs、CPU/5xx/Pipeline アラーム |
| ~~setup-aws-waf.sh~~ | **レガシー** — Express+ALB 時代。Tunnel 移行後は入口 WAF 不要 |
| [setup-aws-fargate-tunnel.sh](../../scripts/setup-aws-fargate-tunnel.sh) | **Fargate + cloudflared** ECS サービス（ALB なし） |
| [setup-aws-cloudfront.sh](../../scripts/setup-aws-cloudfront.sh) | S3 + CloudFront + `static/` 同期 |
| [sync-static-to-s3.sh](../../scripts/sync-static-to-s3.sh) | デプロイ後の static 再同期（`--invalidate` で CF キャッシュ削除） |
| [setup-aws-ecs-secrets.sh](../../scripts/setup-aws-ecs-secrets.sh) | Secrets + ECS env（**Classic ECS 向け**。Express は下記） |
| [update-aws-express-env.sh](../../scripts/update-aws-express-env.sh) | **レガシー** — ECS Express env（移行前） |
| [migrate-aws-express-to-fargate-tunnel.sh](../../scripts/migrate-aws-express-to-fargate-tunnel.sh) | Express → Fargate + Tunnel 一括移行 |

共通設定: [scripts/lib/aws_common.sh](../../scripts/lib/aws_common.sh)（Git Bash では `MSYS2_ARG_CONV_EXCL=*` で `/ecs/` パス変換を無効化）

## CloudFront 後の ECS 設定

`setup-aws-cloudfront.sh` 実行後:

```bash
# scripts/.aws-static-cdn-url に URL が保存される
STATIC_CDN_BASE_URL=$(cat scripts/.aws-static-cdn-url)

# .env に追記して ECS へ反映
echo "STATIC_CDN_BASE_URL=${STATIC_CDN_BASE_URL}" >> .env
./scripts/setup-aws-ecs-secrets.sh .env
```

アプリは `url_for('static', ...)` 経由で CloudFront URL を返す（[config/aws_features.py](../../config/aws_features.py) `resolve_static_asset_url`）。

## CodePipeline 連携（任意）

CodeBuild では [buildspec.yml](../../buildspec.yml) 既定 `SYNC_STATIC_TO_S3=true` で push 毎に post_build から `sync-static-to-s3.sh --invalidate` と `aws-staging-smoke.sh`（Translate / Polly / CDN）を実行。

CodeBuild ロールに以下が必要:

- `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket` on `medicine-recommend-static-*`
- `cloudfront:CreateInvalidation`

## 環境変数（上書き用）

| 変数 | 既定 |
|------|------|
| `AWS_REGION` | `ap-northeast-1` |
| `ECS_CLUSTER` / `ECS_SERVICE` | `default` / `medicine-recommend` |
| `ECS_TASK_FAMILY` | `default-medicine-recommend` |
| `ALB_ARN` | 自動解決（失敗時は手動指定） |
| `WAF_RATE_LIMIT` | `2000` / 5分 / IP |
| `STATIC_S3_BUCKET` | `medicine-recommend-static-<account>` |
| `ALARM_SNS_TOPIC_ARN` | 未設定時はアラームのみ（通知なし） |

## Admin IAM

初回セットアップ用ポリシー: [AWS_IAM_ADMIN_POLICY.json](./AWS_IAM_ADMIN_POLICY.json)

Permission Boundary がある場合は `wafv2:*`, `cloudfront:*`, `logs:*` が許可されているか確認。

## 検証

```bash
curl -s https://aws-medicine.yutok.dev/health
curl -s https://origin-aws-medicine.yutok.dev/health
# CloudFront 設定後（ブラウザ DevTools）:
#   /static/css/main.css が cloudfront.net または STATIC_CDN_BASE_URL から読み込まれる
```

## 関連

- [AWS_FARGATE_TUNNEL.md](./AWS_FARGATE_TUNNEL.md) — **移行後 SSOT**
- [AWS_WAKE_ON_ACCESS.md](./AWS_WAKE_ON_ACCESS.md) — Cloud Run 型運用
- [AWS_FEATURES_ROLLOUT.md](./AWS_FEATURES_ROLLOUT.md)
- Phase 3: `scripts/setup-aws-bedrock-kb.sh`, `scripts/sync-concierge-kb-to-s3.sh`
- Phase 4: `scripts/setup-aws-elasticache.sh`, `scripts/setup-aws-personalize.sh`
- 計画: [.cursor/plans/aws_cloudflare_一括改善_afd2b593.plan.md](../../.cursor/plans/aws_cloudflare_一括改善_afd2b593.plan.md)
