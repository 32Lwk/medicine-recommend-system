# AWS CodePipeline（GitHub main → CodeBuild → ECR → ECS）

GitHub `32Lwk/medicine-recommend-system` の **main** ブランチへの push で、AWS 側が自動ビルド・デプロイします。

## 構成

```
GitHub push (main)
    ↓ CodeStar Connection
CodePipeline: medicine-recommend-main
    ↓
CodeBuild: medicine-recommend-build  (buildspec.yml)
    ├─ docker build linux/amd64
    ├─ ECR push medicine-recommend:latest
    └─ ecs update-service --force-new-deployment
    ↓
ECS Express: medicine-recommend @ aws.medicine.yutok.dev
```

## AWS リソース（アカウント 290780119994 / ap-northeast-1）

| リソース | 名前 |
|----------|------|
| Pipeline | `medicine-recommend-main` |
| CodeBuild | `medicine-recommend-build` |
| CodeStar Connection | `medicine-recommend-github` |
| S3 アーティファクト | `medicine-recommend-pipeline-artifacts-290780119994` |
| IAM ロール | `medicine-recommend-codepipeline-role`, `medicine-recommend-codebuild-role` |

コンソール: [CodePipeline](https://ap-northeast-1.console.aws.amazon.com/codesuite/codepipeline/pipelines/medicine-recommend-main/view)

## 初回セットアップ（OAuth・1回だけ）

1. [Connections](https://ap-northeast-1.console.aws.amazon.com/codesuite/settings/connections) を開く
2. `medicine-recommend-github` → **保留中の更新を完了** / **Complete pending connection**
3. GitHub で **Authorize AWS Connector for GitHub**
4. インストール対象: **`32Lwk/medicine-recommend-system`**（または All repositories）
5. ステータスが **Available** になることを確認

## リポジトリに必要なファイル

main ブランチに以下が含まれていること:

- `buildspec.yml`（ルート）
- `Dockerfile`

初回はローカルから push:

```bash
git add buildspec.yml scripts/deploy-aws-ecs.sh scripts/setup-aws-codepipeline.sh docs/ops/AWS_CODEPIPELINE.md
git commit -m "feat: add AWS CodePipeline buildspec and setup scripts"
git push origin main
```

## 手動で Pipeline 実行

```bash
export AWS_PROFILE=medicine-recommend-dev
aws codepipeline start-pipeline-execution \
  --name medicine-recommend-main \
  --region ap-northeast-1
```

## 再セットアップ（IAM / Pipeline 作り直し）

```bash
export AWS_PROFILE=medicine-recommend-dev
./scripts/setup-aws-codepipeline.sh
```

## 手動デプロイ（Pipeline なし）

```bash
export AWS_PROFILE=medicine-recommend-dev
./scripts/deploy-aws-ecs.sh
```

## コスト目安

| サービス | 目安 |
|----------|------|
| CodePipeline | ~$1/月 |
| CodeBuild | ビルド ~5–10 分/回 × 従量 |
| ECS / ALB / ECR | 既存と同じ（Budget $50 内で要監視） |

## トラブルシュート

| 症状 | 対処 |
|------|------|
| push しても Build が走らない | Source の Webhook / CodeStar Connection が **Available** か確認。Console → Pipeline → 実行履歴 |
| Build は走るが毎回 Failed（post_build） | CloudWatch `/aws/codebuild/medicine-recommend-build` を確認。`AWS_PROFILE medicine-recommend-dev could not be found` → CodeBuild では IAM ロールを使う（`aws_common.sh` 修正済み）。`SMOKE FAIL: POST /api/smoke/aws-translate` → ECS **taskRole** に Translate/Polly 権限なし → `./scripts/setup-aws-ecs-task-role.sh`（admin IAM） |
| push 後 Pipeline が Failed だが `/health` の commit は新しい | **デプロイ自体は成功**していることが多い。post_build の smoke が advisory（`SMOKE_STRICT` 未設定時は警告のみ）になった。Translate/Polly を本番同等に通すには task role 設定が必要 |
| Source 失敗 `Connection not available` | GitHub OAuth 未完了 → Connections で Available に |
| Build 失敗 `Cannot connect to Docker` | CodeBuild `privilegedMode: true` を確認 |
| Build 成功 / ECS 503 | `/health` を確認。Secrets（OPENAI 等）未設定は別問題 |
| `buildspec.yml not found` | main に merge されているか確認 |
| push から反映まで 6 分以上 | CANARY bake 時間・CodeBuild キャッシュを確認（下記 § パフォーマンス） |

## パフォーマンス（ECS Express デプロイ遅延）

**調査日 2026-07-22** — `https://aws.medicine.yutok.dev`（ECS Express Mode）

| 要因 | 内容 | 対策 |
|------|------|------|
| CANARY デプロイ | Express Gateway は **ROLLING 不可**。既定 bake 3+3 分で push→反映が 6〜8 分 | `bakeTimeInMinutes=0` / `canaryBakeTimeInMinutes=0` に短縮（`scripts/tune-aws-ecs-performance.sh`） |
| CodeBuild | `BUILD_GENERAL1_SMALL`、キャッシュ無効時 ~2 分/回 | `LOCAL_DOCKER_LAYER_CACHE` 有効化、`buildspec.yml` で BuildKit + `--cache-from ECR:latest` |
| ランタイム同時処理 | タスク定義 `GUNICORN_WORKERS=1` | `GUNICORN_WORKERS=2`（512 CPU / 1024 MiB ステージング向け） |
| ウォーム `/health` | 50〜150 ms — ALB/タスク自体は速い | 遅延の大半は **デプロイ待ち** と **ビルド** |
| Secrets 未設定 | `DATABASE_URL` 無し → セッション未永続化、UI が「AI分析中」のまま | `./scripts/setup-aws-ecs-secrets.sh .env` |

一括調整:

```bash
export AWS_PROFILE=medicine-recommend-dev
./scripts/tune-aws-ecs-performance.sh
```

Secrets 投入:

```bash
cp .env.example .env   # OPENAI_API_KEY, DATABASE_URL, SECRET_KEY
./scripts/setup-aws-ecs-secrets.sh .env
```

ECS タスクロール（Translate / Polly / Bedrock KB — **admin IAM 推奨**）:

```bash
AWS_PROFILE=admin ./scripts/setup-aws-ecs-task-role.sh
```

`ecsTaskExecutionRole` のみのままだと `/api/smoke/aws-translate` が `empty_or_unchanged`（AccessDenied）になります。

## KB 自動化（Phase 5）

`buildspec.yml` post_build に KB sync / ingestion / eval フックを追加（初回 merge 時は env すべて `false`）。

### CodeBuild env 変数

| 変数 | 既定 | 説明 |
|------|------|------|
| `SYNC_KB_TO_S3` | `false` | `sync-all-kb-to-s3.sh` |
| `KB_INGESTION_ON_PUSH` | `false` | `start-managed-kb-ingestion.sh`（非同期、待機なし） |
| `RUN_KB_EVAL` | `false` | Medicine + Concierge retrieve eval |
| `KB_EVAL_STRICT` | `false` | `true` で eval 閾値未達時 build fail |

### 段階的ロールアウト（ユーザー作業）

| 順序 | env | 条件 |
|------|-----|------|
| 1 | すべて `false` | buildspec merge のみ |
| 2 | `SYNC_KB_TO_S3=true` | Step 5-0b 完了 + ローカル sync OK |
| 3 | `KB_INGESTION_ON_PUSH=true` | ingestion failed=0 確認後 |
| 4 | `RUN_KB_EVAL=true` | 週次 or 手動パイプライン |

CodeBuild コンソール → `medicine-recommend-build` → Environment → Additional configuration → Environment variables。

### IAM 要件（CodeBuild ロール）

`medicine-recommend-codebuild-role` に不足がある場合、admin で追加:

```bash
export AWS_PROFILE=admin
./scripts/setup-aws-codebuild-kb-role.sh
```

付与内容:

- `bedrock:StartIngestionJob` / `bedrock-agent:StartIngestionJob` on Concierge / Medicine KB
- `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket` on `medicine-recommend-kb-source-290780119994`

CodeBuild post_build で `build_medicine_kb_documents.py` を実行するため **pandas** が必要（`buildspec.yml` / `sync-all-kb-to-s3.sh` で `pip3 install pandas`）。

### eval 閾値（CI）

```bash
.venv/bin/python scripts/eval_medicine_kb.py \
  --mode both --min-pass-pct 80 --min-interaction-pass 5
.venv/bin/python scripts/eval_concierge_kb.py --min-pass-pct 80
```

## 関連

- **Phase 1 インフラ**: [AWS_INFRA.md](./AWS_INFRA.md)（CloudWatch / WAF / CloudFront）
- GCP 自動デプロイ: `cloudbuild.yaml` + Cloud Build トリガー
- 手動 AWS デプロイ: `scripts/deploy-aws-ecs.sh`
