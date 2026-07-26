# OTC Image Bulk Sync — Batch 1 Summary

**Run date:** 2026-07-26 (JST)  
**Command:** `.venv/bin/python scripts/sync_otc_images_bulk.py --batch 1 --upload --delay 0.6`  
**Batch plan:** `log/analysis/otc_image_sync_bulk/batch_1.json` (111 items)

## Results

| Metric | Count |
|--------|------:|
| Total | 111 |
| **Newly uploaded to R2** | **59** |
| Skipped (already on R2) | 2 |
| Not found (no image source) | 50 |
| Review rejected | 0 |
| Download error | 0 |
| Upload error | 0 |
| Errors (total) | 0 |

**Success rate (upload + skip):** 61 / 111 (55.0%)

## High-priority URL research

No items qualified for mandatory retry (source=`missing_top200` or `recommendation_count>=10`): **0** not_found in that tier. Skipped web search / `OFFICIAL_IMAGE_URLS` updates for this batch.

## Not found breakdown

- **famous_csv_fill:** 39
- **famous_brand:** 11

## Top 10 failures (by priority)

1. **JPS桂枝加朮附湯エキス錠N** — `not_found` (source=famous_csv_fill, rec=0)
2. **JPS桂枝加竜骨牡蛎湯エキス錠N** — `not_found` (source=famous_csv_fill, rec=0)
3. **お熱散** — `not_found` (source=famous_csv_fill, rec=0)
4. **アルピタンγ(五苓散)** — `not_found` (source=famous_csv_fill, rec=0)
5. **アンベリーホワイトCプラス** — `not_found` (source=famous_csv_fill, rec=0)
6. **ウチダの十味敗毒散** — `not_found` (source=famous_csv_fill, rec=0)
7. **ウチダの十味敗毒湯** — `not_found` (source=famous_csv_fill, rec=0)
8. **ウチダの茵ちん五苓湯** — `not_found` (source=famous_csv_fill, rec=0)
9. **ウレッシュCプラスホワイト** — `not_found` (source=famous_csv_fill, rec=0)
10. **キミエホワイトプラス** — `not_found` (source=famous_csv_fill, rec=0)

## Newly uploaded (59)

- ハイシー1000, チョコラBBルーセントC, メンソレータムエクシブWクリーム
- メンソレータムヒビプロKTα, ムヒアルファEX, メンソレータムリシーナ注入軟膏A
- メンソレータムリシーナ軟膏A, チョコラBB口内炎リペアショット, メンソレータムヒビプロLP
- メンソレータムエクシブWきわケアジェル, サロンパスAe, 穴あきサロンパスAe
- フェイタスZαジクサス, ロキソニンSハードゲル, ロキソニンEXローション
- ロキソニンEXゲル, ロキソニンSローションa, ロキソニンSゲル
- フェイタスZジクサスシップF, エアーサロンパスZ, フェイタスZαジクサスゲル
- フェイタスZαジクサス温感大判, フェイタスZαジクサス温感, フェイタスZジクサスシップ
- 液体ムヒアルファEX, 液体ムヒS2a, ハイチオールCプラス2
- ハイチオールCプラス, ハイチオールCホワイティア, ハイチオールCプラスEX
- ハイチオールCプルミエール, DHCエルシスホワイト240EX, 茵ちん五苓散エキス細粒G「コタロー」
- 陰陽調和エキス顆粒A, レディガードコーワ, ユンケル心臓薬
- エミネトン, 桂枝加苓朮附湯エキス錠クラシエ, ボーコレン
- 柴胡加竜骨牡蛎湯エキス錠クラシエ, 「クラシエ」漢方猪苓湯エキス錠, 「クラシエ」漢方桂枝加苓朮附湯エキス顆粒
- 「クラシエ」漢方猪苓湯エキス顆粒, 「クラシエ」漢方柴胡加竜骨牡蛎湯エキス顆粒, 「クラシエ」漢方桂枝加竜骨牡蛎湯エキス顆粒
- JPS漢方顆粒-10号, Vロートナイトプレミアムアイ内服薬, サンテドウプラスEアルファ
- ロートアルガードクリアマイルドZ, ロートアルガードクリアマイルドEXa, ロートアルガードクリアブロックEXa
- サンテメディカルガードEX, ロートアルガードクリアブロックZII, ロートアルガードクリアマイルドZII
- サンテALn, サンテPC, サンテFXVプラス
- サンテALクールII, ロートアルガードクリアブロックZ

## Skipped — already on R2

- イブロック冷感S, DHCエルシスホワイト240

**Artifacts:** `results_batch_1.json`, `batch_1_run.log`
