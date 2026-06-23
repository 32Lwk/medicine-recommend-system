"""
相談トリアージ判定モジュール

counseling_response から分離（SRP改善）。
不適切要求検出、感情的症状タイプ判定、重篤疾患判定などのトリアージロジックを担当。
"""

import logging
import re
from typing import Dict, Optional

# キーワードリストのインポート
try:
    from config.keywords import (
        SEVERE_DISEASE_KEYWORDS,
        SYMPTOM_KEYWORDS,
        TREATMENT_KEYWORDS,
        MEDICAL_PREVENTION_KEYWORDS
    )
except ImportError:
    SEVERE_DISEASE_KEYWORDS = {}
    SYMPTOM_KEYWORDS = []
    TREATMENT_KEYWORDS = []
    MEDICAL_PREVENTION_KEYWORDS = []
    logging.warning("config/keywords.pyが見つかりません。キーワードリストを使用できません。")

try:
    from src.core.scoring_utils import normalize_text
except ImportError:
    def normalize_text(text: str) -> str:
        if not text or not isinstance(text, str):
            return ""
        return text.lower().strip()

logger = logging.getLogger(__name__)


def is_treatment_mention(user_text: str, skip_diagnosis_only: bool = False) -> bool:
    """
    「治療中」を示すキーワードが含まれているかを判定

    Args:
        user_text: ユーザーの入力テキスト
        skip_diagnosis_only: Trueの場合、診断名のみ（疾患名+「です」のパターン）を「治療中」として判定しない

    Returns:
        True: 「治療中」キーワードが含まれている場合
    """
    user_text_normalized = normalize_text(user_text)

    for keyword in TREATMENT_KEYWORDS:
        keyword_normalized = normalize_text(keyword)
        if keyword_normalized in user_text_normalized:
            logger.debug(f"「治療中」キーワード検出: {keyword}")
            return True

    if not skip_diagnosis_only:
        for category, keywords in SEVERE_DISEASE_KEYWORDS.items():
            for disease in keywords:
                pattern = rf"{re.escape(disease)}(です|です、|です。)"
                if re.search(pattern, user_text):
                    logger.debug(f"「治療中」キーワード検出（疾患名+です）: {disease}")
                    return True

    if "血圧が高い" in user_text or "血圧が高いです" in user_text:
        logger.debug("「治療中」キーワード検出: 血圧が高い")
        return True

    return False


def has_specific_symptom(user_text: str) -> bool:
    """
    具体的な症状が述べられているかを判定

    Args:
        user_text: ユーザーの入力テキスト

    Returns:
        True: 症状キーワードが含まれている場合
    """
    user_text_normalized = normalize_text(user_text)

    for keyword in SYMPTOM_KEYWORDS:
        keyword_normalized = normalize_text(keyword)
        if keyword_normalized in user_text_normalized:
            logger.debug(f"症状キーワード検出: {keyword}")
            return True

    return False


def is_severe_disease_request(user_text: str, triage_result: Optional[Dict] = None) -> bool:
    """
    重篤な疾患の要求かどうかを判定（キーワードベース優先）

    Args:
        user_text: ユーザーの入力テキスト
        triage_result: トリアージ結果（オプション、LLM判定が必要な場合に使用）

    Returns:
        True: 重篤な疾患の要求と判定された場合
    """
    if is_treatment_mention(user_text):
        return False

    if has_specific_symptom(user_text):
        return False

    user_text_normalized = normalize_text(user_text)

    for category, keywords in SEVERE_DISEASE_KEYWORDS.items():
        for keyword in keywords:
            keyword_normalized = normalize_text(keyword)
            if keyword_normalized in user_text_normalized:
                if "心臓" in keyword or "心" in keyword:
                    if has_specific_symptom(user_text):
                        return False
                    if triage_result:
                        subcategory = triage_result.get("subcategory", "").lower()
                        if "heart" in subcategory or "心臓" in subcategory:
                            cat = triage_result.get("category", "")
                            if cat == "Physical" or cat == "Emergency":
                                return False
                logger.debug(f"重篤疾患キーワード検出: {keyword} (カテゴリ: {category})")
                return True

    return False


def is_medical_prevention_request(user_text: str) -> bool:
    """
    「医薬的な予防」の要求かどうかを判定

    Args:
        user_text: ユーザーの入力テキスト

    Returns:
        True: 「医薬的な予防」キーワードが含まれている場合
    """
    user_text_normalized = normalize_text(user_text)

    for keyword in MEDICAL_PREVENTION_KEYWORDS:
        keyword_normalized = normalize_text(keyword)
        if keyword_normalized in user_text_normalized:
            logger.debug(f"「医薬的な予防」キーワード検出: {keyword}")
            return True

    if "風邪" in user_text_normalized and "予防" in user_text_normalized:
        is_severe = False
        for category_keywords in SEVERE_DISEASE_KEYWORDS.values():
            for severe_keyword in category_keywords:
                if normalize_text(severe_keyword) in user_text_normalized:
                    is_severe = True
                    break
            if is_severe:
                break

        if not is_severe:
            logger.debug(f"「医薬的な予防」キーワード検出（柔軟マッチング）: 風邪 + 予防")
            return True

    return False


def is_psychiatric_disease_request(user_text: str, triage_result: Optional[Dict] = None) -> bool:
    """
    精神疾患関連の要求かどうかを判定

    Args:
        user_text: ユーザーの入力テキスト
        triage_result: トリアージ結果（オプション）

    Returns:
        True: 精神疾患関連の要求と判定された場合
    """
    user_text_normalized = normalize_text(user_text)

    if "neurological_psychiatric" in SEVERE_DISEASE_KEYWORDS:
        for keyword in SEVERE_DISEASE_KEYWORDS["neurological_psychiatric"]:
            keyword_normalized = normalize_text(keyword)
            if keyword_normalized in user_text_normalized:
                logger.debug(f"精神疾患キーワード検出: {keyword}")
                return True

    return False


