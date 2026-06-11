# 手動 QA: ユーザー嗜好 LLM 統合

開発環境で推奨フローを通したうえで確認するチェックリスト。

## 花粉症 + 運転（GC-PREF-001）

1. チャット: `花粉症で鼻水とくしゃみ。車の運転もします。`
2. 期待: top に第2世代抗ヒスタミン系が優先、総合感冒薬のみが top1 にならない
3. 推奨 JSON / ログ: `user_preferences_summary.avoid_drowsiness` = true、`sources.avoid_drowsiness` = safety

## 口渇が少ない薬（GC-PREF-002）

1. `花粉症で口が渇きにくい薬を探しています`
2. 期待: `avoid_dry_mouth` = true（GPT、confidence ≥ 0.5）
3. 症状としての「口渇」単独では `avoid_dry_mouth` が立たないこと

## 点鼻回避（GC-PREF-003）

1. `花粉症です。点鼻は苦手です`
2. 期待: 血管収縮点鼻が top から外れる／ステロイド点鼻は残り得る

## 属性モーダル other_info（GC-PREF-004）

1. 属性モーダル「その他」: `眠気が心配、1日1回がいい` → 送信
2. チャット: `花粉症で鼻水`
3. セッション再読込後も `other_info` が保持されていること
4. `preferred_max_daily_doses` または `prefer_fewer_daily_doses` が summary に反映

## 英語入力（GC-PERS-I18N-001）

1. `I have a runny nose and sneezing. It's allergy season.`
2. NLU 症状名が日本語 canonical（鼻水・くしゃみ）
3. 鼻炎用薬方向の推奨

## 回帰

- `pytest tests/core/test_pollen_rhinitis_*.py tests/core/test_preference_*.py tests/agents/test_nlu_resolve_parallel.py -q`
