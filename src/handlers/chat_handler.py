"""
チャットPOSTリクエストハンドラー

index() の POST 処理を委譲し、責務を分離する。
"""

import os
import time
import logging
import uuid
from datetime import datetime

from flask import jsonify, request, has_request_context

from src.utils.request_logger import log_user_interaction, log_medicine_logic_call, log_network_request
from src.utils.input_helpers import is_symptom_input, check_missing_attributes, is_ambiguous_input
from src.core.language_utils import detect_language
from src.utils.performance_monitor import log_performance_metrics
from src.services.analytics import log_access_analytics
from src.utils.user_attribute_registration import register_user_attributes_from_message
from src.utils.debug_logger import add_network_log
from src.services.session_manager import (
    get_admin_mode,
    get_manual_reply_queue,
    set_manual_reply_queue,
    get_session_from_db,
    save_session_to_db,
    remove_duplicate_user_messages_after_ai_response,
    get_admin_sessions,
)
from src.core.medicine_logic import (
    client,
    select_symptoms_via_gpt,
    analyze_symptoms_and_medicine_type,
    rule_based_medicine_recommendation,
)
from src.services.chat_response_service import generate_personalized_advice
from src.handlers.chat.chat_input_validator import validate_and_block_input
from src.handlers.chat.chat_response_builder import build_success_response
from src.handlers.chat.chat_recommendation_flow import run_recommendation_flow

logger = logging.getLogger(__name__)


