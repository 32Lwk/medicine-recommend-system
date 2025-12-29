"""
店舗案内・遺失物対応ハンドラーモジュール
店舗案内や遺失物関連の質問を検出し、適切な案内を提供する
"""

import json
import logging
import re
from typing import Dict, Optional, Tuple
from openai import OpenAI

logger = logging.getLogger(__name__)

# 店舗案内関連のキーワード
STORE_INQUIRY_KEYWORDS = [
    "場所を教えて", "場所は", "どこにありますか", "どこですか", "どこに",
    "場所を", "場所が", "場所の", "案内", "教えてください", "教えて",
    "どこ", "場所",
    # トイレ関連（症状キーワードがない場合のみ）
    "トイレ", "お手洗い", "便所", "化粧室", "洗面所",
    "うんこしたい", "うんちしたい", "おしっこしたい", "用を足したい",
    "トイレに行きたい", "お手洗いに行きたい", "トイレは", "お手洗いは"
]

# 症状を示すキーワード（これらのキーワードがある場合は医薬品推奨を優先）
SYMPTOM_KEYWORDS_FOR_TOILET = [
    "出ない", "出にくい", "出ません", "出ませんでした",
    "便秘", "下痢", "腹痛", "痛い", "痛み",
    "困っている", "悩んでいる", "症状", "薬", "医薬品"
]

# 遺失物関連のキーワード
LOST_AND_FOUND_KEYWORDS = [
    "忘れ物", "落とし物", "落とした", "拾いました", "拾った", "拾う",
    "紛失", "失くした", "なくした", "落として", "落ちた", "落ちて",
    "忘れました", "忘れた", "忘れて", "忘れてしまった", "忘れてしまいました",
    "置き忘れ", "置き忘れた", "置き忘れました", "置き忘れて"
]

# 店舗内外の判定キーワード
STORE_LOCATION_KEYWORDS = {
    "inside": ["店舗内", "店内", "店の中", "お店の中", "お店にいます", "店にいます", "店舗にいます"],
    "outside": ["店舗外", "店外", "店の外", "お店の外", "お店の外にいます", "店の外にいます", "店舗外にいます"]
}


def detect_store_inquiry_keywords(user_text: str) -> Tuple[bool, Optional[str]]:
    """
    キーワードマッチングで店舗案内・遺失物関連の質問を検出
    
    Args:
        user_text: ユーザーの入力テキスト
    
    Returns:
        (is_detected, inquiry_type): (検出されたか, 質問タイプ: "store_inquiry" | "lost_and_found" | None)
    """
    user_text_lower = user_text.lower()
    
    # 遺失物関連のキーワードをチェック（優先度が高い）
    for keyword in LOST_AND_FOUND_KEYWORDS:
        if keyword in user_text_lower:
            logger.info(f"🔍 遺失物関連キーワード検出: {keyword}")
            return True, "lost_and_found"
    
    # トイレ関連のキーワードをチェック（症状キーワードがない場合のみ）
    toilet_keywords = ["うんこしたい", "うんちしたい", "おしっこしたい", "用を足したい", 
                      "トイレに行きたい", "お手洗いに行きたい", "トイレは", "お手洗いは"]
    has_toilet_keyword = any(keyword in user_text_lower for keyword in toilet_keywords)
    
    if has_toilet_keyword:
        # 症状キーワードが含まれている場合は医薬品推奨を優先（店舗案内として扱わない）
        has_symptom_keyword = any(keyword in user_text_lower for keyword in SYMPTOM_KEYWORDS_FOR_TOILET)
        if has_symptom_keyword:
            logger.info(f"🔍 トイレ関連キーワード検出だが、症状キーワードも検出されたため医薬品推奨を優先")
            return False, None
        else:
            logger.info(f"🔍 トイレ関連キーワード検出（症状キーワードなし）: 店舗案内として処理")
            return True, "store_inquiry"
    
    # その他の店舗案内関連のキーワードをチェック
    for keyword in STORE_INQUIRY_KEYWORDS:
        if keyword in user_text_lower:
            logger.info(f"🔍 店舗案内関連キーワード検出: {keyword}")
            return True, "store_inquiry"
    
    return False, None


