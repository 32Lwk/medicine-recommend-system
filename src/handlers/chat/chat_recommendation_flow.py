"""
チャット推奨フロー実行

責務: Physical カテゴリ時の医薬品推奨一連処理（分析→rule_based_medicine_recommendation→
性別/妊娠処理→使用上の注意→build_success_response）。
"""

import os
import re
import time
import logging
from src.services.html_formatter import (
    format_diagnosis_notification,
    format_error_display,
    format_escalation_display,
    format_medicine_type_notice,
    format_system_error,
)
import json
import html
import uuid
from datetime import datetime

from src.utils.request_logger import log_medicine_logic_call, log_network_request
from src.utils.performance_monitor import log_performance_metrics
from src.utils.debug_logger import add_network_log
from src.utils.input_helpers import check_missing_attributes, is_ambiguous_input
from src.services.analytics import log_access_analytics
from src.services.chat_response_service import generate_personalized_advice
from src.services.session_manager import (
    get_session_from_db,
    save_session_to_db,
    get_admin_sessions,
    get_manual_reply_queue,
)
from src.core.medicine_logic import (
    analyze_symptoms_and_medicine_type,
    rule_based_medicine_recommendation,
)
from src.core.translation_service import translate_medicine_recommendation
from src.handlers.chat.chat_response_builder import build_success_response

logger = logging.getLogger(__name__)


def _emit_explanation_followup_sse(
    session,
    sid,
    recommended_medicines,
    recommendation_result,
    recommendation_client,
) -> None:
    """カード先行後に ExplanationAgent で推奨理由を生成し SSE で追送する。"""
    if not sid or not recommended_medicines:
        return
    try:
        from config.llm_flags import is_agent_enabled
        from src.services.sse_emit import emit_explanations, is_streaming_active

        if not is_agent_enabled() or not is_streaming_active(sid):
            return
        from src.agents.explanation_agent import generate_explanations_for_recommendation
        from src.services.processing_status import mark_processing_step

        mark_processing_step(sid, "medicine_select", detail_code="explanation")
        nlu = recommendation_result.get("nlu_result") or {}
        user_info = dict(session.get("user_attributes") or {})
        safety = recommendation_result.get("safety_result") or {}
        out = generate_explanations_for_recommendation(
            recommended_medicines,
            nlu,
            user_info,
            recommendation_client,
            safety_result=safety,
        )
        explanations = out.get("explanations") or []
        for i, med in enumerate(recommended_medicines[: len(explanations)]):
            if explanations[i]:
                med["explanation"] = explanations[i]
                med["reason"] = explanations[i]
        emit_explanations(recommended_medicines, explanations, session_id=sid)
        from src.services.sse_emit import emit_bot_followup

        emit_bot_followup(
            session_id=sid,
            message_type="explanations_ready",
            payload={"count": len([e for e in explanations if e])},
        )
    except Exception as exc:
        logger.debug("explanation SSE follow-up skipped: %s", exc)


