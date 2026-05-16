"""Concierge 向けキーワード候補プローブ（確定は meta_triage / 完全一致ゲート）"""
from __future__ import annotations

import re
from typing import List

_CHITCHAT_CANDIDATE_PATTERNS = (
    re.compile(r"^(今日|きょう).{0,8}(天気|暑|寒)"),
    re.compile(r"^(暇|ひま|退屈)"),
    re.compile(r"^(面白|おもしろ|笑)"),
    re.compile(r"^(元気|げんき)"),
)


def probe_concierge_keyword_candidates(user_text: str) -> List[str]:
    text = (user_text or "").strip()
    if not text:
        return []
    candidates: List[str] = []
    for pat in _CHITCHAT_CANDIDATE_PATTERNS:
        if pat.search(text):
            candidates.append("concierge_chitchat")
            break
    if len(text) <= 30 and "?" not in text and "？" not in text:
        if any(w in text for w in ("天気", "暇", "つまら", "冗談", "ジョーク", "元気")):
            if "concierge_chitchat" not in candidates:
                candidates.append("concierge_chitchat")
    return candidates
