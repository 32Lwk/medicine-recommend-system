"""副作用 Q&A 向け — PMDA/CSV 原文を読みやすい表示用に整形する。"""
from __future__ import annotations

import html
import re
from typing import Any

_COMMON_SYMPTOM_KEYWORDS = (
    "傾眠",
    "眠気",
    "頭痛",
    "動悸",
    "吐き気",
    "悪心",
    "下痢",
    "便秘",
    "発疹",
    "めまい",
    "口渇",
    "胃腸障害",
    "食欲不振",
    "浮腫",
    "不眠",
    "口内乾燥",
    "疲労",
    "かゆみ",
    "そう痒",
)

_LEVEL_LABELS = {"高": "要注意", "中": "注意", "低": "軽度"}
_LEVEL_CSS = {"高": "high", "中": "medium", "低": "low"}


def _short_ingredient_name(name: str, max_len: int = 14) -> str:
    text = re.sub(r"\s+", "", str(name or "").strip())
    for suffix in ("ナトリウム水和物", "ナトリウム", "塩酸塩", "水和物", "マレイン酸塩"):
        if text.endswith(suffix) and len(text) > len(suffix) + 2:
            text = text[: -len(suffix)]
            break
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _is_pmda_format(text: str) -> bool:
    return bool(re.search(r"11\.[12]", text or ""))


def _parse_simple_symptoms(text: str) -> list[str]:
    parts = re.split(r"[・、,/]", str(text or ""))
    out: list[str] = []
    for part in parts:
        item = part.strip()
        if not item or len(item) > 24:
            continue
        if item not in out:
            out.append(item)
    return out[:8]


def _names_from_serious_chunk(chunk: str) -> list[str]:
    names: list[str] = []
    for hit in re.finditer(
        r"([ぁ-んァ-ヶー一-龠a-zA-Z][ぁ-んァ-ヶー一-龠a-zA-Z0-9\-]*)\((?:頻度|いずれも頻度|0\.\d+)[^)]*\)",
        chunk[:240],
    ):
        name = hit.group(1).strip()
        if name and name not in names:
            names.append(name)
    if names:
        return names
    for part in re.split(r"[、,]", chunk[:120]):
        cleaned = re.sub(r"\([^)]*\)", "", part).strip()
        if cleaned and len(cleaned) <= 20 and cleaned not in names:
            names.append(cleaned)
    return names


def _extract_serious_effect_groups(text: str) -> list[list[str]]:
    section_match = re.search(r"11\.1\s*重大な副作用(.*)(?:11\.2|$)", text, re.DOTALL)
    if not section_match:
        return []
    section = section_match.group(1)
    groups: list[list[str]] = []

    for hit in re.finditer(
        r"11\.1\.\d+\s+(.+?)(?=\s*11\.1\.\d+|\s*11\.2|$)",
        section,
        re.DOTALL,
    ):
        names = _names_from_serious_chunk(hit.group(1))
        if names:
            groups.append(names)

    return groups[:5]


def _extract_serious_effects(text: str) -> list[str]:
    flat: list[str] = []
    for group in _extract_serious_effect_groups(text):
        for name in group:
            if name not in flat:
                flat.append(name)
    return flat[:6]


def _extract_common_effects(text: str) -> list[str]:
    if _is_pmda_format(text):
        section_match = re.search(r"11\.2\s*その他の副作用(.*)$", text, re.DOTALL)
        if not section_match:
            return []
        section = section_match.group(1)
        out: list[str] = []
        for kw in _COMMON_SYMPTOM_KEYWORDS:
            if kw in section and kw not in out:
                out.append(kw)
        return out[:6]
    return _parse_simple_symptoms(text)


def parse_side_effect_row(row: dict[str, Any]) -> dict[str, Any]:
    ingredient = str(row.get("成分名") or "").strip()
    level = str(row.get("副作用レベル") or "中").strip()
    if level not in _LEVEL_LABELS:
        level = "中"
    symptoms_raw = str(row.get("副作用症状") or "").strip()
    serious_groups = (
        _extract_serious_effect_groups(symptoms_raw) if _is_pmda_format(symptoms_raw) else []
    )
    serious = [name for group in serious_groups for name in group][:6]
    common = _extract_common_effects(symptoms_raw)
    if not serious and not common and symptoms_raw:
        common = _parse_simple_symptoms(symptoms_raw)[:5]
    return {
        "ingredient": ingredient,
        "ingredient_short": _short_ingredient_name(ingredient),
        "level": level,
        "level_label": _LEVEL_LABELS.get(level, "注意"),
        "level_css": _LEVEL_CSS.get(level, "medium"),
        "serious": serious,
        "serious_groups": serious_groups,
        "common": common,
    }


def _format_effect_group(group: list[str]) -> str:
    """同一 11.1.x グループを表示用1行に整形。"""
    items = list(group)
    name_set = set(items)
    if "ショック" in name_set and "アナフィラキシー" in name_set:
        rest = [n for n in items if n not in ("ショック", "アナフィラキシー")]
        items = ["アナフィラキシーショック"] + rest
    text = "・".join(items[:4])
    if len(items) > 4:
        text += " 等"
    return text


def build_side_effect_cards_html(
    rows: list[dict[str, Any]],
    *,
    reference_only: bool = False,
) -> str:
    parsed = [parse_side_effect_row(r) for r in rows if r]
    if not parsed:
        return ""

    max_cards = 2 if reference_only else 4
    cards: list[str] = []
    for item in parsed[:max_cards]:
        card = _render_side_effect_card(item, compact=reference_only)
        if card:
            cards.append(card)

    if not cards:
        return ""

    inner = (
        '<div class="ui-side-effect-list'
        + (" ui-side-effect-list--compact" if reference_only else "")
        + '">'
        + "".join(cards)
        + '<p class="ui-side-effect-footnote">'
        "※ 添付文書の抜粋です。"
        "</p>"
        "</div>"
    )

    if reference_only:
        return (
            '<details class="ui-side-effect-details" open>'
            '<summary class="ui-side-effect-details__summary">'
            "参考：添付文書の副作用抜粋"
            "</summary>"
            + inner
            + "</details>"
        )
    return inner


