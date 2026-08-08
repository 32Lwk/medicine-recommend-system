# AWS ステージング — Cloud Run 型運用（Wake + 自動 Stop）

> **入口 URL（これだけブックマーク）**: `https://aws-medicine.yutok.dev`  
> **オリジン（Tunnel）**: `https://origin-aws-medicine.yutok.dev`  
> **方式**: Cloudflare Worker → Lambda wake / touch → ECS Fargate。アイドル 30 分で自動停止。  
> **移行完了**: 2026-08-07（Express + ALB 廃止）

## Cloud Run との対応

| Cloud Run | AWS ステージング（本構成） |
|-----------|---------------------------|
| アクセスで自動起動 | ✅ Worker → wake Lambda |
| 同じ URL で待機→表示 | ✅ `/health` ポーリング後に同一 URL で UI |
| アイドルで自動 0 | ✅ EventBridge + idle-stop Lambda（30 分） |
| 手動 stop / resume 不要 | ✅ 通常不要（手動 stop も可） |
| ALB 等の固定費 | なし | ✅ **$0**（Tunnel 移行後） |
| コールドスタート | 数秒〜1–2 分 | **3〜6 分**（Fargate pull + 起動） |

`aws.medicine.yutok.dev` は **CI/E2E 用レガシー URL**（DNS only）。日常利用は **`aws-medicine.yutok.dev` のみ**。

## 仕組み

```
https://aws-medicine.yutok.dev (Worker, Proxied)
    ↓ ORIGIN_URL → origin-aws-medicine.yutok.dev (Tunnel)
    ↓ origin 503/接続失敗 → wake Lambda（ECS 起動）
    ↓ 「起動中」HTML → /health ポーリング → 同一 URL でアプリ表示
    ↓ 利用中 → touch Lambda（SSM last-activity 更新）
    ↓ 30 分アイドル → idle-stop Lambda（ECS desired=0, min/max=0）
```

| コンポーネント | 役割 |
|----------------|------|
| `workers/src/index.js` | プロキシ・wake・touch・Legacy Host リダイレクト書換 |
| `workers/wrangler.toml` | `ORIGIN_URL=https://origin-aws-medicine.yutok.dev` |
| Lambda `medicine-recommend-wake-staging` | wake / touch / SSM activity |
| Lambda `medicine-recommend-idle-stop-staging` | 10 分毎チェック → 30 分アイドルで stop |
| SSM `/medicine-recommend/staging/last-activity` | 最終アクセス時刻 |
| Fargate `[cloudflared \| app]` | Tunnel サイドカー + 同一 Docker イメージ |

## 精度・RAG・レイテンシ

| 観点 | 影響 |
|------|------|
| 推奨 / スコアリング / Chat Pipeline | **なし**（同一イメージ） |
| RAG（local） | **なし** |
| ウォーム時 API | **ほぼ同等**（Tunnel + 数十 ms） |
| コールドスタート | **+3〜6 分**（Worker 起動待ち UI） |

## セットアップ

### AWS

```bash
AWS_PROFILE=default ./scripts/setup-aws-wake-staging.sh
AWS_PROFILE=default ./scripts/setup-aws-idle-stop-staging.sh
# IDLE_MINUTES=45 ./scripts/setup-aws-idle-stop-staging.sh  # 任意
```

Fargate + Tunnel 本体: [AWS_FARGATE_TUNNEL.md](./AWS_FARGATE_TUNNEL.md)

### Cloudflare

| 項目 | 値 |
|------|-----|
| DNS `origin-aws-medicine` | Tunnel 自動（Proxied） |
| Worker Route | `aws-medicine.yutok.dev/*` |
| Tunnel | `origin-aws-medicine.yutok.dev` → `http://localhost:8080` |
| Runtime Secret | `WAKE_TOKEN`（`ORIGIN_URL` / `WAKE_API_URL` は wrangler.toml） |

Git デploy: Root `workers`, Deploy `npm install && npx wrangler deploy`

## 使い方

1. ブラウザで `https://aws-medicine.yutok.dev` を開く（停止中でも OK）
2. 起動中ページ → **3〜6 分**後 **同じ URL** でアプリが表示される
3. 30 分操作がなければ **自動停止**（次回アクセスで再 wake）

```bash
# 手動 stop（コスト削減・通常は idle-stop で十分）
./scripts/stop-aws-staging.sh

# 手動 resume（Pipeline 有効化 + ECS 起動）
./scripts/resume-aws-staging.sh
```

**注意**: `stop-aws-staging.sh` 後に `aws-medicine.yutok.dev` へアクセスすると Worker が **wake** し ECS が再起動する。

## コスト目安

| 状態 | USD/月 |
|------|--------|
| 停止デフォルト | ~$6–7 |
| 週 5h 利用 | ~$7–9 |
| 起動中 | ~$0.036/h |

詳細: [AWS_COST_PLAN.md](./AWS_COST_PLAN.md)

## 関連

- [AWS_FARGATE_TUNNEL.md](./AWS_FARGATE_TUNNEL.md) — 移行 SSOT
- [AWS_COST_PLAN.md](./AWS_COST_PLAN.md)
- [AWS_ACCOUNT_MIGRATION.md](./AWS_ACCOUNT_MIGRATION.md)
