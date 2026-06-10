"""
チャット応答生成サービス

挨拶応答、個別アドバイス生成、質問応答など、チャットボットの応答を構築する責務を持つ。
"""

import html
import json
import logging
import random
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# デフォルトのユーザー属性（質問応答後の初期化用）
DEFAULT_USER_ATTRIBUTES = {
    'age': None,
    'gender': None,
    'pregnant': None,
    'breastfeeding': None,
    'current_medications': [],
    'allergies': [],
    'medical_history': [],
    'symptom_duration_days': None,
    'other_info': None
}

# 汎用挨拶（こんにちは等）— ランダムに1つ選ぶ
GREETING_INTRO_POOL: List[str] = [
    'こんにちは。こちらは医薬品相談の窓口です。頭痛やのどの痛み、お薬の選び方など、お気軽にご相談ください。',
    'こんにちは。症状やお薬についてのご質問を承ります。今お困りのことがあれば、具体的に教えてください。',
    'こんにちは。市販薬の選び方や飲み合わせなど、できる範囲でお手伝いします。まずはお困りの内容をお聞かせください。',
    'こんにちは。お体の不調や薬のご相談でしたら、こちらでサポートいたします。気になる症状があれば教えてください。',
    'こんにちは。医薬品相談AIです。のどの痛み、発熱、胃のむかつきなど、気になることがあればお知らせください。',
    'こんにちは。症状・お薬名・服用状況などを教えていただければ、できる限りご案内します。お気軽にどうぞ。',
    'こんにちは。お薬選びのお手伝いをしています。今のお悩みや症状を、よろしければメッセージでお送りください。',
    'こんにちは。こちらでは市販薬に関するご相談を受け付けています。お困りごとがございましたら、お書きください。',
    'こんにちは。症状のつらさや薬について、落ち着いてご案内します。どのようなことでお悩みか教えてください。',
    'こんにちは。医薬品に関することなら、できる範囲でお答えします。具体的な症状やご質問をお待ちしています。',
]

# 時間帯・初対面など固定トーンの挨拶
GREETING_RESPONSES: Dict[str, str] = {
    'ありがとう': 'どういたしまして。ほかにご質問や症状がございましたら、お気軽にお聞かせください。',
    'ありがとうございます': 'どういたしまして。ほかにご質問や症状がございましたら、お気軽にお聞かせください。',
    'どうも': 'どういたしまして。ほかにご質問や症状がございましたら、お気軽にお聞かせください。',
    'どうもありがとう': 'どういたしまして。ほかにご質問や症状がございましたら、お気軽にお聞かせください。',
    'hello': (
        'Hello! What symptoms are you experiencing? '
        'Please tell me your specific symptoms, and I will recommend appropriate over-the-counter medicines.'
    ),
    'hi': (
        'Hi! What symptoms are you experiencing? '
        'Please tell me your specific symptoms, and I will recommend appropriate over-the-counter medicines.'
    ),
    'thanks': "You're welcome! If you have any other questions or symptoms, please feel free to let me know.",
    'thank you': "You're welcome! If you have any other questions or symptoms, please feel free to let me know.",
}

