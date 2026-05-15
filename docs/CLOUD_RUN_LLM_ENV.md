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

LLM_MODEL_PROFILE=legacy         # 段階的に gpt5
LLM_CANARY_PERCENT=0             # 新規 sid のみ gpt5
OPENAI_USE_RESPONSES_API=false

LLM_AGENT_ENABLED=false
LLM_AGENT_CANARY_PERCENT=0
LLM_GPT_RECOMMEND_FALLBACK=false

OPENAI_MONTHLY_BUDGET_JPY=50000
OPENAI_SESSION_COST_ALERT_JPY=15
```

## timeout

Cloud Run リクエスト timeout: **120s**（長い推奨フロー向け）
