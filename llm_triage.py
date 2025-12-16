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


def check_pain_keywords_override(user_text: str) -> Dict:
    """
    痛み関連キーワードのオーバーライドチェック
    
    痛み関連キーワードが心臓関連キーワードと併用されている場合、
    文脈に関わらず強制的に緊急度を上げる。
    
    Returns:
        {
            "has_pain_keywords": bool,
            "override_emergency": bool,
            "detected_pain_keywords": List[str]
        }
    """
    pain_keywords = [
        "痛い", "痛み", "苦しい", "締め付けられる", "締め付け",
        "圧迫感", "圧迫", "重い", "重圧感", "息苦しい"
    ]
    
    heart_keywords = [
        "心臓", "心臓部", "心臓部分", "心臓付近", "心臓のあたり",
        "心臓が", "心臓も", "心臓に", "心臓を", "胸", "胸部"
    ]
    
    detected_pain = []
    has_heart_keyword = any(keyword in user_text for keyword in heart_keywords)
    
    for keyword in pain_keywords:
        if keyword in user_text:
            detected_pain.append(keyword)
    
    has_pain_keywords = len(detected_pain) > 0
    override_emergency = has_pain_keywords and has_heart_keyword
    
    return {
        "has_pain_keywords": has_pain_keywords,
        "override_emergency": override_emergency,
        "detected_pain_keywords": detected_pain
    }


def check_negative_expressions(user_text: str) -> Dict:
    """
    否定表現の検知
    
    「心臓は痛くない」「心臓に問題はない」などの否定表現を検知。
    
    Returns:
        {
            "has_negative": bool,
            "negative_score": float,  # 0.0-1.0、高いほど緊急度を下げる
            "detected_negations": List[str]
        }
    """
    import re
    
    negative_patterns = [
        r"心臓.*(?:痛くない|問題.*ない|異常.*ない|大丈夫|平気)",
        r"(?:痛くない|問題.*ない|異常.*ない|大丈夫|平気).*心臓",
        r"心臓.*(?:は|が).*(?:痛くない|問題.*ない|異常.*ない)",
        r"胸.*(?:痛くない|問題.*ない|異常.*ない|大丈夫|平気)",
    ]
    
    detected_negations = []
    for pattern in negative_patterns:
        matches = re.findall(pattern, user_text)
        if matches:
            detected_negations.extend(matches)
    
    has_negative = len(detected_negations) > 0
    # 否定表現がある場合、緊急度を0.5下げる
    negative_score = 0.5 if has_negative else 0.0
    
    return {
        "has_negative": has_negative,
        "negative_score": negative_score,
        "detected_negations": detected_negations
    }


