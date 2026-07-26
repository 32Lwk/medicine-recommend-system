# missing104 batch 1 retry summary

**Date:** 2026-07-26  
**Plan:** `missing104_batch_1.json` (24 items, highest recommendation_count)  
**Results:** `results_missing104_retry_1.json`

## Outcome

| Status | Count |
|--------|------:|
| **uploaded** (new R2) | **7** |
| skipped_exists (R2 already had image) | 17 |
| not_found | 0 |
| review_rejected | 0 |
| errors | 0 |

**Effective R2 coverage:** 24/24 (100%) — 17 were already present from an earlier multi-source probe; 7 newly uploaded in this run.

## Sources used

| Source | Items |
|--------|------:|
| Rakuten EC (`shop.r10s.jp`) | 23 |
| Manufacturer official (`tokiwayakuhin.co.jp`) | 1 (救風) |
| Matsukiyo | 0 (all had failed in bulk sync) |
| Yahoo EC | 0 (Rakuten candidates scored higher) |

All resolved images came via `official_url` / `candidate_urls` research → `resolve_multi_source()` with `verify_image_match` (review_score 90, match_score 105).

## Newly uploaded (7)

| Product | R2 URL |
|---------|--------|
| エスタックイブファインＥＸ | https://images.yutok.dev/otc/エスタックイブファインEX.webp |
| バファリンかぜＥＸ錠《瓶》 | https://images.yutok.dev/otc/バファリンかぜEX錠瓶.webp |
| 仁壽 | https://images.yutok.dev/otc/仁壽.webp |
| 暖中錠 | https://images.yutok.dev/otc/暖中錠.webp |
| 新スキントールＳ | https://images.yutok.dev/otc/新スキントールS.webp |
| フジコールＩＰ錠 | https://images.yutok.dev/otc/フジコールIP錠.webp |
| サンワ白虎加人参湯エキス細粒 | https://images.yutok.dev/otc/サンワ白虎加人参湯エキス細粒.webp |

## Already in R2 (skipped_exists, 17)

イブプロフェン錠２００Ｓ, セイヨン総合かぜ薬, 新スカイブブロンゴールド錠, カイゲンＡＺのどスプレー, スカイブブロンストレート, 新ストナエースＧ, 救風, カゼンエース, 新スカイブブロンゴールド微粒, 健栄のどフレッシュ, コーフパウダー, 第一三共胃腸薬コアブロック散剤, 新エスタックイブエースカプセル, スカイブブロンＮＡスプレー, グットエイドＥＸ, ジキニン鼻炎ＡＧ顆粒, クミアイ新頭痛錠

## Research notes (manual verification highlights)

- **救風:** 常盤薬品公式 `H079454.jpg` + JAN4987438076035。誤候補 `kyuka.jpg` を除外
- **新スカイブブロンゴールド微粒:** JAN4954391105270（錠4954391105720と区別）
- **第一三共胃腸薬コアブロック散剤:** 東亜薬品製造 JAN4987107676849
- **バファリンかぜＥＸ錠《瓶》:** ライオン製造終了品、楽天EC瓶包装画像

## Remaining failures

**None.** No `OFFICIAL_IMAGE_URLS` manual additions required for this batch.

## Top failures list

N/A — 0 not_found, 0 review_rejected.
