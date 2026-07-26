# missing104 retry batch 2 — サマリー

**実行日:** 2026-07-26  
**ラベル:** `missing104_retry_2`  
**入力:** `missing104_batch_2.json`（24 件）

## 最終統計

| 指標 | 件数 |
|------|------|
| **total** | 24 |
| **uploaded** | 24 |
| **skipped_exists** | 0 |
| **not_found** | 0 |
| **review_rejected** | 0 |
| **errors** | 0 |

### ソース内訳（uploaded）

| source | 件数 |
|--------|------|
| official_url（candidate_urls / official_url 指定） | 23 |
| rakuten_ec（マルチソース自動解決） | 1 |

## 調査方針

1. 楽天・Yahoo 検索 + `verify_image_match` で商品名・メーカー一致を確認
2. JAN コード付き `shop.r10s.jp` URL を優先（パッケージ画像）
3. 佐藤製薬ストナデイタイムは stona.jp 公式画像が別商品（のどスプレー）のため、楽天 reg-kenseido を `OFFICIAL_IMAGE_URLS` に登録
4. 摩耶堂 清風散は JAN 4987045109287 を使用（drugpure 4987210301034 は別商品）

## アップロード成功（24 件）

| # | 商品名 | メーカー | R2 URL |
|---|--------|----------|--------|
| 1 | ニタンダ麻杏甘石湯エキス顆粒 | 二反田薬品工業 | https://images.yutok.dev/otc/ニタンダ麻杏甘石湯エキス顆粒.webp |
| 2 | ヤマサンシャゼンソウ | 小島漢方 | https://images.yutok.dev/otc/ヤマサンシャゼンソウ.webp |
| 3 | ストナデイタイム | 佐藤製薬 | https://images.yutok.dev/otc/ストナデイタイム.webp |
| 4 | グロンサンゴールド錠Ａ | 廣貫堂 | https://images.yutok.dev/otc/グロンサンゴールド錠A.webp |
| 5 | エイクレス | 大石膏盛堂 | https://images.yutok.dev/otc/エイクレス.webp |
| 6 | コリクリアーＳローション | 東光薬品工業 | https://images.yutok.dev/otc/コリクリアーSローション.webp |
| 7 | オムニンエース | オール薬品工業 | https://images.yutok.dev/otc/オムニンエース.webp |
| 8 | ウチダの大黄牡丹皮湯 | ウチダ和漢薬 | https://images.yutok.dev/otc/ウチダの大黄牡丹皮湯.webp |
| 9 | ザッツ | 武田コンシューマーヘルスケア | https://images.yutok.dev/otc/ザッツ.webp |
| 10 | 新リバヘルスゴールド | 大峰堂薬品工業 | https://images.yutok.dev/otc/新リバヘルスゴールド.webp |
| 11 | 清風散 | 摩耶堂製薬 | https://images.yutok.dev/otc/清風散.webp |
| 12 | ヒストミンせき止め液ＮＸ | 小林薬品工業 | https://images.yutok.dev/otc/ヒストミンせき止め液NX.webp |
| 13 | ナカジマキキョウ末 | 中嶋生薬 | https://images.yutok.dev/otc/ナカジマキキョウ末.webp |
| 14 | 再春痛散湯エキス顆粒 | 再春館製薬所 | https://images.yutok.dev/otc/再春痛散湯エキス顆粒.webp |
| 15 | ウチダの麻黄附子細辛湯 | ウチダ和漢薬 | https://images.yutok.dev/otc/ウチダの麻黄附子細辛湯.webp |
| 16 | 新セキリック液 | 米田薬品 | https://images.yutok.dev/otc/新セキリック液.webp |
| 17 | クールワンせき止めＧＸプラス | テイカ製薬 | https://images.yutok.dev/otc/クールワンせき止めGXプラス.webp |
| 18 | カコナールせき止め液Ｗ | 日新薬品工業 | https://images.yutok.dev/otc/カコナールせき止め液W.webp |
| 19 | のどスッキリスプレーＡＣ | 健栄製薬 | https://images.yutok.dev/otc/のどスッキリスプレーAC.webp |
| 20 | 清痛顆粒 | 第一薬品工業 | https://images.yutok.dev/otc/清痛顆粒.webp |
| 21 | クミアイ解熱鎮痛錠 | 協同薬品 | https://images.yutok.dev/otc/クミアイ解熱鎮痛錠.webp |
| 22 | 竹参かぜまる | タキザワ漢方廠 | https://images.yutok.dev/otc/竹参かぜまる.webp |
| 23 | ササイサン | 和漢薬研究所 | https://images.yutok.dev/otc/ササイサン.webp |
| 24 | フラーリンＪ粒 | 剤盛堂薬品 | https://images.yutok.dev/otc/フラーリンJ粒.webp |

## 成果物

- 更新プラン: `missing104_batch_2.json`（`official_url` / `candidate_urls` / `research_note` 追加）
- 実行結果: `results_missing104_retry_2.json`
- 登録先: `scripts/sync_top50_otc_images.py` → `OFFICIAL_IMAGE_URLS`（24 件追加）

## 備考

- 初回実行で全件成功のため、stubborn failure の再実行は不要
- ストナデイタイムは初回 `official_url`（stona.jp）経由でアップロード済みだが、`OFFICIAL_IMAGE_URLS` には正しい楽天パッケージ URL を登録（次回以降の品質向上）
