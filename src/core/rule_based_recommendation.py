"""
ルールベース医薬品推奨システム

ChatGPT APIはNLU（症状抽出）のみに使用し、
医薬品推奨は登録販売者の判断を再現するルールベース/スコアリング型アルゴリズムで実装

後方互換のため、以下のシンボルは他モジュールから再エクスポートされています:
- 定数: recommendation_constants から import
- キャッシュ: nlu_service から import
- 安全性: safety_filter から import
- ログ: recommendation_logger から import
"""

# 後方互換のため再エクスポート（他モジュールから import 可能）
__all__ = [
    "rule_based_medicine_recommendation",
    "rule_based_recommendation",
    "determine_kampo_sho",
    "detect_influenza_risk",
    "check_missing_information",
    "hybrid_nlu_extraction",
    "extract_symptoms_with_gpt",
    "simple_pattern_matching_nlu",
    "generate_explanation",
    "generate_usage_notes_and_consultation_with_gpt",
    "generate_default_usage_notes_and_consultation",
    "check_safety_contraindications",
    "check_sleep_medicine_safety",
    "log_recommendation_session",
    "get_cached_nlu_result",
    "set_cached_nlu_result",
    "clear_nlu_cache",
    "get_candidate_medicines",
    "filter_by_efficacy_symptom_match",
    "calculate_final_score",
    "calculate_medicine_score",
    "calculate_ingredient_based_boost",
    "check_ingredient_overlap",
    "classify_medicine_mechanism",
    "DEBUG_MODE",
    "SYMPTOM_DICTIONARY",
]

import pandas as pd
import os
import json
import re
import logging
import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from openai import OpenAI
from src.core.scoring_utils import normalize_text, normalize_medicine_name_to_hankaku
from src.utils.candidate_normalizer import normalize_candidate_for_scoring

# ロガー設定
logger = logging.getLogger(__name__)
DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'


def _mark_rb_pipeline_step(step: str) -> None:
    """rule_based 内部区間の pipeline_perf マーク（計測専用・失敗時は無視）。"""
    try:
        from src.services.pipeline_perf import mark_pipeline_step

        mark_pipeline_step(step)
    except Exception:
        pass


def merge_pollen_combination_into_usage(
    usage_and_consultation: Dict,
    recommendations: List[Dict],
    nlu_result: Dict,
    user_text: str,
) -> Dict:
    """花粉症併用注意を usage_notes に追記（rb 内/flow 外の両方から利用）。"""
    try:
        from src.core.candidate_scoring import is_pollen_rhinitis_focus
        from src.core.recommendation.pollen_combination_advice import build_pollen_combination_advice

        symptom_names = [s.get("name") for s in nlu_result.get("symptoms", []) if s.get("name")]
        if is_pollen_rhinitis_focus(
            user_text, symptom_names, str(nlu_result.get("medicine_type") or "")
        ):
            combo_html = build_pollen_combination_advice(recommendations)
            if combo_html:
                base_notes = usage_and_consultation.get("usage_notes") or ""
                usage_and_consultation = dict(usage_and_consultation)
                usage_and_consultation["usage_notes"] = (
                    f"{base_notes}\n\n{combo_html}" if base_notes else combo_html
                )
    except Exception as combo_err:
        logger.warning("花粉症併用注意の生成でエラー: %s", combo_err)
    return usage_and_consultation

# CSVファイルのパス設定（プロジェクトルート基準）
from src import PROJECT_ROOT
BASE_DIR = PROJECT_ROOT
DATA_DIR = os.path.join(BASE_DIR, "data")
CSV_PATH = os.path.join(DATA_DIR, "otc_medicine_data.csv")

# 定数・データ構造は recommendation_constants からインポート（SRP改善）
from src.core.recommendation_constants import (
    DEFAULT_ADULT_AGE,
    PEDIATRIC_KEYWORDS,
    PEDIATRIC_USAGE_KEYWORDS,
    RED_FLAG_SYMPTOMS,
    PREGNANCY_SYMPTOMS,
    FEMALE_SPECIFIC_SYMPTOMS,
    DOCTOR_REFERRAL_CONDITIONS,
    CONTRAINDICATION_RULES,
    SCORING_WEIGHTS,
    RISK_INGREDIENTS_EXCLUDE,
    ANTIDIARRHEAL_INGREDIENTS,
    ANTIDIARRHEAL_KEYWORDS,
    MIN_SYMPTOM_MATCH_SINGLE,
    MIN_SYMPTOM_MATCH_MULTI,
    SPECIFIC_USE_PATTERNS,
    SPECIFIC_USE_EXCLUSION_KEYWORDS,
    COMPOUND_MEDICINE_INDICATORS,
    BODY_PART_SPECIFIC_KEYWORDS,
    SYMPTOM_CATEGORY_PENALTY,
    MULTI_SYMPTOM_COMBINATIONS,
    SYMPTOM_PATTERN_OPTIMIZATION,
    THROAT_SYMPTOM_TOKENS,
    THROAT_KEYWORD_TOKENS,
    THROAT_LIQUID_TOKENS,
    THROAT_SPECIFIC_INGREDIENTS,
    STOMACH_MUCOSAL_PROTECTANTS,
    STOMACH_MEDICINE_PRIORITY,
    CONSTIPATION_MEDICINE_PRIORITY,
    IRRITANT_LAXATIVE_INGREDIENTS,
    MAJOR_ANALGESIC_MEDICINES,
    ANALGESIC_PRIORITY,
    MENSTRUAL_MEDICINE_PRIORITY,
    THROAT_TOPICAL_PRIORITY,
    SLEEP_DISORDER_PRIORITY,
    WOUND_MEDICINE_PRIORITY,
    BURN_SEVERITY_KEYWORDS,
    RISK_INGREDIENTS_OVERLAP,
    MENSTRUAL_ONLY_PRODUCTS,
    MENSTRUAL_GENERAL_EFFICACY_KEYWORDS,
    MENSTRUAL_SYMPTOM_KEYWORDS,
    CHICKENPOX_KEYWORDS,
    TRUSTED_MANUFACTURERS,
    STRONG_PRODUCTS,
    STRONG_INGREDIENTS,
)

from src.core.dictionary_loader import load_ingredient_dictionary, load_symptom_dictionary

