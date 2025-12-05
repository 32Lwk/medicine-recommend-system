# スコアリングシステムの課題分析と改善提案

## 1. 症状と効能効果テキストの照合における不一致リスク

### 1.1 現在のマッチング方法

**実装**:
```python
# calculate_symptom_match_score関数
efficacy_text = normalize_text(candidate.get('efficacy', ''))
normalized_symptom = normalize_text(symptom_name)
synonym_set = {normalized_symptom}
# 同義語を追加
for synonym in dictionary_entry.get("synonyms", []):
    normalized_synonym = normalize_text(synonym)
    if normalized_synonym:
        synonym_set.add(normalized_synonym)

if any(token in efficacy_text for token in synonym_set):
    weight = dictionary_entry.get("weight", 0.5)
    症状スコア += weight
```

**問題点**:
1. **部分一致のみ**: `in`演算子による部分一致のみで、文脈を考慮していない
2. **表現の不一致**: 効能効果テキストの表現と症状名が完全に一致しない場合にマッチしない
3. **同義語の限界**: 同義語リストに含まれていない表現はマッチしない

### 1.2 具体的な不一致例

#### 例1: 表現の違い
- **ユーザー症状**: 「頭がズキズキする」→「頭痛」として抽出
- **効能効果テキスト**: 「頭部の痛み」「頭部痛」「頭部の不快感」
- **結果**: マッチしない可能性（「頭痛」が効能効果テキストに含まれていない場合）

#### 例2: 専門用語の違い
- **ユーザー症状**: 「のどが痛い」→「のどの痛み」として抽出
- **効能効果テキスト**: 「咽頭炎」「咽頭部の炎症」「喉頭痛」
- **結果**: マッチしない可能性（「のど」「喉」が効能効果テキストに含まれていない場合）

#### 例3: 複合表現
- **ユーザー症状**: 「お腹が痛い」→「腹痛」として抽出
- **効能効果テキスト**: 「腹部不快感」「腹部膨満感」「胃腸の痛み」
- **結果**: マッチしない可能性（「腹痛」が効能効果テキストに含まれていない場合）

### 1.3 リスクの影響度

**影響度**: ★★★★☆（高い）

**理由**:
- 最適な医薬品が推奨されない可能性がある
- 症状適合度スコアが低くなり、上位候補から除外される可能性がある
- ユーザーの症状と医薬品の効能が実際には適合しているにも関わらず、スコアが低くなる

### 1.4 改善提案

#### 改善案1: 症状マッピング辞書の拡張（優先度: 高）

**内容**:
- 効能効果テキストでよく使われる表現を症状辞書に追加
- 例: 「頭痛」→「頭部の痛み」「頭部痛」「頭部の不快感」を同義語に追加

**メリット**:
- 実装が容易
- 既存のシステムに影響が少ない

**デメリット**:
- 手動での辞書拡張が必要
- すべての表現を網羅するのは困難

**実装工数**: 16-32時間

#### 改善案2: 意味的類似度の活用（優先度: 中）

**内容**:
- 単語埋め込み（Word2Vec、fastText）やBERTを使用した意味的類似度計算
- 効能効果テキストと症状名の意味的類似度を計算

**メリット**:
- 表現の違いに柔軟に対応
- より正確なマッチングが可能

**デメリット**:
- 実装が複雑
- 計算コストが高い
- 日本語の医療用語に対応したモデルが必要

**実装工数**: 64-128時間

#### 改善案3: 成分情報からの効能推測（優先度: 高）

**内容**:
- 成分情報から効能を推測し、症状マッチングに活用
- 例: イブプロフェン含有 → 解熱鎮痛効果 → 頭痛・発熱にマッチ

**メリット**:
- 効能効果テキストに症状名が含まれていなくても、成分から推測可能
- 既存の成分情報を活用

**デメリット**:
- 成分-効能のマッピング辞書が必要
- 複数成分の組み合わせを考慮する必要がある

**実装工数**: 32-64時間

## 2. 成分情報の活用不足

### 2.1 現在の成分情報の活用状況

