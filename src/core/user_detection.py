"""
ユーザー属性・症状検出モジュール

重症度判定、痛み緊急性、消化器感受性、産後・授乳、
ユーザー要望抽出、不足情報減点の責務を持つ。
"""
import re
import logging
from typing import Dict

logger = logging.getLogger(__name__)

PENALTY_MAP = {
    "age": 0.15,
    "allergies": 0.15,
    "pregnancy_status": 0.15,
    "gender": 0.05,
    "current_medications": 0.05,
    "symptom_duration": 0.02,
    "symptoms": 0.0
}


def detect_severity_escalation(user_message: str, nlu_result: dict, user_info: dict) -> dict:
    """症状の重症度による受診勧奨の判定"""
    needs_escalation = False
    reason = ""
    urgency = "low"
    message = ""
    user_message_lower = user_message.lower() if user_message else ""

    temporal_keywords = ['年々', '徐々に', 'だんだん', '次第に', '段々', 'だんだんと', '徐々', '年を追うごとに', '年を重ねるごとに']
    severity_keywords = ['ひどくなっている', '悪化', '悪化している', 'ひどくなった', '強くなっている', '強くなった', 'つらくなっている', 'つらくなった']
    pain_keywords = ['生理痛', '月経痛', '腹痛', 'お腹の痛み', '下腹部痛', '下腹部の痛み']

    has_temporal = any(kw in user_message_lower for kw in temporal_keywords)
    has_severity = any(kw in user_message_lower for kw in severity_keywords)
    has_pain = any(kw in user_message_lower for kw in pain_keywords)

    if has_temporal and has_severity and has_pain:
        needs_escalation = True
        reason = "生理痛が年々ひどくなっている"
        urgency = "high"
        message = "生理痛が年々ひどくなっている場合、子宮内膜症などの疾患が隠れている可能性があります。婦人科での受診をお勧めします。"
        logger.info(f"🚨 受診勧奨: {reason} (緊急度: {urgency})")
        return {"needs_escalation": needs_escalation, "reason": reason, "urgency": urgency, "message": message}

    if nlu_result:
        symptoms = nlu_result.get("symptoms", [])
        for symptom in symptoms:
            symptom_name = symptom.get("name", "")
            if "進行" in str(symptom) or "悪化" in str(symptom):
                if "生理痛" in symptom_name or "月経痛" in symptom_name:
                    needs_escalation = True
                    reason = "生理痛の進行パターンが検出されました"
                    urgency = "high"
                    message = "生理痛が進行している場合、子宮内膜症などの疾患が隠れている可能性があります。婦人科での受診をお勧めします。"
                    logger.info(f"🚨 受診勧奨: {reason} (緊急度: {urgency})")
                    return {"needs_escalation": needs_escalation, "reason": reason, "urgency": urgency, "message": message}

    excessive_bleeding_keywords = [
        '出血量が多い', '過多月経', 'ナプキンがすぐにいっぱいになる',
        '出血が多い', '経血量が多い', '出血が異常に多い', '出血量が異常',
        '大量出血', '出血が止まらない', '出血が長引く'
    ]
    severity_modifiers = ['異常に', '非常に', '大量に', 'すごく', 'とても', 'かなり', 'めちゃくちゃ']
    bleeding_keywords = ['出血', '経血', '生理の出血', '月経の出血']

    if any(kw in user_message_lower for kw in excessive_bleeding_keywords):
        needs_escalation = True
        reason = "過多月経の可能性"
        urgency = "high"
        message = "出血量が異常に多い場合、子宮筋腫や子宮内膜症などの疾患が隠れている可能性があります。婦人科での受診をお勧めします。"
        logger.info(f"🚨 受診勧奨: {reason} (緊急度: {urgency})")
        return {"needs_escalation": needs_escalation, "reason": reason, "urgency": urgency, "message": message}

    has_severity_modifier = any(kw in user_message_lower for kw in severity_modifiers)
    has_bleeding = any(kw in user_message_lower for kw in bleeding_keywords)
    if has_severity_modifier and has_bleeding:
        needs_escalation = True
        reason = "異常な出血量の可能性"
        urgency = "high"
        message = "出血量が異常に多い場合、子宮筋腫や子宮内膜症などの疾患が隠れている可能性があります。婦人科での受診をお勧めします。"
        logger.info(f"🚨 受診勧奨: {reason} (緊急度: {urgency})")
        return {"needs_escalation": needs_escalation, "reason": reason, "urgency": urgency, "message": message}

    if nlu_result:
        symptoms = nlu_result.get("symptoms", [])
        for symptom in symptoms:
            symptom_name = symptom.get("name", "")
            if "過多月経" in symptom_name or "出血量" in symptom_name:
                needs_escalation = True
                reason = "過多月経の症状が検出されました"
                urgency = "high"
                message = "出血量が異常に多い場合、子宮筋腫や子宮内膜症などの疾患が隠れている可能性があります。婦人科での受診をお勧めします。"
                logger.info(f"🚨 受診勧奨: {reason} (緊急度: {urgency})")
                return {"needs_escalation": needs_escalation, "reason": reason, "urgency": urgency, "message": message}

    return {"needs_escalation": False, "reason": "", "urgency": "", "message": ""}


