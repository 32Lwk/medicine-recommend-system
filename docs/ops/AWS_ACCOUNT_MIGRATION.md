# AWS アカウント移行 Runbook

> **旧アカウント**: `290780119994` → **新アカウント**: `620992446973`  
> **リージョン**: `ap-northeast-1`  
> **アカウント移行日**: 2026-08-06  
> **Fargate + Tunnel 移行日**: 2026-08-07

GCP 本番 `medicine.yutok.dev` には影響なし。AWS ステージング `aws-medicine.yutok.dev` / `aws.medicine.yutok.dev` のみ対象。

## 移行後リソース（新アカウント — 2026-08-07 更新）

| 種別 | 値 |
|------|-----|
| **入口 URL** | `https://aws-medicine.yutok.dev`（Cloudflare Worker + Wake） |
| **オリジン（Tunnel）** | `https://origin-aws-medicine.yutok.dev` |
| ECS | Fargate `default` / `medicine-recommend`（タスク定義 `medicine-recommend-tunnel`） |
| ~~ECS Express エンドポイント~~ | **削除済**（2026-08-07） |
| ~~ALB~~ | **0 件** |
| CloudFront static | `https://dnv1ek9xdguhs.cloudfront.net/static` |
| ECR | `620992446973.dkr.ecr.ap-northeast-1.amazonaws.com/medicine-recommend` |
| CodePipeline | `medicine-recommend-main` |
| CodeStar Connection | `medicine-recommend-github`（**AVAILABLE**） |
| デプロイモード | `fargate_tunnel`（`scripts/.aws-deploy-mode`） |
| IAM ユーザー | `Admin`, `medicine-recommend-dev` |

詳細 SSOT: [AWS_FARGATE_TUNNEL.md](./AWS_FARGATE_TUNNEL.md)

## CLI ログイン

旧プロファイル `admin` / `medicine-recommend-dev` には**旧アカウントのアクセスキー**が残っています。
`aws login` する前に、どちらかを選んでください。

### 方法 A: 新プロファイル名で login（推奨）

```powershell
aws login --profile admin-620992446973
aws login --profile medicine-recommend-dev-620992446973
```

### 方法 B: 旧キーを削除して同名プロファイルで login

`~/.aws/credentials` から `[admin]` と `[medicine-recommend-dev]` の
`aws_access_key_id` / `aws_secret_access_key` 行を削除してから:

```powershell
aws login --profile admin
aws login --profile medicine-recommend-dev
```

### 方法 C: 移行作業中は default（root login）を使用

```powershell
aws login
aws sts get-caller-identity
# Account: 620992446973
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

### 1. DNS + TLS — **完了（2026-08-06）**

| 項目 | 状態 |
|------|------|
| ACM 証明書 | **ISSUED** — `arn:aws:acm:ap-northeast-1:620992446973:certificate/149784c5-8abc-4a09-85b7-7c3b47390061` |
| ALB HTTPS リスナー | カスタム証明書アタッチ済み |
| Host ヘッダールール | `aws.medicine.yutok.dev` + Express 既定 URL |
| HTTPS 検証 | `curl -s https://aws.medicine.yutok.dev/health` → 200 |

**原因（HTTPS 証明書エラー / post_build 失敗）**

1. ACM は **ISSUED** だったが、ALB 443 リスナーに **未アタッチ**（`InUseBy: []`）
2. CodeBuild の `wait-staging-health-commit.sh` が `https://aws.medicine.yutok.dev/health` に `curl -sf` するが、TLS 検証失敗で 420 秒タイムアウト → post_build Failed

**実施した対処**

```bash
AWS_PROFILE=default ./scripts/setup-aws-custom-domain.sh
```

**推奨 DNS（任意）** — ~~ALB 直 CNAME~~ **レガシー（2026-08-07 ALB 削除済）**:

> 現構成: `aws-medicine.yutok.dev` → Worker、`origin-aws-medicine.yutok.dev` → Tunnel。`aws.medicine.yutok.dev` は CI/E2E 用 DNS only。

```
# レガシー（移行前）
aws.medicine.yutok.dev → ecs-express-gateway-alb-7a197fcf-1310163209.ap-northeast-1.elb.amazonaws.com
```

**再発防止**: `stop-aws-staging.sh` が Auto Scaling **min/max=0** まで下げる。`resume-aws-staging.sh` で min/max/desired を復元。

**503 について**: 停止中は Tunnel 先にターゲットがなく **503 が正常**。Worker wake → 3–6 分待ち、または `./scripts/resume-aws-staging.sh`。

### 2. CodeStar GitHub OAuth — **完了**

Connection status: `AVAILABLE`

push 後の Pipeline 手動実行:

