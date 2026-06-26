"""
チャット入力の検証・ブロック判定

責務: 絶対ブロックリスト、セキュリティ検証、危機キーワード検出、ユーザー属性登録
"""
import logging
import uuid
from datetime import datetime

from src.utils.jst_datetime import now_jst_iso
from src.utils.request_logger import log_user_interaction
from src.utils.user_attribute_registration import register_user_attributes_from_message
from src.services.session_manager import (
    get_session_from_db,
    save_session_to_db,
    get_manual_reply_queue,
    set_manual_reply_queue,
    append_user_message,
)

logger = logging.getLogger(__name__)


def _persist_block_messages_to_db(session, client, sid):
    """ブロック時にFlask sessionへ追加したメッセージをDB（またはメモリ）に保存する。"""
    if not sid:
        return
    session_data = get_session_from_db(sid)
    if not session_data:
        session_data = {
            'session_id': sid,
            'username': session.get('username', 'Unknown'),
            'messages': list(session.get('messages', [])),
            'last_activity': now_jst_iso(),
            'client_ip': client.client_ip,
            'user_agent': client.user_agent,
            'user_attributes': session.get('user_attributes', {}),
            'session_active': True,
        }
    else:
        session_data['messages'] = list(session.get('messages', []))
        session_data['last_activity'] = now_jst_iso()
    save_session_to_db(sid, session_data)


def _append_blocked_user_message(session) -> None:
    if 'messages' not in session:
        session['messages'] = []
    from src.utils.jst_datetime import now_jst_iso

    session['messages'].append({
        'type': 'user',
        'content': '（この入力はブロックされました）',
        'timestamp': now_jst_iso(),
        'uuid': str(uuid.uuid4())
    })


def _append_security_block_bot(session, sid, message: str, *, kind: str, variant: str = "caution") -> None:
    from src.services.sage_bot_response import build_notice_bot

    session['messages'].append(
        build_notice_bot(
            session,
            sid,
            message,
            title="入力について",
            variant=variant,
            kind=kind,
            uuid=str(uuid.uuid4()),
        )
    )


