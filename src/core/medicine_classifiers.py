"""
医薬品タイプ判定

candidate_scoring から分離（SRP改善）。
特殊用途医薬品、小児専用、乗り物酔い薬、総合風邪薬の判定を行う。
"""

import logging
import os
from typing import Dict

from src.core.recommendation_constants import (
    PEDIATRIC_KEYWORDS,
    PEDIATRIC_USAGE_KEYWORDS,
    SPECIFIC_USE_EXCLUSION_KEYWORDS,
    COMPOUND_MEDICINE_INDICATORS,
)

logger = logging.getLogger(__name__)
_DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

MOTION_SICKNESS_SYMPTOM_KEYWORDS = [
    "乗り物酔い", "車酔い", "船酔い", "バス酔い", "酔い", "乗り物に酔う",
    "乗物酔い", "乗物に酔う", "車に乗ると気持ち悪い", "船に乗ると気持ち悪い"
]

MOTION_SICKNESS_MEDICINE_KEYWORDS = [
    "乗り物酔い", "乗物酔い", "乗り物酔い止め", "乗物酔い止め"
]


def is_specific_use_medicine(candidate: Dict) -> bool:
    """
    特殊用途医薬品かどうかを判定
    ホルモン剤、男性器塗布剤などの特殊用途医薬品を検出
    """
    product_name = str(candidate.get('product_name', '')).lower()
    efficacy = str(candidate.get('efficacy', '')).lower()
    usage = str(candidate.get('usage', '')).lower()
    ingredients = str(candidate.get('ingredients', '')).lower()
    combined_text = product_name + efficacy + usage + ingredients
    for category, keywords in SPECIFIC_USE_EXCLUSION_KEYWORDS.items():
        if any(kw in combined_text for kw in keywords):
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"特殊用途医薬品を検出: {candidate.get('product_name', '')} (カテゴリ: {category})")
            return True
    return False


def _is_pediatric_specific(candidate: Dict) -> bool:
    """
    小児専用製品かどうかを判定する。

    製品名、医薬品タイプ、用法、効能から小児専用製品を判定し、
    15歳以上または年齢不明のユーザー向け推奨から除外する際に使用。

    Args:
        candidate: 候補医薬品の情報

    Returns:
        小児専用製品の場合True
    """
    product_name = str(candidate.get('product_name', candidate.get('製品名', '')))
    efficacy = str(candidate.get('efficacy', candidate.get('効能', candidate.get('効能効果', ''))))
    usage = str(candidate.get('usage', candidate.get('用法', candidate.get('用法用量', ''))))
    efficacy_lower = efficacy.lower()
    usage_lower = usage.lower()

    # 製品名: 小児専用を示すキーワード（PEDIATRIC_KEYWORDS のうち明確なもの）
    pediatric_name_keywords = [
        "小児用", "小児専用", "こども用", "子ども用", "子供用",
        "キッズ", "ジュニア", "ベビー", "幼児用", "乳児用", "小中学生用"
    ]
    if any(kw in product_name for kw in pediatric_name_keywords):
        return True

    # 製品名: PEDIATRIC_KEYWORDS の組み合わせ（「小児」「こども」等 + 用法）
    name_has_pediatric = any(kw in product_name for kw in PEDIATRIC_KEYWORDS)
    usage_has_pediatric_form = any(kw in usage_lower for kw in PEDIATRIC_USAGE_KEYWORDS)
    if name_has_pediatric and usage_has_pediatric_form:
        return True

    # 効能: 「小児の」「小児用」が含まれる場合は小児専用とみなす
    if "小児の" in efficacy or "小児用" in efficacy_lower:
        return True

    return False


def _has_motion_sickness_symptom(nlu_result: Dict, user_text: str = "") -> bool:
    """
    NLU結果およびユーザー入力から乗り物酔い症状が検出されるか判定する。

    Args:
        nlu_result: NLU解析結果（symptoms を含む）
        user_text: ユーザーの入力テキスト

    Returns:
        乗り物酔い症状が検出された場合True
    """
    symptoms = nlu_result.get("symptoms", [])
    symptom_names = [s.get("name", "") for s in symptoms]
    for name in symptom_names:
        if any(kw in name for kw in MOTION_SICKNESS_SYMPTOM_KEYWORDS):
            return True
    return any(kw in (user_text or "") for kw in MOTION_SICKNESS_SYMPTOM_KEYWORDS)


