"""
NLU（自然言語理解）サービス

症状抽出、キャッシュ管理を担当（rule_based_recommendation から分離・SRP改善）
"""

import logging
import os
import re
from typing import Dict, Optional

from openai import OpenAI

from src.core.dictionary_loader import load_symptom_dictionary
from src.core.recommendation_constants import (
    RED_FLAG_SYMPTOMS,
    FEMALE_SPECIFIC_SYMPTOMS,
    PREGNANCY_SYMPTOMS,
)

logger = logging.getLogger(__name__)
_DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

# NLUキャッシュ（セッション間でも共有可能なキャッシュ）
_nlu_cache: Dict = {}
_max_cache_size = 100

# 医薬品タイプ判定キャッシュ
_medicine_type_cache: Dict = {}
_max_medicine_type_cache_size = 50

# 翻訳キャッシュ
_translation_cache: Dict = {}
_max_translation_cache_size = 200

# 症状パターンマッチングキャッシュ
_symptom_pattern_cache: Dict = {}
_max_symptom_pattern_cache_size = 200

# 成分抽出キャッシュ
_ingredient_extraction_cache: Dict = {}
_max_ingredient_extraction_cache_size = 500


def get_cached_nlu_result(user_text: str, session_id: str = None) -> Optional[Dict]:
    """
    NLUキャッシュから結果を取得（セッション間でも共有可能）
    """
    text_hash = hash(user_text)
    if session_id:
        cache_key = f"{session_id}:{text_hash}"
        if cache_key in _nlu_cache:
            return _nlu_cache[cache_key]
    for key, value in _nlu_cache.items():
        if key.endswith(f":{text_hash}"):
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"NLUキャッシュヒット（セッション間共有）: {key}")
            return value
    return None


def set_cached_nlu_result(user_text: str, nlu_result: Dict, session_id: str = None):
    """NLUキャッシュに結果を保存"""
    text_hash = hash(user_text)
    if len(_nlu_cache) >= _max_cache_size:
        oldest_key = next(iter(_nlu_cache))
        del _nlu_cache[oldest_key]
    cache_key = f"{session_id}:{text_hash}" if session_id else f"shared:{text_hash}"
    _nlu_cache[cache_key] = nlu_result
    if _DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"NLUキャッシュに保存: {cache_key}")


def clear_nlu_cache():
    """NLUキャッシュをクリア"""
    global _nlu_cache
    _nlu_cache.clear()
    logger.info("NLUキャッシュをクリアしました")


def get_cached_medicine_type(user_text: str) -> Optional[str]:
    """医薬品タイプ判定キャッシュから結果を取得"""
    text_hash = hash(user_text)
    return _medicine_type_cache.get(text_hash)


def set_cached_medicine_type(user_text: str, medicine_type: str):
    """医薬品タイプ判定キャッシュに結果を保存"""
    global _medicine_type_cache
    if len(_medicine_type_cache) >= _max_medicine_type_cache_size:
        oldest_key = next(iter(_medicine_type_cache))
        del _medicine_type_cache[oldest_key]
    text_hash = hash(user_text)
    _medicine_type_cache[text_hash] = medicine_type
    if _DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"医薬品タイプキャッシュに保存: {medicine_type}")


def get_cached_translation(text: str, target_language: str) -> Optional[str]:
    """翻訳キャッシュから結果を取得"""
    cache_key = f"{target_language}:{hash(text)}"
    return _translation_cache.get(cache_key)


def set_cached_translation(text: str, target_language: str, translated_text: str):
    """翻訳キャッシュに結果を保存"""
    global _translation_cache
    if len(_translation_cache) >= _max_translation_cache_size:
        oldest_key = next(iter(_translation_cache))
        del _translation_cache[oldest_key]
    cache_key = f"{target_language}:{hash(text)}"
    _translation_cache[cache_key] = translated_text
    if _DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"翻訳キャッシュに保存: {cache_key[:50]}...")


