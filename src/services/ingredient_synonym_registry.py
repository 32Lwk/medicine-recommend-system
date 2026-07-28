"""成分・ブランド同義語レジストリ — RAG build / retrieve / brand resolve 共通。"""
from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple

_ROOT = Path(__file__).resolve().parents[2]
_DATA_DIR = _ROOT / "data"
_DICT_PATH = _DATA_DIR / "ingredient_dictionary.json"
_OPTIONAL_SYN_PATH = _DATA_DIR / "ingredient_synonyms.json"


def normalize_token(text: str) -> str:
    return unicodedata.normalize("NFKC", (text or "").strip())


@lru_cache(maxsize=1)
def load_ingredient_dictionary() -> Dict[str, dict]:
    if not _DICT_PATH.is_file():
        return {}
    try:
        raw = json.loads(_DICT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


@lru_cache(maxsize=1)
def _optional_synonym_file() -> Dict[str, Tuple[str, ...]]:
    if not _OPTIONAL_SYN_PATH.is_file():
        return {}
    try:
        raw = json.loads(_OPTIONAL_SYN_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, Tuple[str, ...]] = {}
    for key, val in raw.items():
        canonical = normalize_token(str(key))
        if not canonical:
            continue
        syns: List[str] = []
        if isinstance(val, list):
            syns = [normalize_token(str(s)) for s in val if s]
        elif isinstance(val, dict):
            raw_syns = val.get("synonyms") or []
            if isinstance(raw_syns, list):
                syns = [normalize_token(str(s)) for s in raw_syns if s]
        if syns:
            out[canonical] = tuple(s for s in syns if s and s != canonical)
    return out


@lru_cache(maxsize=1)
def _brand_resolve_aliases() -> Tuple[Tuple[str, str], ...]:
    """(alias, canonical_or_hint) — brand hints と ingredient_aliases。"""
    from src.services.medicine_brand_resolve import BRAND_RESOLVE_RULES

    pairs: List[Tuple[str, str]] = []
    for rule in BRAND_RESOLVE_RULES:
        target = rule.canonical_product or (rule.hints[0] if rule.hints else "")
        if not target:
            continue
        for hint in rule.hints:
            h = normalize_token(hint)
            if h:
                pairs.append((h, normalize_token(target)))
        for ing in rule.ingredient_aliases:
            i = normalize_token(ing)
            if i:
                pairs.append((i, i))
    return tuple(pairs)


@lru_cache(maxsize=1)
def alias_to_canonical() -> Dict[str, str]:
    """任意表記 → canonical（最長一致用に alias 長さ降順キーも export）。"""
    mapping: Dict[str, str] = {}

    for key, entry in load_ingredient_dictionary().items():
        canonical = normalize_token(str(entry.get("canonical_name") or key))
        if not canonical:
            continue
        mapping[canonical] = canonical
        for syn in entry.get("synonyms") or []:
            s = normalize_token(str(syn))
            if s:
                mapping.setdefault(s, canonical)

    for canonical, syns in _optional_synonym_file().items():
        mapping.setdefault(canonical, canonical)
        for syn in syns:
            mapping.setdefault(syn, canonical)

    for alias, target in _brand_resolve_aliases():
        mapping.setdefault(alias, target)

    for alias, target in brand_query_shorthands().items():
        mapping.setdefault(alias, target)

    return mapping


@lru_cache(maxsize=1)
def canonical_to_synonyms() -> Dict[str, Tuple[str, ...]]:
    """canonical → 同義語タプル（検索用テキスト注入）。"""
    out: Dict[str, Set[str]] = {}

    def _add(canonical: str, synonym: str) -> None:
        c = normalize_token(canonical)
        s = normalize_token(synonym)
        if not c or not s or c == s:
            return
        out.setdefault(c, set()).add(s)

    for key, entry in load_ingredient_dictionary().items():
        canonical = normalize_token(str(entry.get("canonical_name") or key))
        if not canonical:
            continue
        for syn in entry.get("synonyms") or []:
            _add(canonical, str(syn))

    for canonical, syns in _optional_synonym_file().items():
        for syn in syns:
            _add(canonical, syn)

    from src.services.medicine_brand_resolve import BRAND_RESOLVE_RULES

    for rule in BRAND_RESOLVE_RULES:
        for ing in rule.ingredient_aliases:
            canonical = normalize_token(ing)
            if not canonical:
                continue
            for hint in rule.hints:
                _add(canonical, hint)

    return {k: tuple(sorted(v)) for k, v in out.items()}


@lru_cache(maxsize=1)
def brand_query_shorthands() -> Dict[str, str]:
    """local_rag_query 用 — 略称 → 検索 prefix / canonical。"""
    from src.services.medicine_brand_resolve import MEDICINE_BRAND_HINTS

    shorthands: Dict[str, str] = {}
    for hint in MEDICINE_BRAND_HINTS:
        h = normalize_token(hint)
        if h:
            shorthands[h] = h
    shorthands.setdefault("ロキソ", "ロキソニン")
    shorthands.setdefault("ワルファリン", "ワーファリン")
    return shorthands


def split_ingredient_field(text: str) -> List[str]:
    import re

    parts = re.split(r"[\n\r、,/／・]+", text or "")
    out: List[str] = []
    seen: Set[str] = set()
    for part in parts:
        name = normalize_token(part)
        if len(name) < 2 or name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out


def lookup_synonyms_for_names(names: Sequence[str], *, max_items: int = 24) -> str:
    """metadata / MD 追記用 — カンマ区切り同義語。"""
    canon_map = canonical_to_synonyms()
    alias_map = alias_to_canonical()
    seen: Set[str] = set()
    collected: List[str] = []

    for raw in names:
        key = normalize_token(raw)
        if not key:
            continue
        canonical = alias_map.get(key, key)
        for syn in canon_map.get(canonical, ()):
            if syn not in seen and syn != key:
                seen.add(syn)
                collected.append(syn)
        for syn in canon_map.get(key, ()):
            if syn not in seen and syn != key:
                seen.add(syn)
                collected.append(syn)
        if canonical != key and canonical not in seen:
            seen.add(canonical)
            collected.append(canonical)

    return ",".join(collected[:max_items])


def brand_hints_for_product(product_name: str) -> Tuple[str, ...]:
    """製品名から BRAND_RESOLVE ルールの hints / preferred を同義語として返す。"""
    from src.services.medicine_brand_resolve import BRAND_RESOLVE_RULES

    name = normalize_token(product_name)
    if not name:
        return ()
    hints: Set[str] = set()
    for rule in BRAND_RESOLVE_RULES:
        matched = False
        if rule.canonical_product and name == normalize_token(rule.canonical_product):
            matched = True
        elif rule.product_prefix and name.startswith(normalize_token(rule.product_prefix)):
            matched = True
        elif any(name.startswith(normalize_token(h)) for h in rule.hints):
            matched = True
        elif rule.product_name_contains and any(
            normalize_token(c) in name for c in rule.product_name_contains
        ):
            matched = True
        if matched:
            for h in rule.hints:
                hints.add(normalize_token(h))
    return tuple(sorted(h for h in hints if h))


def expand_query_with_aliases(query: str) -> str:
    """retrieve クエリに canonical / 同義語を付加（既存語は重複しない）。"""
    text = normalize_token(query)
    if not text:
        return query
    alias_map = alias_to_canonical()
    extras: List[str] = []
    seen = set(_tokenize_simple(text))

    # 長い alias から部分一致（brand hint 誤爆抑制）
    for alias in sorted(alias_map.keys(), key=len, reverse=True):
        if len(alias) < 2 or alias not in text:
            continue
        canonical = alias_map[alias]
        if canonical not in seen:
            seen.add(canonical)
            extras.append(canonical)
        for syn in canonical_to_synonyms().get(canonical, ()):
            if syn not in seen:
                seen.add(syn)
                extras.append(syn)

    if not extras:
        return query
    return f"{query} {' '.join(extras[:12])}".strip()


def _tokenize_simple(text: str) -> List[str]:
    import re

    return [m.group(0) for m in re.finditer(r"[\w一-龥ぁ-んァ-ヶ]{2,}", text)]


def clear_caches() -> None:
    load_ingredient_dictionary.cache_clear()
    _optional_synonym_file.cache_clear()
    _brand_resolve_aliases.cache_clear()
    alias_to_canonical.cache_clear()
    canonical_to_synonyms.cache_clear()
    brand_query_shorthands.cache_clear()