# キーワード → ランダムプール（汎用 intro と同系統だが冒頭を合わせる）
_GREETING_POOL_BY_PREFIX: Dict[str, List[str]] = {
    'こんばんは': [
        f'こんばんは。{body}'
        for body in (
            'お疲れさまです。体調のことやお薬のご相談があれば、お気軽にお聞かせください。',
            '今夜もお体の不調があれば、症状を教えていただければご案内します。',
            '市販薬の選び方など、できる範囲でお手伝いします。お困りのことがあればどうぞ。',
        )
    ],
    'おはようございます': [
        f'おはようございます。{body}'
        for body in (
            '本日もお体のご相談を承ります。気になる症状があれば教えてください。',
            'お薬のことでお困りでしたら、具体的にお書きください。',
            'のどの痛みや胃の不調など、お気軽にご相談ください。',
        )
    ],
    'おはよう': [
        f'おはようございます。{body}'
        for body in (
            '本日もお体のご相談を承ります。気になる症状があれば教えてください。',
            'お薬のことでお困りでしたら、具体的にお書きください。',
        )
    ],
    'はじめまして': [
        f'はじめまして。{body}'
        for body in (
            '医薬品相談の窓口です。症状やお薬のご質問をお待ちしています。',
            '市販薬に関するご相談を承ります。お困りのことがあれば教えてください。',
        )
    ],
    '初めまして': [
        f'初めまして。{body}'
        for body in (
            '医薬品相談の窓口です。症状やお薬のご質問をお待ちしています。',
            '市販薬に関するご相談を承ります。お困りのことがあれば教えてください。',
        )
    ],
    'よろしくお願いします': [
        f'よろしくお願いします。{body}'
        for body in (
            '医薬品相談の窓口です。症状やお薬のことでしたら、お気軽にどうぞ。',
            'お体の不調やお薬選びでお困りのことがあれば、お聞かせください。',
        )
    ],
    'よろしく': [
        f'よろしくお願いします。{body}'
        for body in (
            '医薬品相談の窓口です。症状やお薬のことでしたら、お気軽にどうぞ。',
            'お体の不調やお薬選びでお困りのことがあれば、お聞かせください。',
        )
    ],
}


def build_greeting_response(user_message: str) -> str:
    """
    ユーザーメッセージに応じた挨拶返答を生成する。
    汎用の「こんにちは」系は GREETING_INTRO_POOL からランダムに選択する。
    """
    lowered = (user_message or '').lower()
    for greeting_key, response in GREETING_RESPONSES.items():
        if greeting_key in lowered:
            return response
    for prefix, pool in _GREETING_POOL_BY_PREFIX.items():
        if prefix in lowered:
            return random.choice(pool)
    return random.choice(GREETING_INTRO_POOL)


