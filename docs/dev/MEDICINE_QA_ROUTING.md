# Medicine QA Routing — 意図推定・ルート切り分け

**正本**: `src/services/medicine_qa_routing.py`  
**LLM 補完**: `src/services/medicine_qa_focus_llm.py`  
**関連**: `src/services/medicine_side_effect_routing.py`, `src/services/local_rag_router.py`, [`MEDICINE_BRAND_RESOLVE.md`](MEDICINE_BRAND_RESOLVE.md)

---

## 目的

ユーザー発話（口語・省略・指示語・複合 intent）から **focus** を推定し、`medicine_side_effect_qa`（CSV 高速）と `medicine_qa`（KB + LLM unified）を切り分ける。テストケース特化ではなく **文脈 slot・因果表現・併用 substance** など一般ルールで判定する。

---

## ルート arbitration

```
ユーザー発話 + session 文脈
    ↓ infer_medicine_qa_focuses()
    ↓ should_use_medicine_qa_unified()
    ├─ 単独 side_effect のみ → medicine_side_effect_qa
    └─ それ以外（比較・写真・複合・効き目+副作用等）→ medicine_qa
```

| 関数 | 用途 |
|------|------|
| `is_medicine_information_question` | 症状推奨をスキップする gate |
| `is_strict_medicine_side_effect_question` | 副作用 CSV ルート専用 gate |
| `needs_medicine_clarification` | 指示語のみ・履歴なし → 確認質問 |

---

## Focus 一覧

| focus | 検出の要点 | 例 |
|-------|-----------|-----|
| `comparison` | 現発話 2 剤、または比較語 + 履歴 2 剤 | ロキソとイブ何が違う？ / 結局どっち？ |
| `side_effect` | 副作用語・眠気・因果（飲むとだるい） | ロキソ飲んだらガチ眠い？ |
| `interaction` | 併用語・**アルコール** | ワイン飲んでるけど平気？ |
| `usage` | 用法・頻度・食前食後（副作用因果と分離） | それ、どのくらいの頻度で？ |
| `ingredient` | 成分・中身 | 何入ってる？ |
| `age` | 年齢語 + 履歴 slot | 風邪薬 OTC で平気？（履歴: 小学2年） |
| `doping` | 競技語 + 履歴 slot | それ使っていい？（履歴: マラソン） |
| `product_image` | 写真・箱・パッケージ | パッケージ見たい |
| `general` | 上記いずれも未命中 | LLM 補完候補 |

---

## 文脈解決

### エンティティ（`_resolve_medicine_entities`）

1. ブランド通称・略称（`_extract_brand_mentions` + dedupe）
2. `extract_drug_entities`（plausible のみ）
3. 成分名
4. `recommended_medicines`（session 推奨）
5. `extract_context_substances`（履歴）

### 指示語（anaphora）

`それ` / `これ` / `この薬` 等 + **推奨履歴 or 会話履歴** があれば entity 相当として focus / retrieve に利用。履歴なしは `needs_medicine_clarification`。

### 比較の誤検出防止

- `_distinct_brand_count` の **第一判定は現発話のみ**
- 履歴 2 剤は `どっち` / `違い` 等の比較語がある場合のみ使用
- 通称重複（ロキソニン + ロキソ）は `_dedupe_brand_mentions` で 1 剤に統合

### 副作用 vs 用法

`_SIDE_EFFECT_CAUSAL_DRINK_RE`（飲むと / 飲んだら / 飲めば）+ 副作用 topic → **usage にしない**。

### 効き目 + 副作用

`_has_efficacy_concern_intent` + `side_effect` → `should_use_medicine_qa_unified` True。推奨文脈では `is_medicine_information_question` も True。

---

## LLM 補完（任意）

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `MEDICINE_QA_FOCUS_LLM` | `false` | rule が `general` のみ + 文脈あり → LLM で focus 推定 |
| `MEDICINE_QA_FOCUS_LLM_MODEL` | `gpt-4o-mini` | 補完モデル |

オフライン eval では `--with-llm-stress` 時に自動 ON。本番は latency / コストに応じて明示設定。

---

## Local RAG 連携

`infer_medicine_qa_focuses` の結果は `local_rag_router.infer_medicine_category_from_qa_focuses` 経由で retrieve category に写像（LLM 追加コストなし）。`bedrock_kb_retrieve.augment_medicine_prompt_with_kb` が `conversation_history` / `qa_focuses` を retrieve に渡す。

---

## 評価

```bash
# 固定 43 問（日常 + 文脈）
MEDICINE_RAG_PROVIDER=local .venv/bin/python scripts/eval_medicine_qa_robustness.py

# GPT 会話 + LLM 言い換え stress
MEDICINE_RAG_PROVIDER=local .venv/bin/python scripts/eval_medicine_qa_robustness.py \
  --with-gpt-conversation --with-llm-stress

# E2E 配線 19 問
MEDICINE_RAG_PROVIDER=local .venv/bin/python scripts/eval_medicine_qa_e2e.py
```

Fixtures: `tests/fixtures/medicine_qa_everyday_eval.yaml`, `medicine_qa_gpt_conversation.yaml`

### pytest

```bash
.venv/bin/pytest tests/routing/test_medicine_qa_routing.py \
  tests/routing/test_medicine_qa_multi_focus.py \
  tests/routing/test_medicine_qa_context_routing.py -q
```

---

## 関連ドキュメント

- [`LOCAL_RAG.md`](../ops/LOCAL_RAG.md) — retrieve eval・環境変数
- [`CHAT_PIPELINE_V2.md`](CHAT_PIPELINE_V2.md) — sub_route 一覧
- [`MEDICINE_BRAND_RESOLVE.md`](MEDICINE_BRAND_RESOLVE.md) — 通称解決
