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

from src.services.store_inquiry_keyword_catalog import get_store_inquiry_keywords

logger = logging.getLogger(__name__)

# 商品照合は store_product_index（Aho-Corasick）に委譲

# 店舗案内キーワード（data/store_inquiry_keyword_catalog.json が定義元）
_STORE_KW = get_store_inquiry_keywords()
STORE_INQUIRY_KEYWORDS = _STORE_KW.store_inquiry_keywords
STORE_INQUIRY_CONTEXT_DEPENDENT_KEYWORDS = _STORE_KW.store_inquiry_context_dependent_keywords
SYMPTOM_KEYWORDS_FOR_TOILET = _STORE_KW.symptom_keywords_for_toilet
LOST_AND_FOUND_KEYWORDS = _STORE_KW.lost_and_found_keywords
STORE_LOCATION_KEYWORDS = {
    "inside": _STORE_KW.store_location_inside,
    "outside": _STORE_KW.store_location_outside,
}

_EXTERNAL_CHAIN_KEYWORDS = (
    "マツキヨ",
    "マツモトキヨシ",
    "ウエルシア",
    "ツルハ",
    "サンドラッグ",
    "ココカラファインファーマシー",
    "ココカラ",
    "スギ薬局",
    "セイムス",
)

_LOCATION_INQUIRY_HINTS = ("近く", "どこ", "ありますか", "近隣", "場所")


def classify_store_user_intent(user_text: str) -> str:
    """
    店舗入力の意図分類。
    Returns: facilities | locator | inventory | external_chain | generic
    """
    t = (user_text or "").strip()
    if not t:
        return "generic"
    if _has_explicit_store_stock_intent(t):
        return "inventory"
    if detect_external_chain_location_inquiry(t):
        return "external_chain"
    if any(h in t for h in _LOCATION_INQUIRY_HINTS) or "ドラッグストア" in t:
        if any(k in t for k in ("薬局", "ドラッグストア", "店", "売場")):
            return "locator"
        return "facilities"
    return "generic"


def detect_external_chain_location_inquiry(user_text: str) -> bool:
    t = user_text or ""
    if "ドラッグストア" in t and any(h in t for h in _LOCATION_INQUIRY_HINTS):
        return True
    has_chain = any(k in t for k in _EXTERNAL_CHAIN_KEYWORDS)
    has_location = any(h in t for h in _LOCATION_INQUIRY_HINTS)
    return bool(has_chain and has_location)


def _external_chain_location_message() -> Dict[str, str]:
    simple_message = (
        "当キオスクでは近隣店舗の位置情報は提供できません。"
        "地図アプリまたは各チェーンの公式サイトでご確認ください。\n\n"
        "店内の市販薬（OTC）売場や在庫については、お近くのスタッフにお声がけください。"
    )
    structured_html = f"""<div class="store-inquiry-response">
    <h4>🏪 近隣店舗のご案内</h4>
    <p>{html.escape(simple_message).replace(chr(10), "<br>")}</p>
</div>"""
    return {"simple_message": simple_message, "structured_html": structured_html}
INVENTORY_INQUIRY_KEYWORDS = _STORE_KW.inventory_inquiry_keywords
SYMPTOM_KEYWORDS = _STORE_KW.symptom_keywords
FACILITIES_SPATIAL_KEYWORDS = _STORE_KW.spatial_keywords
FACILITY_TYPE_KEYWORDS = _STORE_KW.facility_type_keywords
FACILITIES_LOCATION_QUESTION_KEYWORDS = _STORE_KW.location_question_keywords
STORE_LOCATION_BARE_KEYWORDS = _STORE_KW.store_location_bare_keywords
FACILITY_NAMES_AMBIGUOUS = _STORE_KW.facility_names_ambiguous
FACILITY_NAMES = _STORE_KW.facility_names
TAX_FREE_KEYWORDS = _STORE_KW.tax_free_keywords
TOURISM_KEYWORDS = _STORE_KW.tourism_keywords
BUSINESS_HOURS_KEYWORDS = _STORE_KW.business_hours_keywords
PAYMENT_KEYWORDS = _STORE_KW.payment_keywords
PARKING_KEYWORDS = _STORE_KW.parking_keywords
SERVICES_KEYWORDS = _STORE_KW.services_keywords