def detect_store_location(user_text: str) -> Optional[str]:
    """
    ユーザーが明示的に店舗内外を指定しているか判定
    
    Args:
        user_text: ユーザーの入力テキスト
    
    Returns:
        "inside" | "outside" | None
    """
    user_text_lower = user_text.lower()
    
    # 店舗内のキーワードをチェック
    for keyword in STORE_LOCATION_KEYWORDS["inside"]:
        if keyword in user_text_lower:
            logger.info(f"🏪 店舗内を検出: {keyword}")
            return "inside"
    
    # 店舗外のキーワードをチェック
    for keyword in STORE_LOCATION_KEYWORDS["outside"]:
        if keyword in user_text_lower:
            logger.info(f"🏪 店舗外を検出: {keyword}")
            return "outside"
    
    return None


def classify_inquiry_with_llm(user_text: str, client: OpenAI, triage_result: Optional[Dict] = None) -> Dict:
    """
    LLMを使用して店舗案内・遺失物関連の質問を詳細分類
    
    Args:
        user_text: ユーザーの入力テキスト
        client: OpenAIクライアントインスタンス
        triage_result: LLMトリアージ結果（オプション）
    
    Returns:
        {
            "is_store_inquiry": bool,
            "inquiry_type": "store_inquiry" | "lost_and_found" | None,
            "confidence": float,
            "reasoning": str
        }
    """
    try:
        # トリアージ結果からsubcategoryを確認
        if triage_result and triage_result.get("category") == "Other":
            subcategory = triage_result.get("subcategory", "").lower()
            if "store_inquiry" in subcategory or "lost_and_found" in subcategory:
                logger.info(f"🔍 トリアージ結果から店舗案内・遺失物関連を検出: {subcategory}")
                return {
                    "is_store_inquiry": True,
                    "inquiry_type": "store_inquiry" if "store_inquiry" in subcategory else "lost_and_found",
                    "confidence": triage_result.get("confidence", 0.8),
                    "reasoning": f"トリアージ結果から検出: {subcategory}"
                }
        
        # LLMで詳細分類
        prompt = """
あなたは薬剤師です。ユーザーの入力が店舗案内や遺失物関連の質問かを判定してください。

【判定基準】
1. 店舗案内関連（store_inquiry）: 「場所を教えてください」「どこにありますか」「トイレはどこですか」など、店舗内の場所に関する質問
   - 「うんこしたい」「トイレに行きたい」など、トイレの場所を尋ねている場合は店舗案内として扱う
   - ただし、「うんこしたいけど出ない」「便秘でうんこしたい」など、症状を示すキーワードが含まれている場合は医薬品推奨を優先（is_store_inquiry=false）
2. 遺失物関連（lost_and_found）: 「忘れ物を拾いました」「落とし物を拾いました」など、遺失物に関する質問
3. その他: 上記に該当しない場合は、is_store_inquiryをfalseに設定

【重要な注意事項】
- 「うんこしたい」「トイレに行きたい」だけの場合は店舗案内として扱う
- 「うんこしたいけど出ない」「便秘でうんこしたい」「下痢で困っている」など、症状を示すキーワードが含まれている場合は医薬品推奨を優先する（is_store_inquiry=false）

【回答形式】
JSON形式で回答してください：
{
    "is_store_inquiry": true/false,
    "inquiry_type": "store_inquiry" | "lost_and_found" | null,
    "confidence": 0.0-1.0の数値,
    "reasoning": "判定理由"
}
"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは薬剤師です。店舗案内・遺失物関連の質問を正確に分類してください。"},
                {"role": "user", "content": f"{prompt}\n\n【ユーザーの入力】\n{user_text}"}
            ],
            temperature=0.1,
            max_tokens=200,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        
        try:
            result = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析エラー: {e}, レスポンス: {content}")
            return {
                "is_store_inquiry": False,
                "inquiry_type": None,
                "confidence": 0.0,
                "reasoning": f"JSON解析エラー: {str(e)}"
            }
        
        is_store_inquiry = bool(result.get("is_store_inquiry", False))
        inquiry_type = result.get("inquiry_type")
        confidence = float(result.get("confidence", 0.0))
        reasoning = result.get("reasoning", "判定理由が提供されませんでした")
        
        # confidenceの範囲チェック
        if confidence < 0.0:
            confidence = 0.0
        elif confidence > 1.0:
            confidence = 1.0
        
        logger.info(f"🔍 LLM分類結果: is_store_inquiry={is_store_inquiry}, inquiry_type={inquiry_type}, confidence={confidence:.2f}")
        
        return {
            "is_store_inquiry": is_store_inquiry,
            "inquiry_type": inquiry_type,
            "confidence": confidence,
            "reasoning": reasoning
        }
        
    except Exception as e:
        logger.error(f"❌ LLM分類エラー: {e}")
        import traceback
        traceback.print_exc()
        return {
            "is_store_inquiry": False,
            "inquiry_type": None,
            "confidence": 0.0,
            "reasoning": f"エラーが発生しました: {str(e)}"
        }


def generate_store_inquiry_response(
    user_text: str,
    inquiry_type: str,
    store_location: Optional[str] = None
) -> Dict[str, str]:
    """
    店舗案内・遺失物関連の応答を生成
    
    Args:
        user_text: ユーザーの入力テキスト
        inquiry_type: 質問タイプ（"store_inquiry" | "lost_and_found"）
        store_location: 店舗内外の判定（"inside" | "outside" | None）
    
    Returns:
        {
            "simple_message": str,  # シンプルなテキストメッセージ
            "structured_html": str   # 構造化されたHTML
        }
    """
    if inquiry_type == "store_inquiry":
        return generate_store_location_response(user_text, store_location)
    elif inquiry_type == "lost_and_found":
        return generate_lost_and_found_response(user_text, store_location)
    else:
        return {
            "simple_message": "申し訳ございませんが、ご質問の内容を理解できませんでした。",
            "structured_html": ""
        }


def generate_store_location_response(user_text: str, store_location: Optional[str] = None) -> Dict[str, str]:
    """
    店舗案内関連の応答を生成
    
    Args:
        user_text: ユーザーの入力テキスト
        store_location: 店舗内外の判定（"inside" | "outside" | None）
    
    Returns:
        {
            "simple_message": str,
            "structured_html": str
        }
    """
    user_text_lower = user_text.lower()
    is_toilet_inquiry = any(keyword in user_text_lower for keyword in [
        "トイレ", "お手洗い", "便所", "化粧室", "洗面所",
        "うんこしたい", "うんちしたい", "おしっこしたい", "用を足したい"
    ])
    
    if is_toilet_inquiry:
        # トイレの場所を尋ねている場合
        if store_location == "inside":
            simple_message = """トイレの場所についてお尋ねいただき、ありがとうございます。

