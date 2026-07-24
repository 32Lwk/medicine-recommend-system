# 推奨候補フィルタ — 製品除外リスト

ルールベース推奨（`rule_based_recommendation`）では、`data/otc_medicine_data.csv` の全行を候補にするわけではない。小児専用・特殊用途・乗り物酔い専用などと同様に、**消費者向け推奨に不向きな製品**を候補プールから除外する。

## 推奨除外リスト（`RECOMMENDATION_EXCLUDED_PRODUCTS`）

正本: [src/core/recommendation_constants.py](../../src/core/recommendation_constants.py)

| 製品名 | メーカー | CSV | 推奨 | 理由 |
|--------|----------|-----|------|------|
| イブプロフェン錠２００Ｓ | 奥田製薬 | 残す | **除外** | ジェネリック名のみ・大手 EC 未掲載・商品画像なし |
| イブプロフェン錠２００ＳＣ | セントラル製薬 | 残す | **除外** | 同上 |

**除外しても製品が存在しないわけではない**（JAPIC / KEGG / 添付文書で実在確認済み）。ユーザーが店頭で特定・購入しにくく、代替（トキワイブプロエースＡ、イブ/EVE 系等）があるため推奨画面には載せない。

## 判定・適用箇所

1. **`is_recommendation_excluded_product()`** — [src/core/medicine_classifiers.py](../../src/core/medicine_classifiers.py)  
   製品名を NFKC + 半角数字で正規化し、リストと**完全一致**で判定（部分一致しない）。

2. **`get_candidate_medicines()`** — [src/core/candidate_scoring.py](../../src/core/candidate_scoring.py)  
   CSV 行を候補 dict に変換する `append_candidate` の早い段階で return。

3. **`rule_based_recommendation()`** — [src/core/rule_based_recommendation.py](../../src/core/rule_based_recommendation.py)  
   小児専用フィルタの直後に二重チェック（ログ: `推奨除外リストのため候補をN件除外`）。

## リストへの追加手順

1. `RECOMMENDATION_EXCLUDED_PRODUCTS` に全角・半角両方の表記を追加（任意だが推奨）
2. `tests/core/test_recommendation_excluded_products.py` に除外対象と**除外されない類似品**のテストを追加
3. CHANGELOG.md に理由（EC 未掲載・画像・UX 等）を記載
4. **CSV から行削除はしない**（PMDA 正本・KB・分析用途を維持）

## 関連フィルタ（別リスト）

| フィルタ | モジュール | 用途 |
|----------|------------|------|
| 小児専用 | `medicine_classifiers._is_pediatric_specific` | 15 歳以上 / 年齢不明ユーザー向け |
| 特殊用途 | `is_specific_use_medicine` | ホルモン剤等 |
| 乗り物酔い専用 | `_is_motion_sickness_medicine` | 症状なし時 |
| ドーピング | `RECO_SPORTS_DOPING_FILTER` | 競技文脈 |

## 関連

- OTC 画像: [CLOUDFLARE_R2_IMAGES.md](./CLOUDFLARE_R2_IMAGES.md)
- 変更履歴: [CHANGELOG.md](../../CHANGELOG.md)（2026-07-25）