def generate_personalized_advice(
    user_attrs: Dict,
    medicines: List[Dict],
    symptoms: List[str],
    client,
    user_text: str = "",
    influenza_risk: bool = False,
    influenza_reason: str = "",
    session_id: Optional[str] = None,
) -> str:
    """
    ユーザー属性に基づいた個別アドバイスをChatGPTで生成（インフルエンザリスク対応含む）

    Args:
        user_attrs: ユーザー属性情報
        medicines: 推奨医薬品リスト
        symptoms: 症状リスト
        client: OpenAIクライアント
        user_text: ユーザーの入力テキスト
        influenza_risk: インフルエンザリスクの有無
        influenza_reason: インフルエンザリスクの理由

    Returns:
        個別アドバイステキスト
    """
    # ユーザー属性を文章化
    attr_text = []
    if user_attrs.get('age'):
        attr_text.append(f"年齢: {user_attrs['age']}歳")
    if user_attrs.get('gender'):
        attr_text.append(f"性別: {user_attrs['gender']}")
    if user_attrs.get('pregnant'):
        attr_text.append("妊娠中")
    if user_attrs.get('breastfeeding'):
        attr_text.append("授乳中")
    if user_attrs.get('allergies'):
        allergy_list = user_attrs['allergies']
        if allergy_list and allergy_list != ['なし']:
            attr_text.append(f"アレルギー: {', '.join(allergy_list)}")
    if user_attrs.get('symptom_duration_days') is not None:
        days = user_attrs['symptom_duration_days']
        if days == 0:
            attr_text.append("症状開始: 今日から")
        elif days == 1:
            attr_text.append("症状開始: 昨日から")
        else:
            attr_text.append(f"症状開始: {days}日前から")

    attr_summary = '、'.join(attr_text) if attr_text else '情報なし'

    # 推奨医薬品の名前リストとリスク警告を収集
    medicine_names = [m.get('product_name', '') or m.get('name', '') for m in medicines[:3]]
    risk_warnings = []
    for m in medicines[:3]:
        if m.get('risk_warning'):
            risk_warnings.append(f"{m.get('product_name', '') or m.get('name', '')}: {m.get('risk_warning')}")

    # インフルエンザリスク情報を追加
    influenza_info = ""
    if influenza_risk:
        influenza_info = f"\n\n【重要】インフルエンザの可能性: {influenza_reason}\nインフルエンザの可能性がある場合は、アスピリンを含む医薬品の使用は避け、早めに医療機関を受診することをお勧めします。"

    # リスク成分警告情報を追加
    risk_warning_info = ""
    if risk_warnings:
        risk_warning_info = f"\n\n【リスク成分について】\n{chr(10).join(risk_warnings)}\nこれらの成分が含まれる医薬品については、使用前に必ず添付文書を確認し、不安な点があれば薬剤師または登録販売者にご相談ください。"

    prompt = f"""
あなたは登録販売者です。以下のユーザー情報と推奨医薬品を基に、このユーザーに合わせた個別のアドバイスを100-200字程度で生成してください。

【ユーザーの入力】
{user_text if user_text else '症状情報なし'}

【ユーザー情報】
{attr_summary}

【症状】
{', '.join(symptoms) if symptoms else '症状情報なし'}

【推奨医薬品】
{', '.join(medicine_names) if medicine_names else '推奨医薬品なし'}{influenza_info}{risk_warning_info}

【生成するアドバイス】
- ユーザーの入力内容（「{user_text[:50] if user_text else ''}...」など）に言及し、親身な対応を心がけてください
- ユーザーの年齢、性別、妊娠状態などを考慮
- 推奨医薬品がこのユーザーに適している理由を、ユーザーの言葉を使って自然に説明してください（例：「〇〇という症状に基づき、複数の症状を同時にカバーできる総合感冒薬を優先して選んでいます」）
- 特に注意すべきポイント
- インフルエンザリスクがある場合はその注意喚起を含める
- 温かく、分かりやすい言葉で

100-200字程度で、このユーザーに合わせた温かいアドバイスを生成してください。
"""

    try:
        from src.core.i18n_prompts import normalize_lang
        from src.core.llm_client import chat_completion_create
        from src.core.i18n_prompts import append_dialect_counseling_hints, append_language_instruction
        from src.core.translation_service import translate_medicine_recommendation
        from src.services.sse_emit import is_streaming_active

        lang = normalize_lang((user_attrs or {}).get("language") or (user_attrs or {}).get("lang"))
        system_content = append_dialect_counseling_hints(
            "あなたは親切な登録販売者です。ユーザーに寄り添った温かいアドバイスを提供してください。",
            lang,
        )
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt},
        ]
        sid = session_id
        stream_active = is_streaming_active(sid)

        if stream_active or lang != "ja":
            user_content = append_language_instruction(prompt, lang) if lang != "ja" else prompt
            response = chat_completion_create(
                client,
                model_role="counsel",
                path="chat_response_service.personalized_advice",
                messages=[
                    messages[0],
                    {"role": "user", "content": user_content},
                ],
                temperature=0.7,
                max_tokens=200,
            )
            advice = response.choices[0].message.content.strip()
            if lang != "ja":
                advice = translate_medicine_recommendation(advice, lang, session_id=sid)
        else:
            response = chat_completion_create(
                client,
                model_role="counsel",
                path="chat_response_service.personalized_advice",
                messages=messages,
                temperature=0.7,
                max_tokens=200,
            )
            advice = response.choices[0].message.content.strip()

        logger.info(f"✅ 個別アドバイス生成完了: {len(advice)}字")
        return advice

    except Exception as e:
        logger.error(f"❌ 個別アドバイス生成エラー: {e}")
        logger.error(f"エラー詳細: {str(e)}")
        # フォールバック
        age = user_attrs.get('age')
        pregnant = user_attrs.get('pregnant')
        breastfeeding = user_attrs.get('breastfeeding')

        duration_days = user_attrs.get('symptom_duration_days')

        logger.info(f"フォールバック: age={age}, pregnant={pregnant}, breastfeeding={breastfeeding}, duration={duration_days}")

        # 症状期間の警告
        duration_warning = ""
        if duration_days and duration_days >= 3:
            if duration_days >= 7:
                duration_warning = f"症状が{duration_days}日間続いているとのこと、1週間以上症状が続く場合は早めに医師の診察を受けることをお勧めします。"
            else:
                duration_warning = f"症状が{duration_days}日間続いているとのこと、"

        if pregnant is True or pregnant == 'True':
            base_msg = "妊娠中のためご連絡ありがとうございます。推奨した医薬品は妊娠中でも使用可能なものを選んでいますが、服用前に必ず医師にご相談いただくとより安心です。お大事になさってください。"
            return f"{duration_warning}{base_msg}"
        elif breastfeeding is True or breastfeeding == 'True':
            base_msg = "授乳中のためご連絡ありがとうございます。推奨した医薬品は授乳中でも使用可能なものを選んでいますが、服用前に医師にご相談いただくとより安心です。"
            return f"{duration_warning}{base_msg}"
        elif age and age < 15:
            base_msg = f"{age}歳のお子様への服用となります。推奨医薬品は年齢に適したものを選んでいますが、必ず保護者の方が用法用量を確認し、監督のもとで服用してください。"
            return f"{duration_warning}{base_msg}"
        elif age and age >= 65:
            base_msg = "ご高齢の方への推奨となります。推奨医薬品は適切なものを選んでいますが、持病をお持ちの場合や他のお薬を服用されている場合は、飲み合わせにご注意ください。"
            return f"{duration_warning}{base_msg}"
        else:
            # 属性情報があればそれを含める
            info_parts = []
            if age:
                info_parts.append(f"{age}歳")
            if user_attrs.get('gender'):
                info_parts.append(user_attrs['gender'])

            if info_parts:
                info_str = '、'.join(info_parts)
                return f"{info_str}の方への推奨です。あなたの情報を考慮して最適な医薬品を選んでいます。服用前に添付文書をよく読み、用法用量を守ってご使用ください。お大事にしてください。"
            else:
                return "あなたの情報を考慮して、最適な医薬品を推奨しています。服用前に添付文書をよく読み、用法用量を守ってご使用ください。お大事にしてください。"


