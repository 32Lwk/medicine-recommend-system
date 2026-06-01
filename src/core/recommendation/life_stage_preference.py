"""
ライフステージ・嗜好・成分多様性の算出（SRP: 1ファイル＝1責務）

determine_life_stage, apply_user_preference_bonus, ensure_ingredient_diversity を提供。
rule_based_recommendation から import して利用する。
"""
import logging
import os
from typing import Dict, List, Optional, Tuple

from src.core.preference_merge import preference_field_confidence
from src.core.scoring_utils import _is_kampo_or_herbal_medicine

logger = logging.getLogger(__name__)
DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'


def determine_life_stage(user_info: Dict, nlu_result: Dict) -> str:
    """
    ライフステージ（年齢層）の分類

    Args:
        user_info: ユーザー情報
        nlu_result: NLU解析結果

    Returns:
        ライフステージ: "若年層", "中間層", "更年期前後", "不明"
    """
    age = user_info.get('age')

    # 年齢情報から判定
    if age is not None:
        if 10 <= age <= 29:
            return "若年層"
        elif 30 <= age <= 49:
            return "中間層"
        elif age >= 50:
            return "更年期前後"

    # 年齢情報が取得できない場合: 症状から推測
    symptoms = nlu_result.get("symptoms", [])
    symptom_names = [s.get("name", "") for s in symptoms]

    # ニキビがある場合は若年層と推測
    if "ニキビ" in symptom_names:
        return "若年層"

    # 更年期関連の症状がある場合は更年期前後と推測
    if any(kw in str(symptom_names) for kw in ['更年期', 'ほてり', 'のぼせ']):
        return "更年期前後"

    # デフォルト: 不明
    return "不明"