def _extract_body_part_from_user_text(user_text: str, symptom_name: str) -> Optional[str]:
    """
    ユーザー入力テキストから部位情報を抽出（拡張版）

    Args:
        user_text: ユーザーの入力テキスト
        symptom_name: 検出された症状名

    Returns:
        部位名（"scalp", "throat", "arm", "leg", "hand", "eye", "nose", "chest", "stomach", "back", "delicate_area"など）、またはNone
    """
    if not user_text:
        return None

    user_text_lower = user_text.lower()

    # 優先度の高い特殊部位（症状名との組み合わせを考慮）
    # 頭皮関連のキーワード
    scalp_keywords = ["頭", "頭皮", "頭部", "フケ", "頭頂部", "後頭部"]
    if any(kw in user_text_lower for kw in scalp_keywords):
        if symptom_name in ["かゆみ", "発疹", "湿疹"] or "かゆ" in user_text_lower or "フケ" in user_text_lower:
            return "scalp"

    # デリケート部位関連のキーワード（多言語対応）
    delicate_keywords_jp = ["デリケート", "おりもの", "ナプキン", "蒸れ", "おむつ", "陰部", "股間",
                            "ペニス", "性器", "生殖器", "局部", "私部", "陰茎", "陰嚢", "亀頭"]
    delicate_keywords_zh = ["陰莖", "陰茎", "生殖器", "性器", "私處", "私处", "私部", "局部",
                            "陰部", "股間", "股间", "陰囊", "陰囊", "龜頭", "龟头", "阴茎"]
    delicate_keywords_en = ["penis", "genital", "private area", "genitalia", "genitals",
                           "private parts", "intimate area", "groin", "pubic", "scrotum",
                           "glans", "foreskin"]

    delicate_keywords = delicate_keywords_jp + delicate_keywords_zh + delicate_keywords_en
    normalized_text = user_text_lower.replace(" ", "").replace("\t", "").replace("\n", "")

    for kw in delicate_keywords:
        kw_lower = kw.lower()
        if kw_lower in user_text_lower or kw_lower in normalized_text:
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"デリケート部位を検出: キーワード='{kw}', 入力テキスト='{user_text[:50]}...'")
            return "delicate_area"

    # のど関連のキーワード
    throat_keywords = ["のど", "喉", "咽頭", "喉頭", "声帯"]
    if any(kw in user_text_lower for kw in throat_keywords):
        if symptom_name in ["のどの痛み", "かゆみ", "咳"] or "痛" in user_text_lower or "かゆ" in user_text_lower:
            return "throat"

    general_body_parts = {
        'arm': ['腕', 'うで', '上腕', '前腕', '二の腕', 'ひじ', '肘'],
        'leg': ['足', '脚', 'あし', '下肢', '太もも', 'ふともも', 'もも', 'すね', '脛', 'ふくらはぎ', '膝', 'ひざ'],
        'hand': ['手', 'て', '手首', '手のひら', '手の甲', '指', '親指', '人差し指', '中指', '薬指', '小指'],
        'foot': ['足首', 'くるぶし', '足の裏', '足の甲', 'つま先', 'かかと'],
        'eye': ['目', '眼', 'まぶた', '眼球', '白目', '黒目', '瞳', '目頭', '目尻'],
        'nose': ['鼻', 'はな', '鼻腔', '鼻の穴', '鼻先', '鼻筋'],
        'ear': ['耳', 'みみ', '耳たぶ', '耳の穴', '耳の奥'],
        'mouth': ['口', 'くち', '口腔', '唇', 'くちびる', '歯茎', '歯', '舌', 'した'],
        'chest': ['胸', '胸部', '乳房', 'おっぱい', '乳首'],
        'stomach': ['お腹', '腹部', '胃', 'みぞおち', 'へそ', 'おへそ', '下腹部', 'わき腹', '脇腹'],
        'back': ['背中', '腰', '腰部', '腰椎', '背骨', '脊椎'],
        'shoulder': ['肩', 'かた', '肩甲骨', '肩こり'],
        'neck': ['首', 'くび', '首筋', 'うなじ'],
        'face': ['顔', 'かお', '頬', 'ほほ', 'ほっぺ', 'あご', '顎', '額', 'ひたい', 'こめかみ'],
        'skin': ['皮膚', '肌', 'はだ', '表皮']
    }

    for part_name, keywords in general_body_parts.items():
        if any(kw in user_text_lower for kw in keywords):
            return part_name

    return None


