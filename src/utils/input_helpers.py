"""
入力判定ヘルパーモジュール

曖昧入力・操作コマンド・症状入力の判定、
不足属性のチェックを行う。
"""
import re
from typing import Any, Dict, List, Optional, Tuple


def resolve_llm_user_text(
    original_user_message: str = "",
    user_message: str = "",
    *fallbacks: str,
) -> str:
    """
    LLM プロンプトに渡すユーザー入力。正規化前の生データを優先する。

    ルーティング・キーワード照合・スコアリングには sanitized / processed を使うこと。
    """
    for candidate in (original_user_message, user_message, *fallbacks):
        text = (candidate or "").strip()
        if text:
            return text
    return ""


def is_ambiguous_input(user_text: str, symptoms: List[str], nlu_result: Dict) -> bool:
    """
    曖昧な入力かどうかを判定

    Args:
        user_text: ユーザー入力テキスト
        symptoms: 抽出された症状リスト（文字列のリスト）
        nlu_result: NLU解析結果

    Returns:
        bool: 曖昧な入力の場合True
    """
    symptom_count = len(symptoms) if symptoms else 0
    if symptom_count < 3:
        return False

    text_length = len(user_text.strip())
    if text_length > 30:
        return False

    confidence_score = nlu_result.get('confidence_score', 1.0)
    user_text_lower = user_text.lower()
    explicit_symptoms = []
    symptom_keywords = {
        "発熱": ["発熱", "熱", "高熱", "微熱", "熱がある"],
        "頭痛": ["頭痛", "頭が痛い"],
        "咳": ["咳", "せき"],
        "鼻水": ["鼻水", "鼻みず"],
        "のどの痛み": ["のど", "喉", "のどの痛み", "喉が痛い"],
        "くしゃみ": ["くしゃみ"],
        "寒気": ["寒気", "悪寒"]
    }

    for symptom_name, keywords in symptom_keywords.items():
        if any(keyword in user_text_lower for keyword in keywords):
            explicit_symptoms.append(symptom_name)

    if len(explicit_symptoms) >= 2:
        return False

    if confidence_score < 0.5:
        return True

    return True


def check_missing_attributes(user_attributes: Dict) -> Tuple[List[str], str]:
    """不足している属性情報をチェックし、追加質問を生成"""
    missing_questions = []
    missing_priority = 'optional'

    if not user_attributes.get('age'):
        missing_questions.append('年齢を教えてください。（医薬品の適切な選択に必要です）')
        missing_priority = 'critical'

    if not user_attributes.get('gender'):
        missing_questions.append('性別を教えてください。（男性/女性）')
        missing_priority = 'critical'

    if user_attributes.get('gender') == 'female' and user_attributes.get('pregnant') is None:
        missing_questions.append('現在、妊娠中または授乳中ですか？（はい/いいえ）')
        if missing_priority == 'optional':
            missing_priority = 'important'

    if not user_attributes.get('symptom_duration_days'):
        missing_questions.append('症状はいつ頃から続いていますか？（例：昨日から、3日前から）')
        if missing_priority == 'optional':
            missing_priority = 'important'

    symptom_duration = user_attributes.get('symptom_duration_days')
    if symptom_duration and symptom_duration > 7:
        missing_questions.append(
            '⚠️ 症状が7日を超えている場合は、市販薬での対応が困難な可能性があります。'
            '医療機関（病院・クリニック）での受診をお勧めします。'
        )
        missing_priority = 'critical'

    if not user_attributes.get('allergies'):
        missing_questions.append('アレルギーはありますか？（薬物アレルギー、食物アレルギーなど）')

    if not user_attributes.get('current_medications'):
        missing_questions.append('現在服用中の薬はありますか？')

    if not user_attributes.get('medical_history'):
        missing_questions.append('持病や既往歴はありますか？')

    return missing_questions, missing_priority


def is_operation_command(user_message: str) -> bool:
    """
    操作指示を検出（誤検出を防ぐための厳密な検出ロジック）

    セキュリティ対策:
    - 操作指示キーワードが文脈的に操作指示として使われているかを確認
    - 命令形（「更新して」「更新してください」など）を含む場合のみ検出
    - 症状記述（例: 「症状が更新されました」）は誤検出しない
    """
    operation_patterns = [
        r'情報を(足しました|追加しました).*更新',
        r'更新して(ください|くれ)',
        r'再読み込み(してください|してくれ)',
        r'リロード(してください|してくれ)',
        r'reload',
        r'refresh',
        r'更新(してください|してくれ|しろ|せよ)',
        r'情報を更新',
        r'ページを更新',
        r'画面を更新'
    ]

    symptom_patterns = [
        r'症状が更新',
        r'状態が更新',
        r'体調が更新',
        r'痛みが更新'
    ]

    for pattern in symptom_patterns:
        if re.search(pattern, user_message):
            return False

    for pattern in operation_patterns:
        if re.search(pattern, user_message, re.IGNORECASE):
            return True

    return False


