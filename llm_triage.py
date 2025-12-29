"""
LLMトリアージモジュール
ユーザー入力をカテゴリに分類し、適切な処理フローに振り分ける
"""

import json
import logging
from typing import Dict, Optional, List
from openai import OpenAI

logger = logging.getLogger(__name__)

# LLMトリアージ結果のキャッシュ（完全一致のみ）
_triage_cache: Dict[str, Dict] = {}
_MAX_CACHE_SIZE = 1000

TRIAGE_PROMPT = """
あなたは薬剤師です。ユーザーの入力を以下の5つのカテゴリに分類してください。

【カテゴリ】
1. Physical（身体的症状）: 頭痛、発熱、のどの痛み、腹痛など、身体的な症状
2. Emotional（精神的・感情的症状）: 緊張、不安、ストレス、恋愛の悩みなど、心理的な症状
3. Emergency（緊急性が高い症状）: 心臓が痛い、呼吸困難、激しい頭痛など、即座に医療機関受診が必要な症状
4. Ask（医薬品質問）: 特定の医薬品についての質問
5. Other（その他）: 挨拶、不明な入力、店舗案内、遺失物関連、在庫確認、周辺施設の案内など

【重要な判定ルール】
- 「心臓が痛い」「心臓部分が痛い」→ Emergency（身体的・緊急性高）
- 「心が痛い」「心が痛む」→ Emotional または Ambiguous_Heart（曖昧性あり）
- 「恋の病」「好きな人」→ Emotional（比喩的表現）
- 「緊張する」「不安」→ Emotional
- 「頭痛」「発熱」→ Physical
- **「眠くて寝てしまう」「仕事中に寝てしまう」「眠気が強い」「眠い」「眠たい」など、眠気（sleepiness/drowsiness）の症状を訴える → Physical（subcategory: drowsiness）**
- **「眠れない」「不眠」「睡眠不足」「寝つきが悪い」など、不眠（insomnia）の症状を訴える → Emotional（subcategory: insomnia）**
- **「睡眠薬を教えて」「睡眠薬について」「睡眠薬を知りたい」「睡眠改善薬を教えて」など、睡眠薬に関する質問 → Emotional（subcategory: insomnia）を優先**
- **注意: 眠気と不眠は明確に区別してください。眠気は日中の眠さ、不眠は夜間に眠れない症状です。**
- **注意: 睡眠薬に関する質問は、Askカテゴリではなく、Emotionalカテゴリ（subcategory: insomnia）として分類してください。これは、不眠の症状に対するカウンセリングが必要なためです。**
- **「場所を教えてください」「どこにありますか」「トイレはどこですか」など、店舗案内に関する質問 → Other（subcategory: store_inquiry）**
- **「忘れ物を拾いました」「落とし物を拾いました」など、遺失物に関する質問 → Other（subcategory: lost_and_found）**
- **「ありますか」「在庫」「取り寄せ」など、在庫確認に関する質問 → Other（subcategory: store_inquiry/inventory）**
- **「近くに」「周辺に」「コンビニ」「銀行」など、周辺施設に関する質問 → Other（subcategory: store_inquiry/facilities）**
- **「免税」「免税対応」などのキーワードがある場合 → Other（subcategory: store_inquiry/tax_free）**
- **「観光地」「観光」「名所」などのキーワードがある場合 → Other（subcategory: store_inquiry/tourism）**
- **「営業時間」「アクセス」「開店」「閉店」などのキーワードがある場合 → Other（subcategory: store_inquiry/business_hours）**
- **「支払い」「決済」「カード」「現金」などのキーワードがある場合 → Other（subcategory: store_inquiry/payment）**
- **「駐車場」「パーキング」「駐車」などのキーワードがある場合 → Other（subcategory: store_inquiry/parking）**
- **「サービス」「取り扱い」「配達」などのキーワードがある場合 → Other（subcategory: store_inquiry/services）**
- **その他の挨拶や不明な入力 → Other（subcategory: general_other）**

【比喩的表現・アニメ・小説のセリフの検出】
以下のような表現は比喩的表現やアニメ・小説のセリフの可能性が高いため、OtherカテゴリまたはEmotionalカテゴリ（metaphoricalサブカテゴリ）として分類してください：
- 「心臓を捧げよ」「心臓を捧げる」→ Other（アニメ・小説のセリフ）またはEmotional（metaphorical）
- 「心臓を[動詞]」構文で、実際の身体的症状を表していない表現
- 明らかに比喩的・文学的・創作的表現
- 会話の文脈から、実際の身体的症状ではなく比喩的表現であることが明らかな場合

【会話履歴の考慮】
会話履歴が提供されている場合、以下の点を考慮してください：
- 直前のメッセージに恋愛関連のキーワード（「失恋」「好きな人」など）がある場合、現在のメッセージも恋愛文脈として扱う
- 会話の流れから、比喩的表現であることが推測できる場合は、それを反映する
- セッション全体の文脈を考慮して判定する

【曖昧性の処理】
「心が痛い」のような表現は、身体的症状（心臓疾患）と心理的症状の両方の可能性があります。
この場合は、subcategoryに"Ambiguous_Heart"を設定し、詳細質問を生成する必要があることを示してください。

【confidence（確信度）の重要性】
- confidenceは0.0-1.0の範囲で、判定の確信度を示します
- 0.7未満の場合は、判定に不確実性があることを示します
- 低い確信度の場合は、ユーザーに確認を求める必要があります
- 比喩的表現の可能性がある場合は、confidenceを低めに設定する

【回答形式】
JSON形式で回答してください。以下の形式を厳密に守ってください：
{
    "category": "カテゴリ名（Physical/Emotional/Emergency/Ask/Other）",
    "confidence": 0.0-1.0の数値,
    "subcategory": "詳細カテゴリ（例: heart_pain, anxiety, headache, drowsiness, insomnia, metaphorical, store_inquiry, store_inquiry/inventory, store_inquiry/facilities, store_inquiry/tax_free, store_inquiry/tourism, store_inquiry/business_hours, store_inquiry/payment, store_inquiry/parking, store_inquiry/services, lost_and_found, general_other）",
    "requires_immediate_action": true/false,
    "reasoning": "判定理由"
}
"""


