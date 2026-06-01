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

Cloud Run リクエスト timeout: **120s**（長い推奨フロー向け）
