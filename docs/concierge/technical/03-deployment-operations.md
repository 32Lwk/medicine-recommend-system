# デプロイ・運用

> CI/CD・KB 同期・ロールバックの SSOT。ヘルス確認は [07-observability-ops.md](07-observability-ops.md)、横断 FAQ は [../rag/technical-infra-rag.md](../rag/technical-infra-rag.md)。

## Q: GCP 本番（medicine.yutok.dev）へのデプロイ方法

<!-- rag-keywords: GCP 本番 Cloud Run デプロイ Cloud Build medicine.yutok.dev 反映 -->

**回答要点**

- **トリガー**: GitHub `main` への push → `cloudbuild.yaml` → Cloud Run デプロイ
- **正本リポジトリ**: GitHub `32Lwk/medicine-recommend-system`（PR / CI / デプロイの正本）
- **ビルドメタ**: Docker ビルド時に Git コミットハッシュ・日付をイメージへ埋め込み → `/health` の `git_commit` とオンボーディング UI に反映
- **本番設定**: DeepL 翻訳、Google Cloud Text-to-Speech、Local RAG — **AWS 専用機能は含めない**
- **DB**: Neon PostgreSQL（サーバーレス）
- **関連**: [01-cross-cloud-architecture.md](01-cross-cloud-architecture.md)、[docs/ops/CLOUD_RUN_LLM_ENV.md](../../ops/CLOUD_RUN_LLM_ENV.md)

### 例外・境界・よくある誤解

- **誤解**: 「GitLab push で本番デプロイ」→ GitLab は **ミラー**。本番 CI/CD トリガーは **GitHub main**
- **境界**: GCP dev（`medicine-recommend-dev`）は別 Cloud Run サービス — 本番 push だけでは dev は自動更新されない場合あり
- **例外**: GitHub 障害時は GitLab から作業後、復旧時に GitHub へ反映（[docs/ops/GITLAB_TEMPORARY_MIGRATION.md](../../ops/GITLAB_TEMPORARY_MIGRATION.md) §10）

---

## GCP 本番（medicine.yutok.dev）

- **CI**: `cloudbuild.yaml` — Git push → Cloud Run デプロイ
- **設定**: Git コミット情報、医薬品画像 CDN ベース URL 等 — AWS 向け機能フラグは **含めない**
- **DB**: Neon PostgreSQL（サーバーレス）
- **起動確認**: Cloud Run startup probe が `/health` を参照（DB 非依存の軽量応答）

---

## Q: AWS ステージングへの自動デプロイの流れ

<!-- rag-keywords: AWS デプロイ CodePipeline CodeBuild ECS ECR GitHub push ステージング -->

**回答要点**

- **トリガー**: GitHub `main` push → CodeStar Connection → CodePipeline `medicine-recommend-main`
- **ビルド**: CodeBuild `medicine-recommend-build` — `buildspec.yml` で Docker build（linux/amd64）→ ECR push
- **デプロイ**: `ecs update-service --force-new-deployment` → ECS Express @ `aws.medicine.yutok.dev`
- **post_build**（`scripts/codebuild-post-deploy.sh`）:
  1. `/health` で新 `git_commit` を待機（`services-stable` より早く実応答を確認）
  2. **条件付き** static S3 + CloudFront 同期（`static/` 変更時）
  3. **条件付き** KB S3 同期（`data/` / `docs/concierge/` 等の変更時）
  4. **並列**: static sync / KB sync / `verify-concierge-ssot.sh`
  5. **毎回**: staging smoke（Translate / Polly / CDN / health）
  6. （KB 変更時）Managed KB ingestion 非同期起動
- **変更検知不可時**: 従来どおり **全 sync**（精度優先フォールバック — `codebuild_deploy_paths.py`）
- **関連**: [docs/ops/AWS_CODEPIPELINE.md](../../ops/AWS_CODEPIPELINE.md)、[07-observability-ops.md](07-observability-ops.md)