def llm_triage(user_text: str, client: OpenAI, use_cache: bool = True) -> Dict:
    """
    LLMを使用してユーザー入力をカテゴリに分類
    
    Args:
        user_text: ユーザーの入力テキスト
        client: OpenAIクライアントインスタンス
        use_cache: キャッシュを使用するか（デフォルト: True）
    
    Returns:
        {
            "category": "Physical" | "Emotional" | "Emergency" | "Ask" | "Other",
            "confidence": 0.0-1.0,
            "subcategory": str,  # 詳細カテゴリ（例: "heart_pain", "anxiety"）
            "requires_immediate_action": bool,  # 緊急対応が必要か
            "reasoning": str  # 判定理由
        }
    """
    # キャッシュをチェック（完全一致のみ）
    if use_cache:
        cache_key = user_text.strip()
        if cache_key in _triage_cache:
            logger.debug(f"💾 キャッシュからLLMトリアージ結果を取得: {cache_key[:50]}...")
            return _triage_cache[cache_key].copy()
    
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
        
        result = {
            "category": category,
            "confidence": confidence,
            "subcategory": subcategory,
            "requires_immediate_action": requires_immediate_action,
            "reasoning": reasoning
        }
        
        # キャッシュに保存（完全一致のみ）
        if use_cache:
            cache_key = user_text.strip()
            if len(_triage_cache) >= _MAX_CACHE_SIZE:
                # 最も古いエントリを削除（FIFO方式）
                oldest_key = next(iter(_triage_cache))
                del _triage_cache[oldest_key]
                logger.debug(f"💾 キャッシュが満杯のため、最も古いエントリを削除: {oldest_key[:50]}...")
            
            _triage_cache[cache_key] = result.copy()
            logger.debug(f"💾 LLMトリアージ結果をキャッシュに保存: {cache_key[:50]}...")
        
        return result
        
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