def generate_doctor_referral_message(escalation_info: dict) -> dict:
    """受診勧奨メッセージの生成"""
    if not escalation_info.get("needs_escalation", False):
        return {}
    reason = escalation_info.get("reason", "")
    urgency = escalation_info.get("urgency", "medium")
    message = escalation_info.get("message", "")
    recommended_department = "婦人科"
    urgency_message = "早めに" if urgency == "high" else ("なるべく早く" if urgency == "medium" else "可能な限り")
    return {
        "title": "受診をお勧めします",
        "reason": reason,
        "recommended_department": recommended_department,
        "urgency": urgency,
        "urgency_message": urgency_message,
        "message": message,
        "additional_info": "市販薬で対応できない症状の可能性があります。専門医の診察を受けることをお勧めします。"
    }


def determine_pain_urgency(user_message: str, nlu_result: dict) -> dict:
    """痛みの緊急性判定（痛みが主訴か随伴症状かを判定）"""
    user_message_lower = user_message.lower() if user_message else ""
    detected_keywords = []
    primary_pain_keywords = ['痛い', '激痛', '痛くて辛い', '痛くてつらい', '痛みが強い', '痛みがひどい', '痛みで', '痛みのため']
    secondary_pain_keywords = ['たまに痛む', '時々痛む', '痛むことがある', '痛みがある', '痛みを感じる']
    primary_patterns = [r'痛くて\s*辛い', r'痛くて\s*つらい', r'痛みが\s*強い', r'痛みが\s*ひどい', r'激痛', r'痛みで\s*', r'痛みのため\s*']
    secondary_patterns = [r'たまに\s*痛む', r'時々\s*痛む', r'痛む\s*ことが\s*ある', r'痛みが\s*ある', r'痛みを\s*感じる']

    has_primary_keyword = any(kw in user_message_lower for kw in primary_pain_keywords)
    has_secondary_keyword = any(kw in user_message_lower for kw in secondary_pain_keywords)
    for kw in primary_pain_keywords:
        if kw in user_message_lower:
            detected_keywords.append(kw)
            break
    if not has_primary_keyword:
        for kw in secondary_pain_keywords:
            if kw in user_message_lower:
                detected_keywords.append(kw)
                break

    has_primary_pattern = any(re.search(p, user_message_lower) for p in primary_patterns)
    has_secondary_pattern = any(re.search(p, user_message_lower) for p in secondary_patterns) if not has_primary_pattern else False

    nlu_primary = False
    if nlu_result:
        symptoms = nlu_result.get("symptoms", [])
        for i, symptom in enumerate(symptoms):
            symptom_name = symptom.get("name", "")
            if "痛" in symptom_name or "痛み" in symptom_name:
                if i == 0 or symptom.get("priority", 0) > 0.7:
                    nlu_primary = True
                    break

    is_primary = has_primary_keyword or has_primary_pattern or nlu_primary
    pain_level = "mild"
    if any(kw in user_message_lower for kw in ['激痛', '激しい痛み', '強い痛み', 'ひどい痛み']):
        pain_level = "severe"
    elif any(kw in user_message_lower for kw in ['痛い', '痛み', '痛む']):
        pain_level = "moderate"

    logger.info(f"🔍 痛みの緊急性判定: is_primary={is_primary}, pain_level={pain_level}, keywords={detected_keywords}")
    return {"is_primary": is_primary, "pain_level": pain_level, "keywords": detected_keywords}


