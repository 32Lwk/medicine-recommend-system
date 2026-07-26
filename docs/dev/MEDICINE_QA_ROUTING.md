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
| `age` | 年齢語、または **履歴のライフステージ文脈 + 市販薬可否の型** | 熱に市販薬でいい？（履歴: 幼稚園の子ども） |
| `doping` | 競技語 + 履歴 slot | それ使っていい？（履歴: マラソン） |
| `product_image` | 写真・箱・パッケージ | パッケージ見たい |
| `general` | 上記いずれも未命中 | LLM 補完候補 |

**`product_image` と `comparison` の排他**: 写真 intent が付く発話では比較 focus を付けない（「ロキソニンとイブの画像見せて」で比較セクションが出ない）。

### 年齢・ライフステージ（一般化）

学校種ごとのキーワード追加ではなく、次の **型** で判定する（正本: `_has_age_intent`）。

1. `_history_has_life_stage_context` — 履歴に小児〜高齢・妊娠等のライフステージ語彙／数値年齢がある
2. `_looks_medicine_suitability_ask` — 現発話が市販薬・服用の可否を問う型（症状の追加報告だけは除外）

例: 履歴「幼稚園の子どもが熱っぽい」+「市販薬使っても大丈夫？」→ `age`。  
「咳も出ているし元気がない」だけの追記 → `age` にしない。

---

## 製品画像 Q&A（2026-07-26）

**正本**: `src/services/medicine_qa_images.py`  
**配線**: `medicine_response_builder._finalize_structured_qa_response`  
**準備判定**: `medicine_image_urls.medicine_has_ready_image`

### 回答文案（サーバー生成）

LLM のストリーム回答は `product_image` focus 時 **上書き** され、以下の形式に統一される。

| 状態 | 冒頭例 |
|------|--------|
| 全製品準備済 | 「A、Bのパッケージ画像です。」 |
| 全製品未準備 | 「A、Bのパッケージ画像はまだ準備できていません。」 |
| 2 製品・片方のみ | 「Aのパッケージ画像を表示しました。Bのパッケージ画像はまだ準備できていません。」 |
| 3 製品以上・混在 | 「A、B、Cのうち、A、Bのパッケージ画像を表示しました。Cの…」 |

末尾に **成分・用途 1 文**（`build_product_image_answer_text` → `_product_image_summary_sentence`）を常に付与。

### UI

- HTML: `build_product_images_html` — 推奨と同型 `ui-med-image--card`
- 未配置 / CDN 404: Noimage ラベルまたは `static/line/medicine-noimage-hero.png`（`onerror`）
- CSS: `.ui-qa-product-images` グリッド（`sage_terrace.css`）

### 比較・選び方案内 HTML

- `_comparison_lines` / `_pick_advice_lines` → `_qa_product_line_html`（Markdown 改行崩れ防止）
- セクションタイトル: 比較=`製品比較`、選び方=`選び方のポイント`（`section_title_for_focuses`）

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

`_SIDE_EFFECT_CAUSAL_DRINK_RE`（飲むと / 飲んだら / 飲めば / 飲んだあと）+ 副作用 topic → **usage にしない**。  
会話フィラーを薬剤エンティティと誤認すると ambiguity LLM がスキップされるため、`local_rag_query._is_drug_like_token` はひらがな優勢の句を拒否寄りにする。

### 効き目 + 副作用

`_has_efficacy_concern_intent` + `side_effect` → `should_use_medicine_qa_unified` True。推奨文脈では `is_medicine_information_question` も True。

---

## LLM 補完（構造的曖昧さ時のみ）

**正本**: `src/services/medicine_qa_focus_llm.py`

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `MEDICINE_QA_FOCUS_LLM` | `auto`（未設定時） | `auto`/未設定: OpenAI client があれば ON。`0/false/off` で強制 OFF、`1/true/on` で強制 ON |
| `MEDICINE_QA_FOCUS_LLM_MODEL` | `gpt-4o-mini` | 補完モデル |

**呼ばれる条件**（コスト抑制）:

- rule focus が `general` のみ
- focus 衝突（例: `side_effect`∩`usage`, `interaction`∩`comparison`, `age`∩`usage`）
- 文脈あり + 固有ブランドが薄い +（指示語 or 短い疑問・心配）

失敗時は rule focuses をそのまま返す。フレーズ一致ではなく **ユーザーが知りたいこと** を優先するプロンプト。

---

## Local RAG 連携

`infer_medicine_qa_focuses` の結果は `local_rag_router.infer_medicine_category_from_qa_focuses` 経由で retrieve category に写像（LLM 追加コストなし）。`bedrock_kb_retrieve.augment_medicine_prompt_with_kb` が `conversation_history` / `qa_focuses` を retrieve に渡す。

---

## 評価

```bash
# 固定 everyday + context（+ meta / conversation_sim）
MEDICINE_RAG_PROVIDER=local MEDICINE_QA_FOCUS_LLM=auto \
  .venv/bin/python scripts/eval_medicine_qa_robustness.py

# GPT 単発会話 + 多ターン文脈 + LLM 言い換え stress
MEDICINE_RAG_PROVIDER=local MEDICINE_QA_FOCUS_LLM=auto \
  .venv/bin/python scripts/eval_medicine_qa_robustness.py \
  --with-gpt-conversation --with-gpt-multiturn \
  --with-llm-stress --llm-stress-variants 3

# E2E 配線 19 問
MEDICINE_RAG_PROVIDER=local .venv/bin/python scripts/eval_medicine_qa_e2e.py
```

| スイート | 内容 |
|---------|------|
| everyday / soft | 日常・方言・ソフト言い回し |
| context | 履歴付き follow-up |
| llm_stress | 固定シードの言い換え生成 → routing |
| conversation_sim | テンプレ follow-up |
| meta_everyday | Concierge 話題 sticky / topic break |
| gpt | ライブ GPT 患者発話 + 意図 fidelity |
| gpt_multiturn | 多ターン文脈保持 |

**2026-07-26 結果（ライブ GPT 含む）**: **253/253 (100%)** — 成果物 `log/analysis/medicine_qa_robustness_eval.json`

Fixtures: `medicine_qa_everyday_eval.yaml`, `medicine_qa_gpt_conversation.yaml`, `medicine_qa_gpt_multiturn.yaml`, `medicine_qa_conversation_sim.yaml`, `meta_topic_everyday_eval.yaml`

### pytest

```bash
.venv/bin/pytest tests/routing/test_medicine_qa_routing.py \
  tests/routing/test_medicine_qa_multi_focus.py \
  tests/routing/test_medicine_qa_context_routing.py \
  tests/routing/test_medicine_qa_sections.py \
  tests/services/test_medicine_qa_images.py \
  tests/services/test_medicine_qa_focus_llm.py -q
```

---

## 関連ドキュメント

- [`LOCAL_RAG.md`](../ops/LOCAL_RAG.md) — retrieve eval・環境変数
- [`CHAT_PIPELINE_V2.md`](CHAT_PIPELINE_V2.md) — sub_route 一覧
- [`MEDICINE_BRAND_RESOLVE.md`](MEDICINE_BRAND_RESOLVE.md) — 通称解決・セッションピン
- Concierge meta: `src/dialogue/routing/context_signals.py`（`suggest_meta_intent_family`）