**現在の活用**:
1. **副作用リスクスコア**: 副作用データベースから該当成分を検索
2. **相互作用リスクスコア**: 相互作用データベースから該当成分を検索
3. **リスク成分チェック**: 高リスク成分（ヒマシ油、センナなど）の検出
4. **成分多様性の確保**: 推奨医薬品の成分重複を避ける
5. **症状特化型ブースト**: 一部の成分（NSAIDsなど）による症状特化判定

**活用されていない領域**:
1. **成分から効能の推測**: 成分情報から効能を推測して症状マッチングに活用
2. **成分によるスコアブースト**: 症状に適した成分含有によるスコアブースト
3. **成分の組み合わせ評価**: 複数成分の組み合わせによる効果の評価

### 2.2 成分情報を活用した改善案

#### 改善案1: 成分-効能マッピング辞書の作成（優先度: 高）

**内容**:
```python
INGREDIENT_EFFICACY_MAPPING = {
    # 解熱鎮痛成分
    "アセトアミノフェン": {
        "efficacies": ["発熱", "頭痛", "関節痛", "筋肉痛", "生理痛", "歯痛"],
        "boost_score": 0.15
    },
    "イブプロフェン": {
        "efficacies": ["発熱", "頭痛", "関節痛", "筋肉痛", "生理痛", "歯痛"],
        "boost_score": 0.20
    },
    "ロキソプロフェン": {
        "efficacies": ["発熱", "頭痛", "関節痛", "筋肉痛", "生理痛", "歯痛"],
        "boost_score": 0.20
    },
    # 鎮咳成分
    "ジヒドロコデイン": {
        "efficacies": ["咳"],
        "boost_score": 0.15
    },
    "デキストロメトルファン": {
        "efficacies": ["咳"],
        "boost_score": 0.12
    },
    # 抗ヒスタミン成分
    "クロルフェニラミン": {
        "efficacies": ["鼻水", "くしゃみ", "目のかゆみ"],
        "boost_score": 0.15
    },
    "ロラタジン": {
        "efficacies": ["鼻水", "くしゃみ", "目のかゆみ"],
        "boost_score": 0.18
    },
    # 胃腸薬成分
    "制酸剤": {
        "efficacies": ["胃痛", "胸やけ", "胃もたれ"],
        "boost_score": 0.12
    },
    "H2ブロッカー": {
        "efficacies": ["胃痛", "胸やけ"],
        "boost_score": 0.15
    }
}
```

**実装**:
```python
def calculate_ingredient_efficacy_boost(candidate: Dict, nlu_result: Dict) -> float:
    """
    成分情報から効能を推測し、症状マッチングにブーストを付与
    """
    ingredients = candidate.get('ingredients', '')
    if not ingredients:
        return 0.0
    
    symptoms = nlu_result.get("symptoms", [])
    symptom_names = [s.get("name") for s in symptoms]
    
    total_boost = 0.0
    ingredient_list = [ing.strip() for ing in ingredients.split('\n') if ing.strip()]
    
    for ingredient in ingredient_list:
        # 成分名を正規化
        normalized_ingredient = normalize_ingredient_name(ingredient)
        
        # 成分-効能マッピングから検索
        if normalized_ingredient in INGREDIENT_EFFICACY_MAPPING:
            mapping = INGREDIENT_EFFICACY_MAPPING[normalized_ingredient]
            efficacies = mapping.get("efficacies", [])
            boost_score = mapping.get("boost_score", 0.0)
            
            # 症状と効能が一致する場合、ブーストを付与
            if any(symptom in efficacies for symptom in symptom_names):
                total_boost += boost_score
    
    return min(0.25, total_boost)  # 最大0.25まで制限
```

**メリット**:
- 効能効果テキストに症状名が含まれていなくても、成分から推測可能
- 既存の成分情報を活用
- 症状マッチングの精度向上

**デメリット**:
- 成分-効能マッピング辞書の作成が必要
- 複数成分の組み合わせを考慮する必要がある

**実装工数**: 32-64時間

#### 改善案2: 成分による症状適合度スコアの補正（優先度: 中）