# 後方互換: app.py 等から SYMPTOM_DICTIONARY として参照される
SYMPTOM_DICTIONARY = load_symptom_dictionary()
from src.core.missing_info_service import (
    check_missing_information,
    generate_symptom_detail_questions_with_gpt,
    detect_burn_severity,
)
from src.core.explanation_generator import (
    generate_explanation,
    generate_individual_usage_notes_with_gpt,
    generate_usage_notes_and_consultation_with_gpt,
    generate_default_usage_notes_and_consultation,
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
from src.core.recommendation.recommendation_finalizer import (
    _enforce_symptom_match_threshold,
    _finalize_recommendations,
)
from src.core.candidate_scoring import (
    _candidate_has_throat_liquid_signature,
    _has_motion_sickness_symptom,
    _is_kakkonto_medicine,
    _is_motion_sickness_medicine,
    _is_pediatric_specific,
    is_specific_use_medicine,
    is_comprehensive_cold_medicine,
    _is_symptom_matching_specific_use,
    _contains_risk_ingredient,
    _extract_min_age_value,
    _has_antidiarrheal_signal,
    _filter_antidiarrheal_without_diarrhea,
    has_symptom_in_efficacy,
    filter_by_efficacy_symptom_match,
    get_candidate_medicines,
    is_exact_product_match,
    _detect_body_part_specificity,
    calculate_symptom_match_score,
    calculate_age_fit_score,
    calculate_body_part_match_score,
    calculate_ingredient_based_boost,
    is_contraindicated,
    ensure_score_difference,
    calculate_display_score,
    calculate_display_score_absolute,
    extract_main_ingredients,
    check_ingredient_overlap,
    classify_medicine_mechanism,
    _recheck_risk_ingredients,
    _check_influenza_compatibility,
    detect_influenza_risk,
)

# ================================================================================
# 1. ヘルパー関数（候補取得・スコアリング関連は candidate_scoring から import）
# THROAT_*, STOMACH_*, MENSTRUAL_*, その他定数は recommendation_constants から import
# ================================================================================

# ================================================================================
# 2. NLU関数（ChatGPT APIで症状抽出のみ）
# ================================================================================

# NLUキャッシュ・NLU関数は nlu_service に移行（SRP改善）
from src.core.nlu_service import (
    get_cached_nlu_result,
    set_cached_nlu_result,
    clear_nlu_cache,
    get_cached_medicine_type,
    set_cached_medicine_type,
    get_cached_translation,
    set_cached_translation,
    simple_pattern_matching_nlu,
    _extract_body_part_from_user_text,
    hybrid_nlu_extraction,
    extract_symptoms_with_gpt,
)

# ================================================================================
# 3. 安全性フィルタ層（safety_filter からインポート）
# ================================================================================

from src.core.safety_filter import (
    check_safety_contraindications,
    check_sleep_medicine_safety,
)

# ================================================================================
# 4. 候補薬取得とスコアリング（filter_by_efficacy_symptom_match, get_candidate_medicines は candidate_scoring から import）
# ensure_ingredient_diversity は recommendation.ingredient_diversity から import（SRP改善）
# ================================================================================

from src.core.recommendation.ingredient_diversity import ensure_ingredient_diversity

from src.core.recommendation.final_score_calculator import calculate_final_score

# calculate_medicine_score は calculate_final_score のエイリアス（テスト互換性のため）
def calculate_medicine_score(candidate: Dict, nlu_result: Dict, user_info: Dict = None, user_text: str = "") -> Dict:
    """
    calculate_final_score のエイリアス関数（テスト互換性のため）
    
    Args:
        candidate: 候補医薬品情報
        nlu_result: NLU解析結果
        user_info: ユーザー情報（デフォルト: None）
        user_text: ユーザー入力テキスト（デフォルト: ""）
    
    Returns:
        calculate_final_score と同じ形式のスコア結果辞書
    """
    if user_info is None:
        user_info = {}
    return calculate_final_score(candidate, nlu_result, user_info, user_text)

# ================================================================================
# 5. 不足情報のチェックと質問生成（missing_info_service から import）
# ================================================================================

def rule_based_recommendation(
    user_text: str,
    user_info: Dict,
    medicine_df: pd.DataFrame,
    client: OpenAI,
    top_n: int = 3,
    session_id: str = None,
    *,
    precomputed_nlu: Optional[Dict] = None,
    llm_user_text: Optional[str] = None,
    precomputed_missing_info: Optional[Dict] = None,
    defer_explanation_llm: bool = False,
) -> Dict:
    """
    ルールベース医薬品推奨システムのメイン関数（全医薬品種類対応）
    
    Args:
        user_text: ユーザーの症状入力
        user_info: {
            'age': int,
            'gender': str,
            'pregnant': bool,
            'breastfeeding': bool,
            'current_medications': List[str],
            'allergies': List[str]
        }
        medicine_df: 医薬品データフレーム
        client: OpenAI client
        top_n: 推奨する医薬品の数
    
    Returns:
        推奨結果
    """
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"\n{'='*80}")
        logger.debug(f"ルールベース医薬品推奨システム 開始")
        logger.debug(f"{'='*80}")
        logger.debug(f"症状文: {user_text}")
        logger.debug(f"ユーザー情報: {user_info}")
    
    # やけどの程度判定（ガードレール）- 早期チェック
    burn_severity, is_burn_doctor_referral = detect_burn_severity(user_text)
    if is_burn_doctor_referral:
        logger.info("やけどの重度判定により、医師受診を推奨します")
        return {
            "status": "doctor_referral",
            "is_doctor_referral": True,
            "reason": "重度のやけどの可能性があります",
            "recommended_medicines": [],
            "usage_notes": "",
            "doctor_consultation": "⚠️ 重度のやけどの可能性があります。水ぶくれがある、痛みを感じない、顔面や広範囲のやけどの場合は、すぐに医師の診察を受けてください。市販薬の使用は控えてください。",
            "error_message": "重度のやけどの可能性があります。水ぶくれがある、痛みを感じない、顔面や広範囲のやけどの場合は、すぐに医師の診察を受けてください。市販薬の使用は控えてください。",
            "severity": burn_severity
        }
    
    # 入力検証: 空入力・意味のない文字列のチェック
    if not user_text or not user_text.strip():
        logger.warning("空の入力が検出されました")
        return {
            "status": "error",
            "reason": "症状を入力してください",
            "recommended_medicines": [],
            "error_message": "症状を入力してください。具体的な症状名（例：頭痛、発熱、のどの痛みなど）を含めて記述してください。",
            "technical_details": f"入力テキスト: '{user_text}', 空文字列または空白のみ"
        }
    
    # 意味のない文字列のチェック
    user_text_stripped = user_text.strip()
    
    # 症状辞書との照合: canonical_name または synonyms に完全一致する場合は3文字チェックをスキップ
    symptom_dict = load_symptom_dictionary()
    is_valid_short_symptom = False
    for canonical_name, entry in symptom_dict.items():
        if user_text_stripped == canonical_name:
            is_valid_short_symptom = True
            break
        for syn in entry.get("synonyms", []):
            if user_text_stripped == syn:
                is_valid_short_symptom = True
                break
        if is_valid_short_symptom:
            break
    
    # 極端に短い文字列（3文字未満）: 症状辞書に完全一致しない場合のみエラー
    if not is_valid_short_symptom and len(user_text_stripped) < 3:
        logger.warning(f"極端に短い入力が検出されました: {user_text_stripped}")
        return {
            "status": "error",
            "reason": "症状を詳しく入力してください",
            "recommended_medicines": [],
            "error_message": "症状を詳しく入力してください（3文字以上）。具体的な症状名を含めて記述してください（例：「頭が痛い」「熱がある」など）。",
            "technical_details": f"入力テキスト: '{user_text_stripped}', 文字数: {len(user_text_stripped)}（3文字未満）"
        }
    
    # 繰り返し文字のみのチェック（例: 「あああ」「テストテスト」）
    if len(set(user_text_stripped)) <= 2 and len(user_text_stripped) >= 3:
        # 同じ文字が3回以上繰り返されている場合
        char_counts = {}
        for char in user_text_stripped:
            char_counts[char] = char_counts.get(char, 0) + 1
        if max(char_counts.values()) >= 3:
            logger.warning(f"繰り返し文字のみの入力が検出されました: {user_text_stripped}")
            return {
                "status": "error",
                "reason": "症状を入力してください",
                "recommended_medicines": [],
                "error_message": "症状を入力してください。具体的な症状名を含めて記述してください（例：「頭が痛い」「熱がある」など）。",
                "technical_details": f"入力テキスト: '{user_text_stripped}', 文字数: {len(user_text_stripped)}, 繰り返し文字パターン検出"
            }
    
    # 医療関連キーワードが一切含まれていない場合のチェック（簡易版）
    # 注: より厳密なチェックはNLU結果に依存するため、ここでは基本的なチェックのみ
    # 重要: load_symptom_dictionary()に登録されているすべての症状に対応するキーワードを網羅的に追加
    # これにより、考慮漏れによって推奨処理が停止することを防ぐ
    medical_keywords = [
        # 基本キーワード（必須）
        "痛", "熱", "咳", "鼻", "喉", "頭", "胃", "下痢", "便秘", "吐", "めまい",
        "かゆ", "発疹", "不眠", "疲労", "症状", "病気", "薬", "医", "病",
        
        # 風邪関連キーワード（「風邪を完治したい」などの表現に対応）
        "風邪", "かぜ", "風邪をひ", "風邪気味", "風邪っぽい", "風邪の症状",
        "風邪を完治", "風邪を治", "風邪を直", "完治", "治したい", "治す", "直したい", "直す",
        
        # 風邪関連症状（load_symptom_dictionary()から抽出）
        "発熱", "熱がある", "熱っぽい", "高熱", "微熱", "体温", "熱",
        "頭痛", "頭が痛い", "ズキズキ", "頭が重い", "偏頭痛",
        "のど", "喉", "咽頭", "声がれ", "のどの痛み", "喉の痛み", "喉の腫れ",
        "せき", "咳", "咳が出る", "咳込む", "空咳",
        "痰", "たん", "痰が絡む", "痰が出る",
        "鼻水", "鼻みず", "鼻汁", "鼻が出る", "水っぽい",
        "鼻づまり", "鼻詰まり", "鼻が詰まる", "鼻閉",
        "くしゃみ", "クシャミ",
        "悪寒", "寒気", "さむけ", "ゾクゾク",
        "関節痛", "関節の痛み", "節々", "関節が痛い",
        "筋肉痛", "筋肉の痛み", "体が痛い", "筋肉が痛い",
        
        # 解熱鎮痛薬関連症状
        "生理痛", "月経痛", "生理の痛み", "下腹部痛", "生理", "月経",
        "歯痛", "歯が痛い", "歯の痛み", "歯",
        
        # 鼻炎用薬関連症状
        "鼻汁過多", "鼻水が多い", "鼻水がとまらない",
        "なみだ目", "涙目", "涙",
        
        # 胃腸薬関連症状
        "胃痛", "胃が痛い", "胃の痛み", "胃部痛", "みぞおち",
        "腹痛", "お腹が痛い", "腹部痛", "おなかが痛い", "腹が痛い", "お腹",
        "軟便", "水様便", "便がゆるい", "便",
        "便が出ない", "便通がない", "便が硬い",
        "吐き気", "むかつき", "気持ち悪い", "嘔吐感", "嘔吐",
        "胸やけ", "胸焼け", "胃もたれ", "胃の重い感じ", "消化が悪い", "胃の不快感",
        
        # 外用薬関連症状
        "かゆみ", "かゆい", "痒み", "痒い", "痒", "皮膚のかゆみ",
        "ブツブツ", "赤い斑点", "皮膚の異常",
        "湿疹", "皮膚炎", "かぶれ", "皮膚の炎症", "皮膚",
        "水虫", "白癬", "足の水虫", "指の間",
        "打撲", "打ち身", "青あざ", "内出血",
        "捻挫", "くじいた", "靭帯損傷",
        "肩こり", "肩の凝り", "肩の痛み", "首肩", "肩", "こり",
        "腰痛", "腰", "腰の痛み",
        
        # 目薬関連症状
        "目の充血", "目が赤い", "充血", "目の血走り", "目", "眼",
        "目の疲れ", "眼精疲労", "目が疲れる", "目の重い感じ", "疲れ",
        "目のかゆみ", "目がかゆい", "目の痒み",
        
        # 睡眠・精神関連症状
        "不眠", "眠れない", "睡眠不足", "寝つきが悪い", "眠", "睡眠",
        "眩暈", "ふらつき", "立ちくらみ",
        "乗り物酔い", "車酔い", "船酔い", "バス酔い", "酔い", "乗り物に酔う", "乗物酔い",
        "疲労感", "疲れ", "だるい", "倦怠感", "倦怠",
        "イライラ", "いらいら", "焦燥感", "落ち着かない",
        "不安", "心配", "憂鬱", "落ち込み",
        "ストレス", "緊張", "プレッシャー",
        
        # 重症疑い症状（RED_FLAG_SYMPTOMS）
        "呼吸困難", "呼吸が苦しい", "息苦しい", "息ができない", "息切れ",
        "38.5度以上", "39度", "40度", "熱が下がらない",
        "胸痛", "胸が痛い", "胸の痛み", "胸部痛", "心臓が痛い", "胸が締め付けられる",
        "意識障害", "意識がもうろう", "意識がない", "気を失う", "意識不明", "ぼーっと",
        "激しい頭痛", "突然の頭痛", "今まで経験したことのない頭痛", "頭が割れる", "耐えられない頭痛",
        "血便", "便に血が混じる", "黒い便", "タール便",
        "喀血", "血を吐く", "吐血",
        "激しい腹痛", "お腹が痛くて動けない", "耐えられない腹痛",
        "顔面麻痺", "顔が動かない", "口が曲がる", "顔の半分が動かない",
        "手足の麻痺", "手足が動かない", "力が入らない", "しびれが続く", "しびれ",
        "持続する嘔吐", "何度も吐く", "止まらない嘔吐", "嘔吐が続く",
        
        # その他の一般的な医療関連キーワード
        "耳", "耳の痛み", "耳鳴り",
        "口内炎", "口", "口の中",
        "喉頭", "気管", "気管支",
        "消化", "食欲", "食欲不振",
        "血圧", "血圧が高い", "血圧が低い",
        "動悸", "心拍", "脈",
        "発汗", "汗", "多汗",
        "冷え", "冷え性", "冷える",
        "むくみ", "浮腫",
        "しこり", "腫れ", "腫れる",
        "炎症", "感染", "菌",
        "ウイルス", "細菌",
        "アレルギー", "アレルギー症状",
        "かぶれ", "接触性皮膚炎",
        "やけど", "火傷", "熱傷",
        "切り傷", "擦り傷", "傷",
        "骨折", "骨",
        "筋肉", "筋",
        "神経", "神経痛",
        "リウマチ", "関節リウマチ",
        "痛風",
        "貧血", "貧血気味",
        "低血糖", "高血糖", "血糖",
        "コレステロール",
        "脂質",
        "肝臓", "肝機能",
        "腎臓", "腎機能",
        "膀胱", "尿", "排尿",
        "月経", "生理", "月経不順",
        "更年期", "ホルモン",
        "妊娠", "妊婦",
        "授乳", "母乳",
        "小児", "子供", "こども", "幼児", "乳児",
        "高齢者", "老人",
        "処方", "処方箋",
        "副作用", "効能", "効果",
        "用法", "用量", "服用", "飲む", "飲み",
        "錠剤", "カプセル", "粉薬", "シロップ", "液剤",
        "軟膏", "クリーム", "ローション", "スプレー",
        "点眼", "点鼻", "点耳",
        # 風邪関連のキーワード
        "風邪", "かぜ", "風邪をひ", "風邪気味", "風邪っぽい", "風邪の症状",
        "風邪を完治", "風邪を治", "風邪を直", "治したい", "治す"
    ]
    has_medical_keyword = any(keyword in user_text_stripped for keyword in medical_keywords)
    
    # ステップ1: NLU（症状抽出）- キーワードチェックの前に実行して、症状が検出される場合はキーワードチェックをスキップ
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"\n--- ステップ1: NLU（症状抽出） ---")
    if precomputed_nlu is not None:
        nlu_result = dict(precomputed_nlu)
    else:
        from src.handlers.chat.nlu_resolve import resolve_nlu_for_recommendation

        nlu_result = resolve_nlu_for_recommendation(
            user_text, user_info, client, session_id=session_id
        )
    
    # やけどの場合、NLU結果から強度を確認（ガードレールで検出されなかった場合）
    if burn_severity is not None and not is_burn_doctor_referral:
        # NLU結果からやけどの強度を確認
        nlu_severity = nlu_result.get("severity", "中等度")
        symptoms_list = nlu_result.get("symptoms", [])
        # やけどの症状がある場合、その強度を確認
        burn_symptoms = [s for s in symptoms_list if "やけど" in s.get("name", "")]
        if burn_symptoms:
            burn_symptom_severity = burn_symptoms[0].get("severity", "中等度")
            # 軽度・中等度は市販薬で対処可能、重度は受診勧奨
            if burn_symptom_severity == "重度" or nlu_severity == "重度":
                logger.info("やけどの重度判定（NLU）により、医師受診を推奨します")
                return {
                    "status": "doctor_referral",
                    "is_doctor_referral": True,
                    "reason": "重度のやけどの可能性があります",
                    "recommended_medicines": [],
                    "usage_notes": "",
                    "doctor_consultation": "⚠️ 重度のやけどの可能性があります。水ぶくれがある、痛みを感じない、顔面や広範囲のやけどの場合は、すぐに医師の診察を受けてください。市販薬の使用は控えてください。",
                    "error_message": "重度のやけどの可能性があります。水ぶくれがある、痛みを感じない、顔面や広範囲のやけどの場合は、すぐに医師の診察を受けてください。市販薬の使用は控えてください。",
                    "severity": "重度"
                }
    
    # NLU結果を確認し、症状が検出されている場合はキーワードチェックをスキップ
    symptoms_detected = nlu_result.get("symptoms", [])
    has_detected_symptoms = len(symptoms_detected) > 0
    
    # 症状が検出されていない場合、select_symptoms_via_gptで抽出を試みる
    gpt_input = (llm_user_text or user_text).strip()
    if not has_detected_symptoms:
        try:
            from src.core.medicine_logic import select_symptoms_via_gpt
            logger.info(f"🔍 select_symptoms_via_gptで症状抽出を試みます: {gpt_input}")
            symptom_extraction_result = select_symptoms_via_gpt(gpt_input, client=client)
            logger.debug(f"🔍 select_symptoms_via_gptの結果: {symptom_extraction_result}")
            
            # select_symptoms_via_gptは直接 {'status': 'success', 'symptoms': [...], 'message': '...'} を返す
            if symptom_extraction_result and 'symptoms' in symptom_extraction_result:
                extracted_symptom_names = symptom_extraction_result['symptoms']
                logger.debug(f"🔍 extracted_symptom_names: {extracted_symptom_names}")
                
                if extracted_symptom_names:
                    # 抽出された症状をnlu_resultに統合
                    symptoms_list = []
                    for symptom_name in extracted_symptom_names:
                        symptoms_list.append({
                            "name": symptom_name,
                            "severity": "中等度",
                            "duration": "不明",
                            "body_part": None
                        })
                    nlu_result["symptoms"] = symptoms_list
                    has_detected_symptoms = True
                    # confidence_scoreも更新
                    nlu_result["confidence_score"] = 0.7  # フォールバック抽出のため中程度の信頼度
                    logger.info(f"✅ select_symptoms_via_gptで症状を抽出: {extracted_symptom_names}")
                else:
                    logger.warning(f"⚠️ select_symptoms_via_gptで症状が抽出されませんでした（空のリスト）")
            else:
                logger.warning(f"⚠️ select_symptoms_via_gptの結果に'symptoms'キーがありません: {symptom_extraction_result}")
        except Exception as e:
            logger.warning(f"⚠️ select_symptoms_via_gptでの症状抽出に失敗: {e}")
            import traceback
            traceback.print_exc()
    
    # 医療キーワードがなく、かつ短い文字列の場合、かつ症状も検出されていない場合のみエラー
    if not has_medical_keyword and len(user_text_stripped) < 10 and not has_detected_symptoms:
        logger.warning(f"医療関連キーワードが含まれていない入力が検出されました（症状も検出されませんでした）: {user_text_stripped}")
        return {
            "status": "error",
            "reason": "症状を入力してください",
            "recommended_medicines": [],
            "error_message": "症状を入力してください（例: 頭痛、発熱、のどの痛みなど）。より具体的な症状名を含めて記述してください。",
            "technical_details": f"入力テキスト: {user_text_stripped}, 文字数: {len(user_text_stripped)}, 医療キーワード検出: {has_medical_keyword}, 症状検出: {has_detected_symptoms}"
        }
    
    # 部位情報の抽出
    symptoms = nlu_result.get("symptoms", [])
    user_body_part = None
    if symptoms:
        # 最初の症状から部位情報を抽出
        first_symptom = symptoms[0]
        symptom_name = first_symptom.get("name", "")
        user_body_part = _extract_body_part_from_user_text(user_text, symptom_name)
        if user_body_part:
            nlu_result["user_body_part"] = user_body_part
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"部位情報を抽出: {user_body_part} (症状: {symptom_name})")
    
    # confidenceチェック（0.4未満の場合はGPTフォールバックを検討）
    confidence_score = nlu_result.get('confidence_score', 0.0)
    symptoms_count = len(nlu_result.get("symptoms", []))
    
    logger.info(f"NLU信頼度スコア: {confidence_score:.2f}, 検出症状数: {symptoms_count}")
    
    # ステップ1.5: 不足情報のチェック
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"\n--- ステップ1.5: 不足情報のチェック ---")
    if precomputed_missing_info is not None:
        missing_info_result = dict(precomputed_missing_info)
    else:
        missing_info_result = check_missing_information(user_info, nlu_result, user_text, client)
    _mark_rb_pipeline_step("rb_missing_info_done")
    
    # 不足情報による減点を事前に計算（後で使用するため）
    from src.core.user_detection import calculate_completeness_penalty
    penalty_result = calculate_completeness_penalty(missing_info_result)
    completeness_penalty = penalty_result.get('completeness_penalty', 0.0)
    missing_fields_detail = penalty_result.get('missing_fields_detail', {})
    
    if missing_info_result["has_missing_info"]:
        priority = missing_info_result["priority"]
        logger.info(f"不足情報検出（優先度: {priority}）")
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"不足フィールド: {missing_info_result['missing_fields']}")
        
        # 症状が検出されていない場合のみ推奨を中断
        # 曖昧症状の質問だけがcriticalの場合は推奨を継続
        missing_fields = missing_info_result.get('missing_fields', [])
        if "symptoms" in missing_fields:
            # 症状が検出されていない場合のみ推奨を中断
            logger.warning(f"症状が検出されていないため推奨を中断します")
            symptom_names = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
            return {
                "status": "missing_critical_info",
                "reason": "症状が検出されていません",
                "missing_fields": missing_info_result['missing_fields'],
                "questions": missing_info_result['questions'],
                "critical_questions": missing_info_result.get('critical_questions', []),
                "recommended_medicines": [],
                "nlu_result": nlu_result,
                "confidence_score": confidence_score,
                "error_message": "入力されたテキストから症状を検出できませんでした。具体的な症状名（例：頭痛、発熱、のどの痛み、かゆみなど）を含めて記述してください。",
                "technical_details": f"入力テキスト: '{user_text}', 検出された症状: {symptom_names}, 信頼度スコア: {confidence_score:.2f}, 不足フィールド: {missing_fields}",
                "timestamp": datetime.now().isoformat()
            }
        else:
            # 曖昧症状の質問がある場合でも推奨は継続
            logger.info(f"推奨は続行しますが、追加質問も表示します")
    
    # ステップ2: インフルエンザリスク検出
    try:
        from config.llm_flags import is_reco_cold_nlu_v2_enabled
        from src.core.recommendation.cold_symptom_expansion import merge_cold_symptoms

        if is_reco_cold_nlu_v2_enabled():
            nlu_result = merge_cold_symptoms(nlu_result, user_text)
    except ImportError:
        pass

    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"\n--- ステップ2: インフルエンザリスク検出 ---")
    influenza_risk, influenza_reason = detect_influenza_risk(nlu_result, user_text)
    if influenza_risk:
        logger.warning(f"インフルエンザの可能性: {influenza_reason}")
    else:
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"インフルエンザリスク: なし")
    
    # ステップ3: 安全性チェック
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"\n--- ステップ3: 安全性チェック ---")
    from src.services.processing_mark import mark_phase

    mark_phase(session_id, "safety", detail_code="contra_check")
    safety_result = check_safety_contraindications(user_info, nlu_result)
    
    if safety_result["requires_escalation"]:
        logger.warning(f"エスカレーション必要: {safety_result['escalation_reason']}")
        return {
            "status": "escalation_required",
            "reason": safety_result["escalation_reason"],
            "warnings": safety_result["warnings"],
            "recommended_medicines": [],
            "nlu_result": nlu_result,
            "influenza_risk": influenza_risk,
            "influenza_reason": influenza_reason,
            "timestamp": datetime.now().isoformat()
        }
    
    scoring_user_info = dict(user_info)
    
    # 消化器症状と産後・授乳中の情報を追加
    try:
        from src.core.user_detection import detect_digestive_sensitivity, detect_postpartum_breastfeeding
        
        # 消化器症状の検出
        digestive_info = detect_digestive_sensitivity(user_text, nlu_result, user_info)
        if digestive_info.get("has_digestive_sensitivity", False):
            scoring_user_info['digestive_sensitivity'] = True
            logger.info(f"🔍 消化器症状検出: {digestive_info.get('reason', '')}")
        
        # 産後・授乳中の判定
        postpartum_info = detect_postpartum_breastfeeding(user_text, nlu_result, user_info)
        if postpartum_info.get("is_postpartum", False):
            scoring_user_info['postpartum'] = True
            logger.info(f"🔍 産後検出: {postpartum_info.get('reason', '')}")
        if postpartum_info.get("is_breastfeeding", False):
            scoring_user_info['breastfeeding'] = True
            logger.info(f"🔍 授乳中検出: {postpartum_info.get('reason', '')}")
    except Exception as e:
        logger.warning(f"消化器症状・産後・授乳中の検出でエラー: {e}")
    
    # user_messageを追加（痛みフラグボーナス用）
    scoring_user_info['user_message'] = user_text

    try:
        from src.core.user_detection import extract_user_preferences

        _prefs = extract_user_preferences(user_text, nlu_result, scoring_user_info)
        scoring_user_info["user_preferences"] = _prefs
        scoring_user_info["prefers_kampo"] = _prefs.get("prefers_kampo", False)
        scoring_user_info["prefers_not_kampo"] = _prefs.get("prefers_not_kampo", False)
    except Exception as e:
        logger.warning(f"ユーザー要望の抽出に失敗: {e}")
        scoring_user_info.setdefault("user_preferences", None)

    age_imputed = False
    if scoring_user_info.get('age') is None:
        scoring_user_info['age'] = DEFAULT_ADULT_AGE
        age_imputed = True
        # age_imputedフラグを追加（calculate_age_fit_scoreで使用）
        scoring_user_info['age_imputed'] = True

    # ステップ4: 候補医薬品取得（インフルエンザリスクを考慮）
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"\n--- ステップ4: 候補医薬品取得 ---")
    mark_phase(session_id, "medicine_select", detail_code="candidate_search")
    candidates = get_candidate_medicines(
        nlu_result,
        medicine_df,
        user_text,
        influenza_risk,
        user_preferences=scoring_user_info.get("user_preferences"),
        preference_user_info=scoring_user_info,
    )

    try:
        from src.core.recommendation.preference_candidate_filter import (
            filter_candidates_by_preferences,
        )

        candidates = filter_candidates_by_preferences(
            candidates,
            scoring_user_info.get("user_preferences"),
            nlu_result=nlu_result,
            user_info=scoring_user_info,
        )
    except Exception as pref_filter_err:
        logger.warning("嗜好候補フィルタでエラー: %s", pref_filter_err)

    try:
        from config.llm_flags import is_reco_sports_doping_filter_enabled
        from src.services.medicine_discovery_routing import has_sports_medicine_context

        if (
            is_reco_sports_doping_filter_enabled()
            and has_sports_medicine_context(user_text)
        ):
            _pre_doping = len(candidates)
            candidates = [
                c
                for c in candidates
                if str(c.get("doping_prohibited") or "").strip() != "禁止物質あり"
            ]
            if len(candidates) != _pre_doping:
                logger.info(
                    "🏃 sports doping filter: candidates %s -> %s",
                    _pre_doping,
                    len(candidates),
                )
    except ImportError:
        pass

    # 初期候補数を記録
    initial_candidate_count = len(candidates)
    
    # 睡眠改善薬専用の安全性チェック（候補医薬品取得後、スコアリング前）
    # 症状から医薬品種類を判定
    medicine_type = None
    symptoms = nlu_result.get("symptoms", [])
    for symptom in symptoms:
        symptom_name = symptom.get("name")
        if symptom_name in load_symptom_dictionary():
            types = load_symptom_dictionary()[symptom_name].get("medicine_types", [])
            if "睡眠障害" in types:
                medicine_type = "睡眠障害"
                break
    
    # 睡眠障害カテゴリの場合、専用の安全性チェックを実行
    if medicine_type == "睡眠障害":
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"\n--- ステップ3.5: 睡眠改善薬専用安全性チェック ---")
        sleep_safety_result = check_sleep_medicine_safety(user_text, user_info, nlu_result, medicine_type)
        
        if not sleep_safety_result["should_recommend"]:
            # 推奨を停止し、医師受診を促す
            logger.warning(f"睡眠改善薬の推奨を停止: {sleep_safety_result['escalation_reason']}")
            return {
                "status": "escalation_required",
                "reason": sleep_safety_result["escalation_reason"],
                "warnings": sleep_safety_result["warnings"],
                "recommended_medicines": [],
                "alternative_therapies": sleep_safety_result.get("alternative_therapies", []),
                "critical_questions": sleep_safety_result.get("critical_questions", []),
                "nlu_result": nlu_result,
                "influenza_risk": influenza_risk,
                "influenza_reason": influenza_reason,
                "timestamp": datetime.now().isoformat()
            }
        
        # 推奨は継続するが、警告と代替療法を保存
        if sleep_safety_result.get("warnings"):
            safety_result["warnings"].extend(sleep_safety_result["warnings"])
        # alternative_therapiesとcritical_questionsは後で使用するため、nlu_resultに保存
        nlu_result["sleep_alternative_therapies"] = sleep_safety_result.get("alternative_therapies", [])
        nlu_result["sleep_critical_questions"] = sleep_safety_result.get("critical_questions", [])
    
    if not candidates:
        logger.warning("該当する候補医薬品が見つかりませんでした")
        symptom_names = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        try:
            from config.llm_flags import is_reco_sports_doping_filter_enabled
            from src.services.medicine_discovery_routing import has_sports_medicine_context

            if (
                is_reco_sports_doping_filter_enabled()
                and has_sports_medicine_context(user_text)
            ):
                esc_reason = (
                    "競技前に使用可能な市販薬（ドーピング禁止物質を含まないもの）が"
                    "見つかりませんでした。アンチドーピング規定を確認のうえ、"
                    "薬剤師または医師にご相談ください。"
                )
                return {
                    "status": "escalation_required",
                    "reason": esc_reason,
                    "warnings": safety_result["warnings"],
                    "recommended_medicines": [],
                    "nlu_result": nlu_result,
                    "influenza_risk": influenza_risk,
                    "influenza_reason": influenza_reason,
                    "timestamp": datetime.now().isoformat(),
                }
        except ImportError:
            pass
        return {
            "status": "no_candidates",
            "reason": "該当する医薬品が見つかりませんでした",
            "warnings": safety_result["warnings"],
            "recommended_medicines": [],
            "nlu_result": nlu_result,
            "confidence_score": confidence_score,
            "error_message": f"検出された症状（{', '.join(symptom_names) if symptom_names else 'なし'}）に対して、適切な市販薬が見つかりませんでした。症状をより具体的に記述するか、医療機関を受診することをお勧めします。",
            "technical_details": f"検出症状: {symptom_names}, 医薬品の種類: {nlu_result.get('medicine_type', '不明')}, 信頼度スコア: {confidence_score:.2f}, インフルエンザリスク: {influenza_risk}",
            "timestamp": datetime.now().isoformat()
        }

    # 小児用医薬品フィルタリング（15歳以上のユーザー、または年齢不明の場合にも適用）
    user_age = scoring_user_info.get('age')
    # 年齢が15歳以上、または年齢不明の場合でも小児専用製品を除外
    # （効能に「小児の」が含まれている場合は年齢不明でも除外）
    if user_age is None or user_age >= 15:
        # 15歳以上のユーザー、または年齢不明の場合には小児専用製品を除外
        before_filter = len(candidates)
        candidates = [c for c in candidates if not _is_pediatric_specific(c)]
        after_filter = len(candidates)
        if after_filter == 0:
            logger.warning("15歳以上のユーザーのため、小児専用製品を除外した結果、候補がなくなりました")
            symptom_names = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
            return {
                "status": "no_candidates",
                "reason": "適切な医薬品が見つかりませんでした",
                "warnings": safety_result["warnings"],
                "recommended_medicines": [],
                "nlu_result": nlu_result,
                "confidence_score": confidence_score,
                "error_message": f"15歳以上のユーザーのため、小児専用製品を除外した結果、検出された症状（{', '.join(symptom_names) if symptom_names else 'なし'}）に対して適切な医薬品が見つかりませんでした。医療機関を受診することをお勧めします。",
                "technical_details": f"ユーザー年齢: {user_age}歳, 検出症状: {symptom_names}, フィルタ前候補数: {before_filter}, フィルタ後候補数: {after_filter}, 信頼度スコア: {confidence_score:.2f}",
                "timestamp": datetime.now().isoformat()
            }
        elif before_filter != after_filter:
            if user_age is None:
                logger.info(f"年齢不明のユーザーのため小児専用製品を{before_filter - after_filter}件除外しました")
            else:
                logger.info(f"15歳以上のユーザーのため小児専用製品を{before_filter - after_filter}件除外しました")
    elif age_imputed:
        # 年齢未入力の場合も従来通り除外
        before_filter = len(candidates)
        candidates = [c for c in candidates if not _is_pediatric_specific(c)]
        after_filter = len(candidates)
        if after_filter == 0:
            logger.warning("年齢未入力のため、小児専用製品を除外した結果、候補がなくなりました")
            symptom_names = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
            return {
                "status": "no_candidates",
                "reason": "年齢未入力のため適切な医薬品が見つかりませんでした",
                "warnings": safety_result["warnings"],
                "recommended_medicines": [],
                "nlu_result": nlu_result,
                "confidence_score": confidence_score,
                "error_message": f"年齢未入力のため、小児専用製品を除外した結果、検出された症状（{', '.join(symptom_names) if symptom_names else 'なし'}）に対して適切な医薬品が見つかりませんでした。年齢を入力するか、医療機関を受診することをお勧めします。",
                "technical_details": f"年齢: 未入力（デフォルト年齢{scoring_user_info.get('age')}歳で評価）, 検出症状: {symptom_names}, フィルタ前候補数: {before_filter}, フィルタ後候補数: {after_filter}, 信頼度スコア: {confidence_score:.2f}",
                "timestamp": datetime.now().isoformat()
            }
        elif before_filter != after_filter:
            logger.info(f"年齢未入力のため小児専用製品を{before_filter - after_filter}件除外しました")
    
    # 乗り物酔い薬のフィルタリング（乗り物酔いの症状がない場合は除外）
    if candidates:
        has_motion_sickness = _has_motion_sickness_symptom(nlu_result, user_text)
        before_motion_filter = len(candidates)
        
        # 二日酔いが検出されている場合は、乗り物酔い薬を強制的に除外
        user_text_lower = user_text.lower()
        hangover_keywords = ["二日酔い", "二日酔", "宿酔", "悪酔い", "悪酔", "飲み過ぎ", "飲みすぎ"]
        is_hangover_case = any(kw in user_text_lower for kw in hangover_keywords)
        
        if is_hangover_case or not has_motion_sickness:
            # 二日酔いの場合、または乗り物酔いの症状がない場合は、乗り物酔い薬を除外
            candidates = [c for c in candidates if not _is_motion_sickness_medicine(c)]
            after_motion_filter = len(candidates)
            if before_motion_filter != after_motion_filter:
                if is_hangover_case:
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"二日酔いが検出されたため、乗り物酔い薬を{before_motion_filter - after_motion_filter}件除外しました")
                else:
                    logger.info(f"乗り物酔い症状がないため、乗り物酔い薬を{before_motion_filter - after_motion_filter}件除外しました")
        else:
            logger.info("乗り物酔い症状が検出されたため、乗り物酔い薬も推奨対象に含めます")
        
        # フィルタリング後に候補がなくなった場合の処理
        if not candidates:
            logger.warning("フィルタリング後、候補医薬品がなくなりました")
            symptom_names = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
            return {
                "status": "no_candidates",
                "reason": "該当する医薬品が見つかりませんでした",
                "warnings": safety_result["warnings"],
                "recommended_medicines": [],
                "nlu_result": nlu_result,
                "confidence_score": confidence_score,
                "error_message": f"フィルタリング後、検出された症状（{', '.join(symptom_names) if symptom_names else 'なし'}）に対して適切な医薬品が見つかりませんでした。症状をより具体的に記述するか、医療機関を受診することをお勧めします。",
                "technical_details": f"検出症状: {symptom_names}, 乗り物酔い症状: {has_motion_sickness}, フィルタ前候補数: {before_motion_filter}, フィルタ後候補数: {after_motion_filter}, 信頼度スコア: {confidence_score:.2f}",
                "timestamp": datetime.now().isoformat()
            }
    
    # ステップ5: 二段階スコアリング（高速化）
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"\n--- ステップ5: スコアリング（二段階方式） ---")
    else:
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug("ステップ5: スコアリング開始")
    mark_phase(session_id, "medicine_select", detail_code="scoring")
    
    # ステップ5.1: 簡易スコアリング（高速）
    def calculate_quick_score(candidate: Dict, nlu_result: Dict, user_info: Dict) -> float:
        """簡易スコア（症状マッチ、効能特異性、年齢適合性、症状特異性ペナルティを含む）"""
        from src.core.scoring_utils import calculate_efficacy_specificity_score
        symptom_score = calculate_symptom_match_score(candidate, nlu_result)
        efficacy_score = calculate_efficacy_specificity_score(candidate, nlu_result)
        age_score = calculate_age_fit_score(candidate, user_info)
        
        # 主要解熱鎮痛薬のボーナス（発熱のみまたは頭痛のみの場合）
        major_analgesic_bonus = 0.0
        symptom_names = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        cold_symptoms = ["発熱", "咳", "鼻水", "のどの痛み", "頭痛", "悪寒", "くしゃみ", "鼻づまり"]
        cold_symptom_count = sum(1 for symptom in symptom_names if symptom in cold_symptoms)
        is_fever_only = cold_symptom_count == 1 and "発熱" in symptom_names
        is_headache_only = cold_symptom_count == 1 and "頭痛" in symptom_names
        
        if is_fever_only or is_headache_only:
            product_name = candidate.get('product_name', '')
            product_name_norm = normalize_medicine_name_to_hankaku(product_name)
            is_major_analgesic = any(
                normalize_medicine_name_to_hankaku(m) in product_name_norm
                for m in MAJOR_ANALGESIC_MEDICINES
            )
            if is_major_analgesic and '解熱鎮痛薬' in candidate.get('medicine_type', ''):
                # 主要解熱鎮痛薬にボーナスを付与（quick_scoreで優先されるように）
                major_analgesic_bonus = 0.3
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"quick_score 主要解熱鎮痛薬ボーナス: {product_name} = +{major_analgesic_bonus}")
        
        # 簡易版の症状特異性ペナルティ（複数症状時の薬効調整）
        symptom_penalty = 0.0
        symptoms = nlu_result.get("symptoms", [])
        symptom_names = [s.get("name") for s in symptoms]
        medicine_type = candidate.get("medicine_type", "")
        
        # 症状パターンマッチングによる最適化ボーナス
        pattern_bonus = 0.0
        # 単一症状の場合はpattern_bonusを適用しない（特化薬を優先するため）
        is_single_symptom_for_pattern = len(symptom_names) == 1
        if not is_single_symptom_for_pattern:
            pattern_info = match_symptom_pattern(nlu_result)
            if pattern_info:
                bonuses = pattern_info.get("bonuses", {})
                product_name = candidate.get('product_name', '')
                ingredients = str(candidate.get('ingredients', '')).lower()
                throat_specificity_level = candidate.get('throat_specificity_level', 'none')
                
                # 「のど痛み+発熱」の場合、総合感冒薬（喉向き）にボーナス
                if "のどの痛み" in symptom_names and "発熱" in symptom_names:
                    if '風邪薬' in medicine_type:
                        if throat_specificity_level == "component_and_efficacy":
                            pattern_bonus = 0.25
                        elif throat_specificity_level == "efficacy_only":
                            pattern_bonus = 0.15
                    elif '解熱鎮痛薬' in medicine_type:
                        pattern_bonus = 0.45  # 0.35から0.45に増加（2位優先のため強化）
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"quick_score pattern_bonus適用: medicine_type=解熱鎮痛薬, product_name={product_name}, pattern_bonus={pattern_bonus}")
                    elif '外用薬（のど）' in medicine_type or ('外用薬' in medicine_type and "のどの痛み" in symptom_names):
                        pattern_bonus = 0.45  # 0.35から0.45に増加（3位優先のため強化）
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"quick_score pattern_bonus適用: medicine_type=外用薬（のど）, product_name={product_name}, pattern_bonus={pattern_bonus}")
        else:
            # pattern_infoがNoneの場合もログ出力（DEBUGレベル）
            if '解熱鎮痛薬' in medicine_type or '外用薬（のど）' in medicine_type:
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"quick_score pattern_info=None: medicine_type={medicine_type}, product_name={candidate.get('product_name', '')}, symptom_names={symptom_names}")
        
        # 単一症状（発熱のみ）の場合、解熱鎮痛薬にボーナスを付与、総合感冒薬にペナルティ
        if is_single_symptom_for_pattern and "発熱" in symptom_names:
            if '解熱鎮痛薬' in medicine_type:
                pattern_bonus = 0.3  # 単一症状（発熱のみ）の場合、解熱鎮痛薬を優先
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"quick_score pattern_bonus適用（単一症状・発熱）: medicine_type=解熱鎮痛薬, product_name={candidate.get('product_name', '')}, pattern_bonus={pattern_bonus}")
            elif '風邪薬' in medicine_type:
                pattern_bonus = -0.2  # 単一症状（発熱のみ）の場合、総合感冒薬にペナルティ
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"quick_score pattern_bonus適用（単一症状・発熱）: medicine_type=風邪薬, product_name={candidate.get('product_name', '')}, pattern_bonus={pattern_bonus}")
        
        if len(symptom_names) >= 2:
            # のどの痛み + 発熱のパターン（既存ロジックは維持）
            if "のどの痛み" in symptom_names and "発熱" in symptom_names:
                if "解熱鎮痛薬" in medicine_type:
                    symptom_penalty = 0.0
                elif "風邪薬" in medicine_type:
                    symptom_penalty = 0.25
        
        # 二日酔いブーストを簡易スコアにも適用
        hangover_quick_boost = candidate.get('hangover_boost', 0.0)
        
        # 年齢適合性も含めて精度向上（重みは症状:効能:年齢 = 0.5:0.3:0.2）
        # 症状パターンボーナス、二日酔いブースト、主要解熱鎮痛薬ボーナスも追加
        quick_score_result = (symptom_score * 0.5 + efficacy_score * 0.3 + age_score * 0.2 + symptom_penalty + pattern_bonus + hangover_quick_boost + major_analgesic_bonus)
        
        # 解熱鎮痛薬と外用薬（のど）のquick_score計算の詳細をログ出力（DEBUGレベル）
        if '解熱鎮痛薬' in medicine_type or '外用薬（のど）' in medicine_type:
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"quick_score計算詳細: medicine_type={medicine_type}, product_name={candidate.get('product_name', '')}, symptom_score={symptom_score:.3f}, efficacy_score={efficacy_score:.3f}, age_score={age_score:.3f}, symptom_penalty={symptom_penalty:.3f}, pattern_bonus={pattern_bonus:.3f}, hangover_boost={hangover_quick_boost:.3f}, major_analgesic_bonus={major_analgesic_bonus:.3f}, quick_score={quick_score_result:.3f}")
        
        return quick_score_result
    
    # 簡易スコアで上位N×250件を選別（異なる薬効カテゴリの多様性確保）
    # 候補数が少ない場合は全件を詳細スコアリング（精度確保）
    selection_count = min(top_n * 250, len(candidates))

    try:
        from config.llm_flags import is_score_parallel_enabled
        _parallel_scores = is_score_parallel_enabled()
    except Exception:
        _parallel_scores = False

    if _parallel_scores and len(candidates) > 1:
        from concurrent.futures import ThreadPoolExecutor

        def _quick_pair(c):
            return (calculate_quick_score(c, nlu_result, scoring_user_info), c)

        _workers = min(8, len(candidates))
        with ThreadPoolExecutor(max_workers=_workers) as pool:
            quick_scores = list(pool.map(_quick_pair, candidates))
    else:
        quick_scores = [(calculate_quick_score(c, nlu_result, scoring_user_info), c) for c in candidates]
    
    # 解熱鎮痛薬と外用薬（のど）のquick_scoreをログ出力（DEBUGレベル）
    for score, candidate in quick_scores:
        medicine_type = candidate.get('medicine_type', '')
        product_name = candidate.get('product_name', '')
        if '解熱鎮痛薬' in medicine_type or '外用薬（のど）' in medicine_type:
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"quick_score: {score:.3f}, medicine_type={medicine_type}, product_name={product_name}")
    
    quick_scores_sorted = sorted(quick_scores, key=lambda x: x[0], reverse=True)
    top_candidates_for_scoring = quick_scores_sorted[:selection_count]
    
    # 簡易スコアが0.3以上の場合も含める（閾値ベースの選別）
    threshold_candidates = [(score, c) for score, c in quick_scores if score >= 0.3]
    if len(threshold_candidates) > selection_count:
        # 閾値を超える候補が多い場合は、それらも含める
        top_candidates_for_scoring = sorted(threshold_candidates, key=lambda x: x[0], reverse=True)
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"閾値ベース選別: 簡易スコア0.3以上の候補 {len(top_candidates_for_scoring)}件を選別")
    
    # スコアリング後の候補数を記録（閾値ベース選別後）
    after_scoring_candidate_count = len(top_candidates_for_scoring)
    
    # 解熱鎮痛薬と外用薬（のど）を優先的に詳細スコアリングに含める
    # 「のど痛み+発熱」パターンの場合、解熱鎮痛薬と外用薬（のど）を確実に含める
    # 発熱のみの場合、主要解熱鎮痛薬を優先的に含める
    symptom_names = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
    has_throat_and_fever = "のどの痛み" in symptom_names and "発熱" in symptom_names
    cold_symptoms = ["発熱", "咳", "鼻水", "のどの痛み", "頭痛", "悪寒", "くしゃみ", "鼻づまり"]
    cold_symptom_count = sum(1 for symptom in symptom_names if symptom in cold_symptoms)
    is_fever_only = cold_symptom_count == 1 and "発熱" in symptom_names
    is_headache_only = cold_symptom_count == 1 and "頭痛" in symptom_names
    
    # 発熱のみまたは頭痛のみの場合、主要解熱鎮痛薬を優先的に含める
    if is_fever_only or is_headache_only:
        logger.info(f"🔥 発熱/頭痛のみを検出: symptom_names={symptom_names}, cold_symptom_count={cold_symptom_count}, is_fever_only={is_fever_only}, is_headache_only={is_headache_only}")
        # 主要解熱鎮痛薬を抽出
        major_analgesic_candidates = []
        for score, candidate in quick_scores:
            product_name = candidate.get('product_name', '')
            product_name_norm = normalize_medicine_name_to_hankaku(product_name)
            is_major_analgesic = any(
                normalize_medicine_name_to_hankaku(m) in product_name_norm
                for m in MAJOR_ANALGESIC_MEDICINES
            )
            if is_major_analgesic and '解熱鎮痛薬' in candidate.get('medicine_type', ''):
                major_analgesic_candidates.append((score, candidate))
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"主要解熱鎮痛薬候補: {product_name} (score={score:.3f})")
        
        # 主要解熱鎮痛薬を優先的に含める（上位30件）
        top_major_analgesic = sorted(major_analgesic_candidates, key=lambda x: x[0], reverse=True)[:30]
        
        # 既存の候補に追加（重複を避ける）
        existing_products = {c.get('product_name', '') for _, c in top_candidates_for_scoring}
        added_count = 0
        for score, candidate in top_major_analgesic:
            if candidate.get('product_name', '') not in existing_products:
                # スコアが低くても強制的に追加（主要解熱鎮痛薬を優先）
                # スコアが0.2未満の場合は0.2に底上げして追加
                adjusted_score = max(score, 0.2)
                top_candidates_for_scoring.append((adjusted_score, candidate))
                existing_products.add(candidate.get('product_name', ''))
                added_count += 1
                logger.info(f"⭐ 主要解熱鎮痛薬を優先的に追加: {candidate.get('product_name', '')} (score={score:.3f} → {adjusted_score:.3f})")
        
        # スコア順に再ソート
        top_candidates_for_scoring = sorted(top_candidates_for_scoring, key=lambda x: x[0], reverse=True)
        logger.info(f"🔥 発熱のみの場合、主要解熱鎮痛薬を優先的に追加: {len(top_major_analgesic)}件中{added_count}件を追加")
        
        # 主要解熱鎮痛薬が既に含まれている場合もログ出力
        if added_count == 0 and len(top_major_analgesic) > 0:
            existing_major_analgesics = []
            for score, candidate in top_major_analgesic:
                if candidate.get('product_name', '') in existing_products:
                    existing_major_analgesics.append(candidate.get('product_name', ''))
            if existing_major_analgesics:
                logger.info(f"🔥 主要解熱鎮痛薬は既に候補に含まれています: {existing_major_analgesics[:5]}")
    
    if has_throat_and_fever:
        # 解熱鎮痛薬と外用薬（のど）を抽出
        analgesic_candidates = [(score, c) for score, c in quick_scores if '解熱鎮痛薬' in c.get('medicine_type', '')]
        throat_external_candidates = [(score, c) for score, c in quick_scores if '外用薬（のど）' in c.get('medicine_type', '')]
        
        # 解熱鎮痛薬と外用薬（のど）を優先的に含める（上位50件ずつ）
        top_analgesic = sorted(analgesic_candidates, key=lambda x: x[0], reverse=True)[:50]
        top_throat_external = sorted(throat_external_candidates, key=lambda x: x[0], reverse=True)[:50]
        
        # 既存の候補に追加（重複を避ける）
        existing_products = {c.get('product_name', '') for _, c in top_candidates_for_scoring}
        for score, candidate in top_analgesic + top_throat_external:
            if candidate.get('product_name', '') not in existing_products:
                top_candidates_for_scoring.append((score, candidate))
                existing_products.add(candidate.get('product_name', ''))
        
        # スコア順に再ソート
        top_candidates_for_scoring = sorted(top_candidates_for_scoring, key=lambda x: x[0], reverse=True)
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"解熱鎮痛薬と外用薬（のど）を優先的に追加: 解熱鎮痛薬={len(top_analgesic)}件, 外用薬（のど）={len(top_throat_external)}件")
    
    # 解熱鎮痛薬と外用薬（のど）が詳細スコアリングに進んでいるか確認（500件に絞り込む前）
    analgesic_count_before = 0
    throat_external_count_before = 0
    for score, candidate in top_candidates_for_scoring:
        medicine_type = candidate.get('medicine_type', '')
        if '解熱鎮痛薬' in medicine_type:
            analgesic_count_before += 1
        if '外用薬（のど）' in medicine_type:
            throat_external_count_before += 1
    
    # より積極的に候補を絞り込む（750件から500件に削減）
    # ただし、解熱鎮痛薬と外用薬（のど）は確実に含める
    if len(top_candidates_for_scoring) > 500:
        # 解熱鎮痛薬と外用薬（のど）を分離
        analgesic_candidates_in_top = [(score, c) for score, c in top_candidates_for_scoring if '解熱鎮痛薬' in c.get('medicine_type', '')]
        throat_external_candidates_in_top = [(score, c) for score, c in top_candidates_for_scoring if '外用薬（のど）' in c.get('medicine_type', '')]
        other_candidates = [(score, c) for score, c in top_candidates_for_scoring if '解熱鎮痛薬' not in c.get('medicine_type', '') and '外用薬（のど）' not in c.get('medicine_type', '')]
        
        # 解熱鎮痛薬と外用薬（のど）を優先的に含める（それぞれ最大50件）
        top_analgesic_included = sorted(analgesic_candidates_in_top, key=lambda x: x[0], reverse=True)[:50]
        top_throat_external_included = sorted(throat_external_candidates_in_top, key=lambda x: x[0], reverse=True)[:50]
        
        # 残りの枠を他の候補で埋める
        remaining_slots = 500 - len(top_analgesic_included) - len(top_throat_external_included)
        top_other_candidates = sorted(other_candidates, key=lambda x: x[0], reverse=True)[:remaining_slots]
        
        # 統合して再ソート
        top_candidates_for_scoring = sorted(top_analgesic_included + top_throat_external_included + top_other_candidates, key=lambda x: x[0], reverse=True)
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"簡易スコアリング完了: {len(candidates)}件 → 上位{len(top_candidates_for_scoring)}件を選別（500件に削減、解熱鎮痛薬={len(top_analgesic_included)}件、外用薬（のど）={len(top_throat_external_included)}件を優先的に含む）")
    else:
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"簡易スコアリング完了: {len(candidates)}件 → 上位{len(top_candidates_for_scoring)}件を選別")
    
    # 解熱鎮痛薬と外用薬（のど）が詳細スコアリングに進んでいるか確認（500件に絞り込んだ後）
    analgesic_count = 0
    throat_external_count = 0
    for score, candidate in top_candidates_for_scoring:
        medicine_type = candidate.get('medicine_type', '')
        if '解熱鎮痛薬' in medicine_type:
            analgesic_count += 1
        if '外用薬（のど）' in medicine_type:
            throat_external_count += 1
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"詳細スコアリング対象: 解熱鎮痛薬={analgesic_count}件, 外用薬（のど）={throat_external_count}件（絞り込み前: 解熱鎮痛薬={analgesic_count_before}件, 外用薬（のど）={throat_external_count_before}件）")
    
    # ステップ5.2: 詳細スコアリング（選別された候補のみ）
    # サマリーログ用のデータ収集
    analgesic_scores = []
    throat_external_scores = []
    top_10_scores = []

    def _apply_detailed_score(idx_score_candidate):
        idx, (score, candidate) = idx_score_candidate
        score_result = calculate_final_score(candidate, nlu_result, scoring_user_info, user_text)
        if score_result is None:
            logger.warning(
                "calculate_final_score returned None for candidate: %s",
                candidate.get("product_name", ""),
            )
            score_result = {
                "total_score": 0.0,
                "raw_score": 0.0,
                "score_breakdown": {},
            }
        candidate["final_score"] = score_result["total_score"]
        candidate["raw_score"] = score_result.get("raw_score", score_result["total_score"])
        candidate["score_breakdown"] = score_result["score_breakdown"]
        if "allergy_warning" in score_result:
            candidate["allergy_warning"] = score_result["allergy_warning"]
        if "interaction_warnings" in score_result:
            candidate["interaction_warnings"] = score_result["interaction_warnings"]
        medicine_type = candidate.get("medicine_type", "")
        product_name = candidate.get("product_name", "")
        raw_score = candidate["raw_score"]
        return idx, score, candidate, score_result, medicine_type, product_name, raw_score

    if _parallel_scores and len(top_candidates_for_scoring) > 1:
        from concurrent.futures import ThreadPoolExecutor

        indexed = list(enumerate(top_candidates_for_scoring))
        _d_workers = min(8, len(indexed))
        with ThreadPoolExecutor(max_workers=_d_workers) as pool:
            scored = list(pool.map(_apply_detailed_score, indexed))
        for idx, score, candidate, score_result, medicine_type, product_name, raw_score in sorted(
            scored, key=lambda x: x[0]
        ):
            if idx < 10:
                score_breakdown = score_result.get("score_breakdown", {})
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(
                        "詳細スコアリング結果: medicine_type=%s, product_name=%s, raw_score=%.3f",
                        medicine_type,
                        product_name,
                        raw_score,
                    )
            if "解熱鎮痛薬" in medicine_type:
                analgesic_scores.append((product_name, raw_score))
            if "外用薬（のど）" in medicine_type:
                throat_external_scores.append((product_name, raw_score))
            if idx < 10:
                top_10_scores.append((product_name, medicine_type, raw_score))
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(
                    "%s: raw=%.3f, final=%.3f",
                    product_name,
                    raw_score,
                    candidate["final_score"],
                )
    else:
        for idx, (score, candidate) in enumerate(top_candidates_for_scoring):
            _, _, _, score_result, medicine_type, product_name, raw_score = _apply_detailed_score(
                (idx, (score, candidate))
            )
            if idx < 10:
                score_breakdown = score_result.get("score_breakdown", {})
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"詳細スコアリング結果: medicine_type={medicine_type}, product_name={product_name}, raw_score={raw_score:.3f}, base_score={score_breakdown.get('base_score', 0.0):.3f}, adjusted_base_score={score_breakdown.get('adjusted_base_score', 0.0):.3f}, throat_bonus={score_breakdown.get('throat_bonus', 0.0):.3f}, symptom_specific_boost={score_breakdown.get('symptom_specific_boost', 0.0):.3f}, multi_symptom_bonus={score_breakdown.get('multi_symptom_bonus', 0.0):.3f}, pattern_bonus={score_breakdown.get('pattern_bonus', 0.0):.3f}, adjustment_score={score_result.get('adjustment_score', 0.0):.3f}")
            if "解熱鎮痛薬" in medicine_type:
                analgesic_scores.append((product_name, raw_score))
            if "外用薬（のど）" in medicine_type:
                throat_external_scores.append((product_name, raw_score))
            if idx < 10:
                top_10_scores.append((product_name, medicine_type, raw_score))
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"{product_name}: raw={raw_score:.3f}, final={candidate['final_score']:.3f}")
    
    # サマリーログ出力
    if analgesic_scores:
        max_analgesic = max(analgesic_scores, key=lambda x: x[1])
        avg_analgesic = sum(s[1] for s in analgesic_scores) / len(analgesic_scores)
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"解熱鎮痛薬スコアリングサマリー: {len(analgesic_scores)}件, 最高スコア={max_analgesic[1]:.3f} ({max_analgesic[0]}), 平均スコア={avg_analgesic:.3f}")
    
    if throat_external_scores:
        max_throat = max(throat_external_scores, key=lambda x: x[1])
        avg_throat = sum(s[1] for s in throat_external_scores) / len(throat_external_scores)
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"外用薬（のど）スコアリングサマリー: {len(throat_external_scores)}件, 最高スコア={max_throat[1]:.3f} ({max_throat[0]}), 平均スコア={avg_throat:.3f}")
    
    if top_10_scores:
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"詳細スコアリング上位10件: {', '.join([f'{s[0]}({s[2]:.3f})' for s in top_10_scores[:5]])}...")
    
    # ステップ5.2.5: 閾値判定のセーフティガード（減点適用前のraw_scoreで判定）
    # raw_score < 0.3の候補を除外（現在の完璧な薬が除外されないよう保護）
    # ただし、主要解熱鎮痛薬は優先的に含める（発熱のみの場合）
    threshold = 0.3
    excluded_candidates = []
    valid_candidates_for_scoring = []
    
    # 発熱のみまたは頭痛のみの場合、主要解熱鎮痛薬を優先的に含める
    symptom_names = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
    cold_symptoms = ["発熱", "咳", "鼻水", "のどの痛み", "頭痛", "悪寒", "くしゃみ", "鼻づまり"]
    cold_symptom_count = sum(1 for symptom in symptom_names if symptom in cold_symptoms)
    is_fever_only = cold_symptom_count == 1 and "発熱" in symptom_names
    is_headache_only = cold_symptom_count == 1 and "頭痛" in symptom_names
    
    for score, candidate in top_candidates_for_scoring:
        raw_score = candidate.get('raw_score', 0.0)
        product_name = candidate.get('product_name', '')
        product_name_norm = normalize_medicine_name_to_hankaku(product_name)
        # 発熱のみまたは頭痛のみの場合、主要解熱鎮痛薬は優先的に含める（閾値を下回っていても）
        is_major_analgesic = any(
            normalize_medicine_name_to_hankaku(m) in product_name_norm
            for m in MAJOR_ANALGESIC_MEDICINES
        )
        if (is_fever_only or is_headache_only) and is_major_analgesic and raw_score >= 0.2:  # 閾値を0.2に緩和
            valid_candidates_for_scoring.append((score, candidate))
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"主要解熱鎮痛薬を優先的に含める: {product_name} raw_score={raw_score:.3f} (閾値緩和)")
        elif raw_score < threshold:
            excluded_candidates.append(candidate)
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"閾値以下で除外: {product_name} raw_score={raw_score:.3f} < {threshold}")
        else:
            valid_candidates_for_scoring.append((score, candidate))
    
    if excluded_candidates:
        logger.info(f"閾値判定: {len(excluded_candidates)}件の候補を除外（raw_score < {threshold}）、残り{len(valid_candidates_for_scoring)}件")
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"除外された候補: {[c.get('product_name', '') for c in excluded_candidates[:5]]}...")
    
    # 有効な候補のみを使用
    top_candidates_for_scoring = valid_candidates_for_scoring
    
    # ステップ5.2.5.5: raw_scoreで順序を確定し、original_rankを保存（ランキング保護）
    # 正規化前のraw_scoreでソートし、順序を確定
    candidates_with_scores = [(c.get('raw_score', 0.0), c) for _, c in top_candidates_for_scoring]
    candidates_with_scores_sorted = sorted(candidates_with_scores, key=lambda x: x[0], reverse=True)
    
    # 各候補にoriginal_rankを保存（raw_scoreでの順位）
    for rank, (raw_score, candidate) in enumerate(candidates_with_scores_sorted, 1):
        candidate['original_rank'] = rank
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"original_rank保存: rank={rank}, product_name={candidate.get('product_name', '')}, raw_score={raw_score:.3f}")
    
    # 元の形式に戻す（タプルのリスト）
    top_candidates_for_scoring = [(score, candidate) for score, candidate in candidates_with_scores_sorted]
    
    # ステップ5.2.6: 正規化プロセスを簡素化（絶対評価ベースのため、raw_scoreをそのまま保持）
    # Min-Max正規化、重み付き線形変換、底上げロジックを削除
    # raw_scoreをそのままfinal_scoreとして使用（絶対評価ベース）
    for _, candidate in top_candidates_for_scoring:
        raw_score = candidate.get('raw_score', 0.0)
        score_breakdown = candidate.get('score_breakdown', {})
        hangover_boost = score_breakdown.get('hangover_boost', 0.0)
        is_hangover_medicine = candidate.get('is_hangover', False)
        
        # 二日酔い医薬品の場合、閾値を下げる
        min_threshold = 0.3 if (hangover_boost > 0 or is_hangover_medicine) else 0.5
        
        # 閾値以下のスコアは0.0にマッピング
        if raw_score <= min_threshold:
            # 二日酔い医薬品で0.2以上の場合は、最低限のスコアを与える
            if (hangover_boost > 0 or is_hangover_medicine) and raw_score >= 0.2:
                final_score = 0.4  # 最低限の推奨可能スコア
            else:
                final_score = 0.0
        else:
            # raw_scoreをそのままfinal_scoreとして使用（絶対評価ベース）
            final_score = raw_score
        
        candidate['final_score'] = final_score
        
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"正規化簡素化: product_name={candidate.get('product_name', '')}, raw_score={raw_score:.3f} → final_score={final_score:.3f}")
    
    # ステップ5.3: 詳細スコアリング（選別された候補のみ）
    # 正規化後、original_rankに基づいて順序を復元（ランキング保護）
    candidates_list = [c for _, c in top_candidates_for_scoring]
    candidates_sorted = sorted(candidates_list, key=lambda x: x.get('original_rank', 9999))
    
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"正規化後、original_rankに基づいて順序を復元: {len(candidates_sorted)}件")
    
    # スコア差が僅差（0.1以内）の場合、指定第2類医薬品を優先するソートロジック（乗り物酔い薬の場合）
    symptom_names = [s.get("name") for s in nlu_result.get("symptoms", [])]
    if len(candidates_sorted) >= 2 and "乗り物酔い" in symptom_names:
        # 上位2件のスコア差を確認
        top_score = candidates_sorted[0].get('final_score', 0.0)
        second_score = candidates_sorted[1].get('final_score', 0.0)
        score_diff = top_score - second_score
        
        # スコア差が0.1以内の場合、指定第2類を優先
        if score_diff <= 0.1:
            top_classification = str(candidates_sorted[0].get('classification', '')).lower()
            second_classification = str(candidates_sorted[1].get('classification', '')).lower()
            
            # 2位が指定第2類で、1位が指定第2類でない場合、入れ替え
            if '指定第2類' in second_classification and '指定第2類' not in top_classification:
                candidates_sorted[0], candidates_sorted[1] = candidates_sorted[1], candidates_sorted[0]
                # original_rankを更新（ランキング保護のため）
                candidates_sorted[0]['original_rank'], candidates_sorted[1]['original_rank'] = candidates_sorted[1]['original_rank'], candidates_sorted[0]['original_rank']
                logger.info(f"スコア差が僅差（{score_diff:.3f}）のため、指定第2類医薬品を優先しました（original_rankを更新）")
    
    # 肩こり・筋肉痛の場合、最適解の外用薬（フェイタス、バンテリン、サロンパス）を優先するソートロジック
    has_musculoskeletal_symptom = any(s in symptom_names for s in ["肩こり", "筋肉痛", "関節痛", "腰痛"])
    if has_musculoskeletal_symptom and len(candidates_sorted) >= 2:
        optimal_keywords = ["フェイタス", "バンテリン", "サロンパス"]
        
        # 最適解の製品を探す
        optimal_indices = []
        for i, candidate in enumerate(candidates_sorted):
            product_name = str(candidate.get('product_name', '')).lower()
            if any(kw.lower() in product_name for kw in optimal_keywords):
                optimal_indices.append(i)
        
        # 最適解が見つかり、1位でない場合、優先的に上位に移動
        if optimal_indices:
            for idx in optimal_indices:
                if idx > 0:  # 1位でない場合
                    # スコア差が0.2以内の場合、最適解を優先
                    optimal_score = candidates_sorted[idx].get('final_score', 0.0)
                    top_score = candidates_sorted[0].get('final_score', 0.0)
                    score_diff = top_score - optimal_score
                    
                    if score_diff <= 0.2:
                        # 最適解を1位に移動
                        optimal_candidate = candidates_sorted.pop(idx)
                        candidates_sorted.insert(0, optimal_candidate)
                        # original_rankを更新（ランキング保護のため）
                        # 1位からidx位までのoriginal_rankをシフト
                        for i in range(idx):
                            candidates_sorted[i + 1]['original_rank'] = i + 2
                        candidates_sorted[0]['original_rank'] = 1
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"肩こり外用薬の最適解を優先しました: {optimal_candidate.get('product_name')} (スコア差: {score_diff:.3f}, original_rankを更新)")
                        break
    
    # ensure_ingredient_diversity 側で「花粉症っぽさ/感染症っぽさ」を判定できるよう、原文を載せる
    if isinstance(nlu_result, dict):
        nlu_result.setdefault("user_text", user_text)

    mark_phase(session_id, "medicine_select", detail_code="ranking")
    top_candidates = ensure_ingredient_diversity(candidates_sorted, top_n=top_n, nlu_result=nlu_result, user_info=user_info)
    if top_candidates is None:
        logger.warning("ensure_ingredient_diversity returned None, using empty list")
        top_candidates = []
    
    # フィルタリング後の候補数を記録
    after_filtering_candidate_count = len(top_candidates)
    
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(
            f"詳細スコアリング完了: {len(top_candidates_for_scoring)}件 → 上位{len(top_candidates)}件を選択（成分多様性考慮）"
        )
    
    # 最終推奨結果をログ出力（解熱鎮痛薬と外用薬（のど）の確認用、DEBUGレベル）
    for i, candidate in enumerate(top_candidates, 1):
        medicine_type = candidate.get('medicine_type', '')
        product_name = candidate.get('product_name', '')
        final_score = candidate.get('final_score', 0.0)
        raw_score = candidate.get('raw_score', 0.0)
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"最終推奨結果 rank{i}: medicine_type={medicine_type}, product_name={product_name}, final_score={final_score:.3f}, raw_score={raw_score:.3f}")
    
    # ステップ5.3.5: 不足情報による減点情報の保存（絶対評価ベースのため、final_scoreには適用しない）
    # 減点はdisplay_score計算時に適用されるため、ここでは情報のみを保存
    if completeness_penalty > 0:
        logger.info(f"不足情報による減点情報を保存: penalty={completeness_penalty:.3f}, missing_fields={list(missing_fields_detail.keys())}")
        
        # 減点適用前のraw_scoreをログ出力（INFOレベルで出力）
        for i, candidate in enumerate(top_candidates[:3], 1):
            logger.info(f"減点適用前 rank{i}: {candidate.get('product_name', '')} final_score={candidate.get('final_score', 0.0):.3f}, raw_score={candidate.get('raw_score', 0.0):.3f}")
        
        # score_breakdownに減点情報を追加（final_scoreには影響しない）
        for candidate in top_candidates:
            if 'score_breakdown' not in candidate:
                candidate['score_breakdown'] = {}
            candidate['score_breakdown']['completeness_penalty'] = -completeness_penalty
            candidate['score_breakdown']['missing_fields_detail'] = missing_fields_detail
            
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"減点情報を保存: {candidate.get('product_name', '')} penalty={completeness_penalty:.3f} (final_scoreには適用しない)")
    
    # ステップ5.3.6: MaxPossibleScore計算（絶対評価ベースのため、MaxPossibleScore情報のみ保存）
    # 絶対評価ベースのため、MaxPossibleScore正規化は不要
    MaxPossibleScore = 1.0 - completeness_penalty  # 最大-0.15でキャップ済み
    for candidate in top_candidates:
        candidate['max_possible_score'] = MaxPossibleScore
    
    # ステップ5.4: 相対スコア化（最高スコアを100%として正規化）
    # ensure_ingredient_diversity実行後、relative_scoreを再計算
    # 注意: ensure_ingredient_diversityが順序を変更する可能性があるため、
    # 実際の最高スコアを取得してから相対スコアを計算する
    if top_candidates:
        # 実際の最高スコアを取得（順序に関係なく）
        max_score = max(candidate.get('final_score', 0.0) for candidate in top_candidates)
        if max_score > 0:
            for candidate in top_candidates:
                final_score = candidate.get('final_score', 0.0)
                # final_scoreが0.0の場合はrelative_scoreも0.0に設定
                if final_score <= 0.0:
                    candidate['relative_score'] = 0.0
                    candidate['score_level'] = '低'
                else:
                    relative_score = final_score / max_score
                    # 1.0を超えないようにクリップ
                    relative_score = min(1.0, relative_score)
                    candidate['relative_score'] = relative_score
                    
                    # スコアレベルの再定義（情報網羅率を考慮）
                    # Criticalな不足情報があるかチェック
                    has_critical_missing = False
                    if missing_info_result.get("has_missing_info", False):
                        critical_fields = ["age", "allergies", "pregnancy_status"]
                        missing_fields = missing_info_result.get("missing_fields", [])
                        has_critical_missing = any(field in missing_fields for field in critical_fields)
                    
                    # 新しいスコアレベル判定（計画7.1に従う）
                    if relative_score >= 0.8 and not has_critical_missing:
                        candidate['score_level'] = '高'  # 高（S）: 80%以上 + Criticalな不足情報なし
                    elif relative_score >= 0.6:
                        candidate['score_level'] = '中'  # 中（A）: 60%以上
                    elif relative_score < 0.4:
                        candidate['score_level'] = '低'  # 低（B）: 40%未満 または 閾値ギリギリ
                    else:
                        # 0.4 <= relative_score < 0.6 の場合は中（A）として扱う
                        candidate['score_level'] = '中'
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"相対スコア: {candidate.get('product_name', '')} = {candidate.get('relative_score', 0.0):.3f} ({candidate.get('score_level', '')})")
        
        # 相対スコア計算後、original_rankに基づいて順序を復元（ランキング保護）
        top_candidates = sorted(top_candidates, key=lambda x: x.get('original_rank', 9999))
        
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"相対スコア計算後、original_rankに基づいて順序を復元: {len(top_candidates)}件")
        
        # ステップ5.4.5: 絶対評価ベースの表示用スコア計算
        if len(top_candidates) >= 1:
            # 各候補に対してdisplay_scoreを計算（絶対評価ベース）
            for rank, candidate in enumerate(top_candidates[:3], 1):
                raw_score = candidate.get('raw_score', 0.0)
                
                # 絶対評価ベースのdisplay_scoreを計算
                display_score = calculate_display_score_absolute(rank, raw_score, completeness_penalty)
                candidate['display_score'] = display_score
                
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"表示用スコア（絶対評価ベース）: rank={rank}, {candidate.get('product_name', '')} = {display_score:.1f}% (raw_score={raw_score:.3f}, penalty={completeness_penalty:.3f})")
    
    # ステップ5.5: 推奨後の検証処理
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"\n--- ステップ5.5: 推奨後の検証処理 ---")
    
    # 減点適用後、final_scoreが0になった候補も保持（ランキング保護のため）
    # 減点適用前のraw_scoreで閾値判定済みのため、減点適用後も候補を保持
    validated_candidates = _finalize_recommendations(top_candidates, nlu_result, influenza_risk)
    
    # 減点適用後、final_scoreが0になった候補も保持（最低3件推奨するため）
    # 減点適用前のraw_scoreで閾値判定済みのため、減点適用後も候補を保持
    if len(validated_candidates) < top_n:
        # 減点適用後、final_scoreが0になった候補も追加
        excluded_by_validation = [c for c in top_candidates if c not in validated_candidates]
        # 減点適用前のraw_scoreで閾値判定済みのため、減点適用後も候補を保持
        for candidate in excluded_by_validation:
            if candidate.get('raw_score', 0.0) >= 0.3:  # 減点適用前のraw_scoreで閾値判定済み
                validated_candidates.append(candidate)
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"減点適用後も候補を保持: {candidate.get('product_name', '')} (raw_score={candidate.get('raw_score', 0.0):.3f}, final_score={candidate.get('final_score', 0.0):.3f})")
    
    # 推奨医薬品が3件未満の場合、スコアが低い候補も含める（最低3件推奨するため）
    if len(validated_candidates) < top_n and len(top_candidates) > len(validated_candidates):
        # 除外された候補から、減点適用前のraw_score >= 0.3の候補を追加
        # 減点適用後、final_scoreが0になっても、減点適用前のraw_scoreで閾値判定済みのため保持
        excluded_candidates = [c for c in top_candidates if c not in validated_candidates]
        excluded_candidates = [c for c in excluded_candidates if c.get('raw_score', 0.0) >= 0.3]
        
        # original_rankに基づいてソート（ランキング保護）
        excluded_candidates = sorted(excluded_candidates, key=lambda x: x.get('original_rank', 9999))
        
        # 不足分を追加
        needed_count = top_n - len(validated_candidates)
        for candidate in excluded_candidates[:needed_count]:
            # 低スコア警告を追加
            candidate['low_score_warning'] = True
            validated_candidates.append(candidate)
            logger.info(f"⚠️ 推奨医薬品が{top_n}件未満のため、低スコア候補を追加: {candidate.get('product_name', '')} (スコア: {candidate.get('final_score', 0.0):.3f})")
        
        # original_rankに基づいて順序を復元（ランキング保護）
        validated_candidates = sorted(validated_candidates, key=lambda x: x.get('original_rank', 9999))
    
    # 最終的な順序復元（すべての処理後、original_rankに基づいて順序を復元）
    validated_candidates = sorted(validated_candidates, key=lambda x: x.get('original_rank', 9999))
    
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"最終的な順序復元: original_rankに基づいて順序を復元: {len(validated_candidates)}件")

    _mark_rb_pipeline_step("rb_scoring_only_done")

    # ステップ6: 説明生成
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"\n--- ステップ6: 説明生成 ---")
    recommendations = []
    for i, candidate in enumerate(validated_candidates, 1):
        explanation = generate_explanation(candidate, nlu_result, safety_result, scoring_user_info)
        
        recommendation_item = {
            "rank": i,
            "number": i,  # ChatGPTベース互換性のため追加
            "product_name": candidate['product_name'],
            "manufacturer": candidate['manufacturer'],
            "medicine_type": candidate['medicine_type'],
            "classification": candidate.get('classification', ''),  # C列
            "efficacy": candidate['efficacy'],  # E列
            "usage": candidate['usage'],  # F列
            "age_restriction": candidate.get('age_restriction', ''),  # G列
            "ingredients": candidate['ingredients'],  # H列
            "doping_prohibited": candidate.get('doping_prohibited', ''),  # I列
            "competition_category": candidate.get('competition_category', ''),  # J列
            "conditions": candidate.get('conditions', ''),  # K列
            "usage_notes": candidate.get('usage_notes', '用法用量を守ってご使用ください。'),
            "score": candidate['final_score'],
            "relative_score": candidate.get('relative_score', candidate['final_score']),  # 相対スコア（最高スコアを1.0として正規化）
            "display_score": candidate.get('display_score'),  # 表示用スコア（小数点第1位、絶対評価ベース）
            "score_level": candidate.get('score_level', '中'),  # スコア帯（高/中/低）
            "score_breakdown": candidate.get('score_breakdown', {}),
            "explanation": explanation,
            "reason": explanation,  # ChatGPTベース互換性のため追加
            "allergy_warning": candidate.get('allergy_warning', ''),
            "interaction_warnings": candidate.get('interaction_warnings', []),
            "completeness_penalty": completeness_penalty,  # 不足情報による減点
            "max_possible_score": candidate.get('max_possible_score', 1.0),  # MaxPossibleScore
            "raw_score": candidate.get('raw_score'),  # 管理者向け: raw_score（絶対評価ベースの計算元）
            "original_rank": candidate.get('original_rank', i)  # 管理者向け: original_rank（ランキング保護用）
        }
        
        # リスク警告を追加
        if candidate.get('risk_warning'):
            recommendation_item['risk_warning'] = candidate['risk_warning']
        if candidate.get('low_score_warning'):
            recommendation_item['low_score_warning'] = True
        if candidate.get('pollen_product_class'):
            recommendation_item['pollen_product_class'] = candidate['pollen_product_class']
        if candidate.get('has_vasoconstrictor_nasal'):
            recommendation_item['has_vasoconstrictor_nasal'] = True
        
        recommendations.append(recommendation_item)
    
    # ステップ7: 使用上の注意と医師相談アドバイスをChatGPTで生成
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"\n--- ステップ7: 使用上の注意と医師相談アドバイスの生成 ---")
    if defer_explanation_llm:
        usage_and_consultation = {"usage_notes": "", "doctor_consultation": ""}
    else:
        usage_and_consultation = generate_usage_notes_and_consultation_with_gpt(
            recommendations, nlu_result, scoring_user_info, client
        )
        _mark_rb_pipeline_step("rb_explain_batch_done")

    usage_and_consultation = merge_pollen_combination_into_usage(
        usage_and_consultation, recommendations, nlu_result, user_text
    )
    
    logger.info(f"推奨完了: {len(recommendations)}件の医薬品を推奨")
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"{'='*80}")
    
    # score_breakdownのJSON出力（デバッグ・トレース用）
    score_breakdown_json = None
    if recommendations:
        try:
            score_breakdowns = [r.get('score_breakdown', {}) for r in recommendations]
            score_breakdown_json = json.dumps(score_breakdowns, ensure_ascii=False, indent=2)
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"📊 Score Breakdown JSON:\n{score_breakdown_json}")
        except Exception as e:
            logger.warning(f"Score breakdown JSON化エラー: {e}")
    
    # 不足情報の質問を追加（すべての優先度で表示）
    additional_questions = []
    missing_priority = None
    if missing_info_result.get("has_missing_info"):
        additional_questions = missing_info_result.get("questions", [])
        missing_priority = missing_info_result.get("priority")
    
    # 代替療法の取得（睡眠改善薬の場合）
    alternative_therapies = nlu_result.get("sleep_alternative_therapies", [])
    sleep_critical_questions = nlu_result.get("sleep_critical_questions", [])
    
    # critical_questionsに睡眠改善薬の質問を追加
    all_critical_questions = missing_info_result.get("critical_questions", [])
    if sleep_critical_questions:
        all_critical_questions.extend(sleep_critical_questions)
    
    from src.core.preference_merge import build_user_preferences_summary

    user_preferences_summary = build_user_preferences_summary(
        scoring_user_info.get("user_preferences")
    )

    return {
        "status": "success",
        "recommended_medicines": recommendations,
        "warnings": safety_result["warnings"],
        "usage_notes": usage_and_consultation.get('usage_notes', ''),
        "doctor_consultation": usage_and_consultation.get('doctor_consultation', ''),
        "additional_questions": additional_questions,
        "critical_questions": all_critical_questions,  # 睡眠改善薬の質問も含める
        "missing_priority": missing_priority,
        "alternative_therapies": alternative_therapies,  # 代替療法（睡眠改善薬の場合）
        "user_preferences_summary": user_preferences_summary,
        "nlu_result": nlu_result,
        "influenza_risk": influenza_risk,  # 新規追加
        "influenza_reason": influenza_reason,  # 新規追加
        "confidence_score": confidence_score,  # confidence_scoreを追加
        "score_breakdown_json": score_breakdown_json,  # デバッグ用JSON出力
        "completeness_penalty": completeness_penalty,  # 不足情報による減点
        "max_possible_score": MaxPossibleScore,  # MaxPossibleScore
        "candidate_counts": {
            "initial": initial_candidate_count,
            "after_scoring": after_scoring_candidate_count,
            "after_filtering": after_filtering_candidate_count
        },
        "timestamp": datetime.now().isoformat()
    }

