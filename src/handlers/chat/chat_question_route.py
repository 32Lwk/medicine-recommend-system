"""
質問モード判定・挨拶・医薬品 Q&A・属性抽出
"""
from __future__ import annotations

import logging
import re
import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Tuple

from openai import OpenAI

from src.core.language_utils import update_session_language_from_message
from src.core.medicine_logic import (
    client as openai_client,
    extract_user_attributes_multilingual,
)
from src.services.session_manager import get_session_from_db, save_session_to_db
from src.utils.input_helpers import is_symptom_input, is_operation_command

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]


@dataclass
class QuestionFlowResult:
    response: Optional[ResponseTuple] = None
    is_question: bool = True
    user_message: str = ""
    sanitized_message: str = ""


def _mark_session_modified(session: Any) -> None:
    if hasattr(session, "modified"):
        session.modified = True


def _should_route_medicine_discovery_to_recommendation(
    session: Any,
    sid: Optional[str],
    user_message: str,
    *,
    triage_category: Optional[str] = None,
) -> bool:
    from src.services.medicine_discovery_routing import (
        should_route_medicine_discovery_to_recommendation,
    )

    return should_route_medicine_discovery_to_recommendation(
        session,
        sid,
        user_message,
        triage_category=triage_category,
    )


def _execute_medicine_qa_flow(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
) -> QuestionFlowResult:
    """医薬品 Q&A を実行し JSON 応答用の QuestionFlowResult を返す。"""
    try:
        from src.handlers.chat.chat_medicine_qa_html import run_medicine_question_qa

        count, _ = run_medicine_question_qa(session, client_info, sid, user_message)
        return QuestionFlowResult(
            response=({"status": "ok", "message_count": count}, 200),
            is_question=True,
            user_message=user_message,
            sanitized_message=sanitized_message,
        )
    except Exception as exc:
        logger.error("❌ 医薬品相談機能実行時エラー: %s", exc, exc_info=True)
        from src.services.sage_bot_response import build_bot_response
        from src.services.status_diagnosis_builder import build_system_error_status

        legacy_content = (
            "申し訳ございません。一時的にエラーが発生しました。"
            "しばらく時間をおいてもう一度お試しいただくか、"
            "症状を詳しく入力して再度ご相談ください。"
        )
        sage_diag = build_system_error_status(message=legacy_content).to_client_dict()
        bot_response = build_bot_response(
            session,
            sid,
            sage_diagnosis=sage_diag,
            legacy_content=legacy_content,
        )
        if sid:
            session_data = get_session_from_db(sid)
            if session_data:
                if "messages" not in session_data:
                    session_data["messages"] = []
                session_data["messages"].append(bot_response)
                session_data["last_activity"] = datetime.now()
                save_session_to_db(sid, session_data)
        if "messages" in session:
            del session["messages"]
            _mark_session_modified(session)
        updated = get_session_from_db(sid) if sid else {}
        count = len(updated.get("messages", []))
        return QuestionFlowResult(
            response=({"status": "ok", "message_count": count}, 200),
            is_question=True,
            user_message=user_message,
            sanitized_message=sanitized_message,
        )


def _resolve_medicine_qa_gate_decision(
    session: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
    recommendation_client: OpenAI,
    routing: Any = None,
):
    from src.services.medicine_qa_eligibility import resolve_medicine_qa_route
    from src.dialogue.history import resolve_concierge_history_with_fallback

    triage = None
    if routing is not None and getattr(routing, "triage_result", None):
        triage = routing.triage_result
    if triage is None:
        triage = session.get("last_triage_result")

    history = resolve_concierge_history_with_fallback(session, sid)
    return resolve_medicine_qa_route(
        sanitized_message or user_message,
        session=session,
        triage_result=triage,
        conversation_history=history,
        client=recommendation_client,
    )


