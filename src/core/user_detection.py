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
    """ユーザー要望（nlu_result.user_preferences 優先、未設定時は安全キーワードのみ）。"""
    from src.core.preference_merge import default_user_preferences, merge_user_preferences

    if nlu_result and nlu_result.get("user_preferences"):
        return dict(nlu_result["user_preferences"])

    text = preference_context_text(user_message or "", user_info)
    if not text.strip():
        return default_user_preferences()
    return merge_user_preferences({}, text, nlu_result)


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
