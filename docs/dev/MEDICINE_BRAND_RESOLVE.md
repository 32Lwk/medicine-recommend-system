# ブランド通称 → 代表製品解決（Medicine Brand Resolve）

**正本**: `src/services/medicine_brand_resolve.py`  
**関連**: `src/services/medicine_qa_routing.py`, `src/core/medicine/medicine_response_builder.py`

---

## 目的

ユーザー発話の **通称**（ロキソニン、イブ、PL 等）を OTC CSV（`data/otc_medicine_data.csv`）上の **代表製品 1 件**に解決し、医薬品 Q&A・比較質問の LLM コンテキストと補足セクションに渡す。

### 解決した問題

| 問題 | 例 |
|------|-----|
| 部分一致の誤検出 | 「イブ」→ ケイ**イブ**ク（顆粒） |
| 日本語の空白なし | `split()` では製品名を検出できない |
| 通称と製品名の不一致 | アドビル → 製品名「イブ」 |
| 短い通称 | PL → パイロンＰＬ錠（`contains` ルール） |

---

## アーキテクチャ

```
ユーザー発話
    ↓ extract_drug_entities()  ← MEDICINE_BRAND_HINTS（レジストリ由来）
    ↓ resolve_brand_hint_product(hint, otc_df)
    ├─ 1. canonical_product（完全一致）
    ├─ 2. preferred_products（フラッグシップ候補、順序付き）
    ├─ 3. product_name_contains（PL → パイロンＰＬ）
    ├─ 4. product_prefix 先頭一致（最短名優先）
    └─ 5. ingredient_aliases（イブ → イブプロフェン）
    ↓
detect_medicine_name_in_query / chat_with_medicine_context
```

`context_signals._MEDICINE_BRAND_HINTS` は **`medicine_brand_resolve.MEDICINE_BRAND_HINTS`** を import（重複定義禁止）。

---

## BrandResolveRule

```python
@dataclass(frozen=True)
class BrandResolveRule:
    hints: tuple[str, ...]              # 表記ゆれ（例: イブ, アドビル）
    ingredient_aliases: tuple[str, ...] # 主成分フォールバック
    canonical_product: str | None       # 最優先製品名
    product_prefix: str | None          # 先頭一致（未指定時 hints 最長）
    product_name_contains: tuple[str, ...]  # 部分一致（PL 等）
    preferred_products: tuple[str, ...]    # CSV に存在する代表候補
```

### 新規通称の追加

`BRAND_RESOLVE_RULES` に 1 行追加するだけで、`MEDICINE_BRAND_HINTS` と `_HINT_TO_RULE` が自動更新される。

```python
_rule(
    "新ブランド",
    ingredients=("主成分名",),
    prefix="新ブランド",
    preferred=("代表製品名Ａ", "代表製品名Ｂ"),
),
```

ルール未登録の通称は **完全一致 → 先頭一致（最短）** のフォールバックのみ。

---

## 先頭一致（`_brand_prefix_match`）

「イブ」が「ケイブク」にマッチしないよう、**製品名の先頭**のみ許可。

| hint | product_name | 結果 |
|------|--------------|------|
| イブ | イブ | ✅ |
| イブ | イブＡ錠 | ✅ |
| イブ | ケイブク（顆粒） | ❌ |
| ロキソニン | ロキソニンＳ | ✅ |

---

## 医薬品 Q&A との連携

| ルート | 条件 | ハンドラ |
|--------|------|----------|
| `medicine_side_effect_qa` | 副作用・眠気が主題（厳密判定） | `handle_medicine_side_effect_qa` |
| `medicine_qa` | 比較・説明・選び方（2 製品以上等） | `handle_medicine_information_qa` → LLM |

補足セクションは `infer_medicine_qa_focus` + `prune_qa_response` で **質問に関連する項目のみ**表示（汎用テンプレ除去）。

---

## テスト

```bash
.venv/bin/python -m pytest tests/services/test_medicine_brand_resolve.py \
  tests/routing/test_medicine_qa_sections.py \
  tests/routing/test_medicine_qa_routing.py -q
```

---

## 関連ドキュメント

- [`CHAT_PIPELINE_V2.md`](CHAT_PIPELINE_V2.md) — `medicine_qa` / `medicine_side_effect_qa` sub_route
- [`CHAT_ROUTE_EXPECTATIONS.md`](CHAT_ROUTE_EXPECTATIONS.md)
