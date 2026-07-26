#!/usr/bin/env python3
"""
OTC パッケージ画像のマルチソース解決（マツキヨ / 楽天 / Yahoo / 登録済み公式 URL）。

各ソースの検索結果を verify_image_match でスコアリングし、最良の候補を返す。
"""
from __future__ import annotations

import io
import json
import re
import time
import unicodedata
from dataclasses import dataclass, field
from html import unescape
from typing import Any
from urllib.parse import quote, urljoin

import requests

from scripts.sync_otc_images_from_matsukiyo import (
    Candidate,
    MatsukiyoClient,
    resolve_image,
)
from scripts.sync_top50_otc_images import OFFICIAL_IMAGE_URLS, verify_image_match

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) medicine-recommend/1.0"


@dataclass
class ImageCandidate:
    source: str
    image_url: str
    source_label: str
    score: int = 0
    review_score: int = 0
    review_reasons: list[str] = field(default_factory=list)
    approved: bool = False
    meta: dict[str, Any] = field(default_factory=dict)


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "").strip())


def _query_variants(product_name: str, manufacturer: str) -> list[str]:
    raw = (product_name or "").strip()
    cleaned = re.sub(r"[「」『』\"'（）()《》]", "", raw)
    core = re.sub(r"[Ａ-ＺA-Z0-9]+$", "", cleaned).strip()
    mfr = _norm(manufacturer)[:8] if manufacturer else ""
    out: list[str] = []
    for base in dict.fromkeys([raw, cleaned, core]):
        if not base:
            continue
        if mfr:
            out.append(f"{base} {mfr}")
        out.append(base)
    if len(core) >= 6:
        out.append(core[: min(14, len(core))])
    return out[:8]


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def _preview_url(url: str, session: requests.Session | None = None) -> bytes | None:
    headers = {"User-Agent": USER_AGENT}
    if "matsukiyococokara-online.com" in url:
        headers["Referer"] = "https://www.matsukiyococokara-online.com/store/"
    if "shop.r10s.jp" in url:
        headers["Referer"] = "https://www.rakuten.co.jp/"
    sess = session or _session()
    try:
        r = sess.get(url, timeout=30, headers=headers)
        r.raise_for_status()
        if len(r.content) < 2000:
            return None
        return r.content
    except requests.RequestException:
        return None


def _score_candidate(
    product_name: str,
    manufacturer: str,
    cand: ImageCandidate,
    *,
    session: requests.Session | None = None,
) -> ImageCandidate:
    body = _preview_url(cand.image_url, session)
    if not body:
        cand.review_reasons = ["download_failed"]
        return cand
    review = verify_image_match(product_name, manufacturer, cand.source_label, body)
    cand.review_score = review.score
    cand.review_reasons = review.reasons
    cand.approved = review.approved
    # ソース別ボーナス（公式・EC パッケージ優先）
    bonus = {"official_url": 15, "matsukiyo": 10, "rakuten_ec": 5, "yahoo_ec": 5}.get(cand.source, 0)
    cand.score = review.score + bonus
    cand.meta["preview_bytes"] = len(body)
    return cand


def search_rakuten(query: str, *, limit: int = 6) -> list[ImageCandidate]:
    """楽天市場検索 HTML から商品画像 URL を抽出。"""
    sess = _session()
    url = f"https://search.rakuten.co.jp/search/mall/{quote(query)}/"
    try:
        r = sess.get(url, timeout=30)
        r.raise_for_status()
    except requests.RequestException:
        return []
    time.sleep(0.5)
    out: list[ImageCandidate] = []
    # thumbnail + title pairs
    for m in re.finditer(
        r'<img[^>]+src="(https://[^"]+(?:shop\.r10s\.jp|thumbnail\.image\.rakuten\.co\.jp)[^"]+)"'
        r'[^>]*(?:alt="([^"]*)")?',
        r.text,
        flags=re.I,
    ):
        img_url = m.group(1)
        title = unescape(m.group(2) or "")
        if "logo" in img_url.lower() or "icon" in img_url.lower():
            continue
        # normalize rakuten thumbnail to larger image when possible
        img_url = re.sub(r"\?_ex=\d+x\d+", "", img_url)
        out.append(ImageCandidate(source="rakuten_ec", image_url=img_url, source_label=title or query))
        if len(out) >= limit:
            break
    # fallback: shop.r10s.jp direct
    if not out:
        for img in re.findall(r'(https://shop\.r10s\.jp/[^"\']+\.(?:jpg|jpeg|png|webp))', r.text, flags=re.I):
            out.append(ImageCandidate(source="rakuten_ec", image_url=img, source_label=query))
            if len(out) >= limit:
                break
    return out