def detect_digestive_sensitivity(user_message: str, nlu_result: dict, user_info: dict) -> dict:
    """消化器症状の検出（お腹を壊しやすい、下痢しやすいなど）"""
    has_digestive_sensitivity = False
    reason = ""
    user_message_lower = user_message.lower() if user_message else ""
    digestive_keywords = ['お腹を壊しやすい', '下痢しやすい', 'お腹が弱い', '胃腸が弱い', '下痢をしやすい', 'お腹を下しやすい']
    if any(kw in user_message_lower for kw in digestive_keywords):
        has_digestive_sensitivity = True
        reason = "明示的なキーワード検出"
    if not has_digestive_sensitivity and nlu_result:
        for symptom in nlu_result.get("symptoms", []):
            if "下痢" in symptom.get("name", "") or "消化器" in symptom.get("name", ""):
                has_digestive_sensitivity = True
                reason = "NLU解析による検出"
                break
    if not has_digestive_sensitivity and user_info.get('digestive_sensitivity') is True:
        has_digestive_sensitivity = True
        reason = "ユーザー属性による検出"
    return {"has_digestive_sensitivity": has_digestive_sensitivity, "reason": reason}


def preference_context_text(user_message: str = "", user_info: dict = None) -> str:
    """チャット本文と属性モーダル「その他」を結合（毎回のメッセージ解析用）。"""
    parts: list[str] = []
    if user_message and str(user_message).strip():
        parts.append(str(user_message).strip())

    if not user_info:
        return "\n".join(parts)

    for key in ("other_info",):
        val = user_info.get(key)
        if val and str(val).strip():
            snippet = str(val).strip()
            if snippet not in "\n".join(parts):
                parts.append(snippet)

    attrs = user_info.get("user_attributes")
    if isinstance(attrs, dict):
        other = attrs.get("other_info")
        if other and str(other).strip():
            snippet = str(other).strip()
            if snippet not in "\n".join(parts):
                parts.append(snippet)

    return "\n".join(parts)


