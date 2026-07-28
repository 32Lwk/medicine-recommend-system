# 監視・運用・デプロイ確認

> ヘルスチェック・ログ・smoke の SSOT。デプロイ手順は [03-deployment-operations.md](03-deployment-operations.md)、横断 FAQ は [../rag/technical-infra-rag.md](../rag/technical-infra-rag.md)。

## Q: `/health` エンドポイントで何が確認できるか

<!-- rag-keywords: health ヘルスチェック git_commit 稼働 確認 エンドポイント -->

**回答要点**

- **URL**: `GET /health`（GCP 本番・AWS ステージング・ローカル共通）
- **応答**: `{ "status": "ok", "git_commit": "<hash>" }`
- **用途**: Cloud Run startup probe、ALB ヘルスチェック、デプロイ反映確認
- **設計**: DB・LLM **非依存**の軽量エンドポイント — 起動完了の早期判定用（`main.py` `health_check`）
- **利用者向け**: commit hash は公開情報として述べてよい（[00-disclosure-policy.md](00-disclosure-policy.md)）
- **関連**: [03-deployment-operations.md](03-deployment-operations.md)

### 例外・境界・よくある誤解

- **誤解**: 「`/health` = DB 接続 OK」→ DB 状態は **含まない**。DB 可用性は管理画面 `/admin/system_status` 等
- **typo**: 外部モニタが `/helth` を叩く 404 が CloudWatch に記録される — 正しくは `/health`
- **GCP 注意**: startup probe 失敗（DB 初期化前のタイムアウト等）で新 revision が拒否される事例あり — probe 設計と `/health` の軽量性の整合を確認

---

## ヘルスチェック（公開）

- `GET /health` — `{ "status": "ok", "git_commit": "<hash>" }`
- `GET /health/aws` — 機能の利用有無（翻訳/TTS/KB/CDN 等）。**Secrets や設定変数名は含まない**

利用者向け回答では「公開されているデプロイ情報」として commit や URL を述べてよい。  
「環境変数を読み取った」等のメタは出さない。

---

## Q: `/health/aws` の用途と返却内容

<!-- rag-keywords: health/aws AWS 機能 フラグ Translate Polly Bedrock KB 確認 -->

**回答要点**

- **URL**: `GET /health/aws` — **AWS ステージング向け**（GCP 本番でも呼べるが AWS 機能は off）
- **返却例**: 翻訳プロバイダ、TTS プロバイダ、Bedrock KB 利用有無、KB ID、Comprehend Medical 有無、static CDN ベース URL、医薬品画像 CDN ベース
- **用途**: CodeBuild smoke、運用者の機能フラグ確認、Concierge ランタイム参照（Phase Q3 — シークレット名は除外）
- **コード**: `main.py` `health_aws_features` → `config/aws_features.py`
- **関連**: [01-cross-cloud-architecture.md](01-cross-cloud-architecture.md)、[03-deployment-operations.md](03-deployment-operations.md)

### 例外・境界・よくある誤解

- **誤解**: 「API キーや DB URL が返る」→ **利用有無と公開 ID のみ**。シークレット値は含まない
- **Concierge 回答**: 内部参照に使っても、利用者向け出力にエンドポイント名や設定変数名を **そのまま出さない**

---

## Q: ログはどこに出力されるか

<!-- rag-keywords: ログ CloudWatch Cloud Logging log 出力 先 確認 -->

**回答要点**

| 環境 | ログ先 | ロググループ / 備考 |
|------|--------|---------------------|
| GCP Cloud Run | Cloud Logging | リクエスト・例外・LLM 呼び出し等 |
| AWS ECS | CloudWatch Logs | `/ecs/medicine-recommend` |
| CodeBuild | CloudWatch Logs | `/aws/codebuild/medicine-recommend-build` |
| 開発 | リポジトリ `log/` | JSONL・Markdown 分析成果物 |

- **分析スキル**: GCP = `.cursor/skills/gcp-log-analysis/`、AWS = `.cursor/skills/aws-log-analysis/`
- **エクスポート**: `scripts/export_aws_logs.py`、`scripts/prepare_aws_log_analysis.py`
- **関連**: [04-data-security.md](04-data-security.md)、[docs/ops/AWS_LOG_ANALYSIS.md](../../ops/AWS_LOG_ANALYSIS.md)

