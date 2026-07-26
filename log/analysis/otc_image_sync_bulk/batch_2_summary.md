# OTC Image Bulk Sync — Batch 2 Summary

**Run date:** 2026-07-26 (JST)  
**Command:** `.venv/bin/python scripts/sync_otc_images_bulk.py --batch 2 --upload --delay 0.6`  
**Batch plan:** `log/analysis/otc_image_sync_bulk/batch_2.json` (111 items)

## Results

| Metric | Count |
|--------|------:|
| Total | 111 |
| **Newly uploaded to R2** | **30** |
| Skipped (already on R2) | 22 |
| Not found (no image source) | 59 |
| Review rejected | 0 |
| Download error | 0 |
| Upload error | 0 |

**Success rate (upload + skip):** 52 / 111 (46.8%)

## Newly uploaded (30)

目薬・睡眠・禁煙・漢方など:

- サンテPCコンタクト, サンテFXコンタクト, ロートビタうるる洗眼薬W+, ロートV7洗眼薬, ロートCキューブアミノモイスト
- アイリスPC, スマイルコンタクトAL-Wクール, AL-Wマイルド, EXAL-Wクール
- サンテメディカルプラスガードEX, アイリスAGガード, アイボンALd, スマイル40EXゴールドクールMAX
- 新V・ロート, Vロートプレミアム
- ドリエルEX, ドリエル, ドリーミンZ, トメルミン, エスタロンモカ錠
- ニコレット, ニコチネルパッチ10, ニコチネルスペアミント
- ドキシン錠, 雲仙散, 山本漢方ぼうい, ぼういヤマモト, コリホグス, パンセダン, ナリピタン

## Skipped — already on R2 (22)

エスタロンモカ12, ノイロンムーンS, フストールS, デイトナS, エスタロンモカ内服液, カロナールA, 新キャベジンコーワS, 大正漢方胃腸薬（複数 SKU）, キャベジンコーワ細粒, 爽和, 太田胃散（複数）, ビオフェルミン止瀉/下痢止め, 大正胃腸薬K, 液キャベジンコーワL など

## Not found (59)

- **famous_csv_fill:** 51 — マツキヨ検索・既知 URL マップで画像未特定（睡眠改善薬・漢方・ボウイ系など）
- **famous_brand:** 8 — ニコチネルマンゴー, クレンジル, 大正漢方胃腸薬アクティブ&lt;微粒&gt;, パンシロンソフトベール, キャベジンコーワα《瓶》, 正露丸糖衣錠G, 太田胃散&lt;内服液&gt;, 正露丸《瓶》

### High-priority retry (missing_top200 / recommendation_count ≥ 10)

**0 items** — 本バッチの not_found に該当なし。`OFFICIAL_IMAGE_URLS` 追加・部分再実行は実施せず。

## Artifacts

- Run log: `log/analysis/otc_image_sync_bulk/batch_2_run.log`
- Results JSON: `log/analysis/otc_image_sync_bulk/results_batch_2.json`
- Merged (batch 1+2): `log/analysis/otc_image_sync_bulk/results_all.json` — total 221, uploaded 30 (batch 2 only in this run’s new uploads), skipped_exists 54 cumulative, not_found 137 cumulative

## Notes

- Runtime ~10 min (111 × delay + Matsukiyo fetch + R2 upload).
- R2 credentials loaded from `.env`.
- 次の改善候補: famous_brand の 10 件はメーカー公式 / shop.r10s.jp の手動 URL を `scripts/sync_top50_otc_images.py` の `OFFICIAL_IMAGE_URLS` に追加すると再実行で拾える可能性あり（本タスクの高優先度条件外のため未実施）。
