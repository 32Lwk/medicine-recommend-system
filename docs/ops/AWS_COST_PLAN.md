# AWS ステージング コスト試算・削減計画

> **アカウント**: `620992446973`（個人）  
> **リージョン**: `ap-northeast-1`  
> **対象 URL**: `https://aws.medicine.yutok.dev`  
> **作成日**: 2026-08-06

GCP 本番（`medicine.yutok.dev`）は別請求。ここでは **AWS ステージングのみ** を対象とする。

---

## 1. 現状インフラ（新アカウント）

| カテゴリ | リソース | 備考 |
|----------|----------|------|
| Compute | ECS Express `medicine-recommend` | Fargate。Express 作成時に **ALB が一体** |
| ネットワーク | ALB + ACM + WAF `medicine-recommend-web-acl` | ALB は Express 経由で削除不可（Express 削除まで残る） |
| CDN | CloudFront `dnv1ek9xdguhs` | static のみ（`static/` → S3） |
| CI/CD | CodePipeline + CodeBuild + CodeStar Connection | push 毎ビルド |
| シークレット | Secrets Manager `medicine-recommend/aws-staging/*` | OpenAI / DB 等 |
| イメージ | ECR `medicine-recommend` | タスク定義参照 |
| ログ | CloudWatch `/ecs/medicine-recommend` 等 | 取り込み + 保管 |
| 未構築 | Bedrock Managed KB / OpenSearch Serverless | Phase 3 未実施（**現時点コスト 0**） |

**現在の運用状態（2026-08-06 時点）**

- `scripts/.aws-staging-stop-state.json` あり → **ECS `desiredCount=0`・Pipeline 自動デプロイ停止** の可能性大
- 大会用一時スケール（512/1024・max 10 タスク）スクリプトは旧アカウント向けに存在。新アカウントでは **未再設定**

---

## 2. 月額コスト試算（USD / 730h 想定）