def extract_user_preferences(user_message: str, nlu_result: dict = None, user_info: dict = None) -> dict:
    """ユーザー要望を抽出（成分・バランス、飲みやすさ、随伴症状など）"""
    text = preference_context_text(user_message or "", user_info)
    if not text.strip():
        return {
            "ingredient_balance": False,
            "ease_of_taking": False,
            "accompanying_symptoms": False,
            "confidence": 0.0,
            "reasons": [],
            "prefers_kampo": False,
            "prefers_not_kampo": False,
            "avoid_drowsiness": False,
            "prefer_non_sedating": False,
            "avoid_dry_mouth": False,
            "prefer_fewer_daily_doses": False,
            "preferred_max_daily_doses": None,
            "prefer_nasal_route": False,
            "avoid_nasal_route": False,
        }
    user_message_lower = text.lower()
    reasons = []
    ingredient_balance_keywords = ["成分", "バランス", "配合", "ビタミン", "栄養", "総合", "複合", "成分重視", "バランス重視", "配合成分", "成分のバランス", "ビタミン配合", "栄養補給", "総合的な", "複合的な", "成分・バランス", "成分・バランス重視", "成分バランス", "生薬重視", "漢方重視", "複合成分"]
    ease_of_taking_keywords = ["飲みやすい", "飲みやすさ", "錠剤", "カプセル", "顆粒", "顆粒が苦手", "味が苦手", "漢方の味", "苦い", "飲みにくい", "服用しやすい", "簡単に", "手軽に", "1日1回", "1日2回", "服用回数が少ない", "飲みやすさ重視", "服用しやすさ", "手軽に飲める", "錠剤タイプ", "錠剤タイプが", "錠剤が", "カプセルタイプ", "顆粒苦手", "味が苦手", "携帯しやすい"]
    accompanying_symptoms_keywords = ["随伴症状", "併発", "一緒に", "同時に", "複数の症状", "いろいろな症状", "ニキビ", "肌荒れ", "腰痛", "頭痛", "めまい", "冷え症", "むくみ", "複数の悩み", "様々な症状", "多様な症状", "幅広い症状", "あれこれ", "あれこれ気になる", "色々気になる", "色々な症状", "複合的な症状", "全体的に", "まとめて", "随伴症状対応"]
    ingredient_balance = sum(1 for kw in ingredient_balance_keywords if kw in user_message_lower)
    ease_of_taking = sum(1 for kw in ease_of_taking_keywords if kw in user_message_lower)
    accompanying_symptoms = sum(1 for kw in accompanying_symptoms_keywords if kw in user_message_lower)
    if nlu_result and len(nlu_result.get("symptoms", [])) >= 2:
        accompanying_symptoms += 1
        reasons.append("随伴症状対応: 複数の症状が検出されました")
    for kw in ingredient_balance_keywords:
        if kw in user_message_lower:
            reasons.append(f"成分・バランス重視: '{kw}'を検出")
    for kw in ease_of_taking_keywords:
        if kw in user_message_lower:
            reasons.append(f"飲みやすさ重視: '{kw}'を検出")
    for kw in accompanying_symptoms_keywords:
        if kw in user_message_lower:
            reasons.append(f"随伴症状対応: '{kw}'を検出")
    total = sum(1 for kw in ingredient_balance_keywords if kw in user_message_lower) + sum(1 for kw in ease_of_taking_keywords if kw in user_message_lower) + accompanying_symptoms
    ib = any(kw in user_message_lower for kw in ingredient_balance_keywords)
    et = any(kw in user_message_lower for kw in ease_of_taking_keywords)
    ac = any(kw in user_message_lower for kw in accompanying_symptoms_keywords) or (nlu_result and len(nlu_result.get("symptoms", [])) >= 2)
    if not ib and any(kw in user_message_lower for kw in ["ビタミン", "総合", "複合", "配合"]):
        ib = True
        reasons.append("成分・バランス重視: ビタミンや総合的な表現から推測")
    if not et and any(kw in user_message_lower for kw in ["錠剤", "カプセル", "1日1回", "1日2回", "服用回数"]):
        et = True
        reasons.append("飲みやすさ重視: 錠剤や服用回数に関する言及から推測")
    if not ac and nlu_result and len(nlu_result.get("symptoms", [])) >= 2:
        ac = True
        reasons.append("随伴症状対応: 複数の症状から推測")
    confidence = min(1.0, 0.7 + (total - 3) * 0.1) if total >= 3 else (0.5 + (total - 2) * 0.1 if total >= 2 else (0.3 + (total - 1) * 0.1 if total >= 1 else 0.0))

    # 漢方薬希望/忌避の抽出
    prefers_kampo_keywords = ["漢方", "漢方薬", "漢方希望", "漢方がいい", "漢方の方が", "生薬", "生薬希望", "漢方で", "漢方を使って", "漢方が良い", "漢方薬がいい"]
    prefers_not_kampo_keywords = [
        "漢方はいや", "漢方いや", "漢方薬はいや", "漢方は嫌", "漢方嫌", "漢方薬嫌", "漢方薬は避けたい",
        "漢方以外", "漢方以外がいい", "漢方以外が良い", "西洋薬がいい", "西洋薬希望", "西洋薬で",
        "漢方は苦手", "漢方薬は苦手", "漢方が苦手", "漢方薬が苦手"
    ]
    avoid_drowsiness_keywords = [
        "眠気", "眠くなる", "眠くなり", "寝てしまう", "運転", "車を", "車の運転",
        "ふらつき", "だるさが気になる", "非鎮静", "眠気の少ない", "眠気が少ない",
        "起きない", "日中の眠気", "仕事中に眠",
    ]
    avoid_dry_mouth_keywords = [
        "口渇",
        "口が渇",
        "口が乾",
        "口の渇き",
        "口の乾燥",
        "喉が渇",
        "喉の渇き",
        "喉の乾燥",
        "のどが渇",
        "のどの渇き",
        "のどの乾燥",
        "渇きにくい",
        "渇きが少ない",
        "渇きの少ない",
        "乾燥感",
        "乾燥が少ない",
    ]
    prefer_fewer_dose_keywords = [
        "1日1回", "一日1回", "1回だけ", "回数が少ない", "服用回数が少ない", "飲み忘れ",
        "手間が少ない", "1日2回以内", "1日２回以内",
    ]
    prefer_nasal_keywords = [
        "点鼻", "鼻に直接", "鼻のスプレー", "鼻喷雾", "噴霧", "鼻に入れる",
    ]
    avoid_nasal_keywords = [
        "点鼻は", "点鼻が苦手", "鼻に入れるのは", "鼻に入れるのが", "スプレーは苦手",
        "鼻に入れたくない",
    ]
    prefers_kampo = any(kw in user_message_lower for kw in prefers_kampo_keywords)
    prefers_not_kampo = any(kw in user_message_lower for kw in prefers_not_kampo_keywords)
    avoid_drowsiness = any(kw in user_message_lower for kw in avoid_drowsiness_keywords)
    avoid_dry_mouth = any(kw in user_message_lower for kw in avoid_dry_mouth_keywords)
    if nlu_result:
        for symptom in nlu_result.get("symptoms", []):
            if symptom.get("name") == "口渇":
                avoid_dry_mouth = True
                reasons.append("口渇回避: NLU症状「口渇」から検出")
                break
    prefer_fewer_daily_doses = any(kw in user_message_lower for kw in prefer_fewer_dose_keywords)
    prefer_nasal_route = any(kw in user_message_lower for kw in prefer_nasal_keywords)
    avoid_nasal_route = any(kw in user_message_lower for kw in avoid_nasal_keywords)
    preferred_max_daily_doses = None
    if "1日1回" in user_message_lower or "一日1回" in user_message_lower:
        preferred_max_daily_doses = 1
    elif "1日2回" in user_message_lower or "一日2回" in user_message_lower:
        preferred_max_daily_doses = 2
    elif "1日3回" in user_message_lower:
        preferred_max_daily_doses = 3
    prefer_non_sedating = avoid_drowsiness or any(
        kw in user_message_lower for kw in ["非鎮静", "眠気の出にくい", "眠くなりにくい"]
    )
    # 両方検出された場合はprefers_not_kampo（避けたい）を優先
    if prefers_kampo and prefers_not_kampo:
        prefers_kampo = False

    if avoid_drowsiness:
        reasons.append("眠気回避: キーワードから検出")
    if avoid_dry_mouth:
        reasons.append("口渇回避: キーワードから検出")
    if prefer_fewer_daily_doses or preferred_max_daily_doses:
        reasons.append(f"服用回数の希望: max={preferred_max_daily_doses}")
    if prefer_nasal_route:
        reasons.append("点鼻希望: キーワードから検出")
    if avoid_nasal_route:
        reasons.append("点鼻回避: キーワードから検出")

    logger.info(
        f"📋 ユーザー要望抽出: 成分・バランス={ib}, 飲みやすさ={et}, 随伴症状={ac}, "
        f"漢方希望={prefers_kampo}, 漢方忌避={prefers_not_kampo}, 眠気回避={avoid_drowsiness}, "
        f"口渇回避={avoid_dry_mouth}, 点鼻希望={prefer_nasal_route}, 確信度={confidence:.2f}"
    )
    return {
        "ingredient_balance": ib,
        "ease_of_taking": et,
        "accompanying_symptoms": ac,
        "confidence": confidence,
        "reasons": reasons,
        "prefers_kampo": prefers_kampo,
        "prefers_not_kampo": prefers_not_kampo,
        "avoid_drowsiness": avoid_drowsiness,
        "prefer_non_sedating": prefer_non_sedating,
        "avoid_dry_mouth": avoid_dry_mouth,
        "prefer_fewer_daily_doses": prefer_fewer_daily_doses,
        "preferred_max_daily_doses": preferred_max_daily_doses,
        "prefer_nasal_route": prefer_nasal_route,
        "avoid_nasal_route": avoid_nasal_route,
    }