def simple_pattern_matching_nlu(user_text: str, user_info: Dict) -> Dict:
    """
    強化されたルールベースNLU（正規表現、重症度推定、期間抽出）
    """
    text_lower = user_text.lower()
    detected_symptoms = []
    red_flags = []

    severity_patterns = {
        "重度": [
            r"激しい", r"ひどい", r"重い", r"酷い", r"深刻", r"重症", r"強烈", r"猛烈",
            r"耐えられない", r"我慢できない", r"今までにない", r"異常に", r"非常に",
            r"緊急", r"救急", r"命に関わる", r"危険", r"危篤", r"重症化"
        ],
        "軽度": [
            r"少し", r"軽い", r"軽微", r"微か", r"弱い", r"軽度", r"軽い",
            r"ちょっと", r"やや", r"わずか", r"軽く", r"微か", r"軽微",
            r"始まったばかり", r"初期", r"初期の", r"初期段階", r"初期症状",
            r"軽く", r"軽め", r"軽症", r"軽い症状", r"軽い痛み", r"軽い熱"
        ],
        "中等度": [
            r"中程度", r"普通", r"まあまあ", r"そこそこ", r"それなりに",
            r"そこそこ", r"普通程度", r"一般的", r"標準的"
        ]
    }

    duration_patterns = [
        r'(\d+)\s*(日|日間|日前)',
        r'(昨日|今日|一昨日|おととい)',
        r'(先週|今週|先月|今月)',
        r'(数日|数日前|数週間|数ヶ月|長期間|慢性的)',
        r'(今朝|昨夜|今晩|今午後)',
        r'(先ほど|さっき|つい先ほど)',
        r'(ずっと|継続的に|持続的に)'
    ]

    SYMPTOM_COMBINATIONS = {
        '風邪': {'required': ['発熱', '咳'], 'optional': ['鼻水', 'のどの痛み', '悪寒'], 'confidence_boost': 0.2},
        'インフルエンザ': {'required': ['高熱', '頭痛'], 'optional': ['関節痛', '悪寒', '筋肉痛'], 'confidence_boost': 0.3},
        '胃腸炎': {'required': ['下痢', '腹痛'], 'optional': ['吐き気', '嘔吐', '発熱'], 'confidence_boost': 0.25},
        'アレルギー性鼻炎': {'required': ['鼻水', 'くしゃみ'], 'optional': ['鼻づまり', '目のかゆみ'], 'confidence_boost': 0.2}
    }

    for symptom_name, symptom_data in load_symptom_dictionary().items():
        matched = False
        canonical = symptom_data["canonical_name"]
        if canonical in user_text:
            matched = True

        if not matched:
            for synonym in symptom_data["synonyms"]:
                if synonym in user_text:
                    matched = True
                    break

        if not matched:
            if "痛み" in canonical or "痛い" in canonical:
                base_symptom = canonical.replace("の痛み", "").replace("痛み", "").replace("が痛い", "")
                if base_symptom and base_symptom in user_text and "痛" in user_text:
                    matched = True

            if not matched:
                for synonym in symptom_data["synonyms"]:
                    if "痛い" in synonym:
                        base_syn = synonym.replace("が痛い", "").replace("痛い", "")
                        if base_syn and base_syn in user_text and "痛" in user_text:
                            matched = True
                            break

        if matched:
            detected_symptoms.append({
                "name": symptom_name,
                "severity": "中等度",
                "duration_days": None
            })

    for flag_name, flag_keywords in RED_FLAG_SYMPTOMS.items():
        for keyword in flag_keywords:
            if keyword in user_text:
                red_flags.append(flag_name)
                break

    for symptom in detected_symptoms:
        symptom_text = user_text
        severity = "中等度"
        for severity_level, patterns in severity_patterns.items():
            for pattern in patterns:
                if re.search(pattern, symptom_text):
                    severity = severity_level
                    break
            if severity != "中等度":
                break
        symptom["severity"] = severity

    severity_tag_from_dialect = user_info.get('detected_severity_tag')
    escalation_score = user_info.get('escalation_score', 0.0)

    severity_order = {
        "重度": 5,
        "やや重度": 4,
        "中等度": 3,
        "軽度": 2,
        "やや軽度": 1
    }

    if escalation_score >= 4.0:
        if _DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"escalation_scoreが閾値を超えています: {escalation_score:.1f}")

    for symptom in detected_symptoms:
        current_severity = symptom.get("severity")
        current_level = severity_order.get(current_severity, 0)
        if severity_tag_from_dialect:
            dialect_level = severity_order.get(severity_tag_from_dialect, 0)
            if dialect_level > current_level:
                symptom["severity"] = severity_tag_from_dialect
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"方言から抽出した重症度タグを適用: {severity_tag_from_dialect}")

    duration_days = None
    for pattern in duration_patterns:
        match = re.search(pattern, user_text)
        if match:
            if pattern.startswith(r'(\d+)'):
                duration_days = int(match.group(1))
            elif "昨日" in match.group(0):
                duration_days = 1
            elif "一昨日" in match.group(0):
                duration_days = 2
            elif "先週" in match.group(0):
                duration_days = 7
            elif "数日" in match.group(0):
                duration_days = 3
            elif "数週間" in match.group(0):
                duration_days = 14
            break

    if duration_days is not None:
        for symptom in detected_symptoms:
            symptom["duration_days"] = duration_days

    detected_symptom_names = [s["name"] for s in detected_symptoms]
    if "不眠" in detected_symptom_names and "眠気" in detected_symptom_names:
        if any(keyword in user_text for keyword in ["寝てしまう", "眠くて", "眠すぎて"]):
            detected_symptoms = [s for s in detected_symptoms if s["name"] == "眠気"]
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug("不眠と眠気の両方が検出されましたが、文脈から眠気を優先しました")
        elif any(keyword in user_text for keyword in ["眠れない", "寝つきが悪い"]):
            detected_symptoms = [s for s in detected_symptoms if s["name"] == "不眠"]
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug("不眠と眠気の両方が検出されましたが、文脈から不眠を優先しました")

    symptom_names = [s['name'] for s in detected_symptoms]
    combination_boost = 0.0

    for pattern_name, pattern_data in SYMPTOM_COMBINATIONS.items():
        required_symptoms = pattern_data['required']
        optional_symptoms = pattern_data['optional']
        boost = pattern_data['confidence_boost']
        required_matched = sum(1 for req in required_symptoms if req in symptom_names)
        if required_matched == len(required_symptoms):
            optional_matched = sum(1 for opt in optional_symptoms if opt in symptom_names)
            combination_boost = boost + (optional_matched * 0.05)
            break

    confidence_score = 0.0
    if detected_symptoms:
        confidence_score += min(len(detected_symptoms) * 0.3, 0.6)
        severity_specificity = sum(1 for s in detected_symptoms if s["severity"] != "中等度")
        confidence_score += severity_specificity * 0.1
        if severity_specificity == 0 and len(detected_symptoms) > 0:
            confidence_score += 0.05
        if duration_days is not None:
            confidence_score += 0.2
        confidence_score += combination_boost

        first_symptom_name = detected_symptoms[0].get("name", "") if detected_symptoms else ""
        body_part = _extract_body_part_from_user_text(user_text, first_symptom_name)
        if body_part:
            confidence_score += 0.1
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"部位情報検出による信頼度向上: {body_part}")

        symptom_dict_matches = 0
        for symptom in detected_symptoms:
            sn = symptom.get("name", "")
            if sn in load_symptom_dictionary():
                symptom_dict_matches += 1
        if symptom_dict_matches > 0:
            confidence_score += min(symptom_dict_matches * 0.05, 0.15)
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"症状名の明確性による信頼度向上: {symptom_dict_matches}個の症状がload_symptom_dictionary()に完全一致")

        text_length = len(user_text.strip())
        if text_length > 15:
            confidence_score += 0.05
        if text_length > 30:
            confidence_score += 0.05
        if _DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"入力テキストの詳細度: {text_length}文字")

        explicit_patterns = [
            r'[がは]かゆ', r'[がは]痛', r'[がは]熱', r'[がは]咳',
        ]
        explicit_count = sum(1 for pattern in explicit_patterns if re.search(pattern, user_text))
        if explicit_count > 0:
            confidence_score += min(explicit_count * 0.03, 0.1)
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"明確な記述パターン検出: {explicit_count}個")

        confidence_score = min(confidence_score, 1.0)
    else:
        body_part = None

    needs_escalation = len(red_flags) > 0
    escalation_reason = f"重症疑い症状が検出されました: {', '.join(red_flags)}" if needs_escalation else ""

    if _DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug("=== 強化NLU結果 ===")
        logger.debug(f"検出された症状: {[s['name'] for s in detected_symptoms]}")
        logger.debug(f"重症疑い: {red_flags}")
        logger.debug(f"エスカレーション必要: {needs_escalation}")
        logger.debug(f"部位情報: {body_part if body_part else 'なし'}")
        logger.debug(f"信頼度スコア: {confidence_score:.2f}")

    if detected_symptoms:
        severity_levels = {"軽度": 1, "中等度": 2, "重度": 3}
        max_severity = max(
            (severity_levels.get(s.get("severity", "中等度"), 2) for s in detected_symptoms),
            default=2
        )
        severity_map = {1: "軽度", 2: "中等度", 3: "重度"}
        overall_severity = severity_map.get(max_severity, "中等度")
    else:
        overall_severity = "中等度"

    gender_detected_symptoms = []
    gender_detected = None
    current_gender = user_info.get('gender', '').strip() if user_info.get('gender') else ''

    if current_gender == '男性':
        gender_detected = {
            "detected": False,
            "gender": None,
            "confidence": None,
            "symptoms": [],
            "reason": "既存の性別が男性のため、症状からの自動判定をスキップ",
            "warning": "女性特有の症状が検出されましたが、既に性別が男性として登録されているため、性別は変更しませんでした。"
        }
    else:
        for symptom_name, symptom_data in FEMALE_SPECIFIC_SYMPTOMS.items():
            confidence = symptom_data["confidence"]
            synonyms = symptom_data["synonyms"]
            if confidence == "high":
                matched = False
                user_text_lower = user_text.lower()
                for synonym in synonyms:
                    synonym_lower = synonym.lower()
                    if synonym_lower in user_text_lower or user_text_lower in synonym_lower:
                        matched = True
                        break
                    pattern = re.escape(synonym_lower).replace(r'\ ', r'\s*')
                    if re.search(pattern, user_text_lower):
                        matched = True
                        break

                if matched:
                    gender_detected_symptoms.append(symptom_name)

        if len(gender_detected_symptoms) > 0:
            gender_detected = {
                "detected": True,
                "gender": "female",
                "confidence": "high",
                "symptoms": gender_detected_symptoms,
                "reason": f"{', '.join(gender_detected_symptoms)}の症状から女性と判定"
            }
            logger.info(f"👤 性別自動判定: {gender_detected['reason']}")
        else:
            gender_detected = {
                "detected": False,
                "gender": None,
                "confidence": None,
                "symptoms": [],
                "reason": "女性特有の症状が検出されませんでした"
            }

    pregnancy_detected_symptoms = []
    pregnancy_score = 0.0
    if gender_detected and gender_detected.get('detected'):
        detected_gender_en = gender_detected.get('gender')
        if detected_gender_en == 'female':
            gender = '女性'
        elif detected_gender_en == 'male':
            gender = '男性'
        else:
            gender = current_gender
    else:
        gender = current_gender

    if gender == '男性':
        pregnancy_possible = {
            "detected": False,
            "score": 0.0,
            "symptoms": [],
            "confidence": None,
            "gender": "male"
        }
    else:
        for symptom_name, symptom_data in PREGNANCY_SYMPTOMS.items():
            weight = symptom_data["weight"]
            synonyms = symptom_data["synonyms"]
            matched = False
            for synonym in synonyms:
                if synonym in user_text:
                    matched = True
                    break

            if matched:
                pregnancy_detected_symptoms.append(symptom_name)
                pregnancy_score += weight

        if gender == '女性':
            threshold = 4.0
        else:
            threshold = 4.5

        if gender != '女性' and pregnancy_score >= threshold:
            pregnancy_possible = {
                "detected": True,
                "score": pregnancy_score,
                "symptoms": pregnancy_detected_symptoms,
                "confidence": "low",
                "gender": "unknown"
            }
        elif gender != '女性' and pregnancy_score > 0.0:
            important_symptoms = ["つわり", "生理の遅れ", "着床出血", "胸の張り"]
            has_important_symptom = any(symptom in important_symptoms for symptom in pregnancy_detected_symptoms)

            if has_important_symptom:
                pregnancy_possible = {
                    "detected": True,
                    "score": pregnancy_score,
                    "symptoms": pregnancy_detected_symptoms,
                    "confidence": "low",
                    "gender": "unknown"
                }
            else:
                pregnancy_possible = {
                    "detected": False,
                    "score": pregnancy_score,
                    "symptoms": pregnancy_detected_symptoms,
                    "confidence": None,
                    "gender": "unknown"
                }
        elif gender == '女性' and pregnancy_score >= threshold:
            pregnancy_possible = {
                "detected": True,
                "score": pregnancy_score,
                "symptoms": pregnancy_detected_symptoms,
                "confidence": "high",
                "gender": "female"
            }
        else:
            pregnancy_possible = {
                "detected": False,
                "score": pregnancy_score,
                "symptoms": pregnancy_detected_symptoms,
                "confidence": None,
                "gender": gender if gender else "unknown"
            }

    if pregnancy_possible.get('detected', False):
        logger.info(f"🤰 妊娠の可能性検出: detected={pregnancy_possible['detected']}, score={pregnancy_possible['score']:.2f}, confidence={pregnancy_possible['confidence']}, symptoms={pregnancy_possible['symptoms']}, gender={pregnancy_possible.get('gender', 'unknown')}")
    else:
        if pregnancy_possible.get('score', 0.0) > 0.0:
            threshold = 2.0 if gender == '女性' else 4.5
            logger.info(f"🤰 妊娠可能性検出（閾値未満）: score={pregnancy_possible['score']:.2f}, threshold={threshold}, symptoms={pregnancy_possible['symptoms']}, gender={pregnancy_possible.get('gender', 'unknown')}")
        elif _DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"妊娠可能性検出: detected={pregnancy_possible['detected']}, score={pregnancy_possible['score']:.2f}, confidence={pregnancy_possible['confidence']}, symptoms={pregnancy_possible['symptoms']}")

    insomnia_diagnosed = False
    chronic_insomnia = False
    has_insomnia_symptom = any(s.get("name") == "不眠" for s in detected_symptoms)

    if has_insomnia_symptom:
        insomnia_diagnosis_keywords = [
            "不眠症と診断", "不眠症と言われた", "不眠症の診断", "病院で不眠症",
            "医師から不眠症", "不眠症です", "不眠症と", "不眠症で", "不眠症の"
        ]
        for keyword in insomnia_diagnosis_keywords:
            if keyword in user_text:
                insomnia_diagnosed = True
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"不眠症診断キーワード検出: {keyword}")
                break

        chronic_insomnia_keywords = [
            "慢性的", "ずっと", "長期間", "何ヶ月も", "何年も", "継続的",
            "ずっと続いている", "長い間", "ずっと続く", "慢性的に"
        ]
        for keyword in chronic_insomnia_keywords:
            if keyword in user_text:
                chronic_insomnia = True
                if _DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"慢性的不眠キーワード検出: {keyword}")
                break

        if duration_days is not None and duration_days >= 7:
            chronic_insomnia = True
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"期間による慢性的不眠判定: {duration_days}日間")

    return {
        "symptoms": detected_symptoms,
        "red_flags": red_flags,
        "needs_escalation": needs_escalation,
        "escalation_reason": escalation_reason,
        "confidence_score": confidence_score,
        "user_body_part": body_part,
        "severity": overall_severity,
        "pregnancy_possible": pregnancy_possible,
        "gender_detected": gender_detected,
        "insomnia_diagnosed": insomnia_diagnosed,
        "chronic_insomnia": chronic_insomnia
    }


