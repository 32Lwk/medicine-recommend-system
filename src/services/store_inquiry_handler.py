"""
店舗案内・遺失物対応ハンドラーモジュール
店舗案内や遺失物関連の質問を検出し、適切な案内を提供する
"""

import html
import json
import logging
import os
import re
from typing import Dict, List, Optional, Tuple

from openai import OpenAI

from src.services.routing_keyword_policy import attach_routing_keyword_candidates

logger = logging.getLogger(__name__)

# 商品リストの読み込み
PRODUCT_CATEGORIES = {}
try:
    from src import PROJECT_ROOT
    product_list_path = os.path.join(PROJECT_ROOT, 'data', 'store_products.json')
    with open(product_list_path, 'r', encoding='utf-8') as f:
        PRODUCT_CATEGORIES = json.load(f)
    logger.info(f"✅ 商品リストを読み込みました: {len(PRODUCT_CATEGORIES)}カテゴリ")
except Exception as e:
    logger.warning(f"⚠️ 商品リストの読み込みに失敗: {e}")
    PRODUCT_CATEGORIES = {}

# 店舗案内関連のキーワード
# 注意: 「教えてください」「教えて」は文脈依存のため、店舗案内関連の文脈でのみ検出
STORE_INQUIRY_KEYWORDS = [
    "場所を教えて", "場所は", "どこにありますか", "どこですか", "どこに",
    "場所を", "場所が", "場所の", "案内",
    # 注意: 「教えてください」「教えて」は単独では検出しない（文脈依存）
    # 代わりに、店舗案内関連のキーワードと組み合わせて検出（例：「場所を教えてください」）
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

# 在庫確認関連のキーワード
INVENTORY_INQUIRY_KEYWORDS = [
    "ありますか", "どこですか", "在庫", "取り寄せ", "置いてありますか",
    "売っていますか", "扱っていますか", "取り扱い", "あります",
    "在庫ありますか", "在庫は", "在庫が", "在庫の", "在庫確認",
    "取り寄せ可能", "取り寄せできますか", "注文", "発注",
    "どこにありますか", "どこに置いてありますか", "どこで売っていますか",
    "どこで買えますか", "どこで購入できますか", "どこで手に入りますか",
    "場所は",  # 商品名と組み合わせて在庫確認として扱う
    "どこ"  # 商品名と組み合わせて在庫確認として扱う（「歯ブラシはどこ？」など）
]

# 症状を示すキーワード（これらのキーワードがある場合は医薬品推奨を優先）
SYMPTOM_KEYWORDS = [
    "かぶれ", "症状", "痛い", "痒い", "痛み", "かゆみ", "アレルギー",
    "炎症", "腫れ", "発疹", "湿疹", "赤み", "赤い", "腫れている",
    "薬", "医薬品", "治療", "治したい", "治る", "改善", "緩和"
]

# 周辺施設: 空間的な文脈（これがない限り曖昧施設名だけでは facilities にしない）
FACILITIES_SPATIAL_KEYWORDS = [
    "近くに", "周辺に", "近くの", "周辺の", "近所に", "近所の",
    "この辺", "付近", "近辺", "周り", "最寄り", "最寄", "徒歩圏",
    "店から", "店舗から", "ここから", "店の近く", "お店の近く",
]

# 周辺施設: 施設タイプ（コンビニ等）。単独では弱シグナル — 位置質問・空間文脈と組み合わせる
FACILITY_TYPE_KEYWORDS = [
    # 買い物
    "コンビニ", "セブンイレブン", "ファミリーマート", "ローソン", "ミニストップ",
    "スーパー", "スーパーマーケット", "ショッピングモール", "デパート", "百貨店",
    "ドラッグストア", "薬局", "家電量販店", "ホームセンター", "100円ショップ", "書店", "リサイクルショップ",
    # 金融・郵便
    "銀行", "ATM", "郵便局", "ゆうちょ銀行", "信用金庫", "証券会社",
    # 飲食
    "レストラン", "カフェ", "喫茶店", "飲食店", "ファミレス", "居酒屋", "ファストフード", "弁当屋", "パン屋",
    # 医療・福祉
    "病院", "総合病院", "クリニック", "診療所", "医院", "歯科医院", "整骨院", "接骨院", "介護施設", "老人ホーム",
    # 交通・インフラ
    "駅", "バス停", "タクシー乗り場", "駐車場", "ガソリンスタンド", "道の駅", "サービスエリア", "コインランドリー",
    # 公共施設（教育施設は FACILITY_NAMES_AMBIGUOUS で別管理）
    "公園", "図書館", "公民館", "市役所", "区役所", "役場", "警察署", "交番", "消防署",
    # 宿泊・入浴・リラクゼーション
    "ホテル", "旅館", "銭湯", "温泉", "サウナ", "マッサージ店", "整体院", "エステサロン", "美容室", "理容室",
    # 娯楽・スポーツ
    "映画館", "カラオケ", "ゲームセンター", "パチンコ", "動物園", "水族館", "美術館", "博物館",
    "体育館", "運動公園", "ジム", "フィットネスクラブ", "ゴルフ練習場", "キャンプ場",
    # その他
    "神社", "寺院", "教会", "葬儀場"
]

FACILITIES_LOCATION_QUESTION_KEYWORDS = [
    "どこに", "どこで", "どこですか", "どこにあり", "どこにある",
    "場所は", "場所を", "行き方", "アクセス", "道順",
]

# 店舗案内の「どこ」単独マッチを抑止（文脈ありのときのみ許可）
STORE_LOCATION_BARE_KEYWORDS = frozenset({
    "どこ", "場所", "どこに", "どこですか", "どこにありますか",
})

# 運営者情報・メタ質問と紛れやすい施設名（周辺案内には空間文脈が必須）
FACILITY_NAMES_AMBIGUOUS = frozenset({
    "大学", "小学校", "中学校", "高校", "幼稚園", "保育園", "塾", "予備校",
})

# 周辺施設名リスト
FACILITY_NAMES = [
    # 買い物
    "コンビニ", "セブンイレブン", "ファミリーマート", "ローソン", "ミニストップ",
    "スーパー", "スーパーマーケット", "ショッピングモール", "デパート", "百貨店",
    "ドラッグストア", "薬局", "家電量販店", "ホームセンター", "100円ショップ", "書店", "リサイクルショップ",
    # 金融・郵便
    "銀行", "ATM", "郵便局", "ゆうちょ銀行", "信用金庫", "証券会社",
    # 飲食
    "レストラン", "カフェ", "喫茶店", "飲食店", "ファミレス", "居酒屋", "ファストフード", "弁当屋", "パン屋",
    # 医療・福祉
    "病院", "総合病院", "クリニック", "診療所", "医院", "歯科医院", "整骨院", "接骨院", "介護施設", "老人ホーム",
    # 交通・インフラ
    "駅", "バス停", "タクシー乗り場", "駐車場", "ガソリンスタンド", "道の駅", "サービスエリア", "コインランドリー",
    # 公共施設・教育
    "公園", "図書館", "公民館", "市役所", "区役所", "役場", "警察署", "交番", "消防署",
    "小学校", "中学校", "高校", "大学", "幼稚園", "保育園", "塾", "予備校",
    # 宿泊・入浴・リラクゼーション
    "ホテル", "旅館", "銭湯", "温泉", "サウナ", "マッサージ店", "整体院", "エステサロン", "美容室", "理容室",
    # 娯楽・スポーツ
    "映画館", "カラオケ", "ゲームセンター", "パチンコ", "動物園", "水族館", "美術館", "博物館",
    "体育館", "運動公園", "ジム", "フィットネスクラブ", "ゴルフ練習場", "キャンプ場",
    # その他
    "神社", "寺院", "教会", "葬儀場"
]


def _text_lower(user_text: str) -> str:
    return (user_text or "").lower()


def has_facilities_spatial_context(user_text: str) -> bool:
    t = _text_lower(user_text)
    return any(k in t for k in FACILITIES_SPATIAL_KEYWORDS)


def has_facilities_location_question(user_text: str) -> bool:
    t = _text_lower(user_text)
    if any(k in t for k in FACILITIES_LOCATION_QUESTION_KEYWORDS):
        return True
    if "どこ" in t or "場所" in t:
        return True
    return False


def has_store_scoped_location_context(user_text: str) -> bool:
    """店内・売場・トイレなど、店舗案内としての位置質問文脈。"""
    t = _text_lower(user_text)
    scoped = (
        "トイレ", "お手洗い", "便所", "化粧室", "洗面所",
        "レジ", "店内", "売り場", "棚", "コーナー", "フロア", "階",
        "案内", "受付",
    )
    return any(k in t for k in scoped)


def should_defer_store_to_concierge(
    user_text: str,
    triage_result: Optional[Dict] = None,
) -> bool:
    """
    キーワードだけで店舗案内にせず Concierge / メタ応答へ譲る。
    オーケストレーターが付与した concierge_intent があれば常に譲る。
    """
    triage = triage_result or {}
    if triage.get("concierge_intent"):
        logger.info(
            "🔍 店舗案内をスキップ: concierge_intent=%s",
            triage.get("concierge_intent"),
        )
        return True
    t = _text_lower(user_text)
    if not t:
        return False
    for name in FACILITY_NAMES_AMBIGUOUS:
        if name.lower() in t and has_facilities_location_question(user_text):
            if not has_facilities_spatial_context(user_text) and not has_store_scoped_location_context(user_text):
                logger.info(
                    "🔍 店舗案内をスキップ: 曖昧施設「%s」+ 位置質問（周辺文脈なし）",
                    name,
                )
                return True
    return False


# 免税対応関連のキーワード
TAX_FREE_KEYWORDS = [
    "免税", "免税対応", "免税できますか", "免税は", "免税が",
    "タックスフリー", "tax free", "duty free"
]

# 周辺観光地関連のキーワード
TOURISM_KEYWORDS = [
    "観光地", "観光", "観光スポット", "名所", "見どころ",
    "観光案内", "観光情報", "おすすめ", "観光名所"
]

# 営業時間・アクセス関連のキーワード
BUSINESS_HOURS_KEYWORDS = [
    "営業時間", "営業", "開店", "閉店", "何時まで", "何時から",
    "アクセス", "行き方", "道順", "最寄り駅", "最寄り", "駅",
    "バス", "電車", "車", "徒歩", "駐車場"
]

# 支払い方法関連のキーワード
PAYMENT_KEYWORDS = [
    "支払い", "支払い方法", "お支払い", "決済", "現金", "カード",
    "クレジットカード", "電子マネー", "Suica", "ICOCA", "PayPay",
    "QRコード", "QR決済", "キャッシュレス"
]

# 駐車場関連のキーワード
PARKING_KEYWORDS = [
    "駐車場", "パーキング", "駐車", "車", "駐車できますか",
    "駐車場は", "駐車場が", "駐車場の", "駐車料金"
]

# 店舗サービス関連のキーワード
SERVICES_KEYWORDS = [
    "サービス", "サービス内容", "取り扱い", "取り扱い商品",
    "配達", "配送", "取り寄せ", "予約", "注文"
]


def probe_store_keyword_candidates(user_text: str) -> List[str]:
    """店舗案内系キーワード候補（確定ではない）。"""
    detected, inquiry_type = _probe_store_inquiry_keywords(user_text)
    if not detected:
        return []
    tag = f"store_{inquiry_type}" if inquiry_type else "store_inquiry"
    extras: List[str] = []
    if detect_facilities_inquiry(user_text)[0]:
        extras.append("store_facilities")
    if detect_inventory_inquiry(user_text)[0]:
        extras.append("store_inventory")
    if detect_tax_free_inquiry(user_text):
        extras.append("store_tax_free")
    if detect_tourism_inquiry(user_text):
        extras.append("store_tourism")
    if detect_business_hours_inquiry(user_text):
        extras.append("store_business_hours")
    if detect_payment_inquiry(user_text):
        extras.append("store_payment")
    if detect_parking_inquiry(user_text):
        extras.append("store_parking")
    if detect_services_inquiry(user_text):
        extras.append("store_services")
    return [tag, *extras]


def detect_store_inquiry_keywords(user_text: str) -> Tuple[bool, Optional[str]]:
    """
    後方互換: 候補プローブ結果。単独ではルート確定に使わないこと。
    """
    return _probe_store_inquiry_keywords(user_text)


def _probe_store_inquiry_keywords(user_text: str) -> Tuple[bool, Optional[str]]:
    """
    キーワード候補のプローブ（店舗案内・遺失物）。最終判定は LLM + 文脈ゲート。
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
    # 「どこ」「場所」単独は文脈依存（店内・周辺・トイレ等と組み合わせ時のみ）
    store_inquiry_context_keywords = [
        "案内", "トイレ", "お手洗い", "店内", "売り場", "レジ", "棚",
    ]
    has_store_context = (
        any(keyword in user_text_lower for keyword in store_inquiry_context_keywords)
        or has_store_scoped_location_context(user_text)
        or has_facilities_spatial_context(user_text)
    )

    for keyword in STORE_INQUIRY_KEYWORDS:
        if keyword not in user_text_lower:
            continue
        if keyword in ["教えてください", "教えて"]:
            if has_store_context:
                logger.info(f"🔍 店舗案内関連キーワード検出（文脈あり）: {keyword}")
                return True, "store_inquiry"
            logger.debug(f"🔍 「{keyword}」は店舗文脈なしのためスキップ")
            continue
        if keyword in STORE_LOCATION_BARE_KEYWORDS:
            if has_store_context or has_facilities_spatial_context(user_text):
                logger.info(f"🔍 店舗案内関連キーワード検出（位置+文脈）: {keyword}")
                return True, "store_inquiry"
            logger.debug(f"🔍 「{keyword}」は位置質問のみのためスキップ")
            continue
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
                if should_defer_store_to_concierge(user_text, triage_result):
                    logger.info(
                        "🔍 トリアージ store 候補だが Concierge 優先のため店舗案内しない: %s",
                        subcategory,
                    )
                    return {
                        "is_store_inquiry": False,
                        "inquiry_type": None,
                        "confidence": 0.0,
                        "reasoning": "トリアージ候補を文脈ゲートが Concierge に譲渡",
                    }
                logger.info(f"🔍 トリアージ結果から店舗案内・遺失物関連を検出: {subcategory}")
                return {
                    "is_store_inquiry": True,
                    "inquiry_type": "store_inquiry" if "store_inquiry" in subcategory else "lost_and_found",
                    "confidence": triage_result.get("confidence", 0.8),
                    "reasoning": f"トリアージ LLM 結果: {subcategory}",
                }
            # general_otherの場合は店舗案内として扱わない（カウンセリングフローに流す）
            elif "general_other" in subcategory or subcategory == "":
                logger.info(f"🔍 トリアージ結果がgeneral_otherのため、店舗案内として扱わない: {subcategory}")
                return {
                    "is_store_inquiry": False,
                    "inquiry_type": None,
                    "confidence": 0.0,
                    "reasoning": f"トリアージ結果がgeneral_otherのため、店舗案内として扱わない: {subcategory}"
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
- 不適切なメッセージ（暴言、脅迫など）が含まれている場合は、is_store_inquiryをfalseに設定
- 意味不明なメッセージ、意味のないメッセージ、ランダムな文字列、繰り返しの文字列（例：「うんこうんこ」「ああああ」など）の場合は、is_store_inquiryをfalseに設定
- 不明な場合や曖昧な場合は、is_store_inquiryをfalseに設定（カウンセリングフローに流すため）
- 店舗案内や遺失物関連の明確な意図がない場合は、is_store_inquiryをfalseに設定

【回答形式】
JSON形式で回答してください：
{
    "is_store_inquiry": true/false,
    "inquiry_type": "store_inquiry" | "lost_and_found" | null,
    "confidence": 0.0-1.0の数値,
    "reasoning": "判定理由"
}
"""
        
        from src.core.llm_client import chat_completion_create

        response = chat_completion_create(
            client,
            model_role="triage",
            path="store_inquiry_handler.classify",
            messages=[
                {"role": "system", "content": "あなたは薬剤師です。店舗案内・遺失物関連の質問を正確に分類してください。"},
                {"role": "user", "content": f"{prompt}\n\n【ユーザーの入力】\n{user_text}"},
            ],
            temperature=0.1,
            max_tokens=200,
            response_format={"type": "json_object"},
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


def generate_feedback_section(user_text: str, response_content: str) -> str:
    """
    フィードバックボタンセクションを生成（医薬品相談フローと同じ構造）
    
    Args:
        user_text: ユーザーの入力テキスト
        response_content: 応答内容
    
    Returns:
        フィードバックボタンセクションのHTML
    """
    # エスケープ処理
    escaped_user_message = html.escape(user_text[:500] if len(user_text) > 500 else user_text)
    escaped_ai_response = html.escape(response_content[:500] if len(response_content) > 500 else response_content)
    
    # フィードバックデータ
    feedback_data = {
        'user_message': escaped_user_message,
        'ai_response': escaped_ai_response,
        'security_score': None,
        'inquiry_type': 'store_inquiry'
    }
    feedback_json = html.escape(json.dumps(feedback_data, ensure_ascii=False))
    
    # 不具合報告用のデータ属性
    bug_report_data_attrs = f'data-user-message="{escaped_user_message}" data-ai-response="{escaped_ai_response}" data-security-score=""'
    
    return f"""
    <div class="feedback-buttons">
        <p class="feedback-question">このメッセージはいかがでしたか？</p>
        <div class="feedback-buttons-container">
            <button class="feedback-btn-positive" onclick="handlePositiveFeedback({feedback_json})">
                適切
            </button>
            <button class="feedback-btn-negative" onclick="handleNegativeFeedback({feedback_json})">
                不適切
            </button>
            <button class="bug-report-btn" onclick="handleSecurityReportFromButton(this)" {bug_report_data_attrs}>
                🐛 不具合報告
            </button>
        </div>
    </div>"""


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
            
            # 応答内容を先に生成（フィードバックセクション生成のため）
            response_content = """トイレの場所についてお尋ねいただき、ありがとうございます。

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
    {generate_feedback_section(user_text, response_content)}
</div>"""
        else:
            simple_message = """トイレの場所についてお尋ねいただき、ありがとうございます。

店舗内にお越しいただいた際は、店内のスタッフにお尋ねいただければ、トイレの場所を詳しくご案内いたします。
お近くのスタッフまでお気軽にお声がけください。"""
            
            # 応答内容を先に生成（フィードバックセクション生成のため）
            response_content = """トイレの場所についてお尋ねいただき、ありがとうございます。

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
    {generate_feedback_section(user_text, response_content)}
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
        
        # 応答内容を先に生成（フィードバックセクション生成のため）
        response_content = """店舗内の場所についてお尋ねいただき、ありがとうございます。

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
    {generate_feedback_section(user_text, response_content)}
</div>"""
    else:
        # 店舗外の場合または判定できない場合: 一般的な案内のみ
        simple_message = """店舗の場所についてお尋ねいただき、ありがとうございます。

店舗内にお越しいただいた際は、店内のスタッフにお尋ねいただければ、詳しくご案内いたします。
お近くのスタッフまでお気軽にお声がけください。"""
        
        # 応答内容を先に生成（フィードバックセクション生成のため）
        response_content = """店舗の場所についてお尋ねいただき、ありがとうございます。

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
    {generate_feedback_section(user_text, response_content)}
</div>"""
    
    return {
        "simple_message": simple_message,
        "structured_html": structured_html
    }


def generate_facilities_inquiry_response(
    user_text: str,
    facility_name: Optional[str] = None
) -> Dict[str, str]:
    """
    周辺施設の応答を生成
    
    Args:
        user_text: ユーザーの入力テキスト
        facility_name: 施設名（検出された場合）
    
    Returns:
        {
            "simple_message": str,
            "structured_html": str
        }
    """
    simple_message = """周辺施設についてお尋ねいただき、ありがとうございます。

周辺施設の情報については、店内のスタッフにお尋ねいただければ、詳しくご案内いたします。
お近くのスタッフまでお気軽にお声がけください。"""
    
    facility_display = f"（{facility_name}）" if facility_name else ""
    
    # 応答内容を先に生成（フィードバックセクション生成のため）
    response_content = simple_message
    
    structured_html = f"""<div class="store-inquiry-response">
    <h4>🏢 周辺施設について{facility_display}</h4>
    <p>周辺施設についてお尋ねいただき、ありがとうございます。</p>
    <div class="inquiry-options">
        <p><strong>📍 ご案内方法</strong></p>
        <ul>
            <li>周辺施設の情報については、店内のスタッフにお尋ねいただければ、詳しくご案内いたします</li>
            <li>お近くのスタッフまでお気軽にお声がけください</li>
        </ul>
    </div>
    {generate_feedback_section(user_text, response_content)}
</div>"""
    
    return {
        "simple_message": simple_message,
        "structured_html": structured_html
    }


def generate_tax_free_inquiry_response(user_text: str) -> Dict[str, str]:
    """
    免税対応の応答を生成
    
    Args:
        user_text: ユーザーの入力テキスト
    
    Returns:
        {
            "simple_message": str,
            "structured_html": str
        }
    """
    simple_message = """免税対応についてお尋ねいただき、ありがとうございます。

免税対応の可否については、店内のスタッフにお尋ねいただければ、詳しくご案内いたします。
お近くのスタッフまでお気軽にお声がけください。"""
    
    # 応答内容を先に生成（フィードバックセクション生成のため）
    response_content = simple_message
    
    structured_html = f"""<div class="store-inquiry-response">
    <h4>💰 免税対応について</h4>
    <p>免税対応についてお尋ねいただき、ありがとうございます。</p>
    <div class="inquiry-options">
        <p><strong>📍 ご案内方法</strong></p>
        <ul>
            <li>免税対応の可否については、店内のスタッフにお尋ねいただければ、詳しくご案内いたします</li>
            <li>お近くのスタッフまでお気軽にお声がけください</li>
        </ul>
    </div>
    {generate_feedback_section(user_text, response_content)}
</div>"""
    
    return {
        "simple_message": simple_message,
        "structured_html": structured_html
    }


def generate_tourism_inquiry_response(user_text: str) -> Dict[str, str]:
    """
    周辺観光地の応答を生成
    
    Args:
        user_text: ユーザーの入力テキスト
    
    Returns:
        {
            "simple_message": str,
            "structured_html": str
        }
    """
    simple_message = """周辺観光地についてお尋ねいただき、ありがとうございます。

周辺観光地の情報については、店内のスタッフにお尋ねいただければ、詳しくご案内いたします。
お近くのスタッフまでお気軽にお声がけください。"""
    
    # 応答内容を先に生成（フィードバックセクション生成のため）
    response_content = simple_message
    
    structured_html = f"""<div class="store-inquiry-response">
    <h4>🗾 周辺観光地について</h4>
    <p>周辺観光地についてお尋ねいただき、ありがとうございます。</p>
    <div class="inquiry-options">
        <p><strong>📍 ご案内方法</strong></p>
        <ul>
            <li>周辺観光地の情報については、店内のスタッフにお尋ねいただければ、詳しくご案内いたします</li>
            <li>お近くのスタッフまでお気軽にお声がけください</li>
        </ul>
    </div>
    {generate_feedback_section(user_text, response_content)}
</div>"""
    
    return {
        "simple_message": simple_message,
        "structured_html": structured_html
    }


def generate_business_hours_inquiry_response(user_text: str) -> Dict[str, str]:
    """
    営業時間・アクセスの応答を生成
    
    Args:
        user_text: ユーザーの入力テキスト
    
    Returns:
        {
            "simple_message": str,
            "structured_html": str
        }
    """
    simple_message = """営業時間・アクセスについてお尋ねいただき、ありがとうございます。

営業時間やアクセス方法については、店内のスタッフにお尋ねいただければ、詳しくご案内いたします。
お近くのスタッフまでお気軽にお声がけください。"""
    
    # 応答内容を先に生成（フィードバックセクション生成のため）
    response_content = simple_message
    
    structured_html = f"""<div class="store-inquiry-response">
    <h4>🕐 営業時間・アクセスについて</h4>
    <p>営業時間・アクセスについてお尋ねいただき、ありがとうございます。</p>
    <div class="inquiry-options">
        <p><strong>📍 ご案内方法</strong></p>
        <ul>
            <li>営業時間やアクセス方法については、店内のスタッフにお尋ねいただければ、詳しくご案内いたします</li>
            <li>お近くのスタッフまでお気軽にお声がけください</li>
        </ul>
    </div>
    {generate_feedback_section(user_text, response_content)}
</div>"""
    
    return {
        "simple_message": simple_message,
        "structured_html": structured_html
    }


def generate_payment_inquiry_response(user_text: str) -> Dict[str, str]:
    """
    支払い方法の応答を生成
    
    Args:
        user_text: ユーザーの入力テキスト
    
    Returns:
        {
            "simple_message": str,
            "structured_html": str
        }
    """
    simple_message = """支払い方法についてお尋ねいただき、ありがとうございます。

支払い方法については、店内のスタッフにお尋ねいただければ、詳しくご案内いたします。
お近くのスタッフまでお気軽にお声がけください。"""
    
    # 応答内容を先に生成（フィードバックセクション生成のため）
    response_content = simple_message
    
    structured_html = f"""<div class="store-inquiry-response">
    <h4>💳 支払い方法について</h4>
    <p>支払い方法についてお尋ねいただき、ありがとうございます。</p>
    <div class="inquiry-options">
        <p><strong>📍 ご案内方法</strong></p>
        <ul>
            <li>支払い方法については、店内のスタッフにお尋ねいただければ、詳しくご案内いたします</li>
            <li>お近くのスタッフまでお気軽にお声がけください</li>
        </ul>
    </div>
    {generate_feedback_section(user_text, response_content)}
</div>"""
    
    return {
        "simple_message": simple_message,
        "structured_html": structured_html
    }


def generate_parking_inquiry_response(user_text: str) -> Dict[str, str]:
    """
    駐車場の応答を生成
    
    Args:
        user_text: ユーザーの入力テキスト
    
    Returns:
        {
            "simple_message": str,
            "structured_html": str
        }
    """
    simple_message = """駐車場についてお尋ねいただき、ありがとうございます。

駐車場の情報については、店内のスタッフにお尋ねいただければ、詳しくご案内いたします。
お近くのスタッフまでお気軽にお声がけください。"""
    
    # 応答内容を先に生成（フィードバックセクション生成のため）
    response_content = simple_message
    
    structured_html = f"""<div class="store-inquiry-response">
    <h4>🅿️ 駐車場について</h4>
    <p>駐車場についてお尋ねいただき、ありがとうございます。</p>
    <div class="inquiry-options">
        <p><strong>📍 ご案内方法</strong></p>
        <ul>
            <li>駐車場の情報については、店内のスタッフにお尋ねいただければ、詳しくご案内いたします</li>
            <li>お近くのスタッフまでお気軽にお声がけください</li>
        </ul>
    </div>
    {generate_feedback_section(user_text, response_content)}
</div>"""
    
    return {
        "simple_message": simple_message,
        "structured_html": structured_html
    }


def generate_services_inquiry_response(user_text: str) -> Dict[str, str]:
    """
    店舗サービスの応答を生成
    
    Args:
        user_text: ユーザーの入力テキスト
    
    Returns:
        {
            "simple_message": str,
            "structured_html": str
        }
    """
    simple_message = """店舗サービスについてお尋ねいただき、ありがとうございます。

店舗サービスについては、店内のスタッフにお尋ねいただければ、詳しくご案内いたします。
お近くのスタッフまでお気軽にお声がけください。"""
    
    # 応答内容を先に生成（フィードバックセクション生成のため）
    response_content = simple_message
    
    structured_html = f"""<div class="store-inquiry-response">
    <h4>🛎️ 店舗サービスについて</h4>
    <p>店舗サービスについてお尋ねいただき、ありがとうございます。</p>
    <div class="inquiry-options">
        <p><strong>📍 ご案内方法</strong></p>
        <ul>
            <li>店舗サービスについては、店内のスタッフにお尋ねいただければ、詳しくご案内いたします</li>
            <li>お近くのスタッフまでお気軽にお声がけください</li>
        </ul>
    </div>
    {generate_feedback_section(user_text, response_content)}
</div>"""
    
    return {
        "simple_message": simple_message,
        "structured_html": structured_html
    }


def generate_inventory_inquiry_response(
    user_text: str,
    product_category_info: Optional[Dict],
    store_location: Optional[str] = None
) -> Dict[str, str]:
    """
    在庫確認の応答を生成
    
    Args:
        user_text: ユーザーの入力テキスト
        product_category_info: 商品カテゴリ情報
        store_location: 店舗内外の判定
    
    Returns:
        {
            "simple_message": str,
            "structured_html": str
        }
    """
    # カテゴリ情報の表示用テキストを生成
    category_path = ""
    if product_category_info:
        category = product_category_info.get("category", "")
        subcategory = product_category_info.get("subcategory", "")
        product = product_category_info.get("product", "")
        
        if category and subcategory:
            category_path = f"{category} > {subcategory}"
            if product:
                category_path += f" > {product}"
    
    simple_message = """在庫確認についてお尋ねいただき、ありがとうございます。

店内のスタッフにお尋ねいただければ、在庫状況を詳しくご案内いたします。
お近くのスタッフまでお気軽にお声がけください。"""
    
    # 応答内容を先に生成（フィードバックセクション生成のため）
    response_content = simple_message
    
    structured_html = f"""<div class="store-inquiry-response">
    <h4>📦 在庫確認について</h4>
    <p>在庫確認についてお尋ねいただき、ありがとうございます。</p>
    {f'<p class="category-path"><strong>カテゴリ:</strong> {category_path}</p>' if category_path else ''}
    <div class="inquiry-options">
        <p><strong>📍 ご案内方法</strong></p>
        <ul>
            <li>店内のスタッフにお尋ねいただければ、在庫状況を詳しくご案内いたします</li>
            <li>お近くのスタッフまでお気軽にお声がけください</li>
        </ul>
    </div>
    {generate_feedback_section(user_text, response_content)}
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
        
        # 応答内容を先に生成（フィードバックセクション生成のため）
        response_content = simple_message
        
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
    {generate_feedback_section(user_text, response_content)}
</div>"""
    elif store_location == "outside":
        # 店舗外の場合: 警察への相談を案内
        simple_message = """遺失物についてお尋ねいただき、ありがとうございます。

店舗外で遺失物を拾われた場合は、お近くの警察署または交番にご相談ください。
警察署では遺失物の届出を受け付けています。"""
        
        # 応答内容を先に生成（フィードバックセクション生成のため）
        response_content = simple_message
        
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
    {generate_feedback_section(user_text, response_content)}
</div>"""
    else:
        # 判定できない場合: 両方の案内を表示
        simple_message = """遺失物についてお尋ねいただき、ありがとうございます。

【店舗内で拾われた場合】
店内のスタッフまでお声がけください。スタッフが適切に対応いたします。

【店舗外で拾われた場合】
お近くの警察署または交番にご相談ください。警察署では遺失物の届出を受け付けています。"""
        
        # 応答内容を先に生成（フィードバックセクション生成のため）
        response_content = simple_message
        
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
    {generate_feedback_section(user_text, response_content)}
</div>"""
    
    return {
        "simple_message": simple_message,
        "structured_html": structured_html
    }


def handle_store_inquiry_with_two_stage(
    user_text: str,
    client: OpenAI,
    triage_result: Optional[Dict] = None
) -> Optional[Dict]:
    """
    2段階判定で店舗案内を処理
    
    Args:
        user_text: ユーザーの入力テキスト
        client: OpenAIクライアントインスタンス
        triage_result: LLMトリアージ結果（第1段階の結果）
    
    Returns:
        処理が必要な場合: {
            "is_store_inquiry": True,
            "inquiry_type": str,
            "store_location": str | None,
            "response": Dict,
            "confidence": float,
            "reasoning": str
        }
        処理が不要な場合: None
    """
    # 第1段階: トリアージ結果を確認（Otherカテゴリの場合のみ処理）
    if not triage_result or triage_result.get("category") != "Other":
        logger.debug(f"🔍 第1段階: Otherカテゴリではないため、店舗案内処理をスキップ")
        return None
    
    if should_defer_store_to_concierge(user_text, triage_result):
        return None

    if triage_result is not None:
        candidates = probe_store_keyword_candidates(user_text)
        if candidates:
            merged = attach_routing_keyword_candidates(triage_result, candidates)
            triage_result.clear()
            triage_result.update(merged)

    # 第2段階: 店舗案内の詳細分類
    llm_result = classify_inquiry_with_llm(user_text, client, triage_result)
    confidence = llm_result.get("confidence", 0.0)
    is_store_inquiry = llm_result.get("is_store_inquiry", False)
    
    # is_store_inquiryがFalseの場合は、confidenceに関係なく店舗案内ではないと判定
    # 既存のOtherカテゴリの汎用応答処理（自己紹介、挨拶など）に進むため、Noneを返す
    if not is_store_inquiry:
        logger.info(f"🔍 第2段階: 店舗案内ではないと判定（is_store_inquiry=False, confidence={confidence:.2f}）")
        logger.info(f"🔍 既存のOtherカテゴリの汎用応答処理（自己紹介、挨拶など）に進む")
        return None
    
    # is_store_inquiryがTrueの場合のみ、confidence閾値による分岐を実行
    # confidence閾値による分岐
    if confidence >= 0.8:
        # 高確信度: 詳細分類を実行
        logger.info(f"🔍 高確信度（{confidence:.2f}）: 詳細分類を実行")
        return process_detailed_classification(user_text, llm_result, triage_result)
    elif confidence >= 0.7:
        # 中確信度: 汎用分類
        logger.info(f"🔍 中確信度（{confidence:.2f}）: 汎用分類を実行")
        return process_generic_classification(user_text, llm_result, triage_result)
    else:
        # 低確信度: キーワードフォールバックまたは症状検出
        logger.info(f"🔍 低確信度（{confidence:.2f}）: キーワードフォールバックまたは症状検出を実行")
        return process_low_confidence_case(user_text, llm_result, client, triage_result)


def classify_product_category(user_text: str) -> Optional[Dict]:
    """
    商品名をカテゴリベースで分類
    
    Args:
        user_text: ユーザーの入力テキスト
    
    Returns:
        検出された場合: {
            "category": str,  # カテゴリ名（例: "ビューティ・トイレタリー"）
            "subcategory": str,  # サブカテゴリ名（例: "石鹸"）
            "product": str,  # 商品名
            "matched_keyword": str  # マッチしたキーワード
        }
        検出されなかった場合: None
    """
    if not PRODUCT_CATEGORIES:
        return None
    
    user_text_lower = user_text.lower()
    
    # 各カテゴリをチェック
    for category_name, category_data in PRODUCT_CATEGORIES.items():
        subcategories = category_data.get("subcategories", {})
        
        for subcategory_name, subcategory_data in subcategories.items():
            products = subcategory_data.get("products", [])
            brands = subcategory_data.get("brands", [])
            
            # 商品名をチェック
            for product in products:
                if product.lower() in user_text_lower:
                    logger.info(f"🔍 商品カテゴリ検出: {category_name} > {subcategory_name} > {product}")
                    return {
                        "category": category_name,
                        "subcategory": subcategory_name,
                        "product": product,
                        "matched_keyword": product
                    }
            
            # ブランド名をチェック
            for brand in brands:
                if brand.lower() in user_text_lower:
                    logger.info(f"🔍 ブランド名検出: {category_name} > {subcategory_name} > {brand}")
                    return {
                        "category": category_name,
                        "subcategory": subcategory_name,
                        "product": brand,
                        "matched_keyword": brand
                    }
    
    return None


def detect_inventory_inquiry(user_text: str) -> Tuple[bool, Optional[Dict]]:
    """
    在庫確認の質問を検出
    
    Args:
        user_text: ユーザーの入力テキスト
    
    Returns:
        (is_inventory_inquiry, product_category_info): 
        - is_inventory_inquiry: 在庫確認の質問かどうか
        - product_category_info: 商品カテゴリ情報（検出された場合）
    """
    user_text_lower = user_text.lower()
    
    # まず商品カテゴリを分類（商品名が含まれているかチェック）
    product_category_info = classify_product_category(user_text)
    
    # 在庫確認キーワードをチェック
    has_inventory_keyword = any(keyword in user_text_lower for keyword in INVENTORY_INQUIRY_KEYWORDS)
    
    # 「場所」または「どこ」キーワードの特別処理：商品名が検出された場合のみ在庫確認として扱う
    if "場所" in user_text_lower or "どこ" in user_text_lower:
        if product_category_info:
            # 症状キーワードをチェック（症状の場合は医薬品推奨を優先）
            has_symptom_keyword = any(keyword in user_text_lower for keyword in SYMPTOM_KEYWORDS)
            if has_symptom_keyword:
                logger.info(f"🔍 在庫確認キーワード検出だが、症状キーワードも検出されたため医薬品推奨を優先")
                return False, None
            logger.info(f"🔍 在庫確認の質問を検出（商品名+場所/どこ）: {product_category_info}")
            return True, product_category_info
        # 商品名が検出されない場合は在庫確認として扱わない（店舗案内として扱う）
        return False, None
    
    # 通常の在庫確認キーワードがある場合
    if has_inventory_keyword:
        # 症状キーワードをチェック（症状の場合は医薬品推奨を優先）
        has_symptom_keyword = any(keyword in user_text_lower for keyword in SYMPTOM_KEYWORDS)
        
        if has_symptom_keyword:
            logger.info(f"🔍 在庫確認キーワード検出だが、症状キーワードも検出されたため医薬品推奨を優先")
            return False, None
        
        if product_category_info:
            logger.info(f"🔍 在庫確認の質問を検出: {product_category_info}")
            return True, product_category_info
        
        # 商品カテゴリが検出されなくても、在庫確認キーワードがあれば在庫確認として扱う
        logger.info(f"🔍 在庫確認の質問を検出（商品カテゴリ未特定）")
        return True, None
    
    return False, None


def detect_facilities_inquiry(user_text: str) -> Tuple[bool, Optional[str]]:
    """
    周辺施設の質問を検出（空間文脈 + 施設名/タイプの組み合わせ。単語ヒットのみでは検出しない）。
    """
    user_text_lower = _text_lower(user_text)
    if not user_text_lower:
        return False, None

    spatial = has_facilities_spatial_context(user_text)
    loc_q = has_facilities_location_question(user_text)
    store_scope = has_store_scoped_location_context(user_text)

    facility_name: Optional[str] = None
    for name in sorted(FACILITY_NAMES, key=len, reverse=True):
        if name.lower() in user_text_lower:
            facility_name = name
            break

    has_type = any(k in user_text_lower for k in FACILITY_TYPE_KEYWORDS)

    if facility_name and facility_name in FACILITY_NAMES_AMBIGUOUS:
        if spatial:
            logger.info(f"🔍 周辺施設の質問を検出（曖昧施設+空間文脈）: {facility_name}")
            return True, facility_name
        logger.info(
            f"🔍 周辺施設スキップ: 「{facility_name}」は位置質問のみ（運営者/メタと区別）"
        )
        return False, None

    if facility_name:
        if spatial or store_scope or (loc_q and (has_type or facility_name not in FACILITY_NAMES_AMBIGUOUS)):
            logger.info(f"🔍 周辺施設の質問を検出: {facility_name}")
            return True, facility_name
        logger.debug(f"🔍 周辺施設スキップ: {facility_name}（周辺/店内文脈なし）")
        return False, None

    if has_type and (spatial or (loc_q and not should_defer_store_to_concierge(user_text))):
        logger.info("🔍 周辺施設の質問を検出（施設タイプ+文脈）")
        return True, None

    if spatial and loc_q:
        logger.info("🔍 周辺施設の質問を検出（空間+位置質問）")
        return True, None

    return False, None


def _store_subtype_keyword_hit(
    user_text: str,
    keywords: List[str],
    *,
    require_store_scope: bool = False,
) -> bool:
    t = _text_lower(user_text)
    if not any(k in t for k in keywords):
        return False
    if require_store_scope and not (
        has_store_scoped_location_context(user_text)
        or has_facilities_spatial_context(user_text)
    ):
        return False
    return True


def detect_tax_free_inquiry(user_text: str) -> bool:
    return _store_subtype_keyword_hit(user_text, TAX_FREE_KEYWORDS)


def detect_tourism_inquiry(user_text: str) -> bool:
    if not _store_subtype_keyword_hit(user_text, TOURISM_KEYWORDS):
        return False
    return has_facilities_spatial_context(user_text) or has_facilities_location_question(user_text)


def detect_business_hours_inquiry(user_text: str) -> bool:
    return _store_subtype_keyword_hit(user_text, BUSINESS_HOURS_KEYWORDS)


def detect_payment_inquiry(user_text: str) -> bool:
    return _store_subtype_keyword_hit(
        user_text, PAYMENT_KEYWORDS, require_store_scope=True
    )


def detect_parking_inquiry(user_text: str) -> bool:
    return _store_subtype_keyword_hit(
        user_text, PARKING_KEYWORDS, require_store_scope=True
    )


def detect_services_inquiry(user_text: str) -> bool:
    return _store_subtype_keyword_hit(
        user_text, SERVICES_KEYWORDS, require_store_scope=True
    )


def process_detailed_classification(
    user_text: str,
    llm_result: Dict,
    triage_result: Optional[Dict]
) -> Optional[Dict]:
    """
    高確信度の場合の詳細分類処理
    """
    inquiry_type = llm_result.get("inquiry_type") or "store_inquiry"
    
    # 在庫確認の検出（商品名が検出された場合は優先的に処理）
    is_inventory, product_category_info = detect_inventory_inquiry(user_text)
    
    if is_inventory:
        # 在庫確認の応答を生成
        store_location = detect_store_location(user_text)
        response = generate_inventory_inquiry_response(user_text, product_category_info, store_location)
        
        return {
            "is_store_inquiry": True,
            "inquiry_type": "inventory",
            "store_location": store_location,
            "product_category": product_category_info,
            "response": response,
            "confidence": llm_result.get("confidence", 0.8),
            "reasoning": llm_result.get("reasoning", "")
        }
    
    # 周辺施設の検出
    is_facilities, facility_name = detect_facilities_inquiry(user_text)
    if is_facilities:
        response = generate_facilities_inquiry_response(user_text, facility_name)
        return {
            "is_store_inquiry": True,
            "inquiry_type": "facilities",
            "store_location": None,
            "product_category": None,
            "facility_name": facility_name,
            "response": response,
            "confidence": llm_result.get("confidence", 0.8),
            "reasoning": llm_result.get("reasoning", "")
        }
    
    # 免税対応の検出
    if detect_tax_free_inquiry(user_text):
        response = generate_tax_free_inquiry_response(user_text)
        return {
            "is_store_inquiry": True,
            "inquiry_type": "tax_free",
            "store_location": None,
            "product_category": None,
            "response": response,
            "confidence": llm_result.get("confidence", 0.8),
            "reasoning": llm_result.get("reasoning", "")
        }
    
    # 周辺観光地の検出
    if detect_tourism_inquiry(user_text):
        response = generate_tourism_inquiry_response(user_text)
        return {
            "is_store_inquiry": True,
            "inquiry_type": "tourism",
            "store_location": None,
            "product_category": None,
            "response": response,
            "confidence": llm_result.get("confidence", 0.8),
            "reasoning": llm_result.get("reasoning", "")
        }
    
    # 営業時間・アクセスの検出
    if detect_business_hours_inquiry(user_text):
        response = generate_business_hours_inquiry_response(user_text)
        return {
            "is_store_inquiry": True,
            "inquiry_type": "business_hours",
            "store_location": None,
            "product_category": None,
            "response": response,
            "confidence": llm_result.get("confidence", 0.8),
            "reasoning": llm_result.get("reasoning", "")
        }
    
    # 支払い方法の検出
    if detect_payment_inquiry(user_text):
        response = generate_payment_inquiry_response(user_text)
        return {
            "is_store_inquiry": True,
            "inquiry_type": "payment",
            "store_location": None,
            "product_category": None,
            "response": response,
            "confidence": llm_result.get("confidence", 0.8),
            "reasoning": llm_result.get("reasoning", "")
        }
    
    # 駐車場の検出
    if detect_parking_inquiry(user_text):
        response = generate_parking_inquiry_response(user_text)
        return {
            "is_store_inquiry": True,
            "inquiry_type": "parking",
            "store_location": None,
            "product_category": None,
            "response": response,
            "confidence": llm_result.get("confidence", 0.8),
            "reasoning": llm_result.get("reasoning", "")
        }
    
    # 店舗サービスの検出
    if detect_services_inquiry(user_text):
        response = generate_services_inquiry_response(user_text)
        return {
            "is_store_inquiry": True,
            "inquiry_type": "services",
            "store_location": None,
            "product_category": None,
            "response": response,
            "confidence": llm_result.get("confidence", 0.8),
            "reasoning": llm_result.get("reasoning", "")
        }
    
    if should_defer_store_to_concierge(user_text, triage_result):
        logger.info("🔍 汎用店舗案内をスキップ（Concierge 優先）")
        return None

    # その他の店舗案内
    store_location = detect_store_location(user_text)
    response = generate_store_inquiry_response(user_text, inquiry_type, store_location)

    return {
        "is_store_inquiry": True,
        "inquiry_type": inquiry_type,
        "store_location": store_location,
        "product_category": None,
        "response": response,
        "confidence": llm_result.get("confidence", 0.8),
        "reasoning": llm_result.get("reasoning", "")
    }


def process_generic_classification(
    user_text: str,
    llm_result: Dict,
    triage_result: Optional[Dict]
) -> Optional[Dict]:
    """
    中確信度の場合の汎用分類処理
    """
    if should_defer_store_to_concierge(user_text, triage_result):
        return None
    inquiry_type = llm_result.get("inquiry_type") or "store_inquiry"
    store_location = detect_store_location(user_text)
    response = generate_store_inquiry_response(user_text, inquiry_type, store_location)
    
    return {
        "is_store_inquiry": True,
        "inquiry_type": inquiry_type,
        "store_location": store_location,
        "response": response,
        "confidence": llm_result.get("confidence", 0.7),
        "reasoning": llm_result.get("reasoning", "")
    }


def process_low_confidence_case(
    user_text: str,
    llm_result: Dict,
    client: OpenAI,
    triage_result: Optional[Dict]
) -> Optional[Dict]:
    """
    低確信度の場合の処理（キーワードフォールバックまたは第1段階の再実行）
    """
    # 症状キーワードをチェック（症状の場合は医薬品推奨を優先）
    user_text_lower = user_text.lower()
    has_symptom_keyword = any(keyword in user_text_lower for keyword in SYMPTOM_KEYWORDS)
    
    if has_symptom_keyword:
        logger.info(f"🔍 症状キーワードが検出されたため、医薬品推奨フローへ")
        return None
    
  # キーワードは候補のみ — 低確信時は LLM 再実行へ（単独確定しない）
    candidates = probe_store_keyword_candidates(user_text)
    if candidates and triage_result is not None:
        merged = attach_routing_keyword_candidates(triage_result, candidates)
        triage_result.clear()
        triage_result.update(merged)
        logger.info("🔍 店舗キーワード候補を記録（確定せず）: %s", candidates)

    logger.info("🔍 低確信: キーワード単独確定は行わず第1段階を再実行")
    retry_result = retry_first_stage_with_modified_prompt(user_text, client)
    
    if retry_result and retry_result.get("category") == "Other":
        # 再実行結果がOtherの場合、サブカテゴリを確認
        subcategory = retry_result.get("subcategory", "").lower()
        if "store_inquiry" in subcategory or "lost_and_found" in subcategory:
            # 店舗案内または遺失物関連の場合のみ店舗案内として処理
            store_location = detect_store_location(user_text)
            inquiry_type = "lost_and_found" if "lost_and_found" in subcategory else "store_inquiry"
            response = generate_store_inquiry_response(user_text, inquiry_type, store_location)
            
            return {
                "is_store_inquiry": True,
                "inquiry_type": inquiry_type,
                "store_location": store_location,
                "response": response,
                "confidence": retry_result.get("confidence", 0.6),
                "reasoning": f"第1段階再実行結果: {retry_result.get('reasoning', '')}"
            }
        else:
            # Otherカテゴリだが、store_inquiry/lost_and_found以外（general_otherなど）の場合はNoneを返す
            # これにより、既存のOtherカテゴリの汎用応答処理（自己紹介、挨拶など）に進む
            logger.info(f"🔍 第1段階再実行結果: Otherカテゴリだが、general_otherのため既存の汎用応答処理に進む")
            return None
    
    # 再実行結果がOtherでない場合、Noneを返して症状検出または既存の汎用応答処理に進む
    logger.info(f"🔍 第1段階再実行結果: Otherカテゴリではないため、症状検出または既存の汎用応答処理に進む")
    return None


def retry_first_stage_with_modified_prompt(
    user_text: str,
    client: OpenAI
) -> Optional[Dict]:
    """
    プロンプトを修正して第1段階（LLMトリアージ）を再実行
    
    Args:
        user_text: ユーザーの入力テキスト
        client: OpenAIクライアントインスタンス
    
    Returns:
        再実行されたトリアージ結果
    """
    try:
        from llm_triage import TRIAGE_PROMPT, llm_triage
        
        # プロンプトを修正（店舗案内や遺失物関連の可能性を強調）
        modified_prompt = f"""
{TRIAGE_PROMPT}

【重要】第2段階で信頼度が低いため、再判定してください。
ユーザーの入力が店舗案内や遺失物関連の質問である可能性を再検討してください。
特に以下のパターンに注意してください：
- 「ありますか」「どこですか」「在庫」などのキーワードがある場合 → Other（subcategory: store_inquiry）
- 「忘れ物」「落とし物」などのキーワードがある場合 → Other（subcategory: lost_and_found）
- 「場所を教えて」「どこにありますか」などのキーワードがある場合 → Other（subcategory: store_inquiry）
"""
        
        # LLMトリアージを再実行
        retry_result = llm_triage(user_text, client)
        logger.info(f"🔍 第1段階再実行結果: {retry_result.get('category')}, confidence: {retry_result.get('confidence', 0.0):.2f}")
        
        return retry_result
        
    except Exception as e:
        logger.error(f"❌ 第1段階再実行エラー: {e}")
        import traceback
        traceback.print_exc()
        return None


def handle_store_inquiry(
    user_text: str,
    client: OpenAI,
    triage_result: Optional[Dict] = None
) -> Optional[Dict]:
    """
    店舗案内・遺失物関連の質問を処理（2段階判定を使用）
    
    Args:
        user_text: ユーザーの入力テキスト
        client: OpenAIクライアントインスタンス
        triage_result: LLMトリアージ結果（第1段階の結果）
    
    Returns:
        処理が必要な場合: {
            "is_store_inquiry": True,
            "inquiry_type": str,
            "store_location": str | None,
            "response": {
                "simple_message": str,
                "structured_html": str
            },
            "confidence": float,
            "reasoning": str
        }
        処理が不要な場合: None
    """
    # 2段階判定を使用
    return handle_store_inquiry_with_two_stage(user_text, client, triage_result)