料金は [AWS 公式](https://aws.amazon.com/pricing/) および ap-northeast-1 公開単価に基づく **概算**。為替 **$1 ≈ ¥150** で円換算例を記載。

### 2.1 固定に近いコスト（ECS 停止中でも発生）

| 項目 | 試算（USD/月） | 円目安 | 根拠 |
|------|----------------|--------|------|
| **ALB**（Express 付属） | $18–28 | ¥2,700–4,200 | 時間課金 ~$0.0243/h + LCU（低トラフィックでも最低 LCUs） |
| **WAF Web ACL** | $6–10 | ¥900–1,500 | ACL $5 + ルール $1/本 + リクエスト |
| **CodePipeline** | $1 | ¥150 | アクティブ 1 本 |
| **Secrets Manager** | $2–5 | ¥300–750 | ~$0.40/secret × 本数 |
| **CloudFront + S3 static** | $1–3 | ¥150–450 | 低トラフィック CDN |
| **ECR 保管** | $1–2 | ¥150–300 | イメージ数 GB 依存 |
| **CloudWatch Logs** | $1–10 | ¥150–1,500 | 取り込み量・保持日数依存 |
| **合計（ECS=0）** | **$30–45** | **¥4,500–6,750** | 「止めても残る」ベースライン |

### 2.2 ECS Fargate 稼働コスト（上記に加算）

Fargate 単価（東京）: vCPU **$0.05056/h**、メモリ **$0.00553/GB/h**

| プロファイル | スペック | タスク数 | ECS 追加（USD/月） | 合計目安（USD/月） |
|--------------|----------|----------|-------------------|-------------------|
| **最小** | 512 CPU / 1024 MiB | 1 | ~$23 | **~$53–68** |
| **移行直後（推奨開始）** | 512/1024 | min 1 / max 2 | ~$23–46 | **~$53–91** |
| **旧 contest 復元値** | 512/1024 | min 1 / max **10** | ~$23（通常）〜 **~$230**（最大スケール時） | ピーク依存 |
| **tune スクリプト既定** | **1024/2048** | min **2** / max 10 | **~$90** | **~$120–135** |
| **大会フル** | 1024/2048 | 一時 10 タスク | +$450/月相当（24h フル時） | 短期スパイク |

### 2.3 従量（利用量依存）

| 項目 | 目安 | 備考 |
|------|------|------|
| **CodeBuild** | $0.05–2/月 | ~$0.005/min × 8–10 分 × push 回数。停止中でも手動実行は課金 |
| **Translate / Polly** | $0.1–2/月 | smoke + 手動テスト程度 |
| **データ転送** | $1–5/月 | ステージング低トラフィック想定 |
| **Bedrock KB**（将来） | **$50+/月〜** | OpenSearch Serverless + KB sync。個人ステージングでは **最優先で見送り推奨** |

### 2.4 シナリオ別サマリー

| シナリオ | USD/月 | 円目安（×150） | 説明 |
|----------|--------|----------------|------|
| **A. 完全停止**（ECS=0, Pipeline 停止） | **$30–45** | ¥4,500–6,750 | 現状に近い。URL は 503 |
| **B. 最小常時**（1 タスク 512/1024） | **$53–68** | ¥8,000–10,000 | 個人ステージングの **推奨上限近辺** |
| **C. 開発 active**（1–2 タスク 512/1024） | **$55–91** | ¥8,250–13,650 | 平日のみ起動なら **実効 ~$40–60** |
| **D. tune 既定**（2×1024/2048 常時） | **$120–135** | ¥18,000–20,000 | **個人用途では非推奨** |
| **E. 旧 $100 Budget 設定** | 上限 $100 | ¥15,000 | `apply-aws-budget-notifications.sh` 既定。C 以下なら余裕、D はギリギリ |

---

## 3. 削減計画（フェーズ別）

### Phase 0 — 即時（コスト効果大・ダウンタイム許容）

| # | アクション | 削減効果 | 手順 | トレードオフ |
|---|-----------|----------|------|--------------|
| 0-1 | **ECS 停止 + Pipeline 停止** | ECS ~$23–90/月 | `./scripts/stop-aws-staging.sh` | `aws.medicine.yutok.dev` 不可。復旧は `resume-aws-staging.sh` |
| 0-2 | **最小スペック固定** | 最大 ~$67/月 vs 1024×2 | `ECS_CPU=512 ECS_MEMORY=1024 ECS_MIN_TASKS=1 ECS_MAX_TASKS=2 ./scripts/tune-aws-ecs-capacity.sh` | 同時接続・重い QA で遅くなる |
| 0-3 | **maxTasks を 2 に制限** | スパイク防止 | 上記と同じ | オートスケール上限低 |
| 0-4 | **不要時は必ず stop** | 実効 50–80% 削減 | Windows タスクスケジューラ or 手動 | 起動待ち 3–6 分 |

**目標**: 使わない月は **Scenario A（~$35）**、使う週だけ **Scenario B（+$23）**。

### Phase 1 — 1 週間以内（運用自動化・新アカウント移行）

| # | アクション | 内容 |
|---|-----------|------|
| 1-1 | **Budget 段階 Actions を新アカウントに再構築** | `./scripts/setup-aws-budget-staged-actions.sh` + `apply-aws-budget-notifications.sh`（SNS ARN を `620992446973` に） |
| 1-2 | **予算上限の見直し** | 個人向け **$50/月** 推奨（後述 Ask で確定） |
| 1-3 | **平日スケジュール** | `setup-aws-staging-schedule.ps1` を新アカウント用に更新（プロファイル `default` or 新 dev ユーザー） |
| 1-4 | **CloudWatch Logs 保持 7 日** | Budget stage3 / 手動 `aws logs put-retention-policy` |
| 1-5 | **CodeBuild キャッシュ維持** | ビルド時間短縮 → CodeBuild 従量削減（既存 buildspec 活用） |

### Phase 2 — 1 ヶ月以内（固定費の圧縮）

| # | アクション | 削減効果 | 備考 |
|---|-----------|----------|------|
| 2-1 | **WAF ルール最小化** | $1–3/月 | ステージング単独なら IP 制限 or 削除検討。**Express ALB 直結のため WAF 外すと ALB 削除不可問題は残る** |
| 2-2 | **静的配信の整理** | $1–2/月 | CloudFront は GCP 本番と役割分担済み。AWS 側 invalidation 頻度を post_build 条件分岐のまま維持 |
| 2-3 | **Secrets 統合** | $1–2/月 | キー数を減らす（1 JSON secret にまとめる等） |
| 2-4 | **旧アカウント `290780119994` 完全停止** | 二重請求防止 | ECS=0, Pipeline 停止, 30 日後削除（[AWS_ACCOUNT_MIGRATION.md](./AWS_ACCOUNT_MIGRATION.md)） |

### Phase 3 — 任意（大きな構造変更）

| # | アクション | 削減 | 判断基準 |
|---|-----------|------|----------|
| 3-1 | **Bedrock KB 見送り継続** | $50+/月 回避 | `CONCIERGE_RAG_PROVIDER=local` で十分な間は不要 |
| 3-2 | **Pipeline を手動デプロイのみ** | $1 + CodeBuild 削減 | push 毎自動デプロイが不要なら Source 遷移を常時 OFF |
| 3-3 | **Express → より軽量構成** | ALB 固定費 $18+ | **Express では ALB 単体削除不可**。Express ごと作り直す大工事が必要 → **個人では非推奨** |

---

## 4. 推奨運用モデル（個人・最小コスト）

```
通常時（使わない日）
  → stop-aws-staging.sh（ECS 0, Pipeline OFF）
  → 固定費 ~$35/月

開発・デモ前（30 分前）
  → resume-aws-staging.sh
  → 512/1024 × 1 タスク
  → 追加 ~$0.03/h（~¥5/h）

GitHub push 後の確認が必要な日
  → resume してから merge / push
  → CodeBuild 1 回 ~$0.05

月次上限
  → Budget $50 + 段階 Lambda（[AWS_BUDGET_STAGED_ACTIONS.md](./AWS_BUDGET_STAGED_ACTIONS.md)）
```

**やってはいけない（個人アカウント）**

- `tune-aws-ecs-capacity.sh` **無引数**（1024/2048 × min 2）の常時運用
- contest 用 **maxTasks=10** を復元したまま放置
- Bedrock KB をクォータ取得前に構築
- 旧・新 **2 アカウント同時稼働**

---

## 5. 新アカウントで未実施のコスト関連タスク

- [x] WAF 削除 — `./scripts/remove-aws-waf.sh`（2026-08-06）
- [x] Budget $30 + 段階 Lambda — `setup-aws-budget-staged-actions.sh` + `BUDGET_LIMIT=30 apply-aws-budget-notifications.sh`
- [x] コールドスタート — `./scripts/setup-aws-staging-cold-start.sh`（512/1024, maxTasks=1, ECS=0 既定）
- [ ] 個人用 stop/resume スケジュール（Task Scheduler）の再登録（任意）
- [ ] 旧アカウントリソース停止確認

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
| [AWS_BUDGET_STAGED_ACTIONS.md](./AWS_BUDGET_STAGED_ACTIONS.md) | 予算超過時の自動縮小 |
| [AWS_ACCOUNT_MIGRATION.md](./AWS_ACCOUNT_MIGRATION.md) | 移行 runbook |
| [AWS_CODEPIPELINE.md](./AWS_CODEPIPELINE.md) | CI/CD コスト目安 |

---

## 8. 確定した運用方針（2026-08-06 確認）

| 項目 | 方針 |
|------|------|
| **月次予算** | **$30/月以下** |
| **可用性** | **必要時のみ起動**（停止がデフォルト） |
| **利用時間** | **週 5 時間未満** |
| **WAF** | **削除**（ALB 直結・コスト優先） |
| **Bedrock KB** | **導入しない**（local RAG のみ） |
| **旧アカウント** | **しばらくバックアップとして残す**（二重請求に注意） |

### $30/月達成のための具体プラン

**現実**: ECS Express 付属 ALB だけで **~$18–28/月** の固定費が発生するため、**ECS=0 の停止状態でも $30 をわずかに超える可能性**がある。$30 厳守には次の組み合わせが必要。

| 優先度 | アクション | 効果 |
|--------|-----------|------|
| **P0** | 使わない日は常に `stop-aws-staging.sh` | ECS $0。実効 ~$30–40/月 → 利用週のみ +$1–2 |
| **P0** | **WAF 削除** | **-$6–10/月** | `./scripts/remove-aws-waf.sh`（**2026-08-06 実施済み**） |
| **P0** | ECS は **512/1024 × 1 タスク**のみ、maxTasks=1 | 起動中でも ~$0.03/h（週 5h ≈ **+$0.6/月**） |
| **P1** | Budget **$30** + stage4 で自動停止 | 超過前に ECS 0 |
| **P1** | CloudWatch Logs **7 日保持** | -$1–5/月 |
| **P1** | CodePipeline は停止中 **Source 遷移 OFF**（stop スクリプト済み） | push 誤爆による CodeBuild 防止 |
| **P2** | Secrets 本数整理 | -$1–2/月 |
| **P2** | 旧アカウントは **ECS=0・Pipeline 停止**で請求最小化 | バックアップ維持しつつ二重 ECS 回避 |

**週 5 時間未満・停止デフォルトの試算**

| 構成 | USD/月 | $30 以内 |
|------|--------|----------|
| 停止 + WAF 削除 + Logs 7d | **$24–32** | **おおむね達成** |
| 上記 + 週 5h 起動（512/1024×1） | **$25–34** | ギリギリ〜微超過 |
| WAF 維持のまま | +$6–10 | **超過しやすい** |

**結論**: **WAF 削除 + 停止デフォルト** が $30 目標の必須条件。Express ALB 固定費のため、**完全な $30 以下はトラフィック・Logs 量次第で厳しい** — Budget $30 + 自動停止で上限を守る。

### WAF 削除手順（未実装）

```bash
# 1. ALB から Web ACL デタッチ
aws wafv2 disassociate-web-acl \
  --resource-arn <ALB_ARN> \
  --region ap-northeast-1

# 2. Web ACL 削除
aws wafv2 delete-web-acl \
  --name medicine-recommend-web-acl \
  --scope REGIONAL \
  --id <WEB_ACL_ID> \
  --lock-token <LOCK_TOKEN> \
  --region ap-northeast-1
```

削除後も Express / ALB / ECS はそのまま利用可能。

### 旧アカウント（290780119994）バックアップ方針

- **残す**: 設定・イメージの参照用
- **必須**: ECS `desiredCount=0`、CodePipeline 停止（稼働中タスクがあると **二重で Fargate 課金**）
- 新アカウント安定後（目安 30 日）に再評価

## 9. アクセス時自動起動（Wake on Access）

**Lambda + Cloudflare Worker** で 503 時に ECS を自動起動。詳細: [AWS_WAKE_ON_ACCESS.md](./AWS_WAKE_ON_ACCESS.md)

| 項目 | コスト |
|------|--------|
| Lambda / Worker | **ほぼ $0**（無料枠内） |
| 起動後 Fargate | **~$0.03/時**（手動 resume と同じ） |
| 放置すると | 24h 稼働で **~+$23/月** → 終了後 `stop-aws-staging.sh` |

**Cloudflare DNS**: Wake URL は **`aws-medicine.yutok.dev`（Proxied）**。従来の `aws.medicine.yutok.dev` は DNS only のまま。詳細: [AWS_WAKE_ON_ACCESS.md](./AWS_WAKE_ON_ACCESS.md)
