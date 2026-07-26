# missing104 Retry — Batch 3 Summary

**Run date:** 2026-07-26 (JST)  
**Command:** `.venv/bin/python scripts/sync_otc_images_retry.py --plan log/analysis/otc_image_sync_bulk/missing104_batch_3.json --label missing104_retry_3 --upload --delay 0.8`  
**Batch plan:** `log/analysis/otc_image_sync_bulk/missing104_batch_3.json` (24 items)

## Results

| Metric | Count |
|--------|------:|
| Total | 24 |
| **Newly uploaded to R2** | **24** |
| Skipped (already on R2) | 0 |
| Not found | 0 |
| Review rejected | 0 |
| Download error | 0 |
| Upload error | 0 |
| Errors (total) | 0 |

**Success rate:** 24 / 24 (100%)

## Research approach

All 24 products lacked Matsukiyo matches. Web research via Rakuten/Yahoo EC search identified JAN-verified package images where possible. Each item in the batch plan was updated with:

- `official_url` — primary verified image URL
- `candidate_urls` — 2 fallback URLs
- `research_note` — JAN code or source rationale

All uploads resolved via `official_url` source (score ≥ 55, review approved). No re-run needed.

## OFFICIAL_IMAGE_URLS additions

24 entries added to `scripts/sync_top50_otc_images.py` under `# missing104 batch 3 (2026-07-26)`.

## Product categories

| Category | Count | Examples |
|----------|------:|----------|
| 浣腸 (enema) | 5 | ミカサ浣腸N40, コトブキ浣腸40, コリイス浣腸30 |
| センナ (laxative) | 2 | 東洋漢方のセンナ顆粒S, 本草センナ錠 |
| オウレン (Coptis) | 6 | オウレンいけだや, ナカジマオウレン, オウレンダイコー |
| 胃腸内服液 | 6 | 新バック液, ソルマックEX2, ストーゼ胃腸内服液 |
| その他 | 5 | 大光丸, 救胆, 御百草丸U |

## Newly uploaded (24)

- 東洋漢方のセンナ顆粒Ｓ（分包）
- ミカサ浣腸Ｎ４０
- コトブキ浣腸４０
- コトブキ浣腸４０パステル
- コトブキ浣腸３０パステル
- コリイス浣腸３０
- 本草センナ錠
- 新バック液
- ソルマックＥＸ２
- ストーゼ胃腸内服液
- ガロール健芯液
- ワクナガ生薬胃腸薬
- オウレンいけだや
- オウレン末いけだや
- 新新胃腸薬Ｓ
- イスロ胃腸ドリンクＳ
- 大光丸
- オウレンダイコー
- オウレン末ダイコー
- 大草胃腸薬内服液３０
- 救胆
- ナカジマオウレン
- ナカジマオウレン末
- 御百草丸Ｕ

**Artifacts:** `results_missing104_retry_3.json`, `missing104_batch_3.json` (updated with research fields)