def is_symptom_input(message: str) -> bool:
    """メッセージが症状入力かどうかを判定"""
    if not message:
        return False

    from src.services.store_inquiry_handler import _is_toilet_facility_request

    if _is_toilet_facility_request(message):
        return False

    text = message.strip()
    lower_text = text.lower()

    symptom_keywords = [
        '痛い', '痛み', '熱', '発熱', '咳', '鼻水', '頭痛', '腹痛', '吐き気', '嘔吐', '下痢', '便秘',
        '痒い', 'かゆい', '腫れ', '炎症', '発疹', '湿疹', 'めまい', 'だるい', '倦怠感', '疲れ', '不調', '症状',
        '喉', 'のど', '胃', '腸', '目', '耳', '鼻', '皮膚', '関節', '筋肉', '肩こり', '腰痛', '風邪', 'インフルエンザ',
        '寒気', '寒気がする', '寒気がします', '寒気があります', '寒気があり', '寒気が',
        '痺れ', 'しびれ', 'むくみ', '倦怠', '倦怠感', 'だるさ'
    ]

    question_keywords = [
        'ですか', 'でしょうか', 'ですか？', 'でしょうか？', 'どう', '何', 'なぜ', 'いつ',
        '副作用', '飲み方', '注意', '効果', '効き目', '時間', '回数', '量', '併用',
        'ドーピング', '禁止', '違反', '大丈夫', '安全', '危険', '問題', '影響',
        '一緒に', '同時に', '飲んで', '使って', '服用', '投与', '飲み合わせ',
        'スポーツ', '競技', '運動', 'トレーニング', '試合', '大会', '検査', '陽性',
        '成分', '効能', '作用', 'メカニズム', '仕組み',
        '飲む', '使う', '摂取', '飲むタイミング', '飲む時間',
        '食前', '食後', '食間', '空腹時', '満腹時', '就寝前', '起床時',
        '他の薬', '併用', '同時', '一緒', '組み合わせ',
        '注意点', '気をつける', '避ける', '控える', '中止', '停止',
        '当たる', '当たります', '対象', '対象外', '含まれる', '含まれない',
        '使える', '使えない', '可能', '不可能', '適切', '不適切',
        '効く', '効かない', '効果的', '効果的でない',
        '副作用が出る', '副作用がある', '副作用がない',
        '安全性', '危険性', 'リスク',
        '教えて', '教えてください', '知りたい', '聞きたい'
    ]

    attribute_keywords = [
        '歳です', '歳、', '男性です', '女性です', '男です', '女です',
        'いいえ', 'はい', 'ありません', 'ないです', 'なしです',
        '妊娠', '授乳', 'アレルギー',
        '昨日から', '今日から', 'きのうから', 'きょうから', '日前から', '週間前から',
        '服用している', '飲んでいる', '続いています',
        'years old', 'male', 'female', 'man', 'woman', 'allergy', 'allergies',
        'pregnant', 'breastfeeding', 'taking', 'medication', 'medicine',
        'started', 'days ago', 'weeks ago', 'months ago', 'yesterday', 'today'
    ]

    has_symptom_keyword = any(keyword in text for keyword in symptom_keywords)
    has_question_keyword = any(keyword in text for keyword in question_keywords)
    has_attribute_keyword = any(keyword in text for keyword in attribute_keywords)
    ends_with_question_mark = text.endswith('？') or text.endswith('?') or lower_text.endswith('?')

    attribute_count = sum(1 for keyword in attribute_keywords if keyword in text)
    symptom_count = sum(1 for keyword in symptom_keywords if keyword in text)

    # 「症状＋おすすめ/どれが良い」等はレコメンド（症状入力）に寄せる。
    # 一方で「副作用/飲み方/併用/ドーピング」等の “情報質問” はQ&Aに寄せたいので、
    # 症状語が含まれていても無条件に症状入力にはしない。
    recommendation_intent_keywords = [
        'おすすめ', 'お勧め', 'オススメ',
        'どの薬', 'どれ', '何がいい', 'なにがいい', '何を飲めば', 'なにを飲めば',
        '何飲めば', 'なに飲めば', 'どれ飲めば', 'どれを飲めば',
        '薬ありますか', '薬ある', '市販薬', '薬ください', '薬ちょうだい'
    ]
    informational_intent_keywords = [
        '副作用', '飲み方', '用法', '用量', '併用', '飲み合わせ', '相互作用',
        'ドーピング', '禁止', '陽性', '成分', '効能', '効果', '注意', '危険', '安全'
    ]
    has_recommendation_intent = any(k in text for k in recommendation_intent_keywords)
    has_informational_intent = any(k in text for k in informational_intent_keywords)

    if attribute_count >= 3 and attribute_count > symptom_count:
        return False

    # 症状を「質問形」で入力するユーザーが多いため、
    # 症状キーワードが含まれている場合は、文末の「？」や質問語尾だけで
    # 症状入力判定を False にしない（例:「頭痛いのでおすすめの薬ありますか？」）。
    if has_question_keyword or ends_with_question_mark:
        if has_symptom_keyword and not (attribute_count >= 3 and attribute_count > symptom_count):
            # 情報質問はQ&Aへ（例:「頭痛薬の副作用は？」）
            if has_informational_intent and not has_recommendation_intent:
                return False
            # レコメンド意図がある質問形は症状入力へ（例:「頭痛いのでおすすめの薬ありますか？」）
            if has_recommendation_intent:
                return True
            # どちらとも言えない場合は質問として扱う（誤って症状フローに寄せない）
            return False
        return False

    if has_symptom_keyword:
        return True

    if has_attribute_keyword:
        return False

    return True


