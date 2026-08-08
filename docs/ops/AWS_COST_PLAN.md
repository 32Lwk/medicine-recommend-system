# AWS ステージング コスト試算・削減計画

> **アカウント**: `620992446973`（新） / 旧 `290780119994`（バックアップ・ALB 削除済 2026-08-07）  
> **リージョン**: `ap-northeast-1`  
> **対象 URL**: `https://aws-medicine.yutok.dev`  
> **作成日**: 2026-08-06 / **移行後更新**: 2026-08-07

GCP 本番（`medicine.yutok.dev`）は別請求。ここでは **AWS ステージングのみ** を対象とする。

**2026-08-07**: ECS Express + ALB を廃止し **Fargate + Cloudflare Tunnel** へ移行。ALB 固定費 **$0**。詳細: [AWS_FARGATE_TUNNEL.md](./AWS_FARGATE_TUNNEL.md)

---

## 1. 現状インフラ（移行後 — 新アカウント `620992446973`）

| カテゴリ | リソース | 備考 |
|----------|----------|------|
| Compute | ECS Fargate `medicine-recommend` | タスク定義 `medicine-recommend-tunnel`（app + cloudflared） |
| 入口 | Cloudflare Tunnel | `origin-aws-medicine.yutok.dev` — **ALB なし** |
| フロント | Cloudflare Worker | Wake + プロキシ @ `aws-medicine.yutok.dev` |
| CDN | CloudFront `dnv1ek9xdguhs` | static のみ（`static/` → S3） |
| CI/CD | CodePipeline + CodeBuild + CodeStar Connection | push 毎ビルド（停止中は Source→Build OFF） |
| シークレット | Secrets Manager × 8 | OpenAI / DB / Tunnel token 等 |
| イメージ | ECR `medicine-recommend` | タスク定義参照 |
| ログ | CloudWatch `/ecs/medicine-recommend` 等 | 取り込み + 保管 |
| Wake / Stop | Lambda + EventBridge | idle-stop 10 分毎、30 分アイドルで ECS 0 |
| 未構築 | Bedrock Managed KB / OpenSearch Serverless | **現時点コスト 0** |

**現在の運用状態（2026-08-07）**

- **停止デフォルト**: `desiredCount=0`、Auto Scaling min/max=0（`stop-aws-staging.sh` 実施済）
- Worker アクセスで Wake → 利用後 30 分で自動 stop
- Budget **$30/月** + 段階 Lambda
- 旧アカウント: Express / ALB / WAF **削除済**、ECS=0

---

## 2. 月額コスト試算（USD / 730h 想定）

