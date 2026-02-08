"""
統合スコア計算（1候補あたり）

calculate_symptom_specificity_penalty を提供。
calculate_final_score / calculate_medicine_score は依存が多く
ensure_ingredient_diversity 等と循環するため rule_based_recommendation に残し、
当モジュールからは re-export しない。
"""

import logging
from typing import Dict

from src.core.recommendation_constants import (
    COMPOUND_MEDICINE_INDICATORS,
    MULTI_SYMPTOM_COMBINATIONS,
    SYMPTOM_CATEGORY_PENALTY,
)

logger = logging.getLogger(__name__)
DEBUG_MODE = __import__("os").getenv("DEBUG_MODE", "false").lower() == "true"


def calculate_symptom_specificity_penalty(candidate: Dict, nlu_result: Dict) -> float:
    """
    症状特異性に基づくペナルティを計算
    効能特異性に応じてペナルティを緩和する

    Args:
        candidate: 候補医薬品情報
        nlu_result: NLU解析結果

    Returns:
        ペナルティスコア（負の値、0.0が最大）
    """
    try:
        symptoms = nlu_result.get("symptoms", [])
        if not symptoms:
            return 0.0

        symptom_names = [s.get("name") for s in symptoms]
        medicine_type = candidate.get("medicine_type", "")

        # 効能特異性スコアを計算（外部関数を使用）
        from src.core.scoring_utils import calculate_efficacy_specificity_score

        efficacy_specificity = calculate_efficacy_specificity_score(candidate, nlu_result)

        # 浮動小数点比較用イプシロン
        EPSILON = 0.0001

        # 効能特異性が0.0（イプシロン比較）の場合（症状が効能に全く含まれていない場合）は強いペナルティを適用
        if efficacy_specificity < EPSILON:
            # 単一症状の場合、効能に症状が含まれていない場合は大幅減点
            if len(symptom_names) == 1:
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(
                        f"症状特異性ペナルティ: 効能に症状が含まれていないため大幅減点 (効能特異性{efficacy_specificity:.2f})"
                    )
                return -0.5  # 効能に症状が含まれていない場合は強いペナルティ

        # 単一症状の場合
        if len(symptom_names) == 1:
            symptom_name = symptom_names[0]

            # 症状カテゴリ間優先表からペナルティを取得
            if symptom_name in SYMPTOM_CATEGORY_PENALTY:
                penalty_table = SYMPTOM_CATEGORY_PENALTY[symptom_name]
                if medicine_type in penalty_table:
                    base_penalty = penalty_table[medicine_type]
                    # 単一症状の場合、総合感冒薬（風邪薬）には効能特異性に関係なくペナルティを適用
                    # 効能に症状が含まれていても、単一症状に対して複合薬は過剰処方となる
                    if base_penalty < 0 and medicine_type == "風邪薬":
                        # 総合感冒薬の場合は、効能特異性に関係なくフルペナルティを適用（単一症状時は過剰処方）
                        # 効能特異性が高い場合でも、単一症状に対して複合薬は不適切
                        penalty = base_penalty  # -0.5をそのまま適用（緩和しない）
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(
                                f"症状特異性ペナルティ（単一症状・総合感冒薬）: {symptom_name} + {medicine_type} = {penalty:.2f} (効能特異性{efficacy_specificity:.2f}, フルペナルティ適用)"
                            )
                        return penalty

                    # その他の医薬品タイプの場合、従来のロジックを適用
                    # 効能に症状が明記されている場合（efficacy_specificity >= 0.5）は、ペナルティを適用しない
                    # 効能に症状が含まれているということは、その医薬品が症状に対して適切であることを示している
                    if efficacy_specificity >= 0.5:
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(
                                f"症状特異性ペナルティ: 効能に症状が明記されているためペナルティを適用しない (効能特異性{efficacy_specificity:.2f})"
                            )
                        return 0.0  # ペナルティを適用しない

                    # 効能特異性に応じてペナルティを緩和（緩和率を調整してペナルティを強化）
                    if efficacy_specificity >= 0.95:
                        penalty = base_penalty * 0.25  # 0.17から0.25に変更（緩和を減らす）
                    elif efficacy_specificity >= 0.8:
                        penalty = base_penalty * 0.6  # 0.5から0.6に変更
                    elif efficacy_specificity >= EPSILON:  # イプシロン比較（0.5未満の場合）
                        penalty = base_penalty * 0.7  # 30%緩和
                    elif efficacy_specificity < EPSILON:  # イプシロン比較
                        # 効能特異性が0.0（イプシロン比較）の場合は、ベースペナルティを強化
                        penalty = base_penalty * 1.5  # ペナルティを1.5倍に強化
                    else:
                        penalty = base_penalty
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(
                            f"症状特異性ペナルティ: {symptom_name} + {medicine_type} = {base_penalty} → {penalty:.2f} (効能特異性{efficacy_specificity:.2f})"
                        )
                    return penalty

            # 複合薬識別パターンによるチェック
            # 単一症状なのに複合薬（風邪薬など）が推奨される場合
            if medicine_type in COMPOUND_MEDICINE_INDICATORS:
                compound_info = COMPOUND_MEDICINE_INDICATORS[medicine_type]
                required_count = compound_info.get("required_symptoms_count", 2)
                if len(symptom_names) < required_count:
                    # 単一症状の場合、総合感冒薬（風邪薬）には効能特異性に関係なくペナルティを適用
                    # 効能に症状が含まれていても、単一症状に対して複合薬は過剰処方となる
                    if medicine_type == "風邪薬":
                        # 総合感冒薬の場合は、効能特異性に関係なくフルペナルティを適用（単一症状時は過剰処方）
                        # 効能特異性が高い場合でも、単一症状に対して複合薬は不適切
                        base_penalty = -0.5
                        penalty = base_penalty  # -0.5をそのまま適用（緩和しない）
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(
                                f"複合薬ペナルティ（単一症状・総合感冒薬）: {symptom_name} + {medicine_type} = {penalty:.2f} (効能特異性{efficacy_specificity:.2f}, フルペナルティ適用)"
                            )
                        return penalty

                    # その他の複合薬の場合は従来のロジックを適用
                    # 効能に症状が明記されている場合（efficacy_specificity >= 0.5）は、複合薬ペナルティを適用しない
                    # 効能に症状が含まれているということは、その医薬品が症状に対して適切であることを示している
                    if efficacy_specificity >= 0.5:
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(
                                f"複合薬ペナルティ: 効能に症状が明記されているためペナルティを適用しない (効能特異性{efficacy_specificity:.2f})"
                            )
                        return 0.0  # ペナルティを適用しない

                    # デフォルトペナルティ（カテゴリ間優先表にない場合）
                    base_penalty = -0.3
                    # 効能特異性に応じてペナルティを緩和（緩和率を調整してペナルティを強化）
                    if efficacy_specificity >= 0.95:
                        penalty = base_penalty * 0.25  # 0.17から0.25に変更
                    elif efficacy_specificity >= 0.8:
                        penalty = base_penalty * 0.6  # 0.5から0.6に変更
                    elif efficacy_specificity >= EPSILON:  # イプシロン比較（0.5未満の場合）
                        penalty = base_penalty * 0.7  # 30%緩和
                    elif efficacy_specificity < EPSILON:  # イプシロン比較
                        # 効能特異性が0.0（イプシロン比較）の場合は、ベースペナルティを強化
                        penalty = base_penalty * 1.5  # ペナルティを1.5倍に強化
                    else:
                        penalty = base_penalty
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(
                            f"複合薬ペナルティ: 単一症状({symptom_name})に対して複合薬({medicine_type}) = {base_penalty} → {penalty:.2f} (効能特異性{efficacy_specificity:.2f})"
                        )
                    return penalty

        # 複数症状の場合
        elif len(symptom_names) >= 2:
            from itertools import combinations

            total_adjustment = 0.0

            # 効能特異性が非常に低い場合（症状が効能に全く含まれていない、またはほとんど含まれていない場合）は強いペナルティを適用
            # このペナルティは他のペナルティよりも優先される
            if efficacy_specificity < 0.1:  # 0.0だけでなく、0.1未満も対象とする
                # 複数症状の場合でも、効能に症状が全く含まれていない場合は大幅減点
                unrelated_penalty = -0.4  # 効能が全く関係ない場合のペナルティ
                total_adjustment += unrelated_penalty
                logger.info(
                    f"症状特異性ペナルティ（複数症状・効能無関係）: {candidate.get('product_name', '')} - 効能に症状が含まれていないため大幅減点 (効能特異性{efficacy_specificity:.2f}), penalty={unrelated_penalty:.2f}, total_adjustment={total_adjustment:.2f}"
                )
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(
                        f"症状特異性ペナルティ（複数症状・効能無関係）: 効能に症状が含まれていないため大幅減点 (効能特異性{efficacy_specificity:.2f}), penalty={unrelated_penalty:.2f}"
                    )
            else:
                # 効能特異性が0.1以上の場合は、症状カテゴリ間優先表からペナルティを適用
                penalties = []
                for symptom_name in symptom_names:
                    if symptom_name in SYMPTOM_CATEGORY_PENALTY:
                        penalty_table = SYMPTOM_CATEGORY_PENALTY[symptom_name]
                        if medicine_type in penalty_table:
                            if "風邪薬" in medicine_type:
                                continue
                            penalty_value = penalty_table[medicine_type]
                            penalties.append(penalty_value)
                            if DEBUG_MODE or logger.level <= logging.DEBUG:
                                logger.debug(
                                    f"症状特異性ペナルティ（複数症状）: symptom={symptom_name}, medicine_type={medicine_type}, penalty={penalty_value}"
                                )

                if penalties:
                    base_penalty = max(penalties)
                    if base_penalty < 0:
                        if efficacy_specificity >= 0.95:
                            base_penalty *= 0.25  # 0.17から0.25に変更
                        elif efficacy_specificity >= 0.8:
                            base_penalty *= 0.6  # 0.5から0.6に変更
                        total_adjustment += base_penalty
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(
                                f"症状特異性ペナルティ（複数症状・最終）: medicine_type={medicine_type}, penalties={penalties}, base_penalty={base_penalty:.2f}, total_adjustment={total_adjustment:.2f}, efficacy_specificity={efficacy_specificity:.2f}"
                            )
                            logger.debug(
                                f"症状特異性ペナルティ（複数症状）: {medicine_type} = {penalties} → {base_penalty:.2f} (効能特異性{efficacy_specificity:.2f})"
                            )

            # 複数症状の組み合わせによるペナルティのみを適用（ボーナスはcalculate_symptom_specific_boostで処理）
            for combo in combinations(symptom_names, 2):
                combo_key = frozenset(combo)
                adjustments = MULTI_SYMPTOM_COMBINATIONS.get(combo_key)
                if adjustments and medicine_type in adjustments:
                    adjustment = adjustments[medicine_type]
                    # ペナルティ（負の値）のみを適用
                    if adjustment < 0.0:
                        total_adjustment += adjustment
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(
                                f"複数症状ペナルティ適用: combo={combo_key}, medicine_type={medicine_type}, adjustment={adjustment:.2f}, total_adjustment={total_adjustment:.2f}"
                            )
                            logger.debug(
                                f"複数症状ペナルティ: {combo_key} × {medicine_type} = {adjustment:.2f}"
                            )
                    # ボーナス（正の値）は無視（calculate_symptom_specific_boostで処理される）

            # 「生理痛」のみが効能の医薬品に対するペナルティ（月経不順が主訴の場合）
            # 効能効果欄に「生理痛」のみが含まれ、かつ「月経不順」「月経異常」「血の道症」が含まれない場合にペナルティ適用
            efficacy = str(candidate.get("efficacy", ""))
            has_menstrual_irregularity = any(
                symptom in ["月経不順", "生理不順", "月経異常", "生理異常", "血の道症"]
                for symptom in symptom_names
            )
            has_dysmenorrhea = any(
                symptom in ["生理痛", "月経痛"] for symptom in symptom_names
            )

            # 効能効果欄の確認（大文字小文字を区別しないチェック）
            efficacy_lower = efficacy.lower()
            has_dysmenorrhea_in_efficacy = (
                "生理痛" in efficacy_lower or "月経痛" in efficacy_lower
            )
            has_menstrual_irregularity_in_efficacy = (
                "月経不順" in efficacy_lower
                or "生理不順" in efficacy_lower
                or "月経異常" in efficacy_lower
                or "生理異常" in efficacy_lower
                or "血の道症" in efficacy_lower
                or "血の道" in efficacy_lower
            )

            # 「生理痛」のみが効能で、月経不順が主訴の場合
            # 効能特異性が0.1未満の場合でも、「生理痛」のみが効能の場合は追加でペナルティを適用
            if (
                has_dysmenorrhea_in_efficacy
                and not has_menstrual_irregularity_in_efficacy
                and has_menstrual_irregularity
            ):
                # 症状に「生理痛」が含まれていない場合のみペナルティを適用
                if not has_dysmenorrhea:
                    # 「生理痛」のみが効能で、主訴が「月経不順」の場合、追加ペナルティを適用
                    # 効能特異性が0.1未満の場合は既に-0.4のペナルティが適用されているため、追加で-0.3のペナルティを適用（合計-0.7）
                    # 効能特異性が0.1以上の場合は-0.25のペナルティを適用
                    if efficacy_specificity < 0.1:
                        dysmenorrhea_penalty = -0.3  # 効能特異性が0.1未満の場合は追加で-0.3のペナルティ
                    else:
                        dysmenorrhea_penalty = -0.25  # 効能特異性が0.1以上の場合は-0.25のペナルティ
                    total_adjustment += dysmenorrhea_penalty
                    logger.info(
                        f"「生理痛」のみが効能のペナルティ適用: {candidate.get('product_name', '')} (効能: {efficacy[:100]}...), penalty={dysmenorrhea_penalty:.2f}, efficacy_specificity={efficacy_specificity:.2f}, total_adjustment={total_adjustment:.2f}"
                    )
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(
                            f"「生理痛」のみが効能のペナルティ適用: {candidate.get('product_name', '')} (効能: {efficacy[:100]}...), penalty={dysmenorrhea_penalty:.2f}, efficacy_specificity={efficacy_specificity:.2f}"
                        )

            # ペナルティのみを返す（負の値または0）
            # この関数はペナルティのみを返し、ボーナスは別途calculate_symptom_specific_boostで処理される
            if total_adjustment != 0.0:
                final_penalty = min(0.0, total_adjustment)
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(
                        f"calculate_symptom_specificity_penalty最終結果: {candidate.get('product_name', '')} - total_adjustment={total_adjustment:.2f}, final_penalty={final_penalty:.2f}, efficacy_specificity={efficacy_specificity:.2f}"
                    )
                # 負の値のみを返す（正の値が含まれている場合は0を返す）
                return final_penalty

            return 0.0
    except Exception as e:
        logger.warning(f"症状特異性ペナルティ計算エラー: {e}")
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            import traceback

            logger.debug(f"詳細: {traceback.format_exc()}")
        return 0.0  # エラー時は安全側に倒す