def detect_inappropriate_request(user_text: str, triage_result: Dict) -> Optional[str]:
    """
    不適切な要求の種類を判定

    Args:
        user_text: ユーザーの入力テキスト
        triage_result: トリアージ結果

    Returns:
        要求の種類（"prescription", "medical_examination", "weight_loss", ...
    """
    from src.services.medical_examination_request import (
        resolve_medical_examination_request_type,
    )

    medical_act = resolve_medical_examination_request_type(user_text, triage_result)
    if medical_act:
        return medical_act

    subcategory = triage_result.get("subcategory", "").lower()

    if "inappropriate_request" not in subcategory:
        return None

    if "/medical_examination" in subcategory:
        return "medical_examination"
    if "/prescription" in subcategory:
        return "prescription"
    elif "/weight_loss" in subcategory:
        return "weight_loss"
    elif "/love_potion" in subcategory:
        return "love_potion"
    elif "/cure_prevention" in subcategory:
        if is_treatment_mention(user_text):
            logger.debug("「治療中」キーワードにより、通常フローに進む")
            return None

        if has_specific_symptom(user_text):
            logger.debug("症状キーワードにより、通常フローに進む")
            return None

        if not is_severe_disease_request(user_text, triage_result):
            logger.debug("重篤疾患キーワードがないため、通常フローに進む")
            return None

        if is_psychiatric_disease_request(user_text, triage_result):
            logger.debug("精神疾患関連の完治要求を検出")
            return "psychiatric_cure_prevention"

        if is_medical_prevention_request(user_text):
            logger.debug("「医薬的な予防」キーワードにより、カウンセリングフローに進む")
            return None

        logger.debug("重篤疾患の完治・予防要求を検出")
        return "cure_prevention"
    elif "/anti_aging" in subcategory:
        return "anti_aging"
    elif "/body_shape" in subcategory:
        return "body_shape"
    elif "/hair_growth" in subcategory:
        return "hair_growth"
    elif "/illegal" in subcategory:
        return "illegal"
    elif "/controlled" in subcategory:
        return "controlled"

    return None


def detect_emotional_symptom_type(user_text: str, triage_result: Dict) -> str:
    """
    感情的症状のタイプを判定

    Args:
        user_text: ユーザーの入力テキスト
        triage_result: トリアージ結果

    Returns:
        感情的症状タイプ（"heart_pain", "anxiety", "romantic_concern", "stress", "depression_like", "insomnia"）
    """
    subcategory = triage_result.get("subcategory", "").lower()
    user_text_lower = user_text.lower()

    sleepiness_keywords = [
        "寝てしまう", "眠くて寝てしまう", "眠すぎて寝てしまう",
        "仕事中に寝てしまう", "居眠り", "眠くてたまらない",
        "眠気に襲われる", "眠くて仕方がない", "眠すぎる",
        "眠気が強い", "眠い", "眠たい", "眠気", "だるい", "いつも眠い",
        "眠くて", "眠すぎ", "眠気で", "眠気です", "眠気が", "眠気の",
        "日中の眠気", "昼間の眠気", "眠くて困る", "眠くて仕方ない",
        "眠気が取れない", "眠気が強い", "強い眠気", "眠気がひどい"
    ]
    if any(keyword in user_text_lower for keyword in sleepiness_keywords):
        return "drowsiness"

    insomnia_keywords = [
        "不眠", "眠れない", "睡眠不足", "寝つきが悪い", "眠れません", "眠れないです",
        "眠れない", "夜眠れない", "最近眠れない", "最近眠れません", "夜眠れません",
        "寝れない", "寝れません", "寝れないです", "夜寝れない", "最近寝れない",
        "眠れなくて", "眠れなく", "寝つけない", "寝つけません", "寝つけないです",
        "不眠症", "不眠で", "不眠です", "不眠の", "不眠が",
        "睡眠薬", "睡眠薬を", "睡眠薬について", "睡眠薬を教えて", "睡眠薬を知りたい",
        "睡眠改善薬", "睡眠改善薬を", "睡眠改善薬について", "睡眠改善薬を教えて"
    ]
    if "insomnia" in subcategory or any(keyword in user_text_lower for keyword in insomnia_keywords):
        return "insomnia"

    if "heart" in subcategory or "心" in user_text:
        return "heart_pain"
    elif "anxiety" in subcategory or "緊張" in user_text or "不安" in user_text:
        return "anxiety"
    elif "romantic" in subcategory or "恋" in user_text:
        return "romantic_concern"
    elif "stress" in subcategory or "ストレス" in user_text:
        return "stress"
    else:
        return "general_emotional"


def detect_app_specification_question(user_text: str) -> bool:
    """
    アプリケーションの技術仕様や対応内容に関する質問を検出

    Args:
        user_text: ユーザーの入力テキスト

    Returns:
        アプリケーションの技術仕様に関する質問かどうか
    """
    app_spec_keywords = [
        "あなたについて", "あなたは", "あなたの", "システムについて", "アプリについて",
        "機能について", "対応", "できること", "何ができる", "技術", "仕様", "仕組み",
        "アルゴリズム", "開発", "使用", "利用", "使い方", "特徴", "強み", "データベース",
        "API", "フレームワーク", "言語", "環境", "デプロイ", "監視", "ログ", "セッション",
        "多言語", "翻訳", "対応言語", "対応内容", "できること", "できないこと"
    ]

    user_text_lower = user_text.lower()
    return any(keyword in user_text_lower for keyword in app_spec_keywords)