def _store_match_text(user_text: str) -> str:
    """店舗案内キーワード照合用（basic_normalize_text と同じ正規化を適用）。"""
    raw = (user_text or "").strip()
    if not raw:
        return ""
    try:
        from src.core.scoring_utils import basic_normalize_text

        return basic_normalize_text(raw)
    except ImportError:
        return raw.lower()


def _contains_store_keyword(user_text: str, keyword: str) -> bool:
    if not keyword:
        return False
    match_text = _store_match_text(user_text)
    norm_kw = _store_match_text(keyword)
    if norm_kw:
        return norm_kw in match_text
    return keyword in match_text


# 部分一致だと症状文（例: 「熱があります」）に誤マッチする短い在庫キーワード
_INVENTORY_SUBSTRING_AMBIGUOUS = frozenset({"あります", "どこ", "場所は", "取り扱い"})


def _matches_inventory_keyword(user_text: str, keyword: str) -> bool:
    """
    在庫キーワード照合。フレーズとして含まれる場合のみ True。

    短い曖昧語は全文一致のみ（それ以外はオーケストレーター／トリアージに委譲）。
    「あります」は「があります」（症状）への部分一致を除外する。
    """
    if not keyword:
        return False
    match_text = _store_match_text(user_text)
    norm_kw = _store_match_text(keyword)
    if not norm_kw:
        return False
    if norm_kw in _INVENTORY_SUBSTRING_AMBIGUOUS:
        return match_text.strip() == norm_kw.strip()
    if norm_kw not in match_text:
        return False
    if norm_kw == "あります" and "があります" in match_text:
        return False
    return True


def _text_lower(user_text: str) -> str:
    return _store_match_text(user_text)


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
    return any(
        _contains_store_keyword(user_text, k)
        for k in _STORE_KW.store_scoped_keywords
    )


_TOILET_NEED_PHRASES = tuple(_STORE_KW.toilet_keywords[:6])
_TOILET_PRODUCT_MARKERS = ("トイレット", "トイレ用", "トイレ洗")


def _is_toilet_product_query(user_text: str) -> bool:
    """トイレットペーパー等の商品問い合わせ（施設案内と区別）。"""
    t = _text_lower(user_text)
    if any(m in t for m in _TOILET_PRODUCT_MARKERS):
        return True
    product_ctx = any(
        k in t
        for k in ("売", "買", "在庫", "扱", "取り", "購入", "ペーパー", "洗剤", "ブラシ")
    )
    if product_ctx and "トイレ" in t:
        return True
    info = classify_product_category(user_text)
    if not info:
        return False
    for field in ("product", "matched_term", "category", "subcategory"):
        val = str(info.get(field) or "").lower()
        if any(m in val for m in _TOILET_PRODUCT_MARKERS):
            return True
    return False


def _is_toilet_facility_request(user_text: str) -> bool:
    """トイレ施設の場所・利用需要（商品名の「トイレ」と症状文脈は除外）。"""
    if _is_toilet_product_query(user_text):
        return False
    if any(_contains_store_keyword(user_text, phrase) for phrase in _TOILET_NEED_PHRASES):
        has_symptom = any(
            _contains_store_keyword(user_text, k) for k in SYMPTOM_KEYWORDS_FOR_TOILET
        )
        return not has_symptom
    for keyword in _STORE_KW.toilet_keywords:
        if keyword in _TOILET_NEED_PHRASES:
            continue
        if not _contains_store_keyword(user_text, keyword):
            continue
        if keyword in ("トイレ", "といれ") and _is_toilet_product_query(user_text):
            continue
        has_symptom = any(
            _contains_store_keyword(user_text, k) for k in SYMPTOM_KEYWORDS_FOR_TOILET
        )
        if has_symptom:
            return False
        return True
    return False


