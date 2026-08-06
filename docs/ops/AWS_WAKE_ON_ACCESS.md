# AWS ステージング — アクセス時自動起動（Wake on Access）

> **前提**: ECS コールド停止中（`stop-aws-staging.sh`）  
> **方式**: Cloudflare Worker → Lambda Function URL → ECS 起動

## 仕組み

```
ユーザー → aws.medicine.yutok.dev (Cloudflare Worker)
              ↓ origin 503 / 接続失敗
              ↓ Lambda wake（非同期）
              ↓ 「起動中」HTML（15秒ごと自動更新）
         3〜6 分後 → 通常のステージング UI
```

| コンポーネント | 役割 |
|----------------|------|
| `workers/cloudflare-aws-staging-wake.js` | 503 検知 → wake API 呼び出し → 待機ページ |
| Lambda `medicine-recommend-wake-staging` | ECS min/max/desired 復元 + タスク起動 |
| `scripts/setup-aws-wake-staging.sh` | Lambda / IAM / Function URL 作成 |

**注意**: DNS が **Cloudflare プロキシ（オレンジ雲）** である必要があります。DNS only のままでは Worker が動きません。

## 1. AWS 側セットアップ

```bash
AWS_PROFILE=default ./scripts/setup-aws-wake-staging.sh
```

生成物:

- Lambda + Function URL
- `scripts/.aws-wake-staging.json`（**WAKE_TOKEN 含む — Git にコミットしない**）

## 2. Cloudflare Worker デプロイ

### 方式 A — Dashboard（Git 連携・推奨）

リポジトリに `workers/wrangler.toml` あり。**main に push 後**、Dashboard で以下を入力:

| 項目 | 値 |
|------|-----|
| Project name | `aws-staging-wake` |
| Root directory | `workers` |
| Production branch | `main` |
| Build command | `npm install && npx wrangler deploy` |
| API token | **Create new token**（自動作成で OK） |

**Environment variables**（すべて **Secret**）:

| Variable name | Value |
|---------------|-------|
| `WAKE_API_URL` | Lambda Function URL |
| `WAKE_TOKEN` | Lambda の WAKE_TOKEN |
| `ORIGIN_URL` | Express 直 URL |

値はローカルで:

```bash
AWS_PROFILE=default ./scripts/print-aws-wake-staging-config.sh
# → scripts/.aws-wake-staging.json
```

`ORIGIN_URL` 例: `https://me-9585b72a360742069939f7e74bb4bb46.ecs.ap-northeast-1.on.aws`

デプロイ後:

1. **DNS**: `aws.medicine.yutok.dev` を **Proxied（オレンジ雲）**
2. Route `aws.medicine.yutok.dev/*` は `wrangler.toml` で設定済み（初回 deploy で付与）

### 方式 B — エディタに直接貼り付け

1. [Cloudflare Dashboard](https://dash.cloudflare.com/) → **Workers & Pages** → Create Worker
2. コードを `workers/src/index.js` の内容で置き換え
3. **Settings → Variables**（Secrets）:

| 名前 | 値 |
|------|-----|
| `WAKE_API_URL` | Lambda Function URL（末尾スラッシュなし） |
| `WAKE_TOKEN` | Lambda の `WAKE_TOKEN` |
| `ORIGIN_URL` | **Express 直 URL**（Worker 自身のホスト名ではない） |

4. **Triggers → Routes**: `aws.medicine.yutok.dev/*`
5. **DNS**: Proxied（オレンジ雲）

## 3. 動作確認

```bash
# 停止状態から
./scripts/stop-aws-staging.sh

# ブラウザで https://aws.medicine.yutok.dev を開く
# → 「起動中」ページ → 数分後に通常表示

curl -s https://aws.medicine.yutok.dev/health
# starting → ok
```

手動 wake（Worker なしでテスト）:

```bash
source scripts/.aws-wake-staging.json  # または jq
curl -s -X POST "$function_url" -H "X-Wake-Token: $wake_token"
```

## コスト

| 項目 | 停止中 | アクセス後（タスク稼働中） |
|------|--------|---------------------------|
| **Lambda wake** | $0 | 約 **$0**（月数百回まで無料枠内） |
| **Cloudflare Worker** | $0 | 無料枠 10万 req/日 |
| **Fargate 512/1024 ×1** | $0 | **~$0.03/時**（~$23/月 if 24h 稼働） |
| **ALB 固定** | ~$18–28/月 | 同左（変わらず） |

### 要点

- **Wake 自体はほぼ無料**（Lambda + Worker の従量は微々たるもの）
- **コストが増えるのはタスクが起動して動いている時間** — 手動 `resume` と同じ
- ボット等で連続アクセスされると **起動しっぱなし** になる → 終わったら `./scripts/stop-aws-staging.sh`
- 将来: アイドル 30 分で自動 stop（EventBridge）を追加可能

### 手動 resume との違い

| | `resume-aws-staging.sh` | Wake on Access |
|--|-------------------------|----------------|
| トリガー | CLI | ブラウザアクセス |
| CodePipeline 再有効化 | ✅ | ❌（既定。`ENABLE_PIPELINE_ON_WAKE=true` で変更可） |
| 起動時間 | 3–6 分 | 同左 |

## 関連

- [AWS_COST_PLAN.md](./AWS_COST_PLAN.md) — 月次試算
- [AWS_ACCOUNT_MIGRATION.md](./AWS_ACCOUNT_MIGRATION.md) — コールドスタート運用