def _try_concierge_instead_of_medicine_qa(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
    recommendation_client: OpenAI,
    routing: Any = None,
) -> Optional[QuestionFlowResult]:
    """医薬品 Q&A 直行の前に Concierge（RAG / redirect）へ回す。"""
    from src.handlers.chat.chat_concierge_route import try_concierge_response
    from src.services.medicine_qa_eligibility import MedicineQaRoute

    decision = _resolve_medicine_qa_gate_decision(
        session,
        sid,
        user_message,
        sanitized_message,
        recommendation_client,
        routing=routing,
    )
    if decision.route != MedicineQaRoute.CONCIERGE:
        return None

    triage = dict(
        (getattr(routing, "triage_result", None) if routing else None)
        or session.get("last_triage_result")
        or {}
    )
    if decision.concierge_intent:
        triage["concierge_intent"] = decision.concierge_intent
        triage["concierge_intent_source"] = f"qa_gate:{decision.source}"

    logger.info(
        "🛎️ QA gate → Concierge: intent=%s source=%s text=%r",
        decision.concierge_intent,
        decision.source,
        (sanitized_message or user_message)[:60],
    )
    resp = try_concierge_response(
        session,
        client_info,
        sid,
        user_message,
        sanitized_message,
        triage,
        recommendation_client,
        processed_message=sanitized_message,
        routing_ctx=routing,
    )
    if resp is None:
        return None
    return QuestionFlowResult(
        response=resp,
        is_question=False,
        user_message=user_message,
        sanitized_message=sanitized_message,
    )


def try_qa_gate_concierge_response(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
    recommendation_client: OpenAI,
    *,
    triage_result: Optional[dict] = None,
    routing: Any = None,
) -> Optional[tuple]:
    """QA ゲートで Concierge と判定された入力を HTTP 応答に変換（Physical 直行前にも使用）。"""
    from src.services.medicine_qa_eligibility import MedicineQaRoute

    decision = _resolve_medicine_qa_gate_decision(
        session,
        sid,
        user_message,
        sanitized_message,
        recommendation_client,
        routing=routing,
    )
    if decision.route != MedicineQaRoute.CONCIERGE:
        return None
    result = _try_concierge_instead_of_medicine_qa(
        session,
        client_info,
        sid,
        user_message,
        sanitized_message,
        recommendation_client,
        routing=routing,
    )
    if result is not None and result.response is not None:
        return result.response
    return None


def _gate_medicine_qa_before_execute(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
    recommendation_client: OpenAI,
    routing: Any = None,
) -> Optional[QuestionFlowResult]:
    """
    医薬品 Q&A 実行前ゲート。
    Concierge / Physical へ回す場合は QuestionFlowResult を返す。MEDICINE_QA なら None。
    """
    from src.services.medicine_qa_eligibility import MedicineQaRoute

    decision = _resolve_medicine_qa_gate_decision(
        session,
        sid,
        user_message,
        sanitized_message,
        recommendation_client,
        routing=routing,
    )
    if decision.route == MedicineQaRoute.CONCIERGE:
        concierge_result = _try_concierge_instead_of_medicine_qa(
            session,
            client_info,
            sid,
            user_message,
            sanitized_message,
            recommendation_client,
            routing=routing,
        )
        if concierge_result is not None:
            return concierge_result
        logger.info("⏭️ QA gate Concierge 未処理 — 医薬品 Q&A には進まない")
        return QuestionFlowResult(
            is_question=False,
            user_message=user_message,
            sanitized_message=sanitized_message,
        )
    if decision.route == MedicineQaRoute.PHYSICAL:
        logger.info("💊 QA gate → Physical（症状入力）")
        return QuestionFlowResult(
            is_question=False,
            user_message=user_message,
            sanitized_message=sanitized_message,
        )
    return None


