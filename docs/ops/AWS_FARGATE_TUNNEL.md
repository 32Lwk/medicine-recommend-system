# AWS Fargate + Cloudflare Tunnel — ALB なしステージング（SSOT）

> **入口 URL**: `https://aws-medicine.yutok.dev`（Cloudflare Worker + Wake）  
> **オリジン（Tunnel）**: `https://origin-aws-medicine.yutok.dev`  
> **アカウント**: `620992446973`（新） / 旧 `290780119994` はバックアップのみ  
> **移行完了日**: 2026-08-07

ECS Express（ALB 固定 ~$19/月）をやめ、**通常 ECS Fargate + cloudflared サイドカー** で同一 Docker イメージを公開する。**Cloud Run 型**の Wake / idle-stop と組み合わせ、`desiredCount=0` をデフォルトにできる。

---

## 1. 背景と目的

| 課題 | 対策 |
|------|------|
| ECS Express 付属 ALB が **停止中でも課金** | Express 削除 → Tunnel 経由 |
| App Runner 新規不可（2026/4/30〜） | Fargate + Tunnel を採用 |
| 個人 $10–20/月 目標 | ALB $0 + 停止デフォルト |
| 大会要件 | ECS Express / ALB / CodePipeline は **不要**（Fargate + 手動 deploy で可） |

---

## 2. アーキテクチャ

```
ブラウザ → aws-medicine.yutok.dev (Worker: Wake + プロキシ)
              ↓ ORIGIN_URL
         origin-aws-medicine.yutok.dev (Cloudflare Tunnel, Proxied)
              ↓ cloudflared → localhost:8080
         Fargate タスク [cloudflared | app]
              ※ ALB なし / Public IPv4 あり / desiredCount=0 可
```

| コンポーネント | 役割 |
|----------------|------|
| `workers/src/index.js` | 503/接続失敗時に Wake、稼働中はプロキシ + touch |
| Lambda `medicine-recommend-wake-staging` | wake / touch / SSM last-activity |
| Lambda `medicine-recommend-idle-stop-staging` | 10 分毎 → 30 分アイドルで ECS 0 |
| `cloudflared` サイドカー | Tunnel（外向き接続のみ、インバウンドポート開放不要） |
| `app` コンテナ | 既存 ECR イメージ `medicine-recommend:latest` |

### Cloud Run との対応

| 項目 | Cloud Run | 本構成 |
|------|-----------|--------|
| アクセスで起動 | ✅ | ✅ Worker → wake Lambda |
| アイドルで 0 | ✅ | ✅ idle-stop（30 分） |
| 同 URL で待機→表示 | ✅ | ✅ `/health` ポーリング |
| ALB 固定費 | なし | **$0** |
| コールドスタート | 数秒〜1–2 分 | **3〜6 分** |

詳細: [AWS_WAKE_ON_ACCESS.md](./AWS_WAKE_ON_ACCESS.md)

---

## 3. リソース一覧（新アカウント `620992446973`）

| 種別 | 値 |
|------|-----|
| ECS クラスタ | `default` |
| ECS サービス | `medicine-recommend` |
| タスク定義 family | `medicine-recommend-tunnel`（例: `:2`） |
| CPU / Memory | 512 / 1024 MiB |
| cloudflared イメージ | `cloudflare/cloudflared:2025.2.0` |
| app イメージ | `620992446973.dkr.ecr.ap-northeast-1.amazonaws.com/medicine-recommend:latest` |
| Tunnel シークレット | `medicine-recommend/aws-staging/cloudflare-tunnel-token` |
| 状態ファイル | `scripts/.aws-fargate-tunnel.json` |
| デプロイモード | `scripts/.aws-deploy-mode` → `fargate_tunnel` |
| Worker ORIGIN | `workers/wrangler.toml` → `https://origin-aws-medicine.yutok.dev` |

---

## 4. 移行手順

### 4.1 前提

1. **Cloudflare Zero Trust** で Tunnel 作成
2. Public hostname: `origin-aws-medicine.yutok.dev` → `http://localhost:8080`
3. Tunnel トークンを控える（`CLOUDFLARE_TUNNEL_TOKEN`）

