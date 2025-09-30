# ハイブリッド医薬品推奨システム統合ドキュメント

## 概要

`app.py`にルールベースアルゴリズムとChatGPTベースアルゴリズムを組み合わせたハイブリッドシステムを統合しました。

## システムアーキテクチャ

```
ユーザー入力
    ↓
【ステップ1】ChatGPTで医薬品の種類を判定
    ↓
    ├─→ 風邪薬 / 解熱鎮痛薬 / 鼻炎用薬
    │      ↓
    │   【ステップ2】ルールベースアルゴリズム（安全性重視）
    │      ├─ NLU: 症状抽出（ChatGPT or パターンマッチング）
    │      ├─ 安全性チェック（年齢・妊娠・禁忌・Red Flag）
    │      ├─ 候補薬取得
    │      ├─ スコアリング
    │      ├─ 上位3件推奨
    │      └─ 説明生成
    │
    └─→ その他の医薬品
           ↓
        【ステップ2】ChatGPTベースアルゴリズム
           └─ 従来の包括的推奨システム
```

## 実装の詳細

### 1. インポートの追加

```python
from medicine_logic import rule_based_medicine_recommendation, analyze_symptoms_and_medicine_type, client
```

### 2. ハイブリッド推奨ロジック

#### ステップ1: 医薬品種類の判定
```python
analysis_result = analyze_symptoms_and_medicine_type(user_message, client)
medicine_type = analysis_result.get('medicine_type', 'その他')
```

#### ステップ2: アルゴリズムの選択
```python
target_types = ['風邪薬', '解熱鎮痛薬', '鼻炎用薬']

if medicine_type in target_types:
    # ルールベースアルゴリズム使用
    recommendation_result = rule_based_medicine_recommendation(...)
else:
    # ChatGPTベースアルゴリズム使用
    recommendation_result = comprehensive_medicine_recommendation(...)
```

### 3. ユーザー情報の取得

#### セッションからの取得
```python
user_info = {
    'age': session.get('age'),
    'gender': session.get('gender'),
    'pregnant': session.get('pregnant', False),
    'breastfeeding': session.get('breastfeeding', False),
    'current_medications': session.get('current_medications', []),
    'allergies': session.get('allergies', [])
}
```

#### メッセージからの抽出
```python
# 年齢の抽出
age_match = re.search(r'(\d+)\s*歳', user_message)
if age_match:
    user_info['age'] = int(age_match.group(1))

# 妊娠状態の検出
if '妊娠' in user_message or '妊婦' in user_message:
    user_info['pregnant'] = True

# 授乳状態の検出
if '授乳' in user_message:
    user_info['breastfeeding'] = True
```

### 4. 年齢制限データの反映

CSVファイルのG列（7列目）に年齢制限情報があることを前提に、`rule_based_recommendation.py`で正しく取得：

```python
# CSVのG列（インデックス6）から年齢制限を取得
age_restriction = row.get('年齢制限', '')

# インデックスでも取得を試みる（バックアップ）
if not age_restriction and len(row) > 6:
    age_restriction = row.iloc[6] if hasattr(row, 'iloc') else ''
```

### 5. 結果の表示

#### ルールベース結果の場合
```html
<h5>🏆 1位: 製品名 (メーカー名)</h5>
<p><strong>適合スコア:</strong> 0.422</p>
<p><strong>推奨理由:</strong> この医薬品は咳に適応しています。風邪薬として効果が期待できます。</p>
```

#### エスカレーションの場合
```html
<div class="recommendation-result escalation">
    <h4>⚠️ 重要な注意事項</h4>
    <p class="escalation-warning"><strong>重症疑い症状が検出されました: 高熱</strong></p>
    <h4>🏥 推奨される対応</h4>
    <ul>
        <li>速やかに医師の診察を受けてください</li>
        <li>市販薬での自己治療は推奨されません</li>
        <li>症状が悪化する場合は救急医療機関へ</li>
    </ul>
</div>
```

## 動作フロー例

### 例1: 風邪の症状（ルールベース使用）

```
ユーザー: 「喉が痛くて咳も出ます。熱もあります。」

→ ChatGPTで判定: 医薬品の種類 = "風邪薬"
→ ルールベースアルゴリズム起動
→ NLU: 症状抽出 = ["のどの痛み", "咳", "発熱"]
→ 安全性チェック: 問題なし
→ スコアリング: 上位3件選出
→ 結果表示:
   - 使用アルゴリズム: ルールベースアルゴリズム（安全性重視）
   - 推奨医薬品: 清風散、麻黄湯、新ルルエース
```

### 例2: 胃腸薬（ChatGPTベース使用）

```
ユーザー: 「胃が痛くて吐き気がします。」

→ ChatGPTで判定: 医薬品の種類 = "胃腸薬"
→ ChatGPTベースアルゴリズム起動（従来通り）
→ 結果表示:
   - 使用アルゴリズム: ChatGPTベースアルゴリズム
   - 推奨医薬品: （ChatGPTの推奨結果）
```

### 例3: 重症疑い（エスカレーション）

