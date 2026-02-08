"""
スコア計算

candidate_scoring から分離（SRP改善）。
表示スコア・スコア差保証などの計算を行う。
"""

import logging
import os
from typing import Dict, List

logger = logging.getLogger(__name__)
_DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'


def ensure_score_difference(display_scores: List[float], floor_map: Dict[int, float]) -> List[float]:
    """
    スコア差の保証と衝突回避（最小0.2%の差を強制）

    Args:
        display_scores: 上位3件のdisplay_scoreリスト（整数変換前）
        floor_map: ランク別最低保証スコア（{1: 60.0, 2: 50.0, 3: 40.0}）

    Returns:
        調整後のdisplay_scoreリスト
    """
    if len(display_scores) < 2:
        return display_scores

    adjusted_scores = list(display_scores)
    min_difference = 0.0025

    # 1位-2位の差をチェック
    if len(adjusted_scores) >= 2:
        diff_1_2 = adjusted_scores[0] - adjusted_scores[1]
        if diff_1_2 < min_difference:
            reduction = min_difference - diff_1_2
            new_score_2 = adjusted_scores[1] - reduction
            floor_2 = floor_map.get(2, 50.0)
            if new_score_2 >= floor_2:
                adjusted_scores[1] = new_score_2
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"スコア差調整（1-2位）: 2位を {adjusted_scores[1]:.1f}% → {new_score_2:.1f}% に調整（差: {diff_1_2:.2f}% → {min_difference:.2f}%）")
            else:
                adjusted_scores[0] = adjusted_scores[1] + min_difference
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"スコア差調整（1-2位、Floor保護）: 1位を {display_scores[0]:.1f}% → {adjusted_scores[0]:.1f}% に調整")

    # 2位-3位の差をチェック
    if len(adjusted_scores) >= 3:
        diff_2_3 = adjusted_scores[1] - adjusted_scores[2]
        if diff_2_3 < min_difference:
            reduction = min_difference - diff_2_3
            new_score_3 = adjusted_scores[2] - reduction
            floor_3 = floor_map.get(3, 40.0)
            if new_score_3 >= floor_3:
                adjusted_scores[2] = new_score_3
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"スコア差調整（2-3位）: 3位を {adjusted_scores[2]:.1f}% → {new_score_3:.1f}% に調整（差: {diff_2_3:.2f}% → {min_difference:.2f}%）")
            else:
                adjusted_scores[1] = adjusted_scores[2] + min_difference
                if adjusted_scores[0] - adjusted_scores[1] < min_difference:
                    adjusted_scores[0] = adjusted_scores[1] + min_difference
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"スコア差調整（2-3位、Floor保護）: 2位を {display_scores[1]:.1f}% → {adjusted_scores[1]:.1f}% に調整")

    return adjusted_scores


def calculate_display_score(rank: int, s_final: float, s_min: float, s_max: float, max_possible: float) -> float:
    """
    ランク別最低保証スコアを考慮した表示用スコアを計算（単調増加写像）

    Args:
        rank: ランク（1, 2, 3）
        s_final: 減点適用後のfinal_score
        s_min: 上位3件の最小final_score
        s_max: 上位3件の最大final_score
        max_possible: MaxPossibleScore（1.0 - completeness_penalty）

    Returns:
        display_score: 表示用スコア（40-100%の範囲、整数変換前）
    """
    floor_map = {
        1: 60.0,
        2: 50.0,
        3: 40.0
    }
    floor_rank = floor_map.get(rank, 40.0)
    max_possible_percent = max_possible * 100.0
    score_range = s_max - s_min
    if score_range > 0:
        score_norm = (s_final - s_min) / score_range
    else:
        score_norm = 0.5
    score_norm = max(0.0, min(1.0, score_norm))
    display_score = floor_rank + (max_possible_percent - floor_rank) * score_norm
    return display_score


def calculate_display_score_absolute(rank: int, raw_score: float, completeness_penalty: float) -> float:
    """
    絶対評価ベースの表示用スコアを計算

    Args:
        rank: ランク（1, 2, 3）
        raw_score: 減点適用前のraw_score
        completeness_penalty: 不足情報による減点（0.0-0.15）

    Returns:
        display_score: 表示用スコア（小数点第1位）
    """
    raw_score_clipped = min(raw_score, 1.0)
    base_score = raw_score_clipped * 100.0
    rank_adjustment = (rank - 1) * 1.5
    penalty_percent = completeness_penalty * 100.0
    display_score = (base_score - rank_adjustment) * (1.0 - penalty_percent / 100.0)
    display_score = round(display_score, 1)
    display_score = max(0.0, min(100.0, display_score))
    return display_score