def has_explicit_symptom_signal(message: str) -> bool:
    """
    general_other 高確信時の Physical 上書き用。
    is_symptom_input の最終 True フォールバック（曖昧入力）だけでは True にしない。
    """
    text = (message or "").strip()
    if not text:
        return False

    from src.services.concierge_intent import classify_concierge_intent

    if classify_concierge_intent(text) in ("greeting", "thanks"):
        return False

    normalized = normalize_latin_width(text)
    if is_known_short_symptom(text) or is_known_short_symptom(normalized):
        return True

    if not is_symptom_input(text):
        return False

    symptom_keywords = [
        '痛い', '痛み', '熱', '発熱', '咳', '鼻水', '頭痛', '腹痛', '吐き気', '嘔吐', '下痢', '便秘',
        '痒い', 'かゆい', '腫れ', '炎症', '発疹', '湿疹', 'めまい', 'だるい', '倦怠感', '疲れ', '不調', '症状',
        '喉', 'のど', '胃', '腸', '目', '耳', '鼻', '皮膚', '関節', '筋肉', '肩こり', '腰痛', '風邪', 'インフルエンザ',
        '寒気', '寒気がする', '寒気がします', '寒気があります', '寒気があり', '寒気が',
        '痺れ', 'しびれ', 'むくみ', '倦怠', '倦怠感', 'だるさ',
    ]
    recommendation_intent_keywords = [
        'おすすめ', 'お勧め', 'オススメ',
        'どの薬', 'どれ', '何がいい', 'なにがいい', '何を飲めば', 'なにを飲めば',
        '何飲めば', 'なに飲めば', 'どれ飲めば', 'どれを飲めば',
        '薬ありますか', '薬ある', '市販薬', '薬ください', '薬ちょうだい',
    ]

    has_symptom_keyword = any(keyword in text for keyword in symptom_keywords)
    if has_symptom_keyword:
        return True
    if any(k in text for k in recommendation_intent_keywords):
        return True
    return False


_FULLWIDTH_LATIN = (
    "０１２３４５６７８９"
    "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ"
    "ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ"
)
_HALFWIDTH_LATIN = (
    "0123456789"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
)
_LATIN_WIDTH_MAP = str.maketrans(_FULLWIDTH_LATIN, _HALFWIDTH_LATIN)


def normalize_latin_width(text: str) -> str:
    """全角英数字を半角に統一する。"""
    return (text or "").translate(_LATIN_WIDTH_MAP)


def is_known_short_symptom(text: str) -> bool:
    """症状辞書の canonical / synonyms と完全一致する短い入力か。"""
    stripped = (text or "").strip()
    if not stripped:
        return False
    from src.core.dictionary_loader import load_symptom_dictionary

    symptom_dict = load_symptom_dictionary()
    for canonical_name, entry in symptom_dict.items():
        if stripped == canonical_name:
            return True
        for syn in entry.get("synonyms", []):
            if stripped == syn:
                return True
    return False