```
ユーザー: 「39度の高熱が3日間続いています。呼吸も苦しいです。」

→ ChatGPTで判定: 医薬品の種類 = "風邪薬"
→ ルールベースアルゴリズム起動
→ NLU: Red Flag検出 = ["高熱", "呼吸困難"]
→ 安全性チェック: エスカレーション必要
→ 結果表示:
   - ⚠️ 重要な注意事項
   - 速やかに医師の診察を受けてください
```

## ログ出力

ハイブリッドシステムは詳細なログを出力します：

```
💊 Hybrid medicine recommendation system starting...
🔍 Step 1: Analyzing medicine type with ChatGPT...
📋 Detected medicine type: 風邪薬
📋 Detected symptoms: ['のどの痛み', '咳']
✅ Using RULE-BASED algorithm for 風邪薬
📋 Extracted age from message: 30
=== ルールベース医薬品推奨システム 開始 ===
--- ステップ1: NLU（症状抽出） ---
=== 簡易NLU結果 ===
検出された症状: ['のどの痛み', '咳']
--- ステップ2: 安全性チェック ---
--- ステップ3: 候補医薬品取得 ---
推定された医薬品の種類: {'風邪薬'}
候補医薬品数: 221
--- ステップ4: スコアリング ---
清風散: 0.422
--- ステップ5: 説明生成 ---
💊 MEDICINE_LOGIC CALL:
   Function: hybrid_recommendation (rule_based)
   Execution Time: 2.153s
```

## アルゴリズムの判別

結果に`algorithm`フィールドが追加され、使用されたアルゴリズムを追跡できます：

- `rule_based`: ルールベースアルゴリズム
- `chatgpt`: ChatGPTベースアルゴリズム
- `chatgpt_fallback`: ルールベース失敗時のChatGPTフォールバック

## フォールバック機能

1. **ルールベースアルゴリズムでエラー発生時**
   → ChatGPTベースアルゴリズムに自動切り替え

2. **ChatGPT APIが使用不可の場合**
   → 簡易パターンマッチングで症状抽出

3. **年齢情報が不足の場合**
   → デフォルト値（30歳）を使用し、警告ログを出力

## セキュリティと安全性

### 1. 年齢制限チェック
- 7歳未満: 絶対に医師相談（エスカレーション）
- 7〜14歳: 注意喚起
- 15歳以上: 問題なし

### 2. Red Flag症状
以下の症状が検出された場合、即座にエスカレーション：
- 高熱（38.5度以上）
- 呼吸困難
- 胸痛
- 意識障害
- 吐血・血便

### 3. 妊娠・授乳中
- 禁忌薬の除外
- 警告メッセージの表示
- NSAIDs含有製品の除外

## テスト方法

### 基本的なテスト

```bash
# アプリケーション起動
python app.py

# ブラウザで http://127.0.0.1:5000 にアクセス

# テストケース:
1. "喉が痛くて咳が出ます" → ルールベース（風邪薬）
2. "頭が痛いです" → ルールベース（解熱鎮痛薬）
3. "鼻水とくしゃみが止まりません" → ルールベース（鼻炎用薬）
4. "胃が痛いです" → ChatGPTベース（胃腸薬）
5. "39度の高熱が3日続いています" → エスカレーション
6. "5歳の子供が咳をしています" → エスカレーション（年齢制限）
7. "妊娠中で頭が痛いです" → 警告付き推奨
```

## 今後の改善点

1. **ユーザー情報入力UI**
   - 年齢、性別、妊娠状態などを入力するフォーム
   - セッション管理の改善

2. **アルゴリズム選択の最適化**
   - より精緻な医薬品種類の判定
   - 複数の医薬品種類が必要な場合の処理

3. **監査機能の強化**
   - ダッシュボードでアルゴリズム使用率を表示
   - エスカレーション率の追跡

4. **A/Bテスト機能**
   - ルールベース vs ChatGPTベースの比較
   - ユーザーフィードバックの収集

## ファイル構成

```
medicine recomend/
├── app.py                              # メインアプリケーション（ハイブリッド統合済み）
├── medicine_logic.py                   # 推奨ロジック
├── rule_based_recommendation.py        # ルールベースアルゴリズム
├── HYBRID_SYSTEM_INTEGRATION.md        # このドキュメント
├── RULE_BASED_ALGORITHM.md             # ルールベースアルゴリズム詳細
└── log/
    └── recommendation_log.jsonl        # 監査ログ
```

## まとめ

✅ **統合完了**
- ルールベースアルゴリズムとChatGPTベースアルゴリズムのハイブリッド化
- 風邪薬・解熱鎮痛薬・鼻炎用薬は安全性重視のルールベース
- その他の医薬品は従来のChatGPTベース

✅ **安全性向上**
- Red Flag症状の即時検出
- 年齢制限の厳格なチェック
- 妊娠・授乳中の禁忌薬除外

✅ **説明可能性**
- 使用アルゴリズムの明示
- 推奨理由とスコアの表示
- 詳細なログ出力

✅ **拡張性**
- 新しい医薬品種類の追加が容易
- アルゴリズムの切り替えが柔軟
- フォールバック機能による堅牢性