def check_pain_keywords_override(user_text: str, context_type: str = None) -> Dict:
    """
    痛み関連キーワードのオーバーライドチェック（文脈考慮版）
    
    痛み関連キーワードが心臓関連キーワードと併用されている場合、
    文脈を考慮して緊急度を判定する。
    
    Args:
        user_text: ユーザーの入力テキスト
        context_type: 文脈タイプ（"romantic", "exercise", "nervous", "metaphorical", "actual_emergency"）
    
    Returns:
        {
            "has_pain_keywords": bool,
            "override_emergency": bool,
            "detected_pain_keywords": List[str],
            "context_mitigation": float  # 文脈による緊急度の緩和（0.0-1.0）
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
    
    # 恋愛文脈キーワード
    romantic_keywords = [
        "失恋", "好きな人", "恋愛", "恋", "ときめき", "ドキドキ", "バクバク",
        "好き", "片思い", "両思い", "告白", "振られた", "別れた"
    ]
    
    detected_pain = []
    has_heart_keyword = any(keyword in user_text for keyword in heart_keywords)
    
    for keyword in pain_keywords:
        if keyword in user_text:
            detected_pain.append(keyword)
    
    has_pain_keywords = len(detected_pain) > 0
    
    # 文脈による緊急度の緩和を計算
    context_mitigation = 0.0
    
    # 恋愛文脈が明確な場合、緊急度を緩和（ただし完全には無視しない）
    if context_type == "romantic" or any(keyword in user_text for keyword in romantic_keywords):
        # 恋愛文脈が明確な場合、緊急度を0.5下げる（注意喚起レベルに）
        context_mitigation = 0.5
        # ただし、「心臓が痛い」のように直接的な表現の場合は緩和を減らす
        if "心臓" in user_text and any(p in user_text for p in ["痛い", "痛み"]):
            context_mitigation = 0.3  # より慎重に
    
    # オーバーライド判定（文脈緩和を考慮）
    # 恋愛文脈が明確な場合は、オーバーライドを緩和（緊急対応ではなく注意喚起レベル）
    if has_pain_keywords and has_heart_keyword:
        if context_mitigation >= 0.5:
            # 恋愛文脈が明確な場合、オーバーライドを緩和
            override_emergency = False  # 緊急対応ではなく、注意喚起レベル
        else:
            # 文脈が不明確または実際の緊急の可能性がある場合
            override_emergency = True
    else:
        override_emergency = False
    
    return {
        "has_pain_keywords": has_pain_keywords,
        "override_emergency": override_emergency,
        "detected_pain_keywords": detected_pain,
        "context_mitigation": context_mitigation
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


def detect_metaphorical_expression(
    user_text: str,
    conversation_history: List[Dict] = None,
    client: OpenAI = None
) -> Dict:
    """
    LLMを使用して比喩的表現を検出
    
    アニメ・小説のセリフ、比喩的表現を判定し、実際の身体的症状ではないことを識別する。
    
    Args:
        user_text: ユーザーの入力テキスト
        conversation_history: 会話履歴（オプション、最大20メッセージ）
        client: OpenAIクライアントインスタンス（必須）
    
    Returns:
        {
            "is_metaphorical": bool,
            "confidence": float,  # 0.0-1.0
            "reasoning": str,
            "detected_type": str  # "anime_quote", "literary_metaphor", "idiom", "none"
        }
    """
    if not client:
        logger.warning("detect_metaphorical_expression: OpenAIクライアントが提供されていません")
        return {
            "is_metaphorical": False,
            "confidence": 0.0,
            "reasoning": "OpenAIクライアントが提供されていません",
            "detected_type": "none"
        }
    
    try:
        # 会話履歴を整形（最大20メッセージ）
        history_text = ""
        if conversation_history:
            recent_history = conversation_history[-20:] if len(conversation_history) > 20 else conversation_history
            history_messages = []
            for msg in recent_history:
                msg_type = msg.get('type', 'unknown')
                msg_content = msg.get('content', '')
                if msg_type == 'user':
                    history_messages.append(f"ユーザー: {msg_content}")
                elif msg_type == 'bot':
                    history_messages.append(f"ボット: {msg_content}")
            
            if history_messages:
                history_text = "\n".join(history_messages[-10:])  # 直近10メッセージのみ使用
        
        metaphor_prompt = """
