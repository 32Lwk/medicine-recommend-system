# data/ カタログ（medicine-recommendation-advisor 用）

スコアリング・推奨評価で参照するローカルデータの一覧。

## 必須（リポジトリに含める方針）

| ファイル | 状態 | 用途 |
|----------|------|------|
| `otc_medicine_data.csv` | `data/otc_medicine_data.csv`（約 7.5MB）— リポジトリに含める | 推奨候補の主カタログ |

**運用**: PMDA 由来データを更新したら差分 PR。push サイズが問題なら Git LFS を検討。エージェント評価前に必ずローカルでファイル存在を確認。

```bash
git add data/otc_medicine_data.csv   # 未追跡の場合のみ
```

## 同梱済み（本リポジトリ）

| ファイル | 用途 |
|----------|------|
| `symptom_dictionary.json` | 症状同義語・NLU |
| `ingredient_dictionary.json` | 成分正規化 |
| `medicine_side_effects.csv` | 副作用スコア |
| `medicine_interactions.csv` | 相互作用スコア |
| `kanpo_medicine.csv` | 漢方特化ルール |
| `summarized_efficacy_data.csv` | GPT 補助効能（Physical 主経路外） |
| `store_products.json` | 店舗商品（推奨スコア外） |
| `user_preference_keyword_catalog.json` | 嗜好 GPT 参照語・安全強制語・スコア前除外ルール |

## 更新時

1. PMDA 等で差分確認 → CSV 修正
2. golden case と `log/reviews/` の不整合レポートを照合
3. CHANGELOG / PR にデータ更新理由を記載
