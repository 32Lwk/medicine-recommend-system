# AWS ステージング — Cloud Run 型運用（Wake + 自動 Stop）

> **入口 URL（これだけブックマーク）**: `https://aws-medicine.yutok.dev`  
> **方式**: Cloudflare Worker → Lambda wake / touch → ECS。アイドル 30 分で自動停止。

## Cloud Run との対応

| Cloud Run | AWS ステージング（本構成） |
|-----------|---------------------------|
| アクセスで自動起動 | ✅ Worker → wake Lambda |
| 同じ URL で待機→表示 | ✅ `/health` ポーリング後に同一 URL で UI |
| アイドルで自動 0 | ✅ EventBridge + idle-stop Lambda（30 分） |
| 手動 stop / resume 不要 | ✅ 不要 |
| 固定費ゼロ | ❌ ALB ~$18–28/月 は残る |

`aws.medicine.yutok.dev` は **CI/E2E 用レガシー URL**（DNS only）。日常利用は **`aws-medicine.yutok.dev` のみ**。

## 仕組み

```
https://aws-medicine.yutok.dev (Worker, Proxied)
    ↓ origin 503 → wake Lambda（ECS 起動）
    ↓ 「起動中」→ /health ポーリング → 同一 URL でアプリ表示
    ↓ 利用中 → touch Lambda（SSM last-activity 更新）
    ↓ 30 分アイドル → idle-stop Lambda（ECS desired=0）
```

| コンポーネント | 役割 |
|----------------|------|
| `workers/src/index.js` | プロキシ・wake・touch・Legacy Host リダイレクト書換 |
| Lambda `medicine-recommend-wake-staging` | wake / touch / SSM activity |
| Lambda `medicine-recommend-idle-stop-staging` | 10 分毎チェック → 30 分アイドルで stop |
| SSM `/medicine-recommend/staging/last-activity` | 最終アクセス時刻 |

## セットアップ

### AWS

```bash
AWS_PROFILE=default ./scripts/setup-aws-wake-staging.sh
AWS_PROFILE=default ./scripts/setup-aws-idle-stop-staging.sh
# IDLE_MINUTES=45 ./scripts/setup-aws-idle-stop-staging.sh  # 任意
```

### Cloudflare

| 項目 | 値 |
|------|-----|
| DNS `aws-medicine` | CNAME → ALB、**Proxied** |
| Worker Route | `aws-medicine.yutok.dev/*` |
| Runtime Secret | `WAKE_TOKEN` のみ（`ORIGIN_URL`/`WAKE_API_URL` は wrangler.toml） |

Git デプロイ: Root `workers`, Deploy `npm install && npx wrangler deploy`

## 使い方

1. ブラウザで `https://aws-medicine.yutok.dev` を開く（停止中でも OK）
2. 起動中ページ → 数分後 **同じ URL** でアプリが表示される
3. 30 分操作がなければ **自動停止**（次回アクセスで再 wake）

```bash
# 手動 stop（通常不要）
./scripts/stop-aws-staging.sh
```

## 関連

- [AWS_COST_PLAN.md](./AWS_COST_PLAN.md)
- [AWS_ACCOUNT_MIGRATION.md](./AWS_ACCOUNT_MIGRATION.md)