def check_exclusion_patterns(user_text: str) -> Dict:
    """
    除外キーワード（Negative Lookahead）のチェック
    
    明らかに比喩・否定であるパターンを検知し、スコアを下げる。
    
    Returns:
        {
            "has_exclusion": bool,
            "exclusion_score_reduction": float,  # 0.0-1.0、緊急度スコアから減算
            "detected_patterns": List[str]
        }
    """
    import re
    
    exclusion_patterns = [
        (r"心臓に毛が生え", 0.8),
        (r"心臓が止まるかと思った", 0.7),  # 驚きの表現
        (r"心臓が飛び出", 0.7),  # 驚きの表現
        (r"心臓が.*(?:飛び出|止まる).*と思った", 0.7),
        (r"心臓.*(?:ドキドキ|バクバク).*だけ", 0.3),  # 「心臓がドキドキするだけ」など
    ]
    
    detected_patterns = []
    max_reduction = 0.0
    
    for pattern, reduction in exclusion_patterns:
        if re.search(pattern, user_text):
            detected_patterns.append(pattern)
            max_reduction = max(max_reduction, reduction)
    
    has_exclusion = len(detected_patterns) > 0
    
    return {
        "has_exclusion": has_exclusion,
        "exclusion_score_reduction": max_reduction,
        "detected_patterns": detected_patterns
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
    
    【後方互換性のため残す】
    新しいcheck_heart_emergency_with_context関数を使用することを推奨
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


def check_heart_emergency_with_context(
    user_text: str,
    triage_result: Dict = None,
    counseling_mode: Dict = None,
    client: OpenAI = None
) -> Dict:
    """
    文脈を考慮した心臓緊急チェック
    
    Args:
        user_text: ユーザーの入力テキスト
        triage_result: LLMトリアージ結果（オプション）
        counseling_mode: カウンセリングモード状態（オプション）
        client: OpenAIクライアントインスタンス（オプション、追加判定が必要な場合）
    
    Returns:
        {
            "is_emergency": bool,
            "confidence": float,  # 0.0-1.0
            "context_type": str,  # "romantic", "exercise", "nervous", "metaphorical", "actual_emergency"
            "reasoning": str,
            "should_interrupt_counseling": bool
        }
    """
    # ステップ1: ルールベース安全性層（最優先）
    pain_check = check_pain_keywords_override(user_text)
    negative_check = check_negative_expressions(user_text)
    exclusion_check = check_exclusion_patterns(user_text)
    
    # 痛み関連キーワードのオーバーライド（最優先）
    if pain_check["override_emergency"]:
        return {
            "is_emergency": True,
            "confidence": 0.9,
            "context_type": "actual_emergency",
            "reasoning": f"痛み関連キーワード（{', '.join(pain_check['detected_pain_keywords'])}）が検出されました。文脈に関わらず緊急対応が必要です。",
            "should_interrupt_counseling": True
        }
    
    # ステップ2: キーワードマッチング
    heart_keywords = [
        "心臓", "心臓部", "心臓部分", "心臓付近", "心臓のあたり",
        "心臓が", "心臓も", "心臓に", "心臓を"
    ]
    
    arrhythmia_keywords = [
        "動悸", "ドキドキが止まらない", "脈が飛ぶ", "不整脈",
        "脈が", "脈が速い", "脈が遅い", "脈が不規則"
    ]
    
    has_heart_keyword = any(keyword in user_text for keyword in heart_keywords)
    has_arrhythmia_keyword = any(keyword in user_text for keyword in arrhythmia_keywords)
    
    if not (has_heart_keyword or has_arrhythmia_keyword):
        return {
            "is_emergency": False,
            "confidence": 0.0,
            "context_type": "none",
            "reasoning": "心臓関連キーワードが検出されませんでした。",
            "should_interrupt_counseling": False
        }
    
    # 初期スコア（キーワードが検出された場合）
    emergency_score = 0.7
    context_type = "actual_emergency"
    reasoning_parts = []
    
    # ステップ3: LLMトリアージ結果の活用
    if triage_result:
        category = triage_result.get("category", "")
        subcategory = triage_result.get("subcategory", "").lower()
        confidence = triage_result.get("confidence", 0.5)
        
        if category == "Emergency" and confidence >= 0.8:
            emergency_score = 0.95
            context_type = "actual_emergency"
            reasoning_parts.append("トリアージ結果がEmergency（高確信度）")
        elif category == "Emotional":
            if "romantic" in subcategory or "romantic_concern" in subcategory:
                emergency_score = 0.3
                context_type = "romantic"
                reasoning_parts.append("トリアージ結果がEmotional（恋愛関連）")
            elif "anxiety" in subcategory or "nervous" in subcategory:
                emergency_score = 0.4
                context_type = "nervous"
                reasoning_parts.append("トリアージ結果がEmotional（不安・緊張）")
            else:
                emergency_score = 0.5
                context_type = "metaphorical"
                reasoning_parts.append("トリアージ結果がEmotional")
        elif confidence < 0.7:
            # 低確信度の場合は追加判定が必要
            emergency_score = 0.6
            reasoning_parts.append("トリアージ結果の確信度が低い")
    
    # ステップ4: 除外パターンの適用
    if exclusion_check["has_exclusion"]:
        emergency_score -= exclusion_check["exclusion_score_reduction"]
        reasoning_parts.append(f"除外パターン検出（{exclusion_check['exclusion_score_reduction']:.1f}減点）")
    
    # ステップ5: 否定表現の適用（痛みキーワードがない場合のみ）
    if negative_check["has_negative"] and not pain_check["has_pain_keywords"]:
        emergency_score -= negative_check["negative_score"]
        reasoning_parts.append(f"否定表現検出（{negative_check['negative_score']:.1f}減点）")
    
    # スコアを0.0-1.0の範囲に制限
    emergency_score = max(0.0, min(1.0, emergency_score))
    
    # ステップ6: カウンセリングモード中の判定
    should_interrupt = True
    if counseling_mode and counseling_mode.get('active'):
        symptom_type = counseling_mode.get('symptom_type', '')
        # カウンセリング中の症状タイプが恋愛関連の場合、より慎重に判定
        if symptom_type == 'romantic_concern' and context_type == 'romantic':
            emergency_score *= 0.7  # スコアを下げる
            should_interrupt = emergency_score >= 0.6
            reasoning_parts.append("カウンセリング中（恋愛関連）のため慎重に判定")
    
    # 最終判定
    is_emergency = emergency_score >= 0.6
    
    if not reasoning_parts:
        reasoning = "キーワードマッチングによる判定"
    else:
        reasoning = " | ".join(reasoning_parts)
    
    return {
        "is_emergency": is_emergency,
        "confidence": emergency_score,
        "context_type": context_type,
        "reasoning": reasoning,
        "should_interrupt_counseling": should_interrupt
    }