def apply_user_preference_bonus(candidate: Dict, user_preferences: Dict, nlu_result: Dict = None) -> float:
    """
    ユーザーの要望に基づくスコア調整

    Args:
        candidate: 候補医薬品情報
        user_preferences: ユーザー要望（extract_user_preferencesの結果）
        nlu_result: NLU解析結果（オプション）

    Returns:
        ボーナススコア（0.0-0.25）
    """
    if not user_preferences:
        return 0.0

    bonus = 0.0
    product_name = candidate.get('product_name', '')
    ingredients = str(candidate.get('ingredients', '')).lower()
    efficacy = str(candidate.get('efficacy', '')).lower()
    usage = str(candidate.get('usage', '')).lower()
    medicine_type = candidate.get('medicine_type', '')

    # 成分・バランス重視: 配合成分数、ビタミン類の配合、漢方のバランスに応じたボーナス（0.0-0.25）
    if user_preferences.get('ingredient_balance', False):
        confidence = preference_field_confidence(user_preferences, 'ingredient_balance')

        # ビタミン類の配合チェック
        vitamin_keywords = ['ビタミン', 'vitamin', 'ビタミンe', 'ビタミンb', 'トコフェロール', '酢酸トコフェロール']
        has_vitamin = any(vitamin in ingredients for vitamin in vitamin_keywords)

        # 複数の成分が含まれているかチェック（成分数のカウント）
        ingredient_count = len([ing for ing in ingredients.split(',') if ing.strip()]) if ingredients else 0

        # 総合的な医薬品（命の母、ラムールQなど）のチェック
        is_comprehensive = any(kw in product_name.lower() for kw in ['命の母', 'ラムール', 'ルナエール', 'ルナフェミン'])

        # 漢方のバランス（複数の生薬成分が含まれているか）
        kampo_ingredients = ['トウキ', '当帰', 'シャクヤク', '芍薬', 'ブクリョウ', '茯苓', 'サイコ', '柴胡', 'ケイヒ', '桂枝']
        kampo_count = sum(1 for kampo in kampo_ingredients if kampo.lower() in ingredients)

        ingredient_balance_score = 0.0
        if has_vitamin:
            ingredient_balance_score += 0.08
        if ingredient_count >= 5:
            ingredient_balance_score += 0.05
        if is_comprehensive:
            ingredient_balance_score += 0.10
        if kampo_count >= 3:
            ingredient_balance_score += 0.07

        # 確信度に応じて重み付け
        ingredient_balance_bonus = min(0.25, ingredient_balance_score) * confidence
        bonus += ingredient_balance_bonus

        if ingredient_balance_bonus > 0:
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"💊 成分・バランス重視ボーナス: {product_name} = +{ingredient_balance_bonus:.2f} (確信度: {confidence:.2f})")

    # 飲みやすさ重視: 錠剤タイプ、服用回数の少なさに応じたボーナス（0.0-0.20）
    if user_preferences.get('ease_of_taking', False):
        confidence = preference_field_confidence(user_preferences, 'ease_of_taking')

        # 錠剤タイプのチェック
        is_tablet = any(token in usage.lower() or token in product_name.lower() for token in ['錠', '錠剤', 'カプセル'])

        # 服用回数のチェック（1日1回、1日2回が最優先）
        usage_lower = usage.lower()
        dosage_frequency_score = 0.0
        if any(kw in usage_lower for kw in ['1日1回', '1回', '1日1度']):
            dosage_frequency_score = 0.10
        elif any(kw in usage_lower for kw in ['1日2回', '2回', '朝晩']):
            dosage_frequency_score = 0.08
        elif any(kw in usage_lower for kw in ['1日3回', '3回', '食後']):
            dosage_frequency_score = 0.05

        ease_of_taking_score = 0.0
        if is_tablet:
            ease_of_taking_score += 0.10
        ease_of_taking_score += dosage_frequency_score

        # 確信度に応じて重み付け
        ease_of_taking_bonus = min(0.20, ease_of_taking_score) * confidence
        bonus += ease_of_taking_bonus

        if ease_of_taking_bonus > 0:
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"💊 飲みやすさ重視ボーナス: {product_name} = +{ease_of_taking_bonus:.2f} (確信度: {confidence:.2f})")

    # 随伴症状対応: 効能効果の範囲の広さ、特定の症状の組み合わせに対応する製品にボーナス（0.0-0.20）
    if user_preferences.get('accompanying_symptoms', False):
        confidence = preference_field_confidence(user_preferences, 'accompanying_symptoms')

        # 効能効果の範囲の広さをチェック
        efficacy_keywords = ['月経不順', '生理不順', '生理痛', '月経痛', 'イライラ', 'ニキビ', '肌荒れ', '腰痛', '頭痛', 'めまい', '冷え症', 'むくみ']
        efficacy_coverage = sum(1 for kw in efficacy_keywords if kw in efficacy)

        # 複数の症状に対応しているかチェック
        if nlu_result:
            symptoms = nlu_result.get('symptoms', [])
            symptom_names = [s.get('name', '') for s in symptoms]
            symptom_coverage = sum(1 for symptom in symptom_names if symptom in efficacy)
        else:
            symptom_coverage = 0

        # 随伴症状対応スコア
        accompanying_symptoms_score = 0.0
        if efficacy_coverage >= 3:
            accompanying_symptoms_score += 0.10
        if symptom_coverage >= 2:
            accompanying_symptoms_score += 0.10

        # 確信度に応じて重み付け
        accompanying_symptoms_bonus = min(0.20, accompanying_symptoms_score) * confidence
        bonus += accompanying_symptoms_bonus

        if accompanying_symptoms_bonus > 0:
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"💊 随伴症状対応ボーナス: {product_name} = +{accompanying_symptoms_bonus:.2f} (確信度: {confidence:.2f})")

    # 漢方薬希望: 漢方薬・生薬製剤に +0.15〜0.20 のボーナス（confidence 重み）
    if user_preferences.get('prefers_kampo', False) and not user_preferences.get('prefers_not_kampo', False):
        if _is_kampo_or_herbal_medicine(candidate):
            kampo_conf = preference_field_confidence(user_preferences, 'prefers_kampo')
            kampo_preference_bonus = 0.18 * kampo_conf
            bonus += kampo_preference_bonus
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"💊 漢方薬希望ボーナス: {product_name} = +{kampo_preference_bonus:.2f}")

    return min(0.25, bonus)  # 最大0.25まで
