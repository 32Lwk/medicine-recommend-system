"""
推奨候補の最終化・スコア閾値適用

_enforce_symptom_match_threshold と _finalize_recommendations を提供。
"""

import logging
from typing import Dict, List

import os

from src.core.recommendation_constants import (
    MAJOR_ANALGESIC_MEDICINES,
    MIN_SYMPTOM_MATCH_MULTI,
    MIN_SYMPTOM_MATCH_SINGLE,
)
from src.core.scoring_utils import normalize_medicine_name_to_hankaku
from src.core.candidate_scoring import (
    _check_influenza_compatibility,
    _detect_body_part_specificity,
    _filter_antidiarrheal_without_diarrhea,
    _recheck_risk_ingredients,
    filter_by_efficacy_symptom_match,
    has_symptom_in_efficacy,
    is_exact_product_match,
)
from src.core.recommendation.recommendation_scoring import (
    calculate_symptom_specificity_penalty,
)

logger = logging.getLogger(__name__)
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"


def _enforce_symptom_match_threshold(
    candidates: List[Dict],
    nlu_result: Dict,
) -> List[Dict]:
    """
    症状適合度スコアの最低閾値を適用し、症状との関連が乏しい候補を除外
    """
    if not candidates:
        return candidates

    symptoms = nlu_result.get("symptoms", []) or []
    symptom_names = {s.get("name") for s in symptoms if s.get("name")}
    symptom_names_list = list(symptom_names)
    is_single_symptom = len(symptom_names) == 1
    threshold = (
        MIN_SYMPTOM_MATCH_SINGLE if is_single_symptom else MIN_SYMPTOM_MATCH_MULTI
    )

    filtered: List[Dict] = []
    for candidate in candidates:
        score_breakdown = candidate.get("score_breakdown", {}) or {}
        symptom_match = score_breakdown.get("symptom_match")

        # 主要解熱鎮痛薬の場合は除外しない（発熱のみの場合）
        product_name = candidate.get("product_name", "")
        product_name_norm = normalize_medicine_name_to_hankaku(product_name)
        is_major_analgesic = any(
            normalize_medicine_name_to_hankaku(m) in product_name_norm
            for m in MAJOR_ANALGESIC_MEDICINES
        )
        cold_symptoms = [
            "発熱",
            "咳",
            "鼻水",
            "のどの痛み",
            "頭痛",
            "悪寒",
            "くしゃみ",
            "鼻づまり",
        ]
        cold_symptom_count = sum(
            1 for s in symptoms if s.get("name") in cold_symptoms
        )
        is_fever_only = cold_symptom_count == 1 and any(
            s.get("name") == "発熱" for s in symptoms
        )

        if (
            is_fever_only
            and is_major_analgesic
            and "解熱鎮痛薬" in candidate.get("medicine_type", "")
        ):
            # 主要解熱鎮痛薬は発熱のみの場合、症状適合度が低くても除外しない
            filtered.append(candidate)
            if logger.level <= logging.INFO:
                logger.info(
                    f"✅ 主要解熱鎮痛薬のため症状適合度チェックをスキップ: {product_name} (symptom_match={symptom_match})"
                )
            continue

        # 二日酔いブーストがある医薬品は、症状適合度が低くても除外しない
        hangover_boost = score_breakdown.get("hangover_boost", 0.0)
        is_hangover_medicine = candidate.get("is_hangover", False)

        # 月経不順症状で成分ブーストがある場合の閾値緩和
        menstrual_symptoms = ["月経不順", "生理不順", "生理痛", "月経痛"]
        symptom_names_set = {s.get("name") for s in symptoms if s.get("name")}
        has_menstrual_symptom = any(
            symptom in symptom_names_set for symptom in menstrual_symptoms
        )

        # 成分ブーストの確認（当帰・芍薬を含む場合）
        ingredients = str(candidate.get("ingredients", "")).lower()
        has_ingredient_boost = False
        if has_menstrual_symptom:
            toki_keywords = [
                "トウキ",
                "当帰",
                "とうき",
                "トウキ末",
                "トウキ流エキス",
                "トウキエキス",
                "トウキ乾燥エキス",
            ]
            shakuyaku_keywords = [
                "シャクヤク",
                "芍薬",
                "しゃくやく",
                "シャクヤク末",
                "シャクヤクエキス",
                "シャクヤク乾燥エキス",
            ]
            has_toki = any(kw.lower() in ingredients for kw in toki_keywords)
            has_shakuyaku = any(
                kw.lower() in ingredients for kw in shakuyaku_keywords
            )
            product_name = str(candidate.get("product_name", "")).upper()
            efficacy = str(candidate.get("efficacy", "")).upper()
            has_toki_shakuyaku_san = (
                "当帰芍薬散" in candidate.get("product_name", "")
                or "トウキシャクヤクサン" in product_name
                or "当帰芍薬散" in efficacy
            )
            has_ingredient_boost = (
                has_toki and has_shakuyaku
            ) or has_toki_shakuyaku_san

        if hangover_boost > 0 or is_hangover_medicine:
            # 二日酔い向け医薬品は閾値を下げる
            adjusted_threshold = 0.0  # 二日酔いブーストがあれば症状適合度チェックをスキップ
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(
                    f"二日酔い医薬品のため閾値を0.0に調整: {candidate.get('product_name', '')} (boost={hangover_boost:.3f})"
                )
        elif has_menstrual_symptom and has_ingredient_boost:
            # 月経不順症状で成分ブーストがある場合、閾値を緩和
            adjusted_threshold = max(
                0.0, threshold - 0.15
            )  # 閾値を0.15下げる（例：0.35→0.20）
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(
                    f"月経不順症状+成分ブーストのため閾値を{threshold:.2f}から{adjusted_threshold:.2f}に緩和: {candidate.get('product_name', '')}"
                )
        else:
            adjusted_threshold = threshold

        # 効能に症状が含まれている場合は閾値を緩和（保険として維持）
        if symptom_match is not None and symptom_match < adjusted_threshold:
            has_efficacy_match = has_symptom_in_efficacy(
                candidate, symptom_names_list
            )
            if has_efficacy_match:
                adjusted_threshold = 0.21  # 30%緩和
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(
                        f"効能に症状が含まれているため閾値を{threshold:.2f}から{adjusted_threshold:.2f}に緩和: {candidate.get('product_name', '')}"
                    )

        if symptom_match is not None and symptom_match < adjusted_threshold:
            if logger.level <= logging.INFO:
                logger.info(
                    f"🚫 症状適合度が閾値未満のため候補を除外 (score={symptom_match:.2f}, threshold={adjusted_threshold:.2f}): "
                    f"{candidate.get('product_name', '')}"
                )
            continue
        filtered.append(candidate)

    return filtered


