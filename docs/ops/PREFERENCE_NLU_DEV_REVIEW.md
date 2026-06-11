# 嗜好 NLU 開発レビュー（advisor 用チェックリスト）

[`data/user_preference_keyword_catalog.json`](../data/user_preference_keyword_catalog.json) と除外ルールの品質確認用。

## カタログ

- [ ] 全 `preference_field` が `preference_merge.PREFERENCE_BOOL_FIELDS` と一致
- [ ] `safety_hard_keywords` に運転・妊娠・授乳の誤検出がないか
- [ ] `gpt_reference_keywords` が症状主訴と混同しにくいか（特に `avoid_dry_mouth`）
- [ ] `risk_exclude_rules` の `min_confidence` が 0.8 であること

## 除外ルール

- [ ] `avoid_drowsiness` → `first_gen_antihistamine` のみ（2nd gen は残る）
- [ ] `avoid_nasal_route` → 血管収縮点鼻・combo のみ（`nasal_steroid_allergy` は除外リストに含めない）
- [ ] 服用回数は **除外ルールに含めない**（加点/減点のみ）

## Golden

- [ ] [golden-cases-preferences.md](../.cursor/skills/medicine-recommendation-advisor/references/golden-cases-preferences.md) の 4 ケースを手動またはテストで追跡

## API

- [ ] 推奨レスポンスに `user_preferences_summary` が含まれる
- [ ] `sources` に `llm` / `safety` が入る
