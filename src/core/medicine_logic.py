import pandas as pd
import os
import re
import time
import logging
from typing import Dict
from src.utils.debug_logger import add_network_log, performance_stats
from datetime import datetime

# ログ設定
logger = logging.getLogger(__name__)

# 医薬品データ（CSV読み込み・検索）は medicine_data に集約
from src.core.medicine_data import (
    BASE_DIR,
    CSV_PATH,
    DATA_DIR,
    clean_csv_data,
    csv_load_status,
    df,
    find_otc_candidates,
    get_medicines_by_symptom,
    get_medicines_by_type,
)

from src.core.language_utils import detect_language
from src.core.diagnosis_detection import is_diagnosis_term, is_diagnosis_only, has_side_effect_mention
from src.core.attribute_extractor import (
    create_multilingual_attribute_extraction_prompt,
    extract_user_attributes_multilingual,
)

from src.core.translation_service import translate_medicine_recommendation
from src.core.user_detection import (
    PENALTY_MAP,
    calculate_completeness_penalty,
    detect_digestive_sensitivity,
    detect_postpartum_breastfeeding,
    detect_severity_escalation,
    determine_pain_urgency,
    extract_user_preferences,
    generate_doctor_referral_message,
)
from src.core.llm_medicine_service import (
    analyze_symptoms_and_medicine_type,
    gpt_guess_symptom,
    gpt_select_best_otc,
    select_symptoms_via_gpt,
    simple_symptom_and_type_detection,
)
from src.services.text_formatter import convert_markdown_bold, format_text_for_display
from src.core.explanation_generator import generate_usage_notes

# 後方互換: OpenAI クライアントは openai_client に集約し、ここで re-export
from src.core.openai_client import client, api_key
# 関数内で client 引数が None のときに使うデフォルト（シャドウを避けるため別名）
from src.core.openai_client import client as _default_openai_client
# GPT 推奨フローは medicine.medicine_recommendation_gpt に移管（re-export）
from src.core.medicine.medicine_recommendation_gpt import (
    recommend_otc_medicines_via_gpt,
    recommend_otc_medicines_from_summarized,
    gpt_select_efficacy_candidates,
    recommend_medicines_with_retry,
)
# 医薬品詳細・チャット文脈は medicine.medicine_response_builder に移管（re-export）
from src.core.medicine.medicine_response_builder import (
    get_medicine_details,
    detect_medicine_name_in_query,
    chat_with_medicine_context,
)

def comprehensive_medicine_recommendation(user_text, user_info=None, client=None):
    """
    包括的な医薬品推奨システムのメイン関数
    """
    print(f"=== 包括的医薬品推奨システム開始 ===")
    print(f"症状文: {user_text}")
    
    # ステップ1: 症状と医薬品の種類を分析
    analysis_result = analyze_symptoms_and_medicine_type(user_text, client)
    symptoms = analysis_result.get('symptoms', [])
    medicine_type = analysis_result.get('medicine_type', 'その他')
    
    print(f"分析結果 - 症状: {symptoms}")
    print(f"分析結果 - 医薬品の種類: {medicine_type}")
    
    # ステップ2: 医薬品の種類に基づいて医薬品リストを取得
    medicine_list = get_medicines_by_type(medicine_type)
    
    if not medicine_list:
        print("該当する医薬品が見つかりませんでした")
        return {
            'symptoms': symptoms,
            'medicine_type': medicine_type,
            'recommended_medicines': [],
            'usage_notes': '該当する医薬品が見つかりませんでした。医師にご相談ください。',
            'doctor_consultation': '症状が改善しない場合は医師にご相談ください。'
        }
    
    # ステップ3: ChatGPTに推奨医薬品を選択させる
    recommendation_result = recommend_medicines_with_retry(
        user_text, symptoms, medicine_list, user_info=user_info, client=client
    )
    
    # ステップ4: 推奨医薬品の詳細情報を取得
    detailed_medicines = get_medicine_details(
        recommendation_result.get('recommended_medicines', []), 
        medicine_list
    )
    
    # スコア順にソート（降順：スコアが高い順）
    detailed_medicines.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    # ソート後の順位を更新
    for i, medicine in enumerate(detailed_medicines, 1):
        medicine['number'] = i
    
    # 最終結果を構築
    final_result = {
        'symptoms': symptoms,
        'medicine_type': medicine_type,
        'recommended_medicines': detailed_medicines,
        'usage_notes': recommendation_result.get('usage_notes', ''),
        'doctor_consultation': recommendation_result.get('doctor_consultation', '')
    }
    
    print(f"=== 推奨結果 ===")
    print(f"症状: {symptoms}")
    print(f"医薬品の種類: {medicine_type}")
    print(f"推奨医薬品数: {len(detailed_medicines)}")
    
    return final_result 

# ================================================================================
# ルールベース推奨システム（新規追加）
# ================================================================================

def rule_based_medicine_recommendation(
    user_text,
    user_info,
    client=None,
    session_id=None,
    *,
    precomputed_nlu=None,
    top_n=3,
):
    """
    ルールベース医薬品推奨システムのラッパー関数（後方互換）。
    実装は src.core.rule_based_recommendation.rule_based_medicine_recommendation に委譲。
    """
    if client is None:
        client = _default_openai_client

    try:
        from src.core.rule_based_recommendation import (
            rule_based_medicine_recommendation as _rbr,
        )

        return _rbr(
            user_text,
            user_info,
            client,
            top_n=top_n,
            session_id=session_id,
            precomputed_nlu=precomputed_nlu,
        )

    except ImportError as e:
        logger.error(f"ルールベース推奨モジュールのインポートエラー: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "reason": f"システムエラー(モジュールインポートエラー: {str(e)})",
            "error_type": "import_error"
        }
    except AttributeError as e:
        logger.error(f"ルールベース推奨関数の属性エラー: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "reason": f"システムエラー(関数が見つかりません: {str(e)})",
            "error_type": "attribute_error"
        }
    except Exception as e:
        logger.error(f"ルールベース推奨エラー: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "reason": f"システムエラー({str(e)})",
            "error_type": "unknown_error"
        }

