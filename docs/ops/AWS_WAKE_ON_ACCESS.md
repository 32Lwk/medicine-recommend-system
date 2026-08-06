# AWS ステージング — アクセス時自動起動（Wake on Access）

> **前提**: ECS コールド停止中（`stop-aws-staging.sh`）  
> **方式**: Cloudflare Worker → Lambda Function URL → ECS 起動

## URL の使い分け

| URL | DNS | 用途 |
|-----|-----|------|
| `https://aws.medicine.yutok.dev` | **DNS only（灰色雲）** | 通常のステージング URL（CI/CD・E2E・本番同等）。ECS 稼働中のみ利用 |
| `https://aws-medicine.yutok.dev` | **Proxied（オレンジ雲）** | **Wake on Access** — 停止中にアクセスすると自動起動 |

`aws.medicine.yutok.dev` は 2 段サブドメインのため Cloudflare 無料 Universal SSL の対象外。**Worker + Proxied は `aws-medicine.yutok.dev`（1 段）を使う。**

## 仕組み

```
ユーザー → aws-medicine.yutok.dev (Cloudflare Worker, Proxied)
              ↓ Express origin が 503 / 接続失敗
              ↓ Lambda wake（非同期）
              ↓ 「起動中」HTML（15秒ごと自動更新）
         3〜6 分後 → 通常のステージング UI
```

| コンポーネント | 役割 |
|----------------|------|
| `workers/src/index.js` | 503 検知 → wake API 呼び出し → 待機ページ |
| Lambda `medicine-recommend-wake-staging` | ECS min/max/desired 復元 + タスク起動 |
| `scripts/setup-aws-wake-staging.sh` | Lambda / IAM / Function URL 作成 |

## 1. AWS 側セットアップ

```bash
AWS_PROFILE=default ./scripts/setup-aws-wake-staging.sh
```

生成物:

- Lambda + Function URL
- `scripts/.aws-wake-staging.json`（**WAKE_TOKEN 含む — Git にコミットしない**）

## 2. Cloudflare DNS（`aws-medicine.yutok.dev`）

**DNS** → `yutok.dev` でレコード追加:

| 項目 | 値 |
|------|-----|
| Type | CNAME |
| Name | `aws-medicine` |
| Target | ALB DNS（`aws.medicine` と同じ。例: `ecs-express-gateway-alb-....elb.amazonaws.com`） |
| Proxy | **Proxied（オレンジ雲）** |

`aws.medicine` は **DNS only のまま**変更不要。

## 3. Cloudflare Worker デプロイ

### 方式 A — Dashboard（Git 連携・推奨）

| 項目 | 値 |
|------|-----|
| Project name | `aws-staging-wake` |
| Root directory | `workers` |
| Production branch | `main` |
| Deploy command | `npm install && npx wrangler deploy` |

**Secrets**（3 つ）:

| Variable name | Value |
|---------------|-------|
| `WAKE_API_URL` | Lambda Function URL |
| `WAKE_TOKEN` | Lambda の WAKE_TOKEN |
| `ORIGIN_URL` | Express 直 URL（Worker ホスト名ではない） |

`ORIGIN_URL` 例: `https://me-9585b72a360742069939f7e74bb4bb46.ecs.ap-northeast-1.on.aws`

Route `aws-medicine.yutok.dev/*` は `workers/wrangler.toml` で設定。**main push 後に再デプロイ**。

### 方式 B — エディタ直接

1. Workers & Pages → `aws-staging-wake` → コードを `workers/src/index.js` で置換
2. Secrets 3 つ（上記）
3. **Triggers → Routes**: `aws-medicine.yutok.dev/*`（旧 `aws.medicine.yutok.dev/*` は削除）

## 4. 動作確認

```bash
./scripts/stop-aws-staging.sh

# Wake URL（停止中にこちらを開く）
open https://aws-medicine.yutok.dev
# → 「起動中」ページ → 数分後に通常表示

curl -s https://aws-medicine.yutok.dev/health
# {"status":"starting","eta_seconds":180} → ok

# 従来 URL（ECS 稼働中のみ）
curl -s https://aws.medicine.yutok.dev/health
```

手動 wake（Worker なし）:

```bash
# scripts/.aws-wake-staging.json の function_url / wake_token を使用
curl -s -X POST "$WAKE_API_URL" -H "X-Wake-Token: $WAKE_TOKEN"
```

## コスト

| 項目 | 停止中 | アクセス後（タスク稼働中） |
|------|--------|---------------------------|
| **Lambda wake** | $0 | 約 **$0**（月数百回まで無料枠内） |
| **Cloudflare Worker** | $0 | 無料枠 10万 req/日 |
| **Fargate 512/1024 ×1** | $0 | **~$0.03/時** |
| **ALB 固定** | ~$18–28/月 | 同左 |

終了後は `./scripts/stop-aws-staging.sh`。

## 関連

- [AWS_COST_PLAN.md](./AWS_COST_PLAN.md) — 月次試算
- [AWS_ACCOUNT_MIGRATION.md](./AWS_ACCOUNT_MIGRATION.md) — コールドスタート運用
