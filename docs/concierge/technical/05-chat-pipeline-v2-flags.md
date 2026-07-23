# Chat Pipeline v2 と機能フラグ

## 本番デフォルト ON（2026-07 以降）

| フラグ | 意味 |
|--------|------|
| `CHAT_PIPELINE_V2` | v2 POST パイプライン |
| `INTENT_ROUTER_PRIMARY` | IntentRouter を主経路 |
| `LEGACY_FALLBACK_TRIM` | 二重 triage 抑制 |

env 未設定 = ON（pytest 実行中のみ OFF）。明示 `false` でロールバック。

## 推奨品質フラグ（RECO_*）

| フラグ | 内容 |
|--------|------|
| `RECO_AGE_POLICY_V2` | 年齢未入力時の推奨ポリシー |
| `RECO_COLD_NLU_V2` | 風邪 NLU・症状チップ |
| `RECO_SPORTS_DOPING_FILTER` | 競技・ドーピング配慮 |

本番・dev とも env 未設定 = ON。

## AWS ステージング専用（GCP 本番に注入しない）

`config/aws_features.py` 参照:

- 翻訳: Amazon Translate（AWS）/ DeepL（GCP 本番既定）
- TTS: Amazon Polly（AWS）/ Web Speech（GCP 本番既定）
- Concierge RAG: Bedrock KB（ingestion は Support 待ちの場合あり）
- 画像 CDN: `images.yutok.dev`（GCP も cloudbuild で同 URL 可）

Concierge 技術 FAQ ではフラグ名ではなく「本番では v2 パイプラインが既定で有効」等と述べる。

## 障害 UX

- OPENAI 未設定 → Sage 障害カード（`llm_unavailable`）
- パイプライン無応答 → `system_error` カード（fail loud）