### 例外・境界・よくある誤解

- **誤解**: 「`log/` = 本番利用者の全チャット」→ 主に **開発・検証用**。本番は Cloud Logging / CloudWatch
- **境界**: ログに PII が混ざる可能性 — プロジェクト方針として `log/` は Git 追跡（マスクは別 issue）

---

## ログ

| 環境 | ログ先 |
|------|--------|
| GCP Cloud Run | Cloud Logging |
| AWS ECS | CloudWatch `/ecs/medicine-recommend` |
| CodeBuild | CloudWatch `/aws/codebuild/medicine-recommend-build` |
| 開発 | `log/` 配下 JSONL・Markdown |

---

## Q: デプロイ反映を commit で確認する手順

<!-- rag-keywords: デプロイ 反映 確認 git_commit revision 待ち -->

**回答要点**

- **手順**: push 後、`curl -s https://<host>/health | jq .git_commit` が **push した commit** と一致するまで待つ
- **AWS 自動化**: CodeBuild post_build の `wait-staging-health-commit.sh` が同一確認を自動実行
- **CANARY 中**: 旧タスクと新タスクが並行する時間帯あり — `/health` 200 は継続するが commit が混在する場合がある
- **GCP**: Cloud Build 完了 → Cloud Run 新 revision → startup probe 通過後に traffic 切替
- **関連**: [03-deployment-operations.md](03-deployment-operations.md)

### 例外・境界・よくある誤解

- **誤解**: 「ECS `services-stable` = 新 commit 応答」→ **実際の `/health` 確認**の方が早く正確（採用済み）
- **オンボーディング UI**: commit 日付はサーバー `runtime_client_config` から自動表示 — 手動更新不要

---

## デプロイ確認手順（運用者向け・公開手順として説明可）

**GCP 本番**

- Cloud Build → Cloud Run
- `/health` の `git_commit` で反映 revision を確認

**AWS ステージング**

- GitHub main push → CodePipeline → CodeBuild → ECR → ECS redeploy
- post_build: 条件付き static S3 同期 + 毎回 smoke（Translate / Polly / health）
- `/health` + `/health/aws` で確認

---

## Q: CodePipeline smoke テストの内容

<!-- rag-keywords: smoke テスト CodePipeline aws-staging-smoke Translate Polly CDN 自動 -->

**回答要点**

- **スクリプト**: `scripts/aws-staging-smoke.sh` — CodeBuild post_build 毎回実行
- **検証項目**:
  1. `/health` の `git_commit` が期待 commit と一致
  2. `POST /api/smoke/aws-translate` — Amazon Translate 疎通（サンプル日本語 → 英語）
  3. Amazon Polly TTS 疎通
  4. CloudFront 経由で `static/css/main.css` が取得可能
- **失敗時**: advisory（strict 未設定時は Pipeline 警告のみで **デプロイ自体は成功**していることが多い）
- **典型失敗原因**: ECS task role に Translate/Polly 権限なし → `setup-aws-ecs-task-role.sh`
- **関連**: [docs/ops/AWS_CODEPIPELINE.md](../../ops/AWS_CODEPIPELINE.md)

### 例外・境界・よくある誤解

- **誤解**: 「smoke FAIL = サイトダウン」→ `/health` 200 なら **アプリは稼働**。AWS 機能の IAM 不足が多い
- **Translate smoke**: `translate` プロバイダ OFF 時は `/api/smoke/aws-translate` が 404 — 設定意図的 OFF なら正常

---

## CodePipeline smoke（自動）

`scripts/aws-staging-smoke.sh` — デプロイ commit 一致、Translate/Polly、CloudFront CSS

---

## Q: AWS インフラ監視（WAF / CloudWatch アラーム）

<!-- rag-keywords: WAF CloudWatch アラーム 監視 5xx CPU Rate limit ALB -->

**回答要点**

- **CloudWatch Log Group**: `/ecs/medicine-recommend` — ECS タスク stdout/stderr
- **WAF**: ALB に Web ACL（Rate limit 2000/5分/IP + AWS CommonRuleSet）
- **アラーム**: CPU 高騰、5xx、Pipeline 失敗等（SNS 未設定時はコンソールのみ）
- **セットアップ**: `scripts/setup-aws-infra.sh`（CloudWatch + WAF + CloudFront）
- **関連**: [docs/ops/AWS_INFRA.md](../../ops/AWS_INFRA.md)