def _try_triage_ask_qa(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
    recommendation_client: OpenAI,
    routing: Any = None,
) -> Optional[QuestionFlowResult]:
    """エージェント ON かつトリアージ Ask かつ医療コンテキストありのときのみ Q&A 直行。"""
    from config.llm_flags import is_agent_enabled
    from src.services.medicine_discovery_routing import session_is_medical_cold_start

    if not is_agent_enabled():
        return None
    if session_is_medical_cold_start(session, sid):
        logger.info(
            "⏭️ 初回セッションのため Ask Q&A 直行を禁止（オーケストレーター分類に委譲）"
        )
        return None
    if routing is not None:
        category = routing.triage_category
    else:
        category = (session.get("last_triage_result") or {}).get("category")
    if category != "Ask":
        return None
    if _should_route_medicine_discovery_to_recommendation(
        session, sid, user_message, triage_category="Ask"
    ):
        logger.info("💊 初回の薬探索 → 推奨フローへ（Ask Q&A を迂回）")
        return None
    gated = _gate_medicine_qa_before_execute(
        session,
        client_info,
        sid,
        user_message,
        sanitized_message,
        recommendation_client,
        routing=routing,
    )
    if gated is not None:
        return gated
    logger.info("❓ トリアージ Ask → 医薬品 Q&A 直行（推奨履歴あり）")
    return _execute_medicine_qa_flow(
        session, client_info, sid, user_message, sanitized_message
    )


def _concierge_meta_skip(user_message: str) -> Optional[QuestionFlowResult]:
    """Concierge が応答済みの挨拶・感謝・雑談・メタ質問は二重応答しない。"""
    from src.services.concierge_intent import classify_concierge_intent

    text = (user_message or "").strip()
    intent = classify_concierge_intent(text)
    if intent in ("greeting", "thanks", "chitchat"):
        logger.info("⏭️ Concierge 対象のため question_route をスキップ: intent=%s", intent)
        return QuestionFlowResult(
            response=None,
            is_question=False,
            user_message=user_message,
            sanitized_message=user_message,
        )
    return None


