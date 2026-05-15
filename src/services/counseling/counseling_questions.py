"""
フォローアップ質問の生成（should_generate_question_non_medical, generate_supportive_question）
"""
import logging
from typing import Dict, List
from openai import OpenAI

from src.services.counseling.counseling_format import format_conversation_history

logger = logging.getLogger(__name__)


def should_generate_question_non_medical(
    user_response: str,
    collected_info: Dict,
    question_count: int,
    conversation_history: List[Dict],
    client: OpenAI
) -> Dict:
    """
    医療関連以外のカウンセリングで質問を生成すべきか判断
    
    Returns:
        {
            "should_ask": bool,
            "question_type": str,  # "supportive" | "none"
            "reason": str
        }
    """
    # 質問回数が既に2回以上の場合、質問をスキップ
    if question_count >= 2:
        return {
            "should_ask": False,
            "question_type": "none",
            "reason": "question_limit_reached"
        }
    
    # ユーザーが詳しく話したい場合のみ、支援的な質問を生成
    if len(user_response) > 50 and question_count < 2:
        return {
            "should_ask": True,
            "question_type": "supportive",
            "reason": "user_wants_to_talk"
        }
    
    # デフォルト: 質問をスキップ
    return {
        "should_ask": False,
        "question_type": "none",
        "reason": "default_no_question"
    }


def generate_supportive_question(
    symptom_type: str,
    user_response: str,
    conversation_history: List[Dict],
    client: OpenAI
) -> str:
    """
    支援的な質問を生成（医療関連以外のみ）
    
    例:
    - "何か手助けできることはありますか？"
    - "もっと詳しく聞かせてくれますか？"
    - "他に気になることはありますか？"
    """
    history_text = format_conversation_history(conversation_history[-5:])
    
    prompt = f"""
あなたは医薬品相談AIアシスタントです。ユーザーを応援し、支援するための
自然で親しみやすい質問を1つ生成してください。

【会話履歴】
{history_text}

【ユーザーの最新の回答】
{user_response}

【症状タイプ】
{symptom_type}

【質問の要件】
- 支援的で親しみやすいトーン
- 開かれた質問（Yes/Noで答えられない質問）
- ユーザーが話しやすい質問
- 1つだけ生成
- 50文字以内

【質問を生成してください】
"""
    try:
        from src.services.counseling.counseling_llm import counseling_chat
        response = counseling_chat(
            client,
            "counseling_questions",
            [
                {"role": "system", "content": "あなたは医薬品相談AIアシスタントです。支援的で親しみやすい質問を生成してください。"},
                {"role": "user", "content": prompt},
            ],
            max_tokens=100,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"支援的質問生成エラー: {e}")
        return "何か手助けできることはありますか？"