**内容**:
- 症状適合度スコア計算時に、成分情報も考慮
- 効能効果テキストに症状名が含まれていなくても、成分から推測できればスコアを補正

**実装**:
```python
def calculate_symptom_match_score_with_ingredients(candidate: Dict, nlu_result: Dict) -> float:
    """
    症状適合度スコアを計算（成分情報も考慮）
    """
    # 既存の症状適合度スコアを計算
    base_score = calculate_symptom_match_score(candidate, nlu_result)
    
    # 成分情報から効能を推測
    ingredient_boost = calculate_ingredient_efficacy_boost(candidate, nlu_result)
    
    # 効能効果テキストに症状名が含まれていない場合、成分情報を補正として使用
    if base_score < 0.3:  # 低スコアの場合
        # 成分情報による補正を適用（最大0.2まで）
        corrected_score = base_score + min(0.2, ingredient_boost * 0.5)
        return min(1.0, corrected_score)
    
    return base_score
```

**メリット**:
- 効能効果テキストに症状名が含まれていない場合でも、成分から推測可能
- 症状マッチングの精度向上

**デメリット**:
- 実装が複雑
- 成分-効能マッピング辞書が必要

**実装工数**: 16-32時間（改善案1の実装後）

## 3. 用法簡便性の計算の問題点

### 3.1 現在の実装

**実装**:
```python
def calculate_usage_convenience_score(candidate: Dict) -> float:
    usage_text = candidate.get('usage', '')
    if not usage_text:
        return 0.5  # デフォルトスコア
    
    # 1日の服用回数を抽出する正規表現
    patterns = [
        r'1日(\d+)回',
        r'(\d+)回服用',
        r'(\d+)回に分けて',
        r'(\d+)回服用'
    ]
    
    daily_frequency = None
    for pattern in patterns:
        match = re.search(pattern, usage_text)
        if match:
            daily_frequency = int(match.group(1))
            break
    
    # 服用回数によるスコア計算
    if daily_frequency == 1:
        return 1.0
    elif daily_frequency == 2:
        return 0.8
    # ...
```

### 3.2 問題点

#### 問題1: 改行を含むテキストの処理

**現状**:
- CSVの用法用量は改行（`\r\n`）を含む
- 正規表現は改行を考慮していない（`re.search`はデフォルトで改行を考慮するが、`\r\n`の処理が不十分な可能性）

**確認結果**:
- テストでは「1日3回服用」などのパターンは正しく抽出できている
- ただし、「1日1回を限度として」のような表現では「1日1回」が抽出されるが、実際には「必要時」なので通常の服用回数とは異なる

#### 問題2: 特殊な用法の処理

**例**:
- **禁煙補助薬（ニコレット）**: 「1日4～12個から始めて適宜増減」→ 通常の服用回数の概念が当てはまらない
- **下剤（ヒマシ油）**: 「1日1回を限度として、必要時」→ 通常の服用回数とは異なる

**現在の処理**:
- これらの特殊な用法では服用回数を抽出できず、デフォルトスコア（0.5）が返される
- これは適切な処理だが、より正確な判定が可能

#### 問題3: 年齢による用法の違い

**例**:
- 「大人（15歳以上）：1日3回」「8歳～15歳：1日2回」
- 現在の実装では最初にマッチした服用回数を使用

**問題**:
- ユーザーの年齢に応じた服用回数を考慮していない

### 3.3 改善提案

#### 改善案1: 正規表現パターンの改善（優先度: 高）

