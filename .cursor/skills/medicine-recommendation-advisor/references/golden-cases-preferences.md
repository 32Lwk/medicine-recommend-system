# Golden Cases: ユーザー嗜好（LLM + 安全強制）

## GC-PREF-001 運転 + 花粉症

- **入力**: `花粉症で鼻水とくしゃみ。車の運転もします。`
- **期待**:
  - `user_preferences.avoid_drowsiness` = true（安全強制、confidence 1.0）
  - top3 に第1世代抗ヒスタミン単独が dominance しない
  - `user_preferences_summary` API に含まれる

## GC-PREF-002 口渇が少ない薬（嗜好）

- **入力**: `花粉症で口が渇きにくい薬を探しています`
- **期待**:
  - `avoid_dry_mouth` = true（GPT、confidence ≥ 0.5）
  - 症状「口渇」としての主訴自動変換は **しない**
  - confidence ≥ 0.8 時、第1世代・抗コリン系含有品は候補から除外され得る

## GC-PREF-003 点鼻回避

- **入力**: `花粉症です。点鼻は苦手です`
- **期待**:
  - `avoid_nasal_route` = true
  - 血管収縮点鼻・点鼻複合は除外（ステロイド点鼻は残る）

## GC-PREF-004 属性モーダル other_info

- **other_info**: `眠気が心配、1日1回がいい`
- **症状チャット**: `花粉症で鼻水`
- **期待**: `preference_context_text` 結合後、嗜好 NLU が `avoid_drowsiness` と `preferred_max_daily_doses=1` を検出
