"""
満足度分析（analyze_user_satisfaction）
"""
import json
import logging
from typing import Dict, List
from openai import OpenAI

from src.services.counseling.counseling_format import format_conversation_history

logger = logging.getLogger(__name__)


def analyze_user_satisfaction(
    user_response: str,
    conversation_history: List[Dict],
    client: OpenAI
) -> Dict:
    """
    ユーザーの満足度を分析
    
    Returns:
        {
            "satisfaction_score": float,  # 0.0-1.0
            "wants_to_continue": bool,
            "is_frustrated": bool,
            "reasoning": str
        }
    """
    history_text = format_conversation_history(conversation_history[-5:])
    
    prompt = f"""
あなたは医薬品相談AIアシスタントです。ユーザーの最新の回答から満足度を分析してください。

【会話履歴】
{history_text}

【ユーザーの最新の回答】
{user_response}

【分析すべき内容】
1. ユーザーの満足度（0.0-1.0）
2. 会話を続けたいかどうか
3. フラストレーションを感じているかどうか

【満足度の指標】
- 「ありがとう」「大丈夫」「解決した」など → 満足度高（0.7以上）
- 「わからない」「別に」「特にない」など → 満足度低（0.3以下）
- 通常の回答 → 満足度中（0.4-0.6）

【回答形式】
JSON形式で回答してください：
{{
    "satisfaction_score": 0.0-1.0,
    "wants_to_continue": true/false,
    "is_frustrated": true/false,
    "reasoning": "分析理由"
}}
"""
    try:
        from src.services.counseling.counseling_llm import counseling_chat
        response = counseling_chat(
            client,
            "counseling_satisfaction",
            [
                {"role": "system", "content": "あなたは医薬品相談AIアシスタントです。ユーザーの満足度を正確に分析してください。"},
                {"role": "user", "content": prompt},
            ],
            max_tokens=200,
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"満足度分析エラー: {e}")
        return {
            "satisfaction_score": 0.5,
            "wants_to_continue": True,
            "is_frustrated": False,
            "reasoning": f"エラー: {str(e)}"
        }
