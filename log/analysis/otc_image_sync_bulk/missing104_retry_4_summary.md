# missing104 再試行 batch 4 サマリー

**実行日:** 2026-07-26  
**入力:** `missing104_batch_4.json`（23件）  
**結果:** `results_missing104_retry_4.json`

## 最終統計

| 指標 | 件数 |
|------|------|
| total | 23 |
| **uploaded** | **21** |
| skipped_exists | 2 |
| not_found | 0 |
| review_rejected | 0 |
| errors | 0 |

### ソース内訳（uploaded）

| source | 件数 |
|--------|------|
| official_url | 20 |
| rakuten_ec | 1 |

## 手順

1. 楽天検索 + JAN 調査で全23品目の `official_url` / `candidate_urls` / `research_note` を `missing104_batch_4.json` に反映（調査ログ: `batch4_research.json`）
2. `scripts/sync_otc_images_retry.py --label missing104_retry_4 --upload --delay 0.8` を実行
3. `scripts/sync_top50_otc_images.py` の `OFFICIAL_IMAGE_URLS` を batch 4 検証 URL で更新
4. **イスロンＧⅡ** — 初回 retry が楽天検索ノイズ（ゴルフクラブ画像）を拾ったため、`4992873046703` の正しい URL で R2 を手動差し替え

## R2 アップロード済み（21件・新規）

1. 日野百草丸
2. 百草丸プラス
3. 増田胃腸薬
4. ヤマサンオウレン末
5. ヤマサンオウレン
6. トチモトのオウレンＰ
7. トチモトのオウレン末Ｐ
8. 薬草健胃薬Ｆ
9. 恵命我神散Ｓ＜細粒＞
10. フラーリンＪ錠
11. はらはら薬「翁丸」
12. ニチイ胃腸内服液
13. やまと丸
14. 複方熊胆円
15. 複方熊胆丸
16. 新マルコターンソフト
17. 熊膽圓Ｓ
18. イスロンＧⅡ（差し替え後）
19. タブローンＭⅡ
20. パンジアス顆粒
21. ハイウルソグリーンＳ

## skipped_exists（2件・R2 既存）

- 新グリーン胃腸薬ＤＸ
- 胃腸薬エースプラス

## 備考

- batch 4 は胃腸薬ロングテール中心。マツキヨ未掲載が多く、楽天 EC / Yahoo EC の JAN 画像が主ソース。
- 配置薬系（イスロンＧⅡ 等）は EC 画像が少なく、初回マルチソースで誤ヒットしやすい。`OFFICIAL_IMAGE_URLS` 登録で次回以降を安定化。
- missing104 全4バッチ（95件）の再試行が完了。