def _finalize_recommendations(
    candidates: List[Dict], nlu_result: Dict, influenza_risk: bool
) -> List[Dict]:
    """
    最終推奨の確定処理（責務を統合）

    Args:
        candidates: 候補医薬品リスト
        nlu_result: NLU解析結果
        influenza_risk: インフルエンザリスクの有無

    Returns:
        最終確定された候補リスト
    """
    # 1. インフルエンザ適合性チェック
    validated = _check_influenza_compatibility(candidates, influenza_risk)

    # 2. リスク成分の再チェック
    validated = _recheck_risk_ingredients(validated, nlu_result)

    # 3. 下痢情報がない腹痛単独相談では止瀉薬候補を除外
    validated = _filter_antidiarrheal_without_diarrhea(validated, nlu_result)

    # 3.5. 効能効果と症状のマッチングに基づくフィルタリング（単一症状限定医薬品の除外）
    validated = filter_by_efficacy_symptom_match(validated, nlu_result)

    # 4. 症状適合度スコアの最低閾値を適用
    validated = _enforce_symptom_match_threshold(validated, nlu_result)

    # 4.5. 性器周辺症状の場合、刺激の強い外用薬を除外
    user_body_part = nlu_result.get("user_body_part")
    if user_body_part == "delicate_area":
        filtered_candidates = []
        for candidate in validated:
            medicine_type = str(candidate.get("medicine_type", "")).lower()
            ingredients = str(candidate.get("ingredients", "")).lower()

            # 刺激の強い成分のキーワード
            strong_ingredients = [
                "メントール",
                "カンフル",
                "アンモニア",
                "サリチル酸",
                "メントール",
                "dl-カンフル",
                "l-メントール",
            ]
            has_strong_ingredient = any(
                ing in ingredients for ing in strong_ingredients
            )

            # 性器専用の医薬品は優先
            candidate_body_part = _detect_body_part_specificity(candidate)
            if candidate_body_part == "delicate_area":
                filtered_candidates.append(candidate)
            # 刺激の強い外用薬は除外
            elif "外用薬（皮膚）" in medicine_type or "外用" in medicine_type:
                if has_strong_ingredient:
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(
                            f"性器周辺症状: 刺激の強い外用薬を除外: {candidate.get('product_name', '')}"
                        )
                    continue  # この候補を除外
                else:
                    # 刺激の強い成分がない場合は残すが、警告を追加
                    candidate["delicate_area_warning"] = True
                    filtered_candidates.append(candidate)
            else:
                # 外用薬以外は残す
                filtered_candidates.append(candidate)

        validated = filtered_candidates
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(
                f"性器周辺症状: {len(validated)}件の候補をフィルタリング後"
            )

    # 4.6. 効能特異性が非常に低い医薬品を除外（症状に合わない医薬品を除外）
    from src.core.scoring_utils import calculate_efficacy_specificity_score

    filtered_by_efficacy = []
    for candidate in validated:
        # 効能特異性スコアを計算
        efficacy_specificity = calculate_efficacy_specificity_score(
            candidate, nlu_result
        )
        # 症状特異性ペナルティを計算
        symptom_specificity_penalty = calculate_symptom_specificity_penalty(
            candidate, nlu_result
        )

        # 浮動小数点比較用イプシロン
        EPSILON = 0.0001

        # 効能特異性が0.0（イプシロン比較）または非常に低い（0.1未満）かつ症状特異性ペナルティが-0.6以下の医薬品を除外
        efficacy = str(candidate.get("efficacy", "")).lower()
        product_name_lower = str(candidate.get("product_name", "")).lower()
        has_only_dysmenorrhea = (
            "生理痛" in efficacy or "月経痛" in efficacy
        ) and not any(
            kw in efficacy
            for kw in [
                "月経不順",
                "生理不順",
                "月経異常",
                "生理異常",
                "血の道症",
                "血の道",
            ]
        )

        # 大黄牡丹皮湯の判定（便秘傾向がない場合に除外）
        is_daioubotanpi = (
            "大黄牡丹皮湯" in product_name_lower
            or "だいおうぼたんぴとう" in product_name_lower
            or "ダイオウボタンピトウ" in product_name_lower
        )
        has_constipation_efficacy = (
            "便秘" in efficacy
            or "便通" in efficacy
            or "便秘の傾向" in efficacy
            or "便秘傾向" in efficacy
        )
        symptom_names_list = [
            s.get("name", "") for s in nlu_result.get("symptoms", [])
        ]
        has_constipation_symptom = "便秘" in symptom_names_list

        if is_daioubotanpi:
            logger.info(
                f"🔍 大黄牡丹皮湯チェック: {candidate.get('product_name', '')}, 効能に便秘関連: {has_constipation_efficacy}, 症状に便秘: {has_constipation_symptom}, 効能: {efficacy[:150]}..."
            )

        should_exclude = False
        if efficacy_specificity < 0.1 and symptom_specificity_penalty <= -0.6:
            should_exclude = True
        elif (
            efficacy_specificity < EPSILON
            and symptom_specificity_penalty <= -0.4
            and has_only_dysmenorrhea
        ):
            should_exclude = True
        elif (
            is_daioubotanpi
            and not has_constipation_efficacy
            and not has_constipation_symptom
        ):
            should_exclude = True
            logger.info(
                f"⚠️ 大黄牡丹皮湯を除外: {candidate.get('product_name', '')} (便秘傾向がないため, 効能: {efficacy[:150]}...)"
            )

        if should_exclude:
            product_name = candidate.get("product_name", "")
            efficacy_val = candidate.get("efficacy", "")
            logger.info(
                f"⚠️ 効能特異性が低く症状に合わない医薬品を除外: {product_name} (効能特異性: {efficacy_specificity:.2f}, 症状特異性ペナルティ: {symptom_specificity_penalty:.2f}, 効能: {efficacy_val[:100]}...)"
            )
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(
                    f"⚠️ 効能特異性が低く症状に合わない医薬品を除外: {product_name} (効能特異性: {efficacy_specificity:.2f}, 症状特異性ペナルティ: {symptom_specificity_penalty:.2f})"
                )
            continue

        filtered_by_efficacy.append(candidate)

    validated = filtered_by_efficacy

    # 5. スコアが0.0の候補を除外、0.3未満の候補を警告付きで残す
    priority_medicine_names_for_protection = [
        "ラムールQ",
        "ラムールＱ",
        "ラムールq",
        "ラムールｑ",
        "加味逍遙散",
        "カミショウヨウサン",
        "命の母ホワイト",
        "命の母 ホワイト",
        "ルナエール",
        "ルナフェミン",
        "桂枝茯苓丸",
        "ケイシブクリョウガン",
    ]

    final_candidates = []
    protected_medicines = []
    for candidate in validated:
        score = candidate.get("final_score", 0.0)
        product_name = candidate.get("product_name", "")
        product_name_lower = product_name.lower()

        # 期待される医薬品かどうかをチェック（部分一致も許可）
        is_priority = False
        for priority_name in priority_medicine_names_for_protection:
            priority_name_lower = priority_name.lower()
            if (
                product_name_lower == priority_name_lower
                or priority_name_lower in product_name_lower
                or product_name_lower in priority_name_lower
                or is_exact_product_match(product_name, [priority_name])
            ):
                is_priority = True
                protected_medicines.append(candidate)
                logger.info(
                    f"🔒 期待される医薬品をスコアフィルタリングから保護: {product_name} (スコア: {score:.3f}, 検索名: {priority_name})"
                )
                break

        # スコア0の候補を完全に除外（期待される医薬品は保護）
        if score <= 0.0:
            if is_priority:
                final_candidates.append(candidate)
                logger.info(
                    f"🔒 期待される医薬品をスコアフィルタリングから保護して追加: {product_name} (スコア: {score:.3f})"
                )
            else:
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(
                        f"⚠️ スコア0の候補を除外: {product_name} (スコア: {score:.3f})"
                    )
                continue

        if score < 0.3:
            candidate["low_score_warning"] = True
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(
                    f"⚠️ 低スコア警告: {product_name} (スコア: {score:.3f})"
                )

        if not is_priority:
            final_candidates.append(candidate)

    return final_candidates
