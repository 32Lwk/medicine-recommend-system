"""Canonical text normalization for D2-b preflight (canon-v1).

Side-effect free. Must NOT strip danger/policy markers or sanitize security.
"""
from __future__ import annotations

import re
import unicodedata

NORM_ALGO_VERSION = "canon-v1"

_WS_RE = re.compile(r"\s+", re.UNICODE)


def canonical_normalize(raw: str | None) -> str:
    """NFC + edge strip + collapse internal whitespace to single ASCII space.

    Does not delete policy/crisis/security substrings or zero-width chars
    (zero-width left intact so residual can track evasion — see tests).
    """
    text = "" if raw is None else str(raw)
    text = unicodedata.normalize("NFC", text)
    text = text.strip()
    text = _WS_RE.sub(" ", text)
    return text