def hybrid_nlu_extraction(
    user_text: str,
    user_info: Dict,
    client: OpenAI,
    session_id: str = None,
    *,
    use_cache: bool = True,
) -> Dict:
    """
    ハイブリッドNLU（ルールベース優先、ChatGPT APIフォールバック）
    use_cache=False のときキャッシュ読み書きをスキップ（resolve_nlu 側でマージ後に保存）
    """
    if use_cache:
        cached_result = get_cached_nlu_result(user_text, session_id)
        if cached_result:
            if _DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug("NLUキャッシュから結果を取得")
            return cached_result

    if _DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug("ルールベースNLUを実行")
    rule_based_result = simple_pattern_matching_nlu(user_text, user_info)

    confidence_score = rule_based_result.get('confidence_score', 0.0)
    symptoms_count = len(rule_based_result.get('symptoms', []))

    if symptoms_count == 0 or confidence_score < 0.3:
        if _DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"ルールベースNLUの信頼度が低いため、ChatGPT APIを呼び出し（信頼度: {confidence_score:.2f}）")
        from src.core.language_utils import detect_language

        session_lang = (user_info or {}).get("language")
        detected_lang = detect_language(user_text, session_lang)
        gpt_result = extract_symptoms_with_gpt(
            user_text, user_info, client, detected_language=detected_lang
        )

        if 'gender_detected' in rule_based_result:
            gpt_result['gender_detected'] = rule_based_result['gender_detected']
        if 'pregnancy_possible' in rule_based_result:
            gpt_result['pregnancy_possible'] = rule_based_result['pregnancy_possible']

        if use_cache:
            set_cached_nlu_result(user_text, gpt_result, session_id)
        return gpt_result
    else:
        if _DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"ルールベースNLUの信頼度が十分（信頼度: {confidence_score:.2f}）")
        if use_cache:
            set_cached_nlu_result(user_text, rule_based_result, session_id)
        return rule_based_result