# generate_explanation は explanation_generator から import（SRP改善）

# ================================================================================
# 6. ChatGPTによる使用上の注意と医師相談アドバイス（explanation_generator から import）
# ================================================================================

# ================================================================================
# 7. ロギング（recommendation_logger からインポート）
# ================================================================================

from src.services.recommendation_logger import log_recommendation_session

# ================================================================================
# 7. ラッパー関数（app.pyから呼び出し用）
# ================================================================================

def rule_based_medicine_recommendation(
    user_text: str,
    user_info: Dict,
    client: OpenAI,
    top_n: int = 3,
    session_id: str = None,
    *,
    precomputed_nlu: Optional[Dict] = None,
    llm_user_text: Optional[str] = None,
    precomputed_missing_info: Optional[Dict] = None,
    defer_explanation_llm: bool = False,
) -> Dict:
    """
    ルールベース医薬品推奨システムのラッパー関数（app.pyから呼び出し用）
    
    Args:
        user_text: ユーザーの症状入力
        user_info: ユーザー情報
        client: OpenAI client
        top_n: 推奨医薬品数
        session_id: セッションID（キャッシュ用）
        precomputed_nlu: 推奨フローで既に取得済みの NLU（再実行を避ける）
        precomputed_missing_info: flow 側で取得済みの不足情報（LLM 外部化時）
        defer_explanation_llm: True のときステップ7 LLM をスキップ
    
    Returns:
        推奨結果
    """
    from src.core.medicine_data import CSV_PATH, df as cached_medicine_df

    medicine_df = cached_medicine_df
    if medicine_df is None:
        logger.warning("キャッシュ df 未ロードのため CSV を再読み込みします")
        medicine_df = pd.read_csv(CSV_PATH)
    
    # メイン関数を呼び出し
    result = rule_based_recommendation(
        user_text=user_text,
        user_info=user_info,
        medicine_df=medicine_df,
        client=client,
        top_n=top_n,
        session_id=session_id,
        precomputed_nlu=precomputed_nlu,
        llm_user_text=llm_user_text,
        precomputed_missing_info=precomputed_missing_info,
        defer_explanation_llm=defer_explanation_llm,
    )
    
    return result