店内のスタッフにお尋ねいただければ、トイレの場所を詳しくご案内いたします。
お近くのスタッフまでお気軽にお声がけください。"""
            
            structured_html = f"""
<div class="store-inquiry-response">
    <h4>🚻 トイレの場所について</h4>
    <p>トイレの場所についてお尋ねいただき、ありがとうございます。</p>
    <div class="inquiry-options">
        <p><strong>📍 ご案内方法</strong></p>
        <ul>
            <li>店内のスタッフにお尋ねいただければ、トイレの場所を詳しくご案内いたします</li>
            <li>お近くのスタッフまでお気軽にお声がけください</li>
        </ul>
    </div>
</div>"""
        else:
            simple_message = """トイレの場所についてお尋ねいただき、ありがとうございます。

店舗内にお越しいただいた際は、店内のスタッフにお尋ねいただければ、トイレの場所を詳しくご案内いたします。
お近くのスタッフまでお気軽にお声がけください。"""
            
            structured_html = f"""
<div class="store-inquiry-response">
    <h4>🚻 トイレの場所について</h4>
    <p>トイレの場所についてお尋ねいただき、ありがとうございます。</p>
    <div class="inquiry-options">
        <p><strong>📍 ご案内方法</strong></p>
        <p>店舗内にお越しいただいた際は、店内のスタッフにお尋ねいただければ、トイレの場所を詳しくご案内いたします。</p>
        <p>お近くのスタッフまでお気軽にお声がけください。</p>
    </div>