def _is_ambiguous_facility_defer_only(user_text: str) -> bool:
    """大学はどこ？など、店舗案内ではなく Concierge へ譲る曖昧施設の位置質問。"""
    t = _text_lower(user_text)
    if not t:
        return False
    for name in FACILITY_NAMES_AMBIGUOUS:
        if name.lower() in t and has_facilities_location_question(user_text):
            if not has_facilities_spatial_context(user_text) and not has_store_scoped_location_context(user_text):
                return True
    return False


def is_store_route_locked(triage_result: Optional[Dict] = None) -> bool:
    """LLM トリアージで店舗案内・遺失物が確定している場合 True（Concierge redirect 禁止）。"""
    triage = triage_result or {}
    if triage.get("category") != "Other":
        return False
    sub = (triage.get("subcategory") or "").lower()
    return "lost_and_found" in sub or "store_inquiry" in sub


def has_unambiguous_store_intent(user_text: str) -> bool:
    """医療相談と競合しない、明確な店舗案内・遺失物・在庫（店舗文脈）意図。"""
    try:
        from src.services.counseling_triage import classify_medicine_procurement_route

        if classify_medicine_procurement_route(user_text):
            return True
    except ImportError:
        pass
    if _is_toilet_facility_request(user_text):
        return True
    if _is_ambiguous_facility_defer_only(user_text):
        return False
    detected, itype = _probe_store_inquiry_keywords(user_text)
    if detected and itype == "lost_and_found":
        return True
    if detected and has_store_scoped_location_context(user_text):
        return True
    if detect_business_hours_inquiry(user_text):
        return True
    if detect_tax_free_inquiry(user_text):
        return True
    if detect_payment_inquiry(user_text):
        return True
    if detect_parking_inquiry(user_text):
        return True
    if detect_services_inquiry(user_text):
        return True
    inv_ok, inv_info = detect_inventory_inquiry(user_text)
    if inv_ok and inv_info is not None:
        return True
    if inv_ok and _has_explicit_store_stock_intent(user_text):
        return True
    fac_ok, _ = detect_facilities_inquiry(user_text)
    if fac_ok and (
        has_facilities_spatial_context(user_text)
        or has_facilities_location_question(user_text)
    ):
        return True
    return False


def _has_explicit_store_stock_intent(user_text: str) -> bool:
    """症状・薬探索ではない、店舗在庫・売場位置の明示的意図。"""
    text = (user_text or "").lower()
    if not text:
        return False
    explicit_stock = (
        "在庫",
        "取り寄せ",
        "売ってい",
        "扱ってい",
        "売り場",
        "店内",
        "店舗",
        "置いて",
    )
    return any(k in text for k in explicit_stock)


def is_probable_store_inquiry(
    user_text: str,
    triage_result: Optional[Dict] = None,
) -> bool:
    """店舗案内・遺失物の可能性が高く StoreInquiryAgent を優先すべき入力。

    同一リクエストで is_probable が複数回呼ばれると商品全件スキャンが重複する。
    routing_context.evaluate_store_gate でキャッシュすること（従来 5 回で ~3s 程度）。
    """
    from src.utils.input_helpers import should_prioritize_medical_route_over_store

    if should_prioritize_medical_route_over_store(triage_result, user_text):
        return False
    try:
        from src.services.counseling_triage import classify_medicine_procurement_route

        if classify_medicine_procurement_route(user_text):
            return True
    except ImportError:
        pass
    from src.utils.input_helpers import has_explicit_symptom_signal

    if has_explicit_symptom_signal(user_text) and not _has_explicit_store_stock_intent(user_text):
        return False
    from src.services.concierge_intent import looks_like_service_identity_question

    if looks_like_service_identity_question(user_text):
        return False
    if _is_toilet_facility_request(user_text):
        return True
    if _is_ambiguous_facility_defer_only(user_text):
        return False
    if is_store_route_locked(triage_result):
        return True
    triage = triage_result or {}
    sub = (triage.get("subcategory") or "").lower()
    if triage.get("category") == "Other":
        if "lost_and_found" in sub or "store_inquiry" in sub:
            return True
    detected, itype = _probe_store_inquiry_keywords(user_text)
    if detected and itype == "lost_and_found":
        return True
    if detected and has_store_scoped_location_context(user_text):
        return True
    if detect_business_hours_inquiry(user_text):
        return True
    if detect_tax_free_inquiry(user_text):
        return True
    if detect_payment_inquiry(user_text):
        return True
    if detect_parking_inquiry(user_text):
        return True
    if detect_services_inquiry(user_text):
        return True
    inv_ok, _ = detect_inventory_inquiry(user_text, triage_result)
    if inv_ok:
        return True
    fac_ok, _ = detect_facilities_inquiry(user_text)
    if fac_ok and (
        has_facilities_spatial_context(user_text)
        or has_facilities_location_question(user_text)
    ):
        return True
    return False


