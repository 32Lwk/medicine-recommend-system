# Diagnosis v1 — Sage UI 構造化ペイロード

正本スキーマ: [`src/schemas/recommendation_diagnosis_v1.py`](../src/schemas/recommendation_diagnosis_v1.py)

## render 種別

| 値 | 用途 |
|----|------|
| `sage_reco` | 医薬品推奨（0件・エラー含む） |
| `sage_status` | カウンセリング・診断名・店舗・緊急 |
| `sage_qa` | 医薬品 Q&A |

## メッセージ契約

```json
{
  "type": "bot",
  "content": "sage_reco",
  "diagnosis": { "schema_version": 1, "render": "sage_reco", ... }
}
```

## 主要フィールド

- `recommended_medicines[]` — クライアントカルーセル用
- `usage_sections[]` — 使用上の注意（structured JSON）
- `ingredient_overlap` — `{ summaries, severity, title }`
- `error` — `{ type, severity, title, message, recommendations[] }`
- `admin` — 管理専用（ユーザー API から strip）

## SSE

1. `cards` → 2. `advice_delta` → 3. `done`（core diagnosis）→ 4. `reco_detail`（usage_sections）

## 過去メッセージ

`content` に `recommendation-result` / `chat-status-card` を含む既存メッセージは **読取専用 legacy 描画**（new_only）。
