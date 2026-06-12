# Cloud Run LLM 環境変数（P0-05b）

## サービス

| 環境 | サービス名 | リージョン |
|------|-----------|-----------|
| 本番 | `medicine-recommend` | `asia-northeast1` |
| ステージング | `medicine-recommend-dev` | `asia-northeast1` |

## 必須・推奨変数

```bash
OPENAI_API_KEY_PRODUCTION=sk-...   # 本番
OPENAI_API_KEY_STAGING=sk-...      # dev
APP_ENV=production                 # または development

# コード既定は gpt5。明示する場合のみ:
# LLM_MODEL_PROFILE=gpt5
# LLM_CANARY_PERCENT=0   # gpt5 時は 0/100 とも全セッション gpt5
OPENAI_USE_RESPONSES_API=false   # triage/explain はロール別 Responses

LLM_AGENT_ENABLED=true
# エージェントカナリア（LLM_AGENT_CANARY_PERCENT）は廃止。ON で全セッションがオーケストレータ経路。
LLM_GPT_RECOMMEND_FALLBACK=false

OPENAI_MONTHLY_BUDGET_JPY=50000
OPENAI_SESSION_COST_ALERT_JPY=15
```

## timeout

Cloud Run リクエスト timeout: **300s** 推奨（LINE Webhook バックグラウンドの推奨フロー向け）

Gunicorn（`start.sh` 既定）: `GUNICORN_TIMEOUT=300`, `GUNICORN_GRACEFUL_TIMEOUT=60`

## コールドスタート対策（LINE 応答速度）

LINE Webhook は単独リクエストでインスタンスがスケールゼロから起動すると、初回応答が数十秒遅くなることがあります。**ウォーム時 SLA**（挨拶 <1秒、症状相談 4〜6秒）を満たすには、検証・本番いずれも次を推奨します。

```bash
# dev（手動ベンチ対象）
gcloud run services update medicine-recommend-dev \
  --region=asia-northeast1 \
  --min-instances=1

# 本番（コストと相談）
gcloud run services update medicine-recommend \
  --region=asia-northeast1 \
  --min-instances=1
```

- CPU 常時割り当て: Cloud Run コンソール「CPU は常に割り当てる」を有効化（詳細は [CAPACITY_PLANNING.md](CAPACITY_PLANNING.md)）
- `DATABASE_URL` は Neon **pooler** ホスト（`-pooler`）を使用
- デプロイ後 `/admin/system_status` で `database.available=true` を確認

手動ベンチ手順: [LINE_SPEED_BENCH.md](LINE_SPEED_BENCH.md)

## LINE Webhook（環境構築）

手順の正本: [LINE_WEBHOOK_SETUP.md](LINE_WEBHOOK_SETUP.md)

| 変数 | 必須 | 既定 | 備考 |
|------|------|------|------|
| `LINE_CHANNEL_SECRET` | Webhook 有効時 | — | 署名検証用。ログに出さない |
| `LINE_CHANNEL_ACCESS_TOKEN` | Reply/Push 時 | — | 返信・Flex Push に必須 |
| `LINE_WEBHOOK_ENABLED` | — | `false` | dev のみ `true` 推奨。本番は慎重に |
| `GUNICORN_TIMEOUT` | — | `300`（start.sh） | WORKER TIMEOUT 回避 |

**dev 例**（`medicine-recommend-dev`）:

```bash
gcloud run services update medicine-recommend-dev \
  --region=asia-northeast1 \
  --update-env-vars="LINE_WEBHOOK_ENABLED=true,LINE_CHANNEL_SECRET=YOUR_SECRET"
```

Webhook URL: `https://<dev-service-url>/line/webhook`