#### Tunnel 作成（Cloudflare Dashboard）

1. [Cloudflare Zero Trust](https://one.dash.cloudflare.com/) → **Networks** → **Tunnels**
2. **Create a tunnel** → 名前例: `medicine-recommend-staging`
3. インストール方法: **Docker** → トークンをコピー
4. **Public Hostname**:
   - Subdomain: `origin-aws-medicine`
   - Domain: `yutok.dev`
   - Service: `http://localhost:8080`
5. DNS は自動作成（Proxied）

### 4.2 ワンショット移行

```bash
export AWS_PROFILE=default          # 620992446973
export AWS_ACCOUNT_ID=620992446973
export CLOUDFLARE_TUNNEL_TOKEN='eyJ...'

./scripts/migrate-aws-express-to-fargate-tunnel.sh --confirm
```

内部処理:

1. Express 設定を `scripts/.aws-express-export.json` にエクスポート
2. **ECS Express 削除**（ALB ごと削除）
3. Fargate + Tunnel ECS サービス作成（初期 `desiredCount=0` 推奨）
4. `scripts/.aws-fargate-tunnel.json` 生成

### 4.3 移行後の手動作業

```bash
# Worker ORIGIN を Tunnel に（wrangler.toml 更新済みなら deploy のみ）
cd workers && npm install && npx wrangler deploy

# 確認（起動済みの場合）
curl -s https://origin-aws-medicine.yutok.dev/health
curl -s https://aws-medicine.yutok.dev/health
```

通常利用では **Worker アクセスで自動 Wake** するため、`resume-aws-staging.sh` は手動デプロイ前などにのみ使用。

---

## 5. 移行実施記録（2026-08-07）

### 5.1 新アカウント検証

| 項目 | 結果 |
|------|------|
| ECS Express | **削除済**（describe → Resource not found） |
| ALB | **0 件** |
| WAF | **0 件** |
| ECS サービス | 通常 Fargate、`loadBalancers: []` |
| タスク定義 | `medicine-recommend-tunnel:2` |
| `/health` | Worker / Origin とも 200 OK |
| Budget | $30/月 |

### 5.2 旧アカウント整理（`290780119994`）

| 操作 | 結果 |
|------|------|
| `delete-aws-express-staging.sh --confirm` | Express **INACTIVE** |
| 残存 ALB | Express 削除後も **一時残存** → 手動削除実施 |
| WAF | ALB 削除に伴い **削除** |
| ECS | desired=0 維持 |

```bash
AWS_PROFILE=medicine-recommend-dev AWS_ACCOUNT_ID=290780119994 \
  ./scripts/delete-aws-express-staging.sh --confirm
```

Express 削除直後は ALB が孤立することがある。`aws elbv2 describe-load-balancers` で 0 件になるまで確認し、残存時は listener / WAF デタッチ後に ALB を削除する。

### 5.3 停止デフォルト化

```bash
AWS_PROFILE=default ./scripts/stop-aws-staging.sh
```

| 項目 | 停止後 |
|------|--------|
| desiredCount | 0 |
| Auto Scaling min/max | 0 / 0 |
| CodePipeline | Build ステージ inbound 無効 |
| 状態 | `scripts/.aws-staging-stop-state.json` |

**注意**: `https://aws-medicine.yutok.dev` へのアクセスは Worker が wake Lambda を呼び **ECS が再起動**する。停止維持中は URL にアクセスしない（または stop 後にヘルスチェックを控える）。

---

## 6. スクリプト一覧

| スクリプト | 用途 |
|-----------|------|
| `migrate-aws-express-to-fargate-tunnel.sh` | 移行一括 |
| `setup-aws-fargate-tunnel.sh` | サービス作成/更新 |
| `setup_fargate_tunnel.py` | ECS API 実装 |
| `lib/fargate_tunnel_lib.py` | 2 コンテナタスク定義 |
| `export_aws_express_config.py` | Express バックアップ |
| `delete-aws-express-staging.sh --confirm` | Express + ALB 削除 |
| `tune-aws-fargate-capacity.sh` | CPU/メモリ/scaling |
| `print-aws-fargate-tunnel-config.sh` | 状態表示 |
| `deploy-aws-ecs.sh` | デプロイ（変更なし） |
| `stop-aws-staging.sh` / `resume-aws-staging.sh` | 手動停止/再開 |

---

## 7. デプロイ

CodeBuild / 手動とも **変更なし**（`aws ecs update-service --force-new-deployment`）。

```bash
./scripts/deploy-aws-ecs.sh
```

CodePipeline: `medicine-recommend-main`（停止中は Source→Build 遷移 OFF）。

---

## 8. コスト

詳細試算: [AWS_COST_PLAN.md](./AWS_COST_PLAN.md)

### 単価（ap-northeast-1）

| 項目 | 単価 | 月額（730h） |
|------|------|-------------|
| Fargate 512/1024 | ~$0.031/h | ~$22.5 |
| Public IPv4（タスク 1） | $0.005/h | ~$3.7 |
| Secrets（8 件） | $0.40/secret | ~$3.2 |
| CodePipeline | 固定 | ~$1 |
| ECR + S3 | 従量 | ~$1–2 |

### シナリオ別

| 状態 | USD/月（税抜） |
|------|---------------|
| **停止デフォルト**（desired=0） | **~$6–7** |
| Wake + 週 5h | ~$7–9 |
| 常時 24h | ~$31–32 |
| ALB（移行前 Express） | ~~$19–25~~ → **$0** |

**8/1–8/7 実績（新アカウント）**: $1.28（ELB $0.34 は移行前按分）

---

## 9. 精度・RAG・レイテンシ

| 観点 | 影響 |
|------|------|
| Docker イメージ | **同一**（ECR `medicine-recommend:latest`） |
| 環境変数（OpenAI, Neon, RAG provider 等） | **同一** |
| 推奨スコアリング / Chat Pipeline v2 | **変更なし** |
| RAG（`MEDICINE_RAG_PROVIDER=local`） | **変更なし** |
| ウォーム時 API レイテンシ | **ほぼ同等**（Tunnel + 数十 ms） |
| コールドスタート | **+3〜6 分**（Worker 起動待ち UI） |

変わるのは **ネットワーク経路のみ**（ALB → Tunnel）。アプリ層・データ層は同一。

---

## 10. Budget Lambda

移行後、Lambda 環境変数に追加（未設定の場合は手動 or 再セットアップ）:

```
ECS_DEPLOY_MODE=fargate_tunnel
FARGATE_TASK_FAMILY=medicine-recommend-tunnel
```

```bash
./scripts/setup-aws-budget-staged-actions.sh
```

---

## 11. ロールバック

1. `scripts/.aws-express-export.json` から Express 再作成（`setup-aws-express-gateway-bootstrap.sh` + env 復元）
2. Worker `ORIGIN_URL` を Express URL に戻す → `wrangler deploy`
3. `scripts/.aws-deploy-mode` 削除

---

## 12. トラブルシュート

| 症状 | 原因 | 対処 |
|------|------|------|
| Worker 503 のまま | ECS 停止中 | アクセスで wake 待ち（3–6 分）or `resume-aws-staging.sh` |
| stop 後すぐ起動 | Worker / ヘルスチェックが wake | stop 後は URL にアクセスしない |
| Origin 502 | cloudflared 未起動 / トークン不正 | タスクログ、Secrets の tunnel token 確認 |
| 旧 ALB 残存 | Express 削除後の孤立 ALB | listener 削除 → ALB 削除 → WAF 削除 |
| desired=0 なのに min=1 | resume 後未 stop | `stop-aws-staging.sh` で min/max=0 |

---

## 13. 関連

- [AWS_WAKE_ON_ACCESS.md](./AWS_WAKE_ON_ACCESS.md) — Cloud Run 型運用
- [AWS_COST_PLAN.md](./AWS_COST_PLAN.md) — コスト試算
- [AWS_ACCOUNT_MIGRATION.md](./AWS_ACCOUNT_MIGRATION.md) — アカウント移行
- [AWS_STAGING_CHECKLIST.md](./AWS_STAGING_CHECKLIST.md) — 検証チェックリスト
- [AWS_CODEPIPELINE.md](./AWS_CODEPIPELINE.md) — CI/CD
