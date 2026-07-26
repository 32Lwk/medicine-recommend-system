"""Medicine local RAG — カテゴリ別 deterministic ルーティング。"""
from __future__ import annotations

import csv
import logging
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
BUILD_MEDICINE = ROOT / "build" / "medicine"
DATA_DIR = ROOT / "data"

from src.services.local_rag_query import (
    expand_concepts,
    extract_brand_tokens,
    extract_coordination_pairs,
    normalize_text as _query_normalize,
    _explicit_substance_mention_count,
    _is_drug_like_token,
)

_CATEGORY_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "side_effect": ("副作用", "眠気", "眠く", "眠た", "眠な", "胃が", "吐き気", "キツ", "ぼーっ", "張っ", "きつ"),
}

_ALCOHOL_ALIASES = ("アルコール", "お酒", "酒")

_INGREDIENT_SYNONYMS: Dict[str, str] = {
    "ロキソニン": "ロキソプロフェン",
    "ロキソプロフェンナトリウム": "ロキソプロフェン",
    "ロキソプロフェンナトリウム水和物": "ロキソプロフェン",
    "ワルファリン": "ワーファリン",
    "タイレノール": "アセトアミノフェン",
    "カロナール": "アセトアミノフェン",
}

_CLASS_SLUGS = {
    "ssri": "ssri",
    "snri": "snri",
    "mao阻害薬": "mao阻害薬",
}

_TOKEN_RE = re.compile(r"[\w一-龥ぁ-んァ-ヶ]{2,}")


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", (text or "").strip())


def _canonical_ingredient(name: str) -> str:
    n = _normalize(name)
    if not n:
        return ""
    if n in _INGREDIENT_SYNONYMS:
        return _INGREDIENT_SYNONYMS[n]
    for suffix in (
        "ナトリウム水和物",
        "ナトリウム",
        "塩酸塩",
        "水和物",
        "マレイン酸塩",
    ):
        if n.endswith(suffix) and len(n) > len(suffix) + 1:
            n = n[: -len(suffix)]
            break
    if n in _INGREDIENT_SYNONYMS:
        return _INGREDIENT_SYNONYMS[n]
    upper = n.upper()
    if upper in ("SSRI", "SNRI"):
        return upper
    return n


def _slug_part(ingredient: str) -> str:
    n = _canonical_ingredient(ingredient)
    if n.upper() == "SSRI":
        return "ssri"
    if n.upper() == "SNRI":
        return "snri"
    return n


_MULTI_DRUG_INTENT = re.compile(
    r"併用|一緒|同時|同日|相互作用|飲んじゃ|飲んちゃ|処方.*(?:一緒|併用)|"
    r"一緒に(?:服用|飲|使)|"
    r"悪くない|心臓|ヤバ|やば|あかん"
)

# Medicine QA focus → Local RAG retrieve カテゴリ（ルール低信頼時の橋渡し）
_QA_FOCUS_TO_RAG_CATEGORY: Dict[str, str] = {
    "side_effect": "side_effect",
    "usage": "usage",
    "age": "age",
    "doping": "doping",
    "interaction": "interaction",
    "comparison": "comparison",
    "ingredient": "side_effect",
    "product_image": "usage",
}


def _category_from_qa_focuses(
    query: str,
    conversation_history: Optional[Sequence[Dict[str, Any]]] = None,
    *,
    recommended_medicines: Optional[Sequence[Any]] = None,
) -> str:
    """QA intent 層の focus を RAG category に写像（LLM 不要・低コスト）。"""
    try:
        from src.services.medicine_qa_routing import infer_medicine_qa_focuses

        recs: list[dict[str, Any]] = []
        for item in recommended_medicines or []:
            if isinstance(item, dict):
                recs.append(dict(item))
            elif isinstance(item, str) and item.strip():
                recs.append({"product_name": item.strip()})
        focuses = infer_medicine_qa_focuses(
            query,
            conversation_history=list(conversation_history or []),
            recommended_medicines=recs or None,
        )
        for focus in focuses:
            if focus == "general":
                continue
            mapped = _QA_FOCUS_TO_RAG_CATEGORY.get(focus)
            if mapped:
                return mapped
    except Exception:
        pass
    return ""