### 例外・境界・よくある誤解

- **誤解**: 「Pipeline Failed = デプロイ失敗」→ post_build の smoke が advisory の場合、**`/health` の commit は既に新しい**ことが多い（デプロイ自体は成功）
- **境界**: GitLab push だけでは AWS Pipeline は **走らない** — GitHub main が Source
- **性能**: CANARY bake 時間短縮済み（push → 反映 ~5 分、Pipeline 完了 ~7 分 — backend のみ変更時）
- **IAM**: Translate/Polly smoke 失敗時は ECS **task role** 権限不足が典型 — `setup-aws-ecs-task-role.sh`（admin IAM）

---

## AWS ステージング（aws.medicine.yutok.dev）

- **CI**: CodePipeline `medicine-recommend-main`
  1. GitHub Source（CodeStar Connection、`CODEBUILD_CLONE_REF` 推奨）
  2. CodeBuild `medicine-recommend-build` — Docker build → ECR push
  3. **`scripts/codebuild-post-deploy.sh`**（post_build オーケストレーション）
  4. （任意）`start-managed-kb-ingestion.sh` — KB 変更時
- **確認**: `GET /health` の `git_commit`、`GET /health/aws` の機能利用有無
- **手動デプロイ**: `scripts/deploy-aws-ecs.sh`
- **設定更新**: `scripts/update-aws-express-env.sh`（ECS Express — PassRole 不要）
- **詳細**: [docs/ops/AWS_CODEPIPELINE.md](../../ops/AWS_CODEPIPELINE.md)

---

## Q: デプロイ後の確認方法

<!-- rag-keywords: デプロイ 確認 health git_commit 反映 検証 smoke -->

**回答要点**

- **共通**: `GET /health` → `{ "status": "ok", "git_commit": "<hash>" }` で反映 revision を確認
- **AWS 追加**: `GET /health/aws` → 翻訳/TTS/KB/CDN の **利用有無**（Secrets 名は含まない）
- **AWS smoke**: CodeBuild が自動実行 — Translate 疎通、Polly、CloudFront CSS、commit 一致
- **手動チェックリスト**: [docs/ops/AWS_STAGING_CHECKLIST.md](../../ops/AWS_STAGING_CHECKLIST.md)
- **関連**: [07-observability-ops.md](07-observability-ops.md)

### 例外・境界・よくある誤解

- **誤解**: 「`/health/aws` で API キーが見える」→ **機能フラグの利用有無のみ**。シークレット値・設定変数名は返さない
- **境界**: 利用者向け Concierge 回答では「公開デプロイ情報」として commit を述べてよいが、「環境変数を読んだ」等のメタは出さない（[00-disclosure-policy.md](00-disclosure-policy.md)）
- **typo 注意**: 外部モニタが `/helth` を叩くと 404 — 正しくは `/health`

---

## Q: Bedrock Managed Knowledge Base（Dual KB）の構成

<!-- rag-keywords: Bedrock KB Knowledge Base Concierge Medicine Managed 2CNAGQ2V4P 30BCEJCJHA -->

**回答要点**

- **Concierge KB** `2CNAGQ2V4P`: 技術 FAQ・運用 SSOT（`docs/concierge/` 等）
- **Medicine KB** `30BCEJCJHA`: AskAgent / Explanation RAG（OTC データ・相互作用等）
- **GCP 本番**: Local RAG 維持（ADR Option C — Bedrock 本番切替は GO 条件達成まで保留）
- **AWS ステージング**: Bedrock Managed KB を試験可能（Express env 更新時の既定は Bedrock KB 向け）
- **ソース同期**: `scripts/sync-all-kb-to-s3.sh` → S3 → ingestion
- **ingestion**: `scripts/start-managed-kb-ingestion.sh`（非同期起動のみ — 完了待ちなし）
- **eval 目標**: Medicine ≥80%、Concierge ≥80%、相互作用 5/5 hard gate
- **metadata 制約**: `metadataAttributes` は **string のみ**（boolean 混入 → ingestion 全滅）
- **旧 KB `4PEWLBZGTH`**: 非推奨（Titan Embed 429）
- **関連**: [docs/ops/AWS_BEDROCK_KB.md](../../ops/AWS_BEDROCK_KB.md)、[docs/ops/GCP_RAG_MIGRATION_ADR.md](../../ops/GCP_RAG_MIGRATION_ADR.md)

### 例外・境界・よくある誤解

- **誤解**: 「KB = 薬の推奨順位を決める」→ RAG は **説明・Q&A 層のみ**。推奨順位は PhysicalOrchestrator のルールベース（変更しない方針）
- **誤解**: 「ingestion 429 = アプリ障害」→ Titan Embed クォータ問題は **KB 取り込みのみ**影響。Local RAG は継続動作
- **CodeBuild 自動化**: KB sync / ingestion は staging で有効。eval CI（`RUN_KB_EVAL`）は週次 or 手動が想定

---

## Bedrock Managed Knowledge Base（Dual KB）

| KB | ID | 用途 |
|----|-----|------|
| Concierge | `2CNAGQ2V4P` | 技術 FAQ・運用 |
| Medicine | `30BCEJCJHA` | AskAgent / Explanation RAG |

- **ソース同期**: `scripts/sync-all-kb-to-s3.sh`（Concierge + Medicine build/sync）
- **ingestion**: `scripts/start-managed-kb-ingestion.sh`（非同期起動のみ）
- **eval**: `scripts/eval_medicine_kb.py --mode both --min-pass-pct 80 --min-interaction-pass 5`、`scripts/eval_concierge_kb.py --min-pass-pct 80`
- **CodeBuild 段階ロールアウト**: KB S3 同期・ingestion は staging で有効化済み。eval strict は任意
- **コード**: `src/services/bedrock_kb_retrieve.py` — Managed retrieve + Redis キャッシュ（Bedrock 利用時）

---

## Q: Local RAG と Bedrock KB の使い分け

<!-- rag-keywords: Local RAG Bedrock KB 使い分け GCP AWS 既定 プロバイダ -->

**回答要点**

- **What**: Local RAG = リポジトリ内 Markdown/JSON を BM25 + OpenAI embedding ハイブリッドで検索
- **コード既定**: **Concierge は Local RAG 固定**（2026-07-28〜。`CONCIERGE_RAG_PROVIDER=bedrock_kb` も local に正規化）。Medicine は Local RAG 既定
- **GCP 本番**: 常に Local RAG（Bedrock 本番切替は ADR で保留）
- **AWS ステージング**: Medicine のみ Bedrock Managed KB を試験可能。Concierge は Local RAG
- **Why Local RAG**: OpenSearch OCU コスト回避、GCP/AWS で **同一実装**、本番リスク最小
- **Why Bedrock KB（staging）**: Managed ingestion / eval CI / AWS ネイティブ retrieve の mature 化
- **関連**: [docs/ops/LOCAL_RAG.md](../../ops/LOCAL_RAG.md)、[08-technical-decisions.md](08-technical-decisions.md)

### 例外・境界・よくある誤解

- **誤解**: 「ステージングと本番で RAG 品質は同一」→ Option C 採用中のため **差が残る**。eval で段階的に縮小
- **フォールバック**: embedding 失敗時 BM25 のみ、Bedrock 不可時 Local RAG へ — 推奨順位には影響しない

---

## Q: PMDA データ取り込みと KB 反映

<!-- rag-keywords: PMDA データ 取り込み OTC CSV medicine_interactions KB 反映 -->

**回答要点**

- **正本 CSV**: `data/otc_medicine_data.csv`, `data/medicine_interactions.csv`, `data/medicine_side_effects.csv`
- **取り込み**: `scripts/pmda/run_pmda_import.py` — live fetch は **ローカル回線のみ**（CI では実行しない）
- **KB 反映フルパイプライン**: `scripts/reflect_medicine_kb.sh`（reparse → build → S3 sync → ingestion → eval）
- **手動段階**: `build_medicine_kb_documents.py` → `sync-medicine-kb-to-s3.sh` → re-ingest
- **推奨への影響**: CSV 更新 → PhysicalOrchestrator スコアリングに反映。KB は説明層
- **関連**: [docs/ops/PMDA_DATA_IMPORT.md](../../ops/PMDA_DATA_IMPORT.md)

### 例外・境界・よくある誤解

- **境界**: PMDA live fetch を CodeBuild で回さない — **ネットワーク・レート制限**のためローカル限定
- **誤解**: 「KB 更新 = 薬の順位が変わる」→ 順位は CSV + ルール。KB は Q&A 説明用

---

## PMDA データ取り込み

- **正本**: `data/otc_medicine_data.csv`, `data/medicine_interactions.csv`, `data/medicine_side_effects.csv`
- **パイプライン**: `scripts/pmda/run_pmda_import.py`（live fetch は **ローカル回線のみ**）
- **KB 反映**: `scripts/reflect_medicine_kb.sh` または手動 build → sync → re-ingest
- **詳細**: [docs/ops/PMDA_DATA_IMPORT.md](../../ops/PMDA_DATA_IMPORT.md)

---

## Q: 静的アセット（JS/CSS）と医薬品画像の配信

<!-- rag-keywords: static CDN CloudFront S3 R2 画像 JS CSS 同期 -->

**回答要点**

- **AWS JS/CSS**: S3 + CloudFront — CodeBuild post_build で `static/` 同期（変更検知時）。`aws.medicine.yutok.dev` は CloudFront URL から読み込み
- **localhost**: アプリ同梱 `/static/` を配信（最新 JS を即反映）。dev ホスト名だけでは CDN バイパスにならない
- **医薬品画像**: Cloudflare R2 — `https://images.yutok.dev/otc/{slug}.webp`（GCP/AWS 共通）
- **同期スクリプト**: `scripts/sync-static-to-s3.sh --invalidate`、`scripts/sync_otc_images_from_matsukiyo.py`
- **関連**: [docs/ops/AWS_INFRA.md](../../ops/AWS_INFRA.md)、[docs/ops/CLOUDFLARE_R2_IMAGES.md](../../ops/CLOUDFLARE_R2_IMAGES.md)

### 例外・境界・よくある誤解

- **誤解**: 「static/ 変更は毎回 S3 同期」→ `src/` のみ push 時は **スキップ**（変更検知）。取れない場合は全 sync
- **境界**: R2 = OTC 画像、S3/CloudFront = アプリ JS/CSS — **別ストレージ**

---

## Cloudflare R2（医薬品画像）

- **URL**: `https://images.yutok.dev/otc/{slug}.webp`
- **一括同期（推奨200件）**: `scripts/sync_otc_images_from_matsukiyo.py`
- **上位50品目同期**: `scripts/sync_top50_otc_images.py`
- **単品アップロード**: `scripts/upload-r2-otc-image.sh` / `scripts/upload_r2_otc_image.py`
- **アプリ**: `src/services/medicine_image_urls.py` + カード `onerror` プレースホルダー
- **運用ドキュメント**: [docs/ops/CLOUDFLARE_R2_IMAGES.md](../../ops/CLOUDFLARE_R2_IMAGES.md)

---

## Q: デプロイ失敗・機能障害時のロールバック

<!-- rag-keywords: ロールバック 戻す 失敗 redeploy 復旧 -->

**回答要点**