def _store_text_variants(*texts: Optional[str]) -> List[str]:
    """原文・正規化後など、重複を除いた照合用テキスト列。"""
    seen: set[str] = set()
    out: List[str] = []
    for text in texts:
        t = (text or "").strip()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def is_probable_store_inquiry_any(
    *texts: str,
    triage_result: Optional[Dict] = None,
) -> bool:
    """複数表記（原文 / sanitized）のいずれかが店舗案内候補なら True。"""
    seen: set[str] = set()
    for text in texts:
        t = (text or "").strip()
        if not t or t in seen:
            continue
        seen.add(t)
        if is_probable_store_inquiry(t, triage_result):
            return True
    return False


def should_defer_store_to_concierge(
    user_text: str,
    triage_result: Optional[Dict] = None,
) -> bool:
    """
    キーワードだけで店舗案内にせず Concierge / メタ応答へ譲る。
    明確な店舗案内（トイレ・店内案内等）は is_probable_store_inquiry で除外する。
    """
    if is_probable_store_inquiry(user_text, triage_result):
        return False
    triage = triage_result or {}
    if triage.get("concierge_intent"):
        logger.info(
            "🔍 店舗案内をスキップ: concierge_intent=%s",
            triage.get("concierge_intent"),
        )
        return True
    if _is_ambiguous_facility_defer_only(user_text):
        logger.info("🔍 店舗案内をスキップ: 曖昧施設 + 位置質問（周辺文脈なし）")
        return True
    return False


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
    user_text_lower = _store_match_text(user_text)
    
    # 遺失物関連のキーワードをチェック（優先度が高い）
    for keyword in LOST_AND_FOUND_KEYWORDS:
        if _contains_store_keyword(user_text, keyword):
            logger.info(f"🔍 遺失物関連キーワード検出: {keyword}")
            return True, "lost_and_found"
    
    # トイレ関連（商品名の「トイレットペーパー」と区別）
    if _is_toilet_facility_request(user_text):
        logger.info("🔍 トイレ案内として処理")
        return True, "store_inquiry"
    
    # その他の店舗案内関連のキーワードをチェック
    # 「どこ」「場所」単独は文脈依存（店内・周辺・トイレ等と組み合わせ時のみ）
    has_store_context = (
        any(
            _contains_store_keyword(user_text, keyword)
            for keyword in _STORE_KW.store_inquiry_context_keywords
        )
        or has_store_scoped_location_context(user_text)
        or has_facilities_spatial_context(user_text)
    )

    for keyword in STORE_INQUIRY_KEYWORDS:
        if not _contains_store_keyword(user_text, keyword):
            continue
        if keyword in STORE_INQUIRY_CONTEXT_DEPENDENT_KEYWORDS:
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
    intent = classify_store_user_intent(user_text)
    if intent == "external_chain":
        return _external_chain_location_message()

    is_toilet_inquiry = _is_toilet_facility_request(user_text)
    
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


