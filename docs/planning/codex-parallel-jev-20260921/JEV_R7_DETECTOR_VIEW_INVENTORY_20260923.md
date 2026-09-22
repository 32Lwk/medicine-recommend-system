# R7-B Detector Comparison View — Transform Inventory

| Code points | Action | Detectors | FP risk | Language | Observability field |
| --- | --- | --- | --- | --- | --- |
| U+200B ZWSP, U+200C ZWNJ, U+200D ZWJ, U+2060 WJ, U+FEFF BOM, U+00AD SHY | strip | crisis, exam, rx, controlled, injection, emergency, known_attack | low | none | `stripped_ignorable_count` |
| U+200E/F, U+202A–U+202E bidi | strip | same | low | bidi layout | same |
| Other Unicode category `Cf` | strip | same | low | format chars | same |
| Whitespace (incl. U+3000, `\n`) **between CJK** | remove | same | medium (rare spaced CJK) | JA phrase glue | `cjk_internal_ws_collapsed` |
| Remaining WS | collapse to single space (like canon) | same | low | display unchanged | detector view only |

**Non-goals**: do not strip from `canonical_normalize` / user display; do not write detector view to logs as raw medical text.

**Fail-closed**: if evasion residue remains and SessionOps detected → `evasion_fail_closed=True` → `is_pure_session_ops=False` even if detectors miss.