あなたは薬剤師です。ユーザーの入力が比喩的表現、アニメ・小説のセリフ、または実際の身体的症状かを判定してください。

【判定基準】
1. アニメ・小説のセリフ: 「心臓を捧げよ」など、作品からの引用
2. 文学的比喩: 実際の身体的症状ではなく、感情や状況を表現する比喩
3. 慣用句・慣用表現: 「心臓が止まるかと思った」など、驚きの表現
4. 実際の身体的症状: 実際に身体的な症状を訴えている

【会話履歴の考慮】
会話履歴が提供されている場合、会話の流れから文脈を判断してください。
- 直前のメッセージに恋愛関連のキーワードがある場合、比喩的表現の可能性が高い
- 会話の流れから、アニメ・小説のセリフであることが推測できる場合

【回答形式】
JSON形式で回答してください：
{
    "is_metaphorical": true/false,
    "confidence": 0.0-1.0の数値,
    "reasoning": "判定理由",
    "detected_type": "anime_quote" | "literary_metaphor" | "idiom" | "none"
}
"""
        
        user_prompt = f"{metaphor_prompt}\n\n【ユーザーの入力】\n{user_text}"
        if history_text:
            user_prompt += f"\n\n【会話履歴】\n{history_text}"
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは薬剤師です。比喩的表現を正確に検出してください。"},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=200,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        
        try:
            result = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"比喩的表現検出のJSON解析エラー: {e}, レスポンス: {content}")
            return {
                "is_metaphorical": False,
                "confidence": 0.0,
                "reasoning": f"JSON解析エラー: {str(e)}",
                "detected_type": "none"
            }
        
        is_metaphorical = bool(result.get("is_metaphorical", False))
        confidence = float(result.get("confidence", 0.0))
        reasoning = result.get("reasoning", "判定理由が提供されませんでした")
        detected_type = result.get("detected_type", "none")
        
        # confidenceの範囲チェック
        if confidence < 0.0:
            confidence = 0.0
        elif confidence > 1.0:
            confidence = 1.0
        
        logger.info(f"🔍 比喩的表現検出結果: is_metaphorical={is_metaphorical}, confidence={confidence:.2f}, type={detected_type}")
        logger.debug(f"   判定理由: {reasoning}")
        
        return {
            "is_metaphorical": is_metaphorical,
            "confidence": confidence,
            "reasoning": reasoning,
            "detected_type": detected_type
        }
        
    except Exception as e:
        logger.error(f"比喩的表現検出エラー: {e}")
        import traceback
        traceback.print_exc()
        return {
            "is_metaphorical": False,
            "confidence": 0.0,
            "reasoning": f"エラーが発生しました: {str(e)}",
            "detected_type": "none"
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
        # アニメ・小説のセリフパターン
        (r"心臓を捧げよ", 0.9),  # 進撃の巨人のセリフ
        (r"心臓を捧げる", 0.9),  # 進撃の巨人のセリフ
        (r"心臓を.*捧げ", 0.9),  # 類似表現
        # 比喩的表現パターン（「心臓を[動詞]」構文）
        (r"心臓を.*(?:捧げ|差し出|捧げる|差し出す|捧げよ)", 0.85),  # 比喩的表現
        (r"心臓.*(?:を|が).*(?:捧げ|差し出|捧げる|差し出す)", 0.85),  # 比喩的表現
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


# 文脈タイプに応じた動的閾値
EMERGENCY_THRESHOLDS = {
    'romantic': 0.7,      # 恋愛文脈: より慎重に
    'nervous': 0.65,      # 緊張・不安: やや慎重に
    'exercise': 0.65,     # 運動後: やや慎重に
    'metaphorical': 0.8,  # 比喩的表現: 非常に慎重に
    'actual_emergency': 0.6,  # 実際の緊急: 標準
    'none': 0.6           # デフォルト
}


def check_heart_emergency_with_context(
    user_text: str,
    triage_result: Dict = None,
    counseling_mode: Dict = None,
    client: OpenAI = None,
    conversation_history: List[Dict] = None
) -> Dict:
    """
    文脈を考慮した心臓緊急チェック（会話履歴対応版）
    
    Args:
        user_text: ユーザーの入力テキスト
        triage_result: LLMトリアージ結果（オプション）
        counseling_mode: カウンセリングモード状態（オプション）
        client: OpenAIクライアントインスタンス（オプション、追加判定が必要な場合）
        conversation_history: 会話履歴（オプション、最大20メッセージ）
    
    Returns:
        {
            "is_emergency": bool,
            "confidence": float,  # 0.0-1.0
            "context_type": str,  # "romantic", "exercise", "nervous", "metaphorical", "actual_emergency"
            "reasoning": str,
            "should_interrupt_counseling": bool,
            "metaphor_detection": Dict  # 比喩的表現検出結果（オプション）
        }
    """
    logger.info(f"🔍 心臓緊急チェック開始: {user_text[:50]}...")
    logger.debug(f"   会話履歴: {len(conversation_history) if conversation_history else 0}メッセージ")
    
    # ステップ0: 会話履歴から文脈を推測
    preliminary_context = None
    romantic_keywords = ["失恋", "好きな人", "恋愛", "恋", "ときめき", "ドキドキ", "バクバク", "好き", "片思い", "両思い", "告白", "振られた", "別れた"]
    
    # 会話履歴から恋愛文脈を検出
    if conversation_history:
        for msg in conversation_history[-10:]:  # 直近10メッセージを確認
            msg_content = msg.get('content', '')
            if any(keyword in msg_content for keyword in romantic_keywords):
                preliminary_context = "romantic"
                logger.debug(f"   会話履歴から恋愛文脈を検出: {msg_content[:50]}...")
                break
    
    # 現在のメッセージから文脈を判定
    if not preliminary_context:
        if any(keyword in user_text for keyword in romantic_keywords):
            preliminary_context = "romantic"
        elif triage_result and triage_result.get("category") == "Emotional":
            subcategory = triage_result.get("subcategory", "").lower()
            if "romantic" in subcategory or "romantic_concern" in subcategory:
                preliminary_context = "romantic"
    
    # ステップ1: ルールベース安全性層（文脈を考慮）
    pain_check = check_pain_keywords_override(user_text, context_type=preliminary_context)
    negative_check = check_negative_expressions(user_text)
    exclusion_check = check_exclusion_patterns(user_text)
    
    logger.debug(f"   痛みキーワードチェック: {pain_check}")
    logger.debug(f"   除外パターンチェック: {exclusion_check}")
    
    # 痛み関連キーワードのオーバーライド（文脈を考慮）
    if pain_check["override_emergency"]:
        logger.info(f"   痛み関連キーワードにより緊急対応を判定")
        return {
            "is_emergency": True,
            "confidence": 0.9,
            "context_type": "actual_emergency",
            "reasoning": f"痛み関連キーワード（{', '.join(pain_check['detected_pain_keywords'])}）が検出されました。緊急対応が必要です。",
            "should_interrupt_counseling": True,
            "metaphor_detection": None
        }
    elif pain_check["has_pain_keywords"] and pain_check.get("context_mitigation", 0.0) >= 0.5:
        # 恋愛文脈が明確で痛みキーワードがある場合、注意喚起レベル（緊急対応ではない）
        logger.info(f"   恋愛文脈が明確で痛みキーワードあり（注意喚起レベル）")
        return {
            "is_emergency": False,
            "confidence": 0.4,
            "context_type": "romantic",
            "reasoning": f"恋愛文脈が明確ですが、痛み関連キーワード（{', '.join(pain_check['detected_pain_keywords'])}）も検出されました。念のため医療機関の受診も検討してください。",
            "should_interrupt_counseling": False,
            "metaphor_detection": None
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
        logger.debug(f"   心臓関連キーワードが検出されませんでした")
        return {
            "is_emergency": False,
            "confidence": 0.0,
            "context_type": "none",
            "reasoning": "心臓関連キーワードが検出されませんでした。",
            "should_interrupt_counseling": False,
            "metaphor_detection": None
        }
    
    logger.info(f"   心臓関連キーワード検出: heart={has_heart_keyword}, arrhythmia={has_arrhythmia_keyword}")
    
    # ステップ2.5: 比喩的表現の検出（LLMベース）
    metaphor_detection = None
    if client and (has_heart_keyword or has_arrhythmia_keyword):
        logger.info(f"   比喩的表現検出を実行")
        try:
            metaphor_detection = detect_metaphorical_expression(
                user_text,
                conversation_history=conversation_history,
                client=client
            )
            logger.info(f"   比喩的表現検出結果: is_metaphorical={metaphor_detection.get('is_metaphorical')}, "
                       f"confidence={metaphor_detection.get('confidence'):.2f}, "
                       f"type={metaphor_detection.get('detected_type')}")
        except Exception as e:
            logger.error(f"   比喩的表現検出エラー: {e}")
            metaphor_detection = {
                "is_metaphorical": False,
                "confidence": 0.0,
                "reasoning": f"エラー: {str(e)}",
                "detected_type": "none"
            }
    
    # 比喩的表現が高確信度で検出された場合、緊急対応を回避
    if metaphor_detection and metaphor_detection.get("is_metaphorical") and metaphor_detection.get("confidence", 0.0) >= 0.7:
        logger.info(f"   比喩的表現が高確信度で検出されたため、緊急対応を回避")
        return {
            "is_emergency": False,
            "confidence": 0.2,
            "context_type": "metaphorical",
            "reasoning": f"比喩的表現が検出されました（{metaphor_detection.get('detected_type')}）。実際の身体的症状ではない可能性が高いです。",
            "should_interrupt_counseling": False,
            "metaphor_detection": metaphor_detection
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
        
        logger.debug(f"   トリアージ結果: category={category}, subcategory={subcategory}, confidence={confidence:.2f}")
        
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
            elif "metaphorical" in subcategory:
                emergency_score = 0.2
                context_type = "metaphorical"
                reasoning_parts.append("トリアージ結果がEmotional（比喩的表現）")
            else:
                emergency_score = 0.5
                context_type = "metaphorical"
                reasoning_parts.append("トリアージ結果がEmotional")
        elif category == "Other" and "metaphorical" in subcategory:
            # Otherカテゴリで比喩的表現が検出された場合
            emergency_score = 0.2
            context_type = "metaphorical"
            reasoning_parts.append("トリアージ結果がOther（比喩的表現）")
        elif confidence < 0.7:
            # 低確信度の場合は追加判定が必要
            emergency_score = 0.6
            reasoning_parts.append("トリアージ結果の確信度が低い")
    
    # ステップ4: 除外パターンの適用
    if exclusion_check["has_exclusion"]:
        emergency_score -= exclusion_check["exclusion_score_reduction"]
        reasoning_parts.append(f"除外パターン検出（{exclusion_check['exclusion_score_reduction']:.1f}減点）")
        logger.debug(f"   除外パターン適用: {exclusion_check['exclusion_score_reduction']:.1f}減点")
    
    # ステップ4.5: 比喩的表現検出結果の適用
    if metaphor_detection and metaphor_detection.get("is_metaphorical"):
        metaphor_confidence = metaphor_detection.get("confidence", 0.0)
        # 比喩的表現の確信度に応じてスコアを減点
        reduction = metaphor_confidence * 0.5  # 最大0.5減点
        emergency_score -= reduction
        reasoning_parts.append(f"比喩的表現検出（{reduction:.1f}減点、確信度{metaphor_confidence:.2f}）")
        logger.debug(f"   比喩的表現検出適用: {reduction:.1f}減点")
    
    # ステップ5: 否定表現の適用（痛みキーワードがない場合のみ）
    if negative_check["has_negative"] and not pain_check["has_pain_keywords"]:
        emergency_score -= negative_check["negative_score"]
        reasoning_parts.append(f"否定表現検出（{negative_check['negative_score']:.1f}減点）")
        logger.debug(f"   否定表現適用: {negative_check['negative_score']:.1f}減点")
    
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
            logger.debug(f"   カウンセリング中（恋愛関連）: スコアを0.7倍")
    
    # ステップ7: 動的閾値の適用
    threshold = EMERGENCY_THRESHOLDS.get(context_type, EMERGENCY_THRESHOLDS['none'])
    logger.info(f"   動的閾値適用: context_type={context_type}, threshold={threshold:.2f}, emergency_score={emergency_score:.2f}")
    
    # 最終判定（動的閾値を使用）
    is_emergency = emergency_score >= threshold
    
    if not reasoning_parts:
        reasoning = "キーワードマッチングによる判定"
    else:
        reasoning = " | ".join(reasoning_parts)
    
    logger.info(f"✅ 心臓緊急チェック完了: is_emergency={is_emergency}, "
               f"context_type={context_type}, confidence={emergency_score:.2f}, "
               f"threshold={threshold:.2f}")
    logger.debug(f"   最終判定理由: {reasoning}")
    
    return {
        "is_emergency": is_emergency,
        "confidence": emergency_score,
        "context_type": context_type,
        "reasoning": reasoning,
        "should_interrupt_counseling": should_interrupt,
        "metaphor_detection": metaphor_detection,
        "threshold_used": threshold
    }


def detect_heart_context_pattern(
    user_text: str,
    triage_result: Dict = None,
    client: OpenAI = None
) -> Dict:
    """
    心臓関連キーワードの文脈パターンを判定
    
    判定パターン:
    - romantic: 恋愛・ロマンチックな文脈
    - exercise: 運動・身体活動後の文脈
    - nervous: 緊張・不安による文脈
    - metaphorical: 比喩的表現
    - actual_emergency: 実際の緊急事態
    
    Args:
        user_text: ユーザーの入力テキスト
        triage_result: LLMトリアージ結果（オプション）
        client: OpenAIクライアントインスタンス（オプション）
    
    Returns:
        {
            "context_type": str,
            "confidence": float,
            "reasoning": str
        }
    """
    # トリアージ結果から文脈を推測
    if triage_result:
        category = triage_result.get("category", "")
        subcategory = triage_result.get("subcategory", "").lower()
        confidence = triage_result.get("confidence", 0.5)
        
        if category == "Emergency" and confidence >= 0.8:
            return {
                "context_type": "actual_emergency",
                "confidence": 0.9,
                "reasoning": "トリアージ結果がEmergency（高確信度）"
            }
        elif category == "Emotional":
            if "romantic" in subcategory or "romantic_concern" in subcategory:
                return {
                    "context_type": "romantic",
                    "confidence": 0.8,
                    "reasoning": "トリアージ結果がEmotional（恋愛関連）"
                }
            elif "anxiety" in subcategory or "nervous" in subcategory:
                return {
                    "context_type": "nervous",
                    "confidence": 0.7,
                    "reasoning": "トリアージ結果がEmotional（不安・緊張）"
                }
            else:
                return {
                    "context_type": "metaphorical",
                    "confidence": 0.6,
                    "reasoning": "トリアージ結果がEmotional"
                }
    
    # キーワードベースの簡易判定（フォールバック）
    romantic_keywords = ["好き", "恋", "恋愛", "ドキドキ", "バクバク", "ときめき"]
    exercise_keywords = ["運動", "走", "階段", "登", "上が", "トレーニング", "ジョギング"]
    nervous_keywords = ["緊張", "不安", "プレッシャー", "ストレス", "心配"]
    
    if any(keyword in user_text for keyword in romantic_keywords):
        return {
            "context_type": "romantic",
            "confidence": 0.6,
            "reasoning": "恋愛関連キーワードが検出されました"
        }
    elif any(keyword in user_text for keyword in exercise_keywords):
        return {
            "context_type": "exercise",
            "confidence": 0.6,
            "reasoning": "運動関連キーワードが検出されました"
        }
    elif any(keyword in user_text for keyword in nervous_keywords):
        return {
            "context_type": "nervous",
            "confidence": 0.6,
            "reasoning": "緊張・不安関連キーワードが検出されました"
        }
    
    # デフォルト: 実際の緊急事態の可能性
    return {
        "context_type": "actual_emergency",
        "confidence": 0.5,
        "reasoning": "文脈が不明確なため、安全側に倒して緊急事態の可能性として判定"
    }


def generate_contextual_emergency_message(
    user_text: str,
    emergency_result: Dict,
    counseling_mode: Dict = None,
    triage_result: Dict = None
) -> str:
    """
    文脈を考慮した緊急メッセージを生成（共感的なトーン）
    
    例:
    - 恋愛文脈: "失恋は非常に辛い経験ですね。胸の痛みは、心の苦しみが身体に現れることもありますが..."
    - 比喩的表現: "「心臓を捧げよ」という表現ですね。もし実際に心臓の痛みや動悸などの症状がある場合は..."
    - 実際の緊急: "緊急対応が必要な症状の可能性があります。速やかに医療機関を受診..."
    
    Args:
        user_text: ユーザーの入力テキスト
        emergency_result: 緊急チェック結果
        counseling_mode: カウンセリングモード状態（オプション）
        triage_result: LLMトリアージ結果（オプション）
    
    Returns:
        文脈に応じた緊急メッセージ（共感的なトーン）
    """
    context_type = emergency_result.get('context_type', 'actual_emergency')
    reasoning = emergency_result.get('reasoning', '')
    metaphor_detection = emergency_result.get('metaphor_detection')
    
    # 比喩的表現が検出された場合の軽い確認メッセージ
    if context_type == 'metaphorical' and metaphor_detection and metaphor_detection.get('is_metaphorical'):
        detected_type = metaphor_detection.get('detected_type', 'none')
        if detected_type == 'anime_quote':
            return f"""