def infer_medicine_category(
    query: str,
    *,
    conversation_history: Optional[Sequence[Dict[str, Any]]] = None,
    recommended_medicines: Optional[Sequence[Any]] = None,
) -> str:
    explicit = _explicit_substance_mention_count(query)
    resolved_raw = _extract_ingredients_from_text(query, expand=False)
    if len(resolved_raw) >= 2:
        resolved = resolved_raw
    elif _MULTI_DRUG_INTENT.search(query):
        resolved = _extract_ingredients_from_text(query, expand=True)
    else:
        resolved = resolved_raw
    substance_count = max(explicit, len(resolved))

    cat_query = query
    if conversation_history:
        from src.services.local_rag_context import _history_user_texts, normalize_conversation_history

        prior = " ".join(_history_user_texts(normalize_conversation_history(conversation_history), max_turns=4))
        if prior:
            cat_query = f"{prior} {query}"

    from src.services.local_rag_query import infer_medicine_category_with_confidence
    from config.local_rag_config import category_llm_fallback_enabled

    cat, confidence = infer_medicine_category_with_confidence(
        query, mention_count=substance_count, context_text=cat_query if cat_query != query else ""
    )

    # ルール低信頼 / 未分類 → QA focus 層で補完（追加 LLM コストなし）
    if (not cat or confidence < 0.55) and conversation_history:
        focus_cat = _category_from_qa_focuses(
            query,
            conversation_history,
            recommended_medicines=recommended_medicines,
        )
        if focus_cat and (not cat or focus_cat != cat):
            return focus_cat

    if (
        category_llm_fallback_enabled()
        and confidence < 0.45
        and conversation_history
    ):
        from src.services.local_rag_context import build_contextual_retrieval_query, normalize_conversation_history

        rewritten = build_contextual_retrieval_query(
            query,
            normalize_conversation_history(conversation_history),
            use_llm=True,
        )
        if rewritten:
            cat2, conf2 = infer_medicine_category_with_confidence(
                rewritten, mention_count=substance_count
            )
            if conf2 > confidence:
                return cat2
    return cat


@lru_cache(maxsize=1)
def _load_interaction_ingredients() -> Tuple[str, ...]:
    path = DATA_DIR / "medicine_interactions.csv"
    if not path.is_file():
        return ()
    ingredients: set[str] = set()
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            a = _normalize(row.get("成分A") or "")
            b = _normalize(row.get("成分B") or "")
            if a:
                ingredients.add(a)
            if b:
                ingredients.add(b)
    return tuple(sorted(ingredients, key=len, reverse=True))


@lru_cache(maxsize=1)
def _load_side_effect_ingredients() -> Tuple[str, ...]:
    path = DATA_DIR / "medicine_side_effects.csv"
    if not path.is_file():
        return ()
    out: set[str] = set()
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            name = _normalize(row.get("成分名") or "")
            if name:
                out.add(name)
    return tuple(sorted(out, key=len, reverse=True))


@lru_cache(maxsize=256)
def _product_ingredients(product_name: str) -> Tuple[str, ...]:
    import pandas as pd

    path = DATA_DIR / "otc_medicine_data.csv"
    if not path.is_file() or not product_name:
        return ()
    try:
        df = pd.read_csv(path)
    except OSError:
        return ()
    name = _normalize(product_name)
    norm = df["製品名"].astype(str).apply(_normalize)
    row = df[norm == name]
    if row.empty and len(name) >= 2:
        prefixed = df[norm.str.startswith(name)]
        if not prefixed.empty:
            prefixed = prefixed.assign(_nlen=norm.str.len()).sort_values("_nlen")
            row = prefixed.iloc[[0]]
    if row.empty:
        for brand in extract_brand_tokens(name):
            prefixed = df[norm.str.startswith(_normalize(brand))]
            if not prefixed.empty:
                prefixed = prefixed.assign(_nlen=norm.str.len()).sort_values("_nlen")
                row = prefixed.iloc[[0]]
                break
    if row.empty:
        return ()
    raw = str(row.iloc[0].get("成分") or "")
    parts = [_canonical_ingredient(p) for p in re.split(r"[\n,、]+", raw) if p.strip()]
    return tuple(dict.fromkeys(p for p in parts if p))


