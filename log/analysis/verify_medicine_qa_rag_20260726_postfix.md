# Medicine QA / Local RAG 検証レポート（改善後）

> 改善実施: 2026-07-26 — LLM stress 分類・会話履歴伝播を修正

## Summary

| 項目 | 値 |
|------|-----|
| **判定** | **GO** |
| 改善前 | GO with warnings（LLM stress 94.1%、4 fail） |
| 改善後 | LLM stress **100%**（68/68）、単体 **44/44** |

## 実施した改善

### 1. カテゴリ推論（`local_rag_query.py` / `local_rag_router.py`）

- **概念展開**: `血液をサラサラ` → ワーファリン（`血を` に加え `血液を` も対応）
- **副作用パターン**: 関西弁 `眠たく/眠なる/眠なり`、ひらがな `きつく/張っ`、敬語「経験をお持ち」系
- **interaction 優先**: `一緒に服用/飲/使` で usage（敬語）より interaction を優先
- **usage パターン狭義化**: 単独 `よろしいでしょう` を削除し、食後/用法文脈付きのみ
- **成分抽出**: `extract_coordination_pairs` で `_is_drug_like_token` 未満の誤分割を除外

### 2. Explanation KB citation（`explanation_generator.py`）

- `user_info.conversation_history` / `messages` を `retrieve_medicine_context` に伝播

### 3. 推奨フロー（`chat_recommendation_flow.py`）

- ExplanationAgent 呼び出し時に session `messages[-10:]` を `user_info.conversation_history` に注入

### 4. LLM stress eval（`eval_local_rag_diverse.py`）

- seed の `recommended_medicines` を stress retrieve に渡すよう修正

## Layer 結果（改善後）

| Layer | 結果 |
|-------|------|
| 1 単体 | **44/44** pass |
| 2a 公式 fixture | **100%**, interaction **5/5** |
| 2c diverse | **100%** (52/52) |
| 2d LLM stress | **100%** (68/68) |
| 3 Medicine QA 配線 | **5/5** + E2E **10/10** |

## 残課題

| 優先度 | 課題 |
|--------|------|
| P2 | Bedrock 回帰比較（AWS credentials 要） |
| P3 | HTTP E2E（app 起動後） |