「{user_text}」という表現ですね。

もし実際に心臓の痛みや動悸、息苦しさなどの症状がある場合は、速やかに医療機関を受診することをお勧めします。

緊急の場合は119番（救急）に連絡してください。
"""
        else:
            return f"""
比喩的表現が検出されましたが、もし実際に心臓の痛みや動悸などの症状がある場合は、
速やかに医療機関を受診することをお勧めします。

緊急の場合は119番（救急）に連絡してください。
"""
    
    # カウンセリング中の場合は、カウンセリングの文脈を考慮
    if counseling_mode and counseling_mode.get('active'):
        symptom_type = counseling_mode.get('symptom_type', '')
        if symptom_type == 'romantic_concern' and context_type == 'romantic':
            return f"""
お気持ちをお聞かせいただき、ありがとうございます。

失恋は非常に辛い経験ですね。胸の痛みは、心の苦しみが身体に現れることもありますが、
物理的な締め付け感がある場合は、念のため医療機関に相談することをお勧めします。

感情を無理に抑えず、少しずつ受け入れていくことが大切です。心のサポートも重要ですので、
信頼できる友人やカウンセラーと話してみるのも良いかもしれません。

痛みが続く場合や、息苦しさ、動悸などの症状がある場合は、速やかに医療機関を受診してください。
緊急の場合は119番（救急）に連絡してください。
"""
    
    # 文脈タイプに応じたメッセージ生成（共感的なトーン）
    if context_type == 'romantic':
        return f"""
