"""Medicine QA 向け OTC パッケージ画像 HTML。"""
from __future__ import annotations

import html
from typing import Any

from src.services.medicine_image_urls import enrich_medicine_image_url

_PLACEHOLDER_LABEL = "画像準備中"


def build_product_images_html(medicines: list[dict[str, Any]]) -> str:
    """CDN 画像またはプレースホルダーを横並び HTML で返す。"""
    if not medicines:
        return ""
    blocks: list[str] = []
    for med in medicines[:4]:
        enriched = enrich_medicine_image_url(dict(med))
        name = html.escape(str(enriched.get("product_name") or enriched.get("name") or ""))
        url = str(enriched.get("image_url") or "").strip()
        if url:
            blocks.append(
                f'<figure class="ui-qa-product-images__item">'
                f'<img src="{html.escape(url)}" alt="{name}" loading="lazy" decoding="async" '
                f'class="ui-qa-product-images__img">'
                f'<figcaption class="ui-qa-product-images__caption">{name}</figcaption>'
                f"</figure>"
            )
        else:
            blocks.append(
                f'<figure class="ui-qa-product-images__item ui-qa-product-images__item--placeholder">'
                f'<div class="ui-qa-product-images__ph" aria-label="{_PLACEHOLDER_LABEL}">'
                f'<span>{_PLACEHOLDER_LABEL}</span></div>'
                f'<figcaption class="ui-qa-product-images__caption">{name}</figcaption>'
                f"</figure>"
            )
    if not blocks:
        return ""
    return (
        '<div class="ui-qa-product-images app-scrollbar">'
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
