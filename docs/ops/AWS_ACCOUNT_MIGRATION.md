# AWS アカウント移行 Runbook

> **旧アカウント**: `290780119994` → **新アカウント**: `620992446973`  
> **リージョン**: `ap-northeast-1`  
> **移行日**: 2026-08-06

GCP 本番 `medicine.yutok.dev` には影響なし。AWS ステージング `aws.medicine.yutok.dev` のみ対象。

## 移行後リソース（新アカウント）

| 種別 | 値 |
|------|-----|
| ECS Express エンドポイント | `https://me-9585b72a360742069939f7e74bb4bb46.ecs.ap-northeast-1.on.aws` |
| CloudFront static | `https://dnv1ek9xdguhs.cloudfront.net/static` |
| ECR | `620992446973.dkr.ecr.ap-northeast-1.amazonaws.com/medicine-recommend` |
| CodePipeline | `medicine-recommend-main` |
| CodeStar Connection | `medicine-recommend-github`（**PENDING — OAuth 要**） |
| IAM ユーザー | `Admin`, `medicine-recommend-dev` |

## CLI ログイン

```powershell
# root / Admin Console セッション（初回セットアップ済み）
aws login --profile default

# IAM ユーザー作成後
aws login --profile medicine-recommend-dev
aws login --profile admin
```

## 初回構築手順（新アカウント向け）

```bash
export AWS_PROFILE=default   # または medicine-recommend-dev

# 1. Express Gateway + IAM + ECR
./scripts/setup-aws-express-gateway-bootstrap.sh

# 2. Secrets + env
./scripts/setup-aws-express-secrets.sh .env

# 3. CloudFront / CloudWatch（WAF は ALB 作成後）
./scripts/setup-aws-cloudfront.sh

# 4. Docker ビルド & push（ローカル Docker 要）
./scripts/deploy-aws-ecs.sh

# 5. タスク起動
ECS_MIN_TASKS=1 ECS_MAX_TASKS=2 ./scripts/tune-aws-ecs-capacity.sh

# 6. CI/CD
./scripts/setup-aws-codepipeline.sh
# → Console で CodeStar Connection の GitHub OAuth 完了
```

## コード変更（アカウント ID）

runtime critical（`620992446973` に更新済み）:

- `scripts/lib/aws_common.sh`
- `buildspec.yml`
- `scripts/deploy-aws-ecs.sh`
- `scripts/setup-aws-codepipeline.sh`
- `scripts/setup-aws-ecs-task-role.sh`
- `scripts/setup-aws-budget-staged-actions.sh`
- `scripts/lambda/budget_staged_action/handler.py`
- `docs/ops/AWS_IAM_*.json`

## 未完了（手動作業）

### 1. DNS 切替（必須）

Cloudflare / 外部 DNS で `aws.medicine.yutok.dev` の CNAME を新 Express エンドポイントへ:

```
aws.medicine.yutok.dev → me-9585b72a360742069939f7e74bb4bb46.ecs.ap-northeast-1.on.aws
```

切替前に新 URL で `/health` が 200 であることを確認。

### 2. CodeStar GitHub OAuth（CI/CD 自動デプロイ）

1. [Connections Console](https://ap-northeast-1.console.aws.amazon.com/codesuite/settings/connections)
2. `medicine-recommend-github` → **Update pending connection**
3. GitHub で `32Lwk/medicine-recommend-system` を Authorize
4. リポジトリの `buildspec.yml`（新アカウント ID）を `main` に push
5. `aws codepipeline start-pipeline-execution --name medicine-recommend-main --region ap-northeast-1`

### 3. Bedrock KB（任意 — Phase 3）

新アカウントはクォータ 0 の可能性あり。`docs/ops/AWS_BEDROCK_QUOTAS.md` 参照。

```bash
AWS_PROFILE=admin ./scripts/create-aws-bedrock-kb.sh
# 新 KB ID を ECS env / CodeBuild env に反映
```

移行直後は `CONCIERGE_RAG_PROVIDER=local` で運用可。

### 4. WAF（任意）

Express Gateway の ALB が `elbv2 describe-load-balancers` に表示された後:

```bash
./scripts/setup-aws-waf.sh
```

### 5. 旧アカウント整理（移行確認後 30 日）

- 旧 CodePipeline 停止
- 旧 ECS `desiredCount=0`
- 旧 S3 / Secrets 削除

## トラブルシュート

| 症状 | 原因 | 対処 |
|------|------|------|
| タスク起動失敗 `GetSecretValue` | `ecsTaskExecutionRole` に Secrets 権限なし | bootstrap スクリプト再実行 or IAM inline policy 追加 |
| `exec ./start.sh: no such file` | Windows CRLF | Dockerfile の `sed -i 's/\r$//'` + `CMD ["bash","./start.sh"]` |
| CodePipeline setup 失敗（Windows） | `/tmp` パス | `setup-aws-codepipeline.sh` の `aws_file_arg()` 使用 |
| 503（CANARY 中） | デプロイ bake 3+3 分 | 数分待って `/health` 再確認 |

## 検証

```bash
curl -s https://me-9585b72a360742069939f7e74bb4bb46.ecs.ap-northeast-1.on.aws/health
curl -sI https://dnv1ek9xdguhs.cloudfront.net/static/css/main.css
```

DNS 切替後:

```bash
curl -s https://aws.medicine.yutok.dev/health
GIT_COMMIT=$(git rev-parse HEAD) ./scripts/aws-staging-smoke.sh
```
