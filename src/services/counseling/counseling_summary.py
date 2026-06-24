"""
カウンセリング要約の生成（generate_counseling_summary）
"""
import json
import logging
from typing import Dict, List
from openai import OpenAI

from src.services.counseling.counseling_format import format_conversation_history
from src.services.counseling.counseling_logger import log_counseling_response

logger = logging.getLogger(__name__)


def generate_counseling_summary(
    counseling_mode: Dict,
    interpretation: Dict,
    client: OpenAI,
    conversation_history: List[Dict] = None,
    session_id: str = None,
    user_text: str = None
) -> str:
    """
    カウンセリングの総合的な返信を生成
    
    Args:
        counseling_mode: カウンセリングモードの状態
        interpretation: 解釈結果
        client: OpenAIクライアントインスタンス
        conversation_history: 会話履歴（直近10件まで使用）
        session_id: セッションID（ログ記録用）
    
    Returns:
        総合的な返信テキスト
    """
    collected_info = counseling_mode.get('collected_info', {})
    symptom_type = counseling_mode.get('symptom_type', 'general_emotional')
    
    # 会話履歴の準備（直近10件）
    history_context = ""
    if conversation_history:
        recent_history = conversation_history[-10:]  # 直近10件
        history_text = format_conversation_history(recent_history)
        if history_text.strip():
            history_context = f"""
    
    【会話履歴（文脈理解のため）】
    {history_text}
    """
    
    prompt = f"""
    あなたは医薬品相談AIアシスタントです。カウンセリングで収集した情報を基に、
    総合的な返信を生成してください。
    {history_context}
    【収集した情報】
    {json.dumps(collected_info, ensure_ascii=False, indent=2)}
    
    【症状タイプ】
    {symptom_type}
    
    【返信の要件】
    - 収集した情報を要約する
    - 適切なアドバイスを提供する
    - 必要に応じて医療機関受診を推奨する
    - 共感的で温かいトーンを保つ
    - 会話履歴がある場合は、文脈を考慮した返信を生成する
    
    【返信を生成してください】
    """
    
    try:
        from src.services.counseling.counseling_llm import counseling_chat
        response = counseling_chat(
            client,
            "counseling_summary",
            [
                {"role": "system", "content": "あなたは医薬品相談AIアシスタントです。総合的な返信を生成してください。返信は200文字以内に収めてください。"},
                {"role": "user", "content": prompt},
            ],
            max_tokens=200,
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # 200文字を超える場合は切り詰める
        if len(response_text) > 200:
            response_text = response_text[:200] + "..."
        
        # ログ記録（通常時は会話履歴なし）
        if session_id:
            log_counseling_response(
                session_id=session_id,
                response_content=response_text,
                response_type="counseling_summary",
                category=None,
                confidence=None,
                counseling_mode=counseling_mode,
                user_input=user_text,
                conversation_history=conversation_history
            )
        
        return response_text
    except Exception as e:
        logger.error(f"カウンセリング要約生成エラー: {e}")
        error_response = "お話を伺えました。ありがとうございます。必要に応じて医療機関にご相談されることをお勧めします。"
        
        # エラー時もログ記録を試みる
        if session_id:
            try:
                log_counseling_response(
                    session_id=session_id,
                    response_content=error_response,
                    response_type="counseling_summary_error",
                    category=None,
                    confidence=None,
                    counseling_mode=counseling_mode,
                    user_input=user_text,
                    conversation_history=conversation_history
                )
            except Exception:
                pass
        
        return error_response