def _canonical_symptom_names_csv() -> str:
    return ", ".join(load_symptom_dictionary().keys())


_SYMPTOM_GPT_SYSTEM_JA = """あなたは医療NLUシステムです。症状文から正確に情報を抽出してください。

【最重要ルール - 症状名の正確な抽出】
1. 「目がかゆい」「目もかゆい」「目の痒み」「目かゆい」「目が痒い」→必ず「目のかゆみ」として抽出（「かゆみ」ではない）
2. 「かゆみ」は皮膚のかゆみを指し、「目のかゆみ」とは区別してください
3. 「鼻水+くしゃみ+目のかゆみ」の組み合わせはアレルギー性鼻炎の可能性が高い
4. 「のどが痛い」「喉が痛い」→「のどの痛み」として抽出

【その他の重要な注意事項】
- 高熱（38.5度以上）と複数の風邪症状がある場合は、red_flagsに「インフルエンザ疑い」を追加してください
- 体温情報を正確に抽出し、38.5度以上の場合は「高熱」として扱ってください
- 症状名は必ず提供リストの日本語 canonical 名から選択してください
- 重症疑い症状がある場合は必ずneeds_escalationをtrueにしてください"""

_SYMPTOM_GPT_SYSTEM_I18N = """You are a medical NLU system for Japanese OTC medicine recommendation.
Return valid JSON only. The user may write in a non-Japanese language.

CRITICAL: Each symptoms[].name MUST be an exact Japanese label from the canonical list in the user message (not English).
Examples: itchy eyes -> 目のかゆみ (NOT かゆみ); sore throat -> のどの痛み.
Severity values MUST be Japanese: 軽度, 中等度, or 重度.
red_flags and escalation_reason may be in Japanese."""