</div>"""
        return {
            "simple_message": simple_message,
            "structured_html": structured_html
        }
    
    # その他の店舗案内
    if store_location == "inside":
        # 店舗内の場合: 一般的な案内とスタッフへの案内の両方
        simple_message = """店舗内の場所についてお尋ねいただき、ありがとうございます。

店内のスタッフにお尋ねいただければ、詳しくご案内いたします。
お近くのスタッフまでお気軽にお声がけください。"""
        
        structured_html = f"""
<div class="store-inquiry-response">
    <h4>🏪 店舗案内について</h4>
    <p>店舗内の場所についてお尋ねいただき、ありがとうございます。</p>
    <div class="inquiry-options">
        <p><strong>📍 ご案内方法</strong></p>
        <ul>
            <li>店内のスタッフにお尋ねいただければ、詳しくご案内いたします</li>
            <li>お近くのスタッフまでお気軽にお声がけください</li>
        </ul>
    </div>
</div>"""
    else:
        # 店舗外の場合または判定できない場合: 一般的な案内のみ
        simple_message = """店舗の場所についてお尋ねいただき、ありがとうございます。

店舗内にお越しいただいた際は、店内のスタッフにお尋ねいただければ、詳しくご案内いたします。
お近くのスタッフまでお気軽にお声がけください。"""
        
        structured_html = f"""
<div class="store-inquiry-response">
    <h4>🏪 店舗案内について</h4>
    <p>店舗の場所についてお尋ねいただき、ありがとうございます。</p>
    <div class="inquiry-options">
        <p><strong>📍 ご案内方法</strong></p>
        <p>店舗内にお越しいただいた際は、店内のスタッフにお尋ねいただければ、詳しくご案内いたします。</p>
        <p>お近くのスタッフまでお気軽にお声がけください。</p>
    </div>
</div>"""
    
    return {
        "simple_message": simple_message,
        "structured_html": structured_html
    }


def generate_lost_and_found_response(user_text: str, store_location: Optional[str] = None) -> Dict[str, str]:
    """
    遺失物関連の応答を生成
    
    Args:
        user_text: ユーザーの入力テキスト
        store_location: 店舗内外の判定（"inside" | "outside" | None）
    
    Returns:
        {
            "simple_message": str,
            "structured_html": str
        }
    """
    if store_location == "inside":
        # 店舗内の場合: スタッフへの案内
        simple_message = """遺失物についてお尋ねいただき、ありがとうございます。

店舗内で遺失物を拾われた場合は、店内のスタッフまでお声がけください。
スタッフが適切に対応いたします。"""
        
        structured_html = f"""<div class="lost-and-found-response">
    <h4>🔍 遺失物について</h4>
    <p>遺失物についてお尋ねいただき、ありがとうございます。</p>
    <div class="inquiry-options">
        <p><strong>🏪 店舗内で拾われた場合</strong></p>
        <ul>
            <li>店内のスタッフまでお声がけください</li>
            <li>スタッフが適切に対応いたします</li>
        </ul>
    </div>
</div>"""
    elif store_location == "outside":
        # 店舗外の場合: 警察への相談を案内
        simple_message = """遺失物についてお尋ねいただき、ありがとうございます。