def search_yahoo(query: str, *, limit: int = 6) -> list[ImageCandidate]:
    """Yahoo!ショッピング検索から商品画像 URL を抽出。"""
    sess = _session()
    url = f"https://shopping.yahoo.co.jp/search?p={quote(query)}"
    try:
        r = sess.get(url, timeout=30)
        r.raise_for_status()
    except requests.RequestException:
        return []
    time.sleep(0.5)
    out: list[ImageCandidate] = []
    for m in re.finditer(
        r'<img[^>]+src="(https://[^"]+(?:item-shopping\.c\.yimg\.jp|shopping\.geocities\.jp)[^"]+)"'
        r'[^>]*(?:alt="([^"]*)")?',
        r.text,
        flags=re.I,
    ):
        img_url = m.group(1)
        title = unescape(m.group(2) or "")
        out.append(ImageCandidate(source="yahoo_ec", image_url=img_url, source_label=title or query))
        if len(out) >= limit:
            break
    return out


def resolve_multi_source(
    product_name: str,
    manufacturer: str,
    *,
    client: MatsukiyoClient | None = None,
    official_url: str = "",
    extra_urls: list[str] | None = None,
    try_rakuten: bool = True,
    try_yahoo: bool = True,
    try_matsukiyo: bool = True,
    min_approved_score: int = 55,
) -> ImageCandidate | None:
    """
    複数ソースから画像候補を集め、verify_image_match で最良を選ぶ。
    """
    sess = _session()
    raw_candidates: list[ImageCandidate] = []

    # 1) 明示 URL
    for url in [official_url, OFFICIAL_IMAGE_URLS.get(product_name, ""), *(extra_urls or [])]:
        url = (url or "").strip()
        if not url or url.endswith(".html"):
            continue
        raw_candidates.append(
            ImageCandidate(source="official_url", image_url=url, source_label=product_name)
        )

    queries = _query_variants(product_name, manufacturer)
    matsukiyo = client or MatsukiyoClient(delay_sec=0.5)

    # 2) マツキヨ
    if try_matsukiyo:
        cand = Candidate(product_name=product_name, manufacturer=manufacturer)
        resolve_image(matsukiyo, cand)
        if cand.status == "resolved" and cand.source_image_url:
            raw_candidates.append(
                ImageCandidate(
                    source="matsukiyo",
                    image_url=cand.source_image_url,
                    source_label=cand.matsukiyo_name or product_name,
                    meta={"matsukiyo_jan": cand.matsukiyo_jan},
                )
            )

    # 3) 楽天 / Yahoo（各クエリで上位候補）
    seen_urls: set[str] = set()
    for q in queries[:4]:
        if try_rakuten:
            for c in search_rakuten(q):
                if c.image_url not in seen_urls:
                    seen_urls.add(c.image_url)
                    raw_candidates.append(c)
        if try_yahoo:
            for c in search_yahoo(q):
                if c.image_url not in seen_urls:
                    seen_urls.add(c.image_url)
                    raw_candidates.append(c)

    if not raw_candidates:
        return None

    scored: list[ImageCandidate] = []
    m_sess = matsukiyo.session if try_matsukiyo else sess
    for cand in raw_candidates[:20]:
        use_sess = m_sess if cand.source == "matsukiyo" else sess
        scored.append(_score_candidate(product_name, manufacturer, cand, session=use_sess))

    approved = [c for c in scored if c.approved and c.score >= min_approved_score]
    if not approved:
        # スコア最高を返す（呼び出し側で rejected 扱い可）
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[0] if scored else None

    approved.sort(key=lambda x: x.score, reverse=True)
    return approved[0]
