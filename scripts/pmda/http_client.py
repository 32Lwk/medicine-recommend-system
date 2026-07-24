"""PMDA サイト向け HTTP クライアント（礼儀正しい live fetch）。"""
from __future__ import annotations

import json
import random
import re
import time
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin

import httpx

from scripts.pmda.common import USER_AGENT, normalize_text
from scripts.pmda.queue import normalize_product_search_name

PMDA_OTC_SEARCH = "https://www.pmda.go.jp/PmdaSearch/otcSearch/"
PMDA_IYAKU_SEARCH = "https://www.pmda.go.jp/PmdaSearch/iyakuSearch/"
PMDA_IYAKU_DETAIL = "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/"

PMDA_SOURCE_LABEL = "PMDA iyakuSearch"
PMDA_LIVE_SOURCE_LABELS = frozenset({"PMDA iyakuSearch", "PMDA PackinsSearch"})

JITTER_MIN_SEC = 2.5
JITTER_MAX_SEC = 5.0
BACKOFF_429_SEC = (60, 120, 300)
MAX_EMPTY_HTML_STREAK = 3

PARTNER_ALIASES: Dict[str, List[str]] = {
    "ワーファリン": ["ワーファリン", "ワルファリン"],
    "クマリン系抗凝血薬": ["クマリン", "クマリン系"],
}


class PmdaFetchAborted(Exception):
    """403/429/連続 empty で live fetch を中断。"""


@dataclass
class PmdaLiveStats:
    requested: int = 0
    cache_hits: int = 0
    hits: int = 0
    errors: int = 0
    empty_html: int = 0
    aborted: bool = False
    abort_reason: str = ""
    elapsed_sec: float = 0.0
    started_at: float = field(default_factory=time.time)

    def finish(self) -> None:
        self.elapsed_sec = round(time.time() - self.started_at, 2)


