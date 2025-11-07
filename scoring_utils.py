"""
スコアリング関連のユーティリティ関数
効能特異性、副作用リスク、相互作用リスク、用法簡便性のスコア計算
"""

import pandas as pd
import re
import os
import unicodedata
from typing import Dict, List, Optional, Tuple

# CSVファイルのパス
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SIDE_EFFECTS_CSV = os.path.join(BASE_DIR, "medicine_side_effects.csv")
INTERACTIONS_CSV = os.path.join(BASE_DIR, "medicine_interactions.csv")

# 副作用・相互作用データのキャッシュ
_side_effects_df = None
_interactions_df = None


def normalize_text(text: str) -> str:
    """文字列をNFKC正規化・小文字化し、空白や記号を除去"""
    if not text or not isinstance(text, str):
        return ""

    normalized = unicodedata.normalize('NFKC', text)
    normalized = normalized.lower()
    # 空白と記号を除去（数字・アルファベット・日本語は残す）
    normalized = re.sub(r'[\s\u3000]+', '', normalized)
    normalized = re.sub(r"[^\wぁ-んァ-ン一-龥]+", '', normalized)
    return normalized


BROAD_EFFICACY_KEYWORDS = {
    "滋養強壮": {
        "require_any": {"倦怠感", "疲労感", "虚弱体質", "肉体疲労", "病後"},
        "penalty": 0.45
    },
    "栄養補給": {
        "require_any": {"栄養障害", "食欲不振", "病後", "産前産後"},
        "penalty": 0.35
    },
    "疲労回復": {
        "require_any": {"疲労感", "倦怠感", "肉体疲労"},
        "penalty": 0.3
    }
}

def load_side_effects_data():
    """副作用データを読み込み"""
    global _side_effects_df
    if _side_effects_df is None:
        try:
            _side_effects_df = pd.read_csv(SIDE_EFFECTS_CSV, encoding='utf-8')
        except FileNotFoundError:
            print(f"警告: {SIDE_EFFECTS_CSV} が見つかりません")
            _side_effects_df = pd.DataFrame()
    return _side_effects_df

def load_interactions_data():
    """相互作用データを読み込み"""
    global _interactions_df
    if _interactions_df is None:
        try:
            _interactions_df = pd.read_csv(INTERACTIONS_CSV, encoding='utf-8')
        except FileNotFoundError:
            print(f"警告: {INTERACTIONS_CSV} が見つかりません")
            _interactions_df = pd.DataFrame()
    return _interactions_df

def calculate_efficacy_specificity_score(candidate: Dict, nlu_result: Dict) -> float:
    """
    効能特異性スコアを計算
    医薬品の効能効果が症状に特化しているほど高スコア
    
    Args:
        candidate: 候補医薬品の情報
        nlu_result: NLU結果（症状リスト）
    
    Returns:
        効能特異性スコア (0.0-1.0)
    """
    efficacy_text = candidate.get('efficacy', '')
    if not efficacy_text:
        return 0.0
    
    symptoms = nlu_result.get("symptoms", [])
    if not symptoms:
        return 0.0
    
    # 症状名のリストを作成
    symptom_names = [s.get('name', '') for s in symptoms if s.get('name')]
    if not symptom_names:
        return 0.0

    normalized_efficacy = normalize_text(efficacy_text)
    if not normalized_efficacy:
        return 0.0

    normalized_symptoms = [normalize_text(name) for name in symptom_names]
    normalized_symptom_set = {name for name in normalized_symptoms if name}

    if not normalized_symptom_set:
        return 0.0

    match_count = sum(1 for name in normalized_symptom_set if name in normalized_efficacy)
    specificity_ratio = match_count / len(normalized_symptom_set)

    # 効能効果の長さによる調整（短いほど特化している）
    efficacy_length = len(normalized_efficacy)
    length_penalty = min(1.0, efficacy_length / 120)  # 正規化後のテキスト長を基準

    final_score = specificity_ratio * (1.0 - length_penalty * 0.25)

    # 広域効能（滋養強壮など）の場合は症状との整合性を確認
    penalty_factor = 1.0
    for keyword, rule in BROAD_EFFICACY_KEYWORDS.items():
        normalized_keyword = normalize_text(keyword)
        if normalized_keyword and normalized_keyword in normalized_efficacy:
            required_set = {normalize_text(req) for req in rule.get("require_any", set())}
            if required_set and not any(req in normalized_symptom_set for req in required_set):
                penalty = max(0.0, min(1.0, rule.get("penalty", 0.2)))
                penalty_factor *= (1.0 - penalty)

    final_score *= penalty_factor

    return min(1.0, max(0.0, final_score))