def _render_side_effect_card(item: dict[str, Any], *, compact: bool) -> str:
    groups: list[str] = []
    serious_groups = item.get("serious_groups") or []
    if serious_groups:
        groups.append(
            _symptom_group_html(
                "重大",
                serious_groups,
                "serious",
                grouped=True,
                compact=compact,
            )
        )
    elif item.get("serious"):
        groups.append(
            _symptom_group_html(
                "重大",
                [[name] for name in item["serious"]],
                "serious",
                grouped=True,
                compact=compact,
            )
        )
    if item.get("common"):
        groups.append(
            _symptom_group_html(
                "よくある",
                [[name] for name in item["common"]],
                "common",
                grouped=False,
                compact=compact,
            )
        )
    if not groups:
        return ""
    return (
        '<div class="ui-side-effect-card'
        + (" ui-side-effect-card--compact" if compact else "")
        + '">'
        '<div class="ui-side-effect-card__head">'
        f'<span class="ui-side-effect-card__name">{html.escape(item["ingredient_short"])}</span>'
        f'<span class="ui-side-effect-card__level ui-side-effect-card__level--{html.escape(item["level_css"])}">'
        f'{html.escape(item["level_label"])}</span>'
        "</div>"
        + "".join(groups)
        + "</div>"
    )


def _symptom_group_html(
    label: str,
    groups: list[list[str]],
    kind: str,
    *,
    grouped: bool = False,
    compact: bool = False,
) -> str:
    display_groups = groups[:3 if compact else 4]
    chips: list[str] = []
    hidden = 0
    for group in display_groups:
        if grouped:
            text = _format_effect_group(group)
        else:
            text = group[0] if group else ""
        if not text:
            continue
        chips.append(
            f'<li class="ui-side-effect-chip ui-side-effect-chip--{html.escape(kind)}">'
            f"{html.escape(text)}</li>"
        )
    hidden = max(0, len(groups) - len(display_groups))
    if hidden:
        chips.append(
            f'<li class="ui-side-effect-chip ui-side-effect-chip--more">'
            f"他 {hidden} グループ</li>"
        )
    return (
        f'<div class="ui-side-effect-card__group ui-side-effect-card__group--{html.escape(kind)}">'
        f'<span class="ui-side-effect-card__label">{html.escape(label)}</span>'
        f'<ul class="ui-side-effect-card__chips">{"".join(chips)}</ul>'
        "</div>"
    )


def build_concise_side_effect_answer(
    product_name: str,
    rows: list[dict[str, Any]],
    *,
    focus_keywords: tuple[str, ...] | None = None,
) -> str:
    if not rows:
        return (
            f"「{product_name}」の副作用情報をデータベースから特定できませんでした。"
            "製品の添付文書をご確認いただくか、薬剤師・医師にご相談ください。"
        )

    parsed = [parse_side_effect_row(r) for r in rows[:3]]
    if focus_keywords:
        hits: list[str] = []
        for item in parsed:
            for kw in focus_keywords:
                for bucket in (item["serious"], item["common"]):
                    if any(kw in s for s in bucket) and kw not in hits:
                        hits.append(kw)
        if hits:
            joined = "・".join(hits[:3])
            return (
                f"「{product_name}」では、添付文書上「{joined}」等が報告されています。"
                "個人差があるため、運転・機械操作の前は注意してください。"
            )

    highlights: list[str] = []
    for item in parsed:
        for name in item["serious"][:2]:
            if name not in highlights:
                highlights.append(name)
        for name in item["common"][:2]:
            if name not in highlights:
                highlights.append(name)

    if highlights:
        summary = "、".join(highlights[:5])
        return (
            f"「{product_name}」の主な副作用の要点です（添付文書ベース）。"
            f"{summary} などが報告されています。"
            "個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。"
        )

    return (
        f"「{product_name}」の副作用要点を下にまとめました。"
        "個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。"
    )


def build_drowsiness_answer(product_name: str, side_rows: list[dict[str, Any]]) -> str:
    drowsiness_keywords = ("眠気", "傾眠", "眠くなる", "眠い")
    hits: list[str] = []
    for row in side_rows:
        parsed = parse_side_effect_row(row)
        for kw in drowsiness_keywords:
            for bucket in (parsed["serious"], parsed["common"]):
                if any(kw in s for s in bucket) and kw not in hits:
                    hits.append(kw)

    if hits:
        joined = "・".join(hits[:3])
        return (
            f"「{product_name}」では、添付文書上「{joined}」等が報告されています。"
            "個人差があるため、運転・機械操作の前は注意してください。"
        )

    if "ロキソニン" in product_name or any(
        "ロキソプロフェン" in str(r.get("成分名", "")) for r in side_rows
    ):
        return (
            f"「{product_name}」（ロキソプロフェン系）では、一般に強い眠気は主要な副作用として"
            "挙げられていません。ただし個人差や他の成分・併用薬により眠気を感じる場合があります。"
            "運転前や重要な作業前は注意し、気になる症状が続く場合は薬剤師・医師に相談してください。"
        )

    return (
        f"「{product_name}」について、添付文書ベースの情報からは眠気が主要副作用として"
        "明記されていない場合があります。個人差があるため、眠気を感じたら運転等は控え、"
        "薬剤師・医師に相談してください。"
    )