class _IyakuSearchFormParser(HTMLParser):
    """iyakuSearchForm のデフォルト値を収集。"""

    def __init__(self) -> None:
        super().__init__()
        self.in_form = False
        self.data: Dict[str, str] = {}
        self._current_select: Optional[str] = None
        self._opts: List[tuple[str, bool]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        d = dict(attrs)
        if tag == "form" and d.get("id") == "iyakuSearchForm":
            self.in_form = True
            return
        if not self.in_form:
            return
        if tag == "input":
            name = d.get("name")
            typ = d.get("type", "text").lower()
            if not name:
                return
            if typ in ("checkbox", "radio"):
                if "checked" in d:
                    self.data[name] = d.get("value", "on")
            elif typ not in ("image", "button", "submit"):
                self.data.setdefault(name, d.get("value", ""))
        elif tag == "select":
            self._current_select = d.get("name")
            self._opts = []
        elif tag == "option" and self._current_select:
            self._opts.append((d.get("value", ""), "selected" in d))

    def handle_endtag(self, tag: str) -> None:
        if tag == "form":
            self.in_form = False
        if tag == "select" and self._current_select:
            val = next((v for v, sel in self._opts if sel), self._opts[0][0] if self._opts else "")
            self.data[self._current_select] = val
            self._current_select = None


class _LinkTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: List[Dict[str, str]] = []
        self._in_anchor = False
        self._href = ""
        self._text_parts: List[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href", "")
        if href:
            self._in_anchor = True
            self._href = href
            self._text_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._in_anchor:
            text = normalize_text("".join(self._text_parts))
            if text and self._href:
                self.links.append({"href": self._href, "text": text})
            self._in_anchor = False
            self._href = ""
            self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_anchor:
            self._text_parts.append(data)


class PmdaLiveSession:
    """単一 httpx Client・成分単位キャッシュ・iyakuSearch 経由の低速アクセス。"""

    def __init__(
        self,
        *,
        min_interval_sec: float = 3.0,
        batch_size: int = 30,
        timeout_sec: float = 30.0,
    ) -> None:
        self.min_interval_sec = min_interval_sec
        self.batch_size = batch_size
        self.stats = PmdaLiveStats()
        self._client = httpx.Client(
            timeout=timeout_sec,
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Language": "ja,en;q=0.8",
            },
            follow_redirects=True,
        )
        self._html_cache: Dict[str, str] = {}
        self._form_data: Optional[Dict[str, str]] = None
        self._form_loaded = False
        self._empty_streak = 0
        self._429_attempt = 0
        self._last_request_at = 0.0

    def close(self) -> None:
        self.stats.finish()
        self._client.close()

    def __enter__(self) -> "PmdaLiveSession":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    @property
    def aborted(self) -> bool:
        return self.stats.aborted

    def _abort(self, reason: str) -> None:
        self.stats.aborted = True
        self.stats.abort_reason = reason

    def _sleep_jitter(self) -> None:
        delay = random.uniform(JITTER_MIN_SEC, JITTER_MAX_SEC)
        delay = max(delay, self.min_interval_sec)
        elapsed = time.time() - self._last_request_at
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self._last_request_at = time.time()

    def _can_request(self) -> bool:
        if self.stats.aborted:
            return False
        if self.stats.requested >= self.batch_size:
            self._abort("batch_size_exceeded")
            return False
        return True

    def _record_html(self, html: str, *, allow_no_results: bool = False) -> None:
        text = normalize_text(html)
        invalid = (
            len(text) < 80
            or "条件が指定されていません" in text
            or "予期せぬエラー" in text
            or "入力された条件が正しくありません" in text
        )
        if allow_no_results and "該当するデータはありません" in text:
            invalid = False
        if invalid:
            self.stats.empty_html += 1
            self._empty_streak += 1
            if self._empty_streak >= MAX_EMPTY_HTML_STREAK:
                self._abort("consecutive_empty_html")
                raise PmdaFetchAborted("consecutive_empty_html")
        else:
            self._empty_streak = 0

    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        if not self._can_request():
            raise PmdaFetchAborted(self.stats.abort_reason or "aborted")
        self._sleep_jitter()
        self.stats.requested += 1
        for attempt in range(len(BACKOFF_429_SEC) + 1):
            try:
                resp = self._client.request(method, url, **kwargs)
                if resp.status_code in (403, 429):
                    resp.raise_for_status()
                self._429_attempt = 0
                return resp
            except httpx.HTTPStatusError as exc:
                code = exc.response.status_code
                if code == 403:
                    self.stats.errors += 1
                    self._abort(f"HTTP {code}")
                    raise PmdaFetchAborted(f"HTTP {code}") from exc
                if code == 429:
                    self.stats.errors += 1
                    if self._429_attempt < len(BACKOFF_429_SEC):
                        time.sleep(BACKOFF_429_SEC[self._429_attempt])
                        self._429_attempt += 1
                        continue
                    self._abort(f"HTTP {code}")
                    raise PmdaFetchAborted(f"HTTP {code}") from exc
                self.stats.errors += 1
                raise
            except httpx.HTTPError as exc:
                self.stats.errors += 1
                raise PmdaFetchAborted(str(exc)) from exc
        raise PmdaFetchAborted("HTTP 429")

    def _ensure_form_data(self) -> Dict[str, str]:
        if self._form_data is not None:
            return dict(self._form_data)
        resp = self._request("GET", PMDA_IYAKU_SEARCH)
        parser = _IyakuSearchFormParser()
        parser.feed(resp.text)
        self._form_data = parser.data
        self._form_loaded = True
        return dict(self._form_data)

    def _build_search_payload(self, ingredient: str) -> Dict[str, str]:
        data = self._ensure_form_data()
        data.update(
            {
                "nameWord": ingredient,
                "iyakuHowtoNameSearchRadioValue": "2",
                "howtoMatchRadioValue": "1",
                "ListRows": "10",
                "changeColumnsList": "0",
                "dispColumnsList[0]": "1",
                "_dispColumnsList[0]": "on",
                "btnA.x": "1",
                "btnA.y": "1",
            }
        )
        return data

    @staticmethod
    def _extract_detail_fnames(html: str) -> List[str]:
        patterns = [
            r'detailDisp\("PmdaSearch", "([^"]+)"\)',
            r"detailDisp\('PmdaSearch', '([^']+)'\)",
            r"/PmdaSearch/iyakuDetail/ResultDataSetXML/([^\"'>\s]+)",
        ]
        seen: Set[str] = set()
        fnames: List[str] = []
        for pat in patterns:
            for match in re.findall(pat, html):
                if match in seen:
                    continue
                seen.add(match)
                fnames.append(match)
        return fnames

    def _fetch_result_list_with_docs(self, ingredient: str) -> str:
        payload = self._build_search_payload(ingredient)
        resp = self._request("POST", PMDA_IYAKU_SEARCH, data=payload)
        try:
            self._record_html(resp.text, allow_no_results=True)
        except PmdaFetchAborted:
            return ""
        fnames = self._extract_detail_fnames(resp.text)
        if fnames:
            return resp.text
        payload["changeColumnsList"] = "0"
        ajax = self._request(
            "POST",
            f"{PMDA_IYAKU_SEARCH}CulumChangeRequest/0",
            data=payload,
        )
        try:
            body = ajax.json()
        except json.JSONDecodeError:
            self.stats.errors += 1
            return resp.text
        result_list = body.get("ResultList") or ""
        if result_list:
            try:
                self._record_html(result_list, allow_no_results=True)
            except PmdaFetchAborted:
                return ""
        return result_list or resp.text

    def fetch_iyaku_detail_html(self, fname: str) -> str:
        cache_key = f"detail::{fname}"
        if cache_key in self._html_cache:
            self.stats.cache_hits += 1
            return self._html_cache[cache_key]
        if not self._can_request():
            return ""
        url = f"{PMDA_IYAKU_DETAIL}{fname}"
        try:
            resp = self._request("GET", url)
        except PmdaFetchAborted:
            return ""
        try:
            self._record_html(resp.text)
        except PmdaFetchAborted:
            return ""
        self._html_cache[cache_key] = resp.text
        return resp.text

    def fetch_packins_section(self, ingredient: str, section: str) -> str:
        """ユニーク成分×セクションを 1 回だけ fetch（キャッシュあり）。"""
        if self.stats.aborted:
            return ""
        cache_key = f"{normalize_text(ingredient)}::{section}"
        if cache_key in self._html_cache:
            self.stats.cache_hits += 1
            return self._html_cache[cache_key]

        try:
            result_html = self._fetch_result_list_with_docs(ingredient)
        except PmdaFetchAborted:
            return ""
        if not result_html:
            return ""
        fnames = self._extract_detail_fnames(result_html)
        if not fnames:
            self.stats.empty_html += 1
            return ""

        detail_html = self.fetch_iyaku_detail_html(fnames[0])
        if not detail_html:
            return ""

        section_html = self._extract_section(detail_html, section)
        if section_html:
            self._html_cache[cache_key] = section_html
        return section_html

    @staticmethod
    def _extract_section(html: str, section: str) -> str:
        text = PmdaLiveSession.strip_html(html)
        if section == "10":
            start_markers = ["10.2併用注意", "10.1併用禁忌", "10.相互作用"]
            end_markers = ["11.副作用", "11.1重大な副作用"]
        elif section == "11":
            start_markers = ["11.1重大な副作用", "11.2その他の副作用", "11.副作用"]
            end_markers = ["12.臨床検査", "14.適用上の注意"]
        else:
            return text

        best = ""
        for marker in start_markers:
            start = 0
            while True:
                idx = text.find(marker, start)
                if idx < 0:
                    break
                end = len(text)
                for end_marker in end_markers:
                    end_idx = text.find(end_marker, idx + len(marker))
                    if end_idx >= 0:
                        end = min(end, end_idx)
                chunk = text[idx:end]
                if len(chunk) > len(best):
                    best = chunk
                start = idx + len(marker)
        if len(best) >= 80:
            return best
        return text

    def fetch_otc_search(self, product_name: str) -> str:
        if not self._can_request():
            return ""
        query = normalize_product_search_name(product_name) or product_name
        try:
            resp = self._request(
                "POST",
                PMDA_OTC_SEARCH,
                data={
                    "nameWord": query,
                    "howtoMatchRadioValue": "1",
                    "ListRows": "20",
                    "btnA": "検索",
                },
            )
            html = resp.text
        except PmdaFetchAborted:
            return ""
        try:
            self._record_html(html, allow_no_results=True)
        except PmdaFetchAborted:
            return ""
        return html

    def fetch_otc_detail_html(self, url: str) -> str:
        cache_key = f"otc_detail::{url}"
        if cache_key in self._html_cache:
            self.stats.cache_hits += 1
            return self._html_cache[cache_key]
        if not self._can_request():
            return ""
        try:
            resp = self._request("GET", url)
        except PmdaFetchAborted:
            return ""
        try:
            self._record_html(resp.text)
        except PmdaFetchAborted:
            return ""
        self._html_cache[cache_key] = resp.text
        return resp.text

    @staticmethod
    def match_otc_product_link(
        html: str,
        product_name: str,
        *,
        prefix_len: int = 6,
    ) -> Optional[Dict[str, str]]:
        links = PmdaLiveSession.extract_links(html, PMDA_OTC_SEARCH)
        if not links:
            return None
        raw = normalize_text(product_name)
        normalized = normalize_product_search_name(product_name)
        prefix = normalized[:prefix_len] if len(normalized) >= prefix_len else normalized

        def _score(link_text: str) -> int:
            text = normalize_text(link_text)
            if raw and raw == text:
                return 100
            if normalized and normalized == normalize_product_search_name(text):
                return 90
            if normalized and normalized in text:
                return 80
            if prefix and len(prefix) >= 4 and text.startswith(prefix):
                return 60
            if raw and raw in text:
                return 50
            return 0

        best: Optional[Dict[str, str]] = None
        best_score = 0
        for link in links:
            if "pdf" in link["href"].lower():
                continue
            score = _score(link["text"])
            if score > best_score:
                best_score = score
                best = link
        return best if best_score >= 50 else None

    @staticmethod
    def parse_otc_detail_html(html: str) -> Dict[str, str]:
        text = PmdaLiveSession.strip_html(html)
        fields: Dict[str, str] = {}

        def _extract(label: str, aliases: Optional[List[str]] = None) -> str:
            keys = [label] + (aliases or [])
            for key in keys:
                pattern = rf"{re.escape(key)}\s*[:：]?\s*([^。]+(?:。|$))"
                match = re.search(pattern, text)
                if match:
                    return normalize_text(match.group(1))[:500]
            return ""

        fields["効能効果"] = _extract("効能・効果", ["効能効果", "効能"])
        fields["用法用量"] = _extract("用法・用量", ["用法用量", "用法"])
        fields["成分"] = _extract("成分", ["有効成分"])
        fields["年齢制限"] = _extract("年齢制限", ["使用上の注意", "用法"])
        if not fields["年齢制限"]:
            age_match = re.search(r"(\d+\s*歳(?:未満|以上)?(?:の(?:小児|子供|乳幼児))?[^。]{0,40})", text)
            if age_match:
                fields["年齢制限"] = normalize_text(age_match.group(1))[:120]
        return {k: v for k, v in fields.items() if v}

    def fetch_and_parse_otc_product(self, product_name: str) -> Optional[Dict[str, str]]:
        html = self.fetch_otc_search(product_name)
        if not html:
            return None
        link = self.match_otc_product_link(html, product_name)
        if not link:
            return None
        detail_html = self.fetch_otc_detail_html(link["href"])
        if not detail_html:
            return None
        parsed = self.parse_otc_detail_html(detail_html)
        if not parsed:
            return None
        self.stats.hits += 1
        parsed["_pmda_title"] = link["text"]
        parsed["_pmda_url"] = link["href"]
        return parsed

    @staticmethod
    def extract_links(html: str, base_url: str) -> List[Dict[str, str]]:
        parser = _LinkTextParser()
        parser.feed(html or "")
        out: List[Dict[str, str]] = []
        for item in parser.links:
            href = urljoin(base_url, item["href"])
            out.append({"href": href, "text": item["text"]})
        return out

    @staticmethod
    def strip_html(text: str) -> str:
        cleaned = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text or "")
        cleaned = re.sub(r"(?s)<.*?>", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return normalize_text(cleaned)

    @staticmethod
    def _partner_in_text(partner: str, text: str) -> bool:
        aliases = PARTNER_ALIASES.get(partner, [partner])
        return any(alias in text for alias in aliases)

    def parse_interactions_from_html(
        self,
        html: str,
        ingredient_a: str,
        partners: List[str],
    ) -> List[Dict[str, str]]:
        text = self.strip_html(html) if "<" in html else html
        if not text:
            return []
        rows: List[Dict[str, str]] = []
        level_default = "中"
        if "併用禁忌" in text:
            level_default = "高"
        for partner in partners:
            if not partner or not self._partner_in_text(partner, text):
                continue
            idx = -1
            for alias in PARTNER_ALIASES.get(partner, [partner]):
                idx = text.find(alias)
                if idx >= 0:
                    break
            if idx < 0:
                continue
            snippet = text[max(0, idx - 80) : idx + 180]
            level = "高" if "併用禁忌" in snippet or partner in ("ワーファリン", "MAO阻害薬") else level_default
            rows.append(
                {
                    "成分A": ingredient_a,
                    "成分B": partner,
                    "相互作用レベル": level,
                    "説明": snippet[:240],
                    "出典": PMDA_SOURCE_LABEL,
                }
            )
            self.stats.hits += 1
        return rows

    def parse_side_effects_from_html(self, html: str, ingredient: str) -> List[Dict[str, str]]:
        text = self.strip_html(html) if "<" in html else html
        if not text:
            return []
        level = "高" if "重大な副作用" in text else "中"
        symptoms: List[str] = []
        for marker in ("眠気", "発疹", "ショック", "胃", "吐", "めまい", "下痢", "肝"):
            if marker in text:
                symptoms.append(marker)
        snippet = "、".join(symptoms[:5]) if symptoms else text[:200]
        self.stats.hits += 1
        return [
            {
                "成分名": ingredient,
                "副作用レベル": level,
                "副作用症状": snippet[:240],
                "禁忌条件": "",
                "出典": PMDA_SOURCE_LABEL,
            }
        ]


class PmdaHttpClient(PmdaLiveSession):
    def __init__(self, *, min_interval_sec: float = 3.0, timeout_sec: float = 30.0, live: bool = True):
        super().__init__(min_interval_sec=min_interval_sec, batch_size=10_000, timeout_sec=timeout_sec)
        self.live = live

    def search_packins_by_ingredient(self, ingredient: str, *, item_section: str = "") -> str:
        if not self.live:
            return ""
        return self.fetch_packins_section(ingredient, item_section)

    def search_otc_by_name(self, product_name: str) -> List[Dict[str, str]]:
        if not self.live:
            return []
        html = self.fetch_otc_search(product_name)
        links = self.extract_links(html, PMDA_OTC_SEARCH)
        hits: List[Dict[str, str]] = []
        for link in links:
            if product_name not in link["text"] and normalize_text(product_name) not in link["text"]:
                continue
            if "pdf" in link["href"].lower():
                continue
            hits.append(link)
        return hits[:20]

    def parse_interactions_from_html(self, html: str, ingredient_a: str, ingredient_b: str) -> List[Dict[str, str]]:
        return super().parse_interactions_from_html(html, ingredient_a, [ingredient_b])
