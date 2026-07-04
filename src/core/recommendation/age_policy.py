"""年齢未入力時の推奨ポリシー（RECO_AGE_POLICY_V2）。"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

_AGE_RESTRICTION_RE = re.compile(r"(\d+)歳")

AGE_UNKNOWN_NOTICE_HEADER = "【年齢未確認のご注意】"
AGE_UNKNOWN_NOTICE_BODY = (
    "年齢が未入力のため、表示は成人向けの参考情報です。"
    "各製品のパッケージ表示の年齢制限を必ずご確認のうえご使用ください。"
    "お子さまの場合は、年齢をお知らせいただくか、薬剤師・医師にご相談ください。"
)


def parse_min_age_years(age_restriction: Any) -> Optional[int]:
    text = str(age_restriction or "").strip()
    if not text:
        return None
    match = _AGE_RESTRICTION_RE.search(text)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def medicines_with_age_restriction_gte(
    medicines: List[Dict[str, Any]],
    *,
    min_years: int = 12,
) -> List[Dict[str, Any]]:
    restricted: list[Dict[str, Any]] = []
    for med in medicines or []:
        min_age = parse_min_age_years(med.get("age_restriction"))
        if min_age is not None and min_age >= min_years:
            restricted.append(med)
    return restricted


def build_age_unknown_notice(medicines: List[Dict[str, Any]]) -> Optional[str]:
    restricted = medicines_with_age_restriction_gte(medicines, min_years=12)
    if not restricted:
        return None
    names = [
        str(m.get("product_name") or m.get("name") or "").strip()
        for m in restricted[:5]
    ]
    names = [n for n in names if n]
    lines = [AGE_UNKNOWN_NOTICE_BODY]
    if names:
        lines.append("年齢制限の記載がある製品: " + "、".join(names))
    return "\n".join(lines)


def build_age_unknown_warnings(
    medicines: List[Dict[str, Any]],
    user_info: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """年齢未入力かつ 12 歳以上制限薬がある場合、警告 dict を返す（P1-4）。"""
    if (user_info or {}).get("age") is not None:
        return None
    notice = build_age_unknown_notice(medicines)
    if not notice:
        return None
    restricted = medicines_with_age_restriction_gte(medicines, min_years=12)
    names = [
        str(m.get("product_name") or m.get("name") or "").strip()
        for m in restricted
    ]
    return {
        "age_policy_notice": notice,
        "restricted_medicines": [n for n in names if n],
    }


def prepend_age_notice_to_usage_notes(usage_notes: str, notice: str) -> str:
    base = (usage_notes or "").strip()
    if not notice:
        return base
    block = f"{AGE_UNKNOWN_NOTICE_HEADER}\n{notice}"
    if AGE_UNKNOWN_NOTICE_HEADER in base:
        return base
    if base:
        return f"{block}\n\n{base}"
    return block


def apply_age_unknown_policy_to_result(
    recommendation_result: Dict[str, Any],
    user_info: Optional[Dict[str, Any]],
) -> None:
    """年齢未入力かつ v2 ON 時、警告文案を recommendation_result に付与する。"""
    try:
        from config.llm_flags import is_reco_age_policy_v2_enabled
    except ImportError:
        return
    if not is_reco_age_policy_v2_enabled():
        return
    if (user_info or {}).get("age") is not None:
        return
    medicines = recommendation_result.get("recommended_medicines") or []
    warnings = build_age_unknown_warnings(medicines, user_info)
    if not warnings:
        return
    recommendation_result["age_policy_notice"] = warnings["age_policy_notice"]
    recommendation_result["restricted_medicines"] = warnings["restricted_medicines"]
    recommendation_result["usage_notes"] = prepend_age_notice_to_usage_notes(
        recommendation_result.get("usage_notes") or "",
        warnings["age_policy_notice"],
    )
