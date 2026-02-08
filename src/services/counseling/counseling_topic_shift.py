"""
話題転換の検知（detect_topic_shift）
"""
import json
import logging
from typing import Dict, List
from openai import OpenAI

from src.services.counseling.counseling_format import format_conversation_history

logger = logging.getLogger(__name__)


def detect_topic_shift(
    user_text: str,
    conversation_history: List[Dict],
    current_counseling_topic: str,
    client: OpenAI
) -> Dict:
    """
    カウンセリングモード中に話題が転換されたかを自動検知
    
    Args:
        user_text: ユーザーの入力テキスト
        conversation_history: 会話履歴
        current_counseling_topic: 現在のカウンセリングトピック
        client: OpenAIクライアントインスタンス
    
    Returns:
        {
            "is_topic_shift": bool,  # 話題転換があったか
            "new_topic_category": str,  # 新しい話題のカテゴリ（Physical/Emotional/etc.）
            "relation_to_current_topic": float,  # 現在のトピックとの関連性スコア（0.0-1.0）
            "confidence": float,  # 確信度
            "reasoning": str  # 判定理由
        }
    """
    # 会話履歴を整形
    history_text = format_conversation_history(conversation_history[-10:])  # 直近10件
    
    prompt = f"""
    あなたは医薬品相談AIアシスタントです。カウンセリング中の会話で、ユーザーが話題を転換したかを判定してください。
    
    【会話履歴】
    {history_text}
    
    【現在のカウンセリングトピック】
    {current_counseling_topic}
    
    【ユーザーの最新入力】
    {user_text}
    
    【判定すべき内容】
    1. ユーザーの最新入力は、現在のカウンセリングトピックの続きか？
    2. それとも、新しい症状や話題について話し始めたか？
    3. 現在のトピックとの関連性はどの程度か？
    
    【話題転換の例】
    - 「あ、そういえば頭も痛くて」→ 話題転換（新しい症状：頭痛）
    - 「左側です」→ カウンセリングの続き（質問への回答）
    - 「ありがとう、もう大丈夫」→ カウンセリング終了の意思表示
    
    【誤検知防止のための判定基準】
    - 文脈の連続性を考慮してください
    - 例: 「（恋の悩みで考えすぎて）頭が痛い」→ カウンセリングの続き（関連性高い）
    - 例: 「（殴られて）頭が痛い」→ 話題転換（新しい身体的症状、関連性低い）
    
    【回答形式】
    JSON形式で回答してください：
    {{
        "is_topic_shift": true/false,
        "new_topic_category": "Physical" | "Emotional" | "Emergency" | null,
        "relation_to_current_topic": 0.0-1.0,
        "confidence": 0.0-1.0,
        "reasoning": "判定理由"
    }}
    
    【重要な判定ルール】
    - relation_to_current_topicが0.5以上の場合、話題転換と判定しない（カウンセリングの続きとして処理）
    - カウンセリング中の質問への回答として解釈しやすい入力（「勉強中」「英語の勉強中」など）は、話題転換と判定しない
    - 新しいカテゴリがPhysical/Emergency かつ relation_to_current_topicが0.5未満の場合のみ、話題転換と判定
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは医薬品相談AIアシスタントです。会話の文脈を理解し、話題転換を正確に検知してください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"話題転換検知エラー: {e}")
        import traceback
        traceback.print_exc()
        # エラー時は安全側に倒して話題転換なしと判定
        return {
            "is_topic_shift": False,
            "new_topic_category": None,
            "relation_to_current_topic": 1.0,
            "confidence": 0.0,
            "reasoning": f"エラーが発生しました: {str(e)}"
        }