def generate_medicine_procurement_response(user_text: str, route: str) -> Dict[str, str]:
    """OTC 購入先・処方箋医薬品の薬局案内応答。"""
    if route == "pharmacy_prescription":
        simple_message = """処方箋医薬品の入手についてお尋ねいただき、ありがとうございます。

処方箋医薬品は医師の処方と薬局での調剤が必要です。処方箋をお持ちのうえ、お近くの薬局または店内の薬局売場のスタッフにお尋ねください。
スタッフが受付・売場のご案内をいたします。"""
        title = "💊 処方箋医薬品・薬局について"
    else:
        simple_message = """市販薬（OTC）の購入場所についてお尋ねいただき、ありがとうございます。

当店では市販薬を取り扱っております。売場の場所や在庫については、店内のスタッフにお尋ねいただければ詳しくご案内いたします。
お近くのスタッフまでお気軽にお声がけください。"""
        title = "🛒 市販薬の購入場所について"

    response_content = simple_message
    structured_html = f"""<div class="store-inquiry-response">
    <h4>{html.escape(title)}</h4>
    <p>{html.escape(simple_message).replace(chr(10), "<br>")}</p>
    <div class="inquiry-options">
        <p><strong>📍 ご案内方法</strong></p>
        <p>店内のスタッフにお尋ねいただければ、売場や薬局窓口をご案内いたします。</p>
    </div>
    {generate_feedback_section(user_text, response_content)}
</div>"""
    return {
        "simple_message": simple_message,
        "structured_html": structured_html,
    }