def _safe_format_html(text: Optional[str]) -> str:
    """テキストを安全にHTML表示用に整形"""
    from src.services.text_formatter import safe_format_qa_html

    return safe_format_qa_html(text)


def build_question_response(
    user_message: str,
    sid: Optional[str],
    session: Any,
    request_obj: Any,
    get_session_from_db,
    save_session_to_db,
    chat_with_medicine_context,
) -> Dict[str, Any]:
    """
    医薬品に関する質問に回答し、応答データを返す。

    Args:
        user_message: ユーザーの質問メッセージ
        sid: セッションID
        session: Flaskセッションオブジェクト
        request_obj: Flaskのrequestオブジェクト
        get_session_from_db: セッション取得関数
        save_session_to_db: セッション保存関数
        chat_with_medicine_context: ChatGPT相談関数

    Returns:
        jsonify用の辞書 {'status': 'ok', 'message_count': N}
    """
    try:
        session_data_for_medicines = get_session_from_db(sid) if sid else {}
        latest_recommended_medicines = []
        for msg in reversed(session_data_for_medicines.get('messages', [])):
            if msg.get('type') == 'bot' and msg.get('diagnosis'):
                diagnosis = msg.get('diagnosis', {})
                if diagnosis.get('recommended_medicines'):
                    latest_recommended_medicines = diagnosis.get('recommended_medicines', [])
                    break

        logger.info(f"📋 Latest recommended medicines: {len(latest_recommended_medicines)} items")

        conversation_history = session_data_for_medicines.get('messages', [])[-10:]
        chat_response = chat_with_medicine_context(
            user_message,
            conversation_history,
            latest_recommended_medicines,
            session_id=sid,
        )

        try:
            from src.utils.structured_logger import log_medicine_question_detail
            log_medicine_question_detail(
                session_id=sid,
                user_input=user_message,
                response=chat_response.get('answer', '')
            )
        except Exception as e:
            logger.warning(f"医薬品質疑応答ログ記録エラー: {e}")

        answer_text = _safe_format_html(chat_response.get('answer', '回答を取得できませんでした'))
        medicine_details = _safe_format_html(chat_response.get('medicine_details', ''))
        interactions = _safe_format_html(chat_response.get('interactions', ''))
        doping_check = _safe_format_html(chat_response.get('doping_check', ''))
        side_effects = _safe_format_html(chat_response.get('side_effects', ''))
        consultation_advice = _safe_format_html(chat_response.get('consultation_advice', ''))

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

        message_id = f"msg_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        logger.info(f"[DEBUG] Generated message_id: {message_id}")

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

        if sid:
            session_data = get_session_from_db(sid)
            if not session_data:
                session_data = {
                    'session_id': sid,
                    'username': session.get('username', 'Unknown'),
                    'messages': [],
                    'last_activity': datetime.now(),
                    'client_ip': request_obj.remote_addr,
                    'user_agent': request_obj.headers.get('User-Agent', ''),
                    'user_attributes': session.get('user_attributes', {}),
                    'session_active': True
                }
            if 'messages' not in session_data:
                session_data['messages'] = []
            session_data['messages'].append(bot_response)
            session_data['last_activity'] = datetime.now()
            save_session_to_db(sid, session_data)

        if 'messages' in session:
            del session['messages']
            session.modified = True
        logger.info(f"✅ 質問応答完了: {user_message}")

        session['user_attributes'] = session.get('user_attributes', DEFAULT_USER_ATTRIBUTES.copy())
        session.modified = True

        updated_session = get_session_from_db(sid) if sid else {}
        message_count = len(updated_session.get('messages', []))
        return {'status': 'ok', 'message_count': message_count}

    except Exception as e:
        logger.error(f"❌ 医薬品相談機能実行時エラー: {e}")
        import traceback
        logger.error(traceback.format_exc())
        bot_response = {
            'type': 'bot',
            'content': f"申し訳ございません。システムエラーが発生しました: {str(e)}",
            'diagnosis': None,
            'timestamp': datetime.now().isoformat()
        }

        if sid:
            session_data = get_session_from_db(sid)
            if session_data:
                if 'messages' not in session_data:
                    session_data['messages'] = []
                session_data['messages'].append(bot_response)
                session_data['last_activity'] = datetime.now()
                save_session_to_db(sid, session_data)
        if 'messages' in session:
            del session['messages']
            session.modified = True

        session['user_attributes'] = session.get('user_attributes', DEFAULT_USER_ATTRIBUTES.copy())
        session.modified = True

        updated_session = get_session_from_db(sid) if sid else {}
        message_count = len(updated_session.get('messages', []))
        return {'status': 'ok', 'message_count': message_count}


# 後方互換のため html_formatter の ERROR_MESSAGES を再エクスポート
from src.services.html_formatter import (
    ERROR_MESSAGES,
    format_diagnosis_notification,
    format_error_display,
    format_escalation_display,
    format_feedback_buttons,
    format_medicine_type_notice,
    format_status_card,
    format_system_error,
)


def build_symptom_error_content(
    error_type: str,
    error_details: Dict,
    user_message: str
) -> str:
    """症状推奨エラー時の bot_content を生成する。html_formatter に委譲。"""
    return format_error_display(
        error_type=error_type,
        error_details=error_details,
        user_message=user_message,
        include_feedback_buttons=True
    )


def build_symptom_escalation_content(
    doctor_consultation: str,
    medicine_type: str,
    algorithm: str,
    user_message: str
) -> str:
    """エスカレーションが必要な場合の bot_content を生成する。html_formatter に委譲。"""
    return format_escalation_display(
        doctor_consultation=doctor_consultation,
        medicine_type=medicine_type,
        algorithm=algorithm,
        user_message=user_message,
        include_feedback_buttons=True
    )