def is_unrecognizable_symptom_input(message: str) -> bool:
    """
    症状相談として解釈できない短い・意味不明な入力か。

    単一文字（g / ｇ 等）や症状辞書に無い 3 文字未満の入力を検出する。
    挨拶・感謝など Concierge 向け社交入力は対象外。
    """
    stripped = (message or "").strip()
    if not stripped:
        return False

    from src.services.concierge_intent import classify_concierge_intent

    if classify_concierge_intent(stripped) in ("greeting", "thanks"):
        return False

    normalized = normalize_latin_width(stripped)
    if is_known_short_symptom(stripped) or is_known_short_symptom(normalized):
        return False

    if len(normalized) < 3:
        return True

    if len(normalized) <= 2 and re.match(r"^[a-zA-Z0-9]+$", normalized):
        return True

    return False


def should_apply_unrecognized_symptom_gate(
    triage_result: Optional[Dict[str, Any]],
    message: str = "",
) -> bool:
    """
    「症状から医薬品を選べませんでした」カードを出すべきか。

    トリアージ LLM が Other/general_other と高確信で返した入力は、
    短い文字列ヒューリスティクスより優先して Concierge 等へ流す。
    """
    triage = triage_result or {}
    category = triage.get("category", "")
    subcategory = str(triage.get("subcategory") or "")
    confidence = float(triage.get("confidence") or 0.0)

    if category == "Other" and "general_other" in subcategory and confidence >= 0.7:
        if has_explicit_symptom_signal(message):
            return True
        return False

    if category == "Other" and (
        subcategory.startswith("store_inquiry")
        or subcategory == "lost_and_found"
        or subcategory.startswith("inappropriate_request")
    ):
        return False

    if category in ("Emotional", "Emergency"):
        return False

    if category in ("Physical", "Ask"):
        return is_unrecognizable_symptom_input(message)

    if category == "Other":
        return is_unrecognizable_symptom_input(message)

    return False


def should_prioritize_medical_route_over_store(
    triage_result: Optional[Dict[str, Any]],
    message: str = "",
) -> bool:
    """
    Physical/Ask トリアージが十分な確信度のとき、
    キーワード型の店舗ゲートより医療経路を優先する。

    トイレ・遺失物など明確な店舗意図は store 側を維持する。
    """
    triage = triage_result or {}
    category = triage.get("category", "")
    if category not in ("Physical", "Ask"):
        return False

    subcategory = str(triage.get("subcategory") or "").lower()
    if subcategory.startswith("store_inquiry") or subcategory == "lost_and_found":
        return False

    from config.routing_config import triage_confidence_threshold

    confidence = float(triage.get("confidence") or 0.0)
    if confidence < triage_confidence_threshold():
        return False

    from src.services.store_inquiry_handler import has_unambiguous_store_intent

    if has_unambiguous_store_intent(message):
        return False

    text = (message or "").lower()
    explicit_store_stock = (
        "在庫",
        "取り寄せ",
        "売り場",
        "売ってい",
        "扱ってい",
        "置いてあり",
        "店内",
        "店舗",
    )
    if any(k in text for k in explicit_store_stock):
        return False

    return True


def reroute_symptom_general_other_to_physical(
    triage_result: Optional[Dict[str, Any]],
    message: str,
) -> tuple[str, Dict[str, Any]]:
    """
    general_other 高確信でも症状入力なら Physical へ上書き（Concierge のみ回避）。
    """
    triage = dict(triage_result or {})
    category = triage.get("category", "Other")
    subcategory = str(triage.get("subcategory") or "")
    confidence = float(triage.get("confidence") or 0.0)
    if (
        category == "Other"
        and "general_other" in subcategory
        and confidence >= 0.7
        and has_explicit_symptom_signal(message)
    ):
        triage["category"] = "Physical"
        triage["_symptom_general_other_override"] = True
        return "Physical", triage
    return category, triage


def should_fallback_to_symptom_recommendation(
    triage_result: Optional[Dict[str, Any]],
    message: str = "",
) -> bool:
    """オーケストレーター未解決時に Physical 推奨フローへ落とすか。"""
    triage = triage_result or {}
    category = triage.get("category", "")
    subcategory = str(triage.get("subcategory") or "")

    if category in ("Physical", "Ask"):
        return True
    if category == "Emotional":
        return False
    if category == "Other" and "general_other" in subcategory:
        if message and has_explicit_symptom_signal(message):
            return True
        return False
    if category == "Other" and (
        subcategory.startswith("store_inquiry")
        or subcategory == "lost_and_found"
        or subcategory.startswith("inappropriate_request")
    ):
        return False
    if category == "Emergency":
        return False
    return category not in ("Other",)
