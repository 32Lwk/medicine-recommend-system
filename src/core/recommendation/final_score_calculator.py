"""
最終スコア計算モジュール（SRP: 候補の最終スコア統合のみを担当）
rule_based_recommendation から切り出し。
"""
import logging
import os
import re
from itertools import combinations
from typing import Dict

from src.utils.candidate_normalizer import normalize_candidate_for_scoring
from src.core.recommendation_constants import (
    CHICKENPOX_KEYWORDS,
    KAMPO_PREFERRED_SYMPTOMS,
    MAJOR_ANALGESIC_MEDICINES,
    MENSTRUAL_GENERAL_EFFICACY_KEYWORDS,
    MENSTRUAL_ONLY_PRODUCTS,
    MENSTRUAL_SYMPTOM_KEYWORDS,
    SCORING_WEIGHTS,
    STRONG_INGREDIENTS,
    STRONG_PRODUCTS,
    SYMPTOM_PATTERN_OPTIMIZATION,
    THROAT_KEYWORD_TOKENS,
    THROAT_LIQUID_TOKENS,
    THROAT_SPECIFIC_INGREDIENTS,
    THROAT_SYMPTOM_TOKENS,
    TRUSTED_MANUFACTURERS,
    MULTI_SYMPTOM_COMBINATIONS,
)
from src.core.scoring_utils import (
    calculate_efficacy_specificity_score,
    calculate_side_effect_risk_score,
    calculate_interaction_risk_score,
    calculate_usage_convenience_score,
    check_allergy_contraindication,
    check_drug_interactions,
    calculate_symptom_specific_boost,
    _is_kampo_or_herbal_medicine,
    _is_goreisan,
    normalize_text,
    normalize_medicine_name_to_hankaku,
)
from src.core.candidate_scoring import (
    is_contraindicated,
    calculate_symptom_match_score,
    calculate_age_fit_score,
    calculate_body_part_match_score,
    calculate_ingredient_based_boost,
    ensure_score_difference,
    is_exact_product_match,
    is_comprehensive_cold_medicine,
    is_pollen_rhinitis_focus,
    _is_kakkonto_medicine,
    _is_motion_sickness_medicine,
    classify_medicine_mechanism,
)
from src.core.kampo_logic import determine_kampo_sho
from src.core.recommendation.life_stage_preference import (
    determine_life_stage,
    apply_user_preference_bonus,
)
from src.core.recommendation.symptom_pattern_matcher import match_symptom_pattern
from src.core.recommendation.recommendation_scoring import (
    calculate_symptom_specificity_penalty,
)
from src.core.user_detection import extract_user_preferences

logger = logging.getLogger(__name__)
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"