```bash
aws codepipeline start-pipeline-execution --name medicine-recommend-main --region ap-northeast-1
```

### 3. Bedrock KB（任意 — Phase 3）

新アカウントはクォータ 0 の可能性あり。`docs/ops/AWS_BEDROCK_QUOTAS.md` 参照。

```bash
AWS_PROFILE=admin ./scripts/create-aws-bedrock-kb.sh
# 新 KB ID を ECS env / CodeBuild env に反映
```

移行直後は `CONCIERGE_RAG_PROVIDER=local` で運用可。

### 4. WAF — **削除済み（2026-08-06）**

個人 $30/月方針のため `medicine-recommend-web-acl` を削除。再作成: `./scripts/setup-aws-waf.sh`

### 5. コールドスタート + Budget — **設定済み**

```bash
./scripts/setup-aws-staging-cold-start.sh   # 512/1024, maxTasks=1, ECS=0 既定
./scripts/resume-aws-staging.sh             # 利用時
BUDGET_LIMIT=30 ./scripts/apply-aws-budget-notifications.sh
```

詳細: [AWS_COST_PLAN.md](./AWS_COST_PLAN.md) / [AWS_BUDGET_STAGED_ACTIONS.md](./AWS_BUDGET_STAGED_ACTIONS.md)

### 6. 旧アカウント整理 — **ALB 削除済（2026-08-07）**

| 操作 | 状態 |
|------|------|
| ECS `desiredCount=0` | ✅ |
| `delete-aws-express-staging.sh --confirm` | ✅ Express INACTIVE |
| 残存 ALB / WAF | ✅ **手動削除**（Express 削除後に孤立 ALB が残存したため） |
| 新アカウント Express → Fargate + Tunnel | ✅ [AWS_FARGATE_TUNNEL.md](./AWS_FARGATE_TUNNEL.md) |

```bash
# 旧アカウント Express 削除
AWS_PROFILE=medicine-recommend-dev AWS_ACCOUNT_ID=290780119994 \
  ./scripts/delete-aws-express-staging.sh --confirm
```

30 日後: 旧 ECR / Secrets / S3 の完全削除を再評価。

### 7. Fargate + Cloudflare Tunnel 移行 — **完了（2026-08-07）**

```bash
export AWS_PROFILE=default AWS_ACCOUNT_ID=620992446973
export CLOUDFLARE_TUNNEL_TOKEN='...'
./scripts/migrate-aws-express-to-fargate-tunnel.sh --confirm
cd workers && npx wrangler deploy
./scripts/stop-aws-staging.sh   # 停止デフォルト化
```

| 検証 | 結果 |
|------|------|
| ALB 件数（新） | 0 |
| `/health` Worker / Origin | 200 OK（稼働時） |
| コスト（停止デフォルト） | ~$6–7/月（新のみ） |

## トラブルシュート

| 症状 | 原因 | 対処 |
|------|------|------|
| タスク起動失敗 `GetSecretValue` | `ecsTaskExecutionRole` に Secrets 権限なし | bootstrap スクリプト再実行 or IAM inline policy 追加 |
| `exec ./start.sh: no such file` | Windows CRLF | Dockerfile の `sed -i 's/\r$//'` + `CMD ["bash","./start.sh"]` |
| CodePipeline setup 失敗（Windows） | `/tmp` パス | `setup-aws-codepipeline.sh` の `aws_file_arg()` 使用 |
| 503（停止中） | ECS desired=0 | **正常**。Worker が wake → 3–6 分待ち |
| 503（CANARY 中） | デプロイ bake 3+3 分 | 数分待って `/health` 再確認 |
| stop 後すぐ起動 | Worker / ヘルスチェックが wake | stop 後は URL にアクセスしない |
| Origin 502 | cloudflared / Tunnel token | タスクログ、Secrets 確認 |
| 旧 ALB 残存 | Express 削除後の孤立 | listener 削除 → ALB 削除 |
| HTTPS 証明書エラー（`SEC_E_WRONG_PRINCIPAL`） | ACM が ISSUED でも ALB リスナー未アタッチ | `./scripts/setup-aws-custom-domain.sh` を再実行 |
| post_build Failed（`/health` 420s タイムアウト） | 上記 TLS 未設定で `curl -sf` 失敗 | カスタムドメイン TLS 設定後に Pipeline 再実行 |

## 検証

```bash
curl -s https://aws-medicine.yutok.dev/health
curl -s https://origin-aws-medicine.yutok.dev/health
curl -sI https://dnv1ek9xdguhs.cloudfront.net/static/css/main.css
GIT_COMMIT=$(git rev-parse HEAD) ./scripts/aws-staging-smoke.sh
```