def _resolve_procurement_store_response(
    user_text: str,
    triage_result: Optional[Dict],
    *,
    confidence: float = 0.9,
    reasoning: str = "医薬品購入先 fast-path",
) -> Dict:
    from src.services.counseling_triage import classify_medicine_procurement_route

    route = classify_medicine_procurement_route(user_text) or "otc_store"
    inquiry_type = "facilities" if route == "pharmacy_prescription" else "inventory"
    response = generate_medicine_procurement_response(user_text, route)
    return {
        "is_store_inquiry": True,
        "inquiry_type": inquiry_type,
        "store_location": detect_store_location(user_text),
        "product_category": None,
        "facility_name": "薬局" if route == "pharmacy_prescription" else None,
        "procurement_route": route,
        "response": response,
        "confidence": confidence,
        "reasoning": reasoning,
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
    label = facility_name or "周辺施設"
    facility_display = f"（{facility_name}）" if facility_name else ""
    simple_message = f"""{label}の場所についてお尋ねいただき、ありがとうございます。

周辺のご案内は詳しい情報をお持ちしていないため、店内のスタッフにお尋ねください。
お近くのスタッフまでお気軽にお声がけください。"""
    
    response_content = simple_message
    
    structured_html = f"""<div class="store-inquiry-response">
    <h4>🏢 {html.escape(label)}について{facility_display}</h4>
    <p>{html.escape(simple_message).replace(chr(10), "<br>")}</p>
    <div class="inquiry-options">
        <p><strong>📍 ご案内方法</strong></p>
        <p>店内のスタッフにお尋ねいただければ、周辺の施設についてご案内いたします。</p>
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
    # 商品名は冒頭に簡潔に。カテゴリ階層は補足欄用
    product_name = ""
    category_path = ""
    if product_category_info:
        category = product_category_info.get("category", "")
        subcategory = product_category_info.get("subcategory", "")
        product = product_category_info.get("product", "")
        product_name = str(product or subcategory or "").strip()
        parts = [p for p in (category, subcategory, product) if p]
        category_path = " > ".join(parts)

    if product_name:
        opening = f"「{product_name}」の在庫・お取り扱いについてお尋ねいただき、ありがとうございます。"
    else:
        opening = "在庫確認についてお尋ねいただき、ありがとうございます。"

    simple_message = f"""{opening}

店内のスタッフにお尋ねいただければ、在庫状況を詳しくご案内いたします。
お近くのスタッフまでお気軽にお声がけください。"""
    
    response_content = simple_message
    
    structured_html = f"""<div class="store-inquiry-response">
    <h4>📦 在庫確認について</h4>
    <p>{html.escape(opening)}</p>
    {f'<p class="category-path"><strong>売場の目安:</strong> {html.escape(category_path)}</p>' if category_path and category_path != product_name else ''}
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
    triage_result: Optional[Dict] = None,
    *,
    extra_texts: Optional[List[str]] = None,
) -> Optional[Dict]:
    """
    2段階判定で店舗案内を処理
    
    Args:
        user_text: ユーザーの入力テキスト（通常は sanitized）
        client: OpenAIクライアントインスタンス
        triage_result: LLMトリアージ結果（第1段階の結果）
        extra_texts: 原文など追加の照合用テキスト
    
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
    texts = _store_text_variants(user_text, *(extra_texts or []))
    if not texts:
        return None
    primary = texts[0]

    # 第1段階: トリアージ結果を確認（店舗案内候補は Other 以外でも fast-path 可）
    probable = is_probable_store_inquiry_any(*texts, triage_result=triage_result)
    if not probable and (not triage_result or triage_result.get("category") != "Other"):
        logger.debug("🔍 第1段階: Otherカテゴリではないため、店舗案内処理をスキップ")
        return None
    
    if should_defer_store_to_concierge(primary, triage_result) and not probable:
        return None

    if probable:
        active_text = primary
        try:
            from src.services.counseling_triage import classify_medicine_procurement_route

            proc_route = classify_medicine_procurement_route(active_text)
            if proc_route:
                result = _resolve_procurement_store_response(
                    active_text,
                    triage_result,
                    reasoning="医薬品購入先 fast-path",
                )
                logger.info(
                    "🔍 医薬品購入先 fast-path: route=%s",
                    proc_route,
                )
                return result
        except ImportError:
            pass
        detected, inquiry_type = False, None
        for candidate in texts:
            if not is_probable_store_inquiry(candidate, triage_result):
                continue
            detected, inquiry_type = _probe_store_inquiry_keywords(candidate)
            if detected:
                active_text = candidate
                break
        sub = (triage_result.get("subcategory") or "").lower() if triage_result else ""
        if not inquiry_type and "lost_and_found" in sub:
            inquiry_type = "lost_and_found"
        inquiry_type = inquiry_type or "store_inquiry"
        confidence = max(float((triage_result or {}).get("confidence") or 0), 0.85)
        result = _resolve_detailed_store_response(
            active_text,
            inquiry_type,
            triage_result,
            confidence=confidence,
            reasoning="店舗案内キーワード fast-path",
        )
        logger.info("🔍 店舗案内キーワード fast-path: %s", result.get("inquiry_type"))
        return result

    # 第2段階: 店舗案内の詳細分類
    llm_result = classify_inquiry_with_llm(primary, client, triage_result)
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
    """商品名をカテゴリベースで分類（store_product_index に委譲）。"""
    from src.services.store_product_index import classify_product_category as _classify

    return _classify(user_text)


def classify_product_category_any(*texts: Optional[str]) -> Optional[Dict]:
    """複数表記のいずれかで商品カテゴリを特定。"""
    for text in _store_text_variants(*texts):
        found = classify_product_category(text)
        if found:
            return found
    return None


def _triage_hints_inventory(triage_result: Optional[Dict]) -> bool:
    triage = triage_result or {}
    if triage.get("category") != "Other":
        return False
    sub = (triage.get("subcategory") or "").lower()
    return "store_inquiry" in sub or "inventory" in sub


def _should_skip_inventory_for_medical_triage(
    user_text: str,
    triage_result: Optional[Dict],
) -> bool:
    """Physical/Ask 高確信トリアージでは、店舗在庫の明示語がなければ在庫ゲートを通さない。"""
    triage = triage_result or {}
    category = triage.get("category", "")
    if category not in ("Physical", "Ask"):
        return False
    sub = str(triage.get("subcategory") or "").lower()
    if sub.startswith("store_inquiry") or sub == "lost_and_found":
        return False
    from config.routing_config import triage_confidence_threshold

    if float(triage.get("confidence") or 0.0) < triage_confidence_threshold():
        return False
    return not _has_explicit_store_stock_intent(user_text)


def detect_inventory_inquiry(
    user_text: str,
    triage_result: Optional[Dict] = None,
) -> Tuple[bool, Optional[Dict]]:
    """
    在庫確認の質問を検出。

    商品カタログ照合は在庫キーワード・位置質問・トリアージヒントがある場合のみ実行。
    """
    if _should_skip_inventory_for_medical_triage(user_text, triage_result):
        return False, None

    user_text_lower = user_text.lower()

    has_inventory_keyword = any(
        _matches_inventory_keyword(user_text, keyword)
        for keyword in INVENTORY_INQUIRY_KEYWORDS
    )
    has_location_question = "場所" in user_text_lower or "どこ" in user_text_lower
    triage_inventory_hint = _triage_hints_inventory(triage_result)

    need_product_scan = (
        has_inventory_keyword
        or has_location_question
        or triage_inventory_hint
    )

    product_category_info: Optional[Dict] = None
    if need_product_scan:
        product_category_info = classify_product_category(user_text)

    if not need_product_scan:
        return False, None

    # 「場所」または「どこ」キーワードの特別処理：商品名が検出された場合のみ在庫確認として扱う
    if has_location_question:
        if product_category_info:
            has_symptom_keyword = any(
                keyword in user_text_lower for keyword in SYMPTOM_KEYWORDS
            )
            if has_symptom_keyword:
                logger.info(
                    "🔍 在庫確認キーワード検出だが、症状キーワードも検出されたため医薬品推奨を優先"
                )
                return False, None
            logger.info(
                "🔍 在庫確認の質問を検出（商品名+場所/どこ）: %s",
                product_category_info,
            )
            return True, product_category_info
        return False, None

    if has_inventory_keyword:
        has_symptom_keyword = any(
            keyword in user_text_lower for keyword in SYMPTOM_KEYWORDS
        )
        if _has_explicit_store_stock_intent(user_text):
            if product_category_info:
                logger.info("🔍 店舗在庫確認（明示）: %s", product_category_info)
                return True, product_category_info
            logger.info("🔍 店舗在庫確認（明示・商品カテゴリ未特定）")
            return True, None

        if has_symptom_keyword:
            logger.info(
                "🔍 在庫確認キーワード検出だが、症状キーワードも検出されたため医薬品推奨を優先"
            )
            return False, None

        from src.services.medicine_discovery_routing import has_medicine_discovery_intent

        if has_medicine_discovery_intent(user_text):
            logger.info(
                "🔍 在庫確認キーワード検出だが、薬探索意図のため医薬品推奨を優先"
            )
            return False, None

        if product_category_info:
            logger.info("🔍 在庫確認の質問を検出: %s", product_category_info)
            return True, product_category_info

        logger.info("🔍 在庫確認の質問を検出（商品カテゴリ未特定）")
        return True, None

    if triage_inventory_hint and product_category_info:
        logger.info(
            "🔍 トリアージ在庫ヒント+商品検出: %s",
            product_category_info,
        )
        return True, product_category_info

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
        if _contains_store_keyword(user_text, name):
            facility_name = name
            break

    has_type = any(_contains_store_keyword(user_text, k) for k in FACILITY_TYPE_KEYWORDS)

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
    if not any(_contains_store_keyword(user_text, k) for k in keywords):
        return False
    if require_store_scope and not (
        has_store_scoped_location_context(user_text)
        or has_facilities_spatial_context(user_text)
    ):
        return False
    return True


def _detect_subtype_inquiry(subtype: str, user_text: str) -> bool:
    keywords_map = {
        "tax_free": TAX_FREE_KEYWORDS,
        "tourism": TOURISM_KEYWORDS,
        "business_hours": BUSINESS_HOURS_KEYWORDS,
        "payment": PAYMENT_KEYWORDS,
        "parking": PARKING_KEYWORDS,
        "services": SERVICES_KEYWORDS,
    }
    keywords = keywords_map.get(subtype) or []
    require_scope = _STORE_KW.subtype_require_store_scope.get(subtype, False)
    if not _store_subtype_keyword_hit(
        user_text, keywords, require_store_scope=require_scope
    ):
        return False
    if _STORE_KW.subtype_require_spatial_or_location.get(subtype):
        return (
            has_facilities_spatial_context(user_text)
            or has_facilities_location_question(user_text)
        )
    return True


def detect_tax_free_inquiry(user_text: str) -> bool:
    return _detect_subtype_inquiry("tax_free", user_text)


def detect_tourism_inquiry(user_text: str) -> bool:
    return _detect_subtype_inquiry("tourism", user_text)


def detect_business_hours_inquiry(user_text: str) -> bool:
    return _detect_subtype_inquiry("business_hours", user_text)


def detect_payment_inquiry(user_text: str) -> bool:
    return _detect_subtype_inquiry("payment", user_text)


def detect_parking_inquiry(user_text: str) -> bool:
    return _detect_subtype_inquiry("parking", user_text)


def detect_services_inquiry(user_text: str) -> bool:
    return _detect_subtype_inquiry("services", user_text)


def _resolve_detailed_store_response(
    user_text: str,
    inquiry_type: str,
    triage_result: Optional[Dict],
    *,
    confidence: float = 0.85,
    reasoning: str = "",
) -> Dict:
    """fast-path でも在庫・周辺施設・サブタイプの詳細分類を適用する。"""
    llm_stub = {
        "inquiry_type": inquiry_type,
        "confidence": confidence,
        "reasoning": reasoning,
    }
    detailed = process_detailed_classification(user_text, llm_stub, triage_result)
    if detailed:
        return detailed
    store_location = detect_store_location(user_text)
    response = generate_store_inquiry_response(user_text, inquiry_type, store_location)
    return {
        "is_store_inquiry": True,
        "inquiry_type": inquiry_type,
        "store_location": store_location,
        "product_category": None,
        "response": response,
        "confidence": confidence,
        "reasoning": reasoning,
    }


def process_detailed_classification(
    user_text: str,
    llm_result: Dict,
    triage_result: Optional[Dict]
) -> Optional[Dict]:
    """
    高確信度の場合の詳細分類処理
    """
    try:
        from src.services.counseling_triage import classify_medicine_procurement_route

        proc_route = classify_medicine_procurement_route(user_text)
        if proc_route:
            return _resolve_procurement_store_response(
                user_text,
                triage_result,
                confidence=float(llm_result.get("confidence") or 0.9),
                reasoning=llm_result.get("reasoning") or "医薬品購入先",
            )
    except ImportError:
        pass

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
    低確信時に第1段階（LLMトリアージ）を再実行する。

    llm_triage に委譲（FIRST_STAGE + 第二段階 Other 分類を含む完全トリアージ）。
    """
    try:
        from src.services.llm_triage import llm_triage

        retry_result = llm_triage(user_text, client, use_cache=False)
        logger.info(
            "🔍 第1段階再実行結果: %s, confidence: %.2f",
            retry_result.get("category"),
            retry_result.get("confidence", 0.0),
        )
        return retry_result

    except Exception as e:
        logger.error(f"❌ 第1段階再実行エラー: {e}")
        import traceback
        traceback.print_exc()
        return None


def handle_store_inquiry(
    user_text: str,
    client: OpenAI,
    triage_result: Optional[Dict] = None,
    *,
    extra_texts: Optional[List[str]] = None,
) -> Optional[Dict]:
    """
    店舗案内・遺失物関連の質問を処理（2段階判定を使用）
    
    Args:
        user_text: ユーザーの入力テキスト
        client: OpenAIクライアントインスタンス
        triage_result: LLMトリアージ結果（第1段階の結果）
        extra_texts: 原文など追加の照合用テキスト
    
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
    return handle_store_inquiry_with_two_stage(
        user_text,
        client,
        triage_result,
        extra_texts=extra_texts,
    )