def calculate_final_score(candidate: Dict, nlu_result: Dict, user_info: Dict, user_text: str = "") -> Dict:
    """
    最終スコアを計算（全スコアを統合）
    
    Args:
        candidate: 候補医薬品情報
        nlu_result: NLU解析結果
        user_info: ユーザー情報
        user_text: ユーザー入力テキスト（成分ベースボーナス用）
    
    Returns:
        {
            "total_score": float,
            "score_breakdown": {
                "symptom_match": float,
                "efficacy_specificity": float,
                "age_fit": float,
                "usage_convenience": float,
                "side_effect_risk": float,
                "interaction_risk": float
            }
        }
    """
    # 日本語キー（製品名・成分・効能効果）の候補を英語キーに正規化（テスト・本番の両対応）
    normalize_candidate_for_scoring(candidate)

    # 禁忌事項の優先ハードチェック（スコアリング計算の前）
    contraindication_check = is_contraindicated(candidate, user_info, nlu_result)
    if contraindication_check.get("is_contraindicated", False):
        # スコアリング計算をスキップし、即座に除外
        return {
            "total_score": 0.0,
            "score_breakdown": {
                "symptom_match": 0.0,
                "efficacy_specificity": 0.0,
                "age_fit": 0.0,
                "usage_convenience": 0.0,
                "side_effect_risk": 0.0,
                "interaction_risk": 0.0
            },
            "contraindication_reason": contraindication_check.get("reason", ""),
            "contraindication_severity": contraindication_check.get("severity", "critical")
        }
    
    # --- 生理痛専用医薬品の完全除外チェック（早期チェック） ---
    # 生理痛専用の解熱鎮痛剤を、生理痛以外の場合に完全に除外
    # CSVの列名が'製品名'の場合と'product_name'の場合の両方に対応
    product_name_early = candidate.get('product_name', candidate.get('製品名', ''))
    efficacy_early = str(candidate.get('efficacy', candidate.get('効能効果', ''))).lower()
    
    # 製品名で生理痛専用医薬品を判定（効能効果に関係なく、製品名で判定）
    is_menstrual_only_product = any(menstrual_product in product_name_early for menstrual_product in MENSTRUAL_ONLY_PRODUCTS)
    
    # 効能効果が「生理痛」のみの医薬品を判定（他の効能効果がない場合）
    has_menstrual_only_efficacy = (
        '生理痛' in efficacy_early and
        not any(general_efficacy in efficacy_early for general_efficacy in MENSTRUAL_GENERAL_EFFICACY_KEYWORDS)
    )
    
    # 小児用ノーシンピュアの例外処理（アセトアミノフェンのみの場合は除外しない）
    is_pediatric_noshin_early = "小中学生用ノーシンピュア" in product_name_early or "小中学生用" in product_name_early
    ingredients_check_early = str(candidate.get('ingredients', candidate.get('成分', ''))).lower()
    has_acetaminophen_only_early = 'アセトアミノフェン' in ingredients_check_early and 'イブプロフェン' not in ingredients_check_early
    is_pediatric_exception_early = is_pediatric_noshin_early and has_acetaminophen_only_early
    
    # カロナール・タイレノールの例外（一般用解熱鎮痛薬。CSVの効能が「生理痛」のみでも頭痛・発熱に推奨する）
    is_general_acetaminophen_early = ('カロナール' in product_name_early or 'タイレノール' in product_name_early) and has_acetaminophen_only_early
    
    # ロキソニン系の例外（一般用NSAIDs。CSVの効能が「生理痛」のみでも頭痛・筋肉痛・発熱に推奨する）
    has_loxoprofen_early = 'ロキソプロフェン' in ingredients_check_early
    is_general_loxonin_early = 'ロキソニン' in product_name_early and has_loxoprofen_early
    
    # 生理痛専用医薬品の判定（製品名ベースで判定、効能効果に関係なく除外）
    if (is_menstrual_only_product or has_menstrual_only_efficacy) and not is_pediatric_exception_early and not is_general_acetaminophen_early and not is_general_loxonin_early:
        # 生理痛関連キーワードのチェック
        user_text_lower_early = user_text.lower() if user_text else ''
        has_menstrual_keyword_early = any(kw in user_text_lower_early for kw in MENSTRUAL_SYMPTOM_KEYWORDS)
        
        # 症状名からもチェック
        symptom_names_early = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        has_menstrual_symptom_early = any(
            any(kw in symptom_name.lower() for kw in MENSTRUAL_SYMPTOM_KEYWORDS)
            for symptom_name in symptom_names_early
        )
        
        # 生理痛が明示されていない場合は完全に除外
        if not (has_menstrual_keyword_early or has_menstrual_symptom_early):
            return {
                "total_score": 0.0,
                "score_breakdown": {
                    "symptom_match": 0.0,
                    "efficacy_specificity": 0.0,
                    "age_fit": 0.0,
                    "usage_convenience": 0.0,
                    "side_effect_risk": 0.0,
                    "interaction_risk": 0.0
                },
                "contraindication_reason": f"{product_name_early}は生理痛専用の医薬品です。生理痛が明示されていない場合は使用できません。",
                "contraindication_severity": "critical"
            }
    
    # --- アスピリンとインフルエンザ・水痘の組み合わせの早期チェック（2.5で追加） ---
    # 15歳未満のインフルエンザ・水痘患者ではアスピリンを完全に除外
    # CSVの列名が'成分'の場合と'ingredients'の場合の両方に対応
    ingredients_str_early = str(candidate.get('ingredients', candidate.get('成分', ''))).lower()
    has_aspirin_early = 'アスピリン' in ingredients_str_early or 'アセチルサリチル酸' in ingredients_str_early
    
    if has_aspirin_early and user_info and user_info.get('age') and user_info.get('age') < 15:
        # インフルエンザ・水痘の疑いの検出
        influenza_risk_early = nlu_result.get('influenza_risk', False) or False
        
        # 水痘の疑いの検出（キーワードと症状の両方をチェック）
        user_text_lower_early = user_text.lower() if user_text else ''
        has_chickenpox_keyword_early = any(kw in user_text_lower_early for kw in CHICKENPOX_KEYWORDS)
        
        # 水痘の症状の組み合わせ（発疹 + 水ぶくれ + かゆみ）
        symptom_names_early = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        has_rash_early = any("発疹" in name or "皮疹" in name for name in symptom_names_early)
        has_blister_early = any("水ぶくれ" in name or "水疱" in name for name in symptom_names_early)
        has_itch_early = any("かゆみ" in name or "痒み" in name for name in symptom_names_early)
        has_chickenpox_symptoms_early = (has_rash_early and has_blister_early) or (has_rash_early and has_itch_early) or (has_blister_early and has_itch_early)
        
        chickenpox_risk_early = has_chickenpox_keyword_early or has_chickenpox_symptoms_early
        
        if influenza_risk_early or chickenpox_risk_early:
            # 15歳未満かつインフルエンザ・水痘の疑いがある場合は完全に除外
            return {
                "total_score": 0.0,
                "score_breakdown": {
                    "symptom_match": 0.0,
                    "efficacy_specificity": 0.0,
                    "age_fit": 0.0,
                    "usage_convenience": 0.0,
                    "side_effect_risk": 0.0,
                    "interaction_risk": 0.0
                },
                "contraindication_reason": "アスピリン含有医薬品は、15歳未満のインフルエンザ・水痘患者ではライ症候群のリスクがあるため使用できません。",
                "contraindication_severity": "critical"
            }
    
    # 花粉症・アレルギー性鼻炎文脈（総合感冒薬ボーナス抑制・鼻炎用薬優先）
    _symptom_names_for_pollen = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
    _text_for_pollen = user_text or str(
        nlu_result.get("user_text")
        or nlu_result.get("original_user_text")
        or nlu_result.get("user_message")
        or ""
    )
    focus_pollen = is_pollen_rhinitis_focus(
        _text_for_pollen,
        _symptom_names_for_pollen,
        str(nlu_result.get("medicine_type") or ""),
    )

    # 各スコアを計算
    symptom_score = calculate_symptom_match_score(candidate, nlu_result)
    efficacy_specificity_score = calculate_efficacy_specificity_score(candidate, nlu_result)
    age_score = calculate_age_fit_score(candidate, user_info)
    usage_score = calculate_usage_convenience_score(candidate)
    side_effect_score = calculate_side_effect_risk_score(candidate, user_info)
    interaction_score = calculate_interaction_risk_score(candidate, user_info)
    
    # --- 2.0 強力な医薬品・信頼性の高い医薬品の評価と特化型ボーナス ---
    
    product_name = candidate.get('product_name', '')
    medicine_classification = candidate.get('classification', '')
    manufacturer = candidate.get('manufacturer', '')
    ingredients_str = str(candidate.get('ingredients', ''))
    
    # --- 判定ロジック ---
    is_strong_medicine = False
    strong_medicine_bonus = 0.0

    # A. 分類ボーナス（指定第1類、第1類は薬剤師の関与が必要な強力な薬が多い）
    if '指定第1類' in medicine_classification or '第1類' in medicine_classification:
        strong_medicine_bonus += 0.1

    # B. 成分ボーナス（大文字小文字を区別しない）
    ingredients_lower = ingredients_str.lower()
    if any(ingredient.lower() in ingredients_lower for ingredient in STRONG_INGREDIENTS):
        strong_medicine_bonus += 0.05

    # C. 製品ブランドボーナス（大文字小文字を区別しない、部分一致）
    product_name_lower = product_name.lower()
    if any(product.lower() in product_name_lower for product in STRONG_PRODUCTS):
        is_strong_medicine = True
        strong_medicine_bonus += 0.1

    # D. メーカー信頼度ボーナス（大文字小文字を区別しない、部分一致）
    manufacturer_lower = manufacturer.lower()
    if any(m.lower() in manufacturer_lower for m in TRUSTED_MANUFACTURERS):
        strong_medicine_bonus += 0.05
    
    # --- 【重要】特化型（スペシャリスト）判定 ---
    # ロキソニンなどが風邪薬に負けないための最重要ロジック
    # 成分数が少ない（例：5つ以下）＝ 特定の症状に特化して効く「シャープな薬」
    
    # 成分文字列の正規化と解析
    # 1. 前後の空白を除去
    ingredients_normalized = ingredients_str.strip()
    # 2. 小文字に統一
    ingredients_normalized = ingredients_normalized.lower()
    # 3. 正規表現で分割（カンマ、スペース、改行などに対応）
    # カンマ、カンマ+スペース、改行などで分割
    ingredient_list = re.split(r'[,，\s\n]+', ingredients_normalized)
    # 4. 空文字列を除外
    ingredient_list = [ing for ing in ingredient_list if ing.strip()]
    
    # 成分数のカウント
    ingredient_count = len(ingredient_list)
    
    # 特化型（スペシャリスト）判定（成分数が5つ以下）
    is_focused_medicine = ingredient_count <= 5
    
    # 特化型ボーナス（強力な医薬品かつ特化型の場合のみ+0.15）
    if is_strong_medicine and is_focused_medicine:
        # ブランド力があり、かつ特化型の薬には追加ボーナス
        # これにより「頭痛」単一症状などの場合に、総合風邪薬（成分多）より優先される
        strong_medicine_bonus += 0.15
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"特化型ブランド薬ボーナス適用: {product_name} (成分数: {ingredient_count})")
    
    # ボーナスの適用（上限 +0.3 に設定）
    strong_medicine_bonus_final = min(strong_medicine_bonus, 0.3)
    
    if DEBUG_MODE or logger.level <= logging.DEBUG and strong_medicine_bonus > 0:
        logger.debug(f"強力な医薬品ボーナス合計: {product_name} = +{strong_medicine_bonus_final} (成分数: {ingredient_count}, 特化型: {is_focused_medicine})")
    
    # --- 成人判定（変更なし） ---
    # 成人（15歳以上）には年齢制限のペナルティを適用しない
    # （既存の年齢制限ペナルティロジックで、15歳未満の場合のみペナルティを適用するようにする）
    
    # 期待される医薬品の基本スコアを底上げ（最低0.50を保証）（計画要件: スコアリングシステムの調整）
    # ただし、月経不順関連の症状がない場合（頭痛のみなど）は底上げしない
    priority_medicine_names = ["ラムールQ", "ラムールＱ", "ラムールq", "ラムールｑ", "加味逍遙散", "カミショウヨウサン", "命の母ホワイト", "命の母 ホワイト", "ルナエール", "ルナフェミン", "桂枝茯苓丸", "ケイシブクリョウガン"]
    # 厳密マッチング + 部分一致も許可（CSVデータの表記の違いに対応）
    is_priority_medicine = any(is_exact_product_match(product_name, [name]) or name in product_name for name in priority_medicine_names)
    
    if is_priority_medicine:
        # 月経不順関連の症状があるかチェック
        symptom_names = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        menstrual_symptoms = ["月経不順", "生理不順", "生理痛", "月経痛", "血の道症", "血の道"]
        has_menstrual_symptom = any(symptom in symptom_names for symptom in menstrual_symptoms)
        
        # 月経不順関連の症状がある場合のみ底上げを適用
        if has_menstrual_symptom:
            # 基本スコアを計算（症状マッチ、効能特異性、年齢適合性、用法簡便性の合計）
            base_score = (
                symptom_score * 0.30 +
                efficacy_specificity_score * 0.20 +
                age_score * 0.12 +
                usage_score * 0.03
            )
            
            # 基本スコアが0.50未満の場合は0.50に底上げ
            if base_score < 0.50:
                base_score_boost = 0.50 - base_score
                # 症状スコアに底上げ分を追加（症状マッチの重みが最も高いため）
                symptom_score += base_score_boost / 0.30
                logger.info(f"⭐ 期待される医薬品の基本スコアを底上げ: {product_name} = +{base_score_boost:.2f} (底上げ前: {base_score:.2f})")
        else:
            # 月経不順関連の症状がない場合（頭痛のみなど）は底上げしない
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"期待される医薬品の底上げをスキップ: {product_name} (月経不順関連の症状なし: {symptom_names})")
    
    # --- 2.1 ノーシンピュアの推奨条件の厳格化（小児用例外処理含む） ---
    # ノーシンピュア系医薬品の判定
    noshin_products = ["ノーシンピュア", "オトナノーシンピュア"]
    is_noshin_product = any(noshin_name in product_name for noshin_name in noshin_products)
    
    # 小児用ノーシンピュアの判定（例外処理用）
    is_pediatric_noshin = "小中学生用ノーシンピュア" in product_name or "小中学生用" in product_name
    ingredients_check = str(candidate.get('ingredients', '')).lower()
    has_acetaminophen_only = 'アセトアミノフェン' in ingredients_check and 'イブプロフェン' not in ingredients_check
    is_pediatric_exception = is_pediatric_noshin and has_acetaminophen_only
    
    noshin_penalty = 0.0
    has_menstrual_keyword = False
    has_menstrual_symptom = False
    
    if is_noshin_product and not is_pediatric_exception:
        # 生理痛関連キーワードのチェック（拡張版）
        menstrual_keywords = [
            "生理痛", "月経痛", "生理の痛み", "下腹部痛", "生理中",
            "月経不順", "生理不順", "生理", "月経"
        ]
        user_text_lower = user_text.lower() if user_text else ''
        has_menstrual_keyword = any(kw in user_text_lower for kw in menstrual_keywords)
        
        # 症状名からもチェック
        symptom_names_check = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        has_menstrual_symptom = any(
            any(kw in symptom_name.lower() for kw in menstrual_keywords)
            for symptom_name in symptom_names_check
        )
        
        if not (has_menstrual_keyword or has_menstrual_symptom):
            # 生理痛が明示されていない場合はペナルティを適用
            noshin_penalty = -0.5  # -0.3から-0.5に強化
            
            # 頭痛に対しては追加のペナルティを適用（ノーシンピュアは頭痛に不適切）
            symptom_names_check = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
            has_headache = any("頭痛" in symptom_name for symptom_name in symptom_names_check)
            if has_headache or "頭痛" in (user_text_lower if user_text else ''):
                noshin_penalty -= 0.2  # 頭痛に対して追加で-0.2（合計-0.7）
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"ノーシンピュア頭痛追加ペナルティ: {product_name} = -0.2 (頭痛に対して不適切)")
            
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"ノーシンピュアペナルティ: {product_name} = {noshin_penalty} (生理痛が明示されていない)")
    
    # 小児用ノーシンピュアの例外処理
    if is_pediatric_exception:
        # 小児用でアセトアミノフェンのみの場合は、生理痛キーワードがなくても軽減されたペナルティのみ
        # （通常の-0.3ではなく-0.1に軽減）
        if not (has_menstrual_keyword or has_menstrual_symptom):
            pediatric_noshin_penalty = -0.1  # 軽減されたペナルティ
            noshin_penalty = pediatric_noshin_penalty
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"小児用ノーシンピュア軽減ペナルティ: {product_name} = {pediatric_noshin_penalty}")
    
    # 部位マッチングスコアを計算
    user_body_part = nlu_result.get("user_body_part")
    body_part_score = calculate_body_part_match_score(candidate, user_body_part)
    
    # 症状特化型ブーストを計算
    symptom_boost = calculate_symptom_specific_boost(candidate, nlu_result, user_info)
    
    # ユーザー要望に基づくボーナス
    user_preference_bonus = 0.0
    if user_info and user_info.get('user_preferences'):
        user_preferences = user_info.get('user_preferences')
        user_preference_bonus = apply_user_preference_bonus(candidate, user_preferences, nlu_result)
        if user_preference_bonus > 0:
            logger.info(f"💊 ユーザー要望ボーナス: {candidate.get('product_name', '')} = +{user_preference_bonus:.2f}")
    
    # --- 2.4 痛みフラグボーナスの条件付き適用（既存コードの修正） ---
    # 痛みフラグボーナス（解熱鎮痛剤への独立したボーナス）
    pain_flag_bonus = 0.0
    medicine_type = candidate.get("medicine_type", "")
    if '解熱鎮痛薬' in medicine_type:
        # ユーザー発話に「痛い」「激痛」「生理痛」が含まれる場合
        user_message = user_text or user_info.get('user_message', '') or ''
        user_message_lower = user_message.lower() if user_message else ''
        pain_keywords = ['痛い', '激痛', '生理痛', '月経痛', '腹痛', 'お腹の痛み', '下腹部痛', '痛み', '痛む']
        
        if any(kw in user_message_lower for kw in pain_keywords):
            # 生理痛の場合はボーナスを維持
            menstrual_keywords = ['生理痛', '月経痛', '生理の痛み', '下腹部痛']
            is_menstrual_pain = any(kw in user_message_lower for kw in menstrual_keywords)
            
            # 症状名からもチェック
            symptom_names_pain = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
            has_menstrual_symptom_pain = any(
                any(kw in symptom_name.lower() for kw in menstrual_keywords)
                for symptom_name in symptom_names_pain
            )
            
            if is_menstrual_pain or has_menstrual_symptom_pain:
                pain_flag_bonus = 0.3
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"痛みフラグボーナス（生理痛）: {product_name} = +0.3")
            # それ以外の痛みは削除（アセトアミノフェンボーナスやNSAIDsボーナスに置き換える）
    
    # --- 2.2 アセトアミノフェン含有医薬品へのボーナス追加（炎症系除外） ---
    # アセトアミノフェン含有医薬品へのボーナス
    ingredients_acetaminophen = str(candidate.get('ingredients', '')).lower()
    has_acetaminophen = 'アセトアミノフェン' in ingredients_acetaminophen
    has_ibuprofen = 'イブプロフェン' in ingredients_acetaminophen
    
    acetaminophen_bonus = 0.0
    # アセトアミノフェンのみを含む医薬品（イブプロフェンを含まない）
    if has_acetaminophen and not has_ibuprofen:
        symptom_names_acetaminophen = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        user_text_lower_acetaminophen = user_text.lower() if user_text else ''
        
        # アセトアミノフェンが得意な領域（ボーナス大 +0.3）
        high_match_symptoms = ["頭痛", "発熱", "熱", "悪寒"]
        has_high_match = any(
            any(symptom in symptom_name for symptom in high_match_symptoms)
            for symptom_name in symptom_names_acetaminophen
        )
        
        # 炎症を伴う痛み（NSAIDsの方が適切）
        inflammatory_symptoms = ["筋肉痛", "関節痛", "腰痛", "打撲", "ねんざ", "腱鞘炎"]
        has_inflammatory_pain = any(
            any(symptom in symptom_name for symptom in inflammatory_symptoms)
            for symptom_name in symptom_names_acetaminophen
        )
        
        # 炎症キーワードのチェック
        inflammation_keywords = ["腫れている", "熱を持っている", "炎症"]
        has_inflammation_keyword = any(kw in user_text_lower_acetaminophen for kw in inflammation_keywords)
        
        # 生理痛は除外（ノーシンピュアが適切）
        menstrual_keywords_acetaminophen = ["生理痛", "月経痛", "生理の痛み", "下腹部痛"]
        has_menstrual_pain_acetaminophen = any(
            any(kw in symptom_name.lower() for kw in menstrual_keywords_acetaminophen)
            for symptom_name in symptom_names_acetaminophen
        ) or any(kw in user_text_lower_acetaminophen for kw in menstrual_keywords_acetaminophen)
        
        # 胃への配慮のチェック
        stomach_concern_keywords = [
            "胃が痛い", "胃もたれ", "胃潰瘍", "胃炎", "胃が弱い", 
            "胃が心配", "空腹時", "胃腸が弱い"
        ]
        has_stomach_concern = any(kw in user_text_lower_acetaminophen for kw in stomach_concern_keywords)
        
        # アセトアミノフェンボーナスの適用
        if has_high_match and not has_inflammatory_pain and not has_inflammation_keyword and not has_menstrual_pain_acetaminophen:
            acetaminophen_bonus = 0.4  # 0.3から0.4に強化（カロナールAなどをより推奨）
            # 胃への配慮が検出された場合は追加ボーナス
            if has_stomach_concern:
                acetaminophen_bonus += 0.1  # 合計+0.5
            # カロナールAなどの有名な製品には追加ボーナス
            if 'カロナール' in product_name or 'タイレノール' in product_name:
                acetaminophen_bonus += 0.1  # 合計+0.5または+0.6
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"カロナール/タイレノール追加ボーナス: {product_name} = +0.1")
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"アセトアミノフェンボーナス: {product_name} = +{acetaminophen_bonus}")
    
    # --- 主要解熱鎮痛薬の追加ボーナス（強化版） ---
    # カロナールA、ロキソニンS、タイレノールを第一選択として推奨
    major_analgesic_bonus = 0.0
    product_name_norm = normalize_medicine_name_to_hankaku(product_name)
    is_major_analgesic = any(
        normalize_medicine_name_to_hankaku(major_name) in product_name_norm
        for major_name in MAJOR_ANALGESIC_MEDICINES
    )
    
    if is_major_analgesic:
        # 風邪薬は主要解熱鎮痛薬ボーナスを受けない（総合感冒薬は除外）
        if is_comprehensive_cold_medicine(candidate):
            major_analgesic_bonus = 0.0
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"風邪薬のため主要解熱鎮痛薬ボーナスを適用しない: {product_name}")
        else:
            symptom_names_major = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
            
            # 主要解熱鎮痛薬は効能効果チェックをスキップしてボーナスを付与（第一選択として推奨）
            # 頭痛・発熱に対する第一選択として追加ボーナス
            has_headache_or_fever = any(
                any(symptom in symptom_name for symptom in ['頭痛', '発熱', '熱'])
                for symptom_name in symptom_names_major
            )
            
            # カロナールA、タイレノールの場合（頭痛・発熱の第一選択）
            if has_headache_or_fever and ('カロナール' in product_name or 'タイレノール' in product_name):
                major_analgesic_bonus = 0.8  # 0.6から0.8に強化（総合感冒薬のスコアを確実に上回るように）
                logger.info(f"⭐ 主要解熱鎮痛薬ボーナス（カロナール/タイレノール）: {product_name} = +{major_analgesic_bonus}")
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"主要解熱鎮痛薬ボーナス（カロナール/タイレノール）: {product_name} = +{major_analgesic_bonus}")
            
            # 筋肉痛・関節痛・腰痛に対するロキソニンSのボーナス
            has_muscle_pain = any(
                any(symptom in symptom_name for symptom in ['筋肉痛', '関節痛', '腰痛'])
                for symptom_name in symptom_names_major
            )
            if has_muscle_pain and 'ロキソニン' in product_name:
                # 外用薬（テープ・ゲル・パップなど）の場合は追加ボーナス（筋肉痛には湿布が適切）
                is_topical = any(kw in product_name for kw in ['テープ', 'ゲル', 'パップ', 'ローション'])
                if is_topical:
                    major_analgesic_bonus = max(major_analgesic_bonus, 0.8)  # 外用薬は内服薬より優先（0.6 → 0.8に強化）
                    logger.info(f"⭐ 主要解熱鎮痛薬ボーナス（ロキソニン・筋肉痛・外用薬）: {product_name} = +{major_analgesic_bonus}")
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"主要解熱鎮痛薬ボーナス（ロキソニン・筋肉痛・外用薬）: {product_name} = +{major_analgesic_bonus}")
                else:
                    major_analgesic_bonus = max(major_analgesic_bonus, 0.6)  # 内服薬も適切だが、外用薬を優先（0.5 → 0.6に強化）
                    logger.info(f"⭐ 主要解熱鎮痛薬ボーナス（ロキソニン・筋肉痛）: {product_name} = +{major_analgesic_bonus}")
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"主要解熱鎮痛薬ボーナス（ロキソニン・筋肉痛）: {product_name} = +{major_analgesic_bonus}")
            
            # 頭痛・発熱に対するロキソニンSのボーナス（筋肉痛がない場合）
            elif has_headache_or_fever and 'ロキソニン' in product_name:
                major_analgesic_bonus = max(major_analgesic_bonus, 0.6)  # 頭痛・発熱に対するボーナス（0.4 → 0.6に強化）
                logger.info(f"⭐ 主要解熱鎮痛薬ボーナス（ロキソニン・頭痛/発熱）: {product_name} = +{major_analgesic_bonus}")
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"主要解熱鎮痛薬ボーナス（ロキソニン・頭痛/発熱）: {product_name} = +{major_analgesic_bonus}")
            
            # イブ、ブファリンの場合（頭痛・発熱の第一選択）
            elif has_headache_or_fever and any(kw in product_name for kw in ['イブ', 'EVE', 'ブファリン', 'バファリン']):
                major_analgesic_bonus = max(major_analgesic_bonus, 0.7)  # カロナール/タイレノールに次ぐ優先度
                logger.info(f"⭐ 主要解熱鎮痛薬ボーナス（イブ/ブファリン）: {product_name} = +{major_analgesic_bonus}")
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"主要解熱鎮痛薬ボーナス（イブ/ブファリン）: {product_name} = +{major_analgesic_bonus}")
    
    # --- 2.3 NSAIDs（イブプロフェン、ロキソプロフェンなど）へのボーナス追加 ---
    # NSAIDs含有医薬品へのボーナス
    nsaids_ingredients = ["イブプロフェン", "ロキソプロフェン", "アスピリン", "インドメタシン"]
    has_nsaids = any(nsaid.lower() in ingredients_acetaminophen for nsaid in nsaids_ingredients)
    
    nsaids_bonus = 0.0
    if has_nsaids:
        symptom_names_nsaids = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        user_text_lower_nsaids = user_text.lower() if user_text else ''
        
        # 炎症を伴う症状
        inflammatory_symptoms_nsaids = ["筋肉痛", "関節痛", "腰痛", "打撲", "ねんざ", "腱鞘炎"]
        has_inflammatory_symptom = any(
            any(symptom in symptom_name for symptom in inflammatory_symptoms_nsaids)
            for symptom_name in symptom_names_nsaids
        )
        
        # 炎症キーワードのチェック
        inflammation_keywords_nsaids = ["腫れている", "熱を持っている", "炎症"]
        has_inflammation_keyword_nsaids = any(kw in user_text_lower_nsaids for kw in inflammation_keywords_nsaids)
        
        # 痛みの強度キーワード（拡張版）
        pain_severity_keywords = [
            "激痛", "激しい痛み", "強い痛み", "ズキズキ", "脈打つような痛み",
            "割れそう", "耐えられない", "ひどい痛み"
        ]
        has_severe_pain = any(kw in user_text_lower_nsaids for kw in pain_severity_keywords)
        
        # 炎症が検出された場合
        if has_inflammatory_symptom or has_inflammation_keyword_nsaids:
            nsaids_bonus = 0.2
            # 強い痛みの場合は追加ボーナス
            if has_severe_pain:
                nsaids_bonus += 0.1  # 合計+0.3
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"NSAIDsボーナス: {product_name} = +{nsaids_bonus}")
    
    # 複数症状の組み合わせによるボーナス（MULTI_SYMPTOM_COMBINATIONSから）
    multi_symptom_bonus = 0.0
    symptoms = nlu_result.get("symptoms", [])
    symptom_names = [s.get("name") for s in symptoms]
    if len(symptom_names) >= 2:
        medicine_type = candidate.get("medicine_type", "")
        for combo in combinations(symptom_names, 2):
            combo_key = frozenset(combo)
            adjustments = MULTI_SYMPTOM_COMBINATIONS.get(combo_key)
            if adjustments and medicine_type in adjustments:
                adjustment = adjustments[medicine_type]
                # ボーナス（正の値）のみを適用
                if adjustment > 0.0:
                    multi_symptom_bonus += adjustment
                    symptom_boost += adjustment
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(
                            f"複数症状ボーナス: {combo_key} × {medicine_type} = {adjustment:+.2f}"
                        )
    
    # アレルギー成分チェック
    is_allergic, allergy_ingredient = check_allergy_contraindication(candidate, user_info)
    if is_allergic:
        # アレルギー成分がある場合はスコアを0に設定
        return {
            "total_score": 0.0,
            "score_breakdown": {
                "symptom_match": 0.0,
                "efficacy_specificity": 0.0,
                "age_fit": 0.0,
                "usage_convenience": 0.0,
                "side_effect_risk": 0.0,
                "interaction_risk": 0.0
            },
            "allergy_warning": f"アレルギー成分 '{allergy_ingredient}' が含まれています"
        }
    
    # 相互作用チェック
    has_interaction, interaction_warnings = check_drug_interactions(candidate, user_info)
    if has_interaction:
        # 相互作用がある場合は大幅減点
        interaction_score = min(interaction_score, -0.5)
    
    # 症状特異性ペナルティを計算
    symptom_specificity_penalty = calculate_symptom_specificity_penalty(candidate, nlu_result)
    
    # --- 2.5 NSAIDs全般への条件付きペナルティ（15歳未満禁止成分の範囲拡大、胃薬成分考慮） ---
    # 15歳未満使用不可、または慎重投与のNSAIDs成分リスト（拡張版）
    adult_only_nsaids = [
        "イブプロフェン", "ロキソプロフェン", "アスピリン", "アセチルサリチル酸", 
        "インドメタシン", "メフェナム酸", "ジクロフェナク", "ナプロキセン", 
        "ケトプロフェン", "メロキシカム", "ピロキシカム"
    ]
    ingredients_str_nsaids = str(candidate.get('ingredients', '')).lower()
    has_adult_nsaid = any(nsaid.lower() in ingredients_str_nsaids for nsaid in adult_only_nsaids)
    
    nsaid_penalty = 0.0
    if has_adult_nsaid:
        total_penalty = 0.0  # 複数のNSAIDsが含まれている場合の合計ペナルティ
        
        # 各NSAIDs成分のペナルティ値を定義
        nsaid_penalty_values = {
            "イブプロフェン": -0.2,
            "ロキソプロフェン": -0.2,
            "アスピリン": -0.3,  # インフルエンザ・水痘がない場合
            "アセチルサリチル酸": -0.3,  # インフルエンザ・水痘がない場合
            "インドメタシン": -0.2,
            "メフェナム酸": -0.2,
            "ジクロフェナク": -0.2,
            "ナプロキセン": -0.2,
            "ケトプロフェン": -0.2,
            "メロキシカム": -0.2,
            "ピロキシカム": -0.2
        }
        
        # アスピリン含有のチェック
        has_aspirin = 'アスピリン' in ingredients_str_nsaids or 'アセチルサリチル酸' in ingredients_str_nsaids
        
        # インフルエンザ・水痘の疑いの検出（既存のロジックを拡張）
        # 既存のinfluenza_riskフラグを使用
        influenza_risk = nlu_result.get('influenza_risk', False) or False
        
        # 水痘の疑いの検出（キーワードと症状の両方をチェック）
        user_text_lower_nsaids = user_text.lower() if user_text else ''
        has_chickenpox_keyword = any(kw in user_text_lower_nsaids for kw in CHICKENPOX_KEYWORDS)
        
        # 水痘の症状の組み合わせ（発疹 + 水ぶくれ + かゆみ）
        symptom_names_nsaids_penalty = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        has_rash = any("発疹" in name or "皮疹" in name for name in symptom_names_nsaids_penalty)
        has_blister = any("水ぶくれ" in name or "水疱" in name for name in symptom_names_nsaids_penalty)
        has_itch = any("かゆみ" in name or "痒み" in name for name in symptom_names_nsaids_penalty)
        has_chickenpox_symptoms = (has_rash and has_blister) or (has_rash and has_itch) or (has_blister and has_itch)
        
        chickenpox_risk = has_chickenpox_keyword or has_chickenpox_symptoms
        
        # アスピリンの特別処理（インフルエンザ・水痘の疑いがある場合は完全に除外）
        if has_aspirin:
            if (influenza_risk or chickenpox_risk) and user_info and user_info.get('age') and user_info.get('age') < 15:
                # 15歳未満かつインフルエンザ・水痘の疑いがある場合は完全に除外
                return {
                    "total_score": 0.0,
                    "score_breakdown": {
                        "symptom_match": 0.0,
                        "efficacy_specificity": 0.0,
                        "age_fit": 0.0,
                        "usage_convenience": 0.0,
                        "side_effect_risk": 0.0,
                        "interaction_risk": 0.0
                    },
                    "contraindication_reason": "アスピリン含有医薬品は、15歳未満のインフルエンザ・水痘患者ではライ症候群のリスクがあるため使用できません。",
                    "contraindication_severity": "critical"
                }
        
        # 胃を守る成分のチェック
        stomach_guard_ingredients = [
            "酸化マグネシウム", "乾燥水酸化アルミニウムゲル", 
            "合成ヒドロタルサイト", "メタケイ酸アルミン酸マグネシウム",
            "水酸化マグネシウム"
        ]
        has_stomach_guard = any(guard.lower() in ingredients_str_nsaids for guard in stomach_guard_ingredients)
        
        # 年齢ベースのペナルティ（15歳未満）
        if user_info and user_info.get('age'):
            age = user_info.get('age')
            if age < 15:
                # 各NSAIDs成分のペナルティを計算
                for nsaid, penalty_value in nsaid_penalty_values.items():
                    if nsaid.lower() in ingredients_str_nsaids:
                        # アスピリンの場合は特別処理（インフルエンザ・水痘がない場合のみペナルティ）
                        if nsaid in ["アスピリン", "アセチルサリチル酸"]:
                            if not (influenza_risk or chickenpox_risk):
                                total_penalty += penalty_value
                        else:
                            total_penalty += penalty_value
                
                # ペナルティの合計に上限を設定（-0.5を超える場合はスコアを0にする）
                if total_penalty < -0.5:
                    return {
                        "total_score": 0.0,
                        "score_breakdown": {
                            "symptom_match": 0.0,
                            "efficacy_specificity": 0.0,
                            "age_fit": 0.0,
                            "usage_convenience": 0.0,
                            "side_effect_risk": 0.0,
                            "interaction_risk": 0.0
                        },
                        "contraindication_reason": "15歳未満で使用不可のNSAIDs成分が複数含まれています。",
                        "contraindication_severity": "critical"
                    }
                
                nsaid_penalty = total_penalty
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"NSAIDsペナルティ（年齢）: {product_name} = {nsaid_penalty} (年齢: {age}歳)")
        
        # ユーザー情報ベースのペナルティ（胃腸が弱い、胃潰瘍など）
        if user_info:
            stomach_conditions = [
                '胃腸が弱い', '胃潰瘍', '胃痛', '胃炎', '胃もたれ',
                '胃が弱い', '胃が心配', '空腹時'
            ]
            user_conditions = user_info.get('conditions', []) or []
            has_stomach_condition = any(
                condition in str(user_conditions).lower() or 
                condition in str(user_info).lower() or
                condition in user_text_lower_nsaids
                for condition in stomach_conditions
            )
            
            if has_stomach_condition:
                base_penalty = -0.4  # 胃が弱いのにNSAIDsは原則避けるべきなので強めに
                # 胃薬成分が配合されている場合、かつインフルエンザ・水痘がない場合はペナルティを軽減
                if has_stomach_guard and not (influenza_risk or chickenpox_risk):
                    base_penalty = -0.2  # 胃薬配合なら許容範囲内としてペナルティ軽減（-0.2軽減）
                nsaid_penalty = max(nsaid_penalty, base_penalty)  # より大きいペナルティを適用
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"NSAIDsペナルティ（胃腸）: {product_name} = {base_penalty} (胃薬成分: {has_stomach_guard}, インフルエンザ・水痘リスク: {influenza_risk or chickenpox_risk})")
    
    # --- 2.6 速効性要求への対応（液体カプセルボーナス） ---
    # 速効性要求の検出
    speed_keywords = [
        "速攻", "すぐ", "早く", "即効性", "すぐに効く", 
        "早く治したい", "急いでいる", "すぐ効く"
    ]
    user_text_lower_speed = user_text.lower() if user_text else ''
    has_speed_requirement = any(kw in user_text_lower_speed for kw in speed_keywords)
    
    speed_bonus = 0.0
    if has_speed_requirement:
        # 液体カプセルや溶解の早い製剤の判定
        product_name_lower_speed = product_name.lower()
        usage_speed = str(candidate.get('usage', '')).lower()
        medicine_type_speed = candidate.get('medicine_type', '').lower()
        
        # 液体カプセル、カプセル、顆粒などの判定
        is_fast_dissolving = any(
            form in product_name_lower_speed or form in usage_speed or form in medicine_type_speed
            for form in ['液体', 'カプセル', '顆粒', 'ドリンク', '液剤']
        )
        
        if is_fast_dissolving:
            speed_bonus = 0.1
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"速効性ボーナス: {product_name} = +{speed_bonus}")
    
    # リスク成分の減点（複数症状の場合は減点のみ、単一症状の場合は既に除外済み）
    risk_penalty = 0.0
    if candidate.get('risk_ingredient'):
        risk_penalty = candidate.get('risk_penalty', -0.3)
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"リスク成分ペナルティ: {candidate.get('risk_ingredient')} = {risk_penalty}")
    
    # 症状パターンマッチングによる最適化ボーナス/ペナルティ
    pattern_bonus = 0.0
    # 単一症状の場合はpattern_bonusを適用しない（特化薬を優先するため）
    symptom_names = [s.get("name") for s in nlu_result.get("symptoms", [])]
    is_single_symptom_for_pattern = len(symptom_names) == 1
    pattern_info = None
    if not is_single_symptom_for_pattern:
        pattern_info = match_symptom_pattern(nlu_result)
    if pattern_info:
        bonuses = pattern_info.get("bonuses", {})
        penalties = pattern_info.get("penalties", {})
        product_name = candidate.get('product_name', '')
        efficacy = str(candidate.get('efficacy', ''))
        ingredients = str(candidate.get('ingredients', '')).lower()
        medicine_type = candidate.get('medicine_type', '')
        throat_specificity_level = candidate.get('throat_specificity_level', 'none')
        symptom_names = [s.get("name") for s in nlu_result.get("symptoms", [])]
        
        # 総合感冒薬（喉向き）のボーナス
        if "総合感冒薬（喉向き・成分あり）" in bonuses and throat_specificity_level == "component_and_efficacy":
            pattern_bonus += bonuses["総合感冒薬（喉向き・成分あり）"]
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"症状パターンボーナス（総合感冒薬・喉向き・成分あり）: {product_name} = +{bonuses['総合感冒薬（喉向き・成分あり）']}")
        elif "総合感冒薬（喉向き・効能のみ）" in bonuses and throat_specificity_level == "efficacy_only":
            pattern_bonus += bonuses["総合感冒薬（喉向き・効能のみ）"]
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"症状パターンボーナス（総合感冒薬・喉向き・効能のみ）: {product_name} = +{bonuses['総合感冒薬（喉向き・効能のみ）']}")
        
        # 五苓散の識別とボーナス
        if "五苓散" in bonuses:
            if "五苓散" in product_name or "五苓散" in ingredients:
                pattern_bonus += bonuses["五苓散"]
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンボーナス（五苓散）: {product_name} = +{bonuses['五苓散']}")
        
        # L-システイン含有医薬品の識別とボーナス
        if "L-システイン含有医薬品" in bonuses:
            if "l-システイン" in ingredients or "システイン" in ingredients:
                pattern_bonus += bonuses["L-システイン含有医薬品"]
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンボーナス（L-システイン含有）: {product_name} = +{bonuses['L-システイン含有医薬品']}")
        
        # 生薬配合の胃腸薬の識別とボーナス
        if "生薬配合の胃腸薬" in bonuses:
            if '胃腸薬' in medicine_type:
                # 生薬成分のキーワード
                herbal_ingredients = ["ショウキョウ", "オウバク", "サンショウ", "カンゾウ", "ケイヒ", "ニンジン", "ブクリョウ"]
                has_herbal = any(herb.lower() in ingredients for herb in herbal_ingredients)
                if has_herbal:
                    pattern_bonus += bonuses["生薬配合の胃腸薬"]
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"症状パターンボーナス（生薬配合の胃腸薬）: {product_name} = +{bonuses['生薬配合の胃腸薬']}")
        
        # 加味逍遙散の識別とボーナス（月経不順+イライラ）
        if "加味逍遙散" in bonuses:
            # 製品名マッチング（厳密マッチング + 部分一致も許可）
            kamishoyosan_names = ["加味逍遙散", "カミショウヨウサン", "加味逍遙散エキス", "加味逍遙散エキス顆粒"]
            has_kamishoyosan_name = is_exact_product_match(product_name, kamishoyosan_names)
            
            # 厳密マッチングで見つからない場合、部分一致も試す
            if not has_kamishoyosan_name:
                for kamishoyosan_name in kamishoyosan_names:
                    if kamishoyosan_name in product_name:
                        has_kamishoyosan_name = True
                        logger.debug(f"加味逍遙散を部分一致で検出: {product_name} (検索名: {kamishoyosan_name})")
                        break
            
            # 製品名がマッチした場合にボーナス適用
            if has_kamishoyosan_name:
                pattern_bonus += bonuses["加味逍遙散"]
                logger.info(f"⭐ 症状パターンボーナス（加味逍遙散）: {product_name} = +{bonuses['加味逍遙散']}")
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンボーナス（加味逍遙散）: {product_name} = +{bonuses['加味逍遙散']}")
        
        # 命の母ホワイトの識別とボーナス（月経不順+イライラ）
        if "命の母ホワイト" in bonuses:
            # 製品名マッチング（厳密マッチング + 部分一致も許可）
            inochi_no_haha_white_names = ["命の母ホワイト", "命の母 ホワイト", "命の母ホワイト錠"]
            has_inochi_no_haha_white_name = is_exact_product_match(product_name, inochi_no_haha_white_names)
            
            # 厳密マッチングで見つからない場合、部分一致も試す
            if not has_inochi_no_haha_white_name:
                for inochi_name in inochi_no_haha_white_names:
                    if inochi_name in product_name:
                        has_inochi_no_haha_white_name = True
                        logger.debug(f"命の母ホワイトを部分一致で検出: {product_name} (検索名: {inochi_name})")
                        break
            
            # 製品名がマッチした場合にボーナス適用
            if has_inochi_no_haha_white_name:
                pattern_bonus += bonuses["命の母ホワイト"]
                logger.info(f"⭐ 症状パターンボーナス（命の母ホワイト）: {product_name} = +{bonuses['命の母ホワイト']}")
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンボーナス（命の母ホワイト）: {product_name} = +{bonuses['命の母ホワイト']}")
        
        # 当帰芍薬散の識別とボーナス（月経不順+冷え症）
        if "当帰芍薬散" in bonuses:
            if "当帰芍薬散" in product_name or "トウキシャクヤクサン" in product_name.upper() or "当帰芍薬散" in efficacy:
                pattern_bonus += bonuses["当帰芍薬散"]
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンボーナス（当帰芍薬散）: {product_name} = +{bonuses['当帰芍薬散']}")
        
        # 桂枝茯苓丸の識別とボーナス（月経不順+ニキビ、または月経不順+イライラ）
        if "桂枝茯苓丸" in bonuses:
            # 製品名マッチング（厳密マッチング + 部分一致も許可）
            keishibukuryogan_names = ["桂枝茯苓丸", "ケイシブクリョウガン", "桂枝茯苓丸エキス", "桂枝茯苓丸エキス顆粒"]
            has_keishibukuryogan_name = is_exact_product_match(product_name, keishibukuryogan_names)
            
            # 厳密マッチングで見つからない場合、部分一致も試す
            if not has_keishibukuryogan_name:
                for keishi_name in keishibukuryogan_names:
                    if keishi_name in product_name:
                        has_keishibukuryogan_name = True
                        logger.debug(f"桂枝茯苓丸を部分一致で検出: {product_name} (検索名: {keishi_name})")
                        break
            
            # 効能に「月経不順」「血の道症」が含まれる製品を優先（「打撲症」のみの製品は除外）
            has_menstrual_efficacy = "月経不順" in efficacy or "血の道症" in efficacy or "生理不順" in efficacy
            only_daposho = "打撲症" in efficacy and not has_menstrual_efficacy
            
            # 製品名がマッチし、かつ打撲症のみでない場合にボーナス適用
            if has_keishibukuryogan_name and not only_daposho:
                # 月経不順・血の道症が含まれる場合は追加ボーナス
                if has_menstrual_efficacy:
                    pattern_bonus += bonuses["桂枝茯苓丸"] + 0.05  # 追加ボーナス
                    logger.info(f"⭐ 症状パターンボーナス（桂枝茯苓丸・月経不順あり）: {product_name} = +{bonuses['桂枝茯苓丸'] + 0.05}")
                else:
                    pattern_bonus += bonuses["桂枝茯苓丸"]
                    logger.info(f"⭐ 症状パターンボーナス（桂枝茯苓丸）: {product_name} = +{bonuses['桂枝茯苓丸']}")
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンボーナス（桂枝茯苓丸）: {product_name} = +{bonuses['桂枝茯苓丸']} (効能: {efficacy[:100]}...)")
        
        # ラムールQの識別とボーナス（月経不順+イライラ）
        if "ラムールQ" in bonuses:
            # 製品名マッチング（厳密マッチング + 部分一致も許可）
            ramuruq_names = ["ラムールQ", "ラムールＱ", "ラムールq", "ラムールｑ"]
            has_ramuruq_name = is_exact_product_match(product_name, ramuruq_names)
            
            # 厳密マッチングで見つからない場合、部分一致も試す（CSVデータの表記の違いに対応）
            if not has_ramuruq_name:
                product_name_lower = product_name.lower()
                for ramuruq_name in ramuruq_names:
                    if ramuruq_name.lower() in product_name_lower:
                        has_ramuruq_name = True
                        logger.debug(f"ラムールQを部分一致で検出: {product_name} (検索名: {ramuruq_name})")
                        break
            
            # 製品名がマッチした場合にボーナス適用
            if has_ramuruq_name:
                pattern_bonus += bonuses["ラムールQ"]
                logger.info(f"⭐ 症状パターンボーナス（ラムールQ）: {product_name} = +{bonuses['ラムールQ']}")
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンボーナス（ラムールQ）: {product_name} = +{bonuses['ラムールQ']}")
        
        # ルナエールの識別とボーナス（月経不順+イライラ、錠剤タイプ）
        if "ルナエール" in bonuses:
            # 製品名マッチング（厳密マッチング + 部分一致も許可）
            luna_elle_names = ["ルナエール", "ルナエール錠"]
            has_luna_elle_name = is_exact_product_match(product_name, luna_elle_names)
            
            # 厳密マッチングで見つからない場合、部分一致も試す
            if not has_luna_elle_name:
                for luna_name in luna_elle_names:
                    if luna_name in product_name:
                        has_luna_elle_name = True
                        logger.debug(f"ルナエールを部分一致で検出: {product_name} (検索名: {luna_name})")
                        break
            
            if has_luna_elle_name:
                pattern_bonus += bonuses["ルナエール"]
                logger.info(f"⭐ 症状パターンボーナス（ルナエール）: {product_name} = +{bonuses['ルナエール']}")
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンボーナス（ルナエール）: {product_name} = +{bonuses['ルナエール']}")
        
        # ルナフェミンの識別とボーナス（月経不順+イライラ、錠剤タイプ）
        if "ルナフェミン" in bonuses:
            # 製品名マッチング（厳密マッチング + 部分一致も許可）
            luna_femin_names = ["ルナフェミン", "ルナフェミン錠"]
            has_luna_femin_name = is_exact_product_match(product_name, luna_femin_names)
            
            # 厳密マッチングで見つからない場合、部分一致も試す
            if not has_luna_femin_name:
                for luna_name in luna_femin_names:
                    if luna_name in product_name:
                        has_luna_femin_name = True
                        logger.debug(f"ルナフェミンを部分一致で検出: {product_name} (検索名: {luna_name})")
                        break
            
            if has_luna_femin_name:
                pattern_bonus += bonuses["ルナフェミン"]
                logger.info(f"⭐ 症状パターンボーナス（ルナフェミン）: {product_name} = +{bonuses['ルナフェミン']}")
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンボーナス（ルナフェミン）: {product_name} = +{bonuses['ルナフェミン']}")
        
        # 「イライラ」症状への対応強化：効能効果欄に「ヒステリー」「情緒不安定」「更年期神経症」などのキーワードが含まれる医薬品にボーナス
        if "月経不順" in symptom_names and "イライラ" in symptom_names:
            irritability_keywords = ["ヒステリー", "情緒不安定", "更年期神経症", "更年期障害", "神経症状"]
            efficacy_lower = efficacy.lower()
            has_irritability_keyword = any(keyword in efficacy_lower for keyword in irritability_keywords)
            if has_irritability_keyword:
                irritability_boost = 0.12  # イライラ症状への対応ボーナス
                pattern_bonus += irritability_boost
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"イライラ症状対応ボーナス: {product_name} = +{irritability_boost} (効能: {efficacy[:100]}...)")
        
        # 葛根湯の識別とペナルティ（「のどの痛み+発熱」の場合はペナルティを適用）
        if "葛根湯" in bonuses:
            # 葛根湯の判定：製品名または成分から判定
            is_kampo_check = _is_kampo_or_herbal_medicine(candidate)
            is_kakkonto_by_name = "葛根湯" in product_name
            # 成分から葛根湯を判定（カッコン、カンゾウ、ケイヒ、タイソウ、ショウキョウ、シャクヤク、マオウ）
            kakkonto_keywords = ["カッコン", "カンゾウ", "ケイヒ", "タイソウ", "ショウキョウ", "シャクヤク", "マオウ"]
            ingredients_normalized_check = normalize_text(ingredients)
            has_kakkonto_ingredients_check = sum(1 for kw in kakkonto_keywords if normalize_text(kw.lower()) in ingredients_normalized_check) >= 5  # 主要成分の5つ以上が含まれていれば葛根湯
            is_kakkonto_check = is_kakkonto_by_name or (is_kampo_check and has_kakkonto_ingredients_check)
            if is_kampo_check and is_kakkonto_check:
                # 「のどの痛み+発熱」の場合はペナルティを適用（総合感冒薬を優先）
                symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
                has_throat = any("のど" in name or "喉" in name or "咽頭" in name for name in symptom_names_list)
                has_fever_symptom = "発熱" in symptom_names_list
                if has_throat and has_fever_symptom and len(symptom_names_list) >= 2:
                    # 「のどの痛み+発熱」の場合はペナルティを適用
                    pattern_bonus += bonuses["葛根湯"]  # bonuses["葛根湯"]は-0.1なので、ペナルティとして適用
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"症状パターンペナルティ（葛根湯・のど痛み+発熱）: {product_name} = {bonuses['葛根湯']}")
                else:
                    # その他の症状パターンの場合は通常通り
                    pattern_bonus += bonuses["葛根湯"]
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"症状パターンボーナス（葛根湯）: {product_name} = +{bonuses['葛根湯']}")
        
        # 医薬品種類ごとのボーナス
        for med_type, bonus_value in bonuses.items():
            if med_type in medicine_type:
                pattern_bonus += bonus_value
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンボーナス（{med_type}）: {product_name} = +{bonus_value}")
        
        # 単一症状（発熱のみ）の場合、解熱鎮痛薬にボーナスを付与、総合感冒薬にペナルティ
        symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        is_single_symptom = len(symptom_names_list) == 1
        if is_single_symptom and "発熱" in symptom_names_list:
            if '解熱鎮痛薬' in medicine_type:
                pattern_bonus += 0.3  # 単一症状（発熱のみ）の場合、解熱鎮痛薬を優先
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"詳細スコアリング pattern_bonus適用（単一症状・発熱）: medicine_type=解熱鎮痛薬, product_name={product_name}, pattern_bonus={pattern_bonus}")
            elif '風邪薬' in medicine_type:
                pattern_bonus -= 0.2  # 単一症状（発熱のみ）の場合、総合感冒薬にペナルティ
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"詳細スコアリング pattern_bonus適用（単一症状・発熱）: medicine_type=風邪薬, product_name={product_name}, pattern_bonus={pattern_bonus}")
        
        # リスク成分のペナルティ（便秘薬のセンナ、ヒマシ油など）
        if "リスク成分（センナ、ヒマシ油）" in penalties:
            if "センナ" in ingredients or "ヒマシ油" in ingredients or "カストル油" in ingredients:
                risk_penalty += penalties["リスク成分（センナ、ヒマシ油）"]
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンペナルティ（リスク成分）: {product_name} = {penalties['リスク成分（センナ、ヒマシ油）']}")
        
        # 二日酔いの場合、乗り物酔い薬へのペナルティ
        # 二日酔いの症状パターンがマッチした場合、乗り物酔い薬にペナルティを適用
        hangover_patterns = [
            frozenset({"頭痛", "むくみ", "だるさ"}),
            frozenset({"頭痛", "むくみ"}),
            frozenset({"頭痛", "だるさ"}),
            frozenset({"むくみ", "だるさ"}),
            frozenset({"頭痛", "吐き気"}),
            frozenset({"頭痛", "だるさ", "吐き気"})
        ]
        symptom_list = [s.get("name") for s in nlu_result.get("symptoms", [])]
        # 症状名の正規化（「疲労感」→「だるさ」など）
        symptom_mapping = {
            "疲労感": "だるさ",
            "倦怠感": "だるさ",
            "疲れ": "だるさ",
            "だるい": "だるさ",
        }
        # 各症状を正規化してからセットに変換（重複を除去）
        normalized_symptom_names = [symptom_mapping.get(name, name) for name in symptom_list]
        normalized_symptom_set = frozenset(normalized_symptom_names)
        
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"二日酔いパターンチェック: 元の症状={symptom_list}, 正規化後={list(normalized_symptom_set)}")
        
        # 二日酔いの症状パターンがマッチするかチェック
        # パターンの症状がすべて正規化後の症状セットに含まれているか確認
        is_hangover_pattern = False
        matched_pattern = None
        for pattern in hangover_patterns:
            # パターンのすべての症状が正規化後の症状セットに含まれているか
            if pattern.issubset(normalized_symptom_set):
                is_hangover_pattern = True
                matched_pattern = pattern
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"二日酔い症状パターンマッチ: {pattern} ⊆ {normalized_symptom_set}")
                break
        
        if is_hangover_pattern:
            # 二日酔いの症状パターンがマッチした場合
            if _is_motion_sickness_medicine(candidate):
                # 乗り物酔い薬にペナルティを適用
                pattern_bonus -= 0.20  # 乗り物酔い薬へのペナルティ
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"二日酔い症状のため乗り物酔い薬にペナルティ: {product_name} = -0.20")
    
    throat_bonus = 0.0
    symptoms = nlu_result.get("symptoms", [])
    symptom_names = [s.get("name", "") for s in symptoms]
    # 症状名の正規化（スペースを削除してからチェック）
    has_throat_symptom = False
    for symptom in symptoms:
        symptom_name = symptom.get("name", "")
        # スペースを削除して正規化
        normalized_name = normalize_text(symptom_name.replace(" ", "").replace("　", ""))
        if normalized_name in THROAT_SYMPTOM_TOKENS:
            has_throat_symptom = True
            break
        # 症状名に「のど」「喉」が含まれている場合もチェック
        if "のど" in symptom_name or "喉" in symptom_name or "咽頭" in symptom_name:
            has_throat_symptom = True
            break
    has_fever = "発熱" in symptom_names
    medicine_type = candidate.get('medicine_type', '')
    throat_specificity_level = candidate.get('throat_specificity_level', 'none')
    
    # デバッグログ（has_throat_symptomとhas_feverの判定結果を確認）
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"症状判定: has_throat_symptom={has_throat_symptom}, has_fever={has_fever}, symptom_names={symptom_names}, medicine_type={medicine_type}, product_name={candidate.get('product_name', '')}")
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"症状判定: has_throat_symptom={has_throat_symptom}, has_fever={has_fever}, symptom_names={symptom_names}, throat_specificity_level={throat_specificity_level}, product_name={candidate.get('product_name', '')}")
    
    # 総合感冒薬（喉向き）の識別ログ
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        if throat_specificity_level != "none":
            matched_ingredients = []
            if throat_specificity_level == "component_and_efficacy":
                ingredients_str = str(candidate.get('ingredients', '')).lower()
                ingredients_normalized_log = normalize_text(ingredients_str)
                matched_ingredients = [ing for ing in THROAT_SPECIFIC_INGREDIENTS if normalize_text(ing.lower()) in ingredients_normalized_log]
            logger.debug(f"総合感冒薬（喉向き）識別: {candidate.get('product_name', '')}, level={throat_specificity_level}, ingredients={matched_ingredients}")
    
    # 「のど痛み+発熱」の症状パターンでの特別なボーナス
    # 最初に葛根湯チェックを実行（すべてのthroat_bonus処理の前に）
    # 統一された判定関数を使用
    product_name = candidate.get('product_name', '')
    is_kakkonto_medicine = _is_kakkonto_medicine(candidate)
    
    # 葛根湯の条件付き推奨ロジック
    # 風邪の初期（軽度）の場合のみ推奨、それ以外は低優先度
    kakkonto_penalty = 0.0
    if is_kakkonto_medicine:
        # 効能効果に「かぜの初期」が含まれるか確認
        efficacy = candidate.get('efficacy', '')
        has_initial_cold_efficacy = 'かぜの初期' in efficacy or '感冒の初期' in efficacy or '風邪の初期' in efficacy
        
        # NLU結果のseverityが「軽度」か確認
        severity = nlu_result.get("severity", "中等度")
        is_mild_severity = severity == "軽度"
        
        if has_throat_symptom and has_fever:
            # 「のどの痛み+発熱」の場合
            if has_initial_cold_efficacy and is_mild_severity:
                # 風邪の初期（軽度）の場合、ペナルティを軽減（ただし-0.2に強化）
                kakkonto_penalty = -0.2  # -0.1から-0.2に強化（4位以降に配置するため）
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"葛根湯（風邪の初期・軽度・のど痛み+発熱）: {candidate.get('product_name', '')} = ペナルティ -0.2（強化）")
            else:
                # 風邪の初期でない場合、大きなペナルティを課す
                kakkonto_penalty = -0.3
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"葛根湯（風邪の初期でない・のど痛み+発熱）: {candidate.get('product_name', '')} = ペナルティ -0.3（総合感冒薬優先）")
    
    # throat_bonusの計算前に、葛根湯の場合は0.0に設定（すべてのthroat_bonus処理の前に）
    if is_kakkonto_medicine:
        throat_bonus = 0.0
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"葛根湯のためthroat_bonusを0.0に設定（のど痛み+発熱）: {product_name}")
    
    # 総合風邪薬の優先推奨ボーナス（複数の風邪症状がある場合）
    comprehensive_cold_bonus = 0.0
    if focus_pollen and ('風邪薬' in medicine_type or is_comprehensive_cold_medicine(candidate)):
        comprehensive_cold_bonus = -0.5
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(
                f"花粉症文脈のため総合感冒薬ボーナスを抑制: {candidate.get('product_name', '')} = -0.50"
            )
    elif is_comprehensive_cold_medicine(candidate):
        # 風邪の症状が複数ある場合、総合風邪薬にボーナスを付与
        # 単一症状の場合（ユーザー症状が1つの場合）はボーナスを付与しない（過剰処方を防ぐため）
        cold_symptoms = ["発熱", "咳", "鼻水", "のどの痛み", "頭痛", "悪寒", "くしゃみ", "鼻づまり"]
        cold_symptom_count = sum(1 for symptom in symptom_names if symptom in cold_symptoms)
        is_single_symptom = len(symptom_names) == 1
        
        if cold_symptom_count >= 2 and not is_single_symptom:
            # ボーナスをさらに強化（0.7 → 0.9）して、総合風邪薬のスコアを大幅に向上
            # ただし、単一症状の場合は適用しない
            comprehensive_cold_bonus = 0.9
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"総合風邪薬優先推奨ボーナス: {candidate.get('product_name', '')} = +0.90 (風邪症状数: {cold_symptom_count})")
        elif cold_symptom_count >= 1 and not is_single_symptom:
            # 風邪症状が1つでもある場合、軽度のボーナスを付与
            # ただし、単一症状の場合は適用しない
            comprehensive_cold_bonus = 0.4
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"総合風邪薬優先推奨ボーナス（軽度）: {candidate.get('product_name', '')} = +0.40 (風邪症状数: {cold_symptom_count})")
        elif is_single_symptom:
            # 単一症状の場合はペナルティを適用（過剰処方を防ぐため、-0.8のペナルティに強化）
            comprehensive_cold_bonus = -0.8
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"総合風邪薬ペナルティ（単一症状）: {candidate.get('product_name', '')} = -0.8 (症状: {symptom_names})")
    
    # 複数症状（3症状以上）時の総合感冒薬への追加ボーナス
    multi_symptom_cold_bonus = 0.0
    if len(symptom_names) >= 3 and '風邪薬' in medicine_type:
        multi_symptom_cold_bonus = 0.15
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"複数症状（3症状以上）時の総合感冒薬への追加ボーナス: {candidate.get('product_name', '')} = +0.15")
    
    # 「のど痛み+発熱」パターンのボーナス適用条件をログ出力（DEBUGレベル）
    if has_throat_symptom and has_fever and len(symptom_names) >= 2:
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"「のど痛み+発熱」パターン検出: product_name={candidate.get('product_name', '')}, medicine_type={medicine_type}, is_kakkonto={is_kakkonto_medicine}")
    
    if has_throat_symptom and has_fever and len(symptom_names) >= 2:
        # 葛根湯にはボーナスを適用しない（西洋薬を優先）
        # 葛根湯の場合はスキップ
        if not is_kakkonto_medicine:
            if '風邪薬' in medicine_type:
                if throat_specificity_level == "component_and_efficacy":
                    # 総合感冒薬（喉向き・成分あり）に+0.55のボーナス（強化：0.50から0.55に）
                    throat_bonus = 0.55
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"総合感冒薬（喉向き・成分あり）ボーナス: {candidate.get('product_name', '')} = +0.55")
                elif throat_specificity_level == "efficacy_only":
                    # 総合感冒薬（喉向き・効能のみ）に+0.45のボーナス（強化：0.40から0.45に）
                    throat_bonus = 0.45
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"総合感冒薬（喉向き・効能のみ）ボーナス: {candidate.get('product_name', '')} = +0.45")
                else:
                    # 一般の総合感冒薬にも+0.40のボーナス（強化：0.30から0.40に）
                    throat_bonus = 0.40
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"一般の総合感冒薬ボーナス: {candidate.get('product_name', '')} = +0.40")
            elif '解熱鎮痛薬' in medicine_type:
                # 解熱鎮痛薬に+0.45のボーナス（強化：2位優先のため、0.35から0.45に増加）
                throat_bonus = 0.45
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"解熱鎮痛薬ボーナス（のど痛み+発熱）: {candidate.get('product_name', '')} = +0.45")
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"解熱鎮痛薬ボーナス（のど痛み+発熱）: {candidate.get('product_name', '')} = +0.45")
            elif '外用薬（のど）' in medicine_type or ('外用薬' in medicine_type and has_throat_symptom):
                # 外用薬（喉スプレー・うがい薬）に+0.45のボーナス（強化：3位優先のため、0.35から0.45に増加）
                throat_bonus = 0.45
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"外用薬（のど）ボーナス（のど痛み+発熱）: {candidate.get('product_name', '')} = +0.45")
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"外用薬（のど）ボーナス（のど痛み+発熱）: {candidate.get('product_name', '')} = +0.45")
    
    if has_throat_symptom:
        # 葛根湯チェックは既に上で実行済み（is_kakkonto_medicineを使用）
        # 葛根湯の場合はthroat_bonusを0.0に設定（すべてのthroat_bonus処理の前に）
        if is_kakkonto_medicine:
            throat_bonus = 0.0
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"葛根湯のためthroat_bonusを0.0に設定（のど症状）: {product_name}")
        
        # 単一のど症状の場合、剤形ごとの優先度を明確化
        if len(symptom_names) == 1 and "のどの痛み" in symptom_names:
            # 葛根湯の場合はスキップ
            if not is_kakkonto_medicine:
                if '外用薬（のど）' in medicine_type:
                    throat_bonus = max(throat_bonus, 0.25)  # 局所治療薬を最優先
                elif '外用薬' in medicine_type:
                    throat_bonus = max(throat_bonus, 0.20)
                elif '解熱鎮痛薬' in medicine_type:
                    throat_bonus = max(throat_bonus, 0.08)
                elif '風邪薬' in medicine_type:
                    throat_bonus = max(throat_bonus, 0.05)

        # 通常のthroat_bonus（複数症状や液剤検出時、上記の特別ボーナスがない場合）
        # ただし、葛根湯の場合はスキップ（西洋薬を優先）
        if throat_bonus == 0.0:
            # 葛根湯の場合はスキップ
            if not is_kakkonto_medicine:
                combined_text = candidate.get('product_name', '') + candidate.get('efficacy', '') + medicine_type + candidate.get('usage', '')
                normalized_combined = normalize_text(combined_text)
                detection_bonus = 0.0
                if any(token in normalized_combined for token in THROAT_LIQUID_TOKENS):
                    detection_bonus = 0.12  # 0.18から0.12に調整（液状への加点を適正化）
                elif any(token in normalized_combined for token in THROAT_KEYWORD_TOKENS):
                    detection_bonus = 0.08
                elif '外用薬' in medicine_type:
                    detection_bonus = 0.12

                throat_bonus = max(throat_bonus, detection_bonus)

    # アレルギーペナルティとブースト（アレルギー症状が検出された場合）
    allergy_penalty = candidate.get('allergy_penalty', 0.0)
    allergy_boost = candidate.get('allergy_boost', 0.0)
    pollen_boost = candidate.get('pollen_boost', 0.0)
    pollen_penalty = candidate.get('pollen_penalty', 0.0)
    
    # 二日酔いブースト（二日酔いが検出された場合）
    hangover_boost = candidate.get('hangover_boost', 0.0)
    
    # 複数症状（3症状以上）時の総合感冒薬への追加ボーナスの上限制限
    limited_multi_symptom_cold_bonus = max(0.0, min(0.15, multi_symptom_cold_bonus))
    
    # 総合風邪薬優先推奨ボーナスの上限制限
    # 総合風邪薬ボーナスの上限を0.9に引き上げ（0.7 → 0.9）
    # 単一症状時のペナルティ（-0.8）も適用するため、下限を-0.8に設定
    limited_comprehensive_cold_bonus = max(-0.8, min(0.9, comprehensive_cold_bonus))
    
    # ボーナス/ペナルティの影響を制限（スコアのばらつきを確保しつつ、特化医薬品の優位性を保つ）
    # 特化医薬品のボーナスは最大0.30まで許可（症状特化型ブースト、throat_bonus）- 総合感冒薬ボーナス強化のため上限を0.30に変更
    # 不適切な医薬品のペナルティは最大-0.30まで許可（症状特異性ペナルティ、リスク成分ペナルティ）
    # アレルギー関連は中程度の影響（-0.20から+0.20）
    # 解熱鎮痛薬と外用薬（のど）のボーナス上限を0.50に引き上げ（2位・3位優先のため強化）
    # 総合感冒薬の上限を0.70に引き上げ（throat_bonus 0.55 + multi_symptom_cold_bonus 0.15 = 0.70）
    if '解熱鎮痛薬' in medicine_type or '外用薬（のど）' in medicine_type:
        limited_throat_bonus = max(-0.20, min(0.50, throat_bonus))  # 解熱鎮痛薬と外用薬（のど）の上限を0.50に引き上げ
    elif '風邪薬' in medicine_type:
        # 総合感冒薬の場合、throat_bonus + multi_symptom_cold_bonusの合計が0.70を超えないように制限
        total_cold_bonus = throat_bonus + multi_symptom_cold_bonus
        if total_cold_bonus > 0.70:
            # 合計が0.70を超える場合は、throat_bonusを0.70 - multi_symptom_cold_bonusに制限
            limited_throat_bonus = max(-0.20, min(0.70 - limited_multi_symptom_cold_bonus, throat_bonus))
        else:
            limited_throat_bonus = max(-0.20, min(0.70, throat_bonus))  # 総合感冒薬の上限を0.70に引き上げ
    else:
        limited_throat_bonus = max(-0.20, min(0.40, throat_bonus))  # 特化医薬品の優位性を保つ（総合感冒薬ボーナス強化のため上限を0.40に変更）
    limited_symptom_boost = max(-0.20, min(0.25, symptom_boost))  # 特化医薬品の優位性を保つ
    
    # symptom_specific_boostとmulti_symptom_bonusが両方適用される場合、合計が0.30を超えないように制限
    # multi_symptom_bonusは既にsymptom_boostに含まれているため、重複を避ける
    # ただし、multi_symptom_bonusは表示用に保持する
    combined_boost = limited_symptom_boost  # symptom_boostには既にmulti_symptom_bonusが含まれている
    if combined_boost > 0.30:
        # 0.30を超える場合は、symptom_boostを0.30に制限
        limited_symptom_boost = 0.30
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"symptom_boostが0.30を超えるため制限: {combined_boost:.3f} → 0.30")
    
    limited_allergy_penalty = max(-0.20, min(0.0, allergy_penalty))  # 中程度のペナルティ
    limited_allergy_boost = max(0.0, min(0.20, allergy_boost))  # 中程度のボーナス
    pollen_boost_cap = 0.55 if focus_pollen else 0.25
    limited_pollen_boost = max(0.0, min(pollen_boost_cap, pollen_boost))
    limited_pollen_penalty = max(-0.35, min(0.0, pollen_penalty))
    limited_hangover_boost = max(0.0, min(0.55, hangover_boost))  # 二日酔い医薬品への非常に大幅なブースト（五苓散+頭痛優先）
    # symptom_specificity_penaltyがNoneの場合は0.0を使用
    symptom_specificity_penalty = symptom_specificity_penalty if symptom_specificity_penalty is not None else 0.0
    limited_symptom_specificity_penalty = max(-0.30, min(0.0, symptom_specificity_penalty))  # 不適切な医薬品を確実に下げる
    limited_risk_penalty = max(-0.30, min(0.0, risk_penalty))  # リスク成分のペナルティを強化
    
    # 基本スコア（重み付けによる基本スコア）
    base_score = (
        SCORING_WEIGHTS["症状適合度"] * symptom_score +
        SCORING_WEIGHTS["効能特異性"] * efficacy_specificity_score +
        SCORING_WEIGHTS["年齢適合性"] * age_score +
        SCORING_WEIGHTS["用法簡便性"] * usage_score +
        SCORING_WEIGHTS["副作用リスク"] * side_effect_score +
        SCORING_WEIGHTS["相互作用リスク"] * interaction_score
    )
    
    # 解熱鎮痛薬と外用薬（のど）のbase_scoreを底上げ（「のど痛み+発熱」パターンの場合）
    if has_throat_symptom and has_fever and len(symptom_names) >= 2:
        if '解熱鎮痛薬' in medicine_type:
            # 解熱鎮痛薬のbase_scoreを底上げ（0.316 → 0.40程度に）
            if base_score < 0.40:
                base_score = 0.40
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"解熱鎮痛薬のbase_scoreを底上げ: {product_name} = 0.40")
        elif '外用薬（のど）' in medicine_type or ('外用薬' in medicine_type and has_throat_symptom):
            # 外用薬（のど）のbase_scoreを底上げ（0.316 → 0.40程度に）
            if base_score < 0.40:
                base_score = 0.40
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"外用薬（のど）のbase_scoreを底上げ: {product_name} = 0.40")
    
    # 部位マッチングスコアの制限（-0.5から+0.3の範囲に変更：1.0は大きすぎる）
    limited_body_part_score = max(-0.5, min(0.3, body_part_score))
    
    # 症状パターンボーナスの制限
    limited_pattern_bonus = max(-0.20, min(0.25, pattern_bonus))
    
    # --- 2.7 解熱鎮痛薬以外の医薬品タイプでの多様性向上 ---
    # 解熱鎮痛薬以外の医薬品タイプでの多様性向上
    medicine_type_diversity = candidate.get("medicine_type", "")
    symptom_names_diversity = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
    user_text_lower_diversity = user_text.lower() if user_text else ''
    
    # 症状の重症度に応じた推奨
    severity_keywords = {
        "重度": ["激しい", "ひどい", "重い", "酷い", "深刻", "重症", "強烈", "耐えられない"],
        "軽度": ["少し", "軽い", "軽微", "ちょっと", "やや"],
        "中等度": ["中程度", "普通", "まあまあ"]
    }
    
    # 症状の重症度を判定
    detected_severity = None
    for severity, keywords in severity_keywords.items():
        if any(kw in user_text_lower_diversity for kw in keywords):
            detected_severity = severity
            break
    
    # 重症度に応じたボーナス（重度の症状には強力な医薬品を推奨）
    severity_bonus = 0.0
    if detected_severity == "重度" and is_strong_medicine:
        severity_bonus = 0.1
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"重症度ボーナス: {product_name} = +{severity_bonus}")
    
    # 症状の組み合わせに応じた推奨（複数症状の場合は異なる医薬品を推奨）
    combination_bonus = 0.0
    if len(symptom_names_diversity) >= 2:
        # 複数症状の場合は、より広範囲の効能効果を持つ医薬品にボーナス
        efficacy_diversity = str(candidate.get('efficacy', '')).lower()
        matched_symptoms = sum(1 for symptom in symptom_names_diversity if symptom.lower() in efficacy_diversity)
        if matched_symptoms >= 2:
            combination_bonus = 0.05
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"複数症状マッチボーナス: {product_name} = +{combination_bonus}")
    
    # ユーザーの年齢に応じた推奨（小児用、成人用など）
    age_match_bonus = 0.0
    if user_info and user_info.get('age'):
        age_diversity = user_info.get('age')
        # 小児用製剤の判定
        is_pediatric_form = any(kw in product_name.lower() for kw in ['小児', '子供', 'こども', '小中学生'])
        if age_diversity < 15 and is_pediatric_form:
            age_match_bonus = 0.1
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"年齢適合ボーナス: {product_name} = +{age_match_bonus}")
    
    # 剤形の優先順位調整（症状に応じた剤形ボーナス/ペナルティ）
    dosage_form_bonus = 0.0
    product_name = candidate.get('product_name', '')
    usage = candidate.get('usage', '')
    combined_dosage_text = (product_name + usage).lower()
    
    # のど痛みがある場合、液剤に+0.08、外用薬（のど）に+0.12のボーナス（既存ロジックを維持）
    if has_throat_symptom:
        if any(token in combined_dosage_text for token in ["液", "シロップ", "ドリンク", "内服液"]):
            dosage_form_bonus = max(dosage_form_bonus, 0.08)
        if '外用薬（のど）' in medicine_type:
            dosage_form_bonus = max(dosage_form_bonus, 0.12)
    
    # 胃痛がある場合、錠剤・カプセルを優先（液剤は-0.05のペナルティ）
    if "胃痛" in symptom_names:
        if any(token in combined_dosage_text for token in ["錠", "カプセル", "錠剤"]):
            dosage_form_bonus = max(dosage_form_bonus, 0.05)
        elif any(token in combined_dosage_text for token in ["液", "シロップ", "ドリンク", "内服液"]):
            dosage_form_bonus = min(dosage_form_bonus, -0.05)
    
    # 便秘の場合、錠剤・カプセルを優先
    if "便秘" in symptom_names:
        if any(token in combined_dosage_text for token in ["錠", "カプセル", "錠剤"]):
            dosage_form_bonus = max(dosage_form_bonus, 0.05)
    
    # 筋肉痛の場合、外用薬（テープ・ゲル・パップなど）を優先（湿布が適切）
    if "筋肉痛" in symptom_names:
        is_topical_muscle = any(token in combined_dosage_text for token in ["テープ", "ゲル", "パップ", "ローション", "軟膏", "クリーム"]) or '外用薬（皮膚）' in medicine_type
        if is_topical_muscle:
            dosage_form_bonus = max(dosage_form_bonus, 0.25)  # 筋肉痛には外用薬を強く推奨
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"筋肉痛・外用薬ボーナス: {product_name} = +0.25")
    
    limited_dosage_form_bonus = max(-0.10, min(0.25, dosage_form_bonus))  # 上限を0.25に引き上げ（筋肉痛の外用薬ボーナスに対応）
    
    # 成分ベースのボーナス
    ingredient_boost = calculate_ingredient_based_boost(candidate, nlu_result, user_info, user_text)
    limited_ingredient_boost = max(0.0, min(0.25, ingredient_boost))  # 最大0.25まで
    if limited_ingredient_boost > 0:
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"🔬 成分ベーススコア: {candidate.get('product_name', '')} = +{limited_ingredient_boost:.2f}")
    
    # 月経不順症状で漢方薬かつ食前・食間への微小な加点（新規追加）
    dosage_timing_boost = 0.0
    menstrual_symptoms_list = ["月経不順", "生理不順", "生理痛", "月経痛"]
    has_menstrual_symptom_list = any(symptom in symptom_names for symptom in menstrual_symptoms_list)
    
    # ライフステージ（年齢層）による補正
    life_stage_boost = 0.0
    if has_menstrual_symptom_list:
        life_stage = determine_life_stage(user_info, nlu_result)
        
        # 若年層（10-20代）: 「桂枝茯苓丸」や「鎮痛剤配合薬」をブースト
        if life_stage == "若年層":
            if "桂枝茯苓丸" in product_name or "ケイシブクリョウガン" in product_name.upper():
                life_stage_boost = max(life_stage_boost, 0.15)
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"📅 ライフステージボーナス（若年層）: 桂枝茯苓丸 = +0.15 ({candidate.get('product_name', '')})")
            # 鎮痛剤配合薬（解熱鎮痛薬）をブースト
            if '解熱鎮痛薬' in medicine_type:
                life_stage_boost = max(life_stage_boost, 0.10)
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"📅 ライフステージボーナス（若年層）: 鎮痛剤配合薬 = +0.10 ({candidate.get('product_name', '')})")
        
        # 中間層（30-40代）: 「加味逍遙散」や「命の母ホワイト」をブースト
        elif life_stage == "中間層":
            if is_exact_product_match(product_name, ["加味逍遙散", "カミショウヨウサン"]):
                life_stage_boost = max(life_stage_boost, 0.20)
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"📅 ライフステージボーナス（中間層）: 加味逍遙散 = +0.20 ({candidate.get('product_name', '')})")
            if is_exact_product_match(product_name, ["命の母ホワイト"]) or (is_exact_product_match(product_name, ["命の母"]) and "ホワイト" in product_name):
                life_stage_boost = max(life_stage_boost, 0.20)
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"📅 ライフステージボーナス（中間層）: 命の母ホワイト = +0.20 ({candidate.get('product_name', '')})")
        
        # 更年期前後（50代以上）: 「加味逍遙散」「命の母ホワイト」「ラムールQ」をブースト
        elif life_stage == "更年期前後":
            if is_exact_product_match(product_name, ["加味逍遙散", "カミショウヨウサン"]):
                life_stage_boost = max(life_stage_boost, 0.25)
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"📅 ライフステージボーナス（更年期前後）: 加味逍遙散 = +0.25 ({candidate.get('product_name', '')})")
            if is_exact_product_match(product_name, ["命の母ホワイト"]) or (is_exact_product_match(product_name, ["命の母"]) and "ホワイト" in product_name):
                life_stage_boost = max(life_stage_boost, 0.25)
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"📅 ライフステージボーナス（更年期前後）: 命の母ホワイト = +0.25 ({candidate.get('product_name', '')})")
            if is_exact_product_match(product_name, ["ラムールQ", "ラムールｑ", "ラムールq"]):
                life_stage_boost = max(life_stage_boost, 0.25)
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"📅 ライフステージボーナス（更年期前後）: ラムールQ = +0.25 ({candidate.get('product_name', '')})")
    
    if has_menstrual_symptom_list:
        # 漢方薬の判定
        is_kampo = _is_kampo_or_herbal_medicine(candidate)
        
        if is_kampo:
            # 用法用量テキストから「食前」「食間」「空腹時」のキーワードを抽出
            usage_text = str(candidate.get('usage', '')).lower()
            efficacy_text = str(candidate.get('efficacy', '')).lower()
            combined_usage = usage_text + efficacy_text
            
            if any(kw in combined_usage for kw in ["食前", "食間", "空腹時", "空腹"]):
                dosage_timing_boost = 0.02  # 微小な加点
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"月経不順症状+漢方薬+食前・食間のため加点: {candidate.get('product_name', '')} = +0.02")
        
        # ラムールQ、加味逍遙散、命の母ホワイト、ルナエール、ルナフェミンの優先ボーナス（製品名ベース、厳密なマッチング）
        if is_exact_product_match(product_name, ["ラムールQ", "ラムールｑ", "ラムールq"]):
            priority_boost = 0.15  # ラムールQ優先ボーナス（0.10から0.15に増加）
            dosage_timing_boost += priority_boost
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"ラムールQ優先ボーナス: {candidate.get('product_name', '')} = +{priority_boost}")
        elif is_exact_product_match(product_name, ["加味逍遙散", "カミショウヨウサン"]):
            priority_boost = 0.15  # 加味逍遙散優先ボーナス（0.10から0.15に増加）
            dosage_timing_boost += priority_boost
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"加味逍遙散優先ボーナス: {candidate.get('product_name', '')} = +{priority_boost}")
        elif is_exact_product_match(product_name, ["命の母ホワイト"]) or (is_exact_product_match(product_name, ["命の母"]) and "ホワイト" in product_name):
            priority_boost = 0.15  # 命の母ホワイト優先ボーナス（0.10から0.15に増加）
            dosage_timing_boost += priority_boost
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"命の母ホワイト優先ボーナス: {candidate.get('product_name', '')} = +{priority_boost}")
        elif is_exact_product_match(product_name, ["ルナエール"]):
            priority_boost = 0.12  # ルナエール優先ボーナス
            dosage_timing_boost += priority_boost
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"ルナエール優先ボーナス: {candidate.get('product_name', '')} = +{priority_boost}")
        elif is_exact_product_match(product_name, ["ルナフェミン"]):
            priority_boost = 0.12  # ルナフェミン優先ボーナス
            dosage_timing_boost += priority_boost
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"ルナフェミン優先ボーナス: {candidate.get('product_name', '')} = +{priority_boost}")
        
        # 錠剤タイプへの「飲みやすさ」ボーナス（月経不順症状がある場合）
        if any(token in combined_dosage_text for token in ["錠", "錠剤"]):
            tablet_convenience_boost = 0.08  # 飲みやすさボーナス
            dosage_timing_boost += tablet_convenience_boost
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"月経不順症状+錠剤タイプのため飲みやすさボーナス: {candidate.get('product_name', '')} = +{tablet_convenience_boost}")
        
        # ビタミン配合へのボーナス（月経不順症状がある場合）
        ingredients = str(candidate.get('ingredients', '')).lower()
        vitamin_keywords = ["ビタミン", "vitamin", "ビタミンe", "ビタミンb", "トコフェロール", "酢酸トコフェロール"]
        has_vitamin = any(vitamin in ingredients for vitamin in vitamin_keywords)
        if has_vitamin:
            vitamin_boost = 0.08  # ビタミン配合ボーナス
            dosage_timing_boost += vitamin_boost
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"月経不順症状+ビタミン配合のためボーナス: {candidate.get('product_name', '')} = +{vitamin_boost}")
    
    # タイブレーカー（成分重視型 vs 利便性重視型）
    tiebreaker_boost = 0.0
    nlu_severity = nlu_result.get("severity", None)
    if nlu_severity:
        if nlu_severity == "重度":
            # 症状が「強い」（重度）と判定された場合: 成分重視型
            # 効果的な成分が含まれている場合にボーナス（+0.15）
            # 成分含有の有無で判定（成分量は考慮しない）
            # 既にingredient_boostで評価されているため、追加のボーナスは不要
            tiebreaker_boost = 0.0  # ingredient_boostで既に評価済み
        elif nlu_severity == "軽度":
            # 症状が「軽い/仕事中」（軽度）と判定された場合: 利便性重視型
            # 用法の簡便性にボーナス（+0.10）
            # 服用回数（1日2回 < 1日3回）と剤形（カプセル > 錠剤 > 顆粒）の両方を考慮
            usage = str(candidate.get('usage', '')).lower()
            product_name = str(candidate.get('product_name', '')).lower()
            combined_usage = usage + product_name
            
            # 服用回数のチェック
            if any(kw in combined_usage for kw in ["1日1回", "1回", "1日1度"]):
                tiebreaker_boost = 0.10
            elif any(kw in combined_usage for kw in ["1日2回", "2回", "朝晩"]):
                tiebreaker_boost = 0.10
            elif any(kw in combined_usage for kw in ["1日3回", "3回", "食後"]):
                tiebreaker_boost = 0.05
            
            # 剤形のチェック（カプセル > 錠剤 > 顆粒）
            if "カプセル" in combined_usage:
                tiebreaker_boost = max(tiebreaker_boost, 0.10)
            elif "錠" in combined_usage and "カプセル" not in combined_usage:
                tiebreaker_boost = max(tiebreaker_boost, 0.05)
            elif "顆粒" in combined_usage:
                tiebreaker_boost = max(tiebreaker_boost, 0.02)
    
    limited_tiebreaker_boost = max(0.0, min(0.10, tiebreaker_boost))  # 最大0.10まで
    
    # ライフステージボーナスをdosage_timing_boostに追加
    dosage_timing_boost += life_stage_boost
    
    # 月経不順症状がある場合、錠剤ボーナスとビタミン配合ボーナスが追加されるため、上限を引き上げ
    max_dosage_timing_boost = 0.20 if has_menstrual_symptom_list else 0.02
    limited_dosage_timing_boost = max(0.0, min(max_dosage_timing_boost, dosage_timing_boost))
    
    # 漢方薬・生薬製剤の優先度調整（症状パターンごとに異なる処理）
    # adjustment_scoreの計算前に実行する必要がある
    kampo_adjustment = 0.0
    
    # 証（Sho）判定によるボーナス/ペナルティ（月経不順症状がある場合）
    sho_bonus = 0.0
    if has_menstrual_symptom_list:
        # 証判定を実行
        user_message = user_text or user_info.get('user_message', '') or ''
        sho_result = determine_kampo_sho(user_info, nlu_result, user_message)
        sho = sho_result.get('sho', '不明')
        confidence = sho_result.get('confidence', 0.0)
        
        # 確信度が低い場合（confidence < 0.5）: ペナルティを適用しない（フラット判定モード）
        if confidence >= 0.5:
            # 医薬品の作用機序を分類
            mechanism = classify_medicine_mechanism(candidate)
            
            # 虚証の場合: 補血・調血系にボーナス、理気・駆瘀血系にペナルティ
            if sho == "虚証":
                if mechanism == "補血・調血系":
                    sho_bonus = 0.15 * confidence  # 確信度に応じて重み付け
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"🔍 証ボーナス（虚証→補血系）: {candidate.get('product_name', '')} = +{sho_bonus:.2f} (確信度: {confidence:.2f})")
                elif mechanism == "理気・駆瘀血系":
                    sho_bonus = -0.10 * confidence  # 確信度に応じて重み付け
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"🔍 証ペナルティ（虚証→理気系）: {candidate.get('product_name', '')} = {sho_bonus:.2f} (確信度: {confidence:.2f})")
            
            # 実証の場合: 理気・駆瘀血系にボーナス、補血・調血系にペナルティ
            elif sho == "実証":
                if mechanism == "理気・駆瘀血系":
                    sho_bonus = 0.15 * confidence  # 確信度に応じて重み付け
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"🔍 証ボーナス（実証→理気系）: {candidate.get('product_name', '')} = +{sho_bonus:.2f} (確信度: {confidence:.2f})")
                elif mechanism == "補血・調血系":
                    sho_bonus = -0.10 * confidence  # 確信度に応じて重み付け
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"🔍 証ペナルティ（実証→補血系）: {candidate.get('product_name', '')} = {sho_bonus:.2f} (確信度: {confidence:.2f})")
            
            # 中間証・不明の場合: ペナルティを適用しない（フラット判定モード）
            else:
                sho_bonus = 0.0
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"🔍 証判定（{sho}）のため証ボーナス/ペナルティを適用しません: {candidate.get('product_name', '')}")
        else:
            # 確信度が低い場合: ペナルティを適用しない（フラット判定モード）
            sho_bonus = 0.0
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"🔍 証判定の確信度が低い（{confidence:.2f}）ため証ボーナス/ペナルティを適用しません: {candidate.get('product_name', '')}")
    
    # 二日酔いの場合、漢方薬ペナルティを無効化
    is_hangover_case = candidate.get('is_hangover', False)
    hangover_boost = candidate.get('hangover_boost', 0.0)
    
    # 漢方薬希望/忌避のユーザー意向
    prefers_kampo = user_info.get('prefers_kampo', False)
    prefers_not_kampo = user_info.get('prefers_not_kampo', False)
    kampo_symptom_names = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
    user_message_for_kampo = (user_text or user_info.get('user_message', '') or '').lower()
    is_kampo_preferred_scenario = (
        bool(set(kampo_symptom_names) & KAMPO_PREFERRED_SYMPTOMS) or
        any(kw in user_message_for_kampo for kw in KAMPO_PREFERRED_SYMPTOMS)
    )
    
    if _is_kampo_or_herbal_medicine(candidate):
        # ユーザーが漢方薬を希望する場合、ペナルティを適用しない
        if prefers_kampo and not prefers_not_kampo:
            kampo_adjustment = 0.0
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"漢方薬希望のため漢方薬ペナルティを無効化: {candidate.get('product_name', '')}")
        # ユーザーが漢方薬を避けたい場合、追加ペナルティ
        elif prefers_not_kampo:
            kampo_adjustment = -0.35
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"漢方薬忌避のため漢方薬に追加ペナルティ: {candidate.get('product_name', '')} = -0.35")
        # 二日酔いが検出されている場合、漢方薬ペナルティを適用しない
        elif is_hangover_case or hangover_boost > 0:
            kampo_adjustment = 0.0
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"二日酔いのため漢方薬ペナルティを無効化: {candidate.get('product_name', '')}")
        # 漢方薬推奨シナリオ（生理痛・頻尿・更年期等）の場合、ペナルティを適用しない
        elif is_kampo_preferred_scenario:
            kampo_adjustment = 0.0
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"漢方薬推奨シナリオのため漢方薬ペナルティを無効化: {candidate.get('product_name', '')}")
        else:
            # 症状パターンに基づく漢方薬ボーナス/ペナルティ
            pattern_info = match_symptom_pattern(nlu_result)
            product_name = candidate.get('product_name', '')
            is_goreisan = _is_goreisan(candidate)
            # 統一された判定関数を使用
            is_kakkonto_medicine_check = _is_kakkonto_medicine(candidate)
            
            # 症状パターンごとの特別な処理
            if pattern_info:
                # 「のど痛み+発熱」の場合、葛根湯には大きなペナルティを適用（西洋薬を優先）
                # has_throat_symptomとhas_feverの判定も使用（パターンマッチングが失敗した場合のフォールバック）
                symptoms_list = nlu_result.get("symptoms", [])
                symptom_names_list = [s.get("name", "") for s in symptoms_list]
                has_throat = any("のど" in name or "喉" in name or "咽頭" in name for name in symptom_names_list)
                has_fever_symptom = "発熱" in symptom_names_list
                
                if (frozenset({"のどの痛み", "発熱"}) in SYMPTOM_PATTERN_OPTIMIZATION) or (has_throat and has_fever_symptom and len(symptom_names_list) >= 2):
                    if is_kakkonto_medicine_check:
                        # 症状の強度判定を取得（検出できない場合は中等度として扱う）
                        nlu_severity = nlu_result.get("severity", "中等度")
                        if nlu_severity is None or nlu_severity == "":
                            nlu_severity = "中等度"
                        
                        # 中等度以上の場合は大きなペナルティ（風邪の初期向けの医薬品を推奨しない）
                        if nlu_severity in ["中等度", "重度"]:
                            kampo_adjustment = -0.30  # 大きなペナルティ
                            if DEBUG_MODE or logger.level <= logging.DEBUG:
                                logger.debug(f"のど痛み+発熱（強度: {nlu_severity}）のため葛根湯に大きなペナルティ: {product_name} = -0.30")
                        else:
                            # 軽度の場合は通常のペナルティ
                            kampo_adjustment = -0.15
                            if DEBUG_MODE or logger.level <= logging.DEBUG:
                                logger.debug(f"のど痛み+発熱（強度: {nlu_severity}）のため葛根湯にペナルティ: {product_name} = -0.15")
                    else:
                        # その他の漢方薬は既にpattern_bonusで処理済み
                        kampo_adjustment = 0.0
                # 単一症状（発熱のみ、のど痛みのみ）の場合、漢方薬はペナルティ（症状強度に応じて調整）
                elif len(symptom_names) == 1:
                    # 症状の強度判定を取得（検出できない場合は中等度として扱う）
                    nlu_severity = nlu_result.get("severity", "中等度")
                    if nlu_severity is None or nlu_severity == "":
                        nlu_severity = "中等度"
                    
                    # 縛り表現（必須条件）がある漢方薬の場合はさらに大きなペナルティ
                    efficacy = str(candidate.get('efficacy', '')).lower()
                    has_restrictive_expression = any(
                        kw in efficacy for kw in ['ものの次の諸症', 'ものの次の', 'ものの諸症', 'ものや', 'もの及び', 'もの並びに', 
                                                   '諸関節が腫れて痛む', '各処の筋肉が腫れて痛む', '下腹部に化膿性', '下腹部に凝結']
                    )
                    
                    if has_restrictive_expression:
                        # 縛り表現がある場合は非常に大きなペナルティ（発熱のみには不適切）
                        kampo_adjustment = -0.60
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"単一症状（強度: {nlu_severity}）+ 縛り表現ありのため漢方薬に大きなペナルティ: {product_name} = -0.60")
                    else:
                        # 中等度以上の場合は大きなペナルティ
                        if nlu_severity in ["中等度", "重度"]:
                            kampo_adjustment = -0.40
                            if DEBUG_MODE or logger.level <= logging.DEBUG:
                                logger.debug(f"単一症状（強度: {nlu_severity}）のため漢方薬にペナルティ: {product_name} = -0.40")
                        else:
                            kampo_adjustment = -0.30
                            if DEBUG_MODE or logger.level <= logging.DEBUG:
                                logger.debug(f"単一症状（強度: {nlu_severity}）のため漢方薬にペナルティ: {product_name} = -0.30")
                # 風邪の初期症状（悪寒+発熱）の場合、葛根湯にボーナス（ただし症状強度が中等度以上の場合はペナルティ）
                elif frozenset({"悪寒", "発熱"}) in SYMPTOM_PATTERN_OPTIMIZATION and is_kakkonto_medicine_check:
                    # 症状の強度判定を取得（検出できない場合は中等度として扱う）
                    nlu_severity = nlu_result.get("severity", "中等度")
                    if nlu_severity is None or nlu_severity == "":
                        nlu_severity = "中等度"
                    
                    # 中等度以上の場合はペナルティ（風邪の初期向けの医薬品を推奨しない）
                    if nlu_severity in ["中等度", "重度"]:
                        kampo_adjustment = -0.20
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"悪寒+発熱（強度: {nlu_severity}）のため葛根湯にペナルティ: {product_name} = -0.20")
                    else:
                        # 軽度の場合は既にpattern_bonusで処理済み
                        kampo_adjustment = 0.0
                # 二日酔い（頭痛+むくみ+だるさなど）の場合、五苓散はpattern_bonusとhangover_boostで処理済み
                elif is_goreisan and any(
                    pattern_key in SYMPTOM_PATTERN_OPTIMIZATION 
                    for pattern_key in [
                        frozenset({"頭痛", "むくみ", "だるさ"}),
                        frozenset({"頭痛", "むくみ"}),
                        frozenset({"頭痛", "だるさ"}),
                        frozenset({"むくみ", "だるさ"}),
                        frozenset({"頭痛", "吐き気"}),
                        frozenset({"頭痛", "だるさ", "吐き気"})
                    ]
                ):
                    # 既にpattern_bonus（SYMPTOM_PATTERN_OPTIMIZATION）とhangover_boost（append_candidate内）で処理済み
                    kampo_adjustment = 0.0
                # 胃腸症状（胃もたれ+むかつき）の場合、生薬配合の胃腸薬に+0.15のボーナス
                elif frozenset({"吐き気", "胃もたれ", "むかつき"}) in SYMPTOM_PATTERN_OPTIMIZATION:
                    # 既にpattern_bonusで処理済み
                    kampo_adjustment = 0.0
                # その他の症状パターン: 西洋薬を優先（漢方薬は-0.10のペナルティ）
                else:
                    kampo_adjustment = -0.10
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"その他の症状パターンのため漢方薬にペナルティ: {product_name} = -0.10")
            else:
                # 症状パターンがマッチしない場合、ペナルティを適用（西洋薬を優先）
                kampo_adjustment = -0.35
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"症状パターンがマッチしないため漢方薬にペナルティ: {product_name} = -0.35")
    else:
        kampo_adjustment = 0.0
    
    # 条件付き効能のペナルティ（filter_by_efficacy_symptom_matchで設定された警告）
    # 条件付き効能ペナルティは削除（フィルタリング段階で除外するため不要）
    
    # 調整スコア（ボーナス/ペナルティを制限付きで追加）
    # kampo_adjustmentをadjustment_scoreに含める
    # kakkonto_penalty（葛根湯の条件付き推奨ペナルティ）も追加
    # pain_flag_bonusは独立したボーナス（他のボーナスとは別枠）
    # strong_medicine_bonus_finalは強力な医薬品ボーナス（2.0で追加）
    # noshin_penaltyはノーシンピュアペナルティ（2.1で追加）
    # acetaminophen_bonusはアセトアミノフェンボーナス（2.2で追加）
    # nsaids_bonusはNSAIDsボーナス（2.3で追加）
    # conditional_efficacy_penaltyは条件付き効能ペナルティ（追加）
    adjustment_score = (
        limited_symptom_specificity_penalty +
        limited_risk_penalty +
        limited_throat_bonus +
        limited_multi_symptom_cold_bonus +  # 複数症状（3症状以上）時の総合感冒薬への追加ボーナス
        limited_comprehensive_cold_bonus +  # 総合風邪薬優先推奨ボーナス
        limited_symptom_boost +
        limited_allergy_penalty +
        limited_allergy_boost +
        limited_pollen_boost +
        limited_pollen_penalty +
        limited_hangover_boost +  # 二日酔いブーストを追加
        limited_body_part_score +
        limited_pattern_bonus +
        limited_dosage_form_bonus +
        limited_ingredient_boost +  # 成分ベースのボーナスを追加
        limited_tiebreaker_boost +  # タイブレーカーボーナスを追加
        limited_dosage_timing_boost +  # 用法用量タイミングボーナス（月経不順+漢方薬+食前・食間）を追加
        kampo_adjustment +  # 漢方薬調整を追加
        sho_bonus +  # 証（Sho）判定によるボーナス/ペナルティを追加
        user_preference_bonus +  # ユーザー要望に基づくボーナスを追加
        kakkonto_penalty +  # 葛根湯の条件付き推奨ペナルティを追加
        pain_flag_bonus +  # 痛みフラグボーナス（独立したボーナス、他のボーナスとは別枠）
        strong_medicine_bonus_final +  # 強力な医薬品ボーナス（2.0で追加）
        noshin_penalty +  # ノーシンピュアペナルティ（2.1で追加）
        acetaminophen_bonus +  # アセトアミノフェンボーナス（2.2で追加）
        nsaids_bonus +  # NSAIDsボーナス（2.3で追加）
        nsaid_penalty +  # NSAIDsペナルティ（2.5で追加）
        speed_bonus +  # 速効性ボーナス（2.6で追加）
        severity_bonus +  # 重症度ボーナス（2.7で追加）
        combination_bonus +  # 複数症状マッチボーナス（2.7で追加）
        age_match_bonus +  # 年齢適合ボーナス（2.7で追加）
        major_analgesic_bonus  # 主要解熱鎮痛薬ボーナス（追加）
    )
    
    # ボーナス/ペナルティ適用のデバッグログ
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"ボーナス/ペナルティ適用: {candidate.get('product_name', '')}, throat_bonus={throat_bonus}, kakkonto_penalty={kakkonto_penalty}, kampo_adjustment={kampo_adjustment}, adjustment_score={adjustment_score:.3f}")
    
    # 最終スコア（基本スコア + 調整スコア）
    # スコアの分散を確保しつつ、最大スコアを0.98程度に設定
    # 調整スコアの影響を-0.3から+0.25の範囲に制限（より厳しく制限）
    # これにより、基本スコア0.73 + 調整スコア0.25 = 0.98が最大値となる
    # ただし、adjustment_scoreが異常に高い場合は、より厳しく制限
    # 解熱鎮痛薬と外用薬（のど）の場合、調整スコアの上限を0.30に引き上げ（2位・3位優先のため強化）
    # 総合風邪薬の場合、調整スコアの上限を0.40に引き上げ（1位優先のため強化）
    is_comprehensive_cold = is_comprehensive_cold_medicine(candidate)
    product_name_norm_adj = normalize_medicine_name_to_hankaku(product_name)
    is_major_analgesic = any(
        normalize_medicine_name_to_hankaku(major_name) in product_name_norm_adj
        for major_name in MAJOR_ANALGESIC_MEDICINES
    )
    if is_major_analgesic:
        # 主要解熱鎮痛薬の場合、調整スコアの上限を0.80に引き上げ（major_analgesic_bonusを反映させるため、0.6 → 0.8に強化）
        if adjustment_score > 0.9:
            scaled_adjustment = 0.80
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"主要解熱鎮痛薬のadjustment_scoreが異常に高いため制限: {adjustment_score:.3f} → 0.80")
        else:
            scaled_adjustment = max(-0.30, min(0.80, adjustment_score))
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"主要解熱鎮痛薬のscaled_adjustment: {scaled_adjustment:.3f} (adjustment_score: {adjustment_score:.3f})")
    elif '解熱鎮痛薬' in medicine_type or '外用薬（のど）' in medicine_type:
        # 解熱鎮痛薬と外用薬（のど）の場合、調整スコアの上限を0.30に引き上げ
        if adjustment_score > 0.5:
            scaled_adjustment = 0.30
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"解熱鎮痛薬/外用薬（のど）のadjustment_scoreが異常に高いため制限: {adjustment_score:.3f} → 0.30")
        else:
            scaled_adjustment = max(-0.30, min(0.30, adjustment_score))
    elif is_comprehensive_cold:
        # 総合風邪薬の場合、調整スコアの上限を0.40に引き上げ（1位優先のため強化）
        if adjustment_score > 0.6:
            scaled_adjustment = 0.40
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"総合風邪薬のadjustment_scoreが異常に高いため制限: {adjustment_score:.3f} → 0.40")
        else:
            scaled_adjustment = max(-0.30, min(0.40, adjustment_score))
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"総合風邪薬のscaled_adjustment: {scaled_adjustment:.3f} (adjustment_score: {adjustment_score:.3f})")
    else:
        if adjustment_score > 0.5:
            # 異常に高い場合は0.25に制限
            scaled_adjustment = 0.25
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"adjustment_scoreが異常に高いため制限: {adjustment_score:.3f} → 0.25")
        else:
            scaled_adjustment = max(-0.30, min(0.25, adjustment_score))
    
    # 改善案1: 基本スコアの底上げ（推奨される医薬品の多くが0.7-0.98に収まるように）
    # 基本スコアが0.45未満の場合は、0.5に底上げしてから調整スコアを追加
    # これにより、推奨される医薬品の多くが0.7-0.98の範囲に収まる
    adjusted_base_score = base_score  # デフォルト値
    
    # 単一症状の場合、総合感冒薬の基本スコアを下げる
    is_single_symptom_for_base = len(symptom_names) == 1
    if is_comprehensive_cold and is_single_symptom_for_base:
        # 単一症状の場合、総合感冒薬の基本スコアを0.1下げる
        adjusted_base_score = max(0.3, base_score - 0.1)
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"総合感冒薬の基本スコアを下げる（単一症状）: {product_name} = {adjusted_base_score:.3f} (元: {base_score:.3f})")
    
    # 主要解熱鎮痛薬の場合、基本スコアを底上げする
    if is_major_analgesic:
        if base_score < 0.55:
            # 主要解熱鎮痛薬の基本スコアを0.55に底上げ
            adjusted_base_score = 0.55
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"主要解熱鎮痛薬のbase_scoreを底上げ: {product_name} = 0.55 (元: {base_score:.3f})")
        elif base_score < 0.60:
            # 0.55-0.60の範囲は、0.60に近づけるように補間
            adjusted_base_score = 0.55 + (base_score - 0.55) * 0.05 / 0.05
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"主要解熱鎮痛薬のbase_scoreを補間: {product_name} = {adjusted_base_score:.3f} (元: {base_score:.3f})")
    elif base_score < 0.45:
        # 低スコア領域（0.45未満）は0.5に底上げ
        # ただし、調整スコアが負の場合は、その分を減算
        # これにより、不適切な医薬品は0.5 - 0.3 = 0.2程度まで下がる
        adjusted_base_score = 0.5
    elif base_score < 0.5:
        # 0.45-0.5の範囲は、0.5に近づけるように補間
        # これにより、より滑らかなスコア分布を実現
        adjusted_base_score = 0.5 + (base_score - 0.45) * 0.5 / 0.05
    
    # 改善案2: スコアの分散を確保するための非線形変換
    # 高スコア領域（0.5以上）では、より細かい差別化を行う
    if adjusted_base_score >= 0.5:
        # 0.5-0.73の範囲を0.5-0.73に拡大（より細かい差別化のため）
        # 平方根（0.85乗）を使用して、より細かい差別化を実現
        # 最大スコアが0.98以下になるように、拡大範囲を0.23に制限
        normalized_base = (adjusted_base_score - 0.5) / 0.23  # 0.5-0.73を0-1に正規化
        expanded_base = 0.5 + (normalized_base ** 0.85) * 0.23  # 0.5-0.73に拡大（非線形変換、最大0.98以下を保証）
        total_score = expanded_base + scaled_adjustment
    else:
        # 低スコア領域（0.5未満）はそのまま使用
        total_score = adjusted_base_score + scaled_adjustment
    
    # raw_scoreを保持（正規化は詳細スコアリング完了後に一括で行う）
    raw_score = total_score  # クリップ前の元のスコアを保持
    
    # 詳細ログの追加: Threshold Pass/Fail Detail、Sho Match Score、成分ベーススコア、証判定、ユーザー要望の反映
    threshold_pass_detail = {
        "passed": raw_score >= 0.35,
        "reason": "unknown",
        "base_score_boost": is_priority_medicine and base_score < 0.50,
        "ingredient_boost": limited_ingredient_boost > 0,
        "pattern_bonus": limited_pattern_bonus > 0,
        "user_preference_bonus": user_preference_bonus > 0,
        "life_stage_boost": life_stage_boost > 0,
        "sho_bonus": sho_bonus != 0.0
    }
    
    # スコアが0.35を超えた理由を判定
    if raw_score >= 0.35:
        if is_priority_medicine and base_score < 0.50:
            threshold_pass_detail["reason"] = "期待される医薬品の基本スコア底上げ"
        elif limited_ingredient_boost > 0:
            threshold_pass_detail["reason"] = "成分ブースト"
        elif limited_pattern_bonus > 0:
            threshold_pass_detail["reason"] = "症状パターンボーナス"
        elif user_preference_bonus > 0:
            threshold_pass_detail["reason"] = "ユーザー要望ボーナス"
        elif life_stage_boost > 0:
            threshold_pass_detail["reason"] = "ライフステージボーナス"
        elif sho_bonus > 0:
            threshold_pass_detail["reason"] = "証ボーナス"
        else:
            threshold_pass_detail["reason"] = "基本スコア"
    else:
        threshold_pass_detail["reason"] = "スコア不足"
    
    # Sho Match Score（証判定の詳細）
    sho_match_score = None
    if has_menstrual_symptom_list and user_info:
        user_message = user_text or user_info.get('user_message', '') or ''
        sho_result = determine_kampo_sho(user_info, nlu_result, user_message)
        sho_match_score = {
            "sho": sho_result.get('sho', '不明'),
            "confidence": sho_result.get('confidence', 0.0),
            "reasons": sho_result.get('reasons', []),
            "kyo_indicators": sho_result.get('kyo_indicators', []),
            "jitsu_indicators": sho_result.get('jitsu_indicators', [])
        }
    
    result = {
        "total_score": raw_score,  # 一時的にraw_scoreを返す（後で正規化される）
        "raw_score": raw_score,  # 元のスコア（表示用）
        "threshold_pass_detail": threshold_pass_detail,  # Threshold Pass/Fail Detail
        "sho_match_score": sho_match_score,  # Sho Match Score
        "score_breakdown": {
            "symptom_match": symptom_score,
            "efficacy_specificity": efficacy_specificity_score,
            "body_part_match": limited_body_part_score,  # 制限後のbody_part_scoreを保存
            "age_fit": age_score,
            "usage_convenience": usage_score,
            "side_effect_risk": side_effect_score,
            "interaction_risk": interaction_score,
            "symptom_specificity_penalty": limited_symptom_specificity_penalty,  # 制限後の症状特異性ペナルティ
            "ingredient_boost": limited_ingredient_boost,  # 成分ベーススコア
            "user_preference_bonus": user_preference_bonus,  # ユーザー要望ボーナス
            "life_stage_boost": life_stage_boost,  # ライフステージボーナス
            "sho_bonus": sho_bonus,  # 証ボーナス
            "risk_ingredient_penalty": limited_risk_penalty,  # 制限後のリスク成分ペナルティ
            "throat_bonus": limited_throat_bonus,  # 制限後のthroat_bonus
            "symptom_specific_boost": limited_symptom_boost,  # 制限後の症状特化型ブースト
            "multi_symptom_bonus": multi_symptom_bonus,  # MULTI_SYMPTOM_COMBINATIONSのボーナス（表示用）
            "multi_symptom_cold_bonus": limited_multi_symptom_cold_bonus,  # 複数症状（3症状以上）時の総合感冒薬への追加ボーナス
            "comprehensive_cold_bonus": limited_comprehensive_cold_bonus,  # 総合風邪薬優先推奨ボーナス
            "pattern_bonus": limited_pattern_bonus,  # 制限後の症状パターンボーナス
            "allergy_penalty": limited_allergy_penalty,  # 制限後のアレルギーペナルティ
            "allergy_boost": limited_allergy_boost,  # 制限後のアレルギーブースト
            "hangover_boost": limited_hangover_boost,  # 制限後の二日酔いブースト
            "ingredient_boost": limited_ingredient_boost,  # 成分ベースのボーナス
            "tiebreaker_boost": limited_tiebreaker_boost,  # タイブレーカーボーナス
            "base_score": base_score,  # 基本スコア（デバッグ用）
            "adjusted_base_score": adjusted_base_score,  # 調整後の基本スコア（デバッグ用）
            "adjustment_score": adjustment_score,  # 調整スコア（デバッグ用）
            "kampo_adjustment": kampo_adjustment,  # 漢方薬優先度調整（西洋薬優先の場合-0.2）
            "kakkonto_penalty": kakkonto_penalty  # 葛根湯の条件付き推奨ペナルティ
        }
    }
    
    # 相互作用警告がある場合は追加
    if has_interaction:
        result["interaction_warnings"] = interaction_warnings
    
    # 詳細ログの出力
    if threshold_pass_detail and (DEBUG_MODE or logger.level <= logging.DEBUG):
        logger.debug(f"📊 Threshold Pass/Fail Detail: {candidate.get('product_name', '')} - passed={threshold_pass_detail.get('passed', False)}, reason={threshold_pass_detail.get('reason', 'unknown')}, base_score_boost={threshold_pass_detail.get('base_score_boost', False)}, ingredient_boost={threshold_pass_detail.get('ingredient_boost', False)}, pattern_bonus={threshold_pass_detail.get('pattern_bonus', False)}, user_preference_bonus={threshold_pass_detail.get('user_preference_bonus', False)}, life_stage_boost={threshold_pass_detail.get('life_stage_boost', False)}, sho_bonus={threshold_pass_detail.get('sho_bonus', False)}")
    
    if sho_match_score and (DEBUG_MODE or logger.level <= logging.DEBUG):
        logger.debug(f"🔍 Sho Match Score: {candidate.get('product_name', '')} - sho={sho_match_score.get('sho', '不明')}, confidence={sho_match_score.get('confidence', 0.0):.2f}, reasons={sho_match_score.get('reasons', [])}, kyo_indicators={sho_match_score.get('kyo_indicators', [])}, jitsu_indicators={sho_match_score.get('jitsu_indicators', [])}")
    
    if contraindication_check.get("is_contraindicated", False):
        logger.warning(f"🚫 禁忌事項の除外: {candidate.get('product_name', '')} - {contraindication_check.get('reason', '')}")

    return result
