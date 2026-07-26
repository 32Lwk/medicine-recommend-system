"""
セッション内のブランド→製品ピン留め。

比較・副作用・画像 Q&A で「バファリン」等の総称が毎回別製品に揺れないよう、
一度解決した代表製品を session に保持する。
明示的な製品名（バファリンプレミアム等）が出たときだけピンを更新する。
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional

logger = logging.getLogger(__name__)

SESSION_PIN_KEY = "qa_brand_pins"


def _norm_hint(hint: str) -> str:
    return (hint or "").strip()


def get_session_brand_pins(session: Any) -> Dict[str, Dict[str, Any]]:
    """session / DB payload からブランドピンを取得。"""
    if session is None:
        return {}
    raw: Any = None
    if isinstance(session, Mapping):
        raw = session.get(SESSION_PIN_KEY)
        if not raw:
            attrs = session.get("user_attributes") or {}
            if isinstance(attrs, Mapping):
                raw = attrs.get(SESSION_PIN_KEY)
    if not isinstance(raw, Mapping):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for k, v in raw.items():
        hint = _norm_hint(str(k))
        if not hint or not isinstance(v, Mapping):
            continue
        name = str(v.get("product_name") or "").strip()
        if not name:
            continue
        out[hint] = dict(v)
    return out


def write_session_brand_pins(
    session: MutableMapping[str, Any] | None,
    pins: Mapping[str, Mapping[str, Any]],
) -> None:
    """session と user_attributes の両方にピンを書き込む（DB 永続化向け）。"""
    if session is None:
        return
    clean: Dict[str, Dict[str, Any]] = {}
    for hint, med in pins.items():
        h = _norm_hint(hint)
        if not h or not isinstance(med, Mapping):
            continue
        name = str(med.get("product_name") or "").strip()
        if not name:
            continue
        clean[h] = {
            "product_name": name,
            "manufacturer": str(med.get("manufacturer") or ""),
            "ingredients": str(med.get("ingredients") or ""),
            "efficacy": str(med.get("efficacy") or ""),
            "usage": str(med.get("usage") or ""),
            "age_restriction": str(med.get("age_restriction") or ""),
            "doping_prohibited": str(med.get("doping_prohibited") or ""),
            "medicine_type": str(med.get("medicine_type") or ""),
        }
    session[SESSION_PIN_KEY] = clean
    attrs = session.get("user_attributes")
    if not isinstance(attrs, dict):
        attrs = {}
        session["user_attributes"] = attrs
    attrs[SESSION_PIN_KEY] = clean


def _message_mentions_specific_product(user_message: str, product_name: str) -> bool:
    """ユーザーが特定製品名を明示しているか（総称より具体）。"""
    msg = (user_message or "").strip()
    name = (product_name or "").strip()
    if not msg or not name:
        return False
    if name in msg:
        return True
    from src.services.medicine_brand_resolve import _fold_alnum

    folded_msg = _fold_alnum(msg)
    folded_name = _fold_alnum(name)
    if folded_name and folded_name in folded_msg:
        # 総称だけの一致（バファリン ⊂ バファリンプレミアム）は除外したいが、
        # preferred 候補は具体名なのでそのまま許可
        return True
    return False


def prefer_pinned_product(
    hint: str,
    *,
    user_message: str,
    medicine_df: Any,
    session_pins: Mapping[str, Mapping[str, Any]] | None,
    freshly_resolved: Mapping[str, Any] | None,
) -> Optional[Dict[str, Any]]:
    """
    ピン優先で代表製品を返す。

    - ユーザーが別の具体製品名を明示 → 新解決を採用（呼び出し側でピン更新）
    - それ以外でピンがある → ピンを返す
    - ピンなし → freshly_resolved を返す
    """
    from src.services.medicine_brand_resolve import (
        BRAND_RESOLVE_RULES,
        _find_by_exact_name,
        _lookup_rule,
    )

    h = _norm_hint(hint)
    pins = session_pins or {}
    pinned = pins.get(h)
    fresh = dict(freshly_resolved) if freshly_resolved else None

    # 明示製品名: preferred / CSV 行名が発話に含まれる
    rule = _lookup_rule(h)
    if rule is not None and medicine_df is not None:
        candidates = list(rule.preferred_products)
        if rule.canonical_product:
            candidates.insert(0, rule.canonical_product)
        for cand in candidates:
            if _message_mentions_specific_product(user_message, cand):
                found = _find_by_exact_name(medicine_df, cand)
                if found:
                    return found

    if pinned and str(pinned.get("product_name") or "").strip():
        # ピンが CSV にまだ存在するなら採用
        name = str(pinned.get("product_name"))
        if medicine_df is not None:
            found = _find_by_exact_name(medicine_df, name)
            if found:
                return found
        return dict(pinned)

    return fresh


def remember_resolved_brand_products(
    session: MutableMapping[str, Any] | None,
    *,
    user_message: str,
    products: Iterable[Mapping[str, Any]],
    drug_hints: Iterable[str] | None = None,
) -> Dict[str, Dict[str, Any]]:
    """
    解決済み製品をヒント単位でピン留め。
    hints が無い場合は製品名プレフィックスから BRAND_RESOLVE_RULES を逆引きする。
    """
    from src.services.medicine_brand_resolve import BRAND_RESOLVE_RULES, MEDICINE_BRAND_HINTS
    from src.dialogue.routing.context_signals import extract_drug_entities

    pins = get_session_brand_pins(session)
    hints = list(drug_hints) if drug_hints is not None else extract_drug_entities(user_message)
    products_list = [dict(p) for p in products if isinstance(p, Mapping) and p.get("product_name")]

    # hint → product の対応（順序一致を優先）
    for i, hint in enumerate(hints):
        h = _norm_hint(hint)
        if not h:
            continue
        med: Optional[Mapping[str, Any]] = None
        if i < len(products_list):
            med = products_list[i]
        else:
            # 製品名がヒントで始まるものを探す
            for p in products_list:
                pn = str(p.get("product_name") or "")
                if pn.startswith(h) or h in pn:
                    med = p
                    break
        if med:
            pins[h] = dict(med)

    # ヒントが無い／不足時: 製品名からレジストリヒントを逆引き
    for p in products_list:
        pn = str(p.get("product_name") or "")
        for rule in BRAND_RESOLVE_RULES:
            prefix = rule.product_prefix or max(rule.hints, key=len)
            if pn.startswith(prefix) or any(pn.startswith(h) for h in rule.hints):
                for h in rule.hints:
                    if h in MEDICINE_BRAND_HINTS and (
                        h in (user_message or "") or pn.startswith(h) or pn.startswith(prefix)
                    ):
                        pins.setdefault(h, dict(p))
                break

    write_session_brand_pins(session, pins)
    logger.info("qa_brand_pins updated: %s", {k: v.get("product_name") for k, v in pins.items()})
    return pins


def resolve_products_with_session_pins(
    user_message: str,
    medicine_df: Any,
    session: Any = None,
) -> List[Dict[str, Any]]:
    """ブランド解決 + セッションピン適用の一体 API。"""
    from src.dialogue.routing.context_signals import extract_drug_entities
    from src.services.medicine_brand_resolve import resolve_brand_hint_product

    pins = get_session_brand_pins(session)
    products: List[Dict[str, Any]] = []
    seen: set[str] = set()
    hints = extract_drug_entities(user_message)
    for hint in hints:
        fresh = resolve_brand_hint_product(hint, medicine_df)
        med = prefer_pinned_product(
            hint,
            user_message=user_message,
            medicine_df=medicine_df,
            session_pins=pins,
            freshly_resolved=fresh,
        )
        if not med:
            continue
        name = str(med.get("product_name") or "")
        if not name or name in seen:
            continue
        products.append(dict(med))
        seen.add(name)

    if products and session is not None and isinstance(session, MutableMapping):
        remember_resolved_brand_products(
            session,
            user_message=user_message,
            products=products,
            drug_hints=hints,
        )
    return products
