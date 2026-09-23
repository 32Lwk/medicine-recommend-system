"""Minimal free-text PII redaction for Jev outbound payload (defense in depth).

Heuristic only — not a substitute for DPA/ZDR or payload minimization.
Fail-closed on unexpected errors (returns a short placeholder).

Order matters: high-specificity ID patterns run before phone/postal so digit
spans are not partially consumed (false negatives on LINE / MyNumber).
"""
from __future__ import annotations

import re
from typing import Tuple

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
# LINE userId-ish (U + 32 hex) — before phone (hex digits look numeric)
_LINE_USER_RE = re.compile(r"\bU[0-9a-fA-F]{32}\b")
_CREDITISH_RE = re.compile(r"(?<!\d)(?:\d[ -]*?){13,19}(?!\d)")
# MyNumber with mandatory hyphens (avoids eating leading 12 digits of a 16-digit card)
_MY_NUMBER_RE = re.compile(r"(?<!\d)\d{4}-\d{4}-\d{4}(?!\d)")
_LABELED_NAME_RE = re.compile(
    r"(?:氏名|名前|フルネーム|本名)\s*[:：は]\s*[^\s、。]{1,20}"
)
_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?81[-\s]?)?(?:0\d{1,4}[-\s]?\d{1,4}[-\s]?\d{3,4})(?!\d)"
)
_JP_PHONE_COMPACT = re.compile(r"(?<!\d)0\d{9,10}(?!\d)")
_INTL_PHONE_RE = re.compile(
    r"(?<!\d)\+\d{1,3}[\s.-]?(?:\(?\d{1,4}\)?[\s.-]?){2,4}\d{2,4}(?!\d)"
)
_POSTAL_RE = re.compile(r"(?:〒\s*\d{3}-?\d{4}|(?<!\d)\d{3}-\d{4}(?!\d))")
_JP_ADDRESS_RE = re.compile(
    r"(?:北海道|(?:東京|京都|大阪)府|(?:青森|岩手|宮城|秋田|山形|福島|茨城|栃木|群馬|"
    r"埼玉|千葉|神奈川|新潟|富山|石川|福井|山梨|長野|岐阜|静岡|愛知|三重|滋賀|兵庫|"
    r"奈良|和歌山|鳥取|島根|岡山|広島|山口|徳島|香川|愛媛|高知|福岡|佐賀|長崎|熊本|"
    r"大分|宮崎|鹿児島|沖縄)県)"
    r"[^\s、。]{0,40}?(?:市|区|町|村|郡)[^\s、。]{0,40}"
)


def redact_pii_text(text: str) -> Tuple[str, list[str]]:
    """Return redacted text and list of rule ids applied. Never raises."""
    if not text:
        return "", []
    out = str(text)
    hits: list[str] = []
    try:
        if _EMAIL_RE.search(out):
            out = _EMAIL_RE.sub("[REDACTED_EMAIL]", out)
            hits.append("email")
        if _LINE_USER_RE.search(out):
            out = _LINE_USER_RE.sub("[REDACTED_LINE_ID]", out)
            hits.append("line_user")
        if _CREDITISH_RE.search(out):
            out = _CREDITISH_RE.sub("[REDACTED_CARD]", out)
            hits.append("cardish")
        if _MY_NUMBER_RE.search(out):
            out = _MY_NUMBER_RE.sub("[REDACTED_ID_NUMBER]", out)
            hits.append("my_numberish")
        if _LABELED_NAME_RE.search(out):
            out = _LABELED_NAME_RE.sub("[REDACTED_NAME]", out)
            hits.append("labeled_name")
        if (
            _PHONE_RE.search(out)
            or _JP_PHONE_COMPACT.search(out)
            or _INTL_PHONE_RE.search(out)
        ):
            out = _PHONE_RE.sub("[REDACTED_PHONE]", out)
            out = _JP_PHONE_COMPACT.sub("[REDACTED_PHONE]", out)
            out = _INTL_PHONE_RE.sub("[REDACTED_PHONE]", out)
            hits.append("phone")
        if _POSTAL_RE.search(out):
            out = _POSTAL_RE.sub("[REDACTED_POSTAL]", out)
            hits.append("postal")
        if _JP_ADDRESS_RE.search(out):
            out = _JP_ADDRESS_RE.sub("[REDACTED_ADDRESS]", out)
            hits.append("jp_address")
    except Exception:
        return "[REDACTED_UNSAFE]", ["redact_error"]
    return out, hits
