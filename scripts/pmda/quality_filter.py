"""PMDA 行の品質フィルタ（merge 前 reject）。"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from scripts.pmda.common import normalize_text

_BOILERPLATE = re.compile(
    r"当ウェブサイトを快適にご覧いただくには|"
    r"JavaScript設定を有効|"
    r"Pmda\s*独立行政法人\s*医薬品医療機器総合機構|"
    r"標準\s*大\s*特大\s*医療用医薬品\s*詳細表示"
)

_WRONG_SECTION = re.compile(
    r"§18|18\.\d|17\.\s*臨床成績|薬効薬理|薬理作用|作用機序|"
    r"2\.\s*禁忌|3\.\s*組成|組成・性状"
)

_SECTION10 = re.compile(r"10\.|併用注意|併用禁忌|相互作用")
_SECTION11 = re.compile(r"11\.|副作用|重大な副作用|有害事象")

_KEYWORD_ONLY = re.compile(
    r"^(?:眠気|発疹|ショック|胃|吐|めまい|下痢|肝)(?:[、,・]|(?:$))+$"
)


def reject_reason_interaction(row: Dict[str, Any]) -> str:
    text = normalize_text(str(row.get("説明") or ""))
    if len(text) < 30:
        return "too_short"
    if _BOILERPLATE.search(text):
        return "html_boilerplate"
    if _WRONG_SECTION.search(text) and not _SECTION10.search(text):
        return "wrong_section"
    if not _SECTION10.search(text) and not re.search(r"併用|相互作用|機序", text):
        return "missing_section10"
    return ""


def reject_reason_side_effect(row: Dict[str, Any]) -> str:
    text = normalize_text(str(row.get("副作用症状") or ""))
    if len(text) < 50:
        if _KEYWORD_ONLY.match(text) or len(text) < 15:
            return "truncated_keywords"
        return "too_short"
    if _BOILERPLATE.search(text):
        return "html_boilerplate"
    if _WRONG_SECTION.search(text) and not _SECTION11.search(text):
        return "wrong_section"
    if not _SECTION11.search(text):
        return "missing_section11"
    return ""


def filter_interactions(rows: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], Dict[str, int]]:
    kept: List[Dict[str, Any]] = []
    stats: Dict[str, int] = {"accepted": 0, "rejected": 0}
    for row in rows:
        reason = reject_reason_interaction(row)
        if reason:
            stats["rejected"] += 1
            stats[f"reject_{reason}"] = stats.get(f"reject_{reason}", 0) + 1
            continue
        kept.append(row)
        stats["accepted"] += 1
    return kept, stats


def filter_side_effects(rows: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], Dict[str, int]]:
    kept: List[Dict[str, Any]] = []
    stats: Dict[str, int] = {"accepted": 0, "rejected": 0}
    for row in rows:
        reason = reject_reason_side_effect(row)
        if reason:
            stats["rejected"] += 1
            stats[f"reject_{reason}"] = stats.get(f"reject_{reason}", 0) + 1
            continue
        kept.append(row)
        stats["accepted"] += 1
    return kept, stats