def calculate_side_effect_risk_score(candidate: Dict, user_info: Dict) -> float:
    """
    副作用リスクスコアを計算
    副作用リスクが高いほど負のスコア
    
    Args:
        candidate: 候補医薬品の情報
        user_info: ユーザー情報
    
    Returns:
        副作用リスクスコア (-1.0-0.0、負の値)
    """
    ingredients = candidate.get('ingredients', '')
    if not ingredients:
        return 0.0
    
    # 副作用データを読み込み
    side_effects_df = load_side_effects_data()
    if side_effects_df.empty:
        return 0.0
    
    # 成分リストを抽出（改行区切り）
    ingredient_list = [ing.strip() for ing in ingredients.split('\n') if ing.strip()]
    
    total_risk = 0.0
    risk_count = 0
    
    for ingredient in ingredient_list:
        # 副作用データから該当成分を検索
        matching_rows = side_effects_df[
            side_effects_df['成分名'].str.contains(ingredient, na=False, case=False)
        ]
        
        for _, row in matching_rows.iterrows():
            side_effect_level = row.get('副作用レベル', '')
            contraindications = row.get('禁忌条件', '')
            
            # 副作用レベルを数値に変換
            level_score = 0.0
            if side_effect_level == '高':
                level_score = -0.8
            elif side_effect_level == '中':
                level_score = -0.5
            elif side_effect_level == '低':
                level_score = -0.2
            
            # 禁忌条件のチェック
            if contraindications and user_info:
                # ユーザーの既往症や状態をチェック
                if any(condition in str(user_info) for condition in contraindications.split(',')):
                    level_score *= 2  # 禁忌条件に該当する場合はリスクを倍増
            
            # 妊娠中・授乳中の場合は追加減点
            if user_info.get('pregnant') or user_info.get('breastfeeding'):
                level_score *= 1.5
            
            total_risk += level_score
            risk_count += 1
    
    # 平均リスクスコアを計算
    if risk_count == 0:
        return 0.0
    
    avg_risk = total_risk / risk_count
    return max(-1.0, min(0.0, avg_risk))

def calculate_interaction_risk_score(candidate: Dict, user_info: Dict) -> float:
    """
    相互作用リスクスコアを計算
    相互作用リスクが高いほど負のスコア
    
    Args:
        candidate: 候補医薬品の情報
        user_info: ユーザー情報
    
    Returns:
        相互作用リスクスコア (-1.0-0.0、負の値)
    """
    ingredients = candidate.get('ingredients', '')
    current_medications = user_info.get('current_medications', [])
    
    if not ingredients or not current_medications:
        return 0.0
    
    # 相互作用データを読み込み
    interactions_df = load_interactions_data()
    if interactions_df.empty:
        return 0.0
    
    # 候補医薬品の成分リスト
    candidate_ingredients = [ing.strip() for ing in ingredients.split('\n') if ing.strip()]
    
    total_risk = 0.0
    interaction_count = 0
    
    # 現在服用中の薬との相互作用をチェック
    for medication in current_medications:
        for candidate_ingredient in candidate_ingredients:
            # 相互作用データから該当する組み合わせを検索
            matching_rows = interactions_df[
                (interactions_df['成分A'].str.contains(candidate_ingredient, na=False, case=False) |
                 interactions_df['成分B'].str.contains(candidate_ingredient, na=False, case=False)) &
                (interactions_df['成分A'].str.contains(medication, na=False, case=False) |
                 interactions_df['成分B'].str.contains(medication, na=False, case=False))
            ]
            
            for _, row in matching_rows.iterrows():
                interaction_level = row.get('相互作用レベル', '')
                
                # 相互作用レベルを数値に変換
                level_score = 0.0
                if interaction_level == '高':
                    level_score = -0.8
                elif interaction_level == '中':
                    level_score = -0.5
                elif interaction_level == '低':
                    level_score = -0.2
                
                total_risk += level_score
                interaction_count += 1
    
    # 平均相互作用リスクスコアを計算
    if interaction_count == 0:
        return 0.0
    
    avg_risk = total_risk / interaction_count
    return max(-1.0, min(0.0, avg_risk))

def calculate_usage_convenience_score(candidate: Dict) -> float:
    """
    用法簡便性スコアを計算
    1日の服用回数が少ないほど高スコア
    
    Args:
        candidate: 候補医薬品の情報
    
    Returns:
        用法簡便性スコア (0.0-1.0)
    """
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
    
    # 服用回数が見つからない場合はデフォルト
    if daily_frequency is None:
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