### 例外・境界・よくある誤解

- **誤解**: 「GCP 本番にも WAF 同一構成」→ WAF/CloudFront は **AWS ステージング専用**
- **502/503 調査**: CANARY デプロイ中のタスク入替は `/health` 200 が継続するケースあり — 502/503 件数と時刻を CloudWatch で確認

---

## Q: AWS CloudWatch ログ分析の手順

<!-- rag-keywords: AWS ログ 分析 CloudWatch export analyze 障害 調査 -->

**回答要点**

- **エクスポート**: `scripts/export_aws_logs.py` → `log/raw/downloaded-aws-logs-*.json`
- **解析**: `scripts/analyze_aws_logs.py` — セクション別抽出（HTTP エラー、デプロイ、NLU 等）
- **差分 prepare**: `scripts/prepare_aws_log_analysis.py`（任意 — 増分取得）
- **成果物**: `log/analysis/downloaded-aws-logs-*/`、`log/analysis/YYYY-MM-DD_downloaded-aws-logs-*.md`
- **NLU 連携**: 特定セッション → `tests/fixtures/v2_golden_aws_6_sessions.yaml` でローカル再現
- **関連**: [docs/ops/AWS_LOG_ANALYSIS.md](../../ops/AWS_LOG_ANALYSIS.md)

### 例外・境界・よくある誤解

- **境界**: AWS ログ分析は **ステージング中心**。GCP 本番は gcp-log-analysis スキル

---

## Q: Concierge 技術 FAQ の SSOT 検証

<!-- rag-keywords: Concierge SSOT 検証 verify contract 技術 FAQ メンテナンス -->

**回答要点**

- **SSOT 検証**: `./scripts/verify-concierge-ssot.sh` — ドキュメント整合・リンク
- **FAQ 契約**: `./scripts/concierge-technical-faq-contract.sh` — 40 項目 contract（Bedrock 本番 GO 条件の一つ）
- **CodeBuild**: post_build で `verify-concierge-ssot.sh` を KB/static と **並列**実行
- **メンテナンス**: インフラ変更時は該当 `.md` + `docs/ops/` を同時更新（[docs/ops/CONCIERGE_TECH_FAQ_MAINTENANCE.md](../../ops/CONCIERGE_TECH_FAQ_MAINTENANCE.md)）
- **関連**: [technical/README.md](README.md)

### 例外・境界・よくある誤解

- **誤解**: 「SSOT 更新 = 自動で KB ingestion 完了」→ S3 sync + ingestion は **非同期**。Local RAG はリポジトリ直読みで即反映

---

## 既知ブロッカー・監視上の注意（公開情報）

| 事象 | 影響 | 対処 |
|------|------|------|
| Bedrock KB ingestion Titan Embed 429 | KB 取り込みのみ | AWS Support クォータ provisioning。Local RAG は継続 |
| `/helth` typo 404 | 外部モニタのみ | モニタ URL を `/health` に修正 |
| GCP startup probe 連続失敗 | 新 revision 起動拒否 | `/health` 軽量性と DB 初期化タイミングの確認 |
| CodeBuild post_build smoke FAIL | Pipeline 警告 | task role IAM 確認。デプロイ自体は成功のことが多い |
| CANARY タスク並行 | commit 混在の短時間帯 | `/health` 再確認で安定化を待つ |

---

## 関連ドキュメント

- [01-cross-cloud-architecture.md](01-cross-cloud-architecture.md) — 環境構成
- [03-deployment-operations.md](03-deployment-operations.md) — CI/CD
- [04-data-security.md](04-data-security.md) — データ・公開境界
- [../rag/technical-infra-rag.md](../rag/technical-infra-rag.md) — インフラ横断 FAQ
- [docs/ops/AWS_CODEPIPELINE.md](../../ops/AWS_CODEPIPELINE.md)
- [docs/ops/AWS_LOG_ANALYSIS.md](../../ops/AWS_LOG_ANALYSIS.md)
- [docs/ops/AWS_STAGING_CHECKLIST.md](../../ops/AWS_STAGING_CHECKLIST.md)
- [docs/ops/SMOKE_MANUAL.md](../../ops/SMOKE_MANUAL.md)
