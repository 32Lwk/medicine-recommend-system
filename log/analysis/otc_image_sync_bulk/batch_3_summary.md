# OTC Image Bulk Sync — Batch 3 Summary

**Run date:** 2026-07-26 (JST)  
**Initial command:** `.venv/bin/python scripts/sync_otc_images_bulk.py --batch 3 --upload --delay 0.6`  
**Batch plan:** `log/analysis/otc_image_sync_bulk/batch_3.json` (111 items)

## Final results (after high-priority retry)

| Metric | Count |
|--------|------:|
| Total | 111 |
| **Newly uploaded to R2 (batch 3 total)** | **57** |
| — initial Matsukiyo pass | 40 |
| — retry after `OFFICIAL_IMAGE_URLS` (shop.r10s.jp) | 17 |
| Skipped (already on R2) | 12 |
| Not found (no image source) | 42 |
| Review rejected | 0 |
| Download error | 0 |
| Upload error | 0 |

**Success rate (upload + skip):** 69 / 111 (62.2%)

## High-priority URL research & retry

**17 items** qualified (`source=missing_top200` or `recommendation_count>=10`). All were `not_found` on the initial run.

- Researched package images via Rakuten search (JAN / product name) → `shop.r10s.jp` URLs.
- Validated download size and `verify_image_match` before adding to `scripts/sync_top50_otc_images.py` → `OFFICIAL_IMAGE_URLS` (+17 keys).
- Re-ran failed high-priority items only: **17 new uploads**, 0 errors.

**High-priority not_found remaining:** 0

### Retry uploads (17)

- イブプロフェン錠２００Ｓ
- セイヨン総合かぜ薬
- 新スカイブブロンゴールド錠
- カイゲンＡＺのどスプレー
- スカイブブロンストレート
- 新ストナエースＧ
- 救風
- カゼンエース
- 新スカイブブロンゴールド微粒
- 健栄のどフレッシュ
- コーフパウダー
- 第一三共胃腸薬コアブロック散剤
- 新エスタックイブエースカプセル
- スカイブブロンＮＡスプレー
- グットエイドＥＸ
- ジキニン鼻炎ＡＧ顆粒
- クミアイ新頭痛錠

## Initial pass uploads (40)

- ストッパ下痢止めEX
- バファリンEX
- リングルN
- バファリンルナJ
- イブクイック頭痛薬DX
- 小児用バファリンCII
- バファリンプレミアムDX
- ロキソニンSクイック
- ナロンメディカル
- ナロンエースプレミアム
- ナロンエース
- バファリンルナi
- バファリンライト
- ナロン錠
- ベンザブロックL
- ストナジェルNS
- ベンザブロックLプレミアム
- ベンザブロックLプレミアム錠
- ベンザブロックL錠
- ベンザブロックS
- パブロン点鼻クイックJL
- パブロン点鼻JL
- ナザールGスプレークール
- ナザールGスプレー
- ストナリニZ
- ストナリニZジェル
- パブロン点鼻EX
- ナザールAR<季節性アレルギー専用>
- ナザールαAR<季節性アレルギー専用>
- ストナリニ・サット
- パブロン点鼻クイック
- パブロン点鼻
- ナザールスプレー
- アレジオン20
- ストナリニ・ガード
- ストナリニ・サット小児用
- ナザールαAR0.1%<季節性アレルギー専用>
- ナザール「スプレー」《ポンプ》
- ナザールαAR0.1%C<季節性アレルギー専用>
- アレグラFX

## Skipped — already on R2 (12)

- 新セルベール整胃プレミアム<錠>
- 新セルベール整胃プレミアム<細粒>
- リングルN300
- トキワイブプロエースA
- イブA錠EX
- バファリンA
- イブA錠
- ロキソニンSプレミアム
- ロキソニンS
- ナロン顆粒
- バファリンプレミアム
- ストナリニS

## Not found (42)

- ハイロスラック
- ナロンエースR
- エキセドリンA錠
- エキセドリンプラスS
- ナロンエースT
- 大正トンプク
- ナロンエースプラス
- アナロンゴールド内服液
- エキセドリンカプセル
- エスタックEXネオ
- ベンザブロックIPプレミアム錠
- パブロンセレクトT
- パブロンメディカルC
- パブロンメディカルN
- パブロンメディカルT
- ベンザエースA
- ベンザエースAゴールドW錠
- ベンザエースA錠
- ベンザブロックIPプラス
- ベンザブロックIPプラス錠
- ベンザブロックIPプレミアム
- ベンザブロックLプラス
- ベンザブロックLプラス錠
- ベンザブロックSプラス
- ベンザブロックSプラス錠
- ベンザブロックSプレミアム
- ベンザブロックSプレミアム錠
- パブロンセレクトN
- パブロンセレクトCV
- パブロンセレクトC
- ストナジェルサイナスEX
- ストナプラスジェルS
- パブロンSα<錠>
- パブロン鼻炎カプセルSα
- パブロン鼻炎カプセルZ
- パブロン鼻炎カプセルSα小児用
- パブロン鼻炎速溶錠EX
- パブロン鼻炎速溶錠
- パブロン鼻炎アタックJL<季節性アレルギー専用>
- パブロン鼻炎アタック<季節性アレルギー専用>
- クラリチンEXOD錠
- クラリチンEX

## Artifacts

- Results JSON: `log/analysis/otc_image_sync_bulk/results_batch_3.json`
- Merged: `log/analysis/otc_image_sync_bulk/results_all.json` (443 items cumulative after merge)
- Code change: `scripts/sync_top50_otc_images.py` (`OFFICIAL_IMAGE_URLS` +17)

## Notes

- Initial bulk run ~12 min (111 items, `--delay 0.6`).
- R2 credentials from `.env`.
- Remaining 42 not_found are low-priority `famous_brand` / one `famous_csv_fill` (ハイロスラック); manual manufacturer URLs may help in a future batch.