店舗外で遺失物を拾われた場合は、お近くの警察署または交番にご相談ください。
警察署では遺失物の届出を受け付けています。"""
        
        structured_html = f"""<div class="lost-and-found-response">
    <h4>🔍 遺失物について</h4>
    <p>遺失物についてお尋ねいただき、ありがとうございます。</p>
    <div class="inquiry-options">
        <p><strong>🚔 店舗外で拾われた場合</strong></p>
        <ul>
            <li>お近くの警察署または交番にご相談ください</li>
            <li>警察署では遺失物の届出を受け付けています</li>
        </ul>
    </div>
</div>"""
    else:
        # 判定できない場合: 両方の案内を表示
        simple_message = """遺失物についてお尋ねいただき、ありがとうございます。

【店舗内で拾われた場合】
店内のスタッフまでお声がけください。スタッフが適切に対応いたします。

【店舗外で拾われた場合】
お近くの警察署または交番にご相談ください。警察署では遺失物の届出を受け付けています。"""
        
        structured_html = f"""<div class="lost-and-found-response">
    <h4>🔍 遺失物について</h4>
    <p>遺失物についてお尋ねいただき、ありがとうございます。</p>
    <div class="inquiry-options">
        <div class="location-option">
            <p><strong>🏪 店舗内で拾われた場合</strong></p>
            <ul>
                <li>店内のスタッフまでお声がけください</li>
                <li>スタッフが適切に対応いたします</li>
            </ul>
        </div>
        <div class="location-option">
            <p><strong>🚔 店舗外で拾われた場合</strong></p>
            <ul>
                <li>お近くの警察署または交番にご相談ください</li>
                <li>警察署では遺失物の届出を受け付けています</li>
            </ul>
        </div>
    </div>
</div>"""
    
    return {
        "simple_message": simple_message,
        "structured_html": structured_html
    }


def handle_store_inquiry(
    user_text: str,
    client: OpenAI,
    triage_result: Optional[Dict] = None
) -> Optional[Dict]:
    """
    店舗案内・遺失物関連の質問を処理
    
    Args:
        user_text: ユーザーの入力テキスト
        client: OpenAIクライアントインスタンス
        triage_result: LLMトリアージ結果（オプション）
    
    Returns:
        処理が必要な場合: {
            "is_store_inquiry": True,
            "inquiry_type": "store_inquiry" | "lost_and_found",
            "store_location": "inside" | "outside" | None,
            "response": {
                "simple_message": str,
                "structured_html": str
            }
        }
        処理が不要な場合: None
    """
    # ステップ1: キーワードマッチングで高速判定
    is_detected, inquiry_type = detect_store_inquiry_keywords(user_text)
    
    if not is_detected:
        logger.debug(f"🔍 店舗案内・遺失物関連のキーワードが検出されませんでした")
        return None
    
    # ステップ2: LLMで詳細分類（キーワードで検出された場合のみ）
    llm_result = classify_inquiry_with_llm(user_text, client, triage_result)
    
    if not llm_result.get("is_store_inquiry"):
        logger.debug(f"🔍 LLM分類結果: 店舗案内・遺失物関連ではない")
        return None
    
    # 最終的なinquiry_typeを決定
    final_inquiry_type = llm_result.get("inquiry_type") or inquiry_type
    
    # ステップ3: 店舗内外の判定
    store_location = detect_store_location(user_text)
    
    # ステップ4: 応答を生成
    response = generate_store_inquiry_response(user_text, final_inquiry_type, store_location)
    
    logger.info(f"✅ 店舗案内・遺失物関連の処理完了: inquiry_type={final_inquiry_type}, store_location={store_location}")
    
    return {
        "is_store_inquiry": True,
        "inquiry_type": final_inquiry_type,
        "store_location": store_location,
        "response": response,
        "confidence": llm_result.get("confidence", 0.8),
        "reasoning": llm_result.get("reasoning", "")
    }