def run_recommendation_flow(
    session,
    client,
    sid,
    monitor,
    sanitized_message,
    processed_message,
    triage_result,
    recommendation_client,
    user_message=None,
    user_attributes=None,
):
    if user_message is None:
        user_message = processed_message or sanitized_message or ""
    from src.services.processing_status import mark_processing_step

    mark_processing_step(sid, "attributes")
    ADMIN_SESSIONS = get_admin_sessions()
    if True:  # main recommendation flow (body is 8-space indented)
        # ステップ0: ユーザー情報登録処理（NLU解析の前に実行）
        # ユーザー属性データをセッションから取得
        user_attributes = session.get('user_attributes', {
            'age': None,
            'gender': None,
            'pregnant': None,
            'breastfeeding': None,
            'current_medications': [],
            'allergies': [],
            'medical_history': [],
            'symptom_duration_days': None,
            'other_info': None
        })
                    
        # 登録された情報を追跡（通知メッセージ用）
        registered_info = {
            'gender': {'registered': False, 'value': None, 'source': None, 'message': None},
            'age': {'registered': False, 'value': None, 'source': None, 'message': None},
            'pregnant': {'registered': False, 'value': None, 'source': None, 'message': None},
            'breastfeeding': {'registered': False, 'value': None, 'source': None, 'message': None},
            'allergies': {'registered': False, 'value': [], 'source': None, 'message': None},
            'current_medications': {'registered': False, 'value': [], 'source': None, 'message': None},
            'medical_history': {'registered': False, 'value': [], 'source': None, 'message': None},
            'symptom_duration_days': {'registered': False, 'value': None, 'source': None, 'message': None}
        }
                    
        # 情報登録処理を実行（エラーハンドリング強化）
        logger.info(f"📝 ユーザー情報登録処理を開始: user_message={user_message[:50]}...")
        info_registration_success = True
        try:
            # 明示的な性別の言及を検出（最優先）
            try:
                explicit_gender = None
                explicit_gender_patterns = [
                    (r'私は(?:女性|女)です', '女性'),
                    (r'私は(?:男性|男)です', '男性'),
                    (r'性別は(?:女性|女)', '女性'),
                    (r'性別は(?:男性|男)', '男性'),
                    (r'^(?:女性|女)です', '女性'),
                    (r'^(?:男性|男)です', '男性'),
                    (r'female', '女性'),
                    (r'male', '男性'),
                    (r'woman', '女性'),
                    (r'man', '男性')
                ]
                for pattern, gender in explicit_gender_patterns:
                    if re.search(pattern, user_message, re.IGNORECASE):
                        explicit_gender = gender
                        break
                            
                if explicit_gender:
                    current_gender = user_attributes.get('gender')
                    if not current_gender or current_gender != explicit_gender:
                        user_attributes['gender'] = explicit_gender
                        registered_info['gender'] = {
                            'registered': True,
                            'value': explicit_gender,
                            'source': '明示的な言及',
                            'message': f'性別: {explicit_gender}（明示的な言及から登録）'
                        }
                        logger.info(f"👤 性別を明示的な言及から登録: {explicit_gender}")
            except Exception as e:
                logger.info(f"⚠️ 性別の明示的な言及の検出でエラー: {str(e)}")
                        
            # 年齢の抽出・登録
            try:
                age_match = re.search(r'(\d+)歳', user_message)
                if age_match:
                    age_value = int(age_match.group(1))
                    if age_value > 0 and age_value < 150:
                        if user_attributes.get('age') != age_value:
                            user_attributes['age'] = age_value
                            registered_info['age'] = {
                                'registered': True,
                                'value': age_value,
                                'source': '入力から抽出',
                                'message': f'年齢: {age_value}歳'
                            }
                            logger.info(f"📝 年齢を登録: {age_value}歳")
                else:
                    # 英語の年齢パターン
                    age_match_en = re.search(r'(\d+)\s*years?\s*old', user_message, re.IGNORECASE)
                    if age_match_en:
                        age_value = int(age_match_en.group(1))
                        if age_value > 0 and age_value < 150:
                            if user_attributes.get('age') != age_value:
                                user_attributes['age'] = age_value
                                registered_info['age'] = {
                                    'registered': True,
                                    'value': age_value,
                                    'source': '入力から抽出',
                                    'message': f'年齢: {age_value}歳'
                                }
                                logger.info(f"📝 年齢を登録: {age_value}歳")
            except Exception as e:
                logger.info(f"⚠️ 年齢の抽出でエラー: {str(e)}")
                        
            # アレルギーの抽出・登録
            try:
                if 'アレルギー' in user_message or 'allergy' in user_message.lower() or 'allergies' in user_message.lower():
                    if ('ない' in user_message or 'いいえ' in user_message or 'ありません' in user_message or 'なし' in user_message or 
                        'no allergy' in user_message.lower() or 'no allergies' in user_message.lower()):
                        if user_attributes.get('allergies') != ['なし']:
                            user_attributes['allergies'] = ['なし']
                            registered_info['allergies'] = {
                                'registered': True,
                                'value': ['なし'],
                                'source': '入力から抽出',
                                'message': 'アレルギー: なし'
                            }
                            logger.info(f"📝 アレルギーを登録: なし")
                    else:
                        # 日本語のアレルギー抽出
                        allergens = re.findall(r'([ぁ-んァ-ヶー]+)アレルギー', user_message)
                        if allergens:
                            existing_allergies = user_attributes.get('allergies', [])
                            new_allergies = [a for a in allergens if a not in existing_allergies]
                            if new_allergies:
                                user_attributes['allergies'] = existing_allergies + new_allergies
                                registered_info['allergies'] = {
                                    'registered': True,
                                    'value': user_attributes['allergies'],
                                    'source': '入力から抽出',
                                    'message': f'アレルギー: {", ".join(user_attributes["allergies"])}'
                                }
                                logger.info(f"📝 アレルギーを登録: {user_attributes['allergies']}")
                        else:
                            # 英語のアレルギー抽出
                            allergy_match = re.search(r'have\s+([^,\s]+)\s+allergy', user_message, re.IGNORECASE)
                            if allergy_match:
                                allergy_name = allergy_match.group(1)
                                existing_allergies = user_attributes.get('allergies', [])
                                if allergy_name not in existing_allergies:
                                    user_attributes['allergies'] = existing_allergies + [allergy_name]
                                    registered_info['allergies'] = {
                                        'registered': True,
                                        'value': user_attributes['allergies'],
                                        'source': '入力から抽出',
                                        'message': f'アレルギー: {", ".join(user_attributes["allergies"])}'
                                    }
                                    logger.info(f"📝 アレルギーを登録: {user_attributes['allergies']}")
            except Exception as e:
                logger.info(f"⚠️ アレルギーの抽出でエラー: {str(e)}")
                        
            # 服用中の薬の抽出・登録
            try:
                # 除外パターン：市販薬を探している、薬を探しているなどの文脈を除外
                medication_exclusion_patterns = [
                    r'市販薬を探',
                    r'薬を探',
                    r'薬を.*探',
                    r'薬.*探',
                    r'市販薬.*探',
                    r'探している',
                    r'探しています',
                    r'おすすめ',
                    r'推奨',
                    r'欲しい',
                    r'相談'
                ]
                is_medication_search = any(re.search(pattern, user_message) for pattern in medication_exclusion_patterns)
                            
                if ('服用している薬はありません' in user_message or '他に服用している薬はありません' in user_message or '薬は飲んでいません' in user_message or
                    'not taking' in user_message.lower() or 'no medication' in user_message.lower()):
                    if user_attributes.get('current_medications') != []:
                        user_attributes['current_medications'] = []
                        registered_info['current_medications'] = {
                            'registered': True,
                            'value': [],
                            'source': '入力から抽出',
                            'message': '服用中の薬: なし'
                        }
                        logger.info(f"📝 服用中の薬を登録: なし")
                elif not is_medication_search and ('服用している' in user_message or '飲んでいる' in user_message or
                      'taking' in user_message.lower() or 'medication' in user_message.lower() or 'medicine' in user_message.lower()):
                    # 「服用している」「飲んでいる」などの明確な表現のみを対象
                    medication_patterns = [
                        r'服用している薬[はが]?([^。、\n]+)',
                        r'飲んでいる薬[はが]?([^。、\n]+)',
                        r'服用している[はが]?([^。、\n]+)',
                        r'飲んでいる[はが]?([^。、\n]+)',
                        r'taking\s+([^,\s]+(?:\s+[^,\s]+)*)',
                        r'medication[:\s]+([^,\n]+)',
                        r'medicine[:\s]+([^,\n]+)'
                    ]
                    for pattern in medication_patterns:
                        match = re.search(pattern, user_message)
                        if match:
                            medication_name = match.group(1).strip()
                            # 抽出された名前が空でなく、かつ「探しています」などの除外パターンに含まれていないことを確認
                            if medication_name and not any(ex_pattern in medication_name for ex_pattern in ['探', 'おすすめ', '推奨', '欲しい', '相談']):
                                existing_medications = user_attributes.get('current_medications', [])
                                if medication_name not in existing_medications:
                                    user_attributes['current_medications'] = existing_medications + [medication_name]
                                    registered_info['current_medications'] = {
                                        'registered': True,
                                        'value': user_attributes['current_medications'],
                                        'source': '入力から抽出',
                                        'message': f'服用中の薬: {", ".join(user_attributes["current_medications"])}'
                                    }
                                    logger.info(f"📝 服用中の薬を登録: {medication_name}")
                                    break
            except Exception as e:
                logger.info(f"⚠️ 服用中の薬の抽出でエラー: {str(e)}")
                        
            # 既往歴の抽出・登録
            try:
                # 診断名検出の結果を既往症として登録（「癌なんですが」のような文脈）
                # 診断名検出が既に実行されている場合、その結果を活用
                # ただし、ここではパターンマッチングによる抽出も併用
                if ('既往症' in user_message or '病気' in user_message or '疾患' in user_message or
                    'history' in user_message.lower() or 'disease' in user_message.lower() or 'condition' in user_message.lower()):
                    history_patterns = [
                        r'既往症[はが]?([^。、\n]+)',
                        r'病気[はが]?([^。、\n]+)',
                        r'疾患[はが]?([^。、\n]+)',
                        r'([^。、\n]*病[^。、\n]*)',
                        r'have\s+([^,\s]+(?:\s+[^,\s]+)*)\s+history',
                        r'history\s+of\s+([^,\n]+)',
                        r'disease[:\s]+([^,\n]+)',
                        r'condition[:\s]+([^,\n]+)'
                    ]
                    for pattern in history_patterns:
                        match = re.search(pattern, user_message)
                        if match:
                            history_name = match.group(1).strip()
                            if history_name:
                                existing_history = user_attributes.get('medical_history', [])
                                if history_name not in existing_history:
                                    user_attributes['medical_history'] = existing_history + [history_name]
                                    registered_info['medical_history'] = {
                                        'registered': True,
                                        'value': user_attributes['medical_history'],
                                        'source': '入力から抽出',
                                        'message': f'既往歴: {", ".join(user_attributes["medical_history"])}'
                                    }
                                    logger.info(f"📝 既往歴を登録: {history_name}")
                                    break
                            
                # 「なんですが」「ですが」などの逆接表現の後に症状が続く場合、診断名を既往症として抽出
                # 例：「癌なんですが、頭痛がひどい」
                inverse_patterns = [
                    r'([^。、\n]+)なんですが',
                    r'([^。、\n]+)ですが',
                    r'([^。、\n]+)だけど',
                    r'([^。、\n]+)ですが、',
                    r'([^。、\n]+)なんですが、'
                ]
                for pattern in inverse_patterns:
                    match = re.search(pattern, user_message)
                    if match:
                        potential_diagnosis = match.group(1).strip()
                        # 診断名として認識される可能性がある単語をチェック
                        # 癌、糖尿病、高血圧、心臓病、肝臓病、腎臓病など
                        diagnosis_keywords = ['癌', 'がん', '糖尿病', '高血圧', '心臓病', '肝臓病', '腎臓病', 
                                              '喘息', 'てんかん', 'うつ病', '統合失調症', 'パーキンソン病']
                        if any(keyword in potential_diagnosis for keyword in diagnosis_keywords):
                            existing_history = user_attributes.get('medical_history', [])
                            # 診断名を抽出（キーワードを含む部分）
                            for keyword in diagnosis_keywords:
                                if keyword in potential_diagnosis:
                                    if keyword not in existing_history:
                                        user_attributes['medical_history'] = existing_history + [keyword]
                                        registered_info['medical_history'] = {
                                            'registered': True,
                                            'value': user_attributes['medical_history'],
                                            'source': '入力から抽出（逆接表現）',
                                            'message': f'既往歴: {", ".join(user_attributes["medical_history"])}'
                                        }
                                        logger.info(f"📝 既往歴を登録（逆接表現）: {keyword}")
                                        break
                            break
            except Exception as e:
                logger.info(f"⚠️ 既往歴の抽出でエラー: {str(e)}")
                        
            # 妊娠状態の抽出・登録
            try:
                if '妊娠' in user_message or 'pregnant' in user_message.lower():
                    if '妊娠していません' in user_message or '妊娠中ではありません' in user_message or '妊娠していない' in user_message or 'not pregnant' in user_message.lower():
                        if user_attributes.get('pregnant') != False:
                            user_attributes['pregnant'] = False
                            registered_info['pregnant'] = {
                                'registered': True,
                                'value': False,
                                'source': '入力から抽出',
                                'message': '妊娠状態: 妊娠していない'
                            }
                            logger.info(f"📝 妊娠状態を登録: False")
                    elif any(kw in user_message for kw in ['妊娠中です', '妊娠中', '妊娠しています', '妊娠しました', '妊娠してます', '妊娠した', '妊婦です']) or 'pregnant' in user_message.lower():
                        if user_attributes.get('pregnant') != True:
                            user_attributes['pregnant'] = True
                            registered_info['pregnant'] = {
                                'registered': True,
                                'value': True,
                                'source': '入力から抽出',
                                'message': '妊娠状態: 妊娠中'
                            }
                            logger.info(f"📝 妊娠状態を登録: True")
            except Exception as e:
                logger.info(f"⚠️ 妊娠状態の抽出でエラー: {str(e)}")
                        
            # 授乳状態の抽出・登録
            try:
                if '授乳' in user_message or 'breastfeeding' in user_message.lower():
                    if '授乳していません' in user_message or '授乳中ではありません' in user_message or '授乳していない' in user_message or 'not breastfeeding' in user_message.lower():
                        if user_attributes.get('breastfeeding') != False:
                            user_attributes['breastfeeding'] = False
                            registered_info['breastfeeding'] = {
                                'registered': True,
                                'value': False,
                                'source': '入力から抽出',
                                'message': '授乳状態: 授乳していない'
                            }
                            logger.info(f"📝 授乳状態を登録: False")
                    elif '授乳中です' in user_message or '授乳中' in user_message or '授乳しています' in user_message or 'breastfeeding' in user_message.lower():
                        if user_attributes.get('breastfeeding') != True:
                            user_attributes['breastfeeding'] = True
                            registered_info['breastfeeding'] = {
                                'registered': True,
                                'value': True,
                                'source': '入力から抽出',
                                'message': '授乳状態: 授乳中'
                            }
                            logger.info(f"📝 授乳状態を登録: True")
            except Exception as e:
                logger.info(f"⚠️ 授乳状態の抽出でエラー: {str(e)}")
                        
            # 症状期間の抽出・登録
            try:
                if ('続いています' in user_message or 'から' in user_message or 
                        'started' in user_message.lower() or 'ago' in user_message.lower()):
                    duration_patterns = [
                        (r'(今日|きょう)から', 0),
                        (r'(昨日|きのう)から', 1),
                        (r'(\d+)日前から', None),
                        (r'(\d+)週間前から', None),
                        (r'(\d+)\s*days?\s*ago', None),
                        (r'(\d+)\s*weeks?\s*ago', None),
                        (r'(\d+)\s*months?\s*ago', None)
                    ]
                    for pattern, days in duration_patterns:
                        match = re.search(pattern, user_message)
                        if match:
                            if days is not None:
                                duration_days = days
                            else:
                                if '日前' in user_message:
                                    num_match = re.search(r'(\d+)日前', user_message)
                                    if num_match:
                                        duration_days = int(num_match.group(1))
                                elif '週間前' in user_message:
                                    num_match = re.search(r'(\d+)週間前', user_message)
                                    if num_match:
                                        duration_days = int(num_match.group(1)) * 7
                                elif 'days ago' in user_message.lower():
                                    num_match = re.search(r'(\d+)\s*days?\s*ago', user_message, re.IGNORECASE)
                                    if num_match:
                                        duration_days = int(num_match.group(1))
                                elif 'weeks ago' in user_message.lower():
                                    num_match = re.search(r'(\d+)\s*weeks?\s*ago', user_message, re.IGNORECASE)
                                    if num_match:
                                        duration_days = int(num_match.group(1)) * 7
                                elif 'months ago' in user_message.lower():
                                    num_match = re.search(r'(\d+)\s*months?\s*ago', user_message, re.IGNORECASE)
                                    if num_match:
                                        duration_days = int(num_match.group(1)) * 30
                                else:
                                    continue
                                        
                            if user_attributes.get('symptom_duration_days') != duration_days:
                                user_attributes['symptom_duration_days'] = duration_days
                                registered_info['symptom_duration_days'] = {
                                    'registered': True,
                                    'value': duration_days,
                                    'source': '入力から抽出',
                                    'message': f'症状期間: {duration_days}日前から'
                                }
                                logger.info(f"📝 症状期間を登録: {duration_days}日前から")
                            break
            except Exception as e:
                logger.info(f"⚠️ 症状期間の抽出でエラー: {str(e)}")
                        
            # セッションとDBに保存
            try:
                session['user_attributes'] = user_attributes
                session.modified = True
                            
                sid = session.get('_id')
                if sid:
                    session_data = get_session_from_db(sid)
                    if session_data:
                        session_data['user_attributes'] = user_attributes
                        session_data['last_activity'] = datetime.now()
                        save_session_to_db(sid, session_data)
            except Exception as e:
                logger.info(f"⚠️ ユーザー属性の保存でエラー: {str(e)}")
                        
        except Exception as e:
            logger.info(f"⚠️ ユーザー情報登録処理でエラー: {str(e)}")
            info_registration_success = False
                    
        # 登録された情報をまとめて通知（成功・失敗に関係なく）
        logger.info(f"📢 通知メッセージ生成処理を開始")
        try:
            registered_items = []
            for key, info in registered_info.items():
                if info['registered']:
                    registered_items.append(info['message'])
                elif user_attributes.get(key) is not None:
                    # 既に登録済みの情報も表示
                    if key == 'gender':
                        registered_items.append(f'性別: {user_attributes.get(key)}（既に登録済み）')
                    elif key == 'age':
                        registered_items.append(f'年齢: {user_attributes.get(key)}歳（既に登録済み）')
                    elif key == 'pregnant':
                        if user_attributes.get(key):
                            registered_items.append('妊娠状態: 妊娠中（既に登録済み）')
                        else:
                            registered_items.append('妊娠状態: 妊娠していない（既に登録済み）')
                    elif key == 'breastfeeding':
                        if user_attributes.get(key):
                            registered_items.append('授乳状態: 授乳中（既に登録済み）')
                        else:
                            registered_items.append('授乳状態: 授乳していない（既に登録済み）')
                    elif key in ['allergies', 'current_medications', 'medical_history']:
                        value = user_attributes.get(key, [])
                        if value:
                            registered_items.append(f'{key}: {", ".join(value) if isinstance(value, list) else value}（既に登録済み）')
                        
            # 妊娠可能性が検出された場合、通知メッセージに追加
            pregnancy_possible_value = user_attributes.get('pregnancy_possible')
            if pregnancy_possible_value in ['high', 'low']:
                # 妊娠可能性が検出された場合、「可能性あり」として表示
                registered_items.append('妊娠状態: 可能性あり')
                        
            # 登録された情報がある場合、またはエラーが発生した場合に通知メッセージを生成
            if registered_items or not info_registration_success:
                # 通知メッセージを生成
                if registered_items:
                    info_message = "💡 以下の情報を登録しました：\n" + "\n".join([f"・{item}" for item in registered_items])
                else:
                    info_message = "💡 情報登録を試行しましたが、新しい情報は検出されませんでした。"
                            
                if not info_registration_success:
                    info_message += "\n\n⚠️ 情報登録処理中にエラーが発生しましたが、医薬品推奨を続行します。"
                            
                # 通知メッセージをセッションに追加（即座に表示されるように）
                if 'messages' not in session:
                    session['messages'] = []
                            
                # 通常のメッセージと同じスタイルを使用
                import html
                escaped_info_message = html.escape(info_message)
                info_message_html = escaped_info_message.replace('\n', '<br>')
                info_bot_response = {
                    'type': 'bot',
                    'content': f'<div class="chat-response user-info-notification"><p>{info_message_html}</p><button class="edit-info-btn" onclick="editUserInfo()">情報を修正</button></div>',
                    'diagnosis': None,
                    'timestamp': datetime.now().isoformat()
                }
                # ユーザーメッセージの直後に追加（最後のユーザーメッセージの後）
                user_msg_index = -1
                for i in range(len(session['messages']) - 1, -1, -1):
                    if session['messages'][i].get('type') == 'user':
                        user_msg_index = i
                        break
                            
                if user_msg_index >= 0:
                    # ユーザーメッセージの直後に挿入
                    session['messages'].insert(user_msg_index + 1, info_bot_response)
                else:
                    # ユーザーメッセージが見つからない場合は最後に追加
                    session['messages'].append(info_bot_response)
                session.modified = True
                logger.info(f"📢 情報登録通知メッセージを追加: {len(registered_items)}件の情報を登録（user_msg_index={user_msg_index}）")
                            
                # DBにも保存
                sid = session.get('_id')
                if sid:
                    session_data = get_session_from_db(sid)
                    if session_data:
                        if 'messages' not in session_data:
                            session_data['messages'] = []
                        # DBでも同様にユーザーメッセージの直後に挿入
                        user_msg_index_db = -1
                        for i in range(len(session_data['messages']) - 1, -1, -1):
                            if session_data['messages'][i].get('type') == 'user':
                                user_msg_index_db = i
                                break
                                    
                        if user_msg_index_db >= 0:
                            session_data['messages'].insert(user_msg_index_db + 1, info_bot_response)
                        else:
                            session_data['messages'].append(info_bot_response)
                        session_data['last_activity'] = datetime.now()
                        save_session_to_db(sid, session_data)
                        logger.info(f"💾 情報登録通知メッセージをDBに保存（user_msg_index_db={user_msg_index_db}）")
        except Exception as e:
            logger.info(f"⚠️ 通知メッセージの生成でエラー: {str(e)}")
                    
        # ルールベース推奨用のuser_infoを構築（NLU解析後の最新のuser_attributesを使用）
        # NLU解析で性別が自動登録された場合、user_attributesが更新されているため、再構築が必要
        user_info = {
            'age': user_attributes.get('age'),
            'gender': user_attributes.get('gender'),
            'pregnant': user_attributes.get('pregnant'),
            'breastfeeding': user_attributes.get('breastfeeding'),
            'current_medications': user_attributes.get('current_medications', []),
            'allergies': user_attributes.get('allergies', []),
            'symptom_duration_days': user_attributes.get('symptom_duration_days'),
            'treatment_mention': user_attributes.get('treatment_mention', False),  # 治療中フラグ
            'medical_prevention_request': user_attributes.get('medical_prevention_request', False),  # 医薬的な予防フラグ
            'user_text': sanitized_message  # ユーザー入力テキスト（禁忌チェックで使用）
        }
        logger.info(f"📋 ユーザー情報（NLU解析前）: age={user_info.get('age')}, gender={user_info.get('gender')}, pregnant={user_info.get('pregnant')}, allergies={user_info.get('allergies')}")
                    
        # ステップ1: NLU解析（エージェント ON 時は NLUAgent 経由）
        from src.handlers.chat.nlu_resolve import resolve_nlu_for_recommendation

        nlu_result = {}
        try:
            logger.info(f"🔍 NLU解析を実行中: processed_message={processed_message[:50]}...")
            nlu_result = resolve_nlu_for_recommendation(
                processed_message,
                user_info,
                recommendation_client,
                session_id=sid,
            )
            logger.info(f"✅ NLU解析完了: nlu_result keys={list(nlu_result.keys())}")
            logger.info(f"✅ NLU解析完了: gender_detected={nlu_result.get('gender_detected')}, pregnancy_possible={nlu_result.get('pregnancy_possible')}")
        except Exception as nlu_error:
            logger.info(f"⚠️ NLU解析エラー: {str(nlu_error)}")
            nlu_result = {
                'gender_detected': {'detected': False},
                'pregnancy_possible': {'detected': False}
            }
                    
        # ステップ2: 性別自動判定と妊娠可能性検出の処理（常に実行）
        gender_detected = nlu_result.get('gender_detected')
        if gender_detected is None:
            gender_detected = {}
        pregnancy_possible = nlu_result.get('pregnancy_possible')
        if pregnancy_possible is None:
            pregnancy_possible = {}
        nlu_symptoms = nlu_result.get('symptoms', [])
        logger.info(f"📋 NLU解析結果: gender_detected={gender_detected}, pregnancy_possible={pregnancy_possible}, symptoms={nlu_symptoms}")
                    
        # 性別自動判定の処理（既に性別が登録されている場合は上書きしない）
        gender_auto_registered_from_nlu = False
        gender_notification_message_from_nlu = None
        try:
            # gender_detectedが空の辞書でない場合、かつdetectedがTrueの場合に処理
            logger.info(f"🔍 性別検出を確認: gender_detected={gender_detected}, type={type(gender_detected)}, len={len(gender_detected) if isinstance(gender_detected, dict) else 'N/A'}")
            if gender_detected and isinstance(gender_detected, dict) and len(gender_detected) > 0 and gender_detected.get('detected', False):
                detected_gender = gender_detected.get('gender')
                detected_symptoms = gender_detected.get('symptoms', [])
                reason = gender_detected.get('reason', '')
                logger.info(f"✅ 性別が検出されました: gender={detected_gender}, reason={reason}")
                            
                current_gender = user_attributes.get('gender')
                logger.info(f"📋 現在の性別: {current_gender}")
                            
                # 既に性別が登録されている場合は上書きしない
                if current_gender:
                    if detected_gender == 'female' and current_gender == '男性':
                        warning = gender_detected.get('warning', '')
                        if warning:
                            gender_notification_message_from_nlu = f"⚠️ {warning}"
                            logger.warning(f"👤 性別自動判定の警告: {warning}")
                else:
                    # 性別が未登録の場合のみ自動登録
                    if detected_gender == 'female':
                        user_attributes['gender'] = '女性'
                        gender_auto_registered_from_nlu = True
                        gender_notification_message_from_nlu = f"💡 {reason}。性別を女性として登録しました。"
                        logger.info(f"👤 性別自動登録（NLU解析から）: {reason}")
                                    
                        # セッションとDBに保存
                        try:
                            session['user_attributes'] = user_attributes
                            session.modified = True
                                        
                            sid = session.get('_id')
                            if sid:
                                session_data = get_session_from_db(sid)
                                if session_data:
                                    session_data['user_attributes'] = user_attributes
                                    session_data['last_activity'] = datetime.now()
                                    save_session_to_db(sid, session_data)
                        except Exception as e:
                            logger.info(f"⚠️ 性別自動登録の保存でエラー: {str(e)}")
                                    
                        # 性別自動登録の通知を通常メッセージとして独立して表示
                        try:
                            if 'messages' not in session:
                                session['messages'] = []
                            # 通常のメッセージと同じスタイルを使用
                            import html
                            escaped_gender_message = html.escape(gender_notification_message_from_nlu)
                            gender_bot_response = {
                                'type': 'bot',
                                'content': f'<div class="chat-response gender-notification"><p>{escaped_gender_message}</p></div>',
                                'diagnosis': None,
                                'timestamp': datetime.now().isoformat()
                            }
                            session['messages'].append(gender_bot_response)
                            session.modified = True
                                        
                            # DBにも保存
                            sid = session.get('_id')
                            if sid:
                                session_data = get_session_from_db(sid)
                                if session_data:
                                    if 'messages' not in session_data:
                                        session_data['messages'] = []
                                    session_data['messages'].append(gender_bot_response)
                                    session_data['last_activity'] = datetime.now()
                                    save_session_to_db(sid, session_data)
                        except Exception as e:
                            logger.info(f"⚠️ 性別自動登録の通知メッセージの保存でエラー: {str(e)}")
                    elif detected_gender == 'male':
                        user_attributes['gender'] = '男性'
                        gender_auto_registered_from_nlu = True
                        gender_notification_message_from_nlu = f"💡 {reason}。性別を男性として登録しました。"
                        logger.info(f"👤 性別自動登録（NLU解析から）: {reason}")
                                    
                        # セッションとDBに保存
                        try:
                            session['user_attributes'] = user_attributes
                            session.modified = True
                                        
                            sid = session.get('_id')
                            if sid:
                                session_data = get_session_from_db(sid)
                                if session_data:
                                    session_data['user_attributes'] = user_attributes
                                    session_data['last_activity'] = datetime.now()
                                    save_session_to_db(sid, session_data)
                        except Exception as e:
                            logger.info(f"⚠️ 性別自動登録の保存でエラー: {str(e)}")
                                    
                        # 性別自動登録の通知を通常メッセージとして独立して表示
                        try:
                            if 'messages' not in session:
                                session['messages'] = []
                            # 通常のメッセージと同じスタイルを使用
                            import html
                            escaped_gender_message = html.escape(gender_notification_message_from_nlu)
                            gender_bot_response = {
                                'type': 'bot',
                                'content': f'<div class="chat-response gender-notification"><p>{escaped_gender_message}</p></div>',
                                'diagnosis': None,
                                'timestamp': datetime.now().isoformat()
                            }
                            session['messages'].append(gender_bot_response)
                            session.modified = True
                                        
                            # DBにも保存
                            sid = session.get('_id')
                            if sid:
                                session_data = get_session_from_db(sid)
                                if session_data:
                                    if 'messages' not in session_data:
                                        session_data['messages'] = []
                                    session_data['messages'].append(gender_bot_response)
                                    session_data['last_activity'] = datetime.now()
                                    save_session_to_db(sid, session_data)
                        except Exception as e:
                            logger.info(f"⚠️ 性別自動登録の通知メッセージの保存でエラー: {str(e)}")
        except Exception as e:
            logger.info(f"⚠️ 性別自動判定の処理でエラー: {str(e)}")
                    
        # 性別が自動登録された場合、または既に「女性」として登録されている場合、妊娠可能性検出を再計算
        current_gender = user_attributes.get('gender')
        is_female = (gender_auto_registered_from_nlu or current_gender == '女性')
                    
        try:
            if is_female and pregnancy_possible.get('detected', False):
                pregnancy_score = pregnancy_possible.get('score', 0.0)
                pregnancy_detected_symptoms = pregnancy_possible.get('symptoms', [])
                            
                if pregnancy_score >= 2.0:
                    pregnancy_possible = {
                        "detected": True,
                        "score": pregnancy_score,
                        "symptoms": pregnancy_detected_symptoms,
                        "confidence": "high",
                        "gender": "female"
                    }
                    if gender_auto_registered_from_nlu:
                        logger.info(f"🤰 妊娠可能性検出を再計算: 性別が女性として登録されたため、高信頼度として再設定（score={pregnancy_score:.2f}）")
                    else:
                        logger.info(f"🤰 妊娠可能性検出を再計算: 性別が既に女性として登録されているため、高信頼度として再設定（score={pregnancy_score:.2f}）")
                elif pregnancy_score > 0.0:
                    pregnancy_possible = {
                        "detected": True,
                        "score": pregnancy_score,
                        "symptoms": pregnancy_detected_symptoms,
                        "confidence": "high",
                        "gender": "female"
                    }
                    if gender_auto_registered_from_nlu:
                        logger.info(f"🤰 妊娠可能性検出を再計算: 性別が女性として登録されたため、高信頼度として再設定（score={pregnancy_score:.2f}）")
                    else:
                        logger.info(f"🤰 妊娠可能性検出を再計算: 性別が既に女性として登録されているため、高信頼度として再設定（score={pregnancy_score:.2f}）")
        except Exception as e:
            logger.info(f"⚠️ 妊娠可能性検出の再計算でエラー: {str(e)}")
                    
        # ステップ3: ChatGPTで医薬品の種類を判定
        start_time = time.time()
        try:
            logger.info(f"🔍 Step 3: Analyzing medicine type with ChatGPT...")
            mark_processing_step(sid, "symptom_analysis")
            analysis_result = analyze_symptoms_and_medicine_type(processed_message, recommendation_client)  # 方言変換後のテキストを使用
                        
            # 診断名が検出された場合の処理（早期リターンでAPIコストを削減）
            if analysis_result.get('is_diagnosis', False):
                diagnosis_response = analysis_result.get('diagnosis_response', {})
                diagnosis_message = diagnosis_response.get('message', '診断名が検出されました。医師にご相談ください。')
                diagnosis_type = analysis_result.get('diagnosis_type', 'unknown')
                            
                logger.info(f"🏥 診断名検出による早期リターン: {diagnosis_type} - {user_message}")
                            
                # HTMLエスケープ処理
                import html
                escaped_user_message = html.escape(user_message)
                escaped_diagnosis_message = html.escape(diagnosis_message)
                diagnosis_message_html = escaped_diagnosis_message.replace('\n', '<br>')
                            
                # 評価ボタン用のデータを準備
                import json
                feedback_data = {
                    'user_message': escaped_user_message,
                    'ai_response': escaped_diagnosis_message,
                    'security_score': None,
                    'error_type': 'diagnosis_detected',
                    'diagnosis_type': diagnosis_type
                }
                bug_report_data_attrs = f'data-user-message="{escaped_user_message}" data-ai-response="{escaped_diagnosis_message}" data-security-score=""'
                            
                bot_content = format_diagnosis_notification(
                    diagnosis_message_html,
                    feedback_data,
                    bug_report_attrs=bug_report_data_attrs,
                )
                bot_response = {
                    'type': 'bot',
                    'content': bot_content,
                    'diagnosis': None,
                    'diagnosis_type': diagnosis_type,
                    'timestamp': datetime.now().isoformat()
                }
                if 'messages' not in session:
                    session['messages'] = []
                session['messages'].append(bot_response)
                session.modified = True
                            
                # DBにも保存
                sid = session.get('_id')
                if sid:
                    session_data = get_session_from_db(sid)
                    if not session_data:
                        session_data = {
                            'session_id': sid,
                            'username': session.get('username', 'Unknown'),
                            'messages': [],
                            'last_activity': datetime.now(),
                            'client_ip': client.client_ip,
                            'user_agent': client.user_agent,
                            'user_attributes': session.get('user_attributes', {}),
                            'session_active': True
                        }
                    if 'messages' not in session_data:
                        session_data['messages'] = []
                    session_data['messages'].append(bot_response)
                    session_data['last_activity'] = datetime.now()
                    save_session_to_db(sid, session_data)
                            
                message_count = len(session['messages'])
                return {'status': 'ok', 'message_count': message_count}, 200
                        
            medicine_type = analysis_result.get('medicine_type')
            symptoms = analysis_result.get('symptoms', [])
                        
            # 医薬品種類が判定できない場合（Noneまたは「その他」）の処理
            if not medicine_type or medicine_type == 'その他':
                logger.warning(f"⚠️ 医薬品種類が判定できませんでした: {medicine_type}")
                            
                # 「その他」の場合でも、NLU解析結果から症状を取得し、適切なmedicine_typeを推測
                if nlu_symptoms:
                    from src.core.rule_based_recommendation import SYMPTOM_DICTIONARY
                                
                    # NLU解析結果から検出された症状に基づいてmedicine_typeを推測
                    detected_medicine_types = set()
                    for symptom_name in nlu_symptoms:
                        symptom_data = SYMPTOM_DICTIONARY.get(symptom_name)
                        if symptom_data:
                            medicine_types_for_symptom = symptom_data.get('medicine_types', [])
                            detected_medicine_types.update(medicine_types_for_symptom)
                                
                    if detected_medicine_types:
                        # 最初に見つかったmedicine_typeを使用（優先順位は症状のweightに基づく）
                        medicine_type = list(detected_medicine_types)[0]
                        logger.info(f"🔍 NLU解析結果からmedicine_typeを推測: {medicine_type} (検出された症状: {nlu_symptoms})")
                        
            # 妊娠の可能性が検出された場合の処理
            pregnancy_message = None
            try:
                if pregnancy_possible.get('detected', False):
                    confidence = pregnancy_possible.get('confidence')
                    score = pregnancy_possible.get('score', 0.0)
                    detected_symptoms = pregnancy_possible.get('symptoms', [])
                    gender = pregnancy_possible.get('gender', 'unknown')
                                
                    logger.info(f"🤰 妊娠の可能性検出: confidence={confidence}, score={score:.2f}, symptoms={detected_symptoms}, gender={gender}")
                                
                    if confidence == 'high':
                        user_attributes['pregnancy_possible'] = 'high'
                        user_info['pregnancy_possible'] = 'high'
                        pregnancy_message = "⚠️ 妊娠の可能性があります。医師の診断を受けてください。市販薬の使用は医師にご相談ください。"
                        logger.info(f"📋 妊娠の可能性（高信頼度）を設定: pregnancy_possible=high")
                    elif confidence == 'low':
                        user_attributes['pregnancy_possible'] = 'low'
                        user_info['pregnancy_possible'] = 'low'
                        pregnancy_message = "⚠️ 一部の症状は妊娠の可能性を示す場合がありますが、性別情報がないため確定できません。医師にご相談ください。"
                        logger.info(f"📋 妊娠の可能性（低信頼度）を設定: pregnancy_possible=low")
            except Exception as e:
                logger.info(f"⚠️ 妊娠可能性検出の処理でエラー: {str(e)}")
                        
            # 医薬品種類が判定できない場合（Noneまたは「その他」）の処理
            # 情報登録の成功・失敗に関係なく、医薬品推奨処理に移る
            if not medicine_type or medicine_type == 'その他':
                    # メッセージの組み立て
                    consultation_messages = []
                                
                    # 性別自動登録の通知は既に独立したメッセージとして表示されているため、エラーメッセージには含めない
                    # if gender_notification_message:
                    #     consultation_messages.append(gender_notification_message)
                                
                    if pregnancy_message:
                        consultation_messages.append(pregnancy_message)
                                
                    # 医薬品推奨ができない場合のメッセージ
                    if not medicine_type or medicine_type == 'その他':
                        consultation_messages.append("⚠️ 医薬品種類が判定できませんでした。症状をより具体的に記述していただくか、医師にご相談ください。")
                                
                    doctor_consultation = '\n\n'.join(consultation_messages) if consultation_messages else "症状をより具体的に記述していただくか、医師にご相談ください。"
                                
                    # エラーメッセージの内容（NLU解析結果を含める）
                    error_message = doctor_consultation if consultation_messages else '医薬品種類が判定できませんでした。症状をより具体的に記述していただくか、医師にご相談ください。'
                                
                    # 評価ボタン用のデータを準備（HTMLエスケープ処理）
                    import json
                    import html
                                
                    # HTMLエスケープ処理
                    escaped_user_message = html.escape(user_message)
                    escaped_error_message = html.escape(error_message)
                    escaped_doctor_consultation = html.escape(doctor_consultation)
                                
                    feedback_data = {
                        'user_message': escaped_user_message,
                        'ai_response': escaped_error_message,
                        'security_score': None,
                        'error_type': 'medicine_type_detection_failed'
                    }
                                
                    # JSONエンコードしてHTMLエスケープ
                    bug_report_data_attrs = f'data-user-message="{escaped_user_message}" data-ai-response="{escaped_error_message}" data-security-score=""'
                                
                    doctor_consultation_html = escaped_doctor_consultation.replace('\n', '<br>')
                    bot_content = format_medicine_type_notice(
                        doctor_consultation_html,
                        feedback_data,
                        bug_report_attrs=bug_report_data_attrs,
                    )
                    bot_response = {
                        'type': 'bot',
                        'content': bot_content,
                        'diagnosis': None,
                        'timestamp': datetime.now().isoformat()
                    }
                    if 'messages' not in session:
                        session['messages'] = []
                    session['messages'].append(bot_response)
                    session.modified = True
                                
                    # DBにも保存
                    sid = session.get('_id')
                    if sid:
                        session_data = get_session_from_db(sid)
                        if not session_data:
                            session_data = {
                                'session_id': sid,
                                'username': session.get('username', 'Unknown'),
                                'messages': [],
                                'last_activity': datetime.now(),
                                'client_ip': client.client_ip,
                                'user_agent': client.user_agent,
                                'user_attributes': session.get('user_attributes', {}),
                                'session_active': True
                            }
                        if 'messages' not in session_data:
                            session_data['messages'] = []
                        session_data['messages'].append(bot_response)
                        session_data['last_activity'] = datetime.now()
                        save_session_to_db(sid, session_data)
                                
                    message_count = len(session['messages'])
                    return {'status': 'ok', 'message_count': message_count}, 200
                        
            logger.info(f"📋 Detected medicine type: {medicine_type}")
            logger.info(f"📋 Detected symptoms: {symptoms}")
                        
            # ステップ2: 医薬品の種類に応じて推奨アルゴリズムを選択
            # SYMPTOM_DICTIONARYから動的に対応種類を判定
            from src.core.rule_based_recommendation import SYMPTOM_DICTIONARY
                        
            # SYMPTOM_DICTIONARYに含まれる全てのmedicine_typesを取得
            supported_types = set()
            for symptom_data in SYMPTOM_DICTIONARY.values():
                supported_types.update(symptom_data.get('medicine_types', []))
                        
            # 全ての医薬品種類でルールベース推奨を使用
            # confidence < 0.4 の場合のみGPTフォールバック
            if medicine_type in supported_types:
                # ルールベースアルゴリズムを使用
                logger.info(f"✅ Using RULE-BASED algorithm for {medicine_type}")
                            
                # ユーザー属性データをセッションから取得
                user_attributes = session.get('user_attributes', {
                    'age': None,
                    'gender': None,
                    'pregnant': None,
                    'breastfeeding': None,
                    'current_medications': [],
                    'allergies': [],
                    'medical_history': [],
                    'symptom_duration_days': None,
                    'other_info': None
                })
                            
                # メッセージから属性情報を抽出してセッションに保存
                            
                # 年齢の抽出
                age_match = re.search(r'(\d+)\s*歳', user_message)
                if age_match:
                    extracted_age = int(age_match.group(1))
                    user_attributes['age'] = extracted_age
                    logger.info(f"📋 Extracted age from message: {extracted_age}")
                            
                # 性別の抽出
                previous_gender = user_attributes.get('gender')
                if '女性' in user_message or '女' in user_message:
                    user_attributes['gender'] = '女性'
                    logger.info(f"📋 Detected gender: 女性")
                                
                    # 女性が登録された場合、妊娠の可能性について通知（初回のみ）
                    if previous_gender != '女性' and not user_attributes.get('pregnancy_notified', False):
                        user_attributes['pregnancy_notified'] = True
                        # 通知メッセージを追加（後で表示）
                        if 'pregnancy_notification' not in user_attributes:
                            user_attributes['pregnancy_notification'] = True
                        logger.info(f"📋 女性登録時の妊娠可能性通知フラグを設定")
                elif '男性' in user_message or '男' in user_message:
                    user_attributes['gender'] = '男性'
                    logger.info(f"📋 Detected gender: 男性")
                            
                # 妊娠・授乳の検出
                if '妊娠' in user_message or '妊婦' in user_message:
                    user_attributes['pregnant'] = True
                    logger.info(f"📋 Detected pregnancy status from message")
                elif '妊娠していない' in user_message or '妊娠してない' in user_message:
                    user_attributes['pregnant'] = False
                    logger.info(f"📋 Detected not pregnant from message")
                            
                if '授乳' in user_message:
                    user_attributes['breastfeeding'] = True
                    logger.info(f"📋 Detected breastfeeding status from message")
                elif '授乳していない' in user_message or '授乳してない' in user_message:
                    user_attributes['breastfeeding'] = False
                    logger.info(f"📋 Detected not breastfeeding from message")
                            
                # アレルギーの抽出
                if 'アレルギー' in user_message:
                    if 'ない' in user_message or 'なし' in user_message:
                        user_attributes['allergies'] = ['なし']
                        logger.info(f"📋 No allergies detected")
                    else:
                        # アレルギー情報を追加（簡易的）
                        allergy_match = re.search(r'アレルギー[：:](.*?)(?:[。、]|$)', user_message)
                        if allergy_match:
                            allergy_info = allergy_match.group(1).strip()
                            if allergy_info and allergy_info not in user_attributes['allergies']:
                                user_attributes['allergies'].append(allergy_info)
                                logger.info(f"📋 Extracted allergy: {allergy_info}")
                            
                # セッションに保存
                session['user_attributes'] = user_attributes
                session.modified = True
                            
                # DBも更新
                sid = session.get('_id')
                if sid:
                    session_data = get_session_from_db(sid)
                    if session_data:
                        session_data['user_attributes'] = user_attributes
                        session_data['last_activity'] = datetime.now()
                        save_session_to_db(sid, session_data)
                            
                # ルールベース推奨用のuser_infoを構築（デフォルト値は使用しない）
                user_info = {
                    'age': user_attributes.get('age'),  # Noneのまま渡す
                    'gender': user_attributes.get('gender'),
                    'pregnant': user_attributes.get('pregnant'),  # Noneのまま渡す
                    'breastfeeding': user_attributes.get('breastfeeding'),  # Noneのまま渡す
                    'current_medications': user_attributes.get('current_medications', []),
                    'allergies': user_attributes.get('allergies', []),
                    'symptom_duration_days': user_attributes.get('symptom_duration_days'),  # 症状期間を追加
                    'treatment_mention': user_attributes.get('treatment_mention', False),  # 治療中フラグ
                    'medical_prevention_request': user_attributes.get('medical_prevention_request', False),  # 医薬的な予防フラグ
                    'user_text': sanitized_message  # ユーザー入力テキスト（禁忌チェックで使用）
                }
                            
                logger.info(f"📋 User info for recommendation: age={user_info.get('age')}, gender={user_info.get('gender')}, pregnant={user_info.get('pregnant')}, allergies={user_info.get('allergies')}")
                # NLU解析で性別が自動登録された場合、user_attributesが更新されているため、user_infoを再構築
                user_info = {
                    'age': user_attributes.get('age'),
                    'gender': user_attributes.get('gender'),
                    'pregnant': user_attributes.get('pregnant'),
                    'breastfeeding': user_attributes.get('breastfeeding'),
                    'current_medications': user_attributes.get('current_medications', []),
                    'allergies': user_attributes.get('allergies', []),
                    'symptom_duration_days': user_attributes.get('symptom_duration_days'),
                    'treatment_mention': user_attributes.get('treatment_mention', False),  # 治療中フラグ
                    'medical_prevention_request': user_attributes.get('medical_prevention_request', False),  # 医薬的な予防フラグ
                    'user_text': sanitized_message  # ユーザー入力テキスト（禁忌チェックで使用）
                }
                logger.info(f"📋 User info for recommendation（再構築後）: age={user_info.get('age')}, gender={user_info.get('gender')}, pregnant={user_info.get('pregnant')}, allergies={user_info.get('allergies')}")
                            
                # ユーザー要望を抽出してuser_infoに追加
                try:
                    from src.core.medicine_logic import extract_user_preferences
                    nlu_result_for_preferences = recommendation_result.get('nlu_result', {}) if 'recommendation_result' in locals() else {}
                    user_preferences = extract_user_preferences(user_message, nlu_result_for_preferences, user_info)
                    user_info['user_preferences'] = user_preferences
                    user_info['user_message'] = user_message  # user_messageも追加（証判定などで使用）
                    user_info['prefers_kampo'] = user_preferences.get('prefers_kampo', False)
                    user_info['prefers_not_kampo'] = user_preferences.get('prefers_not_kampo', False)
                    logger.info(f"📋 ユーザー要望を抽出: {user_preferences}")
                except Exception as e:
                    logger.warning(f"⚠️ ユーザー要望抽出でエラー: {str(e)}")
                    user_info['user_preferences'] = None
                            
                mark_processing_step(sid, "safety")
                mark_processing_step(sid, "medicine_select")
                recommendation_result = rule_based_medicine_recommendation(
                    processed_message,  # 方言変換後のテキストを使用
                    user_info,
                    recommendation_client,
                    session_id=sid,
                    precomputed_nlu=nlu_result if nlu_result else None,
                )
                            
                # ルールベース結果のデバッグログ
                logger.info(f"🔍 Rule-based result: {recommendation_result.get('status', 'unknown')}")
                logger.info(f"🔍 Rule-based medicines count: {len(recommendation_result.get('recommended_medicines', []))}")
                            
                # NLU解析結果から性別自動判定と妊娠の可能性を取得
                nlu_result = recommendation_result.get('nlu_result', {})
                gender_detected = nlu_result.get('gender_detected', {})
                pregnancy_possible = nlu_result.get('pregnancy_possible', {})
                            
                # 性別自動判定の処理
                gender_auto_registered = False
                gender_notification_message = None
                if gender_detected.get('detected', False):
                    detected_gender = gender_detected.get('gender')
                    detected_symptoms = gender_detected.get('symptoms', [])
                    reason = gender_detected.get('reason', '')
                                
                    # 既存の性別を確認
                    current_gender = user_attributes.get('gender')
                                
                    if detected_gender == 'female':
                        if not current_gender or current_gender != '女性':
                            # 性別が未登録または女性以外の場合、自動登録
                            user_attributes['gender'] = '女性'
                            gender_auto_registered = True
                            gender_notification_message = f"💡 {reason}。性別を女性として登録しました。"
                            logger.info(f"👤 性別自動登録: {reason}")
                                        
                            # セッションに保存
                            session['user_attributes'] = user_attributes
                            session.modified = True
                                        
                            # DBも更新
                            sid = session.get('_id')
                            if sid:
                                session_data = get_session_from_db(sid)
                                if session_data:
                                    session_data['user_attributes'] = user_attributes
                                    session_data['last_activity'] = datetime.now()
                                    save_session_to_db(sid, session_data)
                        elif current_gender == '男性':
                            # 既存の性別が「男性」の場合は警告のみ
                            warning = gender_detected.get('warning', '')
                            if warning:
                                gender_notification_message = f"⚠️ {warning}"
                                logger.warning(f"👤 性別自動判定の警告: {warning}")
                            
                # 性別が自動登録された場合、または既に「女性」として登録されている場合、妊娠可能性検出を再計算
                current_gender = user_attributes.get('gender')
                is_female = (gender_auto_registered or current_gender == '女性')
                            
                if is_female and pregnancy_possible.get('detected', False):
                    # 性別が「女性」として登録されているので、妊娠可能性検出を再計算
                    # 妊娠可能性検出を再計算（閾値2.0で再判定）
                    pregnancy_score = pregnancy_possible.get('score', 0.0)
                    pregnancy_detected_symptoms = pregnancy_possible.get('symptoms', [])
                                
                    if pregnancy_score >= 2.0:
                        # 閾値を超えている場合、高信頼度として再設定
                        pregnancy_possible = {
                            "detected": True,
                            "score": pregnancy_score,
                            "symptoms": pregnancy_detected_symptoms,
                            "confidence": "high",  # 女性の場合は高信頼度
                            "gender": "female"
                        }
                        if gender_auto_registered:
                            logger.info(f"🤰 妊娠可能性検出を再計算: 性別が女性として登録されたため、高信頼度として再設定（score={pregnancy_score:.2f}）")
                        else:
                            logger.info(f"🤰 妊娠可能性検出を再計算: 性別が既に女性として登録されているため、高信頼度として再設定（score={pregnancy_score:.2f}）")
                    elif pregnancy_score > 0.0:
                        # スコアが0より大きいが閾値未満の場合でも、女性の場合は高信頼度として設定
                        pregnancy_possible = {
                            "detected": True,
                            "score": pregnancy_score,
                            "symptoms": pregnancy_detected_symptoms,
                            "confidence": "high",  # 女性の場合は高信頼度（閾値2.0未満でも検出）
                            "gender": "female"
                        }
                        if gender_auto_registered:
                            logger.info(f"🤰 妊娠可能性検出を再計算: 性別が女性として登録されたため、高信頼度として再設定（score={pregnancy_score:.2f}）")
                        else:
                            logger.info(f"🤰 妊娠可能性検出を再計算: 性別が既に女性として登録されているため、高信頼度として再設定（score={pregnancy_score:.2f}）")
                            
                # 妊娠の可能性が検出された場合の処理
                pregnancy_message = None
                if pregnancy_possible.get('detected', False):
                    confidence = pregnancy_possible.get('confidence')
                    score = pregnancy_possible.get('score', 0.0)
                    detected_symptoms = pregnancy_possible.get('symptoms', [])
                    gender = pregnancy_possible.get('gender', 'unknown')
                                
                    logger.info(f"🤰 妊娠の可能性検出: confidence={confidence}, score={score:.2f}, symptoms={detected_symptoms}, gender={gender}")
                                
                    # 性別に応じた処理
                    if confidence == 'high':  # 女性の場合
                        user_attributes['pregnancy_possible'] = 'high'
                        user_info['pregnancy_possible'] = 'high'  # user_infoにも設定
                        pregnancy_message = "⚠️ 妊娠の可能性があります。医師の診断を受けてください。市販薬の使用は医師にご相談ください。"
                        logger.info(f"📋 妊娠の可能性（高信頼度）を設定: pregnancy_possible=high")
                    elif confidence == 'low':  # 性別不明の場合
                        user_attributes['pregnancy_possible'] = 'low'
                        user_info['pregnancy_possible'] = 'low'  # user_infoにも設定
                        pregnancy_message = "⚠️ 一部の症状は妊娠の可能性を示す場合がありますが、性別情報がないため確定できません。医師にご相談ください。"
                        logger.info(f"📋 妊娠の可能性（低信頼度）を設定: pregnancy_possible=low")
                            
                # ルールベース結果を従来の形式に変換
                if recommendation_result.get('status') == 'success':
                    # API呼び出し回数を記録
                    monitor.increment_api_calls()
                                
                    recommended_medicines = recommendation_result.get('recommended_medicines', [])
                                
                    # 使用上の注意をChatGPTで自動生成（最適化版）
                    mark_processing_step(sid, "usage_notes")
                    usage_notes = recommendation_result.get('usage_notes', '')
                    if not usage_notes or usage_notes == '添付文書をよく読んでご使用ください。':
                        # 推奨された医薬品の使用上の注意を一括生成
                        try:
                            from src.core.medicine_logic import generate_usage_notes
                                        
                            # 上位3つの医薬品の使用上の注意を並列処理で生成
                            generated_notes = []
                            for medicine in recommended_medicines[:3]:  # 上位3つのみ
                                try:
                                    # CSVデータから追加情報を取得
                                    medicine_with_details = medicine.copy()
                                    # 年齢制限とドーピング情報を追加
                                    if 'age_restriction' not in medicine_with_details:
                                        medicine_with_details['age_restriction'] = medicine.get('age_restriction', '情報なし')
                                    if 'doping_prohibited' not in medicine_with_details:
                                        medicine_with_details['doping_prohibited'] = medicine.get('doping_prohibited', 'なし')
                                    if 'competition_category' not in medicine_with_details:
                                        medicine_with_details['competition_category'] = medicine.get('competition_category', '情報なし')
                                    if 'conditions' not in medicine_with_details:
                                        medicine_with_details['conditions'] = medicine.get('conditions', '情報なし')
                                                
                                    # 症状情報を取得（nlu_resultから）
                                    symptoms_list = []
                                    if nlu_result and 'symptoms' in nlu_result:
                                        symptoms_list = nlu_result.get('symptoms', [])
                                                
                                    # 使用上の注意を生成（キャッシュ機能付き）
                                    medicine_notes = generate_usage_notes(
                                        medicine.get('name', ''),
                                        medicine_with_details,
                                        user_info,
                                        symptoms=symptoms_list
                                    )
                                    if medicine_notes and medicine_notes != "使用上の注意の生成に失敗しました。薬剤師または登録販売者にご相談ください。":
                                        generated_notes.append(f"<strong>{medicine.get('name', '')}:</strong><br>{medicine_notes}")
                                except Exception as e:
                                    logger.warning(f"使用上の注意生成エラー: {e}")
                                    continue
                                        
                            if generated_notes:
                                usage_notes = '<br><br>'.join(generated_notes)
                            else:
                                usage_notes = '添付文書をよく読んでご使用ください。'
                                            
                        except Exception as e:
                            logger.warning(f"使用上の注意一括生成エラー: {e}")
                            usage_notes = '添付文書をよく読んでご使用ください。'
                                
                    doctor_consultation = recommendation_result.get('doctor_consultation', '症状が改善しない場合は医師にご相談ください。')
                                
                    # 症状の重症度による受診勧奨チェック
                    try:
                        from src.core.medicine_logic import detect_severity_escalation, generate_doctor_referral_message
                                    
                        escalation_info = detect_severity_escalation(sanitized_message, nlu_result, user_info)
                        if escalation_info.get("needs_escalation", False):
                            referral_message = generate_doctor_referral_message(escalation_info)
                            if referral_message:
                                # 緊急度に応じて表示位置を決定
                                urgency = escalation_info.get("urgency", "medium")
                                if urgency == "high":
                                    # 緊急度が高い場合は推奨リストの前に表示
                                    recommendation_result['severity_escalation'] = referral_message
                                    recommendation_result['severity_escalation_priority'] = 'before_recommendations'
                                else:
                                    # 緊急度が低い場合は推奨リストの後に表示
                                    recommendation_result['severity_escalation'] = referral_message
                                    recommendation_result['severity_escalation_priority'] = 'after_recommendations'
                    except Exception as e:
                        logger.warning(f"受診勧奨チェックでエラー: {e}")
                                
                    # メッセージの順序: 性別自動登録の通知 → 妊娠可能性の警告 → その他の医師相談メッセージ
                    consultation_messages = []
                                
                    # 性別自動登録の通知メッセージを追加（最初に表示）
                    if gender_notification_message:
                        consultation_messages.append(gender_notification_message)
                                
                    # 妊娠の可能性が検出された場合、メッセージを追加
                    if pregnancy_message:
                        consultation_messages.append(pregnancy_message)
                                
                    # その他の医師相談メッセージを追加
                    if doctor_consultation:
                        consultation_messages.append(doctor_consultation)
                                
                    # メッセージを結合
                    if consultation_messages:
                        doctor_consultation = '\n\n'.join(consultation_messages)
                                
                    additional_questions = recommendation_result.get('additional_questions', [])
                    critical_questions = recommendation_result.get('critical_questions', [])
                    influenza_risk = recommendation_result.get('influenza_risk', False)
                    influenza_reason = recommendation_result.get('influenza_reason', '')
                                
                    recommendation_result = {
                        'symptoms': symptoms,
                        'medicine_type': medicine_type,
                        'recommended_medicines': recommended_medicines,
                        'usage_notes': usage_notes,
                        'doctor_consultation': doctor_consultation,
                        'additional_questions': additional_questions,
                        'critical_questions': critical_questions,  # 新規追加
                        'influenza_risk': influenza_risk,  # 新規追加
                        'influenza_reason': influenza_reason,  # 新規追加
                        'algorithm': 'rule_based'
                    }
                elif recommendation_result.get('status') == 'escalation_required':
                    # エスカレーションが必要な場合
                    monitor.increment_error()
                    recommendation_result = {
                        'symptoms': symptoms,
                        'medicine_type': medicine_type,
                        'recommended_medicines': [],
                        'usage_notes': '',
                        'doctor_consultation': recommendation_result.get('reason', ''),
                        'escalation': True,
                        'algorithm': 'rule_based'
                    }
                elif recommendation_result.get('status') == 'no_candidates':
                    # 候補医薬品が見つからない場合 - エラーメッセージを表示
                    monitor.increment_error()
                    confidence_score = recommendation_result.get('confidence_score', 0.0)
                    logger.warning(f"⚠️ Rule-based algorithm: no candidates found (confidence: {confidence_score:.2f})")
                    # エラー情報を保持して後続のエラー表示処理で使用
                    recommendation_result['error'] = True
                    recommendation_result['error_type'] = 'no_candidates'
                    recommendation_result['error_details'] = {
                        'confidence_score': confidence_score,
                        'reason': recommendation_result.get('reason', '該当する医薬品が見つかりませんでした'),
                        'technical_details': f"信頼度スコア: {confidence_score:.2f}, 症状: {symptoms}, 医薬品の種類: {medicine_type}"
                    }
                elif recommendation_result.get('status') == 'error':
                    # ルールベース推奨エラー - エラーメッセージを表示
                    monitor.increment_error()
                    logger.warning(f"⚠️ Rule-based algorithm error: {recommendation_result.get('reason', 'unknown error')}")
                    recommendation_result['error'] = True
                    recommendation_result['error_type'] = 'rule_based_error'
                    recommendation_result['error_details'] = {
                        'reason': recommendation_result.get('reason', 'ルールベース推奨でエラーが発生しました'),
                        'error_message': recommendation_result.get('error_message', ''),
                        'technical_details': f"ステータス: error, 症状: {symptoms}, 医薬品の種類: {medicine_type}"
                    }
                elif recommendation_result.get('status') == 'missing_critical_info':
                    # 必須情報不足 - エラーメッセージを表示
                    monitor.increment_error()
                    logger.warning(f"⚠️ Rule-based algorithm: missing critical information")
                    recommendation_result['error'] = True
                    recommendation_result['error_type'] = 'missing_critical_info'
                    recommendation_result['error_details'] = {
                        'reason': recommendation_result.get('reason', '症状が検出されていません'),
                        'missing_fields': recommendation_result.get('missing_fields', []),
                        'technical_details': f"ステータス: missing_critical_info, 症状: {symptoms}, 医薬品の種類: {medicine_type}"
                    }
                else:
                    # その他のエラーの場合 - エラーメッセージを表示
                    monitor.increment_error()
                    status = recommendation_result.get('status', 'unknown')
                    logger.warning(f"⚠️ Rule-based algorithm failed (status: {status})")
                    recommendation_result['error'] = True
                    recommendation_result['error_type'] = 'unknown_error'
                    recommendation_result['error_details'] = {
                        'reason': recommendation_result.get('reason', f'ルールベース推奨でエラーが発生しました（ステータス: {status}）'),
                        'status': status,
                        'technical_details': f"ステータス: {status}, 症状: {symptoms}, 医薬品の種類: {medicine_type}"
                    }
            else:
                from config.llm_flags import is_gpt_recommend_fallback_enabled
                from src.services.budget_guard import get_admin_message

                if is_gpt_recommend_fallback_enabled():
                    from src.core.medicine_logic import comprehensive_medicine_recommendation

                    logger.info(f"✅ Using ChatGPT-BASED algorithm for {medicine_type}")
                    user_attributes = session.get('user_attributes', {
                        'age': None,
                        'gender': None,
                        'pregnant': None,
                        'breastfeeding': None,
                        'current_medications': [],
                        'allergies': [],
                        'medical_history': [],
                        'symptom_duration_days': None,
                        'other_info': None
                    })
                    recommendation_result = comprehensive_medicine_recommendation(user_message)
                    recommendation_result['algorithm'] = 'chatgpt'
                    monitor.increment_api_calls()
                else:
                    logger.info(
                        "⚠️ Unsupported medicine_type for rule_based (%s) — escalation (GPT fallback OFF)",
                        medicine_type,
                    )
                    esc_msg = get_admin_message("unsupported_medicine_type") or (
                        "お近くの医療機関や薬剤師にご相談ください。"
                        "当てはまる市販薬の自動提案ができない内容のため、"
                        "症状の詳細をお知らせいただくか、店頭でご相談ください。"
                    )
                    recommendation_result = {
                        'symptoms': symptoms,
                        'medicine_type': medicine_type,
                        'recommended_medicines': [],
                        'usage_notes': '',
                        'doctor_consultation': esc_msg,
                        'escalation': True,
                        'algorithm': 'rule_based_escalation',
                        'status': 'escalation_required',
                        'reason': esc_msg,
                    }
                            
                # ChatGPTベースでも個別の医薬品の使用上の注意を表示
                recommended_medicines = recommendation_result.get('recommended_medicines', [])
                if recommended_medicines:
                    # 個別の医薬品の使用上の注意を収集
                    individual_notes = []
                    for medicine in recommended_medicines:
                        if medicine.get('usage_notes') and medicine.get('usage_notes') != '添付文書をよく読んでご使用ください。':
                            individual_notes.append(f"<strong>{medicine.get('product_name', '')}:</strong><br>{medicine.get('usage_notes', '')}")
                                
                    if individual_notes:
                        # 個別の使用上の注意がある場合はそれを使用
                        recommendation_result['usage_notes'] = '<br><br>'.join(individual_notes)
                    elif not recommendation_result.get('usage_notes'):
                        # 個別の使用上の注意がない場合のみ簡易的なものを設定
                        recommendation_result['usage_notes'] = '添付文書をよく読んでご使用ください。妊娠中・授乳中の方、アレルギー体質の方は医師にご相談ください。'
                        
            end_time = time.time()
            response_time = round(end_time - start_time, 3)
                        
            # 属性情報の不足チェック
            user_attributes = session.get('user_attributes', {})
            missing_questions, missing_priority = check_missing_attributes(user_attributes)
                        
            if missing_questions:
                recommendation_result['additional_questions'] = missing_questions
                recommendation_result['missing_priority'] = missing_priority
                logger.info(f"❓ Missing attributes detected: {len(missing_questions)} questions, priority: {missing_priority}")
                        
            # 女性が登録された場合の妊娠可能性通知
            if user_attributes.get('pregnancy_notification', False):
                notification_message = "💡 女性として登録されました。妊娠の可能性がある場合は、医師の診断を受けてください。市販薬の使用は医師にご相談ください。"
                current_consultation = recommendation_result.get('doctor_consultation', '')
                if current_consultation:
                    recommendation_result['doctor_consultation'] = notification_message + '\n\n' + current_consultation
                else:
                    recommendation_result['doctor_consultation'] = notification_message
                # フラグをリセット（一度だけ表示）
                user_attributes['pregnancy_notification'] = False
                session['user_attributes'] = user_attributes
                session.modified = True
                logger.info(f"📋 女性登録時の妊娠可能性通知メッセージを表示")
                        
            # medicine_logic.pyの呼び出しをログ出力
            log_medicine_logic_call(
                f"hybrid_recommendation ({recommendation_result.get('algorithm', 'unknown')})",
                {"user_message": processed_message},  # 方言変換後のテキストをログに表示
                {
                    "symptoms": recommendation_result.get('symptoms', []),
                    "medicine_type": recommendation_result.get('medicine_type', medicine_type),
                    "recommended_medicines_count": len(recommendation_result.get('recommended_medicines', [])),
                    "algorithm": recommendation_result.get('algorithm', 'unknown')
                },
                response_time
            )
                        
            # ネットワークリクエストをログ出力
            log_network_request(
                'POST',
                f'メインサイト - ハイブリッド医薬品推奨 ({recommendation_result.get("algorithm", "unknown")})',
                {'symptom': user_message},
                {'recommendation': recommendation_result},
                response_time,
                'success'
            )
                        
            add_network_log(
                'POST',
                f'メインサイト - ハイブリッド医薬品推奨 ({recommendation_result.get("algorithm", "unknown")})',
                {'symptom': user_message},
                {'recommendation': recommendation_result},
                response_time,
                'success'
            )
                        
            # 推奨結果を整形して表示
            symptoms = recommendation_result.get('symptoms', [])
            medicine_type = recommendation_result.get('medicine_type', '')
            recommended_medicines = recommendation_result.get('recommended_medicines', [])
            usage_notes = recommendation_result.get('usage_notes', '')
            doctor_consultation = recommendation_result.get('doctor_consultation', '')
                        
            # ルールベース推奨失敗時のエラー表示処理
            if recommendation_result.get('error'):
                error_type = recommendation_result.get('error_type', 'unknown')
                error_details = recommendation_result.get('error_details', {})
                bot_content = format_error_display(
                    error_type=error_type,
                    error_details=error_details,
                    user_message=user_message,
                    include_feedback_buttons=True,
                )
            # エスカレーションが必要な場合の特別処理
            elif recommendation_result.get('escalation'):
                bot_content = format_escalation_display(
                    doctor_consultation=doctor_consultation,
                    medicine_type=medicine_type,
                    algorithm=recommendation_result.get('algorithm', 'unknown'),
                    user_message=user_message,
                    include_feedback_buttons=True,
                )
            else:
                # 通常の推奨結果の表示
                algorithm_label = {
                    'rule_based': 'ルールベースアルゴリズム（安全性重視）',
                    'chatgpt': 'ChatGPTベースアルゴリズム',
                    'chatgpt_fallback': 'ChatGPTベースアルゴリズム（フォールバック）'
                }.get(recommendation_result.get('algorithm', 'unknown'), '不明')
                            
                # SSE: 薬カード選定完了を先に通知（アドバイスは続けてストリーム）
                if recommended_medicines and sid:
                    try:
                        from src.services.sse_emit import emit_cards

                        emit_cards(recommended_medicines, session_id=sid)
                        _emit_explanation_followup_sse(
                            session,
                            sid,
                            recommended_medicines,
                            recommendation_result,
                            recommendation_client,
                        )
                    except Exception:
                        pass

                # 全ての推奨結果に対してアドバイスを生成（再分析時だけでなく常時）
                personalized_section = ""
                try:
                    # ユーザー属性を取得
                    user_attrs = session.get('user_attributes', {})
                                
                    # 再分析時はreanalysis_attributesを使用
                    if session.get('is_reanalysis'):
                        user_attrs = session.get('reanalysis_attributes', user_attrs)
                        session.pop('is_reanalysis', None)
                        session.pop('reanalysis_attributes', None)
                                
                    # インフルエンザリスク情報を追加
                    influenza_risk = recommendation_result.get('influenza_risk', False)
                    influenza_reason = recommendation_result.get('influenza_reason', '')
                                
                    personalized_advice = generate_personalized_advice(
                        user_attrs,
                        recommended_medicines,
                        symptoms,
                        recommendation_client,
                        user_text=user_message,
                        influenza_risk=influenza_risk,
                        influenza_reason=influenza_reason,
                        session_id=sid,
                    )
                                
                    personalized_section = f"""
    <div class="warning-info" role="region" aria-label="あなたに合わせたアドバイス" style="padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #2196f3;">
        <h4 style="color: #1976d2; margin-top: 0;">💡 あなたに合わせたアドバイス</h4>
        <p style="margin: 5px 0; line-height: 1.6; white-space: pre-wrap;">{personalized_advice}</p>
    </div>
    """
                except Exception as e:
                    logger.error(f"❌ 個別説明生成エラー: {e}")
                    # エラー時はインフルエンザリスク情報のみ表示
                    influenza_risk = recommendation_result.get('influenza_risk', False)
                    influenza_reason = recommendation_result.get('influenza_reason', '')
                    if influenza_risk:
                        personalized_section = f"""
    <div style="background: #fff3e0; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #ff9800;">
        <h4 style="color: #f57c00; margin-top: 0;">⚠️ インフルエンザの可能性について</h4>
        <p style="margin: 5px 0; line-height: 1.6;">{influenza_reason}。インフルエンザの可能性がある場合は、アスピリンを含む医薬品の使用を避け、早めに医療機関を受診することをお勧めします。</p>
    </div>
    """
                            
                # critical_questionsとadditional_questionsを統合して推奨前に表示
                critical_questions = recommendation_result.get('critical_questions', [])
                additional_questions = recommendation_result.get('additional_questions', [])
                missing_priority = recommendation_result.get('missing_priority')
                            
                # すべての質問を統合（critical_questionsを先に）
                all_questions_before = []
                if critical_questions:
                    all_questions_before.extend(critical_questions)
                if additional_questions:
                    for q in additional_questions:
                        if q not in all_questions_before:
                            all_questions_before.append(q)
                            
                # 推奨前の質問セクション（すべての質問を統合して表示）
                questions_section_before = ""
                if all_questions_before:
                    priority_label = {
                        'critical': '必須',
                        'important': '重要',
                        'optional': '任意'
                    }.get(missing_priority, '重要' if critical_questions else '任意')
                                
                    priority_message = {
                        'critical': 'より適切な医薬品をご提案するため、以下の情報を教えてください：',
                        'important': '安全のため、以下の情報を教えてください：',
                        'optional': 'より安全な使用のため、可能であれば以下の情報を教えてください：'
                    }.get(missing_priority, 'より適切な医薬品をご提案するため、以下の情報を教えてください：')
                                
                    # critical_questionsがある場合はcriticalスタイル、そうでない場合はimportantスタイル
                    if critical_questions:
                        question_bg = '#ffebee'
                        question_border = '#f44336'
                        question_title = '#c62828'
                        if missing_priority != 'critical':
                            missing_priority = 'critical'
                            priority_label = '必須'
                            priority_message = 'より適切な医薬品をご提案するため、以下の情報を教えてください：'
                    elif missing_priority == 'critical':
                        question_bg = '#ffebee'
                        question_border = '#f44336'
                        question_title = '#c62828'
                    elif missing_priority == 'important':
                        question_bg = '#fff3e0'
                        question_border = '#ff9800'
                        question_title = '#f57c00'
                    else:
                        question_bg = '#e8f5e9'
                        question_border = '#4caf50'
                        question_title = '#388e3c'
                                
                    questions_section_before = f"""
    <div style="background: {question_bg}; padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid {question_border};">
        <h4 style="color: {question_title}; margin-top: 0;">❓ 追加でお伺いしたいこと <span style="font-size: 0.9em;">（優先度: {priority_label}）</span></h4>
        <p style="margin: 10px 0;">{priority_message}</p>
        <ul style="margin: 10px 0; padding-left: 20px;">
    """
                    for question in all_questions_before:
                        questions_section_before += f"            <li style='margin: 5px 0;'>{question}</li>\n"
                    questions_section_before += """
        </ul>
        <button onclick="openAttributeModal()" class="answer-questions-btn">📝 回答する</button>
    </div>
    """
                            
                # 属性更新による再推奨の場合、確認メッセージを追加
                attribute_update_message = ""
                if session.get('is_reanalysis_with_updated_attributes'):
                    user_attrs = session.get('user_attributes', {})
                    attribute_info = []
                    if user_attrs.get('age'):
                        attribute_info.append(f"年齢: {user_attrs['age']}歳")
                    if user_attrs.get('gender'):
                        attribute_info.append(f"性別: {user_attrs['gender']}")
                    if user_attrs.get('allergies'):
                        allergies_str = ', '.join(user_attrs['allergies']) if user_attrs['allergies'] else 'なし'
                        attribute_info.append(f"アレルギー: {allergies_str}")
                    if user_attrs.get('current_medications'):
                        meds_str = ', '.join(user_attrs['current_medications']) if user_attrs['current_medications'] else 'なし'
                        attribute_info.append(f"服用中の薬: {meds_str}")
                                
                    attribute_update_message = f"""
    <div style="background: #e1f5fe; padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #0277bd;">
        <h4 style="color: #01579b; margin-top: 0;">✅ 属性情報を更新しました</h4>
        <p style="margin: 5px 0; line-height: 1.6;">{' | '.join(attribute_info) if attribute_info else '属性情報が更新されました'}</p>
        <p style="margin: 5px 0; font-size: 0.9em; color: #666;">更新された情報をもとに、より適切な医薬品を再推奨いたします。</p>
    </div>
    """
                    # アレルギー警告を追加
                    if user_attrs.get('allergies') and user_attrs['allergies'] != ['なし']:
                        allergies_list = [a for a in user_attrs['allergies'] if a != 'なし']
                        if allergies_list:
                            attribute_update_message += f"""
    <div style="background: #fff3e0; padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #ff9800;">
        <h4 style="color: #e65100; margin-top: 0;">⚠️ アレルギー情報について</h4>
        <p style="margin: 5px 0; line-height: 1.6;">アレルギー: <strong>{', '.join(allergies_list)}</strong></p>
        <p style="margin: 5px 0; font-size: 0.9em; color: #666;">アレルギーについて不明な点がある場合はお近くの薬剤師にご相談ください。</p>
    </div>
    """
                    session.pop('is_reanalysis_with_updated_attributes', None)
                            
                # 治療中警告メッセージの生成
                treatment_warning_section = ""
                treatment_mention = user_info.get('treatment_mention', False)
                if treatment_mention:
                    treatment_warning_section = """
    <div class="collapsible-section" data-collapsible="true" data-default-expanded="true" role="region" aria-label="治療中の方へ" style="background: #fff3e0; border-left: 4px solid #f57c00;">
        <button class="collapse-toggle" aria-expanded="true" aria-controls="treatment-warning-content" aria-label="閉じる">
    <span class="collapse-icon">▼</span>
    <h4 style="color: #e65100; margin-top: 0; display: inline;">⚠️ <strong>治療中の方へ</strong></h4>
        </button>
        <div id="treatment-warning-content" style="padding: 15px;">
        <p style="margin: 5px 0; line-height: 1.6;">現在治療中の疾患がある場合、市販薬の服用前に必ず主治医や薬剤師にご相談ください。</p>
        <p style="margin: 5px 0; line-height: 1.6;">治療中の方が市販薬を服用する場合、主疾患への重大な影響を与える可能性があります。</p>
        </div>
    </div>
    """
                            
                # 曖昧な入力への注意書き（治療中警告の前に配置）
                ambiguous_warning_section = ""
                try:
                    # nlu_resultをrecommendation_resultから取得を試みる
                    nlu_result_for_ambiguous = recommendation_result.get('nlu_result', {})
                    # symptomsは文字列のリストとして扱う
                    symptoms_list = [s if isinstance(s, str) else s.get('name', '') if isinstance(s, dict) else str(s) for s in symptoms] if symptoms else []
                    if is_ambiguous_input(user_message, symptoms_list, nlu_result_for_ambiguous):
                        ambiguous_warning_section = """
    <div class="collapsible-section" data-collapsible="true" data-default-expanded="false" role="region" aria-label="ご入力について" style="background: #e3f2fd; border-left: 4px solid #2196f3;">
        <button class="collapse-toggle" aria-expanded="false" aria-controls="ambiguous-warning-content" aria-label="詳細を見る">
    <span class="collapse-icon">▼</span>
    <h4 style="color: #1976d2; margin-top: 0; display: inline;">ℹ️ ご入力について</h4>
        </button>
        <div class="collapse-content" id="ambiguous-warning-content" style="padding: 20px; margin: 15px 0;">
        <p style="margin: 5px 0; line-height: 1.6;">ご入力いただいた内容から、複数の症状が推定されました。より正確な推奨のため、具体的な症状（発熱、咳、鼻水など）を詳しく教えていただくと、より適切な医薬品をご提案できます。</p>
        </div>
    </div>
    """
                except Exception as e:
                    logger.warning(f"曖昧さ判定エラー: {e}")
                            
                # 症状分析結果を折りたたみ可能にする
                symptom_analysis_section = f"""
    <div class="collapsible-section" data-collapsible="true" data-default-expanded="false" role="region" aria-label="症状分析結果">
        <button class="collapse-toggle" aria-expanded="false" aria-controls="symptom-analysis-content" aria-label="詳細を見る">
    <span class="collapse-icon">▼</span>
    <h4 style="color: #1976d2; border-bottom: 2px solid #1976d2; padding-bottom: 8px; display: inline;">🔍 症状分析結果</h4>
        </button>
        <div class="collapse-content" id="symptom-analysis-content">
    <p><strong>推測される症状:</strong> {', '.join(symptoms) if symptoms else '特定できませんでした'}</p>
    <p><strong>医薬品の種類:</strong> {medicine_type}</p>
        </div>
    </div>
    """
                            
                bot_content = f"""
    <div class="recommendation-result">
    {attribute_update_message}
    {ambiguous_warning_section}
    {treatment_warning_section}
    {personalized_section}
    {symptom_analysis_section}
        
    <div style="background: #e8f5e9; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #4caf50;">
        <h4 style="color: #2e7d32; margin-top: 0;">💊 推奨医薬品</h4>
    """
                            
                # 成分重複チェック
                overlap_warning_section = ""
                if recommended_medicines:
                    try:
                        from src.core.rule_based_recommendation import check_ingredient_overlap
                        overlap_result = check_ingredient_overlap(recommended_medicines)
                        if overlap_result.get("has_overlap"):
                            # コンパクトな形式で警告メッセージを生成（1-2行で簡潔に）
                            overlap_summaries = []
                            for overlap in overlap_result.get("overlapping_ingredients", []):
                                medicines_list = "、".join(overlap.get("medicines", []))
                                summary = f"{overlap.get('warning_message', '')}：{medicines_list}{overlap.get('side_effect_message', '')}"
                                overlap_summaries.append(summary)
                                        
                            # 複数の重複がある場合は最初の1-2件のみ表示（コンパクトに）
                            display_summaries = overlap_summaries[:2]  # 最大2件まで表示
                            if len(overlap_summaries) > 2:
                                display_summaries.append(f"他{len(overlap_summaries) - 2}件の重複あり")
                                        
                            # 深刻度に応じたスタイルを決定
                            highest_severity = overlap_result.get("highest_severity", "blue")
                            severity_styles = {
                                "red": {
                                    "icon": "🚨",
                                    "title": "成分の重複について（重複禁止）",
                                    "border_color": "#d32f2f",
                                    "title_color": "#c62828",
                                    "background": "white"
                                },
                                "yellow": {
                                    "icon": "⚠️",
                                    "title": "成分の重複について（注意）",
                                    "border_color": "#f57c00",
                                    "title_color": "#e65100",
                                    "background": "white"
                                },
                                "blue": {
                                    "icon": "ℹ️",
                                    "title": "成分の重複について（情報）",
                                    "border_color": "#1976d2",
                                    "title_color": "#1976d2",
                                    "background": "white"
                                }
                            }
                            style = severity_styles.get(highest_severity, severity_styles["blue"])
                                        
                            # 警告のクラスを決定（深刻度に応じて）
                            warning_class = 'warning-critical' if highest_severity == 'red' else 'warning-caution' if highest_severity == 'yellow' else 'warning-info'
                                        
                            overlap_warning_section = f"""
    <div class="{warning_class}" role="region" aria-label="{style['title']}" style="background: {style['background']}; padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid {style['border_color']};">
        <h4 style="color: {style['title_color']}; margin-top: 0;">{style['icon']} {style['title']}</h4>
        <ul style="margin: 10px 0; padding-left: 20px;">
    {''.join(f'<li style="margin: 3px 0;">{summary}</li>' for summary in display_summaries)}
        </ul>
    </div>
    """
                            bot_content += overlap_warning_section
                    except Exception as e:
                        # 成分重複チェックでエラーが発生した場合は警告を表示せず、処理を続行
                        logger.warning(f"成分重複チェックエラー: {e}")
                            
                if recommended_medicines:
                    for medicine in recommended_medicines:
                        # ルールベース結果の場合
                        if 'rank' in medicine:
                            explanation = medicine.get('explanation', '')
                            score = medicine.get('score', 0)
                                        
                            # 年齢制限の取得と表示
                            age_restriction = medicine.get('age_restriction', '')
                            age_restriction_display = ''
                                        
                            import math
                            if isinstance(age_restriction, float) and math.isnan(age_restriction):
                                age_restriction = ''
                                        
                            # 年齢制限から数値のみを抽出（「15歳以上」→「15」）
                            if age_restriction and isinstance(age_restriction, str):
                                # 数値のみを抽出（例：「15歳以上」→「15」）
                                age_match = re.search(r'(\d+)歳', age_restriction)
                                if age_match:
                                    age_num = age_match.group(1)
                                    age_restriction = f"{age_num}歳以上"
                                        
                            if age_restriction and isinstance(age_restriction, str) and age_restriction.strip():
                                if '15歳未満' in age_restriction:
                                    age_restriction_display = '<p><strong>年齢制限:</strong> <span style="color: #d32f2f;">15歳以上の方が対象です。</span></p>'
                                elif '7歳未満' in age_restriction:
                                    age_restriction_display = '<p><strong>年齢制限:</strong> <span style="color: #d32f2f;">7歳以上の方が対象です。</span></p>'
                                elif '12歳未満' in age_restriction:
                                    age_restriction_display = '<p><strong>年齢制限:</strong> <span style="color: #d32f2f;">12歳以上の方が対象です。</span></p>'
                                else:
                                    # その他の年齢制限がある場合
                                    match = re.search(r'(\d+)歳', age_restriction)
                                    if match:
                                        age_restriction_display = f'<p><strong>年齢制限:</strong> {age_restriction}</p>'
                            elif isinstance(age_restriction, (int, float)):
                                try:
                                    age_val = int(age_restriction)
                                    age_restriction_display = f'<p><strong>年齢制限:</strong> {age_val}歳以上の方が対象です。</p>'
                                except (ValueError, OverflowError):
                                    pass
                                        
                            rank = medicine.get('rank', 1)
                            medicine_type = medicine.get('medicine_type', '')
                                        
                            # 外用薬（のど）の補助療法説明
                            # 実際に外用薬（スプレー、トローチなど）の場合のみ表示
                            auxiliary_note = ""
                            if '外用薬（のど）' in medicine_type:
                                product_name_lower = medicine.get('product_name', '').lower()
                                # 実際に外用薬（スプレー、トローチ、うがい薬など）であることを確認
                                is_external_medicine = any(kw in product_name_lower for kw in ['スプレー', 'トローチ', 'うがい', '含嗽', '噴射', '塗布'])
                                # 漢方薬（湯、散、丸など）の場合は除外
                                is_kampo = any(kw in product_name_lower for kw in ['湯', '散', '丸', 'エキス'])
                                if is_external_medicine and not is_kampo:
                                    auxiliary_note = """
        <p style="margin: 5px 0; padding: 8px; background: #f0f7ff; border-left: 3px solid #2196f3; font-size: 0.9em; color: #1976d2;">
    💡 <strong>補助的な使用について</strong><br>
    この外用薬は、内服薬と併用して喉を直接ケアする補助的な製品です。飲み薬にプラスして使うことで、喉の痛みをより和らげることができます。
        </p>
    """
                                        
                            # スコア表示の生成（display_scoreを優先、整数表示）
                            score_display = ""
                            display_score = medicine.get('display_score')
                            score_level = medicine.get('score_level', '中')
                            completeness_penalty = medicine.get('completeness_penalty', 0.0)
                                        
                            if display_score is not None:
                                # display_scoreを小数点以下1桁表示（例：85.5%）
                                score_percent = round(display_score, 1)
                                score_display = f'<p style="margin: 5px 0;"><strong>📊 最適度:</strong> {score_percent}% <span style="color: #666;">({score_level})</span></p>'
                                            
                                # 不足情報による減点がある場合、メッセージを表示
                                if completeness_penalty > 0:
                                    penalty_percent = round(completeness_penalty * 100, 1)
                                    score_display += f'<p style="margin: 5px 0; color: #f57c00; font-size: 0.9em;"><strong>ℹ️ 情報:</strong> 年齢などの情報が入力されると、より正確な判定が可能です（不足情報により{penalty_percent}%低下中）</p>'
                            elif medicine.get('relative_score') is not None:
                                # display_scoreがない場合はrelative_scoreを使用（フォールバック）
                                relative_score = medicine.get('relative_score')
                                score_percent = int(round(relative_score * 100))
                                score_display = f'<p style="margin: 5px 0;"><strong>📊 最適度:</strong> {score_percent}% <span style="color: #666;">({score_level})</span></p>'
                            elif medicine.get('score') is not None:
                                # 相対スコアがない場合は絶対スコアを表示（フォールバック）
                                score_percent = int(round(medicine.get('score', 0) * 100))
                                score_display = f'<p style="margin: 5px 0;"><strong>📊 最適度:</strong> {score_percent}%</p>'
                                        
                            # リスク警告の表示
                            risk_warning_display = ""
                            if medicine.get('risk_warning'):
                                risk_warning_display = f'<p style="margin: 5px 0; color: #d32f2f;"><strong>⚠️ 注意:</strong> {medicine.get("risk_warning")}</p>'
                                        
                            # 低スコア警告の表示
                            low_score_warning_display = ""
                            if medicine.get('low_score_warning'):
                                low_score_warning_display = '<p style="margin: 5px 0; color: #f57c00;"><strong>⚠️ 推奨スコアが低めです。</strong> 使用前に薬剤師または登録販売者にご相談ください。</p>'
                                        
                            bot_content += f"""
        <div class="medicine-item" style="padding: 10px 0; margin: 10px 0; border-bottom: 1px solid #ddd;">
    <h5 style="margin: 0 0 10px 0;">🏆 {rank}つ目: {medicine.get('product_name', '')} <span style="color: #666; font-size: 0.9em;">({medicine.get('manufacturer', '')})</span></h5>
    {score_display}
    <p style="margin: 5px 0;"><strong>推奨理由:</strong> {explanation}</p>
    {auxiliary_note}
    {age_restriction_display}
    {risk_warning_display}
    {low_score_warning_display}
    <p style="margin: 5px 0;"><strong>効能効果:</strong> {medicine.get('efficacy', '')}</p>
        </div>
    """
                        else:
                            # ChatGPTベース結果の場合
                            efficacy = medicine.get('efficacy', '')
                            ingredients = medicine.get('ingredients', '')
                                        
                            if len(efficacy) > 200:
                                efficacy = efficacy[:200] + "..."
                            if len(ingredients) > 200:
                                ingredients = ingredients[:200] + "..."
                                        
                            bot_content += f"""
    <div class="medicine-item">
        <h5>🏆 {medicine.get('number', '')}つ目: {medicine.get('product_name', '')}</h5>
        <p><strong>メーカー:</strong> {medicine.get('manufacturer', '')}</p>
        <p><strong>推奨理由:</strong> {medicine.get('reason', '')}</p>
        <p><strong>効能効果:</strong> {efficacy}</p>
        <p><strong>成分:</strong> {ingredients}</p>
    </div>
    """
                else:
                    bot_content += "        <p>適切な医薬品が見つかりませんでした。</p>"
                            
                # 推奨医薬品セクションを閉じる
                bot_content += """
    </div>
    """
                            
                if usage_notes or doctor_consultation:
                    # 使用上の注意を整形（セクションごとに色分け）
                    formatted_usage_notes = ""
                    if usage_notes:
                        # ChatGPTベースの使用上の注意（HTML形式）をチェック
                        if '<strong>' in usage_notes and '<br>' in usage_notes:
                            # ChatGPTベースの形式（HTML）の場合はそのまま表示
                            formatted_usage_notes = usage_notes
                        else:
                            # ルールベースの形式（テキスト）の場合は従来の処理
                            lines = usage_notes.split('\n')
                            current_section = None
                            current_html = ""
                                        
                            # 年齢制限の重複チェック用
                            age_restriction_added = False
                                        
                            # セクションID用のカウンター
                            section_counter = 0
                                        
                            for line in lines:
                                line = line.strip()
                                if not line:
                                    continue
                                                
                                if line.startswith('1つ目：') or line.startswith('2つ目：') or line.startswith('3つ目：'):
                                    # 前のセクションを閉じる
                                    if current_section == 'individual' and current_html:
                                        # 前の医薬品セクションのコンテンツとセクション自体を閉じる
                                        formatted_usage_notes += current_html + '</div></div>'
                                        current_html = ""
                                    elif current_section and current_html:
                                        # その他のセクション（caution, usage等）を閉じる
                                        formatted_usage_notes += current_html + '</div></div>'
                                        current_html = ""
                                                
                                    # 新しい医薬品セクション開始（折りたたみ可能）
                                    medicine_num = line.replace('：', '').replace('つ目', '')
                                    section_id = f"medicine-{medicine_num}"
                                    formatted_usage_notes += f'<div class="collapsible-section" data-collapsible="true" data-default-expanded="false" role="region" aria-label="{line}" style="background: #f5f5f5; border-left: 4px solid #4CAF50;"><button class="collapse-toggle" aria-expanded="false" aria-controls="{section_id}" aria-label="詳細を見る"><span class="collapse-icon">▼</span><h5 style="margin: 0; display: inline;">💊 {line}</h5></button><div class="collapse-content" id="{section_id}" style="padding: 15px; margin: 10px 0;">'
                                    current_html = ""
                                    current_section = 'individual'
                                    age_restriction_added = False  # 新しい医薬品セクションでリセット
                                elif line.startswith('【使ってはいけない人】'):
                                    # 前のセクションを閉じる
                                    if current_section == 'individual':
                                        # 医薬品セクションのコンテンツとセクション自体を閉じる
                                        if current_html:
                                            formatted_usage_notes += current_html
                                        formatted_usage_notes += '</div></div>'  # collapse-contentとcollapsible-sectionを閉じる
                                        current_html = ""
                                    elif current_section and current_html:
                                        # その他のセクション（caution, usage等）を閉じる
                                        formatted_usage_notes += current_html + '</div></div>'
                                        current_html = ""
                                    # 禁忌セクション（折りたたみ可能）
                                    section_counter += 1
                                    section_id = f"contraindication-section-{section_counter}"
                                    formatted_usage_notes += f'<div class="collapsible-section" data-collapsible="true" data-default-expanded="false" role="region" aria-label="{line}" style="background: #ffebee; border-left: 4px solid #c62828;"><button class="collapse-toggle" aria-expanded="false" aria-controls="{section_id}" aria-label="詳細を見る"><span class="collapse-icon">▼</span><h5 style="color: #d32f2f; margin: 0; display: inline;">⚠️ {line}</h5></button><div class="collapse-content" id="{section_id}" style="padding: 15px; margin: 10px 0;">'
                                    current_html = ""
                                    current_section = 'caution'
                                elif line.startswith('【OTC医薬品について】'):
                                    # 前のセクションを閉じる（医薬品セクションも含む）
                                    if current_section == 'individual':
                                        # 医薬品セクションのコンテンツとセクション自体を閉じる
                                        if current_html:
                                            formatted_usage_notes += current_html
                                        formatted_usage_notes += '</div></div>'
                                        current_html = ""
                                    elif current_section and current_html:
                                        if current_section in ['caution', 'usage']:
                                            formatted_usage_notes += current_html + '</div></div>'
                                        else:
                                            formatted_usage_notes += current_html + '</div>'
                                        current_html = ""
                                    # OTC医薬品セクション（折りたたみ可能なセクションとして独立）
                                    section_counter += 1
                                    section_id = f"otc-section-{section_counter}"
                                    formatted_usage_notes += f'<div class="collapsible-section" data-collapsible="true" data-default-expanded="false" role="region" aria-label="{line}" style="background: #e3f2fd; border-left: 4px solid #1976d2;"><button class="collapse-toggle" aria-expanded="false" aria-controls="{section_id}" aria-label="詳細を見る"><span class="collapse-icon">▼</span><h5 style="margin: 0; display: inline;">{line}</h5></button><div class="collapse-content" id="{section_id}" style="padding: 15px; margin: 10px 0;">'
                                    current_html = ""
                                    current_section = 'otc'
                                elif line.startswith('【服用時の注意】'):
                                    # 前のセクションを閉じる
                                    if current_section == 'individual':
                                        # 医薬品セクションのコンテンツとセクション自体を閉じる
                                        if current_html:
                                            formatted_usage_notes += current_html
                                        formatted_usage_notes += '</div></div>'  # collapse-contentとcollapsible-sectionを閉じる
                                        current_html = ""
                                    elif current_section and current_html:
                                        # その他のセクション（caution, usage等）を閉じる
                                        formatted_usage_notes += current_html + '</div></div>'
                                        current_html = ""
                                    # 服用注意セクション（折りたたみ可能）
                                    section_counter += 1
                                    section_id = f"usage-note-section-{section_counter}"
                                    formatted_usage_notes += f'<div class="collapsible-section" data-collapsible="true" data-default-expanded="false" role="region" aria-label="{line}" style="background: #fff3e0; border-left: 4px solid #f57c00;"><button class="collapse-toggle" aria-expanded="false" aria-controls="{section_id}" aria-label="詳細を見る"><span class="collapse-icon">▼</span><h5 style="color: #f57c00; margin: 0; display: inline;">📌 {line}</h5></button><div class="collapse-content" id="{section_id}" style="padding: 15px; margin: 10px 0;">'
                                    current_html = ""
                                    current_section = 'usage'
                                elif line.startswith('年齢制限:'):
                                    # 年齢制限の処理（重複を避けるため）
                                    if not age_restriction_added:
                                        age_restriction = line.replace('年齢制限:', '').strip()
                                        if age_restriction and age_restriction != 'なし':
                                            # 年齢制限がある場合のみ表示（重複を避けるため）
                                            if '未満の方は使用しないでください' in age_restriction or '未満は服用しないこと' in age_restriction:
                                                # 既に適切な形式になっている場合はそのまま表示
                                                current_html += f'<p style="margin: 3px 0;"><strong>年齢制限:</strong> {age_restriction}</p>'
                                            elif '歳以上の方が対象です' in age_restriction:
                                                # 「歳以上の方が対象です」の場合はそのまま表示
                                                current_html += f'<p style="margin: 3px 0;"><strong>年齢制限:</strong> {age_restriction}</p>'
                                            else:
                                                # 「〇歳以上」パターンの場合は重複を避けて「〇歳以上の方が対象です。」と表示
                                                match = re.search(r'(\d+)歳以上', age_restriction)
                                                if match:
                                                    age_val = match.group(1)
                                                    current_html += f'<p style="margin: 3px 0;"><strong>年齢制限:</strong> {age_val}歳以上の方が対象です。</p>'
                                                else:
                                                    # その他の場合は「以上の方が対象です」を追加
                                                    current_html += f'<p style="margin: 3px 0;"><strong>年齢制限:</strong> {age_restriction}以上の方が対象です。</p>'
                                            age_restriction_added = True
                                elif line.startswith('ドーピング:'):
                                    # ドーピングの処理
                                    doping_info = line.replace('ドーピング:', '').strip()
                                    if doping_info and doping_info != 'なし':
                                        # ドーピング情報がある場合のみ表示
                                        current_html += f'<p style="margin: 3px 0;"><strong>ドーピング:</strong> {doping_info}</p>'
                                elif line.startswith('・'):
                                    # リストアイテム
                                    current_html += f'<p style="margin: 3px 0; padding-left: 10px;">{line}</p>'
                                else:
                                    # 通常のテキスト（年齢制限とドーピング以外）
                                    # 「⚠️ 治療中の方へ」の内容は、医薬品セクション内では表示（各医薬品の下に表示）、それ以外ではスキップ（上部に表示されているため）
                                    if not line.startswith('年齢制限:') and not line.startswith('ドーピング:'):
                                        # 医薬品セクション内の場合は「治療中の方へ」も表示
                                        if current_section == 'individual':
                                            current_html += f'<p style="margin: 3px 0;">{line}</p>'
                                        else:
                                            # 医薬品セクション外（ルートレベル）の場合は「治療中の方へ」をスキップ
                                            if not (line.startswith('⚠️ 治療中の方へ') or 
                                                    '現在治療中の疾患がある場合' in line or 
                                                    '治療中の方が市販薬を服用する場合' in line or
                                                    '主疾患への重大な影響' in line or
                                                    '重篤な疾患で治療中の方が市販薬を服用する場合' in line):
                                                current_html += f'<p style="margin: 3px 0;">{line}</p>'
                                        
                            # 最後のセクションを閉じる
                            if current_section:
                                if current_section == 'individual':
                                    # 医薬品セクションの場合、コンテンツとセクションを閉じる
                                    if current_html:
                                        formatted_usage_notes += current_html
                                    formatted_usage_notes += '</div></div>'
                                elif current_section in ['caution', 'usage', 'otc']:
                                    # 折りたたみ可能なセクションの場合
                                    if current_html:
                                        formatted_usage_notes += current_html
                                    formatted_usage_notes += '</div></div>'
                                else:
                                    # 折りたたみ不可のセクションの場合
                                    if current_html:
                                        formatted_usage_notes += current_html + '</div>'
                                
                    # 使用上の注意を折りたたみ可能にする
                    usage_notes_content = formatted_usage_notes if formatted_usage_notes else '<p>特になし</p>'
                    bot_content += f"""
    <div class="collapsible-section" data-collapsible="true" data-default-expanded="true" role="region" aria-label="使用上の注意" style="background: #fff3e0; border-left: 4px solid #ff9800;">
        <button class="collapse-toggle" aria-expanded="true" aria-controls="usage-notes-content" aria-label="閉じる">
    <span class="collapse-icon">▼</span>
    <h4 style="color: #e65100; margin-top: 0; display: inline;">⚠️ 使用上の注意</h4>
        </button>
        <div id="usage-notes-content" style="padding: 15px;">
    {usage_notes_content}
        </div>
    </div>
    """
                            
                # 「医師の受診が必要な場合」セクションを準備（翻訳処理の前に追加）
                doctor_consultation_section = ""
                if doctor_consultation or True:  # 常に表示
                    doctor_consultation_text = doctor_consultation if doctor_consultation else '症状が改善しない場合は医師にご相談ください。'
                    doctor_consultation_section = f"""
    <div class="warning-critical" role="region" aria-label="医師の受診が必要な場合" style="padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #f44336;">
        <h4 style="color: #c62828; margin-top: 0;">🏥 医師の受診が必要な場合</h4>
        <p style="margin: 5px 0;">{doctor_consultation_text}</p>
    </div>
    """
                    bot_content += doctor_consultation_section
                            
                # 質問セクションを追加（翻訳処理の前に追加）
                if questions_section_before:
                    bot_content += questions_section_before
                            
                # 表示順序: アドバイス → 推奨 → 使用上の注意 → 医師の受診 → 質問
                            
                # 多言語対応: 入力言語に応じて翻訳（すべてのセクション追加後、フィードバックボタン追加前）
                detected_language = session.get('detected_language', 'ja')
                if detected_language != 'ja' and bot_content:
                    try:
                        logger.info(f"🌍 翻訳開始: {detected_language}")
                        mark_processing_step(sid, "translate")
                        translated_content = translate_medicine_recommendation(bot_content, detected_language, recommendation_client, session_id=sid)
                        if translated_content and translated_content != bot_content:
                            bot_content = translated_content
                            logger.info(f"✅ 翻訳完了: {detected_language}")
                        else:
                            logger.info(f"⚠️ 翻訳スキップ: 翻訳結果が空または同じ")
                    except Exception as e:
                        logger.error(f"❌ 翻訳エラー: {e}")
                        # 翻訳に失敗した場合は元のコンテンツを使用
                            
                # 評価ボタン用のデータを準備（HTMLエスケープ処理）
                import json
                import html
                            
                # HTMLエスケープ処理
                escaped_user_message = html.escape(user_message)
                escaped_ai_response = html.escape(bot_content)
                            
                feedback_data = {
                    'user_message': escaped_user_message,
                    'ai_response': escaped_ai_response,
                    'security_score': None
                }
                            
                # JSONエンコードしてHTMLエスケープ
                feedback_json = html.escape(json.dumps(feedback_data, ensure_ascii=False))
                            
                # フィードバックボタンのテキストも翻訳
                feedback_text = "この推奨結果はいかがでしたか？"
                feedback_positive = "適切"
                feedback_negative = "不適切"
                if detected_language != 'ja':
                    try:
                        feedback_text_translated = translate_medicine_recommendation(feedback_text, detected_language, recommendation_client, session_id=sid)
                        feedback_positive_translated = translate_medicine_recommendation(feedback_positive, detected_language, recommendation_client, session_id=sid)
                        feedback_negative_translated = translate_medicine_recommendation(feedback_negative, detected_language, recommendation_client, session_id=sid)
                        if feedback_text_translated and feedback_text_translated != feedback_text:
                            feedback_text = feedback_text_translated
                        if feedback_positive_translated and feedback_positive_translated != feedback_positive:
                            feedback_positive = feedback_positive_translated
                        if feedback_negative_translated and feedback_negative_translated != feedback_negative:
                            feedback_negative = feedback_negative_translated
                    except Exception as e:
                        logger.warning(f"⚠️ フィードバックボタンの翻訳エラー: {e}")
                            
                bot_content += f"""
    <div id="voice-read-container-inline" style="margin-top: 20px; margin-bottom: 10px;">
        <button type="button" class="voice-read-main-btn" id="voiceReadMainBtn" onclick="toggleVoiceRead()" aria-label="推奨結果を音声で読み上げる" style="width: 100%; padding: 12px 20px; background: #4CAF50; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: 600; min-height: 44px;">
    🔊 音声で聞く
        </button>
        <div id="voice-read-progress-inline" style="margin-top: 10px; display: none;">
    <div style="background: #e0e0e0; border-radius: 4px; height: 8px; overflow: hidden;">
        <div id="voice-read-progress-bar-inline" style="background: #4CAF50; height: 100%; width: 0%; transition: width 0.3s ease;"></div>
    </div>
    <p id="voice-read-percentage-inline" style="margin: 5px 0 0 0; text-align: center; font-size: 14px; color: #666;">0%</p>
        </div>
    </div>
    <div class="feedback-buttons" style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6;">
        <p style="margin: 0 0 10px 0; font-weight: bold; color: #495057;">{feedback_text}</p>
        <button class="feedback-btn-positive" onclick="handlePositiveFeedback({feedback_json})" style="background: #28a745; color: white; border: none; padding: 8px 16px; margin-right: 10px; border-radius: 4px; cursor: pointer; font-size: 14px;">
    {feedback_positive}
        </button>
        <button class="feedback-btn-negative" onclick="handleNegativeFeedback({feedback_json})" style="background: #dc3545; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px;">
    {feedback_negative}
        </button>
    </div>
    </div>"""
                            
                # bot_contentが完成したので、完全なapp_outputでログを追加記録
                try:
                    from src.core.rule_based_recommendation import log_recommendation_session
                    log_recommendation_session(
                        user_text=user_message,
                        user_info=user_info,
                        result=recommendation_result,
                        session_id=sid,
                        app_output=bot_content  # 完全なHTML出力を記録
                    )
                except Exception as e:
                    logger.warning(f"⚠️ ログ追加エラー（無視して続行）: {e}")
                        
                bot_diag = recommendation_result
                        
        except Exception as e:
            logger.error(f"❌ 包括的医薬品推奨システム実行時エラー: {e}", exc_info=True)
            # 技術的なエラー内容はユーザーに表示せず、分かりやすいメッセージを返す
            bot_content = format_system_error(
                title='一時的なエラーが発生しました',
                message='医薬品の推奨処理中に問題が発生しました。しばらく時間をおいてからもう一度お試しください。',
            )
            bot_diag = None
                    
        # 個別アドバイスは既にbot_contentの最初に追加済み（重複削除）
                    
        # bot_diagが未定義の場合はNoneに設定
        if 'bot_diag' not in locals():
            bot_diag = None
                    
        # ユーザー向け情報のサニタイズ
        def sanitize_for_user_storage(diagnosis_data):
            """ユーザー向けに情報をサニタイズ"""
            if not diagnosis_data:
                return diagnosis_data
                        
            sanitized = diagnosis_data.copy()
                        
            # 推奨医薬品から管理者専用情報を除去（管理画面ではスコア情報を保持）
            if 'recommended_medicines' in sanitized:
                for medicine in sanitized['recommended_medicines']:
                    # 管理画面ではスコア情報を保持するため、削除しない
                    # medicine.pop('score', None)
                    # medicine.pop('scores', None)
                    # medicine.pop('score_breakdown', None)
                                
                    # 推奨理由を簡潔化
                    if 'reason' in medicine:
                        # 詳細なスコア情報を含む推奨理由を簡潔化
                        reason = medicine['reason']
                        if '✅' in reason or '⚠️' in reason or '|' in reason:
                            medicine['reason'] = "症状に適した医薬品です"
                        
            return sanitized
                    
        # 診断結果をサニタイズ
        sanitized_diagnosis = sanitize_for_user_storage(bot_diag)
                    
        # 管理者専用の詳細情報を別途保存（session_idを付与してフロントの一致判定を通す）
        if bot_diag and sid:
            if sid not in ADMIN_SESSIONS:
                ADMIN_SESSIONS[sid] = {}
            try:
                bot_diag_with_sid = dict(bot_diag)
            except Exception:
                # 念のためフォールバック
                bot_diag_with_sid = bot_diag
            # フロント側（admin_chat.html）は currentDetailedDiagnosis.session_id === currentSessionId を要求
            # ここでセッションIDを埋め込むことでスコア付き詳細を確実に表示可能にする
            if isinstance(bot_diag_with_sid, dict):
                bot_diag_with_sid['session_id'] = sid
            ADMIN_SESSIONS[sid]['detailed_diagnosis'] = bot_diag_with_sid
            ADMIN_SESSIONS[sid]['last_updated'] = time.time()
            logger.info(f"💾 管理者専用詳細情報を保存: {sid} (session_id付与済み)")
                    
        bot_response = {
            'type': 'bot',
            'content': bot_content,
            'diagnosis': sanitized_diagnosis
        }
                
    # bot_responseが定義されている場合の処理
    logger.info(f"🔍 bot_response check: in locals={('bot_response' in locals())}, bot_response={bot_response is not None if 'bot_response' in locals() else 'N/A'}")
    if 'bot_response' in locals() and bot_response is not None:
        logger.info(f"✅ bot_response found, content length: {len(bot_response.get('content', ''))}")
        # 重複チェック：同じ内容のメッセージが既に存在するかチェック
        # ただし、counseling_medicine_infoメッセージ（「一時的な不眠で、推奨される医薬品を知りたい場合は教えて下さい。」）は重複チェックから除外
        existing_messages = session.get('messages', [])
        is_duplicate = False
                    
        # counseling_medicine_infoメッセージの場合は重複チェックをスキップ
        is_medicine_info_message = bot_response.get('counseling_medicine_info', False)
                    
        if not is_medicine_info_message:
            for existing_msg in existing_messages:
                if (existing_msg.get('type') == 'bot' and 
                    existing_msg.get('content') == bot_response['content']):
                    is_duplicate = True
                    logger.warning(f"⚠️ 重複メッセージを検出、追加をスキップします")
                    break
                    
        if not is_duplicate:
            # DBに保存
            if sid:
                session_data = get_session_from_db(sid)
                if not session_data:
                    # 新しいセッションを作成
                    session_data = {
                        'session_id': sid,
                        'username': session.get('username', 'Unknown'),
                        'messages': [],
                        'last_activity': datetime.now(),
                        'client_ip': client.client_ip,
                        'user_agent': client.user_agent,
                        'user_attributes': session.get('user_attributes', {}),
                        'session_active': True
                    }
                            
                # メッセージを追加
                if 'messages' not in session_data:
                    session_data['messages'] = []
                session_data['messages'].append(bot_response)
                session_data['last_activity'] = datetime.now()
                            
                # detailed_diagnosisをDBにも保存（ADMIN_SESSIONSから取得）
                if sid in ADMIN_SESSIONS and 'detailed_diagnosis' in ADMIN_SESSIONS[sid]:
                    session_data['detailed_diagnosis'] = ADMIN_SESSIONS[sid]['detailed_diagnosis']
                            
                # DBに保存
                save_session_to_db(sid, session_data)
                logger.info(f"💾 メッセージ保存完了: {len(session_data.get('messages', []))} messages")
                            
                # セッションCookie肥大化を防ぐためFlaskセッションからmessagesを削除
                if 'messages' in session:
                    del session['messages']
                    session.modified = True
                                
                    # 医薬品相談回答処理の終了時にフラグをクリア
                    if session.get('is_medicine_consultation', False):
                        session['is_medicine_consultation'] = False
                        logger.info(f"💊 医薬品相談回答処理終了 - フラグクリア完了")
        else:
            logger.info(f"⏭️ 重複メッセージのため追加をスキップしました")
    else:
        logger.error(f"❌ bot_responseが定義されていません - locals: {list(locals().keys())}")
        # フォールバック
        bot_response = {
        'type': 'bot',
        'content': '処理中にエラーが発生しました。',
        'diagnosis': None
        }
        if 'messages' not in session:
            session['messages'] = []
        session['messages'].append(bot_response)
        session.modified = True
    manual_replies = get_manual_reply_queue() or []
    if manual_replies:
        logger.info(f"📝 Manual replies preserved: {len(manual_replies)} messages")
        if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
            logger.debug(f"Manual replies found in session {sid}: {len(manual_replies)} messages")
            for i, reply in enumerate(manual_replies):
                logger.debug(f"  Manual reply {i+1}: {reply.get('content', '')[:50]}...")
        
    # POSTリクエストの場合はJSON形式で成功を返す
    mark_processing_step(sid, "finalize")
    message_count = len(session.get('messages', []))
    return build_success_response(session, message_count)