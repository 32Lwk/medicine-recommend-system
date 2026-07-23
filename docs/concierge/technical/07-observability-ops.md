# 監視・運用・デプロイ確認

## ヘルスチェック（公開）

- `GET /health` — `{ "status": "ok", "git_commit": "<hash>" }`
- `GET /health/aws` — 機能の利用有無（翻訳/TTS/KB 等）。**Secrets や env 変数名は含まない**

利用者向け回答では「公開されているデプロイ情報」として commit や URL を述べてよい。  
「環境変数を読み取った」等のメタは出さない。

## ログ

| 環境 | ログ先 |
|------|--------|
| GCP Cloud Run | Cloud Logging |
| AWS ECS | CloudWatch `/ecs/medicine-recommend` |
| 開発 | `log/` 配下 JSONL・Markdown |

## デプロイ確認手順（運用者向け・公開手順として説明可）

**GCP 本番**

- Cloud Build → Cloud Run
- `/health` の `git_commit` で反映 revision を確認

**AWS ステージング**

- GitHub main push → CodePipeline → CodeBuild → ECR → ECS redeploy
- post_build: static S3 同期 + smoke（Translate/Polly/health）
- `/health` + `/health/aws` で確認

## CodePipeline smoke（自動）

`scripts/aws-staging-smoke.sh` — デプロイ commit 一致、Translate/Polly、CloudFront CSS

## 既知ブロッカー（公開情報）

- Bedrock KB ingestion: Titan Embed 429 時は Support 対応中。AWS ステージング architecture 回答に脚注あり