def handle_chat_post(session, request, sid, monitor, client_ip, user_agent):
    """
    チャットPOSTリクエストを処理する。

    Args:
        session: Flaskセッションオブジェクト
        request: Flaskのrequestオブジェクト
        sid: セッションID
        monitor: パフォーマンスモニター
        client_ip: クライアントIP
        user_agent: User-Agent

    Returns:
        Flask Response (jsonify)
    """
    ADMIN_SESSIONS = get_admin_sessions()

    logger.info(f"📨 POST処理開始")
    user_message = request.form.get('message', '').strip()
    logger.info(f"📝 受信メッセージ: {user_message}")
    if user_message:
        sanitized_message, error_response = validate_and_block_input(session, request, user_message, sid)
        if error_response is not None:
            return error_response

        # ユーザーメッセージをセッションに追加（通常フロー）
        # 危機検出や心臓緊急チェックで早期リターンする場合は既に追加済み
        if 'messages' not in session:
            session['messages'] = []
            
        from datetime import datetime
        import uuid
            
        # 個別チャット単位でAI自動応答のON/OFFを確認（OFFの場合は chat_manual_reply で処理して return）
        session_data_for_ai = get_session_from_db(sid) if sid else {}
        from src.handlers.chat.chat_manual_reply import handle_manual_reply_when_off
        manual_resp = handle_manual_reply_when_off(session, request, sid, sanitized_message, session_data_for_ai)
        if manual_resp is not None:
            return manual_resp

        # ステップ1: LLMトリアージ＋心臓緊急チェック（chat_triage に委譲）
        recommendation_client = client  # medicine_logicからインポート済み
        from src.handlers.chat.chat_triage import run_triage
        early_response, triage_result = run_triage(
            session, request, sid, user_message, sanitized_message, recommendation_client
        )
        if early_response is not None:
            return early_response

        # ステップ1.7: 診断名検出（chat_diagnosis_handler に委譲）
        try:
            from src.handlers.chat.chat_diagnosis_handler import handle_diagnosis_if_detected
            diagnosis_resp = handle_diagnosis_if_detected(session, request, sid, sanitized_message)
            if diagnosis_resp is not None:
                return diagnosis_resp
        except ImportError as e:
            logger.warning(f"⚠️ 診断名検出機能のインポートに失敗: {e}")
        except Exception as e:
            logger.error(f"❌ 診断名検出機能でエラー: {e}")
            import traceback
            traceback.print_exc()

        # ステップ1.7.5: 緊急事案検出（chat_emergency_handler に委譲）
        try:
            from src.handlers.chat.chat_emergency_handler import handle_emergency_if_detected
            emergency_resp = handle_emergency_if_detected(
                session, request, sid, sanitized_message,
                recommendation_client, triage_result,
            )
            if emergency_resp is not None:
                return emergency_resp
        except Exception as e:
            logger.error(f"❌ 緊急事案検出機能でエラー: {e}")
            import traceback
            traceback.print_exc()

        # ステップ1.7.5: 不適切なメッセージの検出（最優先）
        inappropriate_message_detected = False
        try:
            from config.keywords import INAPPROPRIATE_MESSAGE_KEYWORDS
            from src.services.counseling_response import normalize_text
            import re
                
            normalized_message = normalize_text(sanitized_message)
                
            # 誤検知を避けるため、一般的な言葉として使われる可能性があるキーワードのリスト
            # これらのキーワードは単語境界を厳密にチェックする
            AMBIGUOUS_KEYWORDS = [
                "やばい", "ヤバい", "草", "くさ", "クサ", "H", "h",
                "尊い", "たっふい", "タッフイ", "ワロタ", "わろた"
            ]
                
            # 数字による隠語のリスト（性的な意味で使われる数字）
            NUMERIC_SLANG = ["69", "88", "419"]
                
            # 数字による隠語の検出（単独で使われる場合のみ）
            for num_slang in NUMERIC_SLANG:
                # 数字が単独で使われている場合（前後に数字や文字が来ない）を検出
                pattern = r'(?:^|[^\d])' + re.escape(num_slang) + r'(?:[^\d]|$)'
                if re.search(pattern, normalized_message):
                    inappropriate_message_detected = True
                    logger.warning(f"⚠️ 不適切なメッセージを検出（数字隠語）: {num_slang}, session_id={sid}")
                    break
                
            if not inappropriate_message_detected:
                for keyword in INAPPROPRIATE_MESSAGE_KEYWORDS:
                    normalized_keyword = normalize_text(keyword)
                        
                    # 誤検知を避けるため、単語境界を考慮した検出を行う
                    # 短いキーワード（3文字以下）または曖昧なキーワードは単語境界を厳密にチェック
                    if len(keyword) <= 3 or keyword in AMBIGUOUS_KEYWORDS:
                        # 単語境界を考慮したパターン（前後に単語文字が来ない）
                        pattern = r'\b' + re.escape(normalized_keyword) + r'\b'
                        if re.search(pattern, normalized_message):
                            inappropriate_message_detected = True
                            logger.warning(f"⚠️ 不適切なメッセージを検出: {keyword}, session_id={sid}")
                            break
                    else:
                        # 長いキーワードは部分一致でも検出（誤検知のリスクが低い）
                        if normalized_keyword in normalized_message:
                            inappropriate_message_detected = True
                            logger.warning(f"⚠️ 不適切なメッセージを検出: {keyword}, session_id={sid}")
                            break
                
            if inappropriate_message_detected:
                # 不適切なメッセージに対する応答を生成
                from src.services.counseling_response import (
                    generate_counseling_response,
                    generate_follow_up_questions,
                    start_counseling_mode
                )
                    
                # ユーザーメッセージをセッションに追加
                if 'messages' not in session:
                    session['messages'] = []
                    
                import uuid
                user_msg = {
                    'type': 'user',
                    'content': sanitized_message,
                    'timestamp': datetime.now().isoformat(),
                    'uuid': str(uuid.uuid4())
                }
                session['messages'].append(user_msg)
                session.modified = True
                    
                # ユーザーメッセージをDBに保存
                if sid:
                    session_data = get_session_from_db(sid)
                    if session_data:
                        if 'messages' not in session_data:
                            session_data['messages'] = []
                        session_data['messages'].append(user_msg)
                        session_data['last_activity'] = datetime.now()
                        save_session_to_db(sid, session_data)
                    else:
                        session_data = {
                            'session_id': sid,
                            'username': session.get('username', f'ユーザー{get_next_user_number()}'),
                            'messages': [user_msg],
                            'session_active': True,
                            'last_activity': datetime.now(),
                            'client_ip': request.remote_addr,
                            'user_agent': request.headers.get('User-Agent', ''),
                            'user_attributes': session.get('user_attributes', {})
                        }
                        save_session_to_db(sid, session_data)
                    
                # カウンセリングフロー開始（不適切なメッセージ専用）
                symptom_type = "inappropriate_request/inappropriate_message"
                conversation_history = session.get('messages', [])[-10:] if len(session.get('messages', [])) > 10 else session.get('messages', [])
                    
                initial_response = generate_counseling_response(
                    symptom_type, sanitized_message, recommendation_client,
                    conversation_history=conversation_history,
                    session_id=sid
                )
                initial_questions = generate_follow_up_questions(
                    symptom_type, {}, recommendation_client
                )
                start_counseling_mode(session, symptom_type, initial_questions)
                    
                bot_response = {
                    'type': 'bot',
                    'content': initial_response,
                    'counseling': True,
                    'inappropriate_request': True,
                    'request_type': 'inappropriate_message',
                    'timestamp': datetime.now().isoformat()
                }
                session['messages'].append(bot_response)
                    
                if sid:
                    session_data = get_session_from_db(sid)
                    if session_data:
                        if 'messages' not in session_data:
                            session_data['messages'] = []
                        session_data['messages'].append(bot_response)
                        session_data['last_activity'] = datetime.now()
                        save_session_to_db(sid, session_data)
                    
                from src.services.counseling_response import log_counseling_response
                log_counseling_response(
                    session_id=sid,
                    response_content=initial_response,
                    response_type="counseling_inappropriate_message",
                    category="Other",
                    confidence=1.0,
                    counseling_mode=session.get('counseling_mode'),
                    user_input=user_message,
                    conversation_history=None
                )
                    
                session.modified = True
                message_count = len(session['messages'])
                logger.info(f"✅ 不適切なメッセージ処理完了: {message_count} messages")
                return jsonify({
                    'status': 'ok',
                    'message_count': message_count
                })
        except ImportError as e:
            logger.warning(f"⚠️ 不適切なメッセージ検出機能のインポートに失敗: {e}")
        except Exception as e:
            logger.error(f"❌ 不適切なメッセージ検出機能でエラー: {e}")
            import traceback
            traceback.print_exc()
            
        # 元のユーザーメッセージを保持（UI表示用）
        original_user_message = user_message
            
        # ステップ1.7.5.5: 基本正規化（新規追加）
        try:
            from src.core.scoring_utils import basic_normalize_text
            sanitized_message = basic_normalize_text(sanitized_message)
        except ImportError:
            logger.warning("⚠️ 基本正規化機能のインポートに失敗")
        except Exception as e:
            logger.error(f"❌ 基本正規化エラー: {e}")
            
        # ステップ1.7.6: 方言変換（新規追加）
        processed_message = sanitized_message  # 内部処理用のメッセージ
            
        try:
            from src.core.scoring_utils import convert_dialect_to_standard, check_escalation_threshold
            converted_message, severity_tag, escalation_score, non_destructive_candidates, normalized_weights = convert_dialect_to_standard(
                sanitized_message,
                extract_severity=True,
                non_destructive=True,
                use_aho_corasick=True,
                use_index=True,
                use_scanner=True
            )
            processed_message = converted_message  # 内部処理用に変換後のテキストを保存
            # sanitized_messageは元のメッセージのまま保持（UI表示用）
                
            # 重症度タグをセッションに保存
            if severity_tag:
                session['detected_severity_tag'] = severity_tag
                
            # escalation_scoreをセッションに保存
            if escalation_score > 0:
                session['escalation_score'] = escalation_score
                    
                # 閾値を超えている場合は受診勧奨フラグを立てる（閾値4.0：重度×2回分）
                if check_escalation_threshold(escalation_score):
                    session['doctor_referral_required'] = True
                    session['escalation_reason'] = f"複数の強調表現が検出されました（escalation_score: {escalation_score:.1f}）。特に高齢の方の場合、複数の強調語は「痛みに耐えかねている」シグナルです。医師の診断を受けることをお勧めします。"
                
            # 非破壊的変換の候補をセッションに保存
            if non_destructive_candidates:
                session['dialect_candidates'] = non_destructive_candidates
                
            # 正規化された重みをセッションに保存
            if normalized_weights:
                session['normalized_symptom_weights'] = normalized_weights
                
            # デバッグモード時のログ記録
            DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(
                    f"方言変換: {sanitized_message[:50]}... "
                    f"(重症度タグ: {severity_tag}, escalation_score: {escalation_score:.1f}, "
                    f"候補数: {len(non_destructive_candidates)}, 重み数: {len(normalized_weights)})"
                )
        except ImportError:
            logger.warning("⚠️ 方言変換機能のインポートに失敗")
        except Exception as e:
            logger.error(f"❌ 方言変換エラー: {e}")
            import traceback
            traceback.print_exc()
            
        # ステップ1.7.7: 治療中フラグ確認・主訴判定・不適切な要求検出（chat_triage_follow_ups に委譲）
        from src.handlers.chat.chat_triage_follow_ups import run_triage_follow_ups
        early_resp, inappropriate_request_detected = run_triage_follow_ups(
            session, request, sid, sanitized_message, user_message, processed_message,
            triage_result, recommendation_client,
        )
        if early_resp is not None:
            return early_resp

        # ステップ1.8: 店舗案内・遺失物関連の処理（chat_store_inquiry に委譲）
        store_inquiry_result = None
        if not inappropriate_request_detected:
            try:
                from src.handlers.chat.chat_store_inquiry import handle_store_inquiry_response
                store_resp = handle_store_inquiry_response(
                    session, request, sid, sanitized_message,
                    recommendation_client, triage_result,
                )
                if store_resp is not None:
                    return store_resp
            except ImportError as e:
                logger.warning(f"⚠️ 店舗案内・遺失物関連機能のインポートに失敗: {e}")
            except Exception as e:
                logger.error(f"❌ 店舗案内・遺失物関連機能でエラー: {e}")
                import traceback
                traceback.print_exc()
            store_inquiry_result = None
        else:
            logger.info(f"⏭️ 不適切な要求が検出されたため、店舗案内処理をスキップ")

        # ステップ1.8.5: 店舗案内ではないと判定された場合、カウンセリングフローに流す
        if store_inquiry_result is None and triage_result and triage_result.get("category") == "Other":
            logger.info(f"🔍 店舗案内ではないと判定されたため、カウンセリングフローに流す")
            # 妊娠・授乳などユーザー属性のみのメッセージを先に抽出してuser_attributesに登録
            # （カウンセリングフローではユーザー情報登録処理を通らないため、ここで登録する）
            try:
                if 'user_attributes' not in session:
                    session['user_attributes'] = {}
                user_attributes = session['user_attributes']
                msg_for_attr = sanitized_message
                if '妊娠' in msg_for_attr or 'pregnant' in msg_for_attr.lower():
                    if any(kw in msg_for_attr for kw in ['妊娠していません', '妊娠中ではありません', '妊娠していない', '妊娠してない']):
                        user_attributes['pregnant'] = False
                        logger.info(f"📝 妊娠状態を登録（Otherフロー）: False")
                    elif any(kw in msg_for_attr for kw in ['妊娠中です', '妊娠中', '妊娠しています', '妊娠しました', '妊娠してます', '妊娠した', '妊婦です']):
                        user_attributes['pregnant'] = True
                        logger.info(f"📝 妊娠状態を登録（Otherフロー）: True")
                if '授乳' in msg_for_attr or 'breastfeeding' in msg_for_attr.lower():
                    if any(kw in msg_for_attr for kw in ['授乳していません', '授乳中ではありません', '授乳していない']):
                        user_attributes['breastfeeding'] = False
                        logger.info(f"📝 授乳状態を登録（Otherフロー）: False")
                    elif any(kw in msg_for_attr for kw in ['授乳中です', '授乳中', '授乳しています', '授乳しました', '授乳してます']):
                        user_attributes['breastfeeding'] = True
                        logger.info(f"📝 授乳状態を登録（Otherフロー）: True")
                session.modified = True
            except Exception as e:
                logger.warning(f"⚠️ Otherフローでの妊娠・授乳抽出でエラー: {e}")
            # カウンセリングフローに流す
            try:
                from src.services.counseling_response import (
                    generate_counseling_response,
                    generate_follow_up_questions,
                    start_counseling_mode,
                    has_specific_symptom
                )
                    
                # ユーザーメッセージをセッションに追加（重複チェック付き）
                if 'messages' not in session:
                    session['messages'] = []
                    
                # 重複チェック（診断名検出時に既に追加されている可能性がある）
                # UI表示用には正規化前の元入力を使用（カタカナ→ひらがな変換で表示が変わらないように）
                user_message_exists = any(
                    msg.get('type') == 'user' and 
                    msg.get('content') == original_user_message and
                    msg.get('uuid')
                    for msg in session.get('messages', [])
                )
                    
                if not user_message_exists:
                    import uuid
                    user_msg = {
                        'type': 'user',
                        'content': original_user_message,
                        'timestamp': datetime.now().isoformat(),
                        'uuid': str(uuid.uuid4())
                    }
                    session['messages'].append(user_msg)
                    session.modified = True
                        
                    # ユーザーメッセージをDBに保存
                    if sid:
                        session_data = get_session_from_db(sid)
                        if session_data:
                            if 'messages' not in session_data:
                                session_data['messages'] = []
                            # DB側でも重複チェック
                            db_message_exists = any(
                                msg.get('type') == 'user' and 
                                msg.get('content') == original_user_message and
                                msg.get('uuid')
                                for msg in session_data.get('messages', [])
                            )
                            if not db_message_exists:
                                session_data['messages'].append(user_msg)
                                session_data['last_activity'] = datetime.now()
                                save_session_to_db(sid, session_data)
                        else:
                            session_data = {
                                'session_id': sid,
                                'username': session.get('username', f'ユーザー{get_next_user_number()}'),
                                'messages': [user_msg],
                                'session_active': True,
                                'last_activity': datetime.now(),
                                'client_ip': request.remote_addr,
                                'user_agent': request.headers.get('User-Agent', ''),
                                'user_attributes': session.get('user_attributes', {})
                            }
                            save_session_to_db(sid, session_data)
                    
                # 症状が検出されている場合は、より適切なカウンセリングタイプを使用
                has_symptom = has_specific_symptom(processed_message)  # 方言変換後のテキストを使用
                if has_symptom:
                    # 症状が検出されている場合は、一般的な症状相談として扱う
                    symptom_type = "general_symptom"
                else:
                    # 症状が検出されていない場合は、不明な要求として扱う
                    symptom_type = "inappropriate_request/unknown"
                    
                # カウンセリングフロー開始（不明な要求専用）
                symptom_type = "inappropriate_request/unknown"
                conversation_history = session.get('messages', [])[-10:] if len(session.get('messages', [])) > 10 else session.get('messages', [])
                    
                initial_response = generate_counseling_response(
                    symptom_type, sanitized_message, recommendation_client,
                    conversation_history=conversation_history,
                    session_id=sid
                )
                initial_questions = generate_follow_up_questions(
                    symptom_type, {}, recommendation_client
                )
                start_counseling_mode(session, symptom_type, initial_questions)
                    
                bot_response = {
                    'type': 'bot',
                    'content': initial_response,
                    'counseling': True,
                    'inappropriate_request': True,
                    'request_type': 'unknown',
                    'timestamp': datetime.now().isoformat()
                }
                session['messages'].append(bot_response)
                    
                if sid:
                    session_data = get_session_from_db(sid)
                    if session_data:
                        if 'messages' not in session_data:
                            session_data['messages'] = []
                        session_data['messages'].append(bot_response)
                        session_data['last_activity'] = datetime.now()
                        # 妊娠・授乳などのuser_attributesをDBに反映（Otherフローで抽出した属性を永続化）
                        session_data['user_attributes'] = session.get('user_attributes', session_data.get('user_attributes', {}))
                        save_session_to_db(sid, session_data)
                    
                from src.services.counseling_response import log_counseling_response
                log_counseling_response(
                    session_id=sid,
                    response_content=initial_response,
                    response_type="counseling_unknown_request",
                    category="Other",
                    confidence=triage_result.get('confidence', 0.5),
                    counseling_mode=session.get('counseling_mode'),
                    user_input=user_message,
                    conversation_history=None
                )
                    
                session.modified = True
                message_count = len(session['messages'])
                logger.info(f"✅ 不明な要求のカウンセリングフロー処理完了: {message_count} messages")
                return jsonify({
                    'status': 'ok',
                    'message_count': message_count
                })
            except ImportError as e:
                logger.warning(f"⚠️ カウンセリングフロー機能のインポートに失敗: {e}")
            except Exception as e:
                logger.error(f"❌ カウンセリングフロー処理でエラー: {e}")
                import traceback
                traceback.print_exc()
                # エラー時は既存の汎用応答処理に進む
                session['should_handle_other_category'] = True
            
        # ステップ1.9: 眠気関連キーワードのチェック（カウンセリングモードチェックの前、重複チェックの前に実行）
        # 注意: このチェックは重複チェックの前に実行する必要がある（カウンセリングフローにリダイレクトするため）
        sleepiness_keywords = [
            "寝てしまう", "眠くて寝てしまう", "眠すぎて寝てしまう",
            "仕事中に寝てしまう", "居眠り", "眠くてたまらない",
            "眠気に襲われる", "眠くて仕方がない", "眠すぎる",
            "眠気が強い", "眠い", "眠たい", "寝むたい", "寝たい", "眠気", "だるい", "いつも眠い",
            "眠くて", "眠すぎ", "眠気で", "眠気です", "眠気が", "眠気の",
            "日中の眠気", "昼間の眠気", "眠くて困る", "眠くて仕方ない",
            "眠気が取れない", "眠気が強い", "強い眠気", "眠気がひどい",
            "日中に寝てしまう", "日中に寝てしま", "日中寝てしまう", "日中寝てしま"
        ]
        has_sleepiness_keyword = any(keyword in sanitized_message for keyword in sleepiness_keywords)
        # 後続処理で使用するため、セッションに保存
        session['has_sleepiness_keyword'] = has_sleepiness_keyword
            
        # 眠気が検出された場合、カウンセリングフローにリダイレクト（薬推奨フローからの切り替えでない場合）
        if has_sleepiness_keyword and not session.get('sleepiness_medicine_recommendation'):
            logger.info(f"🔄 眠気関連キーワードを検出: カウンセリングフローにリダイレクト (category={triage_result.get('category', 'N/A') if triage_result else 'N/A'})")
            # トリアージ結果をEmotionalカテゴリに変更
            if triage_result:
                triage_result['category'] = 'Emotional'
                triage_result['subcategory'] = 'drowsiness'
                triage_result['reasoning'] = '眠気関連キーワードを検出したため、カウンセリングフローにリダイレクト'
            category = 'Emotional'
            # Emotionalカテゴリの処理に進む（後続処理で実行される）
            
        # 重複チェック（ステップ1.9の後に実行）
        # 元のユーザーメッセージで重複チェック
        user_message_exists = any(
            msg.get('type') == 'user' and 
            msg.get('content') == original_user_message and
            msg.get('uuid')
            for msg in session.get('messages', [])
        )
            
        if not user_message_exists:
            user_msg = {
                'type': 'user',
                'content': original_user_message,  # 元のユーザーメッセージを表示（方言変換前）
                'timestamp': datetime.now().isoformat(),
                'uuid': str(uuid.uuid4())
            }
            session['messages'].append(user_msg)
            session.modified = True
                
            # ユーザーメッセージをDBに保存
            if sid:
                session_data = get_session_from_db(sid)
                if session_data:
                    if 'messages' not in session_data:
                        session_data['messages'] = []
                    session_data['messages'].append(user_msg)
                    session_data['last_activity'] = datetime.now()
                    save_session_to_db(sid, session_data)
        else:
            logger.info(f"⏭️ 重複ユーザーメッセージをスキップ: {original_user_message[:50]}...")
            
        # ステップ2: カウンセリングモード中かチェック（chat_counseling_flow に委譲）
        from src.handlers.chat.chat_counseling_flow import run_counseling_flow
        counseling_response, triage_result = run_counseling_flow(
            session, request, sid, user_message, processed_message, triage_result, recommendation_client
        )
        if counseling_response is not None:
            return counseling_response
        # ステップ2.4.5: 眠気関連キーワードのチェック（不眠チェックの前に行う）
        # 注意: このチェックはステップ1.9で既に実行済み（重複チェックの前に実行）
        # ここでは、眠気が検出された場合に不眠フローに入らないようにするフラグを設定するだけ
        has_sleepiness_keyword = session.get('has_sleepiness_keyword', False)
        skip_insomnia_check = has_sleepiness_keyword
            
        # ステップ2.5: 不眠関連キーワードのチェック（トリアージ結果に関係なく、必ずカウンセリングフローにリダイレクト）
        # 注意: 「不眠症」は診断名としてステップ1.7で既に検出されているため、ここから除外
        insomnia_keywords = [
            "不眠", "眠れない", "睡眠不足", "寝つきが悪い", "眠れません", "眠れないです", 
            "眠れない", "夜眠れない", "最近眠れない", "最近眠れません", "夜眠れません",
            "寝れない", "寝れません", "寝れないです", "夜寝れない", "最近寝れない",
            "眠れなくて", "眠れなく", "寝つけない", "寝つけません", "寝つけないです",
            # "不眠症" は診断名としてステップ1.7で検出されるため除外
            "不眠で", "不眠です", "不眠の", "不眠が",
            "睡眠薬", "睡眠薬を", "睡眠薬について", "睡眠薬を教えて", "睡眠薬を知りたい",
            "睡眠改善薬", "睡眠改善薬を", "睡眠改善薬について", "睡眠改善薬を教えて",
            "睡眠薬を紹介", "睡眠薬を紹介して", "睡眠改善薬を紹介", "睡眠改善薬を紹介して"
        ]
        has_insomnia_keyword = any(keyword in sanitized_message for keyword in insomnia_keywords)
            
        # 不眠関連キーワードが検出された場合、必ずカウンセリングフローにリダイレクト（薬推奨フローからの切り替えでない場合）
        # ただし、眠気が検出された場合は不眠フローには入らない
        if has_insomnia_keyword and not session.get('insomnia_medicine_recommendation') and not skip_insomnia_check:
            logger.info(f"🔄 不眠関連キーワードを検出: カウンセリングフローにリダイレクト (category={triage_result.get('category', 'N/A') if triage_result else 'N/A'})")
            # トリアージ結果をEmotionalカテゴリに変更
            if triage_result:
                triage_result['category'] = 'Emotional'
                triage_result['subcategory'] = 'insomnia'
                triage_result['reasoning'] = '不眠関連キーワードを検出したため、カウンセリングフローにリダイレクト'
            category = 'Emotional'
            # Emotionalカテゴリの処理に進む（後続処理で実行される）
            
        # ステップ3: confidenceスコアをチェック（Emergency例外処理を含む）
        if triage_result:
            try:
                from src.services.triage_analytics import log_confidence_check
                    
                category = triage_result.get('category', 'Other')
                confidence = triage_result.get('confidence', 1.0)
                    
                # Emergencyカテゴリの例外処理
                if category == 'Emergency':
                    # 緊急性が疑われる場合、確信度が低くても安全側に倒す
                    if confidence < 0.5:
                        # 非常に低い確信度の場合は確認を求める（ただし緊急を強調）
                        emergency_message = """
⚠️ 緊急症状の可能性がありますが、確信度が低いため確認が必要です。

心臓の痛みや呼吸困難などの緊急症状はありますか？
緊急の場合は119番（救急）に連絡してください。
"""
                        bot_response = {
                            'type': 'bot',
                            'content': emergency_message,
                            'emergency_warning': True,
                            'requires_confirmation': True,
                            'triage_result': triage_result,
                            'timestamp': datetime.now().isoformat()
                        }
                        session['messages'].append(bot_response)
                        session.modified = True
                            
                        # ログ記録（通常時は会話履歴なし）
                        from src.services.counseling_response import log_counseling_response
                        log_counseling_response(
                            session_id=sid,
                            response_content=emergency_message.strip(),
                            response_type="emergency_low_confidence_confirmation",
                            category="Emergency",
                            confidence=confidence,
                            counseling_mode=None,
                            user_input=user_message,
                            conversation_history=None
                        )
                            
                        # confidenceチェックのログ
                        log_confidence_check(
                            session_id=sid,
                            user_input=sanitized_message,
                            triage_result=triage_result,
                            confidence_threshold=0.5,
                            was_confirmation_requested=True
                        )
                            
                        if sid:
                            session_data = get_session_from_db(sid)
                            if session_data:
                                session_data['messages'] = session['messages'].copy()
                                session_data['last_activity'] = datetime.now()
                                save_session_to_db(sid, session_data)
                            
                        message_count = len(session['messages'])
                        return jsonify({'status': 'ok', 'message_count': message_count})
                    else:
                        # 0.5以上なら緊急対応フローへ（通常のconfidenceチェックをスキップ）
                        emergency_message = """⚠️ 緊急対応が必要な症状の可能性があります。
速やかに医療機関を受診するか、緊急の場合は119番（救急）に連絡してください。
市販薬での対応は推奨できません。医師の診断を受けてください。
"""
                        bot_response = {
                            'type': 'bot',
                            'content': emergency_message,
                            'emergency': True,
                            'medical_consultation': 'urgent',
                            'timestamp': datetime.now().isoformat()
                        }
                        session['messages'].append(bot_response)
                        session.modified = True
                            
                        # ログ記録（通常時は会話履歴なし）
                        from src.services.counseling_response import log_counseling_response
                        log_counseling_response(
                            session_id=sid,
                            response_content=emergency_message.strip(),
                            response_type="emergency_response",
                            category="Emergency",
                            confidence=confidence,
                            counseling_mode=None,
                            user_input=user_message,
                            conversation_history=None
                        )
                            
                        if sid:
                            session_data = get_session_from_db(sid)
                            if session_data:
                                session_data['messages'] = session['messages'].copy()
                                session_data['last_activity'] = datetime.now()
                                save_session_to_db(sid, session_data)
                            
                        message_count = len(session['messages'])
                        return jsonify({'status': 'ok', 'message_count': message_count})
                    
                # その他のカテゴリの通常処理
                if confidence < 0.7:
                    # 確信度が低い場合は確認を求める
                    from src.services.counseling_response import generate_counseling_response, detect_emotional_symptom_type, log_counseling_response
                        
                    # 会話履歴を取得（直近10件）
                    conversation_history = session.get('messages', [])[-10:] if len(session.get('messages', [])) > 10 else session.get('messages', [])
                        
                    # 確認メッセージを生成
                    if category == 'Emotional':
                        symptom_type = detect_emotional_symptom_type(sanitized_message, triage_result)
                        confirmation_message = generate_counseling_response(
                            symptom_type, sanitized_message, recommendation_client,
                            conversation_history=conversation_history,
                            session_id=sid
                        )
                    else:
                        confirmation_message = f"「{sanitized_message}」について、{category}カテゴリと判定しましたが、確信度が低いため確認が必要です。もう少し詳しく教えていただけますか？"
                            
                        # Otherカテゴリの場合もログ記録（通常時は会話履歴なし）
                        log_counseling_response(
                            session_id=sid,
                            response_content=confirmation_message,
                            response_type="low_confidence_confirmation",
                            category=category,
                            user_input=user_message,
                            conversation_history=None,
                            confidence=confidence,
                            counseling_mode=None
                        )
                        
                    bot_response = {
                        'type': 'bot',
                        'content': confirmation_message,
                        'requires_confirmation': True,
                        'triage_result': triage_result,
                        'timestamp': datetime.now().isoformat()
                    }
                    session['messages'].append(bot_response)
                    session.modified = True
                        
                    # confidenceチェックのログ
                    log_confidence_check(
                        session_id=sid,
                        user_input=sanitized_message,
                        triage_result=triage_result,
                        confidence_threshold=0.7,
                        was_confirmation_requested=True
                    )
                        
                    if sid:
                        session_data = get_session_from_db(sid)
                        if session_data:
                            session_data['messages'] = session['messages'].copy()
                            session_data['last_activity'] = datetime.now()
                            save_session_to_db(sid, session_data)
                        
                    message_count = len(session['messages'])
                    return jsonify({'status': 'ok', 'message_count': message_count})
                    
            except ImportError as e:
                logger.warning(f"⚠️ confidenceスコア処理機能のインポートに失敗: {e}")
            except Exception as e:
                logger.error(f"❌ confidenceスコア処理機能でエラー: {e}")
                import traceback
                traceback.print_exc()
            
        # ステップ4: カテゴリに応じて処理を分岐
        if triage_result:
            category = triage_result.get('category', 'Other')
            subcategory = triage_result.get('subcategory', '').lower()
                
            # ステップ4.5: 不適切な要求の検出（トリアージ結果確認後）
            # 注意: 既にステップ1.7.5で検出されている場合はスキップ
            if category == 'Other' and 'inappropriate_request' in subcategory and not inappropriate_request_detected:
                try:
                    from src.services.counseling_response import (
                        detect_inappropriate_request,
                        generate_counseling_response,
                        generate_follow_up_questions,
                        start_counseling_mode
                    )
                        
                    request_type = detect_inappropriate_request(sanitized_message, triage_result)
                        
                    if request_type:
                        # カウンセリングフロー開始
                        symptom_type = f"inappropriate_request/{request_type}"
                            
                        # 会話履歴を取得
                        conversation_history = session.get('messages', [])[-10:] if len(session.get('messages', [])) > 10 else session.get('messages', [])
                            
                        # カウンセリング応答を生成
                        initial_response = generate_counseling_response(
                            symptom_type, sanitized_message, recommendation_client,
                            conversation_history=conversation_history,
                            session_id=sid
                        )
                            
                        # フォローアップ質問を生成（違法薬物・規制薬物の場合は空リスト）
                        initial_questions = generate_follow_up_questions(
                            symptom_type, {}, recommendation_client
                        )
                            
                        # 違法薬物・規制薬物の場合は、カウンセリングモードを開始しない（単一メッセージで完結）
                        if request_type not in ['illegal', 'controlled']:
                            # カウンセリングモードを開始
                            start_counseling_mode(session, symptom_type, initial_questions)
                            
                        # セッションにフラグを設定
                        if 'inappropriate_requests' not in session:
                            session['inappropriate_requests'] = []
                        session['inappropriate_requests'].append({
                            'type': request_type,
                            'timestamp': datetime.now().isoformat(),
                            'user_message': sanitized_message
                        })
                            
                        # 応答をセッションに追加
                        bot_response = {
                            'type': 'bot',
                            'content': initial_response,
                            'counseling': request_type not in ['illegal', 'controlled'],
                            'inappropriate_request': True,
                            'request_type': request_type,
                            'timestamp': datetime.now().isoformat()
                        }
                        session['messages'].append(bot_response)
                            
                        # ログ記録
                        from src.services.counseling_response import log_counseling_response
                        log_counseling_response(
                            session_id=sid,
                            response_content=initial_response,
                            response_type="counseling_inappropriate_request",
                            category=category,
                            confidence=confidence,
                            counseling_mode=session.get('counseling_mode'),
                            user_input=user_message,
                            conversation_history=None
                        )
                            
                        # 検出ログ
                        logger.warning(f"⚠️ 不適切な要求検出: type={request_type}, session_id={sid}")
                            
                        # 早期リターン（通常の処理フローをスキップ）
                        session.modified = True
                        save_session_to_db(sid, session)
                        return jsonify({
                            'response': initial_response,
                            'questions': initial_questions if request_type not in ['illegal', 'controlled'] else [],
                            'counseling': request_type not in ['illegal', 'controlled'],
                            'inappropriate_request': True
                        })
                except Exception as e:
                    logger.error(f"❌ 不適切な要求処理エラー: {e}")
                    import traceback
                    traceback.print_exc()
                    # エラー時は通常の処理フローに戻る（安全側に倒す）
                    # フォールバックメッセージを表示
                    fallback_message = "申し訳ございませんが、システムエラーが発生しました。通常の相談フローに戻ります。"
                    logger.warning(f"⚠️ 不適切な要求処理でエラーが発生しましたが、通常の処理フローに戻ります: {e}")
                
            # 月経不順関連の症状が含まれている場合は、Emotionalカテゴリでも医薬品推奨フローに進む
            menstrual_keywords = ['生理不順', '月経不順', '生理が遅れ', '生理が来ない', '生理周期', 
                                 '月経異常', '血の道症', '生理痛', '月経痛', '生理の遅れ']
            has_menstrual_symptom = any(keyword in sanitized_message for keyword in menstrual_keywords)
                
            # 月経不順関連の症状がある場合は、カテゴリをPhysicalに変更して医薬品推奨フローに進む
            if has_menstrual_symptom and category == 'Emotional':
                category = 'Physical'
                logger.info(f"🔄 月経不順関連症状検出により、カテゴリをEmotionalからPhysicalに変更")
                
            if category == 'Emotional':
                # カウンセリングフロー開始（月経不順関連の症状がない場合のみ）
                try:
                    from src.services.counseling_response import (
                        detect_emotional_symptom_type,
                        generate_counseling_response,
                        generate_follow_up_questions,
                        start_counseling_mode
                    )
                        
                    symptom_type = detect_emotional_symptom_type(sanitized_message, triage_result)
                        
                    # 眠気関連キーワードが検出された場合、symptom_typeを強制的に"drowsiness"に設定
                    if has_sleepiness_keyword and symptom_type != "drowsiness":
                        symptom_type = "drowsiness"
                        logger.info(f"🔄 眠気関連キーワード直接検出により、symptom_typeを'drowsiness'に変更しました")
                        
                    # 不眠関連キーワードが検出された場合、symptom_typeを強制的に"insomnia"に設定（眠気が優先されない場合のみ）
                    if has_insomnia_keyword and symptom_type != "insomnia" and not has_sleepiness_keyword:
                        symptom_type = "insomnia"
                        logger.info(f"🔄 不眠関連キーワード直接検出により、symptom_typeを'insomnia'に変更しました")
                        
                    # 会話履歴を取得（直近10件）
                    conversation_history = session.get('messages', [])[-10:] if len(session.get('messages', [])) > 10 else session.get('messages', [])
                        
                    initial_response = generate_counseling_response(
                        symptom_type, sanitized_message, recommendation_client,
                        conversation_history=conversation_history,
                        session_id=sid
                    )
                    initial_questions = generate_follow_up_questions(
                        symptom_type, {}, recommendation_client
                    )
                        
                    # カウンセリングモードを開始
                    start_counseling_mode(session, symptom_type, initial_questions)
                        
                    # 初期応答と最初の質問を送信
                    bot_response = {
                        'type': 'bot',
                        'content': initial_response,
                        'counseling': True,
                        'timestamp': datetime.now().isoformat()
                    }
                    session['messages'].append(bot_response)
                        
                    # 初期返信のログ記録（通常時は会話履歴なし）
                    from src.services.counseling_response import log_counseling_response
                    log_counseling_response(
                        session_id=sid,
                        response_content=initial_response,
                        response_type="counseling_initial_response",
                        category=category,
                        confidence=confidence,
                        counseling_mode=session.get('counseling_mode'),
                        user_input=user_message,
                        conversation_history=None
                    )
                        
                    # 不眠カウンセリングの場合、「一時的な不眠で、推奨される医薬品を知りたい場合は教えて下さい。」というメッセージを別途送信
                    # symptom_typeが"insomnia"の場合、またはtriage_resultのsubcategoryが"insomnia"の場合、または不眠関連キーワードが検出された場合に送信
                    is_insomnia_counseling = (
                        symptom_type == "insomnia" or 
                        triage_result.get("subcategory", "").lower() == "insomnia" or
                        "insomnia" in triage_result.get("subcategory", "").lower() or
                        has_insomnia_keyword
                    )
                    if is_insomnia_counseling:
                        # 不眠カウンセリングであることを確実にするため、symptom_typeを強制的に"insomnia"に設定
                        if symptom_type != "insomnia":
                            symptom_type = "insomnia"
                            # カウンセリングモードのsymptom_typeも更新
                            if session.get('counseling_mode'):
                                session['counseling_mode']['symptom_type'] = "insomnia"
                            logger.info(f"🔄 不眠関連キーワード検出により、symptom_typeを'insomnia'に変更しました")
                            
                        # 既に同じメッセージが存在するかチェック（重複防止）
                        medicine_info_message = "一時的な不眠で、推奨される医薬品を知りたい場合は教えて下さい。"
                        existing_medicine_info = False
                        for msg in session.get('messages', []):
                            if (msg.get('type') == 'bot' and 
                                msg.get('counseling_medicine_info') and 
                                msg.get('content') == medicine_info_message):
                                existing_medicine_info = True
                                logger.info(f"⏭️ 既に医薬品情報メッセージが存在するため、追加をスキップします")
                                break
                            
                        if not existing_medicine_info:
                            medicine_info_response = {
                                'type': 'bot',
                                'content': medicine_info_message,
                                'counseling': True,
                                'counseling_medicine_info': True,
                                'timestamp': datetime.now().isoformat()
                            }
                            session['messages'].append(medicine_info_response)
                            session.modified = True  # セッション変更を明示的に設定
                                
                            # 医薬品情報メッセージのログ記録（通常時は会話履歴なし）
                            log_counseling_response(
                                session_id=sid,
                                response_content=medicine_info_message,
                                response_type="counseling_medicine_info",
                                category=category,
                                confidence=confidence,
                                counseling_mode=session.get('counseling_mode'),
                                user_input=user_message,
                                conversation_history=None
                            )
                                
                            logger.info(f"✅ 不眠カウンセリング開始: 医薬品情報メッセージを送信しました (symptom_type={symptom_type}, subcategory={triage_result.get('subcategory', 'N/A')})")
                        else:
                            logger.info(f"✅ 不眠カウンセリング開始: 医薬品情報メッセージは既に存在します (symptom_type={symptom_type}, subcategory={triage_result.get('subcategory', 'N/A')})")
                        
                    # 眠気カウンセリングの場合、「眠気で、推奨される医薬品を知りたい場合は教えて下さい。」というメッセージを別途送信
                    # symptom_typeが"drowsiness"の場合、またはtriage_resultのsubcategoryが"drowsiness"の場合、または眠気関連キーワードが検出された場合に送信
                    is_sleepiness_counseling = (
                        symptom_type == "drowsiness" or 
                        triage_result.get("subcategory", "").lower() == "drowsiness" or
                        "drowsiness" in triage_result.get("subcategory", "").lower() or
                        has_sleepiness_keyword
                    )
                    if is_sleepiness_counseling:
                        # 眠気カウンセリングであることを確実にするため、symptom_typeを強制的に"drowsiness"に設定
                        if symptom_type != "drowsiness":
                            symptom_type = "drowsiness"
                            # カウンセリングモードのsymptom_typeも更新
                            if session.get('counseling_mode'):
                                session['counseling_mode']['symptom_type'] = "drowsiness"
                            logger.info(f"🔄 眠気関連キーワード検出により、symptom_typeを'drowsiness'に変更しました")
                            
                        # 既に同じメッセージが存在するかチェック（重複防止）
                        medicine_info_message = "眠気で、推奨される医薬品を知りたい場合は教えて下さい。"
                        existing_medicine_info = False
                        for msg in session.get('messages', []):
                            if (msg.get('type') == 'bot' and 
                                msg.get('counseling_medicine_info') and 
                                msg.get('content') == medicine_info_message):
                                existing_medicine_info = True
                                logger.info(f"⏭️ 既に医薬品情報メッセージが存在するため、追加をスキップします")
                                break
                            
                        if not existing_medicine_info:
                            medicine_info_response = {
                                'type': 'bot',
                                'content': medicine_info_message,
                                'counseling': True,
                                'counseling_medicine_info': True,
                                'timestamp': datetime.now().isoformat()
                            }
                            session['messages'].append(medicine_info_response)
                            session.modified = True  # セッション変更を明示的に設定
                                
                            # 医薬品情報メッセージのログ記録（通常時は会話履歴なし）
                            log_counseling_response(
                                session_id=sid,
                                response_content=medicine_info_message,
                                response_type="counseling_medicine_info",
                                category=category,
                                confidence=confidence,
                                counseling_mode=session.get('counseling_mode'),
                                user_input=user_message,
                                conversation_history=None
                            )
                            logger.info(f"✅ 眠気カウンセリング開始: 医薬品情報メッセージを送信しました (symptom_type={symptom_type}, subcategory={triage_result.get('subcategory', 'N/A')})")
                        else:
                            logger.info(f"✅ 眠気カウンセリング開始: 医薬品情報メッセージは既に存在します (symptom_type={symptom_type}, subcategory={triage_result.get('subcategory', 'N/A')})")
                        
                    if initial_questions:
                        first_question = initial_questions[0]
                        # 質問履歴に追加
                        session['counseling_mode']['question_history'].append({
                            'question': first_question,
                            'asked_at': datetime.now().isoformat(),
                            'question_type': 'initial'
                        })
                            
                        question_response = {
                            'type': 'bot',
                            'content': first_question,
                            'counseling': True,
                            'counseling_question': True,
                            'timestamp': datetime.now().isoformat()
                        }
                        session['messages'].append(question_response)
                            
                        # 初期質問のログ記録
                        log_counseling_response(
                            session_id=sid,
                            response_content=first_question,
                            response_type="counseling_initial_question",
                            category=category,
                            confidence=confidence,
                            counseling_mode=session.get('counseling_mode')
                        )
                        
                    session.modified = True
                        
                    # DBを更新
                    if sid:
                        session_data = get_session_from_db(sid)
                        if session_data:
                            session_data['messages'] = session['messages'].copy()
                            session_data['last_activity'] = datetime.now()
                            session_data['counseling_mode'] = session['counseling_mode']
                            save_session_to_db(sid, session_data)
                        
                    message_count = len(session['messages'])
                    logger.info(f"✅ カウンセリングフロー開始: {message_count} messages")
                    return jsonify({'status': 'ok', 'message_count': message_count})
                        
                except ImportError as e:
                    logger.warning(f"⚠️ カウンセリングフロー機能のインポートに失敗: {e}")
                except Exception as e:
                    logger.error(f"❌ カウンセリングフロー機能でエラー: {e}")
                    import traceback
                    traceback.print_exc()
                
            elif category == 'Physical':
                # Physicalカテゴリの場合は従来の薬推奨フローへ
                # 不眠カウンセリングから薬推奨への切り替えの場合
                if session.get('insomnia_medicine_recommendation'):
                    # 不眠の薬推奨フローを実行
                    user_text_for_recommendation = session.get('insomnia_user_text', '一時的な不眠')
                    # フラグをクリア
                    session.pop('insomnia_medicine_recommendation', None)
                    session.pop('insomnia_user_text', None)
                    session.modified = True
                        
                    # 不眠の症状で薬推奨を実行（後続処理で実行される）
                    # ここではユーザーメッセージを「一時的な不眠」に置き換えて処理を継続
                    sanitized_message = user_text_for_recommendation
                    user_message = user_text_for_recommendation  # user_messageも更新
                    # 症状入力として処理されるように設定
                    is_question = False
                    logger.info(f"✅ 不眠の薬推奨フローに移行: {user_text_for_recommendation}")
                # 眠気カウンセリングから薬推奨への切り替えの場合
                elif session.get('sleepiness_medicine_recommendation'):
                    # 眠気の薬推奨フローを実行
                    user_text_for_recommendation = session.get('sleepiness_user_text', '日中の眠気')
                    # フラグをクリア
                    session.pop('sleepiness_medicine_recommendation', None)
                    session.pop('sleepiness_user_text', None)
                    session.modified = True
                        
                    # 眠気の症状で薬推奨を実行（後続処理で実行される）
                    # ここではユーザーメッセージを「眠気」に置き換えて処理を継続
                    sanitized_message = user_text_for_recommendation
                    user_message = user_text_for_recommendation  # user_messageも更新
                    # 症状入力として処理されるように設定
                    is_question = False
                    logger.info(f"✅ 眠気の薬推奨フローに移行: {user_text_for_recommendation}")
                # （既存の処理を継続）
                pass
                
            elif category == 'Ask':
                # 医薬品質問フロー
                # カウンセリングモード中または直後に「薬を知りたい」という回答が来た場合、不眠・眠気の薬推奨として処理
                counseling_mode_check = session.get('counseling_mode', {})
                is_insomnia_medicine_request = False
                is_sleepiness_medicine_request = False
                    
                # 直前のメッセージを確認（カウンセリングモードが終了していても確認）
                messages = session.get('messages', [])
                if messages:
                    # 直前のbotメッセージを確認
                    for msg in reversed(messages[-5:]):  # 直近5件を確認
                        if msg.get('type') == 'bot' and msg.get('counseling_medicine_info'):
                            # カウンセリングモードのsymptom_typeを確認
                            symptom_type_in_msg = counseling_mode_check.get('symptom_type', '')
                            if symptom_type_in_msg == 'insomnia' or '不眠' in msg.get('content', ''):
                                # 「一時的な不眠で、推奨される医薬品を知りたい場合は教えて下さい。」に対する回答
                                is_insomnia_medicine_request = True
                                logger.info(f"✅ 不眠カウンセリング関連の薬推奨リクエストを検出: {sanitized_message}")
                                break
                            elif symptom_type_in_msg == 'drowsiness' or '眠気' in msg.get('content', ''):
                                # 眠気カウンセリング関連の薬推奨リクエスト
                                is_sleepiness_medicine_request = True
                                logger.info(f"✅ 眠気カウンセリング関連の薬推奨リクエストを検出: {sanitized_message}")
                                break
                    
                # カウンセリングモード中または直前のメッセージが医薬品情報メッセージの場合
                if (counseling_mode_check.get('active') and counseling_mode_check.get('symptom_type') == 'insomnia') or is_insomnia_medicine_request:
                    # 不眠の薬推奨フローに移行
                    logger.info(f"✅ 不眠カウンセリング関連の薬推奨フローに移行: {sanitized_message}")
                        
                    # カウンセリングモードを終了
                    if counseling_mode_check.get('active'):
                        counseling_mode_check['active'] = False
                        session['counseling_mode'] = counseling_mode_check
                        session.modified = True
                        
                    # 不眠の症状で薬推奨フローを実行
                    # トリアージ結果をPhysicalカテゴリに変更
                    if triage_result:
                        triage_result['category'] = 'Physical'
                        triage_result['subcategory'] = 'insomnia'
                        triage_result['reasoning'] = '不眠カウンセリングから薬推奨への切り替え'
                        
                    # ユーザーメッセージを「一時的な不眠」に置き換えて処理を継続（3文字以上の要件を満たすため）
                    sanitized_message = '一時的な不眠'
                    user_message = '一時的な不眠'  # user_messageも更新
                    category = 'Physical'
                    # 症状入力として処理されるように設定
                    is_question = False
                    # should_handle_other_categoryフラグをクリア（薬推奨フローに移行するため）
                    session.pop('should_handle_other_category', None)
                    logger.info(f"✅ カテゴリをPhysicalに変更して薬推奨フローへ: {sanitized_message}")
                elif (counseling_mode_check.get('active') and counseling_mode_check.get('symptom_type') == 'drowsiness') or is_sleepiness_medicine_request:
                    # 眠気の薬推奨フローに移行
                    logger.info(f"✅ 眠気カウンセリング関連の薬推奨フローに移行: {sanitized_message}")
                        
                    # カウンセリングモードを終了
                    if counseling_mode_check.get('active'):
                        counseling_mode_check['active'] = False
                        session['counseling_mode'] = counseling_mode_check
                        session.modified = True
                        
                    # 眠気の症状で薬推奨フローを実行
                    # トリアージ結果をPhysicalカテゴリに変更
                    if triage_result:
                        triage_result['category'] = 'Physical'
                        triage_result['subcategory'] = 'drowsiness'
                        triage_result['reasoning'] = '眠気カウンセリングから薬推奨への切り替え'
                        
                    # ユーザーメッセージを「日中の眠気」に置き換えて処理を継続（3文字以上の要件を満たすため）
                    sanitized_message = '日中の眠気'
                    user_message = '日中の眠気'  # user_messageも更新
                    category = 'Physical'
                    # 症状入力として処理されるように設定
                    is_question = False
                    # should_handle_other_categoryフラグをクリア（薬推奨フローに移行するため）
                    session.pop('should_handle_other_category', None)
                    logger.info(f"✅ カテゴリをPhysicalに変更して薬推奨フローへ: {sanitized_message}")
                    
                # 睡眠薬関連の質問の場合は不眠カウンセリングにリダイレクト
                sleep_medicine_keywords = [
                    "睡眠薬", "睡眠薬を", "睡眠薬について", "睡眠薬を教えて", "睡眠薬を知りたい",
                    "睡眠改善薬", "睡眠改善薬を", "睡眠改善薬について", "睡眠改善薬を教えて"
                ]
                if any(keyword in sanitized_message for keyword in sleep_medicine_keywords):
                    # 不眠カウンセリングフローにリダイレクト
                    try:
                        from src.services.counseling_response import (
                            detect_emotional_symptom_type,
                            generate_counseling_response,
                            generate_follow_up_questions,
                            start_counseling_mode
                        )
                            
                        # トリアージ結果を修正してEmotionalカテゴリとして扱う
                        triage_result['category'] = 'Emotional'
                        triage_result['subcategory'] = 'insomnia'
                            
                        symptom_type = "insomnia"
                            
                        # 会話履歴を取得（直近10件）
                        conversation_history = session.get('messages', [])[-10:] if len(session.get('messages', [])) > 10 else session.get('messages', [])
                            
                        initial_response = generate_counseling_response(
                            symptom_type, sanitized_message, recommendation_client,
                            conversation_history=conversation_history,
                            session_id=sid
                        )
                        initial_questions = generate_follow_up_questions(
                            symptom_type, {}, recommendation_client
                        )
                            
                        # カウンセリングモードを開始
                        start_counseling_mode(session, symptom_type, initial_questions)
                            
                        # 初期応答を送信
                        bot_response = {
                            'type': 'bot',
                            'content': initial_response,
                            'counseling': True,
                            'timestamp': datetime.now().isoformat()
                        }
                        session['messages'].append(bot_response)
                            
                        # 初期返信のログ記録
                        from src.services.counseling_response import log_counseling_response
                        log_counseling_response(
                            session_id=sid,
                            response_content=initial_response,
                            response_type="counseling_initial_response",
                            category='Emotional',
                            confidence=confidence,
                            counseling_mode=session.get('counseling_mode')
                        )
                            
                        # 不眠カウンセリングの場合、「一時的な不眠で、推奨される医薬品を知りたい場合は教えて下さい。」というメッセージを別途送信
                        # symptom_typeが"insomnia"の場合、またはtriage_resultのsubcategoryが"insomnia"の場合、または不眠関連キーワードが検出された場合に送信
                        # Askカテゴリからリダイレクトされた場合は、必ず不眠カウンセリングなので、常に送信
                        is_insomnia_counseling = (
                            symptom_type == "insomnia" or 
                            triage_result.get("subcategory", "").lower() == "insomnia" or
                            "insomnia" in triage_result.get("subcategory", "").lower() or
                            has_insomnia_keyword
                        )
                        if is_insomnia_counseling:
                            # 不眠カウンセリングであることを確実にするため、symptom_typeを強制的に"insomnia"に設定
                            if symptom_type != "insomnia":
                                symptom_type = "insomnia"
                                # カウンセリングモードのsymptom_typeも更新
                                if session.get('counseling_mode'):
                                    session['counseling_mode']['symptom_type'] = "insomnia"
                                logger.info(f"🔄 不眠関連キーワード検出により、symptom_typeを'insomnia'に変更しました（Askカテゴリから）")
                                
                            # 既に同じメッセージが存在するかチェック（重複防止）
                            medicine_info_message = "一時的な不眠で、推奨される医薬品を知りたい場合は教えて下さい。"
                            existing_medicine_info = False
                            for msg in session.get('messages', []):
                                if (msg.get('type') == 'bot' and 
                                    msg.get('counseling_medicine_info') and 
                                    msg.get('content') == medicine_info_message):
                                    existing_medicine_info = True
                                    logger.info(f"⏭️ 既に医薬品情報メッセージが存在するため、追加をスキップします（Askカテゴリから）")
                                    break
                                
                            if not existing_medicine_info:
                                medicine_info_response = {
                                    'type': 'bot',
                                    'content': medicine_info_message,
                                    'counseling': True,
                                    'counseling_medicine_info': True,
                                    'timestamp': datetime.now().isoformat()
                                }
                                session['messages'].append(medicine_info_response)
                                session.modified = True  # セッション変更を明示的に設定
                                    
                                # 医薬品情報メッセージのログ記録
                                log_counseling_response(
                                    session_id=sid,
                                    response_content=medicine_info_message,
                                    response_type="counseling_medicine_info",
                                    category='Emotional',
                                    confidence=confidence,
                                    counseling_mode=session.get('counseling_mode')
                                )
                                    
                                logger.info(f"✅ 不眠カウンセリング開始（Askカテゴリから）: 医薬品情報メッセージを送信しました (symptom_type={symptom_type}, subcategory={triage_result.get('subcategory', 'N/A')})")
                            else:
                                logger.info(f"✅ 不眠カウンセリング開始（Askカテゴリから）: 医薬品情報メッセージは既に存在します (symptom_type={symptom_type}, subcategory={triage_result.get('subcategory', 'N/A')})")
                            
                        if initial_questions:
                            first_question = initial_questions[0]
                            # 質問履歴に追加
                            session['counseling_mode']['question_history'].append({
                                'question': first_question,
                                'asked_at': datetime.now().isoformat(),
                                'question_type': 'initial'
                            })
                                
                            question_response = {
                                'type': 'bot',
                                'content': first_question,
                                'counseling': True,
                                'counseling_question': True,
                                'timestamp': datetime.now().isoformat()
                            }
                            session['messages'].append(question_response)
                                
                            # 初期質問のログ記録
                            log_counseling_response(
                                session_id=sid,
                                response_content=first_question,
                                response_type="counseling_initial_question",
                                category='Emotional',
                                confidence=confidence,
                                counseling_mode=session.get('counseling_mode')
                            )
                            
                        session.modified = True
                            
                        # DBを更新
                        if sid:
                            session_data = get_session_from_db(sid)
                            if session_data:
                                session_data['messages'] = session['messages'].copy()
                                session_data['last_activity'] = datetime.now()
                                session_data['counseling_mode'] = session['counseling_mode']
                                save_session_to_db(sid, session_data)
                            
                        message_count = len(session['messages'])
                        logger.info(f"✅ 睡眠薬質問から不眠カウンセリングフロー開始: {message_count} messages")
                        return jsonify({'status': 'ok', 'message_count': message_count})
                            
                    except ImportError as e:
                        logger.warning(f"⚠️ カウンセリングフロー機能のインポートに失敗: {e}")
                    except Exception as e:
                        logger.error(f"❌ 睡眠薬質問から不眠カウンセリングフローへのリダイレクトでエラー: {e}")
                        import traceback
                        traceback.print_exc()
                    
                # その他の医薬品質問フロー
                # （既存の処理を継続）
                pass
                
            elif category == 'Other':
                # 汎用応答フロー
                # （既存の処理を継続）
                pass
            
        # 「終了」ワード検知（サニタイズされたメッセージでチェック）
        if sanitized_message in ['終了', 'end', 'おわり', '終わり', 'quit', 'exit']:
            logger.info(f"🔚 CHAT ENDED by user: {session.get('username', 'unknown')}")
            session.modified = True
            bot_response = {
                'type': 'bot',
                'content': 'チャットを終了しました。不明点がございましたら、お気軽にお近くの登録販売者にご相談ください。',
                'diagnosis': None,
                'chat_ended': True
            }
            session['messages'].append(bot_response)
            # DBを更新（チャット終了フラグを設定）
            if sid:
                session_data = get_session_from_db(sid)
                if session_data:
                    session_data['messages'] = session['messages'].copy()
                    session_data['last_activity'] = datetime.now()
                    session_data['session_active'] = False  # チャット終了フラグ
                    save_session_to_db(sid, session_data)
            message_count = len(session['messages'])
            logger.info(f"✅ POST処理完了（チャット終了） - JSON返却: {message_count} messages")
            return jsonify({'status': 'ok', 'message_count': message_count})
            
        # ユーザーメッセージを追加（AI自動応答ON/OFF問わず）
        if 'messages' not in session:
            session['messages'] = []
            
        from datetime import datetime
        import uuid
            
        # 重複チェック：同じ内容のユーザーメッセージが既に存在するかチェック
        user_message_exists = any(
            msg.get('type') == 'user' and 
            msg.get('content') == original_user_message and
            msg.get('uuid')  # UUIDが存在する場合は既存メッセージ
            for msg in session.get('messages', [])
        )
            
        if not user_message_exists:
            session['messages'].append({
                'type': 'user',
                'content': original_user_message,  # 元のユーザーメッセージを表示（方言変換前）
                'timestamp': datetime.now().isoformat(),  # タイムスタンプを追加
                'uuid': str(uuid.uuid4())  # 一意な識別子を追加（将来のtemp_idフローに統合可能）
            })
            logger.info(f"✅ ユーザーメッセージ追加: {original_user_message[:50]}...")
        else:
            logger.info(f"⏭️ 重複ユーザーメッセージをスキップ: {sanitized_message[:50]}...")
        # 管理画面表示用にDBへも即時反映（ユーザーメッセージが見えるように）
        if sid:
            session_data = get_session_from_db(sid)
            if not session_data:
                session_data = {
                    'session_id': sid,
                    'username': session.get('username', 'Unknown'),
                    'messages': session['messages'].copy(),
                    'last_activity': datetime.now(),
                    'client_ip': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', ''),
                    'user_attributes': session.get('user_attributes', {}),
                    'session_active': True
                }
                save_session_to_db(sid, session_data)
            else:
                # 医薬品相談回答処理中は即時反映を完全にスキップ（重複を根本的に防止）
                if not session.get('is_medicine_consultation', False):
                    # 既存のDBメッセージと重複チェック
                    existing_messages = session_data.get('messages', [])
                    new_user_messages = [msg for msg in session['messages'] if msg.get('type') == 'user']
                        
                    # 新しいユーザーメッセージのみを追加
                    for new_msg in new_user_messages:
                        if not any(
                            existing_msg.get('type') == 'user' and 
                            existing_msg.get('content') == new_msg.get('content') and
                            existing_msg.get('uuid') == new_msg.get('uuid')
                            for existing_msg in existing_messages
                        ):
                            existing_messages.append(new_msg)
                        
                    session_data['messages'] = existing_messages
                    session_data['last_activity'] = datetime.now()
                    save_session_to_db(sid, session_data)
                else:
                    logger.info(f"📝 医薬品相談回答処理中のため、DB即時反映を完全にスキップ")
            
        # AI自動応答がONの場合の通常処理（ai_auto_replyチェックはLLMトリアージの前で実行済み）
        # ステップ1.8.5の続き: 店舗案内ではないと判定された場合、既存のOtherカテゴリの汎用応答処理（自己紹介、挨拶など）を実行
        should_handle_other_category = session.get('should_handle_other_category', False)
        # フラグが設定されている場合は、is_questionをTrueに固定（後続処理で変更されないようにする）
        force_question_mode = should_handle_other_category
        if should_handle_other_category:
            session['should_handle_other_category'] = False  # フラグをリセット
            logger.info(f"🔍 既存のOtherカテゴリの汎用応答処理（自己紹介、挨拶など）を実行")
            # この処理は、後続の挨拶検出処理で実行される
            # 強制的に質問処理に進むようにする
            is_question = True
            logger.info(f"🔍 フラグ設定により、is_question=Trueに設定（固定）: {user_message}")
        else:
            # フラグが設定されていない場合のみ、通常の判定を実行
            is_question = None  # 未初期化状態
            
        # まず挨拶を検出（症状検出の前に実行）
        greeting_keywords = [
            'こんにちは', 'こんばんは', 'おはよう', 'おはようございます',
            'はじめまして', '初めまして', 'よろしく', 'よろしくお願いします',
            'お疲れ様', 'おつかれさま', 'おつかれ', 'ご苦労様',
            'さようなら', 'さよなら', 'バイバイ', 'またね',
            'ありがとう', 'ありがとうございます', 'どうも', 'どうもありがとう',
            'すみません', 'すいません', 'ごめんなさい', 'ごめん',
            'hello', 'hi', 'good morning', 'good evening', 'good night',
            'thanks', 'thank you', 'bye', 'goodbye'
        ]
            
        # 症状キーワード（is_symptom_input関数と同じリストを使用）
        symptom_keywords = [
            '痛い', '痛み', '熱', '発熱', '咳', '鼻水', '頭痛', '腹痛', '吐き気', '嘔吐', '下痢', '便秘',
            '痒い', 'かゆい', '腫れ', '炎症', '発疹', '湿疹', 'めまい', 'だるい', '倦怠感', '疲れ', '不調', '症状',
            '喉', 'のど', '胃', '腸', '目', '耳', '鼻', '皮膚', '関節', '筋肉', '肩こり', '腰痛', '風邪', 'インフルエンザ',
            '寒気', '寒気がする', '寒気がします', '寒気があります', '寒気があり', '寒気が',
            '痺れ', 'しびれ', 'むくみ', '倦怠', '倦怠感', 'だるさ'
        ]
            
        # 挨拶キーワードが含まれているかチェック
        has_greeting = any(greeting in user_message for greeting in greeting_keywords)
        # 症状キーワードが含まれているかチェック
        has_symptom = any(symptom in user_message for symptom in symptom_keywords)
            
        # 質問か症状入力かを判定（フラグが設定されていない場合のみ）
        if is_question is None:
            is_question = not is_symptom_input(user_message)
            logger.info(f"🔍 is_symptom_input判定結果: is_question={is_question}, user_message={user_message}")
        add_reanalysis_message = False  # 再分析メッセージフラグ
        original_user_message = None  # 元のユーザーメッセージ
            
        # 挨拶のみで症状キーワードが含まれていない場合は質問処理に進む（フラグが設定されていない場合のみ）
        if not force_question_mode and has_greeting and not has_symptom:
            is_question = True
            logger.info(f"🔍 挨拶検出により、is_question=Trueに設定: {user_message}")
            
        # フラグが設定されている場合は、is_questionをTrueに固定（後続処理で変更されないようにする）
        if force_question_mode:
            is_question = True
            logger.info(f"🔍 フラグ固定により、is_question=Trueに再設定: {user_message}")
            
        logger.info(f"🔍 is_question最終判定: is_question={is_question}, force_question_mode={force_question_mode}, user_message={user_message}")
        if is_question:
            # システム紹介質問を検出
            system_intro_keywords = ['あなたについて', 'あなたは', 'システムについて', 'どんなシステム', '何ができる', '機能', '自己紹介']
            is_system_intro = any(keyword in user_message for keyword in system_intro_keywords)
                
            # 医薬品名検索を検出
            medicine_search_keywords = ['の薬', '薬を', '医薬品', 'について教えて', 'を教えて', 'お勧め', 'おすすめ']
            is_medicine_search = any(keyword in user_message for keyword in medicine_search_keywords)
                
            # 質問かどうかを判定（質問キーワードがあるか確認）
            has_question_keyword = False
            question_keywords = [
                'ですか', 'でしょうか', 'ですか？', 'でしょうか？',
                'ますか', 'できますか', '利用できますか', '使用できますか', '使えますか',
                '飲めますか', '飲んでも大丈夫ですか', '使用しても大丈夫ですか', '利用しても大丈夫ですか',
                '服用できますか', '服用しても大丈夫ですか', '摂取できますか',
                'ドーピング', '禁止', '禁止物質', '違反', '大丈夫', '安全', '危険',
                '大会前', '競技', 'レース', '試合前', '試合で', 'アンチドーピング', '陽性',
                '当たる', '当たります', '対象', '含まれる', '使える',
                '副作用', '飲み方', '効果', '効き目',
                '教えて', '教えてください', '知りたい', '聞きたい'
            ]
            question_suffixes = [
                'ですか', 'でしょうか', 'ますか', 'できますか', '利用できますか',
                '使用できますか', '使えますか', '飲めますか', '飲んでも大丈夫ですか',
                '使用しても大丈夫ですか', '利用しても大丈夫ですか', '服用できますか',
                '服用しても大丈夫ですか', '摂取できますか'
            ]
            message_stripped = user_message.strip()
            has_question_suffix = any(message_stripped.endswith(suffix) for suffix in question_suffixes)
            ends_with_question_mark = message_stripped.endswith('?') or message_stripped.endswith('？')
            for keyword in question_keywords:
                if keyword in user_message:
                    has_question_keyword = True
                    break
                
            # 挨拶のみの場合は挨拶への返答を生成
            if has_greeting and not has_symptom and not (is_system_intro or is_medicine_search or has_question_keyword or
                has_question_suffix or ends_with_question_mark):
                logger.info(f"👋 GREETING DETECTED: {user_message}")
                    
                # 挨拶への返答を生成
                greeting_responses = {
                    'こんにちは': 'こんには！どのような症状でお困りですか？具体的な症状を教えていただければ、適切な市販薬をご提案いたします。',
                    'こんばんは': 'こんばんは！どのような症状でお困りですか？具体的な症状を教えていただければ、適切な市販薬をご提案いたします。',
                    'おはよう': 'おはようございます！どのような症状でお困りですか？具体的な症状を教えていただければ、適切な市販薬をご提案いたします。',
                    'おはようございます': 'おはようございます！どのような症状でお困りですか？具体的な症状を教えていただければ、適切な市販薬をご提案いたします。',
                    'はじめまして': 'はじめまして！医薬品相談ツールです。どのような症状でお困りですか？具体的な症状を教えていただければ、適切な市販薬をご提案いたします。',
                    '初めまして': '初めまして！医薬品相談ツールです。どのような症状でお困りですか？具体的な症状を教えていただければ、適切な市販薬をご提案いたします。',
                    'よろしく': 'よろしくお願いします！どのような症状でお困りですか？具体的な症状を教えていただければ、適切な市販薬をご提案いたします。',
                    'よろしくお願いします': 'よろしくお願いします！どのような症状でお困りですか？具体的な症状を教えていただければ、適切な市販薬をご提案いたします。',
                    'ありがとう': 'どういたしまして！他にご質問や症状がございましたら、お気軽にお聞かせください。',
                    'ありがとうございます': 'どういたしまして！他にご質問や症状がございましたら、お気軽にお聞かせください。',
                    'どうも': 'どういたしまして！他にご質問や症状がございましたら、お気軽にお聞かせください。',
                    'どうもありがとう': 'どういたしまして！他にご質問や症状がございましたら、お気軽にお聞かせください。',
                    'hello': 'Hello! What symptoms are you experiencing? Please tell me your specific symptoms, and I will recommend appropriate over-the-counter medicines.',
                    'hi': 'Hi! What symptoms are you experiencing? Please tell me your specific symptoms, and I will recommend appropriate over-the-counter medicines.',
                    'thanks': "You're welcome! If you have any other questions or symptoms, please feel free to let me know.",
                    'thank you': "You're welcome! If you have any other questions or symptoms, please feel free to let me know."
                }
                    
                # 挨拶に応じた返答を選択（デフォルトは汎用挨拶）
                greeting_response = 'こんにちは！どのような症状でお困りですか？具体的な症状を教えていただければ、適切な市販薬をご提案いたします。'
                for greeting_key, response in greeting_responses.items():
                    if greeting_key in user_message.lower():
                        greeting_response = response
                        break
                    
                bot_response = {
                    'type': 'bot',
                    'content': greeting_response,
                    'diagnosis': None
                }
                session['messages'].append(bot_response)
                session.modified = True
                    
                # DB保存処理
                if sid:
                    session_data = get_session_from_db(sid)
                    if not session_data:
                        session_data = {
                            'session_id': sid,
                            'username': session.get('username', 'Unknown'),
                            'messages': session['messages'].copy(),
                            'last_activity': datetime.now(),
                            'client_ip': request.remote_addr,
                            'user_agent': request.headers.get('User-Agent', ''),
                            'user_attributes': session.get('user_attributes', {}),
                            'session_active': True
                        }
                        save_session_to_db(sid, session_data)
                    else:
                        session_data['messages'] = session['messages'].copy()
                        session_data['last_activity'] = datetime.now()
                        save_session_to_db(sid, session_data)
                    
                message_count = len(session['messages'])
                logger.info(f"✅ POST処理完了（挨拶返答） - JSON返却: {message_count} messages")
                return jsonify({'status': 'ok', 'message_count': message_count})
                
            # システム紹介、医薬品検索、明確な質問、または語尾・記号から質問と判断できる場合は質問回答に進む
            if (is_system_intro or is_medicine_search or has_question_keyword or
                has_question_suffix or ends_with_question_mark):
                logger.info(f"❓ CLEAR QUESTION DETECTED: {user_message}")
                    
                # ユーザーメッセージは既に1回目の保存処理で保存済み（重複を避けるため削除）
                # import uuid
                # user_response = {
                #     'type': 'user',
                #     'content': user_message,
                #     'timestamp': datetime.now().isoformat(),
                #     'uuid': str(uuid.uuid4())  # 一意な識別子を追加
                # }
                # ALL_SESSIONS[sid]['messages'].append(user_response)
                # logger.info(f"💾 ユーザー質問を保存: {user_message}")
                    
                # 質問回答に直接進む
                try:
                    # 最新の推奨医薬品を取得
                    session_data_for_medicines = get_session_from_db(sid) if sid else {}
                    latest_recommended_medicines = []
                    for msg in reversed(session_data_for_medicines.get('messages', [])):
                        if msg.get('type') == 'bot' and msg.get('diagnosis'):
                            diagnosis = msg.get('diagnosis', {})
                            if diagnosis.get('recommended_medicines'):
                                latest_recommended_medicines = diagnosis.get('recommended_medicines', [])
                                break
                        
                    logger.info(f"📋 Latest recommended medicines: {len(latest_recommended_medicines)} items")
                        
                    # 会話履歴を取得
                    conversation_history = session_data_for_medicines.get('messages', [])[-10:]
                        
                    # ChatGPTに質問を送信
                    chat_response = chat_with_medicine_context(
                        user_message, 
                        conversation_history, 
                        latest_recommended_medicines
                    )
                        
                    # 医薬品質疑応答のログを記録
                    try:
                        from src.utils.structured_logger import log_medicine_question_detail
                        log_medicine_question_detail(
                            session_id=sid,
                            user_input=user_message,
                            response=chat_response.get('answer', '')
                        )
                    except Exception as e:
                        logger.warning(f"医薬品質疑応答ログ記録エラー: {e}")
                        
                    # 評価ボタン用のデータを準備
                    import json
                    import html
                        
                    # HTML整形用ヘルパー関数
                    def safe_format(text):
                        """テキストを安全にHTML表示用に整形"""
                        if not text:
                            return ""
                        # XSSリスクを防ぐためにエスケープしてから改行を変換
                        escaped = html.escape(text)
                        return escaped.replace("\n", "<br>")
                        
                    # 回答の全文を作成（全項目を含める）
                    answer_text = safe_format(chat_response.get('answer', '回答を取得できませんでした'))
                    medicine_details = safe_format(chat_response.get('medicine_details', ''))
                    interactions = safe_format(chat_response.get('interactions', ''))
                    doping_check = safe_format(chat_response.get('doping_check', ''))
                    side_effects = safe_format(chat_response.get('side_effects', ''))
                    consultation_advice = safe_format(chat_response.get('consultation_advice', ''))
                        
                    full_response_html = f"""
<div class="chat-response">
<h4>💬 医薬品相談回答</h4>
<p><strong>回答:</strong><br>{answer_text}</p>
    
{f'<div style="margin-top: 15px; padding: 10px; background: #e3f2fd; border-radius: 5px;"><strong>💊 医薬品の詳細:</strong><br>{medicine_details}</div>' if medicine_details else ''}
    
{f'<div style="margin-top: 15px; padding: 10px; background: #fff3e0; border-radius: 5px;"><strong>⚠️ 相互作用の注意:</strong><br>{interactions}</div>' if interactions else ''}
    
{f'<div style="margin-top: 15px; padding: 10px; background: #ffebee; border-radius: 5px;"><strong>🏃 ドーピングチェック:</strong><br>{doping_check}</div>' if doping_check else ''}
    
{f'<div style="margin-top: 15px; padding: 10px; background: #fce4ec; border-radius: 5px;"><strong>⚕️ 副作用情報:</strong><br>{side_effects}</div>' if side_effects else ''}
    
{f'<div style="margin-top: 15px; padding: 10px; background: #f1f8e9; border-radius: 5px;"><strong>🩺 相談アドバイス:</strong><br>{consultation_advice}</div>' if consultation_advice else ''}
</div>"""
                        
                    # デバッグログ：ChatGPT応答の内容確認
                    logger.info("-" * 40)
                    logger.info(f"[DEBUG] ChatGPT response fields:")
                    logger.info(f"  - answer: {'✓' if answer_text else '✗'} ({len(answer_text) if answer_text else 0} chars)")
                    logger.info(f"  - medicine_details: {'✓' if medicine_details else '✗'} ({len(medicine_details) if medicine_details else 0} chars)")
                    logger.info(f"  - interactions: {'✓' if interactions else '✗'} ({len(interactions) if interactions else 0} chars)")
                    logger.info(f"  - doping_check: {'✓' if doping_check else '✗'} ({len(doping_check) if doping_check else 0} chars)")
                    logger.info(f"  - side_effects: {'✓' if side_effects else '✗'} ({len(side_effects) if side_effects else 0} chars)")
                    logger.info(f"  - consultation_advice: {'✓' if consultation_advice else '✗'} ({len(consultation_advice) if consultation_advice else 0} chars)")
                        
                    # デバッグログ：HTML構造の整合性確認
                    opening_divs = full_response_html.count('<div')
                    closing_divs = full_response_html.count('</div>')
                    logger.info(f"[DEBUG] HTML structure: {opening_divs} opening divs, {closing_divs} closing divs {'✓' if opening_divs == closing_divs else '✗ MISMATCH'}")
                    logger.info("-" * 40)
                        
                    # メッセージIDを生成
                    message_id = f"msg_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
                    logger.info(f"[DEBUG] Generated message_id: {message_id}")
                        
                    # [SECURITY NOTE]: full_response_html is generated only from safe, pre-sanitized templates.
                    # All user input is escaped via safe_format (html.escape + newline conversion).
                    # Do not re-escape, otherwise structured HTML (icons, sections) will break.
                        
                    # 評価ボタンを追加（メッセージIDベース方式）
                    bot_content = full_response_html + f"""
<div class="feedback-buttons" style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6;">
<p style="margin: 0 0 10px 0; font-weight: bold; color: #495057;">この回答はいかがでしたか？</p>
<button class="feedback-btn-positive" onclick="handlePositiveFeedback('{message_id}')" style="background: #28a745; color: white; border: none; padding: 8px 16px; margin-right: 10px; border-radius: 4px; cursor: pointer; font-size: 14px; min-width: 80px;">
    適切
</button>
<button class="feedback-btn-negative" onclick="handleNegativeFeedback('{message_id}')" style="background: #dc3545; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px; min-width: 80px;">
    不適切
</button>
</div>"""
                        
                    bot_response = {
                        'type': 'bot',
                        'content': bot_content,
                        'message_id': message_id,
                        'diagnosis': {
                            'chat_response': chat_response,
                            'is_question': True
                        },
                        'timestamp': datetime.now().isoformat()
                    }
                        
                    # 質問応答をDBに保存
                    if sid:
                        session_data = get_session_from_db(sid)
                        if not session_data:
                            session_data = {
                                'session_id': sid,
                                'username': session.get('username', 'Unknown'),
                                'messages': [],
                                'last_activity': datetime.now(),
                                'client_ip': request.remote_addr,
                                'user_agent': request.headers.get('User-Agent', ''),
                                'user_attributes': session.get('user_attributes', {}),
                                'session_active': True
                            }
                        if 'messages' not in session_data:
                            session_data['messages'] = []
                        session_data['messages'].append(bot_response)
                        session_data['last_activity'] = datetime.now()
                        save_session_to_db(sid, session_data)
                        
                    # セッションCookie肥大化を防ぐため、Flaskセッションからmessagesを削除
                    if 'messages' in session:
                        del session['messages']
                        session.modified = True
                    logger.info(f"✅ 質問応答完了: {user_message}")
                        
                    # 質問応答の場合は、user_attributesを初期化してセッションに保存
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
                    session['user_attributes'] = user_attributes
                    session.modified = True
                        
                    # JSONレスポンスを返す
                    updated_session = get_session_from_db(sid) if sid else {}
                    message_count = len(updated_session.get('messages', []))
                    return jsonify({'status': 'ok', 'message_count': message_count})
                        
                except Exception as e:
                    logger.error(f"❌ 医薬品相談機能実行時エラー: {e}", exc_info=True)
                    bot_response = {
                        'type': 'bot',
                        'content': "申し訳ございません。一時的にエラーが発生しました。しばらく時間をおいてもう一度お試しいただくか、症状を詳しく入力して再度ご相談ください。",
                        'diagnosis': None,
                        'timestamp': datetime.now().isoformat()
                    }
                        
                    # エラー応答をDBに保存
                    if sid:
                        session_data = get_session_from_db(sid)
                        if session_data:
                            if 'messages' not in session_data:
                                session_data['messages'] = []
                            session_data['messages'].append(bot_response)
                            session_data['last_activity'] = datetime.now()
                            save_session_to_db(sid, session_data)
                    # セッションCookie肥大化を防ぐため、Flaskセッションからmessagesを削除
                    if 'messages' in session:
                        del session['messages']
                        session.modified = True
                        
                    # エラーの場合もuser_attributesを初期化
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
                    session['user_attributes'] = user_attributes
                    session.modified = True
                        
                    # JSONレスポンスを返す
                    updated_session = get_session_from_db(sid) if sid else {}
                    message_count = len(updated_session.get('messages', []))
                    return jsonify({'status': 'ok', 'message_count': message_count})
            else:
                # 操作指示の検出（セキュリティ検証の後）
                if is_operation_command(user_message):
                    logger.info(f"🔄 操作指示を検出: {user_message}")
                        
                    # セッションから過去の症状文を取得
                    session_messages = session.get('messages', [])
                    previous_symptom_text = None
                        
                    # 過去のメッセージから症状文を探す（最初のユーザーメッセージ）
                    for msg in session_messages:
                        if msg.get('type') == 'user':
                            previous_symptom_text = msg.get('content', '')
                            break
                        
                    # 症状文が見つからない場合は、現在のメッセージを症状として扱う
                    if not previous_symptom_text:
                        previous_symptom_text = user_message
                        
                    # ユーザー属性情報を取得
                    user_attributes = session.get('user_attributes', {})
                        
                    # 推奨医薬品の再分析を実行
                    # 既存の医薬品推奨処理を再利用するため、user_messageを一時的にprevious_symptom_textに置き換える
                    original_user_message = user_message
                    user_message = previous_symptom_text
                    # sanitized_messageも更新（再分析用）
                    sanitized_message = previous_symptom_text
                        
                    # 再分析フラグを設定
                    session['is_reanalysis'] = True
                    is_question = False  # 症状分析を強制実行
                        
                    logger.info(f"🔄 再分析を実行: 症状文={previous_symptom_text[:50]}...")
                    
                # 属性応答の可能性がある場合のみ属性抽出を実行
                logger.info(f"❓ POSSIBLE ATTRIBUTE RESPONSE DETECTED: {user_message}")
                    
                # 言語を検出（すべての入力に対して実行）
                detected_language = detect_language(user_message)
                session['detected_language'] = detected_language
                logger.info(f"🌍 検出された言語: {detected_language}")
                    
                # 初回チャットで症状入力の場合は属性抽出をスキップして症状分析に進む
                if len(session.get('messages', [])) <= 1 and is_symptom_input(user_message):
                    logger.info(f"🔄 初回症状入力のため属性抽出をスキップして症状分析に進みます")
                    is_question = False  # 症状分析を強制実行
                else:
                    # ステップ1: 多言語対応ユーザー属性を抽出・更新
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
                        
                    # 多言語対応の属性抽出を実行（言語検出は既に上で実行済み）
                    try:
                        extracted_attrs = extract_user_attributes_multilingual(
                            user_message, 
                            client, 
                            user_attributes
                        )
                            
                        logger.info(f"🤖 多言語属性抽出結果: {extracted_attrs}")
                            
                        # 抽出された情報をセッションに保存
                        for key, value in extracted_attrs.items():
                            if value is not None and value != [] and value != "" and key != 'detected_language':
                                if key == 'age' and isinstance(value, (int, float)):
                                    user_attributes['age'] = int(value)
                                    logger.info(f"📝 年齢を更新: {user_attributes['age']}")
                                    updated = True
                                elif key == 'gender' and value in ['男性', '女性', 'Male', 'Female', '남성', '여성', '男性', '女性']:
                                    # 多言語の性別を日本語に統一
                                    if value in ['Male', '남성', '男性']:
                                        user_attributes['gender'] = '男性'
                                    elif value in ['Female', '여성', '女性']:
                                        user_attributes['gender'] = '女性'
                                    else:
                                        user_attributes['gender'] = value
                                    logger.info(f"📝 性別を更新: {user_attributes['gender']}")
                                    updated = True
                                elif key == 'pregnant' and isinstance(value, bool):
                                    user_attributes['pregnant'] = value
                                    logger.info(f"📝 妊娠状態を更新: {user_attributes['pregnant']}")
                                    updated = True
                                elif key == 'breastfeeding' and isinstance(value, bool):
                                    user_attributes['breastfeeding'] = value
                                    logger.info(f"📝 授乳状態を更新: {user_attributes['breastfeeding']}")
                                    updated = True
                                elif key == 'allergies' and isinstance(value, list):
                                    user_attributes['allergies'] = value
                                    logger.info(f"📝 アレルギーを更新: {user_attributes['allergies']}")
                                    updated = True
                                elif key == 'current_medications' and isinstance(value, list):
                                    user_attributes['current_medications'] = value
                                    logger.info(f"📝 服用中の薬を更新: {user_attributes['current_medications']}")
                                    updated = True
                                elif key == 'medical_history' and isinstance(value, list):
                                    user_attributes['medical_history'] = value
                                    logger.info(f"📝 既往症を更新: {user_attributes['medical_history']}")
                                    updated = True
                                elif key == 'symptom_duration_days' and isinstance(value, (int, float)):
                                    user_attributes['symptom_duration_days'] = int(value)
                                    logger.info(f"📝 症状期間を更新: {user_attributes['symptom_duration_days']}日")
                                    updated = True
                                elif key == 'other_info' and isinstance(value, str):
                                    # 薬に関する情報はother_infoに入れない（current_medicationsに反映される）
                                    medication_patterns = [
                                        r'他に服用.*薬.*(?:あり|なし|ありません|ない)',
                                        r'服用.*薬.*(?:あり|なし|ありません|ない)',
                                        r'薬.*服用.*(?:あり|なし|ありません|ない)',
                                        r'服用.*(?:あり|なし|ありません|ない)',
                                        r'薬.*(?:あり|なし|ありません|ない)',
                                        r'服用している薬.*(?:あり|なし|ありません|ない)',
                                        r'他に服用.*(?:あり|なし|ありません|ない)'
                                    ]
                                    is_medication_info = any(re.search(pattern, value, re.IGNORECASE) for pattern in medication_patterns)
                                        
                                    if not is_medication_info:
                                        user_attributes['other_info'] = value
                                        logger.info(f"📝 その他情報を更新: {user_attributes['other_info']}")
                                        updated = True
                                    else:
                                        logger.info(f"📝 薬に関する情報のためother_infoには設定しません: {value}")
                        
                    except Exception as e:
                        logger.error(f"多言語属性抽出エラー: {e}")
                        logger.info("フォールバック: 正規表現による抽出に切り替えます")
                            
                        # フォールバック: 正規表現による抽出
                            
                        # 年齢（日本語と英語）
                        age_match = re.search(r'(\d+)歳', user_message)
                        if age_match:
                            user_attributes['age'] = int(age_match.group(1))
                            logger.info(f"📝 年齢を更新: {user_attributes['age']}")
                            updated = True
                        else:
                            # 英語の年齢パターン
                            age_match_en = re.search(r'(\d+)\s*years?\s*old', user_message, re.IGNORECASE)
                            if age_match_en:
                                user_attributes['age'] = int(age_match_en.group(1))
                                logger.info(f"📝 年齢を更新: {user_attributes['age']}")
                                updated = True
                            
                        # 性別（日本語と英語）
                        if '男性' in user_message or '男' in user_message or 'male' in user_message.lower():
                            user_attributes['gender'] = '男性'
                            logger.info(f"📝 性別を更新: 男性")
                            updated = True
                        elif '女性' in user_message or '女' in user_message or 'female' in user_message.lower():
                            user_attributes['gender'] = '女性'
                            logger.info(f"📝 性別を更新: 女性")
                            updated = True
                            
                        # 妊娠・授乳（フォールバック処理）
                        if '妊娠' in user_message:
                            if any(kw in user_message for kw in ['妊娠していません', '妊娠中ではありません', '妊娠していない', '妊娠してない']):
                                user_attributes['pregnant'] = False
                                logger.info(f"📝 妊娠状態を更新: False（妊娠していない）")
                            elif any(kw in user_message for kw in ['妊娠中です', '妊娠中', '妊娠しています', '妊娠しました', '妊娠してます', '妊娠した', '妊婦です']):
                                user_attributes['pregnant'] = True
                                logger.info(f"📝 妊娠状態を更新: True（妊娠中）")
                            updated = True
                            
                        if '授乳' in user_message:
                            if '授乳していません' in user_message or '授乳中ではありません' in user_message or '授乳していない' in user_message:
                                user_attributes['breastfeeding'] = False
                                logger.info(f"📝 授乳状態を更新: False（授乳していない）")
                            elif '授乳中です' in user_message or '授乳中' in user_message or '授乳しています' in user_message:
                                user_attributes['breastfeeding'] = True
                                logger.info(f"📝 授乳状態を更新: True（授乳中）")
                            updated = True
                            
                        # アレルギー（日本語と英語）
                        if 'アレルギー' in user_message or 'allergy' in user_message.lower() or 'allergies' in user_message.lower():
                            if ('ない' in user_message or 'いいえ' in user_message or 'ありません' in user_message or 'なし' in user_message or 
                                'no allergy' in user_message.lower() or 'no allergies' in user_message.lower()):
                                user_attributes['allergies'] = ['なし']
                        else:
                            # 日本語のアレルギー抽出
                            allergens = re.findall(r'([ぁ-んァ-ヶー]+)アレルギー', user_message)
                            if allergens:
                                user_attributes['allergies'] = allergens
                            else:
                                # 英語のアレルギー抽出
                                allergy_match = re.search(r'have\s+([^,\s]+)\s+allergy', user_message, re.IGNORECASE)
                                if allergy_match:
                                    user_attributes['allergies'] = [allergy_match.group(1)]
                        logger.info(f"📝 アレルギーを更新: {user_attributes['allergies']}")
                        updated = True
                    updated = True
                    # 症状期間（日本語と英語）
                    if ('続いています' in user_message or 'から' in user_message or 
                            'started' in user_message.lower() or 'ago' in user_message.lower()):
                        duration_patterns = [
                            (r'(今日|きょう)から', 0),
                            (r'(昨日|きのう)から', 1),
                            (r'(\d+)日前から', None),
                            (r'(\d+)週間前から', None),
                            # 英語のパターン
                            (r'(\d+)\s*days?\s*ago', None),
                            (r'(\d+)\s*weeks?\s*ago', None),
                            (r'(\d+)\s*months?\s*ago', None)
                        ]
                        for pattern, days in duration_patterns:
                            match = re.search(pattern, user_message)
                            if match:
                                if days is not None:
                                    user_attributes['symptom_duration_days'] = days
                                else:
                                    # 数値を抽出
                                    if '日前' in user_message:
                                        num_match = re.search(r'(\d+)日前', user_message)
                                        if num_match:
                                            user_attributes['symptom_duration_days'] = int(num_match.group(1))
                                    elif '週間前' in user_message:
                                        num_match = re.search(r'(\d+)週間前', user_message)
                                        if num_match:
                                            user_attributes['symptom_duration_days'] = int(num_match.group(1)) * 7
                                    elif 'days ago' in user_message.lower():
                                        num_match = re.search(r'(\d+)\s*days?\s*ago', user_message, re.IGNORECASE)
                                        if num_match:
                                            user_attributes['symptom_duration_days'] = int(num_match.group(1))
                                    elif 'weeks ago' in user_message.lower():
                                        num_match = re.search(r'(\d+)\s*weeks?\s*ago', user_message, re.IGNORECASE)
                                        if num_match:
                                            user_attributes['symptom_duration_days'] = int(num_match.group(1)) * 7
                                    elif 'months ago' in user_message.lower():
                                        num_match = re.search(r'(\d+)\s*months?\s*ago', user_message, re.IGNORECASE)
                                        if num_match:
                                            user_attributes['symptom_duration_days'] = int(num_match.group(1)) * 30
                                logger.info(f"📝 症状期間を更新: {user_attributes.get('symptom_duration_days')}日前から")
                                updated = True
                                break
                
            # 服用中の薬（日本語と英語）
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
                user_attributes['current_medications'] = []
                logger.info(f"📝 服用中の薬なしを確認")
                updated = True
            elif not is_medication_search and ('服用している' in user_message or '飲んでいる' in user_message or 
                  'taking' in user_message.lower() or 'medication' in user_message.lower() or 'medicine' in user_message.lower()):
                # 薬の名前を抽出（日本語と英語）
                # 「服用している」「飲んでいる」などの明確な表現のみを対象
                medication_patterns = [
                    r'服用している薬[はが]?([^。、\n]+)',
                    r'飲んでいる薬[はが]?([^。、\n]+)',
                    r'服用している[はが]?([^。、\n]+)',
                    r'飲んでいる[はが]?([^。、\n]+)',
                    # 英語のパターン
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
                            if medication_name not in user_attributes['current_medications']:
                                user_attributes['current_medications'].append(medication_name)
                                logger.info(f"📝 服用中の薬を抽出: {medication_name}")
                                updated = True
                                break
                
            # 既往症の抽出（日本語と英語）
            if ('既往症' in user_message or '病気' in user_message or '疾患' in user_message or
                'history' in user_message.lower() or 'disease' in user_message.lower() or 'condition' in user_message.lower()):
                # 既往症のパターンを抽出
                history_patterns = [
                    r'既往症[はが]?([^。、\n]+)',
                    r'病気[はが]?([^。、\n]+)',
                    r'疾患[はが]?([^。、\n]+)',
                    r'([^。、\n]*病[^。、\n]*)',
                    # 英語のパターン
                    r'have\s+([^,\s]+(?:\s+[^,\s]+)*)\s+history',
                    r'history\s+of\s+([^,\n]+)',
                    r'disease[:\s]+([^,\n]+)',
                    r'condition[:\s]+([^,\n]+)'
                ]
                    
                for pattern in history_patterns:
                    match = re.search(pattern, user_message)
                    if match:
                        history_name = match.group(1).strip()
                        if history_name and history_name not in user_attributes['medical_history']:
                            user_attributes['medical_history'].append(history_name)
                            logger.info(f"📝 既往症を抽出: {history_name}")
                            updated = True
                            break
                
            # その他伝えたいことの抽出（日本語と英語）
            # 薬に関する情報（「他に服用している薬はありません」など）を除外
            medication_exclusion_patterns = [
                r'他に服用.*薬.*(?:あり|なし|ありません|ない)',
                r'服用.*薬.*(?:あり|なし|ありません|ない)',
                r'薬.*服用.*(?:あり|なし|ありません|ない)',
                r'服用.*(?:あり|なし|ありません|ない)',
                r'薬.*(?:あり|なし|ありません|ない)'
            ]
            is_medication_message = any(re.search(pattern, user_message, re.IGNORECASE) for pattern in medication_exclusion_patterns)
                
            if not is_medication_message and ('その他' in user_message or '伝えたい' in user_message or 
                'want to know' in user_message.lower() or 'ask about' in user_message.lower() or 'tell you' in user_message.lower()):
                # その他の情報を抽出（「他に」は薬に関する情報の可能性があるため除外）
                other_patterns = [
                    r'その他[はが]?([^。、\n]+)',
                    r'伝えたいこと[はが]?([^。、\n]+)',
                    # 英語のパターン
                    r'want to know about\s+([^,\n]+)',
                    r'ask about\s+([^,\n]+)',
                    r'tell you\s+([^,\n]+)'
                ]
                    
                for pattern in other_patterns:
                    match = re.search(pattern, user_message)
                    if match:
                        other_info = match.group(1).strip()
                        if other_info:
                            # 薬に関する情報はother_infoに入れない（current_medicationsに反映される）
                            medication_patterns = [
                                r'服用.*薬.*(?:あり|なし|ありません|ない)',
                                r'薬.*服用.*(?:あり|なし|ありません|ない)',
                                r'服用.*(?:あり|なし|ありません|ない)',
                                r'薬.*(?:あり|なし|ありません|ない)'
                            ]
                            is_medication_info = any(re.search(pattern, other_info, re.IGNORECASE) for pattern in medication_patterns)
                                
                            if not is_medication_info:
                                user_attributes['other_info'] = other_info
                                logger.info(f"📝 その他情報を抽出: {other_info}")
                                updated = True
                                break
                            else:
                                logger.info(f"📝 薬に関する情報のためother_infoには設定しません: {other_info}")
                                break
                
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
                
            # ステップ2: 属性が更新された場合の追加処理
            if updated:
                logger.info("✅ 属性データが更新されました。前回の症状に対して再推奨を実行します。")
                session.pop('is_reanalysis', None)
                session.pop('reanalysis_attributes', None)

                # 症状期間が7日を超える場合の医療機関受診案内をチェック
                symptom_duration = user_attributes.get('symptom_duration_days')
                if symptom_duration and symptom_duration > 7:
                    logger.info(f"⚠️ 症状期間が7日を超えています: {symptom_duration}日")
                        
                    # ユーザーメッセージをDBに保存（症状期間チェック前に保存）
                    if sid:
                        session_data = get_session_from_db(sid)
                        if session_data:
                            session_data['messages'] = session['messages'].copy()
                            session_data['last_activity'] = datetime.now()
                            save_session_to_db(sid, session_data)
                        logger.info(f"💾 ユーザーメッセージをDBに保存: {len(session['messages'])} messages")
                        
                    # 医療機関受診案内を追加
                    medical_advice = {
                        'type': 'bot',
                        'content': '⚠️ 症状が7日を超えている場合は、市販薬での対応が困難な可能性があります。医療機関（病院・クリニック）での受診をお勧めします。',
                        'medical_advice': True
                    }
                    if 'messages' not in session:
                        session['messages'] = []
                    session['messages'].append(medical_advice)
                    if sid:
                        session_data = get_session_from_db(sid)
                        if session_data:
                            if 'messages' not in session_data:
                                session_data['messages'] = []
                            session_data['messages'].append(medical_advice)
                            session_data['last_activity'] = datetime.now()
                            save_session_to_db(sid, session_data)
                        
                    # 症状期間が7日を超える場合は医薬品推奨を停止
                    logger.info(f"🚫 症状期間が7日を超えるため医薬品推奨を停止します")
                    session.modified = True
                    message_count = len(session['messages'])
                    return jsonify({'status': 'ok', 'message_count': message_count})
                    
                # 属性更新後、前回の症状メッセージを取得して再推奨を実行
                logger.info(f"🔄 属性更新後、前回の症状に対して再推奨を実行します")
                    
                # セッションから前回の症状メッセージを取得
                previous_symptom_message = None
                if sid:
                    session_data = get_session_from_db(sid)
                    if session_data:
                        messages = session_data.get('messages', [])
                        # ユーザーメッセージの中で症状を述べているものを逆順で検索
                        for msg in reversed(messages):
                            if msg.get('type') == 'user':
                                content = msg.get('content', '')
                                    
                                # 属性情報のみのメッセージを除外（年齢、性別、妊娠、授乳、アレルギー、薬などのみのメッセージ）
                                # 症状キーワードを含むかチェック
                                symptom_keywords = [
                                    '痛い', '痛み', '熱', '咳', '鼻水', '頭痛', '発熱', 'のど', '喉', '寒気', 'だるい', '疲れ',
                                    'かゆい', 'かゆみ', '痒い', '痒み', 'かぶれ', '発疹', '湿疹', 'じんましん',
                                    '下痢', '便秘', '腹痛', '胃痛', '吐き気', '嘔吐', '胸やけ', '胃もたれ',
                                    'めまい', '不眠', '肩こり', '腰痛', '関節痛', '筋肉痛',
                                    '生理', '月経', 'つわり', '更年期',
                                    '遅れ', '不順', '異常', '周期', '来ない', '来ていない'
                                ]
                                has_symptom_keyword = any(keyword in content for keyword in symptom_keywords)
                                    
                                # 属性情報のみのパターンをチェック
                                attribute_only_patterns = [
                                    r'^\d+歳です?[。.]?$',
                                    r'^(?:女性|男性|女|男)です?[。.]?$',
                                    r'^(?:妊娠|授乳|アレルギー|薬).*(?:です|ありません|なし)[。.]?$',
                                ]
                                is_attribute_only = False
                                for pattern in attribute_only_patterns:
                                    if re.match(pattern, content.strip()):
                                        is_attribute_only = True
                                        break
                                    
                                # 複数の属性情報のみが含まれている場合も除外
                                if not is_attribute_only and not has_symptom_keyword:
                                    attribute_count = 0
                                    if re.search(r'\d+歳', content):
                                        attribute_count += 1
                                    if re.search(r'(?:女性|男性|女|男)', content):
                                        attribute_count += 1
                                    if re.search(r'(?:妊娠|授乳)', content):
                                        attribute_count += 1
                                    if re.search(r'(?:アレルギー|薬)', content):
                                        attribute_count += 1
                                    # 属性情報が2つ以上で、症状キーワードが含まれていない場合は属性情報のみと判断
                                    if attribute_count >= 2:
                                        is_attribute_only = True
                                    
                                if is_attribute_only:
                                    logger.info(f"⏭️ 属性情報のみのメッセージをスキップ: {content[:50]}...")
                                    continue
                                    
                                # 症状キーワードを含むメッセージを探す
                                if has_symptom_keyword:
                                    previous_symptom_message = content
                                    logger.info(f"📋 前回の症状メッセージを取得: {content[:50]}...")
                                    break
                    
                # 前回の症状が見つかった場合、更新された属性情報で再推奨を実行
                if previous_symptom_message:
                    logger.info(f"💊 更新された属性情報で再推奨を開始: {previous_symptom_message[:50]}...")
                    # 症状メッセージとして扱うため、is_questionをFalseに設定
                    user_message = previous_symptom_message
                    is_question = False
                    # 医薬品相談処理を実行するためにフラグを設定
                    session['is_medicine_consultation'] = True
                    session['is_reanalysis_with_updated_attributes'] = True
                else:
                    # 前回の症状が見つからない場合、属性更新の確認メッセージのみ返す
                    logger.warning(f"⚠️ 前回の症状メッセージが見つかりません。属性更新の確認のみ返します。")
                    bot_response = {
                        'type': 'bot',
                        'content': f"✅ 属性情報を更新しました。\n\n年齢: {user_attributes.get('age', '未入力')}\n性別: {user_attributes.get('gender', '未入力')}\nアレルギー: {', '.join(user_attributes.get('allergies', [])) if user_attributes.get('allergies') else 'なし'}\n服用中の薬: {', '.join(user_attributes.get('current_medications', [])) if user_attributes.get('current_medications') else 'なし'}\n\n症状について教えていただければ、更新された情報をもとに適切な医薬品をご提案いたします。",
                        'diagnosis': None,
                        'attribute_update_confirmation': True
                    }
                        
                    # ユーザーメッセージをDBに保存
                    if sid:
                        session_data = get_session_from_db(sid)
                        if not session_data:
                            session_data = {
                                'session_id': sid,
                                'username': session.get('username', 'Unknown'),
                                'messages': [],
                                'last_activity': datetime.now(),
                                'client_ip': request.remote_addr,
                                'user_agent': request.headers.get('User-Agent', ''),
                                'user_attributes': user_attributes,
                                'session_active': True
                            }
                        if 'messages' not in session_data:
                            session_data['messages'] = []
                        session_data['messages'].append(bot_response)
                        session_data['last_activity'] = datetime.now()
                        save_session_to_db(sid, session_data)
                        logger.info(f"💾 属性更新確認メッセージを保存: {len(session_data.get('messages', []))} messages")
                        
                    # Cookieサイズ削減（メッセージはDBのみに保存）
                    if 'messages' in session:
                        del session['messages']
                        session.modified = True
                        logger.info(f"📝 Session cookie size reduced - messages only in DB")
                        
                    # セッションの他の大きなデータも最小限に
                    if sid:
                        session_data = get_session_from_db(sid)
                        if session_data:
                            session_data['last_activity'] = datetime.now()
                            save_session_to_db(sid, session_data)
                        
                    message_count = len(session_data.get('messages', [])) if sid and session_data else 0
                    logger.info(f"✅ POST処理完了 - 属性更新確認メッセージ返却: {message_count} messages")
                    return jsonify({'status': 'ok', 'message_count': message_count})
            else:
                # 属性が更新されていない場合は通常の質問応答
                logger.info(f"❓ 通常の質問として処理します")
                try:
                    # 最新の推奨医薬品を取得（DBを参照）
                    session_data_for_medicines2 = get_session_from_db(sid) if sid else {}
                    latest_recommended_medicines = []
                    for msg in reversed(session_data_for_medicines2.get('messages', [])):
                        if msg.get('type') == 'bot' and msg.get('diagnosis'):
                            diagnosis = msg.get('diagnosis', {})
                            if diagnosis.get('recommended_medicines'):
                                latest_recommended_medicines = diagnosis.get('recommended_medicines', [])
                                break

                    logger.info(f"📋 Latest recommended medicines: {len(latest_recommended_medicines)} items")

                    # 会話履歴を取得（DBから直近10件）
                    conversation_history = session_data_for_medicines2.get('messages', [])[-10:]

                    # ChatGPTに質問を送信
                    chat_response = chat_with_medicine_context(
                        user_message,
                        conversation_history,
                        latest_recommended_medicines
                    )
                        
                    # 医薬品質疑応答のログを記録
                    try:
                        from src.utils.structured_logger import log_medicine_question_detail
                        log_medicine_question_detail(
                            session_id=sid,
                            user_input=user_message,
                            response=chat_response.get('answer', '')
                        )
                    except Exception as e:
                        logger.warning(f"医薬品質疑応答ログ記録エラー: {e}")

                    # 医薬品相談回答の処理は既に上記で実装済み
                    # 重複コードを削除

                except Exception as e:
                    logger.error(f"❌ 医薬品相談機能実行時エラー: {e}", exc_info=True)
                    bot_response = {
                        'type': 'bot',
                        'content': "申し訳ございません。一時的にエラーが発生しました。しばらく時間をおいてもう一度お試しいただくか、症状を詳しく入力して再度ご相談ください。",
                        'diagnosis': None
                    }

                    # エラー応答をDBに保存
                    if sid:
                        session_data = get_session_from_db(sid)
                        if session_data:
                            if 'messages' not in session_data:
                                session_data['messages'] = []
                            session_data['messages'].append(bot_response)
                            session_data['last_activity'] = datetime.now()
                            save_session_to_db(sid, session_data)
                    # セッションCookie肥大化を防ぐため、Flaskセッションからmessagesを削除
                    if 'messages' in session:
                        del session['messages']
                        session.modified = True
                
        # 症状入力の場合のみ医薬品推奨を実行
        # 質問の場合は属性抽出のみ行い、医薬品推奨は行わない
        # 注意: should_handle_other_categoryフラグが設定されていた場合は、is_questionがFalseに変更されていても質問処理として扱う
        force_question_mode = session.get('should_handle_other_category', False)
        if not is_question and not force_question_mode:
            # レッドフラッグ（妊娠・授乳）チェック：症状解析の前に応答を返す
            ua = session.get('user_attributes', {}) or {}
            if ua.get('pregnant') is True:
                from src.services.html_formatter import format_escalation_display
                escalation_msg = '妊娠中は医師の診断を受けてください。市販薬の使用は医師にご相談ください。'
                logger.warning(f"⚠️ 妊娠中検出: 症状解析をスキップしてエスカレーションメッセージを返却")
                escalation_content = format_escalation_display(
                    doctor_consultation=escalation_msg,
                    medicine_type="該当なし（妊娠中のため推奨中止）",
                    algorithm="禁忌チェック（妊娠）",
                    user_message=user_message,
                    include_feedback_buttons=True
                )
                bot_response = {
                    'type': 'bot',
                    'content': escalation_content,
                    'diagnosis': {'doctor_consultation': escalation_msg, 'escalation': True},
                    'timestamp': datetime.now().isoformat()
                }
                if 'messages' not in session:
                    session['messages'] = []
                session['messages'].append(bot_response)
                session.modified = True
                if sid:
                    session_data = get_session_from_db(sid)
                    if not session_data:
                        session_data = {
                            'session_id': sid,
                            'username': session.get('username', 'Unknown'),
                            'messages': session['messages'].copy(),
                            'last_activity': datetime.now(),
                            'client_ip': request.remote_addr,
                            'user_agent': request.headers.get('User-Agent', ''),
                            'user_attributes': ua,
                            'session_active': True
                        }
                    else:
                        session_data['messages'] = session['messages'].copy()
                        session_data['last_activity'] = datetime.now()
                    save_session_to_db(sid, session_data)
                return jsonify({'status': 'ok', 'message_count': len(session['messages'])})
            if ua.get('breastfeeding') is True:
                from src.services.html_formatter import format_escalation_display
                escalation_msg = '授乳中は医師の診断を受けてください。市販薬の使用は医師にご相談ください。'
                logger.warning(f"⚠️ 授乳中検出: 症状解析をスキップしてエスカレーションメッセージを返却")
                escalation_content = format_escalation_display(
                    doctor_consultation=escalation_msg,
                    medicine_type="該当なし（授乳中のため推奨中止）",
                    algorithm="禁忌チェック（授乳）",
                    user_message=user_message,
                    include_feedback_buttons=True
                )
                bot_response = {
                    'type': 'bot',
                    'content': escalation_content,
                    'diagnosis': {'doctor_consultation': escalation_msg, 'escalation': True},
                    'timestamp': datetime.now().isoformat()
                }
                if 'messages' not in session:
                    session['messages'] = []
                session['messages'].append(bot_response)
                session.modified = True
                if sid:
                    session_data = get_session_from_db(sid)
                    if not session_data:
                        session_data = {
                            'session_id': sid,
                            'username': session.get('username', 'Unknown'),
                            'messages': session['messages'].copy(),
                            'last_activity': datetime.now(),
                            'client_ip': request.remote_addr,
                            'user_agent': request.headers.get('User-Agent', ''),
                            'user_attributes': ua,
                            'session_active': True
                        }
                    else:
                        session_data['messages'] = session['messages'].copy()
                        session_data['last_activity'] = datetime.now()
                    save_session_to_db(sid, session_data)
                return jsonify({'status': 'ok', 'message_count': len(session['messages'])})
                
            # 言語を検出（症状入力時にも実行）
            detected_language = detect_language(user_message)
            session['detected_language'] = detected_language
            logger.info(f"🌍 検出された言語: {detected_language}")
                
            # 医薬品相談回答処理の開始時にフラグを設定
            session['is_medicine_consultation'] = True
            logger.info(f"🏥 SYMPTOM INPUT DETECTED: {user_message}")
            logger.info(f"💊 医薬品相談回答処理開始 - フラグ設定完了")
            last_diagnosis = None
                
            # ユーザー症状文をselect_symptoms_via_gptに渡してChatGPT返答をターミナルに表示
            try:
                logger.info(f"🔍 Calling select_symptoms_via_gpt...")
                start_time = time.time()
                matched_symptoms = select_symptoms_via_gpt(processed_message)  # 方言変換後のテキストを使用
                end_time = time.time()
                execution_time = round(end_time - start_time, 3)
                    
                # medicine_logic.pyの呼び出しをログ出力
                log_medicine_logic_call(
                    "select_symptoms_via_gpt",
                    {"user_message": processed_message},  # 方言変換後のテキストをログに表示
                    {"matched_symptoms": matched_symptoms},
                    execution_time
                )
                    
                # No symptoms detectedの場合は早期リターン
                if matched_symptoms.get('status') == 'success' and matched_symptoms.get('message') == 'No symptoms detected':
                    logger.warning(f"⚠️ 症状が検出できませんでした: {user_message}")
                    bot_response = {
                        'type': 'bot',
                        'content': '申し訳ございませんが、入力いただいた内容から症状を分析することができませんでした。もう少し詳しく症状を教えていただけますか？例えば「頭痛がします」「熱があります」など、具体的な症状を入力してください。',
                        'diagnosis': None
                    }
                    session['messages'].append(bot_response)
                    session.modified = True
                        
                    # DB保存処理
                    if sid:
                        session_data = get_session_from_db(sid)
                        if not session_data:
                            session_data = {
                                'session_id': sid,
                                'username': session.get('username', 'Unknown'),
                                'messages': session['messages'].copy(),
                                'last_activity': datetime.now(),
                                'client_ip': request.remote_addr,
                                'user_agent': request.headers.get('User-Agent', ''),
                                'user_attributes': session.get('user_attributes', {}),
                                'session_active': True
                            }
                            save_session_to_db(sid, session_data)
                        else:
                            session_data['messages'] = session['messages'].copy()
                            session_data['last_activity'] = datetime.now()
                            save_session_to_db(sid, session_data)
                        
                    message_count = len(session['messages'])
                    logger.info(f"✅ POST処理完了（症状検出失敗） - JSON返却: {message_count} messages")
                    return jsonify({'status': 'ok', 'message_count': message_count})
            except Exception as e:
                logger.error(f"❌ select_symptoms_via_gpt実行時エラー: {e}")
                
            # ハイブリッド医薬品推奨システム（ルールベース + ChatGPT）
            logger.info(f"💊 Hybrid medicine recommendation system starting...")
                
            # OpenAI clientを初期化（推奨システム用）
            from openai import OpenAI
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                return jsonify({
                    'error': True,
                    'response': '⚠️ システムエラー: OpenAI APIキーが設定されていません。管理者に連絡してください。'
                })
            recommendation_client = OpenAI(api_key=api_key)
                
            resp = run_recommendation_flow(
                session, request, sid, monitor, client_ip, user_agent,
                sanitized_message, processed_message,
                triage_result, recommendation_client,
                user_message=user_message,
            )

            message_count = len(session.get('messages', []))
            response = resp

        # レスポンス返却後にログ出力（非同期化）
        try:
            # パフォーマンスメトリクスをログに記録
            metrics = monitor.get_metrics()
            log_performance_metrics(monitor, sid, 'POST_request', {
                'user_agent': user_agent,
                'client_ip': client_ip
            })
            
            # アクセス分析ログを記録（DB読み取りは最小限に）
            session_data = get_session_from_db(sid) if sid else None
            actual_message_count = len(session_data.get('messages', [])) if session_data else message_count
            log_access_analytics(sid, user_agent, client_ip, metrics['response_time_ms'], {
                'username': session.get('username', ''),
                'message_count': actual_message_count
            })
            
            logger.info(f"✅ POST処理完了 - JSON返却: {actual_message_count} messages")
        except Exception as e:
            logger.warning(f"ログ出力エラー（無視）: {e}")
    
        return response