def _extract_ingredients_from_text(
    text: str, *, include_brands: bool = True, expand: bool = True
) -> List[str]:
    cleaned = expand_concepts(text) if expand else _normalize(text)
    if not cleaned:
        return []
    found: List[str] = []
    for alias in _ALCOHOL_ALIASES:
        if alias in cleaned and "アルコール" not in found:
            found.append("アルコール")
    if re.search(r"ビール|酒|お酒", cleaned):
        if "アルコール" not in found:
            found.append("アルコール")
    for synonym, canonical in _INGREDIENT_SYNONYMS.items():
        if synonym in cleaned:
            canon = _canonical_ingredient(canonical)
            if canon and canon not in found:
                found.append(canon)
    if include_brands:
        for brand in extract_brand_tokens(cleaned):
            for ing in _product_ingredients(brand):
                if ing not in found:
                    found.append(ing)
    for coord in extract_coordination_pairs(cleaned):
        if not _is_drug_like_token(coord):
            continue
        for ing in _product_ingredients(coord):
            if ing not in found:
                found.append(ing)
        canon = _canonical_ingredient(coord)
        if canon and canon not in found:
            found.append(canon)
    for ing in _load_interaction_ingredients():
        if ing in cleaned:
            canon = _canonical_ingredient(ing)
            if canon and canon not in found:
                found.append(canon)
    for token in ("SSRI", "SNRI"):
        if re.search(rf"\b{re.escape(token)}\b", cleaned, re.I):
            if token not in found:
                found.append(token)
    if "MAO阻害薬" in cleaned and "MAO阻害薬" not in found:
        found.append("MAO阻害薬")
    if "NSAID" in cleaned.upper() and "NSAID" not in found:
        found.append("NSAID")
    return found


def _resolve_interaction_by_content(ingredients: Sequence[str]) -> Optional[Path]:
    if len(ingredients) < 2:
        return None
    inter_dir = BUILD_MEDICINE / "interactions"
    if not inter_dir.is_dir():
        return None
    unique = [_canonical_ingredient(i) for i in ingredients if i][:3]
    if len(unique) < 2:
        return None
    best: Optional[Path] = None
    best_hits = 0
    for md in inter_dir.glob("*.md"):
        stem = md.stem
        snippet = md.read_text(encoding="utf-8")[:800] if md.is_file() else ""
        hits = sum(
            1 for ing in unique[:2] if ing and (ing in stem or ing in snippet)
        )
        if hits > best_hits:
            best_hits = hits
            best = md
    if best and best_hits >= 2:
        return best
    return None


def _resolve_interaction_path(ingredients: Sequence[str]) -> Optional[Path]:
    if len(ingredients) < 2:
        return None
    inter_dir = BUILD_MEDICINE / "interactions"
    if not inter_dir.is_dir():
        return None
    unique = list(
        dict.fromkeys(_canonical_ingredient(i) for i in ingredients if i)
    )
    if len(unique) < 2:
        return None
    a, b = _slug_part(unique[0]), _slug_part(unique[1])
    for slug in (f"{a}-{b}", f"{b}-{a}"):
        path = inter_dir / f"{slug}.md"
        if path.is_file():
            return path
    # 3+ 成分: 先頭 2 つで試行
    for i in range(len(unique)):
        for j in range(i + 1, min(i + 4, len(unique))):
            x, y = _slug_part(unique[i]), _slug_part(unique[j])
            for slug in (f"{x}-{y}", f"{y}-{x}"):
                path = inter_dir / f"{slug}.md"
                if path.is_file():
                    return path
    return _resolve_interaction_by_content(unique)


def _resolve_side_effect_path(ingredient: str) -> Optional[Path]:
    ing = _normalize(ingredient)
    if not ing:
        return None
    base = BUILD_MEDICINE / "side_effects"
    if not base.is_dir():
        return None
    canon = _canonical_ingredient(ing)
    for slug in (canon, ing):
        if not slug:
            continue
        path = base / f"{slug}.md"
        if path.is_file():
            return path
    for known in _load_side_effect_ingredients():
        if known in ing or ing in known or known in canon or canon in known:
            path = base / f"{known}.md"
            if path.is_file():
                return path
    return None


@lru_cache(maxsize=1)
def _product_name_to_path() -> Dict[str, Path]:
    products_dir = BUILD_MEDICINE / "products"
    mapping: Dict[str, Path] = {}
    if not products_dir.is_dir():
        return mapping
    import json

    for meta_path in products_dir.glob("*.md.metadata.json"):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            attrs = meta.get("metadataAttributes") or {}
            pname = _normalize(str(attrs.get("product_name") or ""))
            if pname:
                md_path = meta_path.name.replace(".metadata.json", "")
                mapping[pname] = products_dir / md_path
        except (OSError, json.JSONDecodeError):
            continue
    return mapping


def _resolve_product_by_name(product_name: str) -> Optional[Path]:
    pname = _normalize(product_name)
    if not pname:
        return None
    mapping = _product_name_to_path()
    path = mapping.get(pname)
    if path and path.is_file():
        return path
    candidates: List[Tuple[int, Path]] = []
    for name, candidate in mapping.items():
        if name.startswith(pname) or pname.startswith(name):
            candidates.append((len(name), candidate))
    if not candidates:
        for name, candidate in mapping.items():
            if pname in name or name in pname:
                candidates.append((len(name), candidate))
    if candidates:
        candidates.sort(key=lambda x: x[0])
        best = candidates[0][1]
        if best.is_file():
            return best
    return None


def _resolve_doping_substance_path(query: str) -> Optional[Path]:
    doping_dir = BUILD_MEDICINE / "doping"
    if not doping_dir.is_dir():
        return None
    q = expand_concepts(query)
    substance_hints = (
        "プソイドエフェドリン",
        "エフェドリン",
        "メチルエフェドリン",
        "塩酸メチルエフェドリン",
        "カフェイン",
        "麻黄",
        "鼻薬",
        "点鼻",
    )
    if not any(h in q for h in substance_hints):
        return None
    best: Optional[Path] = None
    best_hits = 0
    for md in doping_dir.glob("*.md"):
        hits = 0
        text = md.read_text(encoding="utf-8") if md.is_file() else ""
        for token in _TOKEN_RE.findall(text[:400]):
            if len(token) >= 3 and token in q:
                hits += 1
        if hits > best_hits:
            best_hits = hits
            best = md
    if best and best_hits >= 1:
        return best
    return None


def _pick_topic_slug(q: str) -> Optional[str]:
    if re.search(r"小[1-6]|小学|小児|うちの子|子供|こども|未就学", q):
        return "age-restriction-guide"
    if re.search(r"\d+代|80代|高齢", q) and re.search(
        r"NSAID|nsaid|非ステロイド|イブプロフェン|イブ", q, re.I
    ):
        return "nsaid-elderly"
    if any(k in q for k in ("何時間", "また飲", "4時間", "間隔", "4 hours", "hours", "again")):
        return "usage-dose-interval"
    for key, slug in (
        ("年齢", "age-restriction-guide"),
        ("15歳", "age-restriction-guide"),
        ("NSAID", "nsaid-elderly"),
        ("高齢", "nsaid-elderly"),
    ):
        if key in q:
            return slug
    return None


def _resolve_topic_or_product(
    query: str,
    recommended_medicines: Optional[List[Dict[str, Any]]] = None,
    *,
    prefer_topics: bool = False,
) -> Optional[Path]:
    q = expand_concepts(query)
    topics_dir = BUILD_MEDICINE / "topics"
    if prefer_topics and topics_dir.is_dir():
        slug = _pick_topic_slug(q)
        if slug:
            path = topics_dir / f"{slug}.md"
            if path.is_file():
                return path
    for med in recommended_medicines or []:
        pname = str(med.get("product_name") or med.get("name") or "").strip()
        path = _resolve_product_by_name(pname)
        if path:
            return path
    return None


def route_medicine_doc(
    query: str,
    *,
    recommended_medicines: Optional[List[Dict[str, Any]]] = None,
    category: str = "",
) -> Optional[Tuple[Path, str, float]]:
    """
    Returns (path, virtual_uri, score) or None.
    virtual_uri uses medicine/ prefix for eval compatibility.
    """
    cat = (category or infer_medicine_category(query)).strip().lower()
    ingredients = _extract_ingredients_from_text(query)
    for med in recommended_medicines or []:
        pname = str(med.get("product_name") or med.get("name") or "")
        for ing in _product_ingredients(pname):
            canon = _canonical_ingredient(ing)
            if canon and canon not in ingredients:
                ingredients.append(canon)
        raw_ings = str(med.get("ingredients") or "")
        for line in raw_ings.split("\n"):
            ing = _normalize(line)
            if ing and ing not in ingredients:
                ingredients.append(ing)

    if cat == "interaction" or (not cat and len(ingredients) >= 2):
        if cat == "comparison" and recommended_medicines:
            for med in recommended_medicines:
                pname = str(med.get("product_name") or med.get("name") or "").strip()
                path = _resolve_product_by_name(pname)
                if path:
                    rel = path.relative_to(BUILD_MEDICINE).as_posix()
                    return path, f"local/medicine/{rel}", 0.91
        path = _resolve_interaction_path(ingredients)
        if path:
            rel = path.relative_to(BUILD_MEDICINE).as_posix()
            return path, f"local/medicine/{rel}", 0.92

    if cat == "side_effect" or (
        not cat and any(k in expand_concepts(query) for k in _CATEGORY_KEYWORDS["side_effect"])
    ):
        for ing in ingredients:
            path = _resolve_side_effect_path(ing)
            if path:
                rel = path.relative_to(BUILD_MEDICINE).as_posix()
                return path, f"local/medicine/{rel}", 0.88

    if cat == "doping":
        if recommended_medicines:
            for med in recommended_medicines or []:
                pname = str(med.get("product_name") or med.get("name") or "").strip()
                path = _resolve_product_by_name(pname)
                if path:
                    rel = path.relative_to(BUILD_MEDICINE).as_posix()
                    return path, f"local/medicine/{rel}", 0.87
        path = _resolve_doping_substance_path(query)
        if path:
            rel = path.relative_to(BUILD_MEDICINE).as_posix()
            return path, f"local/medicine/{rel}", 0.86

    if cat in ("usage", "age"):
        if recommended_medicines and cat == "age":
            for med in recommended_medicines or []:
                pname = str(med.get("product_name") or med.get("name") or "").strip()
                path = _resolve_product_by_name(pname)
                if path:
                    rel = path.relative_to(BUILD_MEDICINE).as_posix()
                    return path, f"local/medicine/{rel}", 0.87
        prefer_topics = (
            cat == "usage"
            and any(
                k in expand_concepts(query)
                for k in ("何時間", "また飲", "4時間", "間隔", "4 hours", "hours", "again")
            )
        ) or cat == "age"
        path = _resolve_topic_or_product(
            query,
            recommended_medicines,
            prefer_topics=prefer_topics,
        )
        if path:
            rel = path.relative_to(BUILD_MEDICINE).as_posix()
            return path, f"local/medicine/{rel}", 0.85

    return None


def route_medicine_docs(
    query: str,
    *,
    recommended_medicines: Optional[List[Dict[str, Any]]] = None,
    category: str = "",
    focuses: Optional[List[str]] = None,
    max_docs: int = 4,
) -> List[Tuple[Path, str, float]]:
    """複数 KB ドキュメントを focus/category に応じて収集。"""
    fs = [f for f in (focuses or []) if f and f != "general"]
    cat = (category or "").strip().lower()
    if not cat and fs:
        if "comparison" in fs:
            cat = "comparison"
        elif "ingredient" in fs or "product_image" in fs:
            cat = "usage"
        elif "interaction" in fs:
            cat = "interaction"
        elif "side_effect" in fs:
            cat = "side_effect"
        elif "doping" in fs:
            cat = "doping"
        elif "age" in fs:
            cat = "age"
        elif "usage" in fs or "ingredient" in fs:
            cat = "usage"
    if not cat:
        cat = infer_medicine_category(query).strip().lower()

    results: List[Tuple[Path, str, float]] = []
    seen: set[str] = set()

    def _add(path: Optional[Path], score: float = 0.85) -> None:
        if path is None or not path.is_file():
            return
        rel = path.relative_to(BUILD_MEDICINE).as_posix()
        uri = f"local/medicine/{rel}"
        if uri in seen:
            return
        seen.add(uri)
        results.append((path, uri, score))

    if cat == "comparison":
        meds = list(recommended_medicines or [])
        if not meds:
            try:
                import pandas as pd

                from src.core.medicine.medicine_response_builder import (
                    detect_medicine_name_in_query,
                )
                from src.core.medicine_data import CSV_PATH
                import os

                if os.path.exists(CSV_PATH):
                    df = pd.read_csv(CSV_PATH, encoding="utf-8")
                    meds = detect_medicine_name_in_query(query, df)
            except Exception:
                meds = []
        for med in meds[:max_docs]:
            pname = str(med.get("product_name") or med.get("name") or "").strip()
            _add(_resolve_product_by_name(pname), 0.9)
        if len(results) >= 2:
            ingredients = _extract_ingredients_from_text(query)
            ix = _resolve_interaction_path(ingredients)
            _add(ix, 0.88)
        if not results:
            single = route_medicine_doc(
                query, recommended_medicines=recommended_medicines, category="comparison"
            )
            if single:
                results.append(single)
        return results[:max_docs]

    if cat in ("usage", "age", "doping", "side_effect", "interaction"):
        single = route_medicine_doc(
            query,
            recommended_medicines=recommended_medicines,
            category=cat,
        )
        if single:
            results.append(single)
        if cat in ("usage", "age") and recommended_medicines:
            for med in recommended_medicines[:2]:
                pname = str(med.get("product_name") or med.get("name") or "").strip()
                _add(_resolve_product_by_name(pname), 0.84)
        return results[:max_docs]

    for med in (recommended_medicines or [])[:max_docs]:
        pname = str(med.get("product_name") or med.get("name") or "").strip()
        _add(_resolve_product_by_name(pname), 0.83)
    if not results:
        single = route_medicine_doc(
            query, recommended_medicines=recommended_medicines, category=cat
        )
        if single:
            results.append(single)
    return results[:max_docs]