失恋は非常に辛い経験ですね。胸の痛みは、心の苦しみが身体に現れることもありますが、
物理的な締め付け感がある場合は、念のため医療機関に相談することをお勧めします。

感情を無理に抑えず、少しずつ受け入れていくことが大切です。心のサポートも重要ですので、
信頼できる友人やカウンセラーと話してみるのも良いかもしれません。

痛みが続く場合や、息苦しさ、動悸などの症状がある場合は、速やかに医療機関を受診してください。
緊急の場合は119番（救急）に連絡してください。
"""
    elif context_type == 'nervous':
        return f"""
緊張や不安による動悸の可能性が高いですが、念のため医療機関の受診も検討してください。

特に痛みや息苦しさがある場合は、速やかに医療機関を受診するか、
緊急の場合は119番（救急）に連絡してください。
"""
    elif context_type == 'exercise':
        return f"""
運動後の動悸の可能性が高いですが、念のため医療機関の受診も検討してください。

特に痛みや息苦しさがある場合は、速やかに医療機関を受診するか、
緊急の場合は119番（救急）に連絡してください。
"""
    else:
        # 実際の緊急事態
        return """⚠️ 緊急対応が必要な症状の可能性があります。

特に「心臓が痛い」という症状は、心臓疾患の可能性があります。
速やかに医療機関を受診するか、緊急の場合は119番（救急）に連絡してください。

市販薬での対応は推奨できません。医師の診断を受けてください。
"""

