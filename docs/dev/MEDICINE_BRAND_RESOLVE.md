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

## セッション内ブランドピン（2026-07-26）

**正本**: `src/services/medicine_qa_session_pins.py`

| 項目 | 内容 |
|------|------|
| 保存先 | `session["qa_brand_pins"]` と `user_attributes["qa_brand_pins"]` |
| 優先 | 同一セッションで一度解決した代表製品を再質問でも維持 |
| 上書き | ユーザーが具体製品名（例: バファリンプレミアム）を明示したときのみ |
| API | `resolve_brand_hints_in_query(..., session=)` / `resolve_products_with_session_pins` |

**目的**: 「バファリン」比較で A ↔ プレミアムがターンごとに入れ替わる揺れを防ぐ。フレーズ固定ではなく **文脈スロット** として扱う。

全角／半角英数は `_fold_alnum` で照合（`ロキソニンＳ` ↔ `ロキソニンS`）。

---

## 医薬品 Q&A との連携

| ルート | 条件 | ハンドラ |
|--------|------|----------|
| `medicine_side_effect_qa` | **単独**で副作用・眠気が主題（厳密判定） | `handle_medicine_side_effect_qa` |
| `medicine_qa` | 比較・説明・成分・年齢・写真・複合 intent 等 | `handle_medicine_information_qa` → LLM |

**ハイブリッド arbitration**（`should_use_medicine_qa_unified`）:

- 副作用のみ → `medicine_side_effect_qa`（CSV/PMDA 高速）
- 副作用 + 写真/比較など複合 → `medicine_qa`（multi-focus KB + LLM）

**multi-focus**（`infer_medicine_qa_focuses`）:

| focus | 例 |
|-------|-----|
| `comparison` | ロキソニンとイブの違い |
| `ingredient` | カロナールの成分 |
| `age` | 何歳から飲める？ / 履歴 slot + OTC 平気？ |
| `doping` | マラソン前に使っていい？ / 履歴 slot + それ使っていい？ |
| `interaction` | ワイン飲んでるけど平気？ / 併用 |
| `usage` | 何時間空ける？ / 頻度 follow-up |
| `product_image` | 写真見せて |
| `side_effect` | 副作用（単独→ CSV、効き目+副作用→ unified） |

**文脈 routing**（2026-07-26）: 比較履歴があっても指示語副作用 follow-up は `comparison` にしない。アルコール併用・年齢 slot・ドーピング slot は履歴 + 現発話の suitability で判定。詳細は [`MEDICINE_QA_ROUTING.md`](MEDICINE_QA_ROUTING.md)。

比較 retrieve 時は `route_medicine_docs` が CSV brand 解決で **2 製品分**の product doc URI を返す。

**Clarify**: 「この薬」「さっきの薬」等、指示語のみで推奨履歴なし → `needs_medicine_clarification` → 確認質問（症状推奨に入れない）。

補足セクションは `build_focused_qa_sections` + `prune_qa_response` で **質問に関連する項目のみ**表示（複合 intent は union）。

**製品画像**（2026-07-26）: `medicine_qa_images.build_product_images_html` — 推奨同型 Noimage / CDN hero。回答は `build_product_image_answer_text` でサーバー統一（準備状況 + 成分 1 文）。詳細は [`MEDICINE_QA_ROUTING.md`](MEDICINE_QA_ROUTING.md) の製品画像セクション。

**比較 HTML**（2026-07-26）: `_qa_product_line_html` で製品名と説明を1ブロック化。選び方は成分別（ロキソプロフェン vs イブプロフェン）。

---

## テスト

```bash
.venv/bin/python -m pytest tests/services/test_medicine_brand_resolve.py \
  tests/routing/test_medicine_qa_sections.py \
  tests/routing/test_medicine_qa_routing.py \
  tests/routing/test_medicine_qa_multi_focus.py \
  tests/routing/test_medicine_qa_context_routing.py -q
```

---

## 関連ドキュメント

- [`MEDICINE_QA_ROUTING.md`](MEDICINE_QA_ROUTING.md) — focus 推定・文脈・eval
- [`CHAT_PIPELINE_V2.md`](CHAT_PIPELINE_V2.md) — `medicine_qa` / `medicine_side_effect_qa` sub_route
- [`CHAT_ROUTE_EXPECTATIONS.md`](CHAT_ROUTE_EXPECTATIONS.md)