- **AWS 機能のみ OFF**: ECS Express 設定で翻訳を DeepL、TTS を Web Speech、RAG を Local RAG に戻して redeploy
- **GCP TTS 障害**: Cloud Run で読み上げをブラウザ Web Speech API に戻して redeploy
- **Chat Pipeline v2**: 通常は設定変更不要。緊急時のみ v2 を明示 OFF（[05-chat-pipeline-v2-flags.md](05-chat-pipeline-v2-flags.md)）
- **イメージロールバック**: ECR の前 revision タグ / 前 commit を redeploy
- **KB 問題**: Bedrock ingestion 失敗時も Local RAG がフォールバック — 推奨機能は継続
- **関連**: [docs/ops/AWS_FEATURES_ROLLOUT.md](../../ops/AWS_FEATURES_ROLLOUT.md) ロールバック節

### 例外・境界・よくある誤解

- **誤解**: 「ロールバック = git revert 必須」→ ECS/Cloud Run の **前 revision redeploy** だけで可な場合が多い
- **境界**: GCP 本番に AWS Bedrock を「一時的に」有効化しない — ADR Option C

---

## ロールバック

- AWS 機能のみ OFF: ECS タスク定義で Translate/Polly/Bedrock KB を **レガシー設定（DeepL / Web Speech / Local RAG）** に戻して redeploy
- GCP TTS ロールバック: Cloud Run で読み上げを Web Speech API（ブラウザ）に戻す設定が可能
- Chat Pipeline v2: 通常は設定変更不要。緊急時のみ v2 フラグを明示 OFF（[05-chat-pipeline-v2-flags.md](05-chat-pipeline-v2-flags.md)）

---

## Q: GitHub と GitLab の CI/CD 関係

<!-- rag-keywords: GitHub GitLab 正本 ミラー CI デプロイ どちら push -->

**回答要点**

- **正本（origin）**: GitHub — PR / CI / GCP 本番デプロイ / AWS CodePipeline Source
- **ミラー（gitlab）**: GitLab — バックアップ・GitHub 障害時フェイルオーバー
- **必須**: `git push origin main` で CI・デプロイが走る
- **推奨**: `git push gitlab main` でミラー同期（CI/デプロイには不要）
- **GitLab CI**: `.gitlab-ci.yml` は存在するが、GitHub 復旧後 **GitLab 向け CI/デプロイは停止**
- **関連**: [docs/ops/GITLAB_TEMPORARY_MIGRATION.md](../../ops/GITLAB_TEMPORARY_MIGRATION.md)

### 例外・境界・よくある誤解

- **誤解**: 「GitLab に push すれば AWS も GCP も更新」→ **GitHub main のみ**がデプロイトリガー
- **履歴**: 2026-06 GitHub 停止期間中は GitLab がプライマリだった — 現行は GitHub 正本に復帰

---

## 医薬品相談としての境界

技術 FAQ に詳しく答えても、**症状・薬の選び方・用法用量** は PhysicalOrchestrator 経路で処理する。Concierge は案内役であり、診断・処方を行わない。

---

## 関連ドキュメント

- [01-cross-cloud-architecture.md](01-cross-cloud-architecture.md) — 環境構成
- [07-observability-ops.md](07-observability-ops.md) — ヘルス・ログ・smoke
- [../rag/technical-infra-rag.md](../rag/technical-infra-rag.md) — インフラ横断 FAQ
- [docs/ops/AWS_CODEPIPELINE.md](../../ops/AWS_CODEPIPELINE.md)
- [docs/ops/AWS_BEDROCK_KB.md](../../ops/AWS_BEDROCK_KB.md)
- [docs/ops/LOCAL_RAG.md](../../ops/LOCAL_RAG.md)

## Bedrock Knowledge Base（Concierge RAG）— 旧記載

<details>
<summary>旧 Customer-managed KB（参考）</summary>

- **KB ID（旧）**: `4PEWLBZGTH`
- **ソース同期**: `scripts/sync-concierge-kb-to-s3.sh` → `scripts/sync-aws-bedrock-kb-ingestion.sh`
- **既知ブロッカー**: Titan Embed v2 on-demand クォータ未 provisioning 時は ingestion 429

</details>