def detect_postpartum_breastfeeding(user_message: str, nlu_result: dict, user_info: dict) -> dict:
    """産後・授乳中の判定"""
    is_postpartum = False
    is_breastfeeding = False
    reason = ""
    user_message_lower = user_message.lower() if user_message else ""
    postpartum_keywords = ['産後', '出産後', '分娩後']
    breastfeeding_keywords = ['授乳中', '授乳', '母乳', '授乳している', '授乳期間中']
    if any(kw in user_message_lower for kw in postpartum_keywords):
        is_postpartum = True
        reason = "明示的なキーワード検出（産後）"
    if any(kw in user_message_lower for kw in breastfeeding_keywords):
        is_breastfeeding = True
        reason = reason + "、授乳中" if reason else "明示的なキーワード検出（授乳中）"
    if not is_postpartum and user_info.get('postpartum') is True:
        is_postpartum = True
        reason = reason or "ユーザー属性による検出（産後）"
    if not is_breastfeeding and user_info.get('breastfeeding') is True:
        is_breastfeeding = True
        reason = reason + "、授乳中" if reason else "ユーザー属性による検出（授乳中）"
    return {"is_postpartum": is_postpartum, "is_breastfeeding": is_breastfeeding, "reason": reason}


def calculate_completeness_penalty(missing_info_result: Dict) -> Dict:
    """不足情報による減点を計算"""
    if not missing_info_result.get("has_missing_info", False):
        return {"completeness_penalty": 0.0, "missing_fields_detail": {}, "max_penalty_reached": False}
    missing_fields = missing_info_result.get("missing_fields", [])
    if not missing_fields:
        return {"completeness_penalty": 0.0, "missing_fields_detail": {}, "max_penalty_reached": False}
    missing_fields_detail = {}
    total_penalty = 0.0
    max_penalty = 0.15
    for field in missing_fields:
        penalty = PENALTY_MAP.get(field, 0.0)
        if penalty > 0:
            missing_fields_detail[field] = penalty
            total_penalty += penalty
    max_penalty_reached = total_penalty >= max_penalty
    completeness_penalty = min(total_penalty, max_penalty)
    if logger.level <= logging.DEBUG:
        logger.debug(f"不足情報減点計算: missing_fields={missing_fields}, total_penalty={total_penalty:.3f}, capped_penalty={completeness_penalty:.3f}, max_reached={max_penalty_reached}")
    return {"completeness_penalty": completeness_penalty, "missing_fields_detail": missing_fields_detail, "max_penalty_reached": max_penalty_reached}