料金は [AWS 公式](https://aws.amazon.com/pricing/) および ap-northeast-1 公開単価に基づく **概算**。

### 2.1 固定に近いコスト（ECS 停止中 — **移行後**）

| 項目 | 試算（USD/月） | 根拠 |
|------|----------------|------|
| ~~**ALB**~~ | **$0** | **2026-08-07 削除**（Express 廃止 + Tunnel） |
| ~~**WAF**~~ | **$0** | 2026-08-06 新アカウント削除 / 2026-08-07 旧アカウント削除 |
| **CodePipeline** | ~$1 | アクティブ 1 本 |
| **Secrets Manager** | ~$3.2 | $0.40 × 8 本 |
| **CloudFront + S3 static** | $1–3 | 低トラフィック CDN |
| **ECR 保管** | $1–2 | イメージ GB 依存 |
| **CloudWatch Logs** | $1–5 | 7 日保持推奨 |
| **Lambda wake / idle-stop** | ~$0 | 無料枠内 |
| **合計（ECS=0・新アカウント）** | **~$6–7** | 停止デフォルト |

旧アカウント（`290780119994`、ALB 削除後）: ECR + Secrets + S3 のみ **~$5–8/月**。

### 2.2 ECS Fargate 稼働コスト（上記に加算）

Fargate 単価（東京）: vCPU **$0.05056/h**、メモリ **$0.00553/GB/h**  
512 CPU / 1024 MiB ≈ **$0.031/h** + Public IPv4 **$0.005/h** ≈ **$0.036/h**

| プロファイル | スペック | ECS 追加（USD/月） |
|--------------|----------|-------------------|
| **最小（推奨）** | 512/1024 × 1 タスク | ~$22.5 + IPv4 ~$3.7 ≈ **~$26** |
| 週 5h 利用 | 上記 × ~20h/月 | **~$0.7** 変動のみ |
| 常時 1 タスク | 730h | **~$26** 変動 |

### 2.3 シナリオ別サマリー（移行後）

| シナリオ | USD/月 | 説明 |
|----------|--------|------|
| **A. 停止デフォルト**（新のみ） | **~$6–7** | **推奨**。Worker wake で利用 |
| **B. 停止 + 週 5h**（新のみ） | **~$7–9** | **$10–20 目標達成** |
| **C. 常時 1 タスク** | **~$31–32** | 開発 active 時 |
| **D. 新 + 旧（両方停止）** | **~$11–15** | 2026-08-07 整理後 |
| **E. 移行前（Express+ALB 停止）** | ~~$23–25~~ | ALB 固定費あり |

### 2.4 実績（Cost Explorer 2026-08-01〜08-07）

| アカウント | 合計 | 内訳（主要） |
|-----------|------|-------------|
| 新 `620992446973` | **$1.28** | ECS $0.46, ELB $0.34（移行前按分）, VPC $0.28, Secrets $0.05 |
| 旧 `290780119994` | **~$30** | ECS $17.76, ELB $3.02, WAF $1.19, VPC $3.63（8/7 以降 ALB/WAF $0 見込） |

---

## 3. 削減計画（フェーズ別 — 2026-08-07 更新）

### 完了済み（Phase 0–2）

| # | アクション | 状態 | 効果 |
|---|-----------|------|------|
| ✅ | **Express → Fargate + Tunnel** | 2026-08-07 | ALB 固定 **-$19〜25/月** |
| ✅ | **WAF 削除**（新・旧） | 2026-08-06 / 08-07 | **-$6–10/月** |
| ✅ | **旧 ALB 削除** | 2026-08-07 | 二重請求解消 |
| ✅ | **停止デフォルト** | `stop-aws-staging.sh` | ECS 変動 $0 |
| ✅ | **Budget $30 + 段階 Lambda** | 設定済 | 上限ガード |
| ✅ | **512/1024 × maxTasks=1** | cold-start 設定 | 起動中 ~$0.036/h |

### 残タスク（任意）

| # | アクション | 内容 |
|---|-----------|------|
| P1 | Budget Lambda `ECS_DEPLOY_MODE=fargate_tunnel` | `setup-aws-budget-staged-actions.sh` 再実行 |
| P1 | CloudWatch Logs **7 日保持** | stage3 / 手動 |
| P2 | Secrets 本数整理 | -$1–2/月 |
| P2 | 8 月後半 Cost Explorer で ELB=$0 確認 | 移行効果検証 |
| P3 | draw.io 図の ALB 経路更新 | [AWS_ARCHITECTURE_DIAGRAMS.md](./AWS_ARCHITECTURE_DIAGRAMS.md) |

---

## 4. 推奨運用モデル（移行後 — Cloud Run 型）

```
通常時（使わない日）
  → 自動: idle-stop（30 分）または stop-aws-staging.sh
  → 固定費 ~$6–7/月（新アカウントのみ）

利用時
  → https://aws-medicine.yutok.dev を開く（Worker が wake）
  → 3–6 分待ち → 同一 URL でアプリ表示
  → 追加 ~$0.036/h

GitHub push 後の確認
  → resume または Worker wake 後に Pipeline 実行
  → CodeBuild 1 回 ~$0.05

月次上限
  → Budget $30 + 段階 Lambda
```

**やってはいけない**

- 常時 24h 稼働（~$32/月）
- stop 後にヘルスチェックで Worker wake を連発
- 旧・新 **2 アカウントで ECS 同時稼働**
- `tune-aws-ecs-capacity.sh` 無引数（1024/2048 × min 2）

---

## 5. コスト関連タスク一覧

- [x] WAF 削除（新 2026-08-06 / 旧 2026-08-07）
- [x] Budget $30 + 段階 Lambda
- [x] Fargate + Tunnel 移行（2026-08-07）
- [x] 旧 Express / ALB 削除（2026-08-07）
- [x] 停止デフォルト（`stop-aws-staging.sh` 2026-08-07）
- [ ] Budget Lambda `ECS_DEPLOY_MODE=fargate_tunnel`
- [ ] 個人用 stop/resume スケジュール（任意）
- [ ] 8 月請求で ELB 按分 $0 確認

---

## 6. 監視・確認コマンド

```bash
# 現在タスク数
aws ecs describe-services --cluster default --services medicine-recommend \
  --region ap-northeast-1 \
  --query 'services[0].{desired:desiredCount,running:runningCount}'

# 請求（要 Cost Explorer 有効化）
aws ce get-cost-and-usage \
  --time-period Start=2026-08-01,End=2026-08-07 \
  --granularity DAILY \
  --metrics UnblendedCost \
  --region us-east-1

# 停止 / 再開
./scripts/stop-aws-staging.sh
./scripts/resume-aws-staging.sh
```

---

## 7. 関連ドキュメント

| ドキュメント | 内容 |
|--------------|------|
| [AWS_FARGATE_TUNNEL.md](./AWS_FARGATE_TUNNEL.md) | **移行 SSOT** — アーキテクチャ・検証・影響 |
| [AWS_WAKE_ON_ACCESS.md](./AWS_WAKE_ON_ACCESS.md) | Cloud Run 型 Wake / idle-stop |
| [AWS_BUDGET_STAGED_ACTIONS.md](./AWS_BUDGET_STAGED_ACTIONS.md) | 予算超過時の自動縮小 |
| [AWS_ACCOUNT_MIGRATION.md](./AWS_ACCOUNT_MIGRATION.md) | アカウント移行 runbook |
| [AWS_CODEPIPELINE.md](./AWS_CODEPIPELINE.md) | CI/CD コスト目安 |

---

## 8. 確定した運用方針（2026-08-07 更新）

| 項目 | 方針 |
|------|------|
| **月次予算** | **$30/月以下** |
| **可用性** | **Cloud Run 型** — Worker wake + idle-stop 30 分 |
| **利用時間** | **週 5 時間未満** |
| **入口** | Fargate + Cloudflare Tunnel（**ALB なし**） |
| **WAF** | **削除済**（Tunnel + Cloudflare エッジで十分） |
| **Bedrock KB** | **導入しない**（local RAG のみ） |
| **旧アカウント** | ALB/WAF 削除済。ECR/Secrets 参照用に残存 |

### $10–20/月 達成条件（移行後）

| 構成 | USD/月 | 達成 |
|------|--------|------|
| 新アカウント・停止デフォルト | **~$6–7** | ✅ |
| 新 + 旧（両方停止） | **~$11–15** | ✅ |
| 上記 + 週 5h 利用 | **~$7–9**（新のみ） | ✅ |

**結論**: Express + ALB 廃止により **停止デフォルトで $10–20/月 達成可能**。Budget $30 + idle-stop で上限を守る。

### 旧アカウント（290780119994）

- **2026-08-07**: Express / ALB / WAF **削除済**
- **残存**: ECR / Secrets / S3（~$5–8/月）
- 新アカウント安定後（目安 30 日）に完全削除を再評価

## 9. アクセス時自動起動 + アイドル自動停止

**Cloud Run 型運用** — 入口は `https://aws-medicine.yutok.dev` のみ。詳細: [AWS_WAKE_ON_ACCESS.md](./AWS_WAKE_ON_ACCESS.md)

| 項目 | コスト |
|------|--------|
| Lambda wake / idle-stop / Worker | **ほぼ $0** |
| 起動後 Fargate + Public IPv4 | **~$0.036/時**（アイドル 30 分で自動 stop） |
| ALB 固定 | **$0**（2026-08-07 移行完了） |
