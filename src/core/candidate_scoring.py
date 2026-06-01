"""
候補医薬品の取得・フィルタ・スコアリング

rule_based_recommendation から分離（SRP改善）
"""

import logging
import math
import os
import re
from itertools import combinations
from typing import Dict, List, Optional, Tuple

import pandas as pd

from src.core.dictionary_loader import load_ingredient_dictionary, load_symptom_dictionary
from src.core.recommendation_constants import (
    PEDIATRIC_KEYWORDS,
    PEDIATRIC_USAGE_KEYWORDS,
    SPECIFIC_USE_EXCLUSION_KEYWORDS,
    SPECIFIC_USE_PATTERNS,
    RISK_INGREDIENTS_EXCLUDE,
    COMPOUND_MEDICINE_INDICATORS,
    ANTIDIARRHEAL_INGREDIENTS,
    ANTIDIARRHEAL_KEYWORDS,
    MAJOR_ANALGESIC_MEDICINES,
    THROAT_SPECIFIC_INGREDIENTS,
    BODY_PART_SPECIFIC_KEYWORDS,
    STOMACH_MUCOSAL_PROTECTANTS,
    STOMACH_MEDICINE_PRIORITY,
    CONSTIPATION_MEDICINE_PRIORITY,
    ANALGESIC_PRIORITY,
    WOUND_MEDICINE_PRIORITY,
    MENSTRUAL_MEDICINE_PRIORITY,
    SLEEP_DISORDER_PRIORITY,
    THROAT_KEYWORD_TOKENS,
    THROAT_LIQUID_TOKENS,
    THROAT_TOPICAL_PRIORITY,
    RISK_INGREDIENTS_OVERLAP,
    RED_FLAG_SYMPTOMS,
)
from src.core.scoring_utils import normalize_text, normalize_medicine_name_to_hankaku, is_word_match, TANN_FALSE_POSITIVE_BLACKLIST
from src.core.medicine_classifiers import (
    is_specific_use_medicine,
    _is_pediatric_specific,
    _has_motion_sickness_symptom,
    _is_motion_sickness_medicine,
    is_comprehensive_cold_medicine,
    MOTION_SICKNESS_SYMPTOM_KEYWORDS,
    MOTION_SICKNESS_MEDICINE_KEYWORDS,
)
from src.core.ingredient_utils import extract_main_ingredients, check_ingredient_overlap
from src.core.score_calculators import (
    ensure_score_difference,
    calculate_display_score,
    calculate_display_score_absolute,
)
from src.core.influenza_detector import detect_influenza_risk, _check_influenza_compatibility

logger = logging.getLogger(__name__)
_DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

# 花粉症文脈を解除する感染兆候（のど痛み単独は含めない）
_POLLEN_STRONG_INFECTION_SYMPTOMS = ("発熱", "咳", "悪寒", "頭痛", "高熱", "痰", "たん")
_POLLEN_STRONG_INFECTION_TEXT_KEYWORDS = (
    "発熱", "熱がある", "熱っぽい", "高熱", "微熱", "体温",
    "咳", "せき", "空咳", "痰", "たん",
    "悪寒", "寒気", "体が痛い", "筋肉痛", "関節痛",
    "風邪", "かぜ", "インフル", "コロナ",
)
_ALLERGIC_RHINITIS_EFFICACY_KEYWORDS = (
    "アレルギー性鼻炎",
    "花粉症",
    "副鼻腔炎",
)


def has_allergic_rhinitis_efficacy(efficacy: str) -> bool:
    """効能がアレルギー性鼻炎・花粉症向けか（総合感冒薬との切り分け用）"""
    if not efficacy:
        return False
    return any(kw in str(efficacy) for kw in _ALLERGIC_RHINITIS_EFFICACY_KEYWORDS)


def is_pollen_rhinitis_focus(user_text: str, symptom_names: List[str], medicine_type_hint: str = "") -> bool:
    """
    花粉症/アレルギー性鼻炎寄りの相談か（風邪薬を出したくない文脈）。

    ルール:
    - 明示キーワード（花粉症など）または medicine_type が鼻炎/アレルギー系
    - 発熱・咳・悪寒など感染兆候が強い場合は False
    - のどの痛みのみ（花粉症+鼻症状併存）は True のまま（GC-COLD-ALL-002 系）
    """
    text = (user_text or "").lower()
    hint = medicine_type_hint or ""

    if any(k in hint for k in ["抗アレルギー", "アレルギー", "鼻炎"]):
        allergy_typed = True
    else:
        allergy_typed = False

    hay_fever_keywords = [
        "花粉症",
        "花粉",
        "アレルギー性鼻炎",
        "季節性アレルギー性鼻炎",
        "常年性アレルギー性鼻炎",
        "pollinosis",
        "hay fever",
    ]
    is_hay_fever_text = any(kw in text for kw in hay_fever_keywords)
    is_hay_fever_symptom = any(
        any(kw in name for kw in ["花粉症", "アレルギー性鼻炎", "季節性アレルギー性鼻炎", "常年性アレルギー性鼻炎"])
        for name in (symptom_names or [])
    )

    hay_fever_context = allergy_typed or is_hay_fever_text or is_hay_fever_symptom
    if not hay_fever_context:
        return False

    has_strong_infection_sign = any(
        s in (symptom_names or []) for s in _POLLEN_STRONG_INFECTION_SYMPTOMS
    )
    has_strong_infection_text = any(kw in text for kw in _POLLEN_STRONG_INFECTION_TEXT_KEYWORDS)

    if has_strong_infection_sign or has_strong_infection_text:
        return False

    return True


def should_apply_cold_preference_rules(nlu_result: Dict) -> bool:
    """
    「風邪向けの並べ替え/総合感冒薬の強制配置」などを適用してよいか。
    """
    if not nlu_result:
        return False

    symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
    user_text = str(
        nlu_result.get("user_text")
        or nlu_result.get("original_user_text")
        or nlu_result.get("user_message")
        or ""
    )
    medicine_type_hint = str(nlu_result.get("medicine_type") or "")

    if is_pollen_rhinitis_focus(user_text, symptom_names_list, medicine_type_hint):
        return False

    infection_like_signs = ["発熱", "咳", "のどの痛み", "頭痛", "悪寒"]
    has_infection_like_sign = any(symptom in infection_like_signs for symptom in symptom_names_list)

    cold_symptoms = ["発熱", "咳", "鼻水", "のどの痛み", "頭痛", "悪寒", "くしゃみ", "鼻づまり", "痰", "たん"]
    cold_symptom_count = sum(1 for symptom in symptom_names_list if symptom in cold_symptoms)
    return cold_symptom_count >= 2 and has_infection_like_sign


def _is_symptom_matching_specific_use(efficacy: str, symptoms: List[Dict], pattern_name: str) -> bool:
    """
    症状が特殊用途パターンと一致するかチェック

    Args:
        efficacy: 効能効果テキスト
        symptoms: 検出された症状リスト
        pattern_name: パターン名（SPECIFIC_USE_PATTERNSのキー）

    Returns:
        一致する場合True
    """
    if pattern_name not in SPECIFIC_USE_PATTERNS:
        return False

    pattern_info = SPECIFIC_USE_PATTERNS[pattern_name]
    pattern = pattern_info.get("pattern")

    if not pattern or not pattern.search(efficacy):
        return False

    if pattern_info.get("strict", False):
        return True

    required_symptoms = pattern_info.get("required_symptoms", [])
    if required_symptoms:
        symptom_names = [s.get("name") for s in symptoms]
        if not all(req in symptom_names for req in required_symptoms):
            return False

    exclude_symptoms = pattern_info.get("exclude_symptoms", [])
    if exclude_symptoms:
        symptom_names = [s.get("name") for s in symptoms]
        if any(excl in symptom_names for excl in exclude_symptoms):
            return False

    return True