# 成分名の正規化辞書
INGREDIENT_NORMALIZATION = {
    "アスピリン": ["アセチルサリチル酸", "ASA", "アスピリン", "aspirin"],
    "イブプロフェン": ["イブ", "ブルフェン", "イブプロフェン", "ibuprofen"],
    "アセトアミノフェン": ["パラセタモール", "タイレノール", "アセトアミノフェン", "acetaminophen"],
    "ロキソプロフェン": ["ロキソニン", "ロキソプロフェン", "loxoprofen"],
    "ジクロフェナク": ["ボルタレン", "ジクロフェナク", "diclofenac"],
    "メフェナム酸": ["ポンタール", "メフェナム酸", "mefenamic acid"],
    "インドメタシン": ["インダシン", "インドメタシン", "indomethacin"],
    "ケトプロフェン": ["モーラス", "ケトプロフェン", "ketoprofen"],
    "ナプロキセン": ["ナイキサン", "ナプロキセン", "naproxen"],
    "セレコキシブ": ["セレコックス", "セレコキシブ", "celecoxib"]
}

def normalize_ingredient_name(ingredient: str) -> str:
    """
    成分名を正規化
    
    Args:
        ingredient: 元の成分名
    
    Returns:
        正規化された成分名
    """
    ingredient_lower = ingredient.lower().strip()
    
    # 正規化辞書から検索
    for normalized_name, variations in INGREDIENT_NORMALIZATION.items():
        for variation in variations:
            if variation.lower() in ingredient_lower:
                return normalized_name
    
    return ingredient.strip()

def check_allergy_contraindication(candidate: Dict, user_info: Dict) -> Tuple[bool, str]:
    """
    アレルギー成分照合を実行（強化版）
    
    Args:
        candidate: 候補医薬品の情報
        user_info: ユーザー情報
    
    Returns:
        (is_allergic: bool, allergy_ingredient: str)
    """
    ingredients = candidate.get('ingredients', '')
    allergies = user_info.get('allergies', [])
    
    if not ingredients or not allergies or allergies == ['なし']:
        return False, ""
    
    # 成分リストを抽出（改行とカンマの両方に対応）
    ingredient_list = []
    for separator in ['\n', ',', '、']:
        if separator in ingredients:
            ingredient_list.extend([ing.strip() for ing in ingredients.split(separator) if ing.strip()])
            break
    else:
        ingredient_list = [ingredients.strip()]
    
    # アレルギー成分との照合（正規化版）
    for allergy in allergies:
        allergy_normalized = normalize_ingredient_name(allergy)
        
        for ingredient in ingredient_list:
            ingredient_normalized = normalize_ingredient_name(ingredient)
            
            # 完全一致チェック
            if allergy_normalized == ingredient_normalized:
                return True, allergy
            
            # 部分一致チェック（より厳密）
            if (allergy_normalized in ingredient_normalized or 
                ingredient_normalized in allergy_normalized):
                return True, allergy
    
    return False, ""

def check_drug_interactions(candidate: Dict, user_info: Dict) -> Tuple[bool, List[str]]:
    """
    薬物相互作用チェックを実行（強化版）
    
    Args:
        candidate: 候補医薬品の情報
        user_info: ユーザー情報
    
    Returns:
        (has_interaction: bool, interaction_warnings: List[str])
    """
    ingredients = candidate.get('ingredients', '')
    current_medications = user_info.get('current_medications', [])
    
    if not ingredients or not current_medications:
        return False, []
    
    # 相互作用データを読み込み
    interactions_df = load_interactions_data()
    if interactions_df.empty:
        return False, []
    
    warnings = []
    candidate_ingredients = [ing.strip() for ing in ingredients.split('\n') if ing.strip()]
    
    # 現在服用中の薬との相互作用をチェック（正規化版）
    for medication in current_medications:
        medication_normalized = normalize_ingredient_name(medication)
        
        for candidate_ingredient in candidate_ingredients:
            candidate_normalized = normalize_ingredient_name(candidate_ingredient)
            
            matching_rows = interactions_df[
                (interactions_df['成分A'].str.contains(candidate_normalized, na=False, case=False) |
                 interactions_df['成分B'].str.contains(candidate_normalized, na=False, case=False)) &
                (interactions_df['成分A'].str.contains(medication_normalized, na=False, case=False) |
                 interactions_df['成分B'].str.contains(medication_normalized, na=False, case=False))
            ]
            
            for _, row in matching_rows.iterrows():
                interaction_level = row.get('相互作用レベル', '')
                description = row.get('説明', '')
                
                # リスクレベルに応じた警告メッセージ
                if interaction_level == '高':
                    warning_msg = f"🚨 禁忌レベル: {candidate_ingredient}と{medication}の併用は避けてください。{description}"
                elif interaction_level == '中':
                    warning_msg = f"⚠️ 注意レベル: {candidate_ingredient}と{medication}の併用時は医師に相談してください。{description}"
                else:
                    warning_msg = f"ℹ️ 情報レベル: {candidate_ingredient}と{medication}について。{description}"
                
                warnings.append(warning_msg)
    
    return len(warnings) > 0, warnings