**内容**:
```python
def calculate_usage_convenience_score(candidate: Dict, user_info: Dict = None) -> float:
    usage_text = candidate.get('usage', '')
    if not usage_text:
        return 0.5
    
    # 改行を考慮した正規表現（複数行モード）
    patterns = [
        r'1日(\d+)回(?!を限度)',  # 「1日1回を限度」を除外
        r'(\d+)回服用(?!の)',     # 「服用の」を除外
        r'(\d+)回に分けて',
        r'通常[、,]?\s*1日(\d+)回',  # 「通常1日3回」などの表現
    ]
    
    # 年齢に応じた服用回数の抽出
    user_age = user_info.get('age') if user_info else None
    daily_frequency = None
    
    if user_age is not None:
        # 年齢に応じた服用回数を抽出
        if user_age >= 15:
            # 大人用の服用回数を抽出
            adult_patterns = [
                r'大人[（(]15歳以上[）)]\s*[：:]\s*.*?1日(\d+)回',
                r'成人[：:]\s*.*?1日(\d+)回',
            ]
            for pattern in adult_patterns:
                match = re.search(pattern, usage_text, re.MULTILINE)
                if match:
                    daily_frequency = int(match.group(1))
                    break
        elif user_age >= 8:
            # 小児用の服用回数を抽出
            child_patterns = [
                r'(\d+)歳[～〜]\d+歳[：:]\s*.*?1日(\d+)回',
            ]
            for pattern in child_patterns:
                match = re.search(pattern, usage_text, re.MULTILINE)
                if match:
                    daily_frequency = int(match.group(2))
                    break
    
    # 年齢に応じた抽出が失敗した場合、通常のパターンで抽出
    if daily_frequency is None:
        for pattern in patterns:
            match = re.search(pattern, usage_text, re.MULTILINE | re.DOTALL)
            if match:
                daily_frequency = int(match.group(1))
                break
    
    # 特殊な用法の判定
    if daily_frequency is None:
        # 禁煙補助薬、下剤などの特殊な用法
        if any(kw in usage_text for kw in ['適宜増減', '必要時', '限度として']):
            return 0.5  # デフォルトスコア
        return 0.5
    
    # 服用回数によるスコア計算
    if daily_frequency == 1:
        return 1.0
    elif daily_frequency == 2:
        return 0.8
    elif daily_frequency == 3:
        return 0.6
    elif daily_frequency == 4:
        return 0.4
    else:
        return 0.2
```

**実装工数**: 8-16時間

#### 改善案2: 用法簡便性スコアの重み付け見直し（優先度: 低）

**内容**:
- 現在の重み付け（0.05）は非常に低い
- 用法簡便性の重要性を再評価し、重み付けを調整

**実装工数**: 4-8時間

## 4. 総合的な改善提案

### 4.1 優先度の高い改善（フェーズ1）

1. **症状マッピング辞書の拡張**（16-32時間）
   - 効能効果テキストでよく使われる表現を症状辞書に追加
   - 症状マッチングの精度向上

2. **成分-効能マッピング辞書の作成**（32-64時間）
   - 成分情報から効能を推測
   - 症状マッチングの精度向上

3. **用法簡便性の計算改善**（8-16時間）
   - 正規表現パターンの改善
   - 年齢に応じた服用回数の抽出

**合計工数**: 56-112時間

**期待される効果**:
- 症状マッチングの精度向上: 約20-30%
- 最適な医薬品が推奨される確率の向上: 約15-25%

### 4.2 優先度の中程度の改善（フェーズ2）

1. **成分による症状適合度スコアの補正**（16-32時間）
   - 効能効果テキストに症状名が含まれていない場合でも、成分から推測

2. **意味的類似度の活用**（64-128時間）
   - 単語埋め込みやBERTを使用した意味的類似度計算

**合計工数**: 80-160時間

**期待される効果**:
- 症状マッチングの精度向上: 約30-50%
- 最適な医薬品が推奨される確率の向上: 約25-40%

## 5. 結論

### 5.1 現在のシステムの課題

1. **症状と効能効果テキストの照合**: 表現の不一致により最適な医薬品が推奨されないリスクがある
2. **成分情報の活用不足**: 副作用・相互作用リスク以外での活用が限定的
3. **用法簡便性の計算**: 特殊な用法や年齢による違いを考慮できていない

### 5.2 推奨される改善

**最優先（フェーズ1）**:
1. 症状マッピング辞書の拡張
2. 成分-効能マッピング辞書の作成
3. 用法簡便性の計算改善

**次優先（フェーズ2）**:
1. 成分による症状適合度スコアの補正
2. 意味的類似度の活用（長期的）

---

**作成日**: 2025年1月
**対象システム**: チャット型医薬品相談ツール
**分析者**: AI Assistant

