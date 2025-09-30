# セッション管理と追加質問機能 - 実装完了

## ✅ 実装完了内容

### 1. ユーザー属性データのセッション管理

**セッションに保存される属性データ:**
```python
session['user_attributes'] = {
    'age': None,              # 年齢
    'gender': None,           # 性別
    'pregnant': None,         # 妊娠中かどうか
    'breastfeeding': None,    # 授乳中かどうか
    'current_medications': [], # 服用中の薬
    'allergies': [],          # アレルギー
    'medical_history': []     # 既往症
}
```

### 2. メッセージからの自動抽出

**年齢の抽出:**
```
ユーザー: "30歳です。頭が痛いです。"
→ user_attributes['age'] = 30
→ セッションに保存
```

**性別の抽出:**
```
ユーザー: "女性です。頭が痛いです。"
→ user_attributes['gender'] = '女性'
→ セッションに保存
```

**妊娠・授乳状態の抽出:**
```
ユーザー: "妊娠中です。頭が痛いです。"
→ user_attributes['pregnant'] = True

ユーザー: "妊娠していないです。"
→ user_attributes['pregnant'] = False
```

**アレルギーの抽出:**
```
ユーザー: "アレルギーはありません。"
→ user_attributes['allergies'] = ['なし']

ユーザー: "アレルギー: 卵、小麦"
→ user_attributes['allergies'] = ['卵、小麦']
```

### 3. セッションの永続化

**セッションライフサイクル:**
```
1. 初回アクセス
   → session['user_attributes'] を初期化
   → すべてNone/空配列

2. ユーザーが情報を提供
   → メッセージから抽出
   → session['user_attributes'] に保存

3. 次回の推奨時
   → session['user_attributes'] から取得
   → 不足情報のみを質問

4. セッション継続中
   → 属性データが蓄積
   → より正確な推奨が可能
```

### 4. 追加質問の表示

**HTML表示:**
```html
<div class="question-box" style="background-color: #fff3e0; border-left: 4px solid #ff9800; padding: 15px; margin: 10px 0;">
    <strong>❓ 追加でお伺いしたいこと</strong>
    <span style="color: #ff9800; font-weight: bold;">（優先度: 任意）</span><br>
    <p style="margin: 5px 0;">
        より安全な使用のため、可能であれば以下の情報を教えてください：
    </p>
    <ul style="margin: 10px 0; padding-left: 20px;">
        <li>症状はいつ頃から続いていますか？（例：昨日から、3日前から）</li>
        <li>薬や食品のアレルギーはありますか？（ある場合は具体的に教えてください）</li>
    </ul>
</div>
```

## 🔄 動作フロー

### 初回アクセス
```
ユーザー: "頭が痛いです。"
    ↓
セッション初期化:
  user_attributes = {age: None, gender: None, ...}
    ↓
不足情報チェック:
  - 年齢: なし → 質問に追加
  - 性別: なし
  - アレルギー: なし → 質問に追加
    ↓
推奨を表示 + 追加質問表示:
  ❓ 追加でお伺いしたいこと（優先度: 必須）
  1. 年齢を教えてください。
  2. 薬や食品のアレルギーはありますか？
```

### 2回目のアクセス（情報提供）
```
ユーザー: "30歳です。アレルギーはありません。"
    ↓
メッセージから抽出:
  age_match = "30歳" → age = 30
  "アレルギー...ない" → allergies = ['なし']
    ↓
セッションに保存:
  user_attributes['age'] = 30
  user_attributes['allergies'] = ['なし']
    ↓
不足情報チェック:
  - 年齢: あり ✓
  - アレルギー: あり ✓
  - 症状期間: なし → 質問に追加（optional）
    ↓
推奨を表示 + オプション質問:
  ❓ 追加でお伺いしたいこと（優先度: 任意）
  1. 症状はいつ頃から続いていますか？
```

### 3回目のアクセス（症状相談）
```
ユーザー: "今度は鼻水が出ます。"
    ↓
セッションから属性取得:
  age = 30 ✓
  allergies = ['なし'] ✓
    ↓
不足情報チェック:
  - 年齢: あり ✓
  - アレルギー: あり ✓
  - 症状期間: なし → 質問（optional）
    ↓
推奨を表示 + 最小限の質問
```

## 📊 セッションデータの確認

**ログ出力例:**
```
📋 Extracted age from message: 30
📋 No allergies detected
📋 Detected gender: 女性
📋 Detected pregnancy status from message
```

**セッション状態:**
```json
{
  "user_attributes": {
    "age": 30,
    "gender": "女性",
    "pregnant": false,
    "breastfeeding": false,
    "current_medications": [],
    "allergies": ["なし"],
    "medical_history": []
  }
}
```

## 🎯 改善点

### Before（修正前）
```
❌ 属性データがセッションで管理されていない
❌ 毎回同じ質問を繰り返す
❌ 追加質問が表示されない
❌ ユーザー情報が蓄積されない
```

### After（修正後）
```
✅ 属性データをセッションで管理
✅ 一度答えた質問は繰り返さない
✅ 追加質問が明確に表示される
✅ セッション中に情報が蓄積
✅ より正確な推奨が可能
```

## 📂 修正ファイル

1. **app.py**
   - 182-192行目: ユーザー属性データの初期化
   - 403-478行目: メッセージからの属性抽出とセッション保存

2. **templates/index.html**
   - 455-482行目: 追加質問の表示（HTML）
   - 827-848行目: 追加質問の表示（JavaScript）

3. **rule_based_recommendation.py**
   - 既存の不足情報チェック機能を活用

## 🎉 完成

すべての要件が実装されました：

- [x] ユーザー属性データのセッション管理
- [x] メッセージからの自動抽出
- [x] セッションへの永続化
- [x] 不足情報の質問表示
- [x] 優先度別の質問メッセージ
- [x] 情報の蓄積による推奨精度向上

システムは完全に機能しています！
