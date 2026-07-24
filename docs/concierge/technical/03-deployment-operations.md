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
  6. （任意）`sync-all-kb-to-s3.sh` — `SYNC_KB_TO_S3=true` 時
  7. （任意）`start-managed-kb-ingestion.sh` — `KB_INGESTION_ON_PUSH=true` 時（非同期）
  8. `verify-concierge-ssot.sh` → staging smoke
- **確認**: `GET /health` の `git_commit`、 `GET /health/aws` の機能フラグ
- **手動デプロイ**: `scripts/deploy-aws-ecs.sh`
- **env 更新**: `scripts/update-aws-express-env.sh`（PassRole 不要）

## Bedrock Managed Knowledge Base（Dual KB）

| KB | ID | 用途 |
|----|-----|------|
| Concierge | `2CNAGQ2V4P` | 技術 FAQ・運用 |
| Medicine | `30BCEJCJHA` | AskAgent / Explanation RAG |

- **ソース同期**: `scripts/sync-all-kb-to-s3.sh`（Concierge + Medicine build/sync）
- **ingestion**: `scripts/start-managed-kb-ingestion.sh`（非同期起動のみ）
- **eval**: `scripts/eval_medicine_kb.py --mode both --min-pass-pct 80 --min-interaction-pass 5`、`scripts/eval_concierge_kb.py --min-pass-pct 80`
- **CodeBuild env**（初回 merge 時すべて `false`）: `SYNC_KB_TO_S3`, `KB_INGESTION_ON_PUSH`, `RUN_KB_EVAL`, `KB_EVAL_STRICT`
- **metadata 制約**: `metadataAttributes` は **string のみ**（boolean → ingestion 全滅）
- **詳細**: `docs/ops/AWS_BEDROCK_KB.md`, `docs/ops/GCP_RAG_MIGRATION_ADR.md`（GCP 本番 Bedrock は Option C で当面 off）
- **旧 KB `4PEWLBZGTH`**: 非推奨（Titan Embed 429）

## PMDA データ取り込み

- **正本**: `data/otc_medicine_data.csv`, `data/medicine_interactions.csv`, `data/medicine_side_effects.csv`
- **パイプライン**: `scripts/pmda/run_pmda_import.py`（live fetch は **ローカル回線のみ**）
- **KB 反映**: `scripts/build_medicine_kb_documents.py` → `sync-medicine-kb-to-s3.sh` → re-ingest
- **詳細**: `docs/ops/PMDA_DATA_IMPORT.md`

## Bedrock Knowledge Base（Concierge RAG）— 旧記載

<details>
<summary>旧 Customer-managed KB（参考）</summary>

- **KB ID（旧）**: `4PEWLBZGTH`
- **ソース同期**: `scripts/sync-concierge-kb-to-s3.sh` → `scripts/sync-aws-bedrock-kb-ingestion.sh`
- **既知ブロッカー**: Titan Embed v2 on-demand クォータ未 provisioning 時は ingestion 429
</details>

- **コード**: `src/services/bedrock_kb_retrieve.py` — Managed retrieve + Redis キャッシュ

## Cloudflare R2（医薬品画像）

- **URL**: `https://images.yutok.dev/otc/{id}.webp`
- **アップロード**: `scripts/upload-r2-otc-image.sh`
- **アプリ**: `src/services/medicine_image_urls.py` + カード `onerror` プレースホルダー

## ロールバック

- AWS 機能のみ OFF: ECS タスク定義で Translate/Polly/Bedrock KB を **レガシー設定（DeepL / Web Speech / ローカル参照）** に戻して redeploy
- Chat Pipeline v2: 通常は env 変更不要。緊急時のみ v2 フラグを明示 OFF（運用ドキュメント参照）

## 医薬品相談としての境界

技術 FAQ に詳しく答えても、**症状・薬の選び方・用法用量** は PhysicalOrchestrator 経路で処理する。Concierge は案内役であり、診断・処方を行わない。
