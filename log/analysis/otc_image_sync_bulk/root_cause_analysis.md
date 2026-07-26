# OTC 画像取得 — 低成功率の原因分析（2026-07-26）

## サマリー

一括同期 443 件の結果: **uploaded 129 (29%)** / skipped_exists 68 / **not_found 246 (56%)**

## 根本原因

### 1. 取得ソースがマツキヨ単一（最大要因）

`sync_otc_images_bulk.py` → `process_item()` のフロー:

1. `OFFICIAL_IMAGE_URLS`（約40件登録）
2. **マツキヨココカラ online 検索のみ**
3. 失敗 → `not_found`

**246 件すべて** の note が `matsukiyo search: no match`。

楽天 EC・Yahoo ショッピング・メーカー公式・ツルハ等は **一括同期では未使用**（top50 同期時のみ手動登録）。

### 2. マツキヨ検索の厳格マッチング

`pick_search_match()` は token overlap **0.45 未満を除外**、best_score **55 未満は no match**。

| 失敗しやすい品目 | 理由 |
|------------------|------|
| 漢方・生薬系（ウチダ、東洋漢方等） | EC 未掲載 or 名称不一致 |
| ジェネリック（イブプロフェン錠200S 等） | 商品名のみ・画像なし |
| 旧品名・地域品（セイヨン、カゼンエース等） | マツキヨに未掲載 |
| スカイブブロン系派生 SKU | 検索ヒットするが名称スコア不足 |

### 3. プランの品目構成

| source | not_found |
|--------|-----------|
| missing_top200 | 95 |
| famous_csv_fill | 91 |
| famous_brand | 60 |

`famous_csv_fill` は CSV からメーカー大手優先で選定したが、**実際には EC 未掲載のロングテール**が多く含まれた。

### 4. 審査（review_rejected）は今回 0 件

画像が取得できていない段階で止まっており、審査で落ちているわけではない。

## 対策（実施）

1. **`scripts/otc_image_multi_source.py`** — マツキヨ + 楽天 + Yahoo + 公式 URL を横断し `verify_image_match` で最良候補を選択
2. **`scripts/sync_otc_images_retry.py`** — missing104 再試行専用
3. **Multitask 4 分割** — Web 調査で `candidate_urls` / `official_url` を補完 → 再アップロード

## missing104 再試行バッチ

| ファイル | 件数 |
|----------|------|
| `missing104_batch_1.json` | 24 |
| `missing104_batch_2.json` | 24 |
| `missing104_batch_3.json` | 24 |
| `missing104_batch_4.json` | 23 |
