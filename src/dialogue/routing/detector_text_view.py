"""Two-stage text views for D2-b (R7-B).

1. canonical_normalize (canon-v1): display / SessionOps classification
2. detector_comparison_view: safety/policy detector input only — never
   written back to user-visible text or general logs.

Transform inventory (detector view only):

| Code points | Action | Detectors | FP risk | Lang | Observability |
| --- | --- | --- | --- | --- | --- |
| U+200B..U+200D, U+2060, U+FEFF, U+00AD | strip | all safety/policy | low | none | stripped_ignorable_count |
| U+200E, U+200F, U+202A..U+202E | strip | same | low | bidi | stripped_ignorable_count |
| other Unicode category Cf | strip | same | low | format | stripped_ignorable_count |
| WS between CJK (incl. U+3000, newline) | remove | crisis/exam/rx/controlled/injection | medium | JA glue | cjk_internal_ws_collapsed |
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from src.dialogue.routing.canonical_normalize import NORM_ALGO_VERSION, canonical_normalize

DETECTOR_VIEW_VERSION = "detector-view-v1"

_STRIP_CPS = frozenset(
    {
        0x00AD,  # soft hyphen
        0x200B,  # ZWSP
        0x200C,  # ZWNJ
        0x200D,  # ZWJ
        0x200E,  # LRM
        0x200F,  # RLM
        0x202A,  # LRE
        0x202B,  # RLE
        0x202C,  # PDF
        0x202D,  # LRO
        0x202E,  # RLO
        0x2060,  # WJ
        0xFEFF,  # BOM / ZWNBSP
    }
)

_CJK_WS_RE = re.compile(
    r"(?<=[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff])"
    r"[\s\u3000]+"
    r"(?=[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff])"
)

_WS_RE = re.compile(r"\s+", re.UNICODE)


@dataclass(frozen=True)
class DetectorViewResult:
    text: str
    stripped_ignorable_count: int
    cjk_internal_ws_collapsed: bool
    had_evasion_residue: bool
    version: str = DETECTOR_VIEW_VERSION


def has_evasion_residue(text: str | None) -> bool:
    """True if text contains strip targets or CJK-internal whitespace."""
    if not text:
        return False
    for ch in text:
        cp = ord(ch)
        if cp in _STRIP_CPS or unicodedata.category(ch) == "Cf":
            return True
    return bool(_CJK_WS_RE.search(text))


def build_detector_comparison_view(source: str | None) -> DetectorViewResult:
    """Build detector-only comparison string. Does not mutate display text."""
    base = "" if source is None else str(source)
    stripped = 0
    buf: list[str] = []
    for ch in base:
        cp = ord(ch)
        if cp in _STRIP_CPS or unicodedata.category(ch) == "Cf":
            stripped += 1
            continue
        buf.append(ch)
    text = "".join(buf)
    collapsed = bool(_CJK_WS_RE.search(text))
    if collapsed:
        text = _CJK_WS_RE.sub("", text)
    return DetectorViewResult(
        text=text,
        stripped_ignorable_count=stripped,
        cjk_internal_ws_collapsed=collapsed,
        had_evasion_residue=stripped > 0 or collapsed,
    )


def prepare_text_views(raw: str | None) -> tuple[str, DetectorViewResult]:
    """Return (canonical for display/SessionOps, detector view for safety/policy)."""
    canonical = canonical_normalize(raw)
    nfc_raw = unicodedata.normalize("NFC", "" if raw is None else str(raw))
    dv = build_detector_comparison_view(nfc_raw)
    final = _WS_RE.sub(" ", dv.text.strip())
    residue = (
        dv.had_evasion_residue
        or has_evasion_residue(nfc_raw)
        or has_evasion_residue(canonical)
    )
    return canonical, DetectorViewResult(
        text=final,
        stripped_ignorable_count=dv.stripped_ignorable_count,
        cjk_internal_ws_collapsed=dv.cjk_internal_ws_collapsed,
        had_evasion_residue=residue,
        version=DETECTOR_VIEW_VERSION,
    )


__all__ = [
    "DETECTOR_VIEW_VERSION",
    "DetectorViewResult",
    "NORM_ALGO_VERSION",
    "build_detector_comparison_view",
    "has_evasion_residue",
    "prepare_text_views",
]
