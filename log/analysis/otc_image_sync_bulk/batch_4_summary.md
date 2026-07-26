# OTC image bulk sync — batch 4 summary

Generated: 2026-07-26T04:17:22.548959+00:00

## Plan
- Source: `log/analysis/otc_image_sync_bulk/batch_4.json`
- Items: **110** (78 `missing_top200`, 32 pre-existing on CDN from earlier batches)

## Run 1 (Matsukiyo only)
Command: `scripts/sync_otc_images_bulk.py --batch 4 --upload --delay 0.6`

| Metric | Count |
|--------|------:|
| uploaded | 0 |
| skipped_exists | 32 |
| not_found | 78 |
| errors | 0 |

All 78 failures were `matsukiyo search: no match` (obscure kanpō / regional SKUs not listed on Matsukiyo Cocokara Online).

## URL research (Rakuten `shop.r10s.jp` / `tshop.r10s.jp`)
- Automated search + `verify_image_match` for all 78 not_found items
- Output: `batch_4_discovered_urls.json` (**78/78** URLs)
- Added **78** entries to `scripts/sync_top50_otc_images.py` → `OFFICIAL_IMAGE_URLS` (131 total keys)

## Run 2 (retry with official URLs)
- Plan: `batch_4_retry.json` (official_url populated)
- Command: custom retry loop with `--upload`

| Metric | Count |
|--------|------:|
| **uploaded (new this retry)** | **22** |
| skipped_exists (already on CDN) | 56 |
| not_found | 0 |
| review_rejected | 0 |
| errors | 0 |

Note: 56 retry items already returned HTTP 200 on `images.yutok.dev` before processing (likely uploaded concurrently during the URL-discovery window).

## Final batch 4 totals (merged `results_batch_4.json`)

| Status | Count |
|--------|------:|
| uploaded | 22 |
| skipped_exists | 88 |
| not_found | 0 |
| **total** | **110** |

## Newly uploaded slugs (this retry)
- `日野百草丸`
- `増田胃腸薬`
- `ヤマサンオウレン末`
- `ヤマサンオウレン`
- `トチモトのオウレンP`
- `トチモトのオウレン末P`
- `薬草健胃薬F`
- `恵命我神散S細粒`
- `フラーリンJ錠`
- `はらはら薬翁丸`
- `ニチイ胃腸内服液`
- `やまと丸`
- `複方熊胆円`
- `複方熊胆丸`
- `新マルコターンソフト`
- `熊膽圓S`
- `イスロンGII`
- `タブローンMII`
- `パンジアス顆粒`
- `ハイウルソグリーンS`
- `新グリーン胃腸薬DX`
- `胃腸薬エースプラス`
