"""
診断名検出後の Physical / OTC 推奨可否（オーナー方針・medicine-recommendation-advisor 準拠）
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

CONSULT_DISCLAIMER = "かかりつけ医・薬剤師にご相談ください。"

TYPE_STRICTNESS = {"serious": 0, "mental_health": 1, "chronic": 2, "other": 3}

CHRONIC_HEADACHE_DENY = (
    "糖尿病",
    "慢性腎臓病",
    "腎不全",
    "透析",
    "心不全",
    "肝硬変",
    "肝硬化",
)

CHRONIC_HEADACHE_ALLOW = ("高血圧", "本態性高血圧", "高血圧症")

INSOMNIA_DIAGNOSIS = ("不眠症", "慢性不眠症", "原発性不眠症")

SLEEP_SYMPTOM_KEYWORDS = ("不眠", "眠れない", "眠れません", "睡眠", "寝付き")

DEPRESSION_KEYWORDS = ("うつ病", "鬱病", "憂鬱症", "抑うつ", "うつ")

OTC_EXPLORATION_KEYWORDS = (
    "市販",
    "市販薬",
    "ドラッグストア",
    "薬局",
    "何の薬",
    "どの薬",
    "おすすめの薬",
)

SEIZURE_KEYWORDS = ("発作", "痙攣", "引きつけ")

IBD_KEYWORDS = ("潰瘍性大腸炎", "クローン病", "炎症性腸疾患", "IBD")


@dataclass
class PhysicalRecommendationDecision:
    allowed: bool
    reason: str = ""
    block_code: str = ""


def append_consult_disclaimer(message: str) -> str:
    if not message:
        return CONSULT_DISCLAIMER
    if CONSULT_DISCLAIMER in message:
        return message
    return message.rstrip() + f"\n\n※{CONSULT_DISCLAIMER}"


def strictest_diagnosis_type(types: List[str]) -> Optional[str]:
    if not types:
        return None
    return min(types, key=lambda t: TYPE_STRICTNESS.get(t, 99))


def _contains_any(text: str, keywords: tuple) -> bool:
    return any(k in text for k in keywords)


def _medical_history_text(user_attributes: Dict[str, Any]) -> str:
    history = user_attributes.get("medical_history") or []
    if isinstance(history, list):
        return " ".join(str(h) for h in history)
    return str(history or "")


def _is_pregnant(user_attributes: Dict[str, Any], text: str) -> bool:
    if user_attributes.get("pregnant") is True:
        return True
    if user_attributes.get("pregnant") is False:
        return False
    if "妊娠中" in text or "妊婦" in text:
        return True
    if "妊娠" in text and "非妊娠" not in text and "妊娠していない" not in text:
        return True
    return False


def _is_pediatric(user_attributes: Dict[str, Any]) -> bool:
    age = user_attributes.get("age")
    if age is None:
        return False
    try:
        return int(age) < 15
    except (TypeError, ValueError):
        return False


def _has_headache(text: str) -> bool:
    return "頭痛" in text


def _has_abdominal_pain(text: str) -> bool:
    return any(k in text for k in ("腹痛", "お腹が痛", "腹部の痛み", "胃痛"))


def _has_insomnia_diagnosis(text: str, user_attributes: Dict[str, Any]) -> bool:
    combined = text + " " + _medical_history_text(user_attributes)
    return _contains_any(combined, INSOMNIA_DIAGNOSIS)


def _has_sleep_symptom(text: str) -> bool:
    return _contains_any(text, SLEEP_SYMPTOM_KEYWORDS)


def _asks_otc_sleep_medicine(text: str) -> bool:
    if not _contains_any(text, ("睡眠薬", "眠れる薬", "寝る薬")):
        return False
    return _contains_any(text, OTC_EXPLORATION_KEYWORDS + ("教えて", "探して", "欲しい", "ください"))


def merge_diagnosis_session(
    session: Any,
    diagnosis_type: Optional[str],
    diagnosis_response: Optional[Dict[str, Any]],
) -> None:
    """診断検出時にセッションへ diagnosis_session_active / diagnosis_block_types を保存。"""
    if "user_attributes" not in session:
        session["user_attributes"] = {}
    ua = session["user_attributes"]
    types: List[str] = list(ua.get("diagnosis_block_types") or [])
    for t in (diagnosis_response or {}).get("diagnosis_block_types") or []:
        if t and t not in types:
            types.append(t)
    if diagnosis_type and diagnosis_type not in types:
        types.append(diagnosis_type)
    ua["diagnosis_block_types"] = types
    ua["diagnosis_session_active"] = True
    if diagnosis_response:
        ua["last_diagnosis_response"] = {
            k: diagnosis_response.get(k)
            for k in (
                "selected_diagnosis",
                "has_symptom",
                "has_treatment",
                "has_side_effect",
                "diagnosis_only",
                "high_risk_context",
            )
        }
    session["user_attributes"] = ua
    if hasattr(session, "modified"):
        session.modified = True


def clear_diagnosis_session_flags(user_attributes: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """新規セッション用の user_attributes 初期値。"""
    base = dict(user_attributes or {})
    base.pop("diagnosis_session_active", None)
    base.pop("diagnosis_block_types", None)
    base.pop("last_diagnosis_response", None)
    return base


def evaluate_physical_recommendation(
    message: str,
    user_attributes: Optional[Dict[str, Any]] = None,
    diagnosis_response: Optional[Dict[str, Any]] = None,
) -> PhysicalRecommendationDecision:
    """
    ルールベース推奨（Physical）を実行してよいか判定する。
    許可時のみ rule_based_medicine_recommendation を呼ぶ。
    """
    text = (message or "").strip()
    ua = dict(user_attributes or {})

    if diagnosis_response is None:
        from src.core.diagnosis_detection import is_diagnosis_term

        is_dx, dx_type, diagnosis_response = is_diagnosis_term(text)
        if not is_dx:
            if not ua.get("diagnosis_session_active"):
                return PhysicalRecommendationDecision(allowed=True, reason="no_diagnosis")
            diagnosis_response = ua.get("last_diagnosis_response") or {}
        else:
            block_types = list(
                diagnosis_response.get("diagnosis_block_types")
                or ua.get("diagnosis_block_types")
                or ([dx_type] if dx_type else [])
            )
    else:
        block_types = list(
            diagnosis_response.get("diagnosis_block_types")
            or ua.get("diagnosis_block_types")
            or []
        )

    if not block_types and not ua.get("diagnosis_session_active"):
        return PhysicalRecommendationDecision(allowed=True, reason="no_active_session")

    block_types = block_types or list(ua.get("diagnosis_block_types") or [])
    strict = strictest_diagnosis_type(block_types)
    dr = diagnosis_response or ua.get("last_diagnosis_response") or {}

    has_side_effect = bool(dr.get("has_side_effect"))
    high_risk = bool(dr.get("high_risk_context"))
    diagnosis_only = bool(dr.get("diagnosis_only"))
    has_treatment = bool(dr.get("has_treatment")) or bool(ua.get("treatment_mention"))
    has_symptom = bool(dr.get("has_symptom")) or _has_sleep_symptom(text) or _has_headache(text)

    if has_side_effect:
        return PhysicalRecommendationDecision(
            allowed=False, reason="side_effect", block_code="side_effect"
        )
    if high_risk:
        return PhysicalRecommendationDecision(
            allowed=False, reason="high_risk_context", block_code="high_risk"
        )
    if diagnosis_only:
        return PhysicalRecommendationDecision(
            allowed=False, reason="diagnosis_only", block_code="diagnosis_only"
        )

    if strict == "serious":
        return PhysicalRecommendationDecision(
            allowed=False, reason="serious", block_code="serious"
        )

    if has_treatment:
        if _has_insomnia_diagnosis(text, ua) and not _is_pediatric(ua):
            return PhysicalRecommendationDecision(
                allowed=False,
                reason="insomnia_on_treatment",
                block_code="insomnia_treatment",
            )
        if "mental_health" in block_types or "chronic" in block_types or "other" in block_types:
            return PhysicalRecommendationDecision(
                allowed=False, reason="on_treatment", block_code="on_treatment"
            )

    if "chronic" in block_types and _has_headache(text):
        combined = text + " " + _medical_history_text(ua)
        if _is_pregnant(ua, text):
            return PhysicalRecommendationDecision(
                allowed=False, reason="hypertension_pregnancy", block_code="chronic_headache"
            )
        if _contains_any(combined, CHRONIC_HEADACHE_DENY):
            return PhysicalRecommendationDecision(
                allowed=False, reason="chronic_headache_deny", block_code="chronic_headache"
            )
        if _contains_any(combined, CHRONIC_HEADACHE_ALLOW):
            return PhysicalRecommendationDecision(
                allowed=True, reason="hypertension_headache_ok", block_code=""
            )
        return PhysicalRecommendationDecision(
            allowed=False, reason="chronic_headache_default", block_code="chronic_headache"
        )

    if "other" in block_types:
        if _contains_any(text, ("てんかん", "癫痫")) and _contains_any(text, SEIZURE_KEYWORDS):
            return PhysicalRecommendationDecision(
                allowed=False, reason="epilepsy_seizure", block_code="epilepsy"
            )
        if _contains_any(text, IBD_KEYWORDS) and _has_abdominal_pain(text):
            return PhysicalRecommendationDecision(
                allowed=False, reason="ibd_abdominal", block_code="ibd"
            )

    if "mental_health" in block_types or strict == "mental_health":
        if _contains_any(text, DEPRESSION_KEYWORDS) and _asks_otc_sleep_medicine(text):
            return PhysicalRecommendationDecision(
                allowed=False, reason="depression_sleep_otc", block_code="depression_sleep"
            )
        if _contains_any(text, DEPRESSION_KEYWORDS) and _has_sleep_symptom(text):
            return PhysicalRecommendationDecision(
                allowed=False, reason="depression_insomnia", block_code="depression_insomnia"
            )
        if _has_insomnia_diagnosis(text, ua):
            if _is_pediatric(ua):
                return PhysicalRecommendationDecision(
                    allowed=False, reason="pediatric_insomnia", block_code="pediatric"
                )
            if has_symptom or _contains_any(text, OTC_EXPLORATION_KEYWORDS):
                return PhysicalRecommendationDecision(
                    allowed=True, reason="insomnia_adult_ok", block_code=""
                )

    if ua.get("diagnosis_session_active") and strict in ("mental_health", "chronic", "other"):
        if _has_sleep_symptom(text) and not _has_insomnia_diagnosis(text, ua):
            if _contains_any(text, DEPRESSION_KEYWORDS):
                return PhysicalRecommendationDecision(
                    allowed=False, reason="depression_symptom", block_code="mental_health"
                )
            return PhysicalRecommendationDecision(
                allowed=True, reason="sleep_counseling_path", block_code=""
            )

    if strict in ("mental_health", "other") and has_symptom:
        return PhysicalRecommendationDecision(
            allowed=False, reason="mental_or_other_default", block_code=strict or ""
        )

    return PhysicalRecommendationDecision(allowed=True, reason="default_allow", block_code="")


def physical_block_user_message(decision: PhysicalRecommendationDecision) -> str:
    """Physical ブロック時にユーザーへ返す短文（日本語）。"""
    messages = {
        "serious": (
            "悪性腫瘍などの重篤な疾患がおありの場合、市販薬の選択は主治医の指示に従ってください。"
            "具体的な症状についてお聞かせいただければ、一般的なご案内は可能です。"
        ),
        "side_effect": "お薬の副作用については、処方医または薬剤師へのご相談を優先してください。",
        "high_risk": "検査中・疑いの状態では、自己判断での市販薬使用はお控えください。",
        "diagnosis_only": "診断名のみのご入力がありました。具体的な症状を教えていただくとご案内しやすくなります。",
        "on_treatment": "治療中のお薬との飲み合わせがあります。市販薬を使う前に医師・薬剤師にご相談ください。",
        "insomnia_treatment": "不眠症で処方薬を服用中の場合、市販の睡眠薬は重複や相互作用の恐れがあります。かかりつけ医にご相談ください。",
        "chronic_headache": "お持ちの疾患により、頭痛薬の市販選択には注意が必要です。医師・薬剤師にご相談ください。",
        "hypertension_pregnancy": "妊娠中の頭痛は市販薬の選択に制限があります。産婦人科医にご相談ください。",
        "epilepsy": "発作の疑いがある場合は、至急医療機関を受診してください。",
        "ibd": "炎症性腸疾患がある場合、腹痛への市販薬は慎重に選ぶ必要があります。医師にご相談ください。",
        "depression_sleep": "うつ病の治療中に市販の睡眠薬を併用するのは危険な場合があります。主治医にご相談ください。",
        "depression_insomnia": "うつ病に伴う不眠は、市販睡眠薬より専門医の診察を優先してください。",
        "pediatric": "お子さまの不眠への市販睡眠薬は、原則お勧めできません。小児科医にご相談ください。",
        "mental_health": "精神疾患のお薬との相互作用があります。市販薬は医師・薬剤師にご相談のうえお選びください。",
    }
    code = decision.block_code or decision.reason
    body = messages.get(code, messages.get(decision.reason, messages["mental_health"]))
    return append_consult_disclaimer(body)
