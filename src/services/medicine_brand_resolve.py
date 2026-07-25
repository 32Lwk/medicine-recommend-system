"""ブランド名・通称から CSV 上の代表製品を解決する（拡張可能レジストリ）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

# ---------------------------------------------------------------------------
# ブランド解決ルール — 新規通称は BRAND_RESOLVE_RULES に 1 行追加する
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BrandResolveRule:
    """
    通称 → 代表製品の解決ルール。

    hints: ユーザー発話で拾う表記ゆれ（例: イブ / アドビル）
    ingredient_aliases: 製品名に通称が無いときの主成分フォールバック
    canonical_product: CSV にあれば最優先する代表製品名
    product_prefix: 先頭一致検索用（未指定時は hints の最長文字列）
    product_name_contains: 部分一致（例: PL → パイロンＰＬ）
    preferred_products: canonical が無いとき試す製品名（順序付き）
    """

    hints: tuple[str, ...]
    ingredient_aliases: tuple[str, ...] = ()
    canonical_product: str | None = None
    product_prefix: str | None = None
    product_name_contains: tuple[str, ...] = ()
    preferred_products: tuple[str, ...] = ()


def _rule(
    *hints: str,
    ingredients: Sequence[str] = (),
    canonical: str | None = None,
    prefix: str | None = None,
    contains: Sequence[str] = (),
    preferred: Sequence[str] = (),
) -> BrandResolveRule:
    return BrandResolveRule(
        hints=hints,
        ingredient_aliases=tuple(ingredients),
        canonical_product=canonical,
        product_prefix=prefix,
        product_name_contains=tuple(contains),
        preferred_products=tuple(preferred),
    )


BRAND_RESOLVE_RULES: tuple[BrandResolveRule, ...] = (
    _rule("イブ", "アドビル", ingredients=("イブプロフェン",), canonical="イブ", prefix="イブ"),
    _rule(
        "ロキソニン",
        ingredients=("ロキソプロフェン",),
        prefix="ロキソニン",
        preferred=("ロキソニンＳ", "ロキソニンＳプレミアム", "ロキソニンＳクイック"),
    ),
    _rule(
        "バファリン",
        ingredients=("アスピリン", "アセトアミノフェン"),
        prefix="バファリン",
        preferred=("バファリンＡ", "バファリンルナｉ", "バファリンプレミアム"),
    ),
    _rule("カロナール", ingredients=("アセトアミノフェン",), prefix="カロナール", preferred=("カロナールＡ",)),
    _rule("タイレノール", ingredients=("アセトアミノフェン",), prefix="タイレノール"),
    _rule("セデス", prefix="セデス", preferred=("セデスＶ", "セデス・ハイ", "セデスキュア")),
    _rule("ルル", prefix="ルル", preferred=("ルルアタックＩＢエース", "ルルアタックＮＸ", "ルルアタックＴＲ")),
    _rule(
        "パブロン",
        prefix="パブロン",
        preferred=(
            "パブロンゴールドＡ＜錠＞",
            "パブロンクオリティ錠",
            "パブロンセレクトＣ",
        ),
    ),
    _rule("ベンザ", prefix="ベンザ", preferred=("ベンザブロックＳ錠", "ベンザブロックＳ", "ベンザブロックＬ")),
    _rule(
        "PL",
        contains=("パイロンＰＬ",),
        preferred=("パイロンＰＬ錠", "パイロンＰＬ顆粒", "パイロンＰＬ錠Ｐｒｏ"),
    ),
    _rule("ペタミン", ingredients=("アセトアミノフェン",), preferred=("カロナールＡ", "タイレノールＡ")),
)

# extract_drug_entities 用 — hints を長い順（部分一致の誤検出を抑える）
MEDICINE_BRAND_HINTS: tuple[str, ...] = tuple(
    sorted({h for rule in BRAND_RESOLVE_RULES for h in rule.hints}, key=len, reverse=True)
)

_HINT_TO_RULE: dict[str, BrandResolveRule] = {
    hint: rule for rule in BRAND_RESOLVE_RULES for hint in rule.hints
}


def _row_to_med(row) -> dict[str, Any]:
    return {
        "product_name": row.get("製品名", ""),
        "manufacturer": row.get("メーカー名", ""),
        "efficacy": row.get("効能効果", ""),
        "usage": row.get("用法用量", ""),
        "age_restriction": row.get("年齢制限", ""),
        "ingredients": row.get("成分", ""),
        "doping_prohibited": row.get("禁止物質あり", ""),
        "medicine_type": row.get("医薬品の種類", ""),
    }


def _ingredients_text(row) -> str:
    return str(row.get("成分") or "").replace("\n", " ")


def _product_name(row) -> str:
    return str(row.get("製品名") or "").strip()


def _brand_prefix_match(hint: str, product_name: str) -> bool:
    """「イブ」が「ケイブク」に部分一致しないよう、先頭一致のみ。"""
    pn = product_name.strip()
    if not hint or not pn:
        return False
    if pn == hint:
        return True
    if not pn.startswith(hint):
        return False
    if len(pn) == len(hint):
        return True
    nxt = pn[len(hint)]
    return not nxt.isascii() or not nxt.isalnum() or nxt in "＜＞（(ＡＥ"


def _lookup_rule(hint: str) -> BrandResolveRule | None:
    return _HINT_TO_RULE.get((hint or "").strip())


def _resolve_prefix(rule: BrandResolveRule, hint: str) -> str:
    if rule.product_prefix:
        return rule.product_prefix
    return max(rule.hints, key=len)


def _find_by_exact_name(medicine_df, name: str) -> dict[str, Any] | None:
    target = (name or "").strip()
    if not target:
        return None
    for _, row in medicine_df.iterrows():
        if _product_name(row) == target:
            return _row_to_med(row)
    return None


def _find_by_prefix(medicine_df, prefix: str) -> dict[str, Any] | None:
    candidates: list[tuple[int, dict[str, Any]]] = []
    for _, row in medicine_df.iterrows():
        pn = _product_name(row)
        if _brand_prefix_match(prefix, pn):
            candidates.append((len(pn), _row_to_med(row)))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def _find_by_contains(medicine_df, fragments: Iterable[str]) -> dict[str, Any] | None:
    candidates: list[tuple[int, dict[str, Any]]] = []
    for _, row in medicine_df.iterrows():
        pn = _product_name(row)
        if not pn:
            continue
        if any(frag in pn for frag in fragments):
            candidates.append((len(pn), _row_to_med(row)))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def _find_by_ingredients(
    medicine_df,
    aliases: Sequence[str],
    *,
    hint: str,
    prefix: str,
) -> dict[str, Any] | None:
    alias_hits: list[tuple[int, dict[str, Any]]] = []
    hint_lower = hint.lower()
    for _, row in medicine_df.iterrows():
        ing = _ingredients_text(row).lower()
        if not any(alias.lower() in ing for alias in aliases):
            continue
        pn = _product_name(row)
        med = _row_to_med(row)
        if _brand_prefix_match(prefix, pn) or _brand_prefix_match(hint, pn):
            alias_hits.append((0, med))
        elif hint_lower in pn.lower():
            alias_hits.append((50 + len(pn), med))
        else:
            alias_hits.append((100 + len(pn), med))
    if not alias_hits:
        return None
    alias_hits.sort(key=lambda x: x[0])
    return alias_hits[0][1]


def resolve_brand_hint_product(hint: str, medicine_df) -> dict[str, Any] | None:
    """
    ブランド通称 1 件に対し代表製品 1 件を返す。
    ルール未登録の通称は先頭一致フォールバックのみ。
    """
    if medicine_df is None or medicine_df.empty or not (hint or "").strip():
        return None
    hint = hint.strip()
    rule = _lookup_rule(hint)

    if rule is not None:
        if rule.canonical_product:
            found = _find_by_exact_name(medicine_df, rule.canonical_product)
            if found:
                return found
        for preferred in rule.preferred_products:
            found = _find_by_exact_name(medicine_df, preferred)
            if found:
                return found
        if rule.product_name_contains:
            found = _find_by_contains(medicine_df, rule.product_name_contains)
            if found:
                return found
        prefix = _resolve_prefix(rule, hint)
        found = _find_by_prefix(medicine_df, prefix)
        if found:
            return found
        if rule.ingredient_aliases:
            found = _find_by_ingredients(
                medicine_df,
                rule.ingredient_aliases,
                hint=hint,
                prefix=prefix,
            )
            if found:
                return found
        return None

    # ルール外: 完全一致 → 先頭一致（最短）
    found = _find_by_exact_name(medicine_df, hint)
    if found:
        return found
    return _find_by_prefix(medicine_df, hint)


def resolve_brand_hints_in_query(user_message: str, medicine_df) -> list[dict[str, Any]]:
    """質問中のブランド通称ごとに代表製品を順序付きで返す。"""
    try:
        from src.dialogue.routing.context_signals import extract_drug_entities
    except ImportError:
        return []

    products: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for hint in extract_drug_entities(user_message):
        med = resolve_brand_hint_product(hint, medicine_df)
        if not med:
            continue
        name = str(med.get("product_name") or "")
        if not name or name in seen_names:
            continue
        products.append(med)
        seen_names.add(name)
    return products


def iter_brand_resolve_rules() -> Iterable[BrandResolveRule]:
    """テスト・管理画面向け: 登録ルール一覧。"""
    return BRAND_RESOLVE_RULES