def validate_and_block_input(session, client, user_message, sid):
    """
    入力の検証・ブロック・危機検出を行う。
    Returns:
        (sanitized_message, error_response) - error_response が (dict, status) なら return する。
    """
    try:
        from src.security.aggressive_input import (
            AGGRESSIVE_INPUT_NOTICE_MESSAGE,
            is_aggressive_expression,
        )

        aggressive, reason = is_aggressive_expression(user_message)
        if aggressive:
            logger.warning("🚫 攻撃的入力により拒否されました: reason=%s", reason)
            block_message = AGGRESSIVE_INPUT_NOTICE_MESSAGE
            _append_blocked_user_message(session)
            _append_security_block_bot(
                session, sid, block_message, kind="aggressive_input", variant="security"
            )
            if hasattr(session, "modified"):
                session.modified = True
            _persist_block_messages_to_db(session, client, sid)
            if sid:
                try:
                    from src.services.processing_status import clear_processing_status

                    clear_processing_status(sid)
                except ImportError:
                    pass
            message_count = len(session["messages"])
            return (
                None,
                (
                    {
                        "status": "ok",
                        "message_count": message_count,
                        "response": block_message,
                    },
                    200,
                ),
            )
    except ImportError:
        pass

    try:
        # known_attack_rules → 即時警告（SECURITY_ROLLOUT_PHASE 非依存）。続けて security_validator でスコアリング。
        from src.security.known_attack_rules import KNOWN_ATTACK_WARN_MESSAGE, match_known_attack
        from src.security.security_logger import log_input_validation

        matched, rule_id = match_known_attack(user_message)
        if matched:
            logger.warning("🛡️ 既知攻撃ルールにより即時警告応答: rule=%s", rule_id)
            log_input_validation(
                user_id=session.get("username", "unknown"),
                input_text=user_message,
                risk_score=100,
                is_safe=False,
                warnings=[f"known_attack:{rule_id}"],
                sanitized_text=user_message,
            )
            _append_blocked_user_message(session)
            _append_security_block_bot(
                session,
                sid,
                KNOWN_ATTACK_WARN_MESSAGE,
                kind="known_attack",
                variant="caution",
            )
            if hasattr(session, "modified"):
                session.modified = True
            _persist_block_messages_to_db(session, client, sid)
            if sid:
                try:
                    from src.services.processing_status import clear_processing_status

                    clear_processing_status(sid)
                except ImportError:
                    pass
            return (
                None,
                (
                    {
                        "status": "ok",
                        "message_count": len(session.get("messages", [])),
                        "response": KNOWN_ATTACK_WARN_MESSAGE,
                    },
                    200,
                ),
            )
    except ImportError:
        pass

    try:
        from src.security.security_validator import validate_user_input
        from src.security.security_config import should_block_input
        from src.security.security_logger import log_input_validation
        is_safe, risk_score, warnings, sanitized_message = validate_user_input(
            user_message, context='chat'
        )
        log_input_validation(
            user_id=session.get('username', 'unknown'),
            input_text=user_message,
            risk_score=risk_score,
            is_safe=is_safe,
            warnings=warnings,
            sanitized_text=sanitized_message
        )
        if should_block_input(risk_score):
            logger.warning(f"⚠️ 入力がブロックされました: リスクスコア {risk_score}")
            block_message = '入力内容に問題が検出されました。症状や質問を自然な文章で入力してください。'
            _append_blocked_user_message(session)
            _append_security_block_bot(session, sid, block_message, kind="security_block")
            session.modified = True
            _persist_block_messages_to_db(session, client, sid)
            return (None, ({
                'status': 'ok',
                'message_count': len(session['messages']),
                'response': block_message
            }, 200))
        if risk_score >= 80:
            logger.warning(f"⚠️ 高リスク入力検出: リスクスコア {risk_score}")
            warn_message = '入力内容に不審なパターンが検出されました。症状や質問を自然な文章で入力してください。'
            _append_blocked_user_message(session)
            _append_security_block_bot(session, sid, warn_message, kind="security_warn", variant="caution")
            session.modified = True
            _persist_block_messages_to_db(session, client, sid)
            return (None, ({
                'status': 'ok',
                'message_count': len(session['messages']),
                'response': warn_message
            }, 200))
        log_user_interaction(sanitized_message, "POST", session.get('_id', 'unknown'), session.get('username', 'unknown'))
    except ImportError as e:
        logger.warning(f"⚠️ セキュリティモジュールのインポートに失敗: {e}")
        sanitized_message = user_message
        log_user_interaction(sanitized_message, "POST", session.get('_id', 'unknown'), session.get('username', 'unknown'))
    except Exception as e:
        logger.error(f"❌ セキュリティ検証でエラー: {e}")
        sanitized_message = user_message
        log_user_interaction(sanitized_message, "POST", session.get('_id', 'unknown'), session.get('username', 'unknown'))

    try:
        from src.handlers.line.line_session import is_line_session_id

        register_user_attributes_from_message(
            session,
            session.get('_id'),
            sanitized_message,
            save_to_db_fn=save_session_to_db,
            get_session_from_db_fn=get_session_from_db,
            schedule_async_extraction=not (sid and is_line_session_id(sid)),
        )
        from src.utils.user_attribute_registration import try_early_attribute_registration_ui

        try_early_attribute_registration_ui(
            session,
            sid,
            sanitized_message,
            save_to_db_fn=save_session_to_db,
            get_session_from_db_fn=get_session_from_db,
            client_info=client,
        )
    except Exception as e:
        logger.warning(f"⚠️ ユーザー属性登録でエラー: {e}")

    try:
        from src.core.crisis_detection import detect_crisis_keywords, get_crisis_support_resources
        from src.security.security_logger import log_crisis_keyword_detection
        has_crisis_keywords, detected_keywords = detect_crisis_keywords(sanitized_message)
        if has_crisis_keywords:
            logger.warning(f"🚨 危機関連ワード検出: {detected_keywords}")
            append_user_message(session, sanitized_message)
            user_language = session.get('language', 'ja')
            crisis_resources = get_crisis_support_resources(user_language)
            from src.services.sage_bot_response import build_bot_response
            from src.services.status_diagnosis_builder import build_crisis_status

            status_diag = build_crisis_status(
                crisis_resources["message"],
                resources=crisis_resources.get("resources"),
                title=crisis_resources.get("title", "相談窓口のご案内"),
            )
            bot_response = build_bot_response(
                session,
                sid,
                sage_diagnosis=status_diag.to_client_dict(),
                legacy_content=crisis_resources["message"],
                crisis_support=True,
                crisis_title=crisis_resources["title"],
                resources=crisis_resources["resources"],
                emergency_message=crisis_resources["emergency_message"],
            )
            session['messages'].append(bot_response)
            session.modified = True
            session['crisis_detected'] = True
            if sid:
                session_data = get_session_from_db(sid)
                if not session_data:
                    session_data = {
                        'session_id': sid,
                        'username': session.get('username', 'Unknown'),
                        'messages': session['messages'].copy(),
                        'last_activity': now_jst_iso(),
                        'client_ip': client.client_ip,
                        'user_agent': client.user_agent,
                        'user_attributes': session.get('user_attributes', {}),
                        'session_active': True,
                        'crisis_detected': True
                    }
                else:
                    session_data['messages'] = session['messages'].copy()
                    session_data['crisis_detected'] = True
                    session_data['last_activity'] = now_jst_iso()
                save_session_to_db(sid, session_data)
            log_crisis_keyword_detection(
                user_id=session.get('username', 'unknown'),
                input_text=sanitized_message,
                detected_keywords=detected_keywords,
                session_id=sid
            )
            crisis_queue_item = {
                'session_id': sid,
                'user_message': sanitized_message,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'status': 'crisis_detected',
                'crisis_keywords': detected_keywords,
                'priority': 'high'
            }
            queue = get_manual_reply_queue()
            queue.append(crisis_queue_item)
            set_manual_reply_queue(queue)
            logger.info(f"🚨 危機対応セッションを手動返信キューに追加: {sid}")
            message_count = len(session['messages'])
            return (None, ({
                'status': 'ok',
                'message_count': message_count,
                'crisis_support': True
            }, 200))
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"❌ 危機対応機能でエラー: {e}")
    return (sanitized_message, None)