def _build_symptom_gpt_user_prompt(
    sanitized_text: str,
    user_info: Dict,
    lang: str,
) -> str:
    from src.core.i18n_prompts import normalize_lang

    lang = normalize_lang(lang)
    canonical = _canonical_symptom_names_csv()
    age = user_info.get("age", "不明")
    gender = user_info.get("gender", "不明")
    pregnant = user_info.get("pregnant", False)
    breastfeeding = user_info.get("breastfeeding", False)

    if lang == "ja":
        return f"""
あなたは医療NLUシステムです。ユーザーの症状文から以下の情報を抽出してください。

【ユーザー入力】
{sanitized_text}

【ユーザー情報】
年齢: {age}
性別: {gender}
妊娠中: {pregnant}
授乳中: {breastfeeding}

【抽出すべき情報】
1. 症状リスト（以下から該当するものを選択）
   {canonical}

2. 各症状の重症度（軽度/中等度/重度）
3. 症状の期間（何日前から）
4. 重症疑い症状の有無（呼吸困難、高熱38.5度以上、胸痛、意識障害など）

【回答形式】
以下のJSON形式で回答してください：
{{
    "symptoms": [
        {{
            "name": "症状名",
            "severity": "軽度 or 中等度 or 重度",
            "duration_days": 数値（不明なら null）
        }}
    ],
    "red_flags": ["重症疑い症状1", "重症疑い症状2"],
    "needs_escalation": true or false,
    "escalation_reason": "エスカレーションが必要な理由"
}}

【重要な注意事項】
- 症状名は必ず上記のリストから選択してください
- 「目がかゆい」「目もかゆい」「目の痒み」などは必ず「目のかゆみ」として抽出してください（「かゆみ」ではありません）
- 「かゆみ」は皮膚のかゆみを指し、「目のかゆみ」とは区別してください
- 「のどが痛い」「喉が痛い」は「のどの痛み」として抽出してください
- 重症疑い症状がある場合は必ず needs_escalation を true にしてください
- 情報が不明な場合は null を使用してください
- インフルエンザの可能性がある場合（高熱38.5度以上+複数の風邪症状）は、red_flagsに「インフルエンザ疑い」を追加してください
- 体温情報がある場合は、38.5度以上の場合は「高熱」としてred_flagsに追加してください
"""

    lang_labels = {
        "en": "English",
        "ko": "Korean",
        "zh": "Chinese",
    }
    lang_label = lang_labels.get(lang, "English")
    return f"""
You are a medical NLU system. The user wrote in {lang_label}. Extract structured symptom data for Japanese OTC routing.

【User input】
{sanitized_text}

【User context】
Age: {age}
Gender: {gender}
Pregnant: {pregnant}
Breastfeeding: {breastfeeding}

【Canonical symptom names — use ONLY these exact Japanese strings in symptoms[].name】
{canonical}

【Extract】
1. Matching symptoms from the canonical list (translate meaning from user language)
2. severity per symptom: 軽度 / 中等度 / 重度 (Japanese only)
3. duration_days (integer or null)
4. red_flags for emergencies (high fever >=38.5C, breathing difficulty, chest pain, etc.)

【JSON shape】
{{
    "symptoms": [{{"name": "<Japanese canonical>", "severity": "軽度|中等度|重度", "duration_days": null}}],
    "red_flags": [],
    "needs_escalation": false,
    "escalation_reason": ""
}}

Rules: itchy eyes -> 目のかゆみ not かゆみ; sore throat -> のどの痛み; runny nose -> 鼻水; sneezing -> くしゃみ.
"""


