"""
LLMトリアージモジュール
ユーザー入力をカテゴリに分類し、適切な処理フローに振り分ける
"""

import json
import logging
from typing import Dict, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

TRIAGE_PROMPT = """
あなたは薬剤師です。ユーザーの入力を以下の5つのカテゴリに分類してください。

【カテゴリ】
1. Physical（身体的症状）: 頭痛、発熱、のどの痛み、腹痛など、身体的な症状
2. Emotional（精神的・感情的症状）: 緊張、不安、ストレス、恋愛の悩みなど、心理的な症状
3. Emergency（緊急性が高い症状）: 心臓が痛い、呼吸困難、激しい頭痛など、即座に医療機関受診が必要な症状
4. Ask（医薬品質問）: 特定の医薬品についての質問
5. Other（その他）: 挨拶、不明な入力など

【重要な判定ルール】
- 「心臓が痛い」「心臓部分が痛い」→ Emergency（身体的・緊急性高）
- 「心が痛い」「心が痛む」→ Emotional または Ambiguous_Heart（曖昧性あり）
- 「恋の病」「好きな人」→ Emotional（比喩的表現）
- 「緊張する」「不安」→ Emotional
- 「頭痛」「発熱」→ Physical

【曖昧性の処理】
「心が痛い」のような表現は、身体的症状（心臓疾患）と心理的症状の両方の可能性があります。
この場合は、subcategoryに"Ambiguous_Heart"を設定し、詳細質問を生成する必要があることを示してください。

【confidence（確信度）の重要性】
- confidenceは0.0-1.0の範囲で、判定の確信度を示します
- 0.7未満の場合は、判定に不確実性があることを示します
- 低い確信度の場合は、ユーザーに確認を求める必要があります

【回答形式】
JSON形式で回答してください。以下の形式を厳密に守ってください：
{
    "category": "カテゴリ名（Physical/Emotional/Emergency/Ask/Other）",
    "confidence": 0.0-1.0の数値,
    "subcategory": "詳細カテゴリ（例: heart_pain, anxiety, headache）",
    "requires_immediate_action": true/false,
    "reasoning": "判定理由"
}
"""


def llm_triage(user_text: str, client: OpenAI) -> Dict:
    """
    LLMを使用してユーザー入力をカテゴリに分類
    
    Args:
        user_text: ユーザーの入力テキスト
        client: OpenAIクライアントインスタンス
    
    Returns:
        {
            "category": "Physical" | "Emotional" | "Emergency" | "Ask" | "Other",
            "confidence": 0.0-1.0,
            "subcategory": str,  # 詳細カテゴリ（例: "heart_pain", "anxiety"）
            "requires_immediate_action": bool,  # 緊急対応が必要か
            "reasoning": str  # 判定理由
        }
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは薬剤師です。ユーザーの入力を正確にカテゴリ分類してください。"},
                {"role": "user", "content": f"{TRIAGE_PROMPT}\n\n【ユーザーの入力】\n{user_text}"}
            ],
            temperature=0.1,
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        
        # JSONをパース
        try:
            result = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析エラー: {e}, レスポンス: {content}")
            # フォールバック: デフォルト値を返す
            return {
                "category": "Other",
                "confidence": 0.0,
                "subcategory": "unknown",
                "requires_immediate_action": False,
                "reasoning": f"JSON解析エラー: {str(e)}"
            }
        
        # 必須フィールドの検証
        category = result.get("category", "Other")
        confidence = float(result.get("confidence", 0.0))
        subcategory = result.get("subcategory", "unknown")
        requires_immediate_action = bool(result.get("requires_immediate_action", False))
        reasoning = result.get("reasoning", "判定理由が提供されませんでした")
        
        # confidenceの範囲チェック
        if confidence < 0.0:
            confidence = 0.0
        elif confidence > 1.0:
            confidence = 1.0
        
        # categoryの検証
        valid_categories = ["Physical", "Emotional", "Emergency", "Ask", "Other"]
        if category not in valid_categories:
            logger.warning(f"無効なカテゴリ: {category}, デフォルトでOtherに設定")
            category = "Other"
            confidence = 0.5
        
        return {
            "category": category,
            "confidence": confidence,
            "subcategory": subcategory,
            "requires_immediate_action": requires_immediate_action,
            "reasoning": reasoning
        }
        
    except Exception as e:
        logger.error(f"LLMトリアージエラー: {e}")
        import traceback
        traceback.print_exc()
        # エラー時は安全側に倒してOtherを返す
        return {
            "category": "Other",
            "confidence": 0.0,
            "subcategory": "error",
            "requires_immediate_action": False,
            "reasoning": f"エラーが発生しました: {str(e)}"
        }


def check_heart_emergency(user_text: str) -> bool:
    """
    「心臓」「動悸」「不整脈」を含む入力を検出し、緊急対応が必要か判定
    
    【安全弁強化版の判定ルール】
    - 「心臓」「動悸」「不整脈」が含まれる → 常に緊急対応（除外ロジックなし）
    - 「心が痛い」でも「心臓」が含まれている場合は緊急対応
    - 例: 「失恋して心が痛いし、実際に心臓もバクバクして痛い」→ 緊急対応
    - 例: 「動悸が止まらない」→ 緊急対応（恋愛文脈でも安全側に倒す）
    
    【医療安全上の理由】
    心理的キーワードがあっても、身体的症状（不整脈、タコツボ心筋症など）の
    可能性を見逃すリスクを避けるため、常に緊急対応を優先します。
    
    【追加キーワード】
    - 動悸関連: 「動悸」「ドキドキが止まらない」「脈が飛ぶ」「不整脈」
    - 心臓関連: 「心臓」「心臓部」「心臓部分」「心臓付近」
    
    【注意】
    - 「胸が苦しい」「胸の圧迫感」は循環器系の可能性もあるが、
      精神的な場合も多いため、LLMトリアージ（Emergency vs Emotional）に任せる
    - ステップ0では「心臓」「動悸」「不整脈」といった臓器・現象名のみをチェック
    """
    heart_keywords = [
        "心臓", "心臓部", "心臓部分", "心臓付近", "心臓のあたり",
        "心臓が", "心臓も", "心臓に", "心臓を"
    ]
    
    arrhythmia_keywords = [
        "動悸", "ドキドキが止まらない", "脈が飛ぶ", "不整脈",
        "脈が", "脈が速い", "脈が遅い", "脈が不規則"
    ]
    
    # 「心臓」または「動悸・不整脈」が含まれている場合は常に緊急対応（除外ロジックなし）
    return (
        any(keyword in user_text for keyword in heart_keywords) or
        any(keyword in user_text for keyword in arrhythmia_keywords)
    )

