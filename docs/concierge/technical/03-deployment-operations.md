# デプロイ・運用

## GCP 本番（medicine.yutok.dev）

- **CI**: `cloudbuild.yaml` — Git push → Cloud Run デプロイ
- **env**: `GIT_COMMIT`, `GIT_COMMIT_DATE`, `MEDICINE_IMAGE_CDN_BASE` 等（AWS フラグは **含めない**）
- **DB**: Neon PostgreSQL（サーバーレス）

## AWS ステージング（aws.medicine.yutok.dev）

- **CI**: CodePipeline `medicine-recommend-main`
  1. GitHub Source（CodeStar Connection）
  2. CodeBuild `medicine-recommend-build` — Docker build → ECR push
  3. `ecs update-service --force-new-deployment`
  4. `services-stable` 待ち
  5. `sync-static-to-s3.sh --invalidate`（CodeBuild で static 同期が有効な場合）
  6. `aws-staging-smoke.sh` — health / Translate / Polly / CDN
- **確認**: `GET /health` の `git_commit`、 `GET /health/aws` の機能フラグ
- **手動デプロイ**: `scripts/deploy-aws-ecs.sh`
- **env 更新**: `scripts/update-aws-express-env.sh`（PassRole 不要）

## Bedrock Knowledge Base（Concierge RAG）

- **KB ID（ステージング）**: `4PEWLBZGTH`
- **ソース同期**: `scripts/sync-concierge-kb-to-s3.sh` → `scripts/sync-aws-bedrock-kb-ingestion.sh`
- **既知ブロッカー**: Titan Embed v2 on-demand クォータ未 provisioning 時は ingestion 429 — Support ケース参照 `docs/ops/AWS_BEDROCK_QUOTAS.md`
- **コード**: `src/services/bedrock_kb_retrieve.py` — retrieve + Redis キャッシュ

## Cloudflare R2（医薬品画像）

- **URL**: `https://images.yutok.dev/otc/{id}.webp`
- **アップロード**: `scripts/upload-r2-otc-image.sh`
- **アプリ**: `src/services/medicine_image_urls.py` + カード `onerror` プレースホルダー

## ロールバック

- AWS 機能のみ OFF: ECS タスク定義で Translate/Polly/Bedrock KB を **レガシー設定（DeepL / Web Speech / ローカル参照）** に戻して redeploy
- Chat Pipeline v2: 通常は env 変更不要。緊急時のみ v2 フラグを明示 OFF（運用ドキュメント参照）

## 医薬品相談としての境界

技術 FAQ に詳しく答えても、**症状・薬の選び方・用法用量** は PhysicalOrchestrator 経路で処理する。Concierge は案内役であり、診断・処方を行わない。