def _contains_risk_ingredient(ingredients: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    リスク成分が含まれているかチェック

    Args:
        ingredients: 成分テキスト

    Returns:
        (contains_risk, ingredient_name, risk_info): リスク成分の有無、成分名、リスク情報
    """
    if not ingredients or not isinstance(ingredients, str):
        return False, None, None

    ingredients_upper = ingredients.upper()

    for risk_name, risk_info in RISK_INGREDIENTS_EXCLUDE.items():
        aliases = risk_info.get("aliases", [])
        for alias in aliases:
            if alias.upper() in ingredients_upper:
                return True, risk_name, risk_info

    return False, None, None


def _extract_min_age_value(age_restriction) -> Optional[int]:
    """年齢制限から最小年齢を抽出"""
    if age_restriction is None:
        return None

    if isinstance(age_restriction, (int, float)):
        if isinstance(age_restriction, float) and math.isnan(age_restriction):
            return None
        try:
            return int(age_restriction)
        except (ValueError, OverflowError):
            return None

    if isinstance(age_restriction, str) and age_restriction.strip():
        match = re.search(r'(\d+)', age_restriction)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None

    return None


def _has_antidiarrheal_signal(candidate: Dict) -> bool:
    """
    止瀉薬系の成分やテキストシグナルが含まれているかを判定
    """
    ingredients = candidate.get('ingredients', '') or ''
    combined_text_parts = [
        candidate.get('product_name', ''),
        candidate.get('efficacy', ''),
        candidate.get('usage', ''),
        candidate.get('classification', ''),
        candidate.get('medicine_type', '')
    ]
    combined_text = ''.join(part for part in combined_text_parts if part)

    for token in ANTIDIARRHEAL_INGREDIENTS:
        if token and token in ingredients:
            return True
    for keyword in ANTIDIARRHEAL_KEYWORDS:
        if keyword and keyword in combined_text:
            return True

    return False


def _filter_antidiarrheal_without_diarrhea(
    candidates: List[Dict],
    nlu_result: Dict
) -> List[Dict]:
    """
    下痢症状が確認できない腹痛単独相談で止瀉薬系候補を除外
    """
    if not candidates:
        return candidates

    symptoms = nlu_result.get("symptoms", []) or []
    symptom_names = {s.get("name") for s in symptoms if s.get("name")}

    if not symptom_names:
        return candidates

    diarrhea_related = {"下痢", "軟便", "水様便"}
    if symptom_names & diarrhea_related:
        return candidates

    abdominal_only = symptom_names == {"腹痛"}
    if not abdominal_only:
        return candidates

    filtered: List[Dict] = []
    for candidate in candidates:
        if _has_antidiarrheal_signal(candidate):
            if logger.level <= logging.INFO:
                logger.info(
                    f"🚫 下痢症状が未確認の腹痛相談のため止瀉薬候補を除外: {candidate.get('product_name', '')}"
                )
            continue
        filtered.append(candidate)

    return filtered


def has_symptom_in_efficacy(candidate: Dict, symptom_names: List[str]) -> bool:
    """
    効能テキストに症状が含まれているかチェック
    単語境界を考慮したマッチングとブラックリストチェックを使用
    """
    try:
        efficacy = str(candidate.get('efficacy', ''))
        if not efficacy:
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"❌ has_symptom_in_efficacy: 効能が空 (症状: {symptom_names})")
            return False

        normalized_efficacy = normalize_text(efficacy)

        if "痰" in normalized_efficacy:
            normalized_efficacy = normalized_efficacy.replace("痰", "たん")

        if _DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"🔍 has_symptom_in_efficacy: 効能={efficacy[:50]}, 正規化後={normalized_efficacy[:50]}, 症状={symptom_names}")

        for symptom_name in symptom_names:
            normalized_symptom = normalize_text(symptom_name)

            hangover_symptom_mapping = {
                "二日酔い": "二日酔", "二日酔": "二日酔", "宿酔": "宿酔",
                "悪酔い": "悪酔", "悪酔": "悪酔",
            }
            if normalized_symptom in hangover_symptom_mapping:
                normalized_symptom = hangover_symptom_mapping[normalized_symptom]

            phlegm_symptom_mapping = {"痰": "たん", "たん": "たん"}
            if normalized_symptom in phlegm_symptom_mapping:
                normalized_symptom = phlegm_symptom_mapping[normalized_symptom]

            blacklist = TANN_FALSE_POSITIVE_BLACKLIST if normalized_symptom == "たん" else None

            if is_word_match(normalized_symptom, normalized_efficacy, blacklist=blacklist):
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"✅ has_symptom_in_efficacy: マッチ成功 (症状: {symptom_name} -> {normalized_symptom}, 効能: {efficacy[:50]}...)")
                return True

            if symptom_name in ["痰", "たん"]:
                for alt_symptom in ["痰", "たん"]:
                    if alt_symptom != symptom_name:
                        normalized_alt = normalize_text(alt_symptom)
                        blacklist_alt = TANN_FALSE_POSITIVE_BLACKLIST if normalized_alt == "たん" else None
                        if is_word_match(normalized_alt, normalized_efficacy, blacklist=blacklist_alt):
                            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                                logger.debug(f"✅ has_symptom_in_efficacy: マッチ成功 (症状: {symptom_name} -> {alt_symptom} -> {normalized_alt}, 効能: {efficacy[:50]}...)")
                            return True

        if _DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"❌ has_symptom_in_efficacy: マッチ失敗 (症状: {symptom_names}, 効能: {efficacy[:50]}...)")
        return False
    except Exception as e:
        logger.warning(f"has_symptom_in_efficacyエラー: {e}")
        if _DEBUG_MODE or logger.level <= logging.DEBUG:
            import traceback
            logger.debug(f"詳細: {traceback.format_exc()}")
        return False


def is_exact_product_match(product_name: str, target_names: List[str]) -> bool:
    """
    厳密な製品名マッチング関数
    """
    if not product_name or not target_names:
        return False
    product_name_lower = product_name.lower()
    for target_name in target_names:
        target_lower = target_name.lower()
        if product_name_lower == target_lower:
            return True
        pattern = r'\b' + re.escape(target_lower) + r'\b'
        if re.search(pattern, product_name_lower):
            return True
        if product_name_lower.startswith(target_lower) or product_name_lower.endswith(target_lower):
            if product_name_lower.startswith(target_lower):
                remaining = product_name_lower[len(target_lower):]
                if not remaining or remaining[0] in [' ', '・', '、', '，', '-', '_', '（', '(']:
                    return True
            elif product_name_lower.endswith(target_lower):
                remaining = product_name_lower[:-len(target_lower)]
                if not remaining or remaining[-1] in [' ', '・', '、', '，', '-', '_', '）', ')']:
                    return True
    return False


def _is_kakkonto_by_ingredients(candidate: Dict) -> bool:
    """成分ベースで葛根湯を判定"""
    ingredients = str(candidate.get('ingredients', '')).lower()
    if not ingredients:
        return False
    kakkonto_keywords = ["カッコン", "カンゾウ", "ケイヒ", "タイソウ", "ショウキョウ", "シャクヤク", "マオウ"]
    ingredients_normalized = normalize_text(ingredients)
    count = sum(1 for kw in kakkonto_keywords if normalize_text(kw.lower()) in ingredients_normalized)
    return count >= 5


def _is_kakkonto_medicine(candidate: Dict) -> bool:
    """
    葛根湯系医薬品かどうかを判定する。

    製品名に「葛根湯」が含まれるか、成分から葛根湯と判定される場合にTrue。

    Args:
        candidate: 候補医薬品の情報

    Returns:
        葛根湯系医薬品の場合True
    """
    product_name = str(candidate.get('product_name', candidate.get('製品名', '')))
    if "葛根湯" in product_name:
        return True
    return _is_kakkonto_by_ingredients(candidate)


def _candidate_has_throat_liquid_signature(candidate: Dict) -> bool:
    """
    のど向け液剤のシグネチャを持つ候補かどうかを判定する。

    製品名・効能・用法にのど関連キーワードと液剤形状の両方が含まれる場合にTrue。
    剤形多様性のため、液剤を1件確保する際に使用。

    Args:
        candidate: 候補医薬品の情報

    Returns:
        のど向け液剤の場合True
    """
    combined = str(candidate.get('product_name', '')) + str(candidate.get('efficacy', '')) + str(candidate.get('usage', ''))
    normalized = normalize_text(combined)
    has_throat = any(token in normalized for token in THROAT_KEYWORD_TOKENS)
    has_liquid = any(token in normalized for token in THROAT_LIQUID_TOKENS)
    return has_throat and has_liquid


def _expand_search_categories(symptom_names: List[str], medicine_types: set) -> set:
    """症状に基づいて検索対象カテゴリを拡張する"""
    expanded_types = set(medicine_types)
    allergy_symptoms = ["目のかゆみ"]
    allergy_indicators = ["くしゃみ", "鼻水", "鼻づまり"]
    has_eye_itch = any(s in symptom_names for s in allergy_symptoms)
    has_allergy_indicator = any(s in symptom_names for s in allergy_indicators)
    if has_eye_itch and has_allergy_indicator:
        if "鼻炎用薬" not in expanded_types:
            expanded_types.add("鼻炎用薬")
        logger.info("アレルギー症状（目のかゆみ + くしゃみ/鼻水）を検出。鼻炎用薬カテゴリを追加しました")
    musculoskeletal_symptoms = ["肩こり", "筋肉痛", "関節痛", "腰痛", "打撲", "捻挫"]
    if any(s in symptom_names for s in musculoskeletal_symptoms):
        topical_category = "外用薬（皮膚）"
        oral_category = "解熱鎮痛薬"
        expanded_types.add(topical_category)
        if "筋肉痛" in expanded_types and oral_category not in expanded_types:
            expanded_types.add(oral_category)
    return expanded_types


def filter_by_efficacy_symptom_match(candidates: List[Dict], nlu_result: Dict) -> List[Dict]:
    """
    効能効果と症状のマッチングに基づいて候補をフィルタリング
    """
    if not candidates:
        return candidates

    filtered = []
    symptom_names = [s.get("name", "") for s in nlu_result.get("symptoms", [])]

    for candidate in candidates:
        efficacy = str(candidate.get('efficacy', '')).lower()
        product_name = candidate.get('product_name', '')

        has_menstrual_pain_only = (
            ('月経痛' in efficacy or '生理痛' in efficacy) and
            not any(kw in efficacy for kw in ['月経不順', '生理不順', '月経異常', '生理異常', '血の道症', '血の道', '頭痛', '発熱', '咳', '鼻水', 'のどの痛み', '悪寒', 'くしゃみ'])
        )
        has_constipation_only = ('便秘' in efficacy and not any(kw in efficacy for kw in ['下痢', '胃痛', '腹痛', '吐き気']))
        has_throat_pain_only = (
            ('のどの痛み' in efficacy or '咽頭痛' in efficacy or '喉の痛み' in efficacy) and
            not any(kw in efficacy for kw in ['発熱', '熱', '解熱', '頭痛', '咳', '鼻水', '鼻づまり', 'くしゃみ', '悪寒', '寒気', '関節の痛み', '筋肉の痛み'])
        )
        has_diarrhea_only = ('下痢' in efficacy and not any(kw in efficacy for kw in ['便秘', '胃痛', '腹痛', '吐き気']))
        has_nutritional_efficacy = any(kw in efficacy for kw in ['栄養補給', '滋養強壮', '虚弱体質', '肉体疲労', '病中病後', '食欲不振', '栄養障害'])
        has_antipyretic_action = any(kw in efficacy for kw in ['解熱', '発熱', '熱']) and any(kw in efficacy for kw in ['鎮痛', '頭痛', '歯痛', '筋肉痛', '関節痛', '腰痛', '神経痛'])
        has_only_fever_consumption = '発熱性消耗性疾患' in efficacy and not has_antipyretic_action
        has_cold_symptom_in_efficacy = any(kw in efficacy for kw in ['頭痛', '咳', '鼻水', '鼻づまり', 'くしゃみ', '悪寒', '寒気', 'のど', '咽頭', '喉', '感冒', 'かぜ', 'せき', 'たん', '鎮痛', '歯痛', '筋肉痛', '関節痛', '腰痛', '神経痛', '咽頭痛', '打撲痛', '急性上気道炎'])
        is_nutritional_only = has_nutritional_efficacy and (has_only_fever_consumption or (not has_cold_symptom_in_efficacy and not has_antipyretic_action))

        if has_menstrual_pain_only:
            has_menstrual_symptom = any('月経痛' in name or '生理痛' in name or '月経不順' in name or '生理不順' in name for name in symptom_names)
            if not has_menstrual_symptom:
                logger.info(f"単一症状限定医薬品を除外: {product_name} (効能: 月経痛のみ)")
                continue
        if has_constipation_only:
            if not any('便秘' in name for name in symptom_names):
                logger.info(f"単一症状限定医薬品を除外: {product_name} (効能: 便秘のみ)")
                continue
        if has_diarrhea_only:
            if not any('下痢' in name for name in symptom_names):
                logger.info(f"単一症状限定医薬品を除外: {product_name} (効能: 下痢のみ)")
                continue
        if has_throat_pain_only:
            throat_symptoms = ['のどの痛み', '咽頭痛', '喉の痛み', 'のど', '喉']
            has_throat_symptom = any(any(ts in name for ts in throat_symptoms) for name in symptom_names)
            other_symptoms = ['発熱', '熱', '咳', '鼻水', '鼻づまり', 'くしゃみ', '悪寒', '寒気', '頭痛', '筋肉痛', '関節痛', '腰痛', '歯痛', '腹痛', '胃痛']
            has_other_symptoms = any(any(os in name for os in other_symptoms) for name in symptom_names)
            if has_other_symptoms or not has_throat_symptom:
                logger.info(f"効能が「のどの痛み」のみの医薬品を除外: {product_name}")
                continue

        is_fever_only = len(symptom_names) == 1 and any('発熱' in name or '熱' in name for name in symptom_names)
        if is_fever_only:
            if re.search(r'発熱して[、,]\s*[^の]*?(?:諸関節|関節|筋肉|神経痛|リウマチ|肩痛|腰痛|関節炎|筋肉痛)', efficacy):
                req = ['関節痛', '筋肉痛', '神経痛', 'リウマチ', '肩痛', '腰痛', '関節炎', '関節の痛み', '筋肉の痛み']
                if not any(any(c in name for c in req) for name in symptom_names):
                    logger.info(f"発熱のみ: 必須条件不足で除外: {product_name}")
                    continue
            if re.search(r'下腹部.*?(?:化膿性.*?腫瘍|凝結|圧痛|便秘)', efficacy) and '発熱' in efficacy:
                req = ['便秘', '下腹部', '化膿', '腫瘍', '圧痛']
                if not any(any(c in name for c in req) for name in symptom_names):
                    logger.info(f"発熱のみ: 必須条件不足で除外: {product_name}")
                    continue
            if ('発熱' in efficacy or '熱' in efficacy):
                if any(kw in efficacy for kw in ['諸関節が腫れて痛む', '各処の筋肉が腫れて痛む', '関節が腫れて痛む', '筋肉が腫れて痛む']):
                    req = ['関節痛', '筋肉痛', '神経痛', 'リウマチ', '肩痛', '腰痛', '関節炎', '関節の痛み', '筋肉の痛み']
                    if not any(any(c in name for c in req) for name in symptom_names):
                        logger.info(f"発熱のみ: 必須条件不足で除外: {product_name}")
                        continue
                if any(kw in efficacy for kw in ['下腹部に化膿性', '下腹部に凝結', '化膿性の腫瘍', '凝結を認め']):
                    req = ['便秘', '下腹部', '化膿', '腫瘍', '圧痛', '凝結']
                    if not any(any(c in name for c in req) for name in symptom_names):
                        logger.info(f"発熱のみ: 必須条件不足で除外: {product_name}")
                        continue
                if any(kw in efficacy for kw in ['ものの次の諸症', 'ものの次の', 'ものの諸症']):
                    req = ['関節痛', '筋肉痛', '神経痛', 'リウマチ', '肩痛', '腰痛', '関節炎', '便秘', '下腹部', '化膿', '腫瘍', '圧痛']
                    if not any(any(c in name for c in req) for name in symptom_names):
                        logger.info(f"発熱のみ: 縛り表現で除外: {product_name}")
                        continue

        if is_nutritional_only:
            cold_symptoms = ['発熱', '熱', '咳', '鼻水', '鼻づまり', 'くしゃみ', '悪寒', '寒気', '頭痛', 'のどの痛み']
            if any(any(cs in name for cs in cold_symptoms) for name in symptom_names):
                logger.info(f"栄養補給薬を除外: {product_name}")
                continue
        if has_nutritional_efficacy:
            has_fever_symptom = any('発熱' in name or '熱' in name for name in symptom_names)
            has_antipyretic_indication = '解熱' in efficacy or (any(kw in efficacy for kw in ['発熱', '熱']) and any(kw in efficacy for kw in ['鎮痛', '頭痛', '急性上気道炎', '感冒', 'かぜ']))
            if has_fever_symptom and (any(kw in product_name for kw in ['ハイゼリー', 'ヘパリーゼ', '栄養補給', '滋養強壮']) or not has_antipyretic_indication):
                logger.info(f"栄養補給薬を除外（発熱）: {product_name}")
                continue

        if 'ケイブク' in product_name and '顆粒' in product_name and ('打撲症' in efficacy or '打撲' in efficacy):
            if not any('打撲' in name or '打ち身' in name or 'ねんざ' in name or '捻挫' in name for name in symptom_names):
                logger.info(f"ケイブク（顆粒）を除外: {product_name}")
                continue
        if 'ビトラック' in product_name and 'Ｓ' in product_name:
            if 'ひざの痛み' in efficacy or '膝の痛み' in efficacy or 'むくみ' in efficacy:
                if not (any('膝' in name or 'ひざ' in name for name in symptom_names) or any('むくみ' in name or '浮腫' in name for name in symptom_names)):
                    logger.info(f"ビトラックＳを除外: {product_name}")
                    continue
        if '大柴胡湯' in product_name:
            has_hypertension_headache = bool(re.search(r'高血圧に伴う頭痛', efficacy))
            has_general_headache = any('頭痛' in name for name in symptom_names)
            has_hypertension = any('高血圧' in name or '血圧' in name for name in symptom_names)
            has_fever_symptom = any('発熱' in name or '熱' in name for name in symptom_names)
            if has_fever_symptom or (has_hypertension_headache and has_general_headache and not has_hypertension):
                logger.info(f"大柴胡湯を除外: {product_name}")
                continue
        if '雲仙散' in product_name:
            if any(kw in efficacy for kw in ['腰痛', '背痛', '五十肩', '筋肉痛', '神経痛', '関節炎', 'リウマチ']):
                has_muscle_joint_pain = any(any(kw in name for kw in ['腰痛', '背痛', '五十肩', '筋肉痛', '神経痛', '関節痛', 'リウマチ']) for name in symptom_names)
                has_headache_or_stomach = any('頭痛' in name for name in symptom_names) or any('腹痛' in name or '胃痛' in name for name in symptom_names)
                if not has_muscle_joint_pain and has_headache_or_stomach:
                    logger.info(f"雲仙散を除外: {product_name}")
                    continue
        if '太田漢方胃腸薬' in product_name and 'Ⅱ' in product_name:
            if any(kw in efficacy for kw in ['胃炎', '胃痛', '腹痛', '胃腸', '神経性', '慢性']):
                has_stomach_symptom = any(any(kw in name for kw in ['腹痛', '胃痛', '胃炎', '胃もたれ', '胸やけ']) for name in symptom_names)
                has_headache_constipation_diarrhea = any('頭痛' in name for name in symptom_names) or any('便秘' in name for name in symptom_names) or any('下痢' in name for name in symptom_names)
                if not has_stomach_symptom and has_headache_constipation_diarrhea:
                    logger.info(f"太田漢方胃腸薬Ⅱを除外: {product_name}")
                    continue

        if symptom_names:
            product_name_norm = normalize_medicine_name_to_hankaku(product_name)
            is_major_analgesic = any(
                normalize_medicine_name_to_hankaku(major_name) in product_name_norm
                for major_name in MAJOR_ANALGESIC_MEDICINES
            )
            hangover_boost = candidate.get('hangover_boost', 0.0)
            is_hangover_medicine = candidate.get('is_hangover', False)
            is_hangover_specialized = hangover_boost > 0 or is_hangover_medicine
            has_hangover_efficacy = any(kw in efficacy for kw in ['二日酔', '宿酔', '悪酔', '五苓散', '茵ちん五苓散'])
            if not is_major_analgesic and not is_hangover_specialized and not has_hangover_efficacy:
                has_symptom_match = has_symptom_in_efficacy(candidate, symptom_names)
                limited_efficacy_patterns = [
                    (r'打撲症[のみ、。]', ['打撲', '打ち身', 'ねんざ', '捻挫']),
                    (r'ひざの痛み[又はのみ、。]', ['膝', 'ひざ']),
                    (r'のどの痛み[のみ、。]', ['のど', '喉', '咽頭']),
                ]
                efficacy_keywords_count = sum(1 for kw in ['頭痛', '発熱', '解熱', '歯痛', '筋肉痛', '関節痛', '腰痛', '神経痛', '月経痛', '生理痛', '咽頭痛', '打撲痛', '急性上気道炎', '咳', '鼻水', '鼻づまり', '痰', 'たん'] if kw in efficacy)
                is_limited_efficacy = efficacy_keywords_count <= 1
                has_single_symptom_only_pattern = False
                for pattern, required_symptoms in limited_efficacy_patterns:
                    if re.search(pattern, efficacy):
                        if not any(any(req in sn for req in required_symptoms) for sn in symptom_names):
                            has_single_symptom_only_pattern = True
                            break
                if (is_limited_efficacy or has_single_symptom_only_pattern) and not has_symptom_match:
                    logger.info(f"効能効果に症状が含まれていない医薬品を除外: {product_name}")
                    continue

        filtered.append(candidate)
    return filtered


def get_candidate_medicines(
    nlu_result: Dict,
    medicine_df: pd.DataFrame,
    user_text: str = "",
    influenza_risk: bool = False,
    user_preferences: Optional[Dict] = None,
    preference_user_info: Optional[Dict] = None,
) -> List[Dict]:
    """
    症状に基づいて候補医薬品を取得（フィルタリング機能付き）
    """
    symptoms = nlu_result.get("symptoms", [])
    if not symptoms:
        return []

    symptom_names = [s.get("name") for s in symptoms]
    is_single_symptom = len(symptom_names) == 1

    medicine_types = set()
    for symptom in symptoms:
        symptom_name = symptom.get("name")
        if symptom_name in load_symptom_dictionary():
            types = load_symptom_dictionary()[symptom_name]["medicine_types"]
            medicine_types.update(types)

    allergy_symptoms = ["目のかゆみ", "かゆみ"]
    allergy_indicators = ["くしゃみ", "鼻水", "鼻づまり"]
    has_eye_itch = any(s in symptom_names for s in allergy_symptoms)
    has_allergy_indicator = any(s in symptom_names for s in allergy_indicators)

    user_text_lower = user_text.lower() if user_text else ""
    if not has_eye_itch:
        eye_itch_keywords = ["目のかゆみ", "目がかゆい", "目の痒み", "目かゆ", "目痒", "目もかゆ", "目も痒"]
        has_eye_itch = any(kw in user_text_lower for kw in eye_itch_keywords)

    if not has_allergy_indicator:
        allergy_indicator_keywords = ["くしゃみ", "鼻水", "鼻づまり", "鼻詰まり", "鼻が詰まる"]
        has_allergy_indicator = any(kw in user_text_lower for kw in allergy_indicator_keywords)

    if "かゆみ" in symptom_names and not has_eye_itch:
        if "目" in user_text_lower or "眼" in user_text_lower:
            has_eye_itch = True
            logger.info("「かゆみ」+「目」の組み合わせから目のかゆみを検出しました")
        elif any(kw in user_text_lower for kw in ["目もかゆ", "目も痒", "目がかゆ", "目が痒"]):
            has_eye_itch = True
            logger.info("「目もかゆい」などの表現から目のかゆみを検出しました")

    is_allergy_case = has_eye_itch and has_allergy_indicator

    if is_allergy_case:
        logger.info(f"アレルギー症状を検出: 目のかゆみ={has_eye_itch}, アレルギー指標={has_allergy_indicator}, ユーザー入力={user_text[:100]}")

    medicine_types = _expand_search_categories(symptom_names, medicine_types)

    if is_allergy_case:
        if "鼻炎用薬" not in medicine_types:
            medicine_types.add("鼻炎用薬")
            logger.info("アレルギー症状が検出されました（ユーザー入力テキストからも検出）。鼻炎用薬カテゴリを追加しました")
        if "風邪薬" in medicine_types and len(medicine_types) > 1:
            logger.info("アレルギー症状が検出されたため、風邪薬へのペナルティを適用します")

    medicine_type_hint = str(nlu_result.get("medicine_type") or "")
    focus_pollen = is_pollen_rhinitis_focus(user_text, symptom_names, medicine_type_hint)
    if focus_pollen:
        if "風邪薬" in medicine_types:
            medicine_types.discard("風邪薬")
            logger.info("花粉症/アレルギー性鼻炎寄りの相談のため、検索カテゴリから風邪薬を除外しました")
        if "鼻炎用薬" not in medicine_types:
            medicine_types.add("鼻炎用薬")
        if "抗アレルギー薬" not in medicine_types:
            medicine_types.add("抗アレルギー薬")
            logger.info("花粉症/アレルギー性鼻炎寄りの相談のため、抗アレルギー薬カテゴリを追加しました")
        if (has_eye_itch or "目のかゆみ" in symptom_names) and "目薬" not in medicine_types:
            medicine_types.add("目薬")
            logger.info("花粉症文脈で目のかゆみのため、目薬カテゴリを追加しました")
        medicine_types.discard("外用薬（皮膚）")
        medicine_types.discard("風邪薬")

    hangover_keywords = ["二日酔い", "二日酔", "宿酔", "悪酔い", "悪酔", "飲み過ぎ", "飲みすぎ", "酒", "アルコール"]
    is_hangover = any(kw in user_text_lower for kw in hangover_keywords)

    hangover_symptom_patterns = [
        frozenset({"頭痛", "むくみ", "だるさ"}),
        frozenset({"頭痛", "むくみ"}),
        frozenset({"頭痛", "だるさ"}),
        frozenset({"むくみ", "だるさ"}),
        frozenset({"頭痛", "吐き気"}),
        frozenset({"頭痛", "だるさ", "吐き気"}),
        frozenset({"吐き気", "むくみ"}),
        frozenset({"吐き気", "だるさ"}),
    ]

    symptom_mapping_for_hangover = {
        "疲労感": "だるさ",
        "倦怠感": "だるさ",
        "疲れ": "だるさ",
        "だるい": "だるさ",
    }
    normalized_symptom_names_for_hangover = [symptom_mapping_for_hangover.get(name, name) for name in symptom_names]
    normalized_symptom_set_for_hangover = frozenset(normalized_symptom_names_for_hangover)

    if not is_hangover:
        for pattern in hangover_symptom_patterns:
            if pattern.issubset(normalized_symptom_set_for_hangover):
                is_hangover = True
                logger.info(f"二日酔い症状パターンを検出: {pattern} ⊆ {normalized_symptom_set_for_hangover}")
                break

    if is_hangover:
        if "抗アレルギー薬" not in medicine_types:
            medicine_types.add("抗アレルギー薬")
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug("二日酔いが検出されました。抗アレルギー薬カテゴリを追加（五苓散対応）")

    logger.info(f"推定された医薬品の種類（拡張後）: {medicine_types}")
    if is_allergy_case:
        logger.info(f"アレルギー症状が検出されました（目のかゆみ: {has_eye_itch}, アレルギー指標: {has_allergy_indicator}）。鼻炎用薬を優先します")

    resolved_preferences = user_preferences
    if resolved_preferences is None and (user_text or preference_user_info):
        from src.core.user_detection import extract_user_preferences

        resolved_preferences = extract_user_preferences(
            user_text, nlu_result, preference_user_info or {}
        )

    if is_hangover:
        if _DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"二日酔いが検出されました（キーワードまたは症状パターン）。二日酔い向け医薬品を優先します")

    def _sanitize_text(value) -> str:
        if value is None:
            return ''
        text = str(value)
        if text.lower() == 'nan':
            return ''
        return text

    candidates: List[Dict] = []
    existing_keys: set = set()

    def append_candidate(row: pd.Series):
        product_name = _sanitize_text(row.get('製品名', ''))
        manufacturer = _sanitize_text(row.get('メーカー名', ''))
        key = (product_name, manufacturer)

        if not product_name and not manufacturer:
            return
        if key in existing_keys:
            return

        efficacy = row.get('効能効果', '')
        ingredients = row.get('成分', '')

        for pattern_name in SPECIFIC_USE_PATTERNS.keys():
            if _is_symptom_matching_specific_use(efficacy, symptoms, pattern_name):
                pattern_info = SPECIFIC_USE_PATTERNS[pattern_name]
                required_symptoms = pattern_info.get("required_symptoms", [])
                if required_symptoms and not all(req in symptom_names for req in required_symptoms):
                    if _DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(
                            f"特殊用途医薬品を除外: {product_name} (パターン: {pattern_name}, 症状不足)"
                        )
                    return

        if influenza_risk:
            contains_risk_aspirin, risk_name_aspirin, _ = _contains_risk_ingredient(ingredients)
            if contains_risk_aspirin and risk_name_aspirin == "アスピリン":
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"インフルエンザリスクのためアスピリン含有医薬品を除外: {product_name}")
                return

        contains_risk, risk_name, risk_info = _contains_risk_ingredient(ingredients)
        if contains_risk and is_single_symptom:
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"単一症状のためリスク成分含有医薬品を除外: {product_name} (成分: {risk_name})")
            return

        candidate_dict = {
            'product_name': product_name,
            'efficacy': efficacy,
            'usage': row.get('用法用量', ''),
            'ingredients': ingredients
        }
        if is_specific_use_medicine(candidate_dict):
            user_symptoms_str = " ".join(symptom_names).lower()
            specific_symptom_keywords = ["性器", "ホルモン", "勃起", "更年期", "記憶力", "男性器", "女性器", "ペニス", "陰茎"]
            is_specific_symptom = any(kw in user_symptoms_str for kw in specific_symptom_keywords)

            if not is_specific_symptom:
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"特殊用途医薬品を除外: {product_name} (症状: {symptom_names})")
                return

        age_restriction = row.get('年齢制限', '')
        if not age_restriction and hasattr(row, 'iloc') and len(row) > 6:
            age_restriction = row.iloc[6]
        if isinstance(age_restriction, (int, float)):
            if isinstance(age_restriction, float) and math.isnan(age_restriction):
                age_restriction = ''
            else:
                age_restriction = f"{int(age_restriction)}歳以上"
        elif age_restriction and isinstance(age_restriction, str):
            age_match = re.search(r'(\d+)歳', age_restriction)
            if age_match:
                age_restriction = f"{age_match.group(1)}歳以上"

        usage_full = row.get('用法用量', '') or ''
        usage_notes = ''
        if '注意' in usage_full or '＜' in usage_full:
            parts = usage_full.split('\n')
            note_parts = [p for p in parts if '注意' in p or '＜' in p or '用法' in p]
            usage_notes = '\n'.join(note_parts[:3])

        medicine_type = _sanitize_text(row.get('医薬品の種類', ''))
        if medicine_type == '外用薬（皮膚）':
            is_kampo = any(kw in product_name for kw in ['湯', '散', '丸', 'エキス', '顆粒', '細粒', '錠'])
            if efficacy and any(keyword in efficacy for keyword in ['のどの痛み', 'のどの', 'のど', '喉', '咽頭', '声がれ']) and not is_kampo:
                is_external_medicine = any(kw in product_name.lower() for kw in ['スプレー', 'トローチ', 'うがい', '含嗽', '噴射', '塗布'])
                if is_external_medicine:
                    medicine_type = '外用薬（のど）'

        if focus_pollen and '風邪薬' in medicine_type:
            logger.info(f"花粉症/アレルギー性鼻炎寄りの相談のため候補から除外: {product_name} (medicine_type={medicine_type})")
            return

        if focus_pollen and is_comprehensive_cold_medicine({
            'product_name': product_name,
            'efficacy': efficacy,
            'medicine_type': medicine_type,
        }) and not has_allergic_rhinitis_efficacy(efficacy):
            logger.info(
                f"花粉症文脈のため総合感冒薬型候補を除外: {product_name} (medicine_type={medicine_type})"
            )
            return

        candidate = {
            'medicine_id': len(candidates),
            'product_name': product_name,
            'manufacturer': manufacturer,
            'medicine_type': medicine_type,
            'classification': _sanitize_text(row.get('分類', '')),
            'efficacy': efficacy,
            'usage': row.get('用法用量', ''),
            'age_restriction': age_restriction,
            'ingredients': ingredients,
            'doping_prohibited': _sanitize_text(row.get('禁止物質あり', '')),
            'competition_category': _sanitize_text(row.get('競技会区分', '')),
            'conditions': _sanitize_text(row.get('条件', '')),
            'usage_notes': usage_notes if usage_notes else '用法用量を守ってご使用ください。',
            'base_score': 0.0,
            'is_allergy_case': is_allergy_case,
            'is_hangover': is_hangover
        }

        if is_allergy_case and '風邪薬' in medicine_type:
            candidate['allergy_penalty'] = -0.35
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"アレルギー症状検出: 風邪薬 {product_name} にペナルティ -0.35 を適用")

        if is_allergy_case and '鼻炎用薬' in medicine_type:
            candidate['allergy_boost'] = 0.40
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"アレルギー症状検出: 鼻炎用薬 {product_name} にブースト +0.40 を適用")

        if focus_pollen:
            from src.core.recommendation.pollen_rhinitis_scoring import (
                apply_pollen_candidate_adjustments,
            )

            apply_pollen_candidate_adjustments(
                candidate,
                focus_pollen=True,
                symptom_names=symptom_names,
                user_preferences=resolved_preferences,
                user_text=user_text,
            )

        if is_hangover:
            has_headache = any("頭痛" in str(s.get("name", "")) for s in symptoms)

            if "五苓散" in product_name or "五苓散" in efficacy:
                if has_headache:
                    candidate['hangover_boost'] = 0.55
                else:
                    candidate['hangover_boost'] = 0.50
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"二日酔い検出: 五苓散 {product_name} にブースト +{candidate['hangover_boost']:.2f} を適用")
            elif any(kw in efficacy.lower() for kw in ["二日酔", "宿酔", "悪酔"]):
                is_cysteine = "l-システイン" in ingredients.lower() or "システイン" in ingredients.lower()
                is_beauty_primary = any(kw in efficacy.lower()[:50] for kw in ["しみ", "そばかす", "色素沈着", "美白"])

                if is_cysteine and is_beauty_primary:
                    candidate['hangover_boost'] = 0.00
                    if _DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"二日酔い検出: L-システイン（美容主体） {product_name} にブースト +0.00 を適用（大幅減少）")
                else:
                    candidate['hangover_boost'] = 0.38
                    if _DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"二日酔い検出: 二日酔い効能明記 {product_name} にブースト +0.38 を適用")
            elif ("l-システイン" in ingredients.lower() or "システイン" in ingredients.lower()) and \
                 any(kw in efficacy.lower() for kw in ["倦怠", "疲労", "肝", "解毒"]):
                candidate['hangover_boost'] = 0.32
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"二日酔い検出: L-システイン含有（二日酔い関連効能） {product_name} にブースト +0.32 を適用")
            elif '胃腸薬' in medicine_type and any(kw in efficacy.lower() for kw in ["生薬", "健胃", "消化"]):
                if any(kw in efficacy.lower() for kw in ["二日酔のむかつき", "悪酔のむかつき"]):
                    candidate['hangover_boost'] = 0.40
                    if _DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"二日酔い検出: 二日酔い専用胃腸薬 {product_name} にブースト +0.40 を適用")
                else:
                    candidate['hangover_boost'] = 0.28
                    if _DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"二日酔い検出: 生薬配合胃腸薬 {product_name} にブースト +0.28 を適用")

        throat_specificity_level = "none"
        is_kakkonto_product = "葛根湯" in product_name
        is_kakkonto_by_ingredients_val = _is_kakkonto_by_ingredients(candidate)
        is_kakkonto_any = is_kakkonto_product or is_kakkonto_by_ingredients_val

        if _DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"葛根湯判定（識別段階）: {product_name}, is_kakkonto_product={is_kakkonto_product}, is_kakkonto_by_ingredients={is_kakkonto_by_ingredients_val}, is_kakkonto_any={is_kakkonto_any}")

        if '風邪薬' in medicine_type and not is_kakkonto_any:
            has_throat_efficacy = efficacy and any(keyword in efficacy for keyword in ['のどの痛み', 'のどの', 'のど', '喉', '咽頭'])
            if has_throat_efficacy:
                ingredients_lower = str(ingredients).lower() if ingredients else ""
                ingredients_normalized = normalize_text(ingredients_lower)
                has_throat_ingredient = False
                for ing in THROAT_SPECIFIC_INGREDIENTS:
                    ing_normalized = normalize_text(ing.lower())
                    if ing_normalized in ingredients_normalized:
                        has_throat_ingredient = True
                        break
                    ing_parts = ing_normalized.split()
                    if any(part in ingredients_normalized for part in ing_parts if len(part) > 3):
                        has_throat_ingredient = True
                        break
                if has_throat_ingredient:
                    throat_specificity_level = "component_and_efficacy"
                    if _DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"総合感冒薬（喉向き・成分あり）を識別: {product_name}, level={throat_specificity_level}")
                else:
                    throat_specificity_level = "efficacy_only"
                    if _DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"総合感冒薬（喉向き・効能のみ）を識別: {product_name}, level={throat_specificity_level} (成分なし)")
            else:
                product_name_lower = str(product_name).lower()
                has_throat_keyword = any(keyword in product_name_lower for keyword in ['のど', '喉', '咽頭', 'トローチ', 'スプレー', 'うがい'])
                if has_throat_keyword:
                    ingredients_normalized = normalize_text(str(ingredients).lower() if ingredients else "")
                    has_throat_ingredient = False
                    for ing in THROAT_SPECIFIC_INGREDIENTS:
                        ing_normalized = normalize_text(ing.lower())
                        if ing_normalized in ingredients_normalized:
                            has_throat_ingredient = True
                            break
                        ing_parts = ing_normalized.split()
                        if any(part in ingredients_normalized for part in ing_parts if len(part) > 3):
                            has_throat_ingredient = True
                            break
                    if has_throat_ingredient:
                        throat_specificity_level = "component_and_efficacy"
                        if _DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"総合感冒薬（喉向き・成分あり）を識別（製品名から）: {product_name}")
                    else:
                        throat_specificity_level = "efficacy_only"
                        if _DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"総合感冒薬（喉向き・効能のみ）を識別（製品名から）: {product_name}")
        candidate['throat_specificity_level'] = throat_specificity_level

        if contains_risk and risk_info:
            candidate['risk_ingredient'] = risk_name
            candidate['risk_warning'] = risk_info.get("warning", "")
            candidate['risk_penalty'] = risk_info.get("penalty_score", -0.3)

        candidates.append(candidate)
        existing_keys.add(key)

    has_headache_or_fever = any(
        any(symptom in symptom_name for symptom in ['頭痛', '発熱', '熱'])
        for symptom_name in symptom_names
    )

    if has_headache_or_fever and '解熱鎮痛薬' in medicine_types:
        def _matches_major_analgesic(name: str) -> bool:
            name_norm = normalize_medicine_name_to_hankaku(str(name))
            return any(
                normalize_medicine_name_to_hankaku(m) in name_norm
                for m in MAJOR_ANALGESIC_MEDICINES
            )
        major_mask = (
            medicine_df['製品名'].astype(str).apply(_matches_major_analgesic) &
            (medicine_df['医薬品の種類'].astype(str) == '解熱鎮痛薬')
        )
        major_rows = medicine_df[major_mask]
        for idx, row in major_rows.iterrows():
            efficacy = str(row.get('効能効果', ''))
            if any(kw in efficacy for kw in ['頭痛', '発熱', '解熱', '鎮痛']):
                append_candidate(row)
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"⭐ 主要解熱鎮痛薬を優先検索: {row.get('製品名', '')} (効能: {efficacy[:100]}...)")

        logger.info(f"頭痛・発熱が検出されました。主要解熱鎮痛薬を優先的に検索しました。")

    extraction_summary = {}
    for medicine_type in medicine_types:
        matched = medicine_df[medicine_df['医薬品の種類'] == medicine_type]
        matched_count = len(matched)
        for _, row in matched.iterrows():
            append_candidate(row)
        if matched_count > 0:
            extraction_summary[medicine_type] = matched_count

    if extraction_summary:
        summary_str = ", ".join([f"{k}: {v}件" for k, v in extraction_summary.items()])
        logger.info(f"候補抽出完了: {summary_str} (合計: {len(candidates)}件)")

    has_throat_pain = "のどの痛み" in symptom_names
    if has_throat_pain:
        if _DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"のどの痛み検出: 局所治療薬（外用薬（のど））を候補に追加します")
        throat_keyword_pattern = r"(?:のど|喉|咽頭)"
        product_keyword_pattern = r"(?:のど|喉|咽|トローチ|スプレー|うがい|キャンディ|飴)"
        throat_specific_keywords = ["ベンザブロック", "ルルアタック", "トラネキサム"]
        throat_specific_mask = medicine_df['製品名'].astype(str).str.contains(
            '|'.join(throat_specific_keywords), na=False, case=False, regex=True
        )

        throat_mask = (
            medicine_df['効能効果'].astype(str).str.contains(throat_keyword_pattern, na=False) |
            medicine_df['製品名'].astype(str).str.contains(product_keyword_pattern, na=False) |
            medicine_df['医薬品の種類'].astype(str).str.contains(throat_keyword_pattern, na=False) |
            throat_specific_mask
        )

        throat_candidates = medicine_df[throat_mask]
        throat_count = 0
        for _, row in throat_candidates.iterrows():
            product_name = _sanitize_text(row.get('製品名', ''))
            manufacturer = _sanitize_text(row.get('メーカー名', ''))
            key = (product_name, manufacturer)
            if key not in existing_keys:
                append_candidate(row)
                throat_count += 1

        if throat_count > 0:
            logger.info(f"のどの痛み関連候補追加: {throat_count}件")
        if throat_specific_mask.any() and (_DEBUG_MODE or logger.level <= logging.DEBUG):
            logger.debug(f"喉の痛み特化医薬品を検出: {throat_specific_mask.sum()}件")

    has_musculoskeletal_symptom = any(s in symptom_names for s in ["肩こり", "筋肉痛", "関節痛", "腰痛"])
    if has_musculoskeletal_symptom:
        vip_ingredients = [
            "フェルビナク", "フェルビナクナトリウム", "フェルビナクナトリウム水和物",
            "インドメタシン", "インダシン", "インドメタシン水和物",
            "ジクロフェナク", "ジクロフェナクナトリウム", "ボルタレン", "ジクロフェナクナトリウム水和物"
        ]

        vip_mask = (
            medicine_df['医薬品の種類'].astype(str).str.contains('外用', na=False) &
            medicine_df['成分'].astype(str).str.contains('|'.join(vip_ingredients), na=False, case=False, regex=True)
        )

        vip_candidates = medicine_df[vip_mask]
        vip_count = 0
        for _, row in vip_candidates.iterrows():
            product_name = _sanitize_text(row.get('製品名', ''))
            manufacturer = _sanitize_text(row.get('メーカー名', ''))
            key = (product_name, manufacturer)

            if key not in existing_keys:
                append_candidate(row)
                vip_count += 1

        if vip_count > 0:
            logger.info(f"VIP成分枠: 第2世代鎮痛成分含有の外用薬を{vip_count}件追加しました")

        optimal_product_keywords = ["フェイタス", "バンテリン", "サロンパス"]
        optimal_mask = (
            medicine_df['医薬品の種類'].astype(str).str.contains('外用', na=False) &
            medicine_df['製品名'].astype(str).str.contains('|'.join(optimal_product_keywords), na=False, case=False, regex=True)
        )

        optimal_candidates = medicine_df[optimal_mask]
        optimal_count = 0
        for _, row in optimal_candidates.iterrows():
            product_name = _sanitize_text(row.get('製品名', ''))
            manufacturer = _sanitize_text(row.get('メーカー名', ''))
            key = (product_name, manufacturer)

            if key not in existing_keys:
                append_candidate(row)
                optimal_count += 1

        if optimal_count > 0:
            logger.info(f"VIP製品名枠: 最適解の外用薬を{optimal_count}件追加しました（フェイタス、バンテリン、サロンパス）")

    if is_hangover:
        hangover_efficacy_keywords = ["二日酔", "宿酔", "悪酔", "五苓散", "茵ちん五苓散"]
        hangover_mask = medicine_df['効能効果'].astype(str).str.contains(
            '|'.join(hangover_efficacy_keywords), na=False, case=False, regex=True
        )

        hangover_candidates = medicine_df[hangover_mask]
        hangover_count = 0
        for _, row in hangover_candidates.iterrows():
            product_name = _sanitize_text(row.get('製品名', ''))
            manufacturer = _sanitize_text(row.get('メーカー名', ''))
            key = (product_name, manufacturer)

            if key not in existing_keys:
                append_candidate(row)
                hangover_count += 1

        if hangover_count > 0:
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"二日酔い特化医薬品を効能効果から{hangover_count}件追加しました")

        cysteine_keywords = ["l-システイン", "lシステイン", "システイン"]
        cysteine_mask = medicine_df['成分'].astype(str).str.contains(
            '|'.join(cysteine_keywords), na=False, case=False, regex=True
        )

        cysteine_candidates = medicine_df[cysteine_mask]
        cysteine_count = 0
        for _, row in cysteine_candidates.iterrows():
            product_name = _sanitize_text(row.get('製品名', ''))
            manufacturer = _sanitize_text(row.get('メーカー名', ''))
            key = (product_name, manufacturer)

            efficacy = str(row.get('効能効果', '')).lower()
            is_hangover_related = any(kw in efficacy for kw in ["二日酔", "宿酔", "悪酔", "肝", "解毒", "倦怠", "疲労"])

            if key not in existing_keys and is_hangover_related:
                append_candidate(row)
                cysteine_count += 1

        if cysteine_count > 0:
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"L-システイン含有医薬品（二日酔い関連）を{cysteine_count}件追加しました")

        for candidate in candidates:
            if not candidate.get('hangover_boost'):
                product_name = candidate.get('product_name', '')
                efficacy = candidate.get('efficacy', '')
                ingredients = str(candidate.get('ingredients', '')).lower()
                medicine_type = candidate.get('medicine_type', '')

                if "五苓散" in product_name or "五苓散" in efficacy:
                    candidate['hangover_boost'] = 0.50
                elif any(kw in efficacy.lower() for kw in ["二日酔", "宿酔", "悪酔"]):
                    is_cysteine = "l-システイン" in ingredients or "システイン" in ingredients
                    is_beauty_primary = any(kw in efficacy.lower()[:50] for kw in ["しみ", "そばかす", "色素沈着", "美白"])

                    if is_cysteine and is_beauty_primary:
                        candidate['hangover_boost'] = 0.10
                    else:
                        candidate['hangover_boost'] = 0.38
                elif ("l-システイン" in ingredients or "システイン" in ingredients) and \
                     any(kw in efficacy.lower() for kw in ["倦怠", "疲労", "肝", "解毒"]):
                    candidate['hangover_boost'] = 0.38
                elif '胃腸薬' in medicine_type and any(kw in efficacy.lower() for kw in ["生薬", "健胃", "消化"]):
                    if any(kw in efficacy.lower() for kw in ["二日酔のむかつき", "悪酔のむかつき"]):
                        candidate['hangover_boost'] = 0.40
                    else:
                        candidate['hangover_boost'] = 0.28

    if nlu_result:
        symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        normalized_symptom_names_list = []
        symptom_mapping = {
            "生理不順": "月経不順",
            "生理異常": "月経不順",
        }
        for name in symptom_names_list:
            normalized_name = symptom_mapping.get(name, name)
            normalized_symptom_names_list.append(normalized_name)

        symptom_set = frozenset(normalized_symptom_names_list)
        is_menstrual_irritability_pattern = symptom_set == frozenset({"月経不順", "イライラ"}) or symptom_set.issubset(frozenset({"月経不順", "イライラ"}))

        if is_menstrual_irritability_pattern:
            priority_medicine_names = ["ラムールQ", "ラムールＱ", "ラムールq", "ラムールｑ", "加味逍遙散", "カミショウヨウサン", "命の母ホワイト", "命の母 ホワイト", "ルナエール", "ルナフェミン", "桂枝茯苓丸", "ケイシブクリョウガン"]
            priority_medicine_count = 0

            for priority_name in priority_medicine_names:
                priority_mask = medicine_df['製品名'].astype(str).str.contains(
                    re.escape(priority_name), na=False, case=False, regex=True
                )
                priority_candidates = medicine_df[priority_mask]

                for _, row in priority_candidates.iterrows():
                    product_name = _sanitize_text(row.get('製品名', ''))
                    manufacturer = _sanitize_text(row.get('メーカー名', ''))
                    key = (product_name, manufacturer)

                    if key in existing_keys:
                        continue

                    if is_exact_product_match(product_name, [priority_name]) or priority_name in product_name:
                        append_candidate(row)
                        priority_medicine_count += 1
                        if _DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"⭐ 期待される医薬品を候補に追加: {product_name} (検索名: {priority_name})")
                        break

            if priority_medicine_count > 0:
                logger.info(f"⭐ 期待される医薬品を{priority_medicine_count}件追加しました")
            else:
                logger.warning(f"⚠️ 期待される医薬品が見つかりませんでした（検索名: {priority_medicine_names}）")

    medicine_type_counts = {}
    for candidate in candidates:
        medicine_type = candidate.get('medicine_type', '不明')
        medicine_type_counts[medicine_type] = medicine_type_counts.get(medicine_type, 0) + 1

    logger.info(f"候補医薬品数: {len(candidates)} (フィルタリング後)")
    logger.info(f"候補医薬品の種類別内訳: {medicine_type_counts}")
    return candidates


def _detect_body_part_specificity(candidate: Dict) -> Optional[str]:
    """
    候補医薬品の部位特異性を検出
    """
    product_name = str(candidate.get('product_name', '')).lower()
    efficacy = str(candidate.get('efficacy', '')).lower()
    usage = str(candidate.get('usage', '')).lower()
    for body_part, keywords_dict in BODY_PART_SPECIFIC_KEYWORDS.items():
        if any(kw.lower() in product_name for kw in keywords_dict.get("product_name_keywords", [])):
            return body_part
        if any(kw.lower() in efficacy for kw in keywords_dict.get("efficacy_keywords", [])):
            return body_part
        if any(kw.lower() in usage for kw in keywords_dict.get("usage_keywords", [])):
            return body_part
    return None
def calculate_symptom_match_score(candidate: Dict, nlu_result: Dict) -> float:
    """
    症状適合度スコアを計算
    """
    import re
    
    def is_word_match(token: str, text: str) -> bool:
        """
        単語境界を考慮したマッチング
        日本語の単語境界を考慮（症状名が独立した単語として存在するかチェック）
        """
        if not token or not text:
            return False
        
        # 症状名が効能テキスト内に存在するかチェック
        if token not in text:
            return False
        
        # 日本語文字の判定関数（助詞・記号を除く）
        def is_japanese_word_char(c: str) -> bool:
            if not c:
                return False
            # 漢字、カタカナのみを単語文字とみなす（ひらがな助詞は境界）
            return ('\u30A0' <= c <= '\u30FF' or  # カタカナ
                    '\u4E00' <= c <= '\u9FFF')    # 漢字
        
        # 症状名の出現位置をすべて取得
        start_positions = []
        start = 0
        while True:
            pos = text.find(token, start)
            if pos == -1:
                break
            start_positions.append(pos)
            start = pos + 1
        
        # 各出現位置で、前後が日本語文字でないことを確認
        for pos in start_positions:
            # 前の文字（存在する場合）
            prev_char = text[pos - 1] if pos > 0 else ''
            # 後の文字（存在する場合）
            next_pos = pos + len(token)
            next_char = text[next_pos] if next_pos < len(text) else ''
            
            # 前後が日本語単語文字でないことを確認
            # （前が文の始まりまたは非単語文字）AND（後が文の終わりまたは非単語文字）
            # ひらがな助詞（の、が、を、に、は、など）や記号（、。）は境界とみなす
            is_valid_start = (pos == 0) or not is_japanese_word_char(prev_char)
            is_valid_end = (next_pos >= len(text)) or not is_japanese_word_char(next_char)
            
            if is_valid_start and is_valid_end:
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"✅ 単語境界マッチ: '{token}' found at position {pos} in '{text}'")
                return True
            else:
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"❌ 単語境界除外: '{token}' at position {pos} (前:'{prev_char}', 後:'{next_char}')")
        
        return False
    
    症状スコア = 0.0
    症状数 = len(nlu_result.get("symptoms", []))
    
    if 症状数 == 0:
        return 0.0
    
    # 効能テキストを取得
    efficacy_text_raw = candidate.get('efficacy', '')
    if not efficacy_text_raw:
        return 0.0
    
    # 二日酔い特別処理：効能効果に「二日酔」「宿酔」「悪酔」が含まれている場合
    efficacy_lower = efficacy_text_raw.lower()
    hangover_keywords_in_efficacy = ["二日酔", "宿酔", "悪酔"]
    has_hangover_efficacy = any(kw in efficacy_lower for kw in hangover_keywords_in_efficacy)
    
    # NLU結果に「二日酔い」症状が含まれているか確認
    symptoms = nlu_result.get("symptoms", [])
    symptom_names = [s.get("name") for s in symptoms]
    has_hangover_symptom = any("二日酔" in str(name) for name in symptom_names)
    
    # 二日酔い症状と二日酔い効能が一致する場合、高スコアを付与
    if has_hangover_symptom and has_hangover_efficacy:
        if _DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"✅ 二日酔い直接マッチ: {candidate.get('product_name', '')} (効能: {efficacy_text_raw[:100]}...)")
        return 0.95  # 二日酔い特化医薬品には高スコア
    
    # 効能テキストを句読点で分割してから正規化
    # 「激しい咳、咽頭痛の緩解」→ 「激しい咳」「咽頭痛の緩解」
    import re
    efficacy_parts_raw = re.split(r'[、。，．,.]', efficacy_text_raw)
    efficacy_parts = [normalize_text(p) for p in efficacy_parts_raw if p.strip()]
    efficacy_parts = [p for p in efficacy_parts if p]
    
    for symptom in nlu_result.get("symptoms", []):
        symptom_name = symptom.get("name")
        if not symptom_name:
            continue
        normalized_symptom = normalize_text(symptom_name)
        if not normalized_symptom:
            continue
        synonym_set = {normalized_symptom}
        dictionary_entry = load_symptom_dictionary().get(symptom_name, {})
        for synonym in dictionary_entry.get("synonyms", []):
            normalized_synonym = normalize_text(synonym)
            if normalized_synonym:
                synonym_set.add(normalized_synonym)
        
        # 血の道症・月経異常の双方向マッピング（効能効果テキスト内の専門用語も認識）
        if symptom_name == "月経不順" or "月経不順" in dictionary_entry.get("canonical_name", ""):
            # 効能効果テキスト内の「血の道症」「月経異常」も「月経不順」として認識
            synonym_set.add(normalize_text("血の道症"))
            synonym_set.add(normalize_text("血の道"))
            synonym_set.add(normalize_text("月経異常"))
            synonym_set.add(normalize_text("生理異常"))
        
        # イライラ症状への対応強化（効能効果欄に「ヒステリー」「情緒不安定」「更年期神経症」などが含まれる場合）
        if symptom_name == "イライラ" or "イライラ" in dictionary_entry.get("canonical_name", ""):
            # 効能効果テキスト内の「ヒステリー」「情緒不安定」「更年期神経症」も「イライラ」として認識
            synonym_set.add(normalize_text("ヒステリー"))
            synonym_set.add(normalize_text("情緒不安定"))
            synonym_set.add(normalize_text("更年期神経症"))
            synonym_set.add(normalize_text("神経症状"))
        
        # 各効能パート内でマッチングを試行
        matched = False
        for part in efficacy_parts:
            # 効能効果テキスト内の「血の道症」「月経異常」もチェック（大文字小文字を区別しない）
            part_lower = part.lower()
            if symptom_name == "月経不順" or "月経不順" in dictionary_entry.get("canonical_name", ""):
                if "血の道症" in part_lower or "血の道" in part_lower or "月経異常" in part_lower or "生理異常" in part_lower:
                    matched = True
                    break
            # 効能効果テキスト内の「ヒステリー」「情緒不安定」などもチェック（大文字小文字を区別しない）
            if symptom_name == "イライラ" or "イライラ" in dictionary_entry.get("canonical_name", ""):
                if "ヒステリー" in part_lower or "情緒不安定" in part_lower or "更年期神経症" in part_lower or "神経症状" in part_lower:
                    matched = True
                    break
            if any(is_word_match(token, part) for token in synonym_set):
                matched = True
                break
        
        if matched:
            weight = dictionary_entry.get("weight", 0.5)
            症状スコア += weight
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"✅ 症状マッチ: {symptom_name} が効能に含まれています (効能: {efficacy_text_raw})")
        elif _DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"❌ 症状マッチなし: {symptom_name} は効能に含まれていません (効能: {efficacy_text_raw})")
    
    # 症状が効能に含まれていない場合の処理
    if 症状スコア == 0.0:
        # 解熱鎮痛薬の場合、発熱やのどの痛みなどの症状に対して一定のスコアを付与
        # ただし、効能効果に症状が含まれている場合のみ
        medicine_type = candidate.get("medicine_type", "")
        if "解熱鎮痛薬" in medicine_type:
            # 解熱鎮痛薬は発熱、頭痛、のどの痛みなどに効果がある
            fever_symptoms = ["発熱", "熱", "高熱", "微熱"]
            throat_symptoms = ["のどの痛み", "咽頭痛", "喉の痛み", "のど痛"]
            headache_symptoms = ["頭痛"]
            
            symptom_names = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
            matched_symptom_count = 0
            
            # 月経不順・生理痛関連症状の定義
            menstrual_symptoms = ["月経不順", "生理不順", "生理痛", "月経痛", "月経異常", "生理異常", "血の道症"]
            menstrual_keywords = ["生理", "月経", "周期", "遅れ", "来ない", "来ていない", "乱れ", "不順", "異常"]
            
            # 効能効果に症状が含まれているかチェック
            efficacy_lower = str(candidate.get('efficacy', '')).lower()
            has_symptom_in_efficacy = False
            
            for symptom_name in symptom_names:
                normalized_symptom = normalize_text(symptom_name)
                # 効能効果に症状名または同義語が含まれているかチェック
                symptom_dict_entry = load_symptom_dictionary().get(symptom_name, {})
                synonyms = [normalized_symptom] + [normalize_text(s) for s in symptom_dict_entry.get("synonyms", [])]
                
                # 発熱関連症状のチェック（先に実行）
                if any(fever in normalized_symptom or fever in symptom_name for fever in fever_symptoms):
                    # 効能効果に「発熱」「熱」「解熱」などが含まれているか
                    if any(kw in efficacy_lower for kw in ['発熱', '熱', '解熱', '高熱', '微熱']):
                        has_symptom_in_efficacy = True
                        matched_symptom_count += 1
                        continue  # 発熱関連症状の場合は次の症状へ
                
                # 効能効果に症状が含まれているか確認（発熱関連症状以外）
                if any(synonym in efficacy_lower for synonym in synonyms if synonym):
                    has_symptom_in_efficacy = True
                    matched_symptom_count += 1
                    continue  # マッチした場合は次の症状へ
                # のど痛み関連症状のチェック
                elif any(throat in normalized_symptom or throat in symptom_name for throat in throat_symptoms):
                    # 効能効果に「のど」「咽頭」「喉」などが含まれているか
                    if any(kw in efficacy_lower for kw in ['のど', '咽頭', '喉', '咽喉']):
                        has_symptom_in_efficacy = True
                    matched_symptom_count += 1
                # 頭痛関連症状のチェック
                elif any(headache in normalized_symptom or headache in symptom_name for headache in headache_symptoms):
                    # 効能効果に「頭痛」が含まれているか
                    if '頭痛' in efficacy_lower:
                        has_symptom_in_efficacy = True
                    matched_symptom_count += 1
                # 月経不順・生理痛関連症状（新規追加）
                elif any(menstrual in normalized_symptom or menstrual in symptom_name for menstrual in menstrual_symptoms):
                    # 効能効果に「月経痛」「生理痛」などが含まれているか
                    if any(kw in efficacy_lower for kw in ['月経痛', '生理痛', '月経不順', '生理不順', '月経異常', '生理異常', '血の道症', '血の道']):
                        has_symptom_in_efficacy = True
                    matched_symptom_count += 1
                # 月経不順・生理痛のキーワードマッチ（「生理が遅れている」など）
                elif any(keyword in normalized_symptom or keyword in symptom_name for keyword in menstrual_keywords):
                    # 効能効果に月経関連キーワードが含まれているか
                    if any(kw in efficacy_lower for kw in ['月経', '生理', '血の道']):
                        has_symptom_in_efficacy = True
                        matched_symptom_count += 1
                else:
                    # その他の症状の場合も、効能効果に含まれているかチェック
                    if normalized_symptom in efficacy_lower or symptom_name in efficacy_lower:
                        has_symptom_in_efficacy = True
                        matched_symptom_count += 1
            
            # 解熱鎮痛薬は発熱、のどの痛み、頭痛、月経不順・生理痛に効果があるため、一定のスコアを付与
            # ただし、効能効果に症状が明示的に含まれている場合のみスコアを付与
            # 効能が「生理痛」のみの場合は、風邪症状に対してスコアを付与しない
            if matched_symptom_count > 0:
                efficacy_lower = str(candidate.get('efficacy', '')).lower()
                is_menstrual_only = ('生理痛' in efficacy_lower or '月経痛' in efficacy_lower) and \
                                   not any(kw in efficacy_lower for kw in ['発熱', '熱', '解熱', '頭痛', 'のど', '咽頭', '喉', '鎮痛', '歯痛', '筋肉痛', '関節痛', '腰痛', '神経痛', '咽頭痛', '打撲痛', '急性上気道炎'])
                
                # 効能が「生理痛」のみの場合は、風邪症状に対してスコアを付与しない
                if is_menstrual_only:
                    # 風邪症状（発熱、頭痛、のどの痛み）が含まれている場合はスコアを付与しない
                    cold_symptoms_in_input = any(
                        any(cold_symptom in name for cold_symptom in ['発熱', '熱', '頭痛', 'のどの痛み', '咽頭痛', '喉の痛み'])
                        for name in symptom_names
                    )
                    if cold_symptoms_in_input:
                        return 0.0  # スコアを付与しない
                
                # 効能効果に症状が明示的に含まれている場合のみスコアを付与
                if has_symptom_in_efficacy:
                    # 効能効果に症状が明示的に含まれている場合：高スコア
                    base_score = 0.45  # 解熱鎮痛薬の基本スコア
                    return base_score * (matched_symptom_count / len(symptom_names))
        
        # 外用薬（のど）の場合、のどの痛みに対して一定のスコアを付与
        if "外用薬（のど）" in medicine_type or ("外用薬" in medicine_type and "のど" in medicine_type):
            throat_symptoms = ["のどの痛み", "咽頭痛", "喉の痛み", "のど痛"]
            symptom_names = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
            
            for symptom_name in symptom_names:
                normalized_symptom = normalize_text(symptom_name)
                if any(throat in normalized_symptom or throat in symptom_name for throat in throat_symptoms):
                    # 外用薬（のど）はのどの痛みに効果があるため、一定のスコアを付与
                    return 0.45
        
        return 0.0
    
    return 症状スコア / 症状数


def calculate_age_fit_score(candidate: Dict, user_info: Dict) -> float:
    """
    年齢適合性スコアを計算
    
    年齢がNoneの場合の処理を修正：
    - 年齢制限がない場合：0.6（年齢不明でも使用可能と判断）
    - 年齢制限が6歳以下：0.65（小児向け、年齢不明でも比較的安全）
    - 年齢制限が12歳以下：0.58（小児向け、年齢不明でも比較的安全）
    - 年齢制限が15歳以上：0.45（成人向け、年齢不明の場合は慎重に）
    """
    age = user_info.get('age')
    age_restriction = candidate.get('age_restriction', '')
    
    # age_imputedフラグがTrueの場合、ageをNoneとして扱う（年齢が不明な場合の処理を適用）
    age_imputed = user_info.get('age_imputed', False)
    if age_imputed:
        age = None
    
    # ageが空文字列や0の場合もNoneとして扱う
    if age == '' or age == 0:
        age = None
    
    # age_restrictionが数値（float/int）の場合も処理
    if isinstance(age_restriction, (int, float)):
        if isinstance(age_restriction, float) and math.isnan(age_restriction):
            age_restriction = ''
        else:
            # 数値の場合は文字列に変換して処理
            age_restriction = f"{int(age_restriction)}歳以上"

    min_age_allowed = _extract_min_age_value(age_restriction)
    
    # デバッグログ（INFOレベルでも出力）
    if _DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"年齢適合性スコア計算: age={age} (type={type(age)}), age_restriction={age_restriction}, min_age_allowed={min_age_allowed}, age is None={age is None}, product_name={candidate.get('product_name', '')}")

    if age is None:
        # 年齢が不明な場合の処理を修正
        # ログと実装の不一致を解消：年齢制限に応じた適切なスコアを返す
        base_score = 0.5
        if min_age_allowed is None:
            # 年齢制限がない場合：年齢不明でも使用可能と判断
            base_score += 0.1  # 0.6
        elif min_age_allowed <= 6:
            # 小児向け（6歳以下）：年齢不明でも比較的安全
            base_score += 0.15  # 0.65
        elif min_age_allowed <= 12:
            # 小児向け（12歳以下）：年齢不明でも比較的安全
            base_score += 0.08  # 0.58
        elif min_age_allowed >= 15:
            # 成人向け（15歳以上）：年齢不明の場合は慎重に
            base_score -= 0.05  # 0.45
        result_score = max(0.0, min(1.0, base_score))
        # INFOレベルでも出力（デバッグログが出力されない問題を解決）
        if _DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"年齢適合性スコア（年齢不明）: min_age_allowed={min_age_allowed}, base_score={base_score}, result={result_score}, product_name={candidate.get('product_name', '')}")
        return result_score

    if min_age_allowed is not None and age < min_age_allowed:
        return 0.0

    if age < 15:
        return 0.8 if min_age_allowed and min_age_allowed <= age else 0.6

    # 年齢が15歳以上の場合、年齢制限が15歳以上なら1.0、それ以外は0.9
    if min_age_allowed is not None and min_age_allowed >= 15:
        return 1.0
    elif min_age_allowed is None:
        # 年齢制限がない場合は1.0
        return 1.0
    else:
        # 年齢制限が15歳未満の場合は0.9（成人向けではない）
        return 0.9


def calculate_body_part_match_score(candidate: Dict, user_body_part: Optional[str]) -> float:
    """
    部位マッチングスコアを計算
    
    Args:
        candidate: 候補医薬品の情報
        user_body_part: ユーザーの症状部位（"delicate_area", "scalp", "throat"など）
    
    Returns:
        部位マッチングスコア
        - 部位が一致する場合: 1.0
        - 部位が不一致の場合: -0.5（大幅減点）
        - 部位情報がない場合: 0.0（ペナルティなし、ただし性器周辺の場合は軽いペナルティ）
    """
    if not user_body_part:
        return 0.0
    
    candidate_body_part = _detect_body_part_specificity(candidate)
    medicine_type = str(candidate.get('medicine_type', '')).lower()
    
    # 性器周辺（delicate_area）の症状に対する特別な処理
    if user_body_part == "delicate_area":
        if candidate_body_part == "delicate_area":
            # 性器専用の医薬品は最優先
            return 1.0
        elif candidate_body_part:
            # 他の部位専用の医薬品は大幅減点
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(
                    f"性器周辺症状に不適切な部位専用医薬品: 候補={candidate_body_part}, "
                    f"製品={candidate.get('product_name', '')}"
                )
            return -0.7  # 通常の-0.5より強いペナルティ
        else:
            # 部位情報がない場合でも、一般的な外用薬（皮膚）には軽いペナルティ
            # 性器周辺は特別な注意が必要なため
            if "外用薬（皮膚）" in medicine_type or "外用" in medicine_type:
                # 刺激の強い成分が含まれている可能性があるため、軽いペナルティ
                ingredients = str(candidate.get('ingredients', '')).lower()
                # 刺激の強い成分のキーワード
                strong_ingredients = ["メントール", "カンフル", "アンモニア", "サリチル酸"]
                has_strong_ingredient = any(ing in ingredients for ing in strong_ingredients)
                
                if has_strong_ingredient:
                    if _DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(
                            f"性器周辺症状に刺激の強い外用薬: 製品={candidate.get('product_name', '')}"
                        )
                    return -0.3  # 刺激の強い成分がある場合はペナルティ
                else:
                    return -0.1  # 一般的な外用薬には軽いペナルティ
            else:
                # 外用薬以外の場合はペナルティなし（内服薬など）
                return 0.0
    
    # その他の部位の処理（既存のロジック）
    if not candidate_body_part:
        # 候補に部位情報がない場合はペナルティなし
        return 0.0
    
    if candidate_body_part == user_body_part:
        # 部位が一致する場合
        return 1.0
    else:
        # 部位が不一致の場合、大幅減点
        if _DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(
                f"部位不一致: 候補={candidate_body_part}, ユーザー={user_body_part}, "
                f"製品={candidate.get('product_name', '')}"
            )
        return -0.5


def calculate_ingredient_based_boost(candidate: Dict, nlu_result: Dict, user_info: Dict, user_text: str = "") -> float:
    """
    成分ベースのスコアリング関数
    症状に応じた優先成分が含まれている場合にボーナスを付与
    
    Args:
        candidate: 候補医薬品の情報
        nlu_result: NLU解析結果
        user_info: ユーザー情報
        user_text: ユーザー入力テキスト（食事との関連性判定用）
    
    Returns:
        成分ベースのボーナススコア（0.0-1.0）
    """
    ingredients = str(candidate.get('ingredients', '')).lower()
    product_name = str(candidate.get('product_name', '')).lower()
    medicine_type = str(candidate.get('medicine_type', '')).lower()
    efficacy = str(candidate.get('efficacy', '')).lower()
    symptoms = nlu_result.get("symptoms", [])
    symptom_names = [s.get("name", "") for s in symptoms]
    
    if not symptoms:
        return 0.0
    
    boost = 0.0
    user_text_lower = user_text.lower() if user_text else ""
    
    # 胃薬・胃腸薬の症状別成分優先順位
    if '胃腸薬' in medicine_type or '胃薬' in medicine_type:
        # 胃痛の場合
        if "胃痛" in symptom_names:
            # 空腹時痛の判定（キーワード検出と症状ベースの両方）
            is_fasting_pain = any(kw in user_text_lower for kw in ["空腹時", "食前", "食事の前", "お腹が空いた時", "空腹"])
            # キーワードがない場合は症状から推測（胃痛のみの場合は空腹時痛の可能性）
            if not is_fasting_pain and len(symptom_names) == 1 and "胃痛" in symptom_names:
                is_fasting_pain = True  # デフォルトで空腹時痛と推測
            
            if is_fasting_pain:
                # 胃粘膜保護成分を優先（製品名と成分列の両方をチェック）
                for ingredient in STOMACH_MUCOSAL_PROTECTANTS:
                    if ingredient.lower() in ingredients or ingredient.lower() in product_name:
                        boost = max(boost, STOMACH_MEDICINE_PRIORITY["胃痛"]["胃粘膜保護"]["boost"])
                        if _DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"胃粘膜保護成分ボーナス（空腹時痛）: {candidate.get('product_name', '')} = +{STOMACH_MEDICINE_PRIORITY['胃痛']['胃粘膜保護']['boost']}")
                        break
            else:
                # 食後痛の場合は制酸薬を優先
                for ingredient in STOMACH_MEDICINE_PRIORITY["胃痛"]["制酸薬"]["ingredients"]:
                    if ingredient.lower() in ingredients:
                        boost = max(boost, STOMACH_MEDICINE_PRIORITY["胃痛"]["制酸薬"]["boost"])
                        if _DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"制酸薬ボーナス（食後痛）: {candidate.get('product_name', '')} = +{STOMACH_MEDICINE_PRIORITY['胃痛']['制酸薬']['boost']}")
                        break
        
        # 胸やけの場合
        if "胸やけ" in symptom_names:
            for ingredient in STOMACH_MEDICINE_PRIORITY["胸やけ"]["H2ブロッカー"]["ingredients"]:
                if ingredient.lower() in ingredients:
                    boost = max(boost, STOMACH_MEDICINE_PRIORITY["胸やけ"]["H2ブロッカー"]["boost"])
                    if _DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"H2ブロッカーボーナス（胸やけ）: {candidate.get('product_name', '')} = +{STOMACH_MEDICINE_PRIORITY['胸やけ']['H2ブロッカー']['boost']}")
                    break
        
        # 胃もたれの場合
        if "胃もたれ" in symptom_names:
            # 健胃消化薬のキーワードを効能効果から検出
            if any(kw in efficacy for kw in STOMACH_MEDICINE_PRIORITY["胃もたれ"]["健胃消化薬"]["ingredients"]):
                boost = max(boost, STOMACH_MEDICINE_PRIORITY["胃もたれ"]["健胃消化薬"]["boost"])
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"健胃消化薬ボーナス（胃もたれ）: {candidate.get('product_name', '')} = +{STOMACH_MEDICINE_PRIORITY['胃もたれ']['健胃消化薬']['boost']}")
        
        # 吐き気の場合
        if "吐き気" in symptom_names:
            for ingredient in STOMACH_MEDICINE_PRIORITY["吐き気"]["制吐薬"]["ingredients"]:
                if ingredient.lower() in ingredients:
                    boost = max(boost, STOMACH_MEDICINE_PRIORITY["吐き気"]["制吐薬"]["boost"])
                    if _DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"制吐薬ボーナス（吐き気）: {candidate.get('product_name', '')} = +{STOMACH_MEDICINE_PRIORITY['吐き気']['制吐薬']['boost']}")
                    break
    
    # 便秘薬の成分優先順位
    if "便秘" in symptom_names:
        # 高優先度（安全性重視）
        for ingredient in CONSTIPATION_MEDICINE_PRIORITY["高優先度（安全性重視）"]["ingredients"]:
            if ingredient.lower() in ingredients:
                boost = max(boost, CONSTIPATION_MEDICINE_PRIORITY["高優先度（安全性重視）"]["boost"])
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"安全性重視便秘薬ボーナス: {candidate.get('product_name', '')} = +{CONSTIPATION_MEDICINE_PRIORITY['高優先度（安全性重視）']['boost']}")
                break
        
        # 中優先度（効果重視だがリスクあり）は既にboostが0.0の場合のみ適用
        if boost == 0.0:
            for ingredient in CONSTIPATION_MEDICINE_PRIORITY["中優先度（効果重視だがリスクあり）"]["ingredients"]:
                if ingredient.lower() in ingredients:
                    boost = max(boost, CONSTIPATION_MEDICINE_PRIORITY["中優先度（効果重視だがリスクあり）"]["boost"])
                    if _DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"効果重視便秘薬ボーナス: {candidate.get('product_name', '')} = +{CONSTIPATION_MEDICINE_PRIORITY['中優先度（効果重視だがリスクあり）']['boost']}")
                    break
    
    # 解熱鎮痛薬の成分優先順位
    if '解熱鎮痛薬' in medicine_type:
        # 高優先度（胃に優しい）
        for ingredient in ANALGESIC_PRIORITY["高優先度（胃に優しい）"]["ingredients"]:
            if ingredient.lower() in ingredients:
                boost = max(boost, ANALGESIC_PRIORITY["高優先度（胃に優しい）"]["boost"])
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"胃に優しい解熱鎮痛薬ボーナス: {candidate.get('product_name', '')} = +{ANALGESIC_PRIORITY['高優先度（胃に優しい）']['boost']}")
                break
        
        # 中優先度（バランス型）
        if boost == 0.0:
            for ingredient in ANALGESIC_PRIORITY["中優先度（バランス型）"]["ingredients"]:
                if ingredient.lower() in ingredients:
                    boost = max(boost, ANALGESIC_PRIORITY["中優先度（バランス型）"]["boost"])
                    if _DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"バランス型解熱鎮痛薬ボーナス: {candidate.get('product_name', '')} = +{ANALGESIC_PRIORITY['中優先度（バランス型）']['boost']}")
                    break
    
    # 外用薬（喉）の成分優先順位
    if '外用薬（のど）' in medicine_type or ('外用薬' in medicine_type and "のどの痛み" in symptom_names):
        # 高優先度
        for ingredient in THROAT_TOPICAL_PRIORITY["高優先度"]["ingredients"]:
            if ingredient.lower() in ingredients:
                boost = max(boost, THROAT_TOPICAL_PRIORITY["高優先度"]["boost"])
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"外用薬（喉）高優先度成分ボーナス: {candidate.get('product_name', '')} = +{THROAT_TOPICAL_PRIORITY['高優先度']['boost']}")
                break
        
        # 中優先度
        if boost == 0.0:
            for ingredient in THROAT_TOPICAL_PRIORITY["中優先度"]["ingredients"]:
                if ingredient.lower() in ingredients:
                    boost = max(boost, THROAT_TOPICAL_PRIORITY["中優先度"]["boost"])
                    if _DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"外用薬（喉）中優先度成分ボーナス: {candidate.get('product_name', '')} = +{THROAT_TOPICAL_PRIORITY['中優先度']['boost']}")
                    break
    
    # 切り傷・擦り傷の成分・剤形ベース判定
    if "切り傷" in symptom_names or "擦り傷" in symptom_names:
        # 成分ベース
        for ingredient in WOUND_MEDICINE_PRIORITY["成分"]["ingredients"]:
            if ingredient.lower() in ingredients:
                boost = max(boost, WOUND_MEDICINE_PRIORITY["成分"]["boost"])
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"切り傷成分ボーナス: {candidate.get('product_name', '')} = +{WOUND_MEDICINE_PRIORITY['成分']['boost']}")
                break
        
        # 剤形ベース
        for form in WOUND_MEDICINE_PRIORITY["剤形"]["forms"]:
            if form in product_name or form in medicine_type:
                boost = max(boost, WOUND_MEDICINE_PRIORITY["剤形"]["boost"])
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"切り傷剤形ボーナス: {candidate.get('product_name', '')} = +{WOUND_MEDICINE_PRIORITY['剤形']['boost']}")
                break
    
    # 月経不順・生理痛向けの成分ベーススコアリング（新規追加）
    menstrual_symptoms = ["月経不順", "生理不順", "生理痛", "月経痛"]
    has_menstrual_symptom = any(symptom in symptom_names for symptom in menstrual_symptoms)
    
    if has_menstrual_symptom:
        # 成分ベースのマッチング
        menstrual_boost = 0.0
        
        # 成分の組み合わせパターンマッチング
        # 加味逍遙散の成分セット（柴胡、当帰、芍薬、茯苓、牡丹皮など）
        has_shakuyo = any(kw in ingredients for kw in ['シャクヨウ', '柴胡', 'しゃくよう'])
        has_toki = any(kw in ingredients for kw in ['トウキ', '当帰', 'とうき'])
        has_shakuyaku = any(kw in ingredients for kw in ['シャクヤク', '芍薬', 'しゃくやく'])
        has_bukuryo = any(kw in ingredients for kw in ['ブクリョウ', '茯苓', 'ぶくりょう'])
        has_botanpi = any(kw in ingredients for kw in ['ボタンピ', '牡丹皮', 'ぼたんぴ'])
        
        # 加味逍遙散の成分パターン（柴胡+当帰+芍薬+茯苓）
        if has_shakuyo and has_toki and has_shakuyaku and has_bukuryo:
            menstrual_boost = max(menstrual_boost, 0.25)
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"🔬 成分ベーススコア: 加味逍遙散パターン = +0.25 ({candidate.get('product_name', '')})")
        
        # 当帰芍薬散の成分パターン（当帰+芍薬+茯苓）
        if has_toki and has_shakuyaku and has_bukuryo:
            menstrual_boost = max(menstrual_boost, 0.20)
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"🔬 成分ベーススコア: 当帰芍薬散パターン = +0.20 ({candidate.get('product_name', '')})")
        
        # 桂枝茯苓丸の成分パターン（桂枝+茯苓+牡丹皮+桃仁+芍薬）
        has_keihi = any(kw in ingredients for kw in ['ケイヒ', '桂枝', 'けいひ'])
        has_tounin = any(kw in ingredients for kw in ['トウニン', '桃仁', 'とうにん'])
        if has_keihi and has_bukuryo and has_botanpi and has_tounin and has_shakuyaku:
            menstrual_boost = max(menstrual_boost, 0.25)
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"🔬 成分ベーススコア: 桂枝茯苓丸パターン = +0.25 ({candidate.get('product_name', '')})")
        
        # 単独成分のマッチング
        # 月経不順に効く成分
        if "月経不順" in symptom_names or "生理不順" in symptom_names:
            if has_toki:
                menstrual_boost = max(menstrual_boost, 0.10)
            if has_shakuyaku:
                menstrual_boost = max(menstrual_boost, 0.10)
            if has_bukuryo:
                menstrual_boost = max(menstrual_boost, 0.08)
        
        # イライラに効く成分
        if "イライラ" in symptom_names:
            if has_shakuyo:
                menstrual_boost = max(menstrual_boost, 0.12)
            if has_botanpi:
                menstrual_boost = max(menstrual_boost, 0.10)
        
        # ネガティブマッチング: 大黄を含む医薬品で、ユーザーが「お腹を壊しやすい」「産後」「授乳中」の場合
        has_daiou = any(kw in ingredients for kw in ['ダイオウ', '大黄', 'だいおう'])
        if has_daiou:
            # ユーザーが「お腹を壊しやすい」場合
            user_message = user_text or user_info.get('user_message', '') or ''
            user_message_lower = user_message.lower() if user_message else ''
            if any(kw in user_message_lower for kw in ['お腹を壊しやすい', '下痢しやすい', 'お腹が弱い', '胃腸が弱い']):
                menstrual_boost -= 0.15  # 小幅減点
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"⚠️ 成分ベーススコア: 大黄含有でお腹を壊しやすい = -0.15 ({candidate.get('product_name', '')})")
            
            # ユーザーが「産後」「授乳中」の場合
            if user_info.get('postpartum') is True or user_info.get('breastfeeding') is True:
                menstrual_boost -= 0.20  # 大幅減点（完全除外はis_contraindicatedで処理）
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"⚠️ 成分ベーススコア: 大黄含有で産後・授乳中 = -0.20 ({candidate.get('product_name', '')})")
        
        boost = max(boost, menstrual_boost)
    
    if has_menstrual_symptom and '解熱鎮痛薬' in medicine_type:
        # ラムールQ、加味逍遙散、命の母ホワイトの製品名ベース識別（最高優先度）
        product_name_lower = product_name.lower()
        efficacy_lower = efficacy.lower()
        
        # ラムールQの識別（厳密なマッチング）
        if is_exact_product_match(product_name, ["ラムールQ", "ラムールｑ", "ラムールq"]):
            boost = max(boost, 0.30)  # ラムールQ専用ボーナス（0.25から0.30に増加）
            logger.info(f"⭐ ラムールQ製品名ボーナス: {candidate.get('product_name', '')} = +0.30")
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"ラムールQ製品名ボーナス: {candidate.get('product_name', '')} = +0.30")
        
        # 加味逍遙散の識別（厳密なマッチング）
        if is_exact_product_match(product_name, ["加味逍遙散", "カミショウヨウサン"]):
            boost = max(boost, 0.30)  # 加味逍遙散専用ボーナス（0.25から0.30に増加）
            logger.info(f"⭐ 加味逍遙散製品名ボーナス: {candidate.get('product_name', '')} = +0.30")
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"加味逍遙散製品名ボーナス: {candidate.get('product_name', '')} = +0.30")
        
        # 命の母ホワイトの識別（厳密なマッチング）
        if is_exact_product_match(product_name, ["命の母ホワイト"]) or (is_exact_product_match(product_name, ["命の母"]) and "ホワイト" in product_name):
            boost = max(boost, 0.30)  # 命の母ホワイト専用ボーナス（0.25から0.30に増加）
            logger.info(f"⭐ 命の母ホワイト製品名ボーナス: {candidate.get('product_name', '')} = +0.30")
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"命の母ホワイト製品名ボーナス: {candidate.get('product_name', '')} = +0.30")
        
        # ルナエールの識別（厳密なマッチング）
        if is_exact_product_match(product_name, ["ルナエール"]):
            boost = max(boost, 0.28)  # ルナエール専用ボーナス
            logger.info(f"⭐ ルナエール製品名ボーナス: {candidate.get('product_name', '')} = +0.28")
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"ルナエール製品名ボーナス: {candidate.get('product_name', '')} = +0.28")
        
        # ルナフェミンの識別（厳密なマッチング）
        if is_exact_product_match(product_name, ["ルナフェミン"]):
            boost = max(boost, 0.28)  # ルナフェミン専用ボーナス
            logger.info(f"⭐ ルナフェミン製品名ボーナス: {candidate.get('product_name', '')} = +0.28")
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"ルナフェミン製品名ボーナス: {candidate.get('product_name', '')} = +0.28")
        
        # 桂枝茯苓丸の識別（月経不順+イライラの症状パターンでも推奨、厳密なマッチング）
        if is_exact_product_match(product_name, ["桂枝茯苓丸", "ケイシブクリョウガン"]) or "桂枝茯苓丸" in efficacy:
            boost = max(boost, 0.28)  # 桂枝茯苓丸専用ボーナス
            logger.info(f"⭐ 桂枝茯苓丸製品名ボーナス: {candidate.get('product_name', '')} = +0.28")
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"桂枝茯苓丸製品名ボーナス: {candidate.get('product_name', '')} = +0.28")
        
        # 当帰芍薬散を含む医薬品（最高優先度）
        product_name_upper = product_name.upper()
        efficacy_upper = efficacy.upper()
        if "当帰芍薬散" in product_name or "トウキシャクヤクサン" in product_name_upper or "当帰芍薬散" in efficacy:
            boost = max(boost, MENSTRUAL_MEDICINE_PRIORITY["高優先度（当帰芍薬散）"]["boost"])
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"当帰芍薬散ボーナス: {candidate.get('product_name', '')} = +{MENSTRUAL_MEDICINE_PRIORITY['高優先度（当帰芍薬散）']['boost']}")
        else:
            # 当帰と芍薬の両方が含まれる場合（高優先度）
            toki_keywords = ["トウキ", "当帰", "とうき", "トウキ末", "トウキ流エキス", "トウキエキス", "トウキ乾燥エキス", "トウキ流エキスＳ", "トウキエキスＳ", "当帰末"]
            shakuyaku_keywords = ["シャクヤク", "芍薬", "しゃくやく", "シャクヤク末", "シャクヤクエキス", "シャクヤク乾燥エキス", "芍薬エキス"]
            
            has_toki = any(kw.lower() in ingredients for kw in toki_keywords)
            has_shakuyaku = any(kw.lower() in ingredients for kw in shakuyaku_keywords)
            
            if has_toki and has_shakuyaku:
                boost = max(boost, MENSTRUAL_MEDICINE_PRIORITY["高優先度（当帰+芍薬の組み合わせ）"]["boost"])
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"当帰+芍薬組み合わせボーナス: {candidate.get('product_name', '')} = +{MENSTRUAL_MEDICINE_PRIORITY['高優先度（当帰+芍薬の組み合わせ）']['boost']}")
            # 当帰または芍薬単独（中優先度）
            elif has_toki or has_shakuyaku:
                boost = max(boost, MENSTRUAL_MEDICINE_PRIORITY["中優先度（当帰または芍薬単独）"]["boost"])
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"当帰または芍薬単独ボーナス: {candidate.get('product_name', '')} = +{MENSTRUAL_MEDICINE_PRIORITY['中優先度（当帰または芍薬単独）']['boost']}")
    
    # 睡眠障害（眠気）向けの成分優先順位
    sleep_disorder_symptoms = ["眠気", "だるさ", "倦怠感", "疲労感"]
    has_sleep_disorder_symptom = any(symptom in symptom_names for symptom in sleep_disorder_symptoms)
    
    if has_sleep_disorder_symptom and '睡眠障害' in medicine_type:
        # 高優先度（ビタミン剤配合カフェイン製剤）
        product_name_original = str(candidate.get('product_name', ''))
        product_name_lower = product_name.lower()
        # 製品名のマッチング（部分マッチでも可）
        for product_pattern in SLEEP_DISORDER_PRIORITY["高優先度（ビタミン剤配合カフェイン製剤）"]["product_names"]:
            if product_pattern.lower() in product_name_lower:
                boost = max(boost, SLEEP_DISORDER_PRIORITY["高優先度（ビタミン剤配合カフェイン製剤）"]["boost"])
                logger.info(f"⭐ ビタミン剤配合カフェイン製剤ボーナス: {product_name_original} = +{SLEEP_DISORDER_PRIORITY['高優先度（ビタミン剤配合カフェイン製剤）']['boost']}")
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"ビタミン剤配合カフェイン製剤ボーナス: {product_name_original} = +{SLEEP_DISORDER_PRIORITY['高優先度（ビタミン剤配合カフェイン製剤）']['boost']}")
                break
        
        # 中優先度（カフェイン単独製剤）- ビタミン剤配合でない場合のみ
        if boost < SLEEP_DISORDER_PRIORITY["高優先度（ビタミン剤配合カフェイン製剤）"]["boost"]:
            for ingredient in SLEEP_DISORDER_PRIORITY["中優先度（カフェイン単独製剤）"]["ingredients"]:
                if ingredient.lower() in ingredients:
                    boost = max(boost, SLEEP_DISORDER_PRIORITY["中優先度（カフェイン単独製剤）"]["boost"])
                    if _DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"カフェイン単独製剤ボーナス: {candidate.get('product_name', '')} = +{SLEEP_DISORDER_PRIORITY['中優先度（カフェイン単独製剤）']['boost']}")
                    break
    
    # 去痰成分へのボーナススコア（単一症状「たん」の場合）
    # 去痰成分の定義（西洋薬 + 漢方薬）
    EXPECTORANT_INGREDIENTS = [
        # 西洋薬
        "カルボシステイン", "L-カルボシステイン",
        "ブロムヘキシン", "ブロムヘキシン塩酸塩",
        "アンブロキソール", "アンブロキソール塩酸塩",
        "グアヤコールスルホン酸カリウム",
        "セネガエキス", "キキョウ", "キキョウ末", "キキョウ流エキス",
        # 漢方薬（包括的リスト）
        "バクモンドウ", "麦門冬", "麦門冬湯",
        "清肺湯",
        "五虎湯",
        "竹茹温胆湯",
        "半夏厚朴湯",
        # その他の去痰に効く漢方薬成分
        "ハンゲ", "半夏",
        "コウベイ", "厚朴"
    ]
    
    # 強力な鎮咳成分の定義（すべての強力な鎮咳成分）
    STRONG_ANTITUSSIVE_INGREDIENTS = [
        "ジヒドロコデイン", "ジヒドロコデインリン酸塩", "ジヒドロコデインリン酸塩水和物",
        "コデイン", "コデインリン酸塩水和物", "リン酸コデイン",
        "デキストロメトルファン", "デキストロメトルファン臭化水素酸塩", "デキストロメトルファン臭化水素酸塩水和物",
        "ノスカピン", "ノスカピン塩酸塩"
        # メチルエフェドリンは気管支拡張作用もあるため、条件付きで判定
    ]
    
    # 単一症状が「たん」の場合のボーナス（重み付け処理）
    if len(symptom_names) == 1 and symptom_names[0] in ["たん", "痰"]:
        # 去痰成分のチェック（成分名と製品名の両方をチェック）
        has_expectorant = False
        expectorant_type = None  # 'western' or 'kampo'
        
        # 成分名でチェック
        for expectorant in EXPECTORANT_INGREDIENTS:
            if expectorant.lower() in ingredients:
                has_expectorant = True
                # 漢方薬か西洋薬かを判定
                if any(kampo in expectorant.lower() for kampo in ['バクモンドウ', '麦門冬', '清肺湯', '五虎湯', '竹茹温胆湯', '半夏厚朴湯', 'ハンゲ', 'コウベイ']):
                    expectorant_type = 'kampo'
                else:
                    expectorant_type = 'western'
                break
        
        # 製品名でチェック（漢方薬の場合）
        if not has_expectorant:
            kampo_product_names = ['麦門冬湯', '清肺湯', '五虎湯', '竹茹温胆湯', '半夏厚朴湯']
            for kampo_name in kampo_product_names:
                if kampo_name.lower() in product_name:
                    has_expectorant = True
                    expectorant_type = 'kampo'
                    break
        
        # 強力な鎮咳成分のチェック
        has_strong_antitussive = False
        for antitussive in STRONG_ANTITUSSIVE_INGREDIENTS:
            if antitussive.lower() in ingredients:
                has_strong_antitussive = True
                break
        
        # 重み付け処理
        if has_expectorant:
            if has_strong_antitussive:
                # 去痰成分と強力な鎮咳成分の両方が含まれている場合
                # 重み付け：去痰成分の種類と鎮咳成分の強度に応じて計算
                if expectorant_type == 'kampo':
                    # 漢方薬の場合：ボーナスを減らしてペナルティを適用
                    expectorant_boost = 0.10 - 0.05  # 0.05（漢方薬は0.10、ペナルティ-0.05）
                else:
                    # 西洋薬の場合：ボーナスを減らしてペナルティを適用
                    expectorant_boost = 0.15 - 0.05  # 0.10（西洋薬は0.15、ペナルティ-0.05）
                
                boost = max(boost, expectorant_boost)
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"去痰成分ボーナス（鎮咳成分含有）: {candidate.get('product_name', '')} = +{expectorant_boost:.2f} (タイプ: {expectorant_type})")
            else:
                # 純粋な去痰効果として高評価
                if expectorant_type == 'kampo':
                    expectorant_boost = 0.10  # 漢方薬は固定値0.10
                else:
                    expectorant_boost = 0.15  # 西洋薬は0.15
                
                boost = max(boost, expectorant_boost)
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"去痰成分ボーナス: {candidate.get('product_name', '')} = +{expectorant_boost:.2f} (タイプ: {expectorant_type})")
    
    return boost


def is_contraindicated(candidate: Dict, user_info: Dict, nlu_result: Dict) -> Dict:
    """
    禁忌事項の優先ハードチェック（スコアリング計算前に除外）

    Args:
        candidate: 候補医薬品情報
        user_info: ユーザー情報
        nlu_result: NLU解析結果

    Returns:
        {
            "is_contraindicated": True/False,
            "reason": "除外理由",
            "severity": "critical/warning"
        }
    """
    product_name = candidate.get('product_name', '')
    ingredients = str(candidate.get('ingredients', '')).lower()
    efficacy = str(candidate.get('efficacy', '')).lower()

    # 妊娠中（またはその可能性）の判定
    is_pregnant = False
    pregnancy_reason = ""

    # 明示的なキーワードを検出
    user_message = user_info.get('user_message', '') or ''
    user_message_lower = user_message.lower()
    pregnancy_keywords = ['妊娠中', '妊娠の可能性', '妊娠している', '妊婦', '妊娠', '妊娠している可能性']
    if any(kw in user_message_lower for kw in pregnancy_keywords):
        is_pregnant = True
        pregnancy_reason = "明示的なキーワード検出"

    # NLUで妊娠関連の状態を抽出
    if not is_pregnant:
        pregnancy_possible = nlu_result.get('pregnancy_possible', {})
        if isinstance(pregnancy_possible, dict) and pregnancy_possible.get('detected', False):
            is_pregnant = True
            pregnancy_reason = "NLU解析による検出"

    # ユーザー属性（user_info）から判定
    if not is_pregnant:
        if user_info.get('pregnant') is True or user_info.get('pregnancy_possible') is True:
            is_pregnant = True
            pregnancy_reason = "ユーザー属性による検出"

    # 妊娠中の場合の除外
    if is_pregnant:
        # 桃仁（トウニン）を含む製品を完全除外
        if '桃仁' in ingredients or 'トウニン' in ingredients or 'とうにん' in ingredients:
            logger.info(f"🚫 Safety Exclusion: {product_name} (妊娠中のため桃仁含有製品を除外)")
            return {
                "is_contraindicated": True,
                "reason": "妊娠中のため除外（桃仁含有）",
                "severity": "critical"
            }

        # 牡丹皮（ボタンピ）を含む製品を完全除外
        if '牡丹皮' in ingredients or 'ボタンピ' in ingredients or 'ぼたんぴ' in ingredients:
            logger.info(f"🚫 Safety Exclusion: {product_name} (妊娠中のため牡丹皮含有製品を除外)")
            return {
                "is_contraindicated": True,
                "reason": "妊娠中のため除外（牡丹皮含有）",
                "severity": "critical"
            }

        # 子宮収縮作用のリスクがある成分を含む製品を除外
        uterine_contraction_ingredients = ['桃仁', 'トウニン', '牡丹皮', 'ボタンピ', '桂枝', 'ケイヒ']
        if any(ing in ingredients for ing in uterine_contraction_ingredients):
            if any(kw in efficacy for kw in ['月経不順', '生理不順', '血の道症', '血の道']):
                logger.info(f"🚫 Safety Exclusion: {product_name} (妊娠中のため子宮収縮作用リスクのある成分含有製品を除外)")
                return {
                    "is_contraindicated": True,
                    "reason": "妊娠中のため除外（子宮収縮作用リスク）",
                    "severity": "critical"
                }

    # 授乳中の判定
    is_breastfeeding = False

    # 明示的なキーワードを検出
    breastfeeding_keywords = ['授乳中', '授乳', '母乳', '授乳している', '授乳期間中']
    if any(kw in user_message_lower for kw in breastfeeding_keywords):
        is_breastfeeding = True

    # ユーザー属性（user_info）から判定
    if not is_breastfeeding:
        if user_info.get('breastfeeding') is True:
            is_breastfeeding = True

    # 授乳中の場合の除外
    if is_breastfeeding:
        # 大黄を含む製品を完全除外
        if '大黄' in ingredients or 'ダイオウ' in ingredients or 'だいおう' in ingredients:
            logger.info(f"🚫 Safety Exclusion: {product_name} (授乳中のため大黄含有製品を除外)")
            return {
                "is_contraindicated": True,
                "reason": "授乳中のため除外（大黄含有）",
                "severity": "critical"
            }

    return {
        "is_contraindicated": False,
        "reason": "",
        "severity": ""
    }


def classify_medicine_mechanism(candidate: Dict) -> str:
    """
    医薬品の作用機序を分類（4カテゴリ）

    Args:
        candidate: 候補医薬品情報

    Returns:
        作用機序カテゴリ: "補血・調血系", "理気・駆瘀血系", "総合女性薬", "鎮痛特化型", "その他"
    """
    product_name = candidate.get('product_name', '')
    efficacy = str(candidate.get('efficacy', '')).lower()
    ingredients = str(candidate.get('ingredients', '')).lower()
    medicine_type = candidate.get('medicine_type', '')

    if '解熱鎮痛薬' in medicine_type:
        return "鎮痛特化型"
    product_name_lower = product_name.lower()
    if any(kw in product_name_lower for kw in ['命の母', 'ラムール', 'ルナエール', 'ルナフェミン']):
        return "総合女性薬"
    if any(vitamin in ingredients for vitamin in ['ビタミン', 'vitamin', 'ビタミンe', 'ビタミンb', 'トコフェロール']):
        if any(kw in efficacy for kw in ['月経不順', '生理不順', '血の道症', '血の道', '生理痛', '月経痛']):
            return "総合女性薬"
    has_toki = any(kw in ingredients for kw in ['トウキ', '当帰', 'とうき'])
    has_shakuyaku = any(kw in ingredients for kw in ['シャクヤク', '芍薬', 'しゃくやく'])
    if '当帰芍薬散' in product_name or (has_toki and has_shakuyaku):
        return "補血・調血系"
    if any(kw in product_name for kw in ['加味逍遙散', '桂枝茯苓丸', '桃核承気湯']):
        return "理気・駆瘀血系"
    has_shakuyo = any(kw in ingredients for kw in ['シャクヨウ', '柴胡', 'しゃくよう'])
    has_bukuryo = any(kw in ingredients for kw in ['ブクリョウ', '茯苓', 'ぶくりょう'])
    has_botanpi = any(kw in ingredients for kw in ['ボタンピ', '牡丹皮', 'ぼたんぴ'])
    has_tounin = any(kw in ingredients for kw in ['トウニン', '桃仁', 'とうにん'])
    has_keihi = any(kw in ingredients for kw in ['ケイヒ', '桂枝', 'けいひ'])
    if has_shakuyo and has_toki and has_shakuyaku and has_bukuryo:
        return "理気・駆瘀血系"
    if has_keihi and has_bukuryo and has_botanpi and has_tounin and has_shakuyaku:
        return "理気・駆瘀血系"
    if has_toki and has_shakuyaku and has_bukuryo:
        return "補血・調血系"
    if any(kw in efficacy for kw in ['血行改善', '冷え性', '冷え', '血を補う', '血を巡らせる']):
        if has_toki or has_shakuyaku:
            return "補血・調血系"
    if any(kw in efficacy for kw in ['滞り', '瘀血', '精神', 'イライラ', 'ストレス', '不安']):
        if has_shakuyo or has_keihi or has_botanpi:
            return "理気・駆瘀血系"
    if any(kw in efficacy for kw in ['月経不順', '生理不順', '血の道症', '血の道']):
        if has_toki or has_shakuyaku:
            return "補血・調血系"
        elif has_shakuyo or has_keihi:
            return "理気・駆瘀血系"
        else:
            return "総合女性薬"
    return "その他"


def _recheck_risk_ingredients(candidates: List[Dict], nlu_result: Dict) -> List[Dict]:
    """
    リスク成分の再チェック

    Args:
        candidates: 候補医薬品リスト
        nlu_result: NLU解析結果

    Returns:
        検証済み候補リスト（リスク警告を追加）
    """
    symptoms = nlu_result.get("symptoms", [])
    symptom_names = [s.get("name") for s in symptoms]
    is_single_symptom = len(symptom_names) == 1

    validated = []
    for candidate in candidates:
        ingredients = candidate.get('ingredients', '')
        contains_risk, risk_name, risk_info = _contains_risk_ingredient(ingredients)

        if contains_risk:
            if 'risk_ingredient' not in candidate:
                candidate['risk_ingredient'] = risk_name
                candidate['risk_warning'] = risk_info.get("warning", "") if risk_info else ""

            if is_single_symptom:
                candidate['risk_warning'] = f"⚠️ {candidate.get('risk_warning', '')} 単一症状のため、より安全な医薬品の検討をお勧めします。"

        validated.append(candidate)

    return validated