def _is_motion_sickness_medicine(candidate: Dict) -> bool:
    """
    乗り物酔い薬かどうかを判定する。

    製品名、医薬品タイプ、効能から乗り物酔い薬を判定。

    Args:
        candidate: 候補医薬品の情報

    Returns:
        乗り物酔い薬の場合True
    """
    product_name = str(candidate.get('product_name', candidate.get('製品名', '')))
    efficacy = str(candidate.get('efficacy', candidate.get('効能', candidate.get('効能効果', ''))))
    medicine_type = str(candidate.get('medicine_type', candidate.get('医薬品の種類', '')))
    combined = product_name + efficacy + medicine_type
    return any(kw in combined for kw in MOTION_SICKNESS_MEDICINE_KEYWORDS)


def is_comprehensive_cold_medicine(candidate: Dict) -> bool:
    """
    総合風邪薬（総合感冒薬）かどうかを判定

    Args:
        candidate: 候補医薬品の情報

    Returns:
        総合風邪薬の場合True
    """
    product_name = str(candidate.get('product_name', '')).lower()
    efficacy = str(candidate.get('efficacy', '')).lower()
    medicine_type = str(candidate.get('medicine_type', '')).lower()

    # 外用薬は総合風邪薬として判定しない
    if medicine_type.startswith('外用薬'):
        return False

    # 製品名に外用薬を示すキーワードが含まれている場合は除外
    external_medicine_keywords = ['スプレー', 'トローチ', 'うがい', '含嗽', '噴射', '塗布', 'のど', '喉']
    if any(kw in product_name for kw in external_medicine_keywords):
        if any(kw in product_name for kw in ['スプレー', 'トローチ', 'うがい', '含嗽', '噴射', '塗布']):
            return False

    # 有名な総合風邪薬のブランド名をチェック
    famous_cold_medicine_brands = [
        "ルルアタック", "ルルエース", "ルルゴールド", "ルルカゼ", "ルル",
        "パブロンゴールド", "パブロンエース", "パブロンセレクト", "パブロンメディカル", "パブロン",
        "ベンザブロックs", "ベンザブロックl", "ベンザブロックip", "ベンザブロック",
        "プレコールエース", "プレコール持続性", "プレコール", "プレコー",
        "パイロンpl", "パイロンＰＬ", "パイロンα", "パイロンmk", "パイロンam", "パイロン",
        "カゼンエース", "カゼン", "カゼブロック"
    ]

    for brand in famous_cold_medicine_brands:
        brand_normalized = brand.lower().replace('ｐ', 'p').replace('ｌ', 'l').replace('ｓ', 's')
        product_name_normalized = product_name.lower().replace('ｐ', 'p').replace('ｌ', 'l').replace('ｓ', 's')

        if brand_normalized in product_name_normalized:
            if any(kw in product_name_normalized for kw in ['スプレー', 'トローチ', 'うがい', '含嗽', '噴射', '塗布', '点鼻']):
                continue
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"✅ 総合風邪薬を検出（ブランド名）: {candidate.get('product_name', '')} (ブランド: {brand})")
            return True

    # 総合感冒薬のパターンをチェック
    patterns = COMPOUND_MEDICINE_INDICATORS.get("風邪薬", {}).get("patterns", [])
    for pattern in patterns:
        if pattern.search(product_name) or pattern.search(efficacy):
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"✅ 総合風邪薬を検出（パターンマッチ）: {candidate.get('product_name', '')}")
            return True

    # 効能効果に複数の風邪症状が含まれているかチェック
    cold_symptoms = ["発熱", "熱", "解熱", "咳", "鎮咳", "去痰", "鼻水", "鼻炎", "のど", "咽頭", "喉", "頭痛", "悪寒", "くしゃみ", "鼻づまり", "感冒", "かぜ", "せき", "たん"]
    symptom_count = sum(1 for symptom in cold_symptoms if symptom in efficacy)

    if "風邪薬" in medicine_type:
        if symptom_count >= 2:
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"✅ 総合風邪薬を検出（複数症状）: {candidate.get('product_name', '')} (症状数: {symptom_count}, 効能: {efficacy[:100]}...)")
            return True
        if "感冒" in efficacy or "かぜ" in efficacy:
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"✅ 総合風邪薬を検出（感冒キーワード）: {candidate.get('product_name', '')}")
            return True

    return False