def extract_symptoms_with_gpt(
    user_text: str,
    user_info: Dict,
    client: OpenAI,
    *,
    detected_language: str = "ja",
) -> Dict:
    """
    ChatGPT APIを使用してユーザーの自由入力から症状を抽出・構造化。
    非日本語入力時も symptoms[].name は辞書の日本語 canonical に正規化する。
    """
    from src.security.security_validator import validate_user_input
    from src.security.security_config import should_block_input
    from src.security.security_logger import log_input_validation
    from src.security.json_validator import safe_json_parse

    is_safe, risk_score, warnings, sanitized_text = validate_user_input(
        user_text, context='symptom'
    )

    log_input_validation(
        user_id=user_info.get('user_id', 'unknown'),
        input_text=user_text,
        risk_score=risk_score,
        is_safe=is_safe,
        warnings=warnings,
        sanitized_text=sanitized_text
    )

    if should_block_input(risk_score):
        if _DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"⚠️ 入力がブロックされました: リスクスコア {risk_score}")
        return {
            "symptoms": [],
            "red_flags": ["入力検証エラー"],
            "needs_escalation": True,
            "escalation_reason": "入力内容に問題が検出されました。症状や質問を自然な文章で入力してください。"
        }

    if risk_score >= 80:
        if _DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug(f"⚠️ 高リスク入力のため症状抽出を停止: リスクスコア {risk_score}")
        return {
            "symptoms": [],
            "red_flags": ["高リスク入力"],
            "needs_escalation": True,
            "escalation_reason": "入力内容に不審なパターンが検出されました。症状や質問を自然な文章で入力してください。"
        }

    from src.core.i18n_prompts import normalize_lang

    lang = normalize_lang(detected_language)
    prompt = _build_symptom_gpt_user_prompt(sanitized_text, user_info, lang)
    system_content = (
        _SYMPTOM_GPT_SYSTEM_JA if lang == "ja" else _SYMPTOM_GPT_SYSTEM_I18N
    )

    try:
        from src.core.llm_client import chat_completion_create

        response = chat_completion_create(
            client,
            model_role="nlu",
            path="nlu_service.extract_symptoms",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1000
        )

        result = response.choices[0].message.content

        try:
            parsed_result = safe_json_parse(result, schema='symptom_analysis')
        except Exception as e:
            logger.warning(f"JSON解析エラー: {e}")
            return {
                "symptoms": [],
                "red_flags": [],
                "needs_escalation": False,
                "escalation_reason": ""
            }

        if _DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug("=== NLU結果 ===")
            logger.debug(f"抽出された症状: {parsed_result.get('symptoms', [])}")
            logger.debug(f"重症疑い: {parsed_result.get('red_flags', [])}")
            logger.debug(f"エスカレーション必要: {parsed_result.get('needs_escalation', False)}")

        symptoms_list = parsed_result.get('symptoms', [])
        if symptoms_list:
            severity_levels = {"軽度": 1, "中等度": 2, "重度": 3}
            max_severity = max(
                (severity_levels.get(s.get("severity", "中等度"), 2) for s in symptoms_list),
                default=2
            )
            severity_map = {1: "軽度", 2: "中等度", 3: "重度"}
            parsed_result["severity"] = severity_map.get(max_severity, "中等度")
        else:
            parsed_result["severity"] = "中等度"

        try:
            rule_based_result = simple_pattern_matching_nlu(user_text, user_info)
            if 'gender_detected' in rule_based_result:
                parsed_result['gender_detected'] = rule_based_result['gender_detected']
            if 'pregnancy_possible' in rule_based_result:
                parsed_result['pregnancy_possible'] = rule_based_result['pregnancy_possible']
        except Exception as e:
            logger.warning(f"性別・妊娠可能性検出の追加でエラー: {e}")

        return parsed_result

    except Exception as e:
        logger.warning(f"NLU処理エラー: {e}")
        logger.info("フォールバック: 簡易パターンマッチングに切り替えます")
        return simple_pattern_matching_nlu(user_text, user_info)
