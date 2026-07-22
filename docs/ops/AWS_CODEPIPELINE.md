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
export AWS_PROFILE=admin
aws codepipeline start-pipeline-execution \
  --name medicine-recommend-main \
  --region ap-northeast-1
```

## 再セットアップ（IAM / Pipeline 作り直し）

```bash
export AWS_PROFILE=admin
./scripts/setup-aws-codepipeline.sh
```

## 手動デプロイ（Pipeline なし）

```bash
export AWS_PROFILE=admin
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
| Source 失敗 `Connection not available` | GitHub OAuth 未完了 → Connections で Available に |
| Build 失敗 `Cannot connect to Docker` | CodeBuild `privilegedMode: true` を確認 |
| Build 成功 / ECS 503 | `/health` を確認。Secrets（OPENAI 等）未設定は別問題 |
| `buildspec.yml not found` | main に merge されているか確認 |

## 関連

- GCP 自動デプロイ: `cloudbuild.yaml` + Cloud Build トリガー
- 手動 AWS デプロイ: `scripts/deploy-aws-ecs.sh`