def handle_question_flow(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
    processed_message: str,
    recommendation_client: OpenAI,
    *,
    pending_route_is_question: Optional[bool] = None,
    routing: Any = None,
) -> QuestionFlowResult:
    if routing is None:
        from src.services.routing_context import RoutingContext

        routing = RoutingContext.from_session(
            session, sid, user_message, sanitized_message
        )
    if pending_route_is_question is None and routing.pending_route_is_question is not None:
        pending_route_is_question = routing.pending_route_is_question

    from config.llm_flags import is_agent_enabled
    from src.services.medicine_discovery_routing import (
        cold_start_needs_recommendation_flow,
        session_is_medical_cold_start,
    )

    cold_start = session_is_medical_cold_start(session, sid)

    if is_agent_enabled() and routing.triage_category:
        cat = routing.triage_category
        if cold_start and cat == "Ask" and cold_start_needs_recommendation_flow(
            user_message
        ):
            logger.info(
                "💊 初回セッション（トリアージ Ask）→ 推奨フローへ（キーワード Q&A 禁止）"
            )
            return QuestionFlowResult(
                is_question=False,
                user_message=user_message,
                sanitized_message=sanitized_message,
            )
        if cat == "Ask":
            if _should_route_medicine_discovery_to_recommendation(
                session, sid, user_message, triage_category=cat
            ):
                logger.info(
                    "💊 初回の薬探索（トリアージ Ask）→ 推奨フローへ"
                )
                return QuestionFlowResult(
                    is_question=False,
                    user_message=user_message,
                    sanitized_message=sanitized_message,
                )
            ask_qa = _try_triage_ask_qa(
                session,
                client_info,
                sid,
                user_message,
                sanitized_message,
                recommendation_client,
                routing=routing,
            )
            if ask_qa is not None:
                return ask_qa
        if cat in ("Physical", "Emotional", "Emergency"):
            logger.info("🔍 トリアージ %s のため question_route をスキップ", cat)
            return QuestionFlowResult(
                is_question=False,
                user_message=user_message,
                sanitized_message=sanitized_message,
            )

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

    skip = _concierge_meta_skip(user_message)
    if skip is not None:
        return skip

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
    if cold_start and cold_start_needs_recommendation_flow(user_message):
        is_question = False
        logger.info("💊 初回セッション: キーワード質問判定を抑止し推奨フローへ")
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
    if pending_route_is_question is not None:
        is_question = pending_route_is_question
        logger.info(f"🔍 カテゴリルートにより is_question={is_question} に上書き")
    elif is_question is None:
        from config.llm_flags import is_agent_enabled

        if is_agent_enabled() and routing.triage_category:
            cat = routing.triage_category
            if cat == "Ask":
                if cold_start:
                    is_question = False
                    logger.info(
                        "🔍 初回セッション: トリアージ Ask でも is_question=False（Q&A 禁止）"
                    )
                else:
                    is_question = True
                    logger.info("🔍 トリアージ Ask のため is_question=True")
            elif cat in ("Physical", "Emotional", "Emergency"):
                is_question = False
                logger.info("🔍 トリアージ %s のため is_question=False", cat)
    if is_question:
        ask_qa = _try_triage_ask_qa(
            session,
            client_info,
            sid,
            user_message,
            sanitized_message,
            recommendation_client,
            routing=routing,
        )
        if ask_qa is not None:
            return ask_qa
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
            if sid:
                try:
                    from src.services.processing_status import mark_processing_step, set_processing_flow

                    set_processing_flow(sid, "greeting")
                    mark_processing_step(sid, "counseling")
                except Exception:
                    pass
                
            from src.agents.concierge_agent import generate_greeting_text
            from src.services.sage_bot_response import build_bot_response
            from src.services.status_diagnosis_builder import build_concierge_text_status

            from src.dialogue.history import resolve_concierge_history_with_fallback

            history = resolve_concierge_history_with_fallback(session, sid)
            greeting_response, _ = generate_greeting_text(
                recommendation_client,
                user_message,
                session_id=sid,
                history=history,
            )
            sage_diag = build_concierge_text_status(
                greeting_response,
                title="ご挨拶",
                kind="concierge_greeting",
            ).to_client_dict()
            bot_response = build_bot_response(
                session,
                sid,
                sage_diagnosis=sage_diag,
                legacy_content=greeting_response,
                greeting=True,
            )
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
                        'client_ip': client_info.client_ip,
                        'user_agent': client_info.user_agent,
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
            return QuestionFlowResult(response=({'status': 'ok', 'message_count': message_count}, 200))
            
        # システム紹介、医薬品検索、明確な質問、または語尾・記号から質問と判断できる場合は質問回答に進む
        if (is_system_intro or is_medicine_search or has_question_keyword or
            has_question_suffix or ends_with_question_mark):
            logger.info("❓ CLEAR QUESTION DETECTED: %s", user_message)
            if cold_start and not is_system_intro:
                logger.info(
                    "⏭️ 初回セッション: キーワード一致による Q&A 直行をスキップ"
                )
                return QuestionFlowResult(
                    is_question=False,
                    user_message=user_message,
                    sanitized_message=sanitized_message,
                )
            if _should_route_medicine_discovery_to_recommendation(
                session,
                sid,
                user_message,
                triage_category=(routing.triage_category if routing else None),
            ):
                logger.info("💊 初回の薬探索 → 推奨フローへ（CLEAR QUESTION を迂回）")
                return QuestionFlowResult(
                    is_question=False,
                    user_message=user_message,
                    sanitized_message=sanitized_message,
                )
            gated = _gate_medicine_qa_before_execute(
                session,
                client_info,
                sid,
                user_message,
                sanitized_message,
                recommendation_client,
                routing=routing,
            )
            if gated is not None:
                return gated
            result = _execute_medicine_qa_flow(
                session, client_info, sid, user_message, sanitized_message
            )
            session.setdefault(
                "user_attributes",
                {
                    "age": None,
                    "gender": None,
                    "pregnant": None,
                    "breastfeeding": None,
                    "current_medications": [],
                    "allergies": [],
                    "medical_history": [],
                    "symptom_duration_days": None,
                    "other_info": None,
                },
            )
            _mark_session_modified(session)
            return result
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
            detected_language = update_session_language_from_message(session, user_message)
            logger.info(f"🌍 検出された言語: {detected_language}")
                
            # 初回チャットで症状入力（または症状キーワードを含む）場合は
            # 属性抽出をスキップして症状分析（推奨フロー）に進む
            if len(session.get('messages', [])) <= 1 and (
                is_symptom_input(user_message) or has_symptom
            ):
                logger.info(
                    "🔄 初回かつ症状を含む入力のため、"
                    "属性抽出をスキップして症状分析・推奨フローに進みます"
                )
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
                        openai_client, 
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
                from src.services.sage_bot_response import build_bot_response
                from src.services.status_diagnosis_builder import build_notice_status

                advice_text = (
                    "症状が7日を超えている場合は、市販薬での対応が困難な可能性があります。"
                    "医療機関（病院・クリニック）での受診をお勧めします。"
                )
                sage_diag = build_notice_status(
                    advice_text,
                    title="医療機関への受診をお勧めします",
                    variant="caution",
                    kind="medical_advice_duration",
                ).to_client_dict()
                medical_advice = build_bot_response(
                    session,
                    sid,
                    sage_diagnosis=sage_diag,
                    legacy_content=(
                        "⚠️ 症状が7日を超えている場合は、市販薬での対応が困難な可能性があります。"
                        "医療機関（病院・クリニック）での受診をお勧めします。"
                    ),
                    medical_advice=True,
                )
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
                return QuestionFlowResult(response=({'status': 'ok', 'message_count': message_count}, 200))
                
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
                from src.services.sage_bot_response import build_bot_response
                from src.services.status_diagnosis_builder import build_attribute_update_status

                legacy_content = (
                    f"✅ 属性情報を更新しました。\n\n"
                    f"年齢: {user_attributes.get('age', '未入力')}\n"
                    f"性別: {user_attributes.get('gender', '未入力')}\n"
                    f"アレルギー: {', '.join(user_attributes.get('allergies', [])) if user_attributes.get('allergies') else 'なし'}\n"
                    f"服用中の薬: {', '.join(user_attributes.get('current_medications', [])) if user_attributes.get('current_medications') else 'なし'}\n\n"
                    f"症状について教えていただければ、更新された情報をもとに適切な医薬品をご提案いたします。"
                )
                sage_diag = build_attribute_update_status(user_attributes).to_client_dict()
                bot_response = build_bot_response(
                    session,
                    sid,
                    sage_diagnosis=sage_diag,
                    legacy_content=legacy_content,
                    attribute_update_confirmation=True,
                )
                    
                # ユーザーメッセージをDBに保存
                if sid:
                    session_data = get_session_from_db(sid)
                    if not session_data:
                        session_data = {
                            'session_id': sid,
                            'username': session.get('username', 'Unknown'),
                            'messages': [],
                            'last_activity': datetime.now(),
                            'client_ip': client_info.client_ip,
                            'user_agent': client_info.user_agent,
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
                    from src.handlers.chat.chat_pipeline_end_guard import (
                        mark_pipeline_turn_bot_appended,
                    )

                    mark_pipeline_turn_bot_appended(session)
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
                return QuestionFlowResult(response=({'status': 'ok', 'message_count': message_count}, 200))
        else:
            logger.info("❓ 通常の質問として処理します")
            gated = _gate_medicine_qa_before_execute(
                session,
                client_info,
                sid,
                user_message,
                sanitized_message,
                recommendation_client,
                routing=routing,
            )
            if gated is not None:
                return gated
            return _execute_medicine_qa_flow(
                session, client_info, sid, user_message, sanitized_message
            )

    return QuestionFlowResult(
        is_question=is_question,
        user_message=user_message,
        sanitized_message=sanitized_message,
    )
