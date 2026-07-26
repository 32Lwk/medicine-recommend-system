"""Medicine QA 向け OTC パッケージ画像 HTML。"""
from __future__ import annotations

import html
from typing import Any

from src.services.medicine_image_urls import (
    enrich_medicine_image_url,
    medicine_has_ready_image,
)

NOIMAGE_HERO_PATH = "/static/line/medicine-noimage-hero.png"
NOIMAGE_LABEL = "Noimage"


def _resolve_product_image_url(medicine: dict[str, Any]) -> str:
    enriched = enrich_medicine_image_url(dict(medicine))
    for key in ("image_url", "product_image_url", "hero_url", "imageUrl"):
        url = str(enriched.get(key) or "").strip()
        if url.startswith("https://") or url.startswith("http://"):
            return url
    return ""


def _main_ingredient_phrase(med: dict[str, Any]) -> str:
    ing = str(med.get("ingredients") or "").replace("\n", " ").strip()
    for token in ("ロキソプロフェンナトリウム水和物", "ロキソプロフェン", "イブプロフェン", "アセトアミノフェン"):
        if token in ing:
            return token
    if ing:
        return ing.split(",")[0].strip()[:40]
    return "要確認"


def _usage_phrase(med: dict[str, Any]) -> str:
    ing = str(med.get("ingredients") or "")
    if "ロキソプロフェン" in ing or "イブプロフェン" in ing:
        return "頭痛・生理痛・歯痛などに用いられます"
    if "アセトアミノフェン" in ing and "イブプロフェン" not in ing:
        return "頭痛・生理痛・発熱などに用いられます"
    efficacy = str(med.get("efficacy") or "").replace("\n", " ").strip()
    if efficacy:
        short = efficacy[:36] + ("…" if len(efficacy) > 36 else "")
        return f"{short}などに用いられます"
    return "一般用医薬品として用いられます"


def _product_image_summary_sentence(medicines: list[dict[str, Any]]) -> str:
    """成分・用途を1文にまとめる。"""
    meds = [m for m in medicines if str(m.get("product_name") or m.get("name") or "").strip()]
    if not meds:
        return ""
    if len(meds) == 1:
        med = meds[0]
        name = str(med.get("product_name") or med.get("name") or "")
        ing = _main_ingredient_phrase(med)
        use = _usage_phrase(med)
        return f"{name}は主成分{ing}の解熱鎮痛薬で、{use}。"
    parts: list[str] = []
    for med in meds[:3]:
        name = str(med.get("product_name") or med.get("name") or "").strip()
        ing = _main_ingredient_phrase(med)
        if name:
            parts.append(f"{name}は{ing}")
    if len(parts) == 2:
        use = _usage_phrase(meds[0])
        return f"{parts[0]}、{parts[1]}を主成分とする解熱鎮痛薬で、{use}。"
    joined = "、".join(parts)
    return f"{joined}を主成分とする解熱鎮痛薬です。"


def _product_display_name(med: dict[str, Any]) -> str:
    return str(med.get("product_name") or med.get("name") or "").strip()


def _join_product_names(names: list[str]) -> str:
    clean = [n for n in names if n]
    if not clean:
        return ""
    if len(clean) == 1:
        return clean[0]
    if len(clean) == 2:
        return f"{clean[0]}、{clean[1]}"
    return "、".join(clean[:-1]) + f"、{clean[-1]}"


def _product_image_lead_sentence(meds: list[dict[str, Any]]) -> str:
    ready_names = [_product_display_name(m) for m in meds if medicine_has_ready_image(m)]
    pending_names = [_product_display_name(m) for m in meds if not medicine_has_ready_image(m)]
    ready_names = [n for n in ready_names if n]
    pending_names = [n for n in pending_names if n]
    all_names = _join_product_names([_product_display_name(m) for m in meds if _product_display_name(m)])

    if ready_names and not pending_names:
        return f"{_join_product_names(ready_names)}のパッケージ画像です。"
    if pending_names and not ready_names:
        return f"{_join_product_names(pending_names)}のパッケージ画像はまだ準備できていません。"
    ready_text = _join_product_names(ready_names)
    pending_text = _join_product_names(pending_names)
    if len(meds) == 2 and len(ready_names) == 1 and len(pending_names) == 1:
        return (
            f"{ready_text}のパッケージ画像を表示しました。"
            f"{pending_text}のパッケージ画像はまだ準備できていません。"
        )
    return (
        f"{all_names}のうち、{ready_text}のパッケージ画像を表示しました。"
        f"{pending_text}のパッケージ画像はまだ準備できていません。"
    )


def build_product_image_answer_text(
    medicines: list[dict[str, Any]],
    *,
    user_message: str = "",
) -> str:
    """画像 QA 用の統一回答（準備状況 + 成分・用途1文）。"""
    _ = user_message
    meds = [
        m
        for m in medicines[:4]
        if _product_display_name(m)
    ]
    if not meds:
        return "パッケージ画像はまだ準備できていません。"

    lead = _product_image_lead_sentence(meds)
    return lead + _product_image_summary_sentence(meds)


def _medicine_image_html(name: str, url: str) -> str:
    """推奨カルーセル（medicine_card.js）と同型の画像 HTML。"""
    name_esc = html.escape(name)
    ph_esc = html.escape(NOIMAGE_HERO_PATH)
    label_esc = html.escape(NOIMAGE_LABEL)
    if url:
        url_esc = html.escape(url)
        return (
            f'<div class="ui-med-image ui-med-image--card">'
            f'<img src="{url_esc}" alt="{name_esc}" loading="lazy" decoding="async"'
            f" onerror=\"this.onerror=null;this.src='{ph_esc}';"
            f"this.closest('.ui-med-image').classList.add('ui-med-image--placeholder');\">"
            f"</div>"
        )
    return (
        f'<div class="ui-med-image ui-med-image--placeholder ui-med-image--card" '
        f'data-no-image="true" aria-label="{label_esc}">'
        f'<span class="ui-med-image__label">{label_esc}</span>'
        f"</div>"
    )


def build_product_images_html(medicines: list[dict[str, Any]]) -> str:
    """CDN 画像または reco 同等の Noimage プレースホルダーを横並び HTML で返す。"""
    if not medicines:
        return ""
    blocks: list[str] = []
    for med in medicines[:4]:
        name = str(med.get("product_name") or med.get("name") or "").strip()
        url = _resolve_product_image_url(med)
        name_esc = html.escape(name)
        blocks.append(
            f'<figure class="ui-qa-product-images__item">'
            f"{_medicine_image_html(name, url)}"
            f'<figcaption class="ui-qa-product-images__caption">{name_esc}</figcaption>'
            f"</figure>"
        )
    if not blocks:
        return ""
    count = len(blocks)
    count_class = f" ui-qa-product-images--count-{count}" if count <= 4 else ""
    return (
        f'<div class="ui-qa-product-images app-scrollbar{count_class}">'
        + "".join(blocks)
        + "</div>"
    )


def attach_product_images_to_response(
    chat_response: dict[str, Any],
    medicines: list[dict[str, Any]],
) -> dict[str, Any]:
    """chat_response に product_images_html を付与。"""
    out = dict(chat_response)
    html_block = build_product_images_html(medicines)
    if html_block:
        out["product_images_html"] = html_block
    return out
