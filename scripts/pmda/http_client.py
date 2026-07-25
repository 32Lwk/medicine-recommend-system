"""PMDA サイト向け HTTP クライアント（礼儀正しい live fetch）。"""
from __future__ import annotations

import json
import random
import re
import time
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin

import httpx

from scripts.pmda.common import USER_AGENT, normalize_text

PMDA_OTC_SEARCH = "https://www.pmda.go.jp/PmdaSearch/otcSearch/"
PMDA_OTC_DETAIL = "https://www.pmda.go.jp/PmdaSearch/otcDetail/"
PMDA_IYAKU_SEARCH = "https://www.pmda.go.jp/PmdaSearch/iyakuSearch/"
PMDA_IYAKU_DETAIL = "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/"

PMDA_SOURCE_LABEL = "PMDA iyakuSearch"
PMDA_OTC_SOURCE_LABEL = "PMDA OTC Search"
PMDA_LIVE_SOURCE_LABELS = frozenset({"PMDA iyakuSearch", "PMDA PackinsSearch"})

_AGE_RESTRICT_RE = re.compile(
    r"([^。\n]{0,40}(?:歳|才)[^。\n]{0,40}(?:服用しない|使用しない|与えない|飲ませない)[^。\n]*)"
)
_OTC_INGREDIENT_ROW_RE = re.compile(
    r"<tr[^>]*>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*</tr>",
    re.I | re.S,
)

JITTER_MIN_SEC = 2.5
JITTER_MAX_SEC = 5.0
FAST_BACKFILL_JITTER_MIN_SEC = 0.8
FAST_BACKFILL_JITTER_MAX_SEC = 1.5
BACKOFF_429_SEC = (60, 120, 300)
MAX_EMPTY_HTML_STREAK = 3

PARTNER_ALIASES: Dict[str, List[str]] = {
    "ワーファリン": ["ワーファリン", "ワルファリン"],
    "クマリン系抗凝血薬": ["クマリン", "クマリン系", "クマリン系抗凝血剤", "クマリン系抗凝固剤"],
}

_PMDA_BOILERPLATE_PATTERNS = (
    r"当ウェブサイトを快適にご覧いただくには、ブラウザのJavaScript設定を有効\(オン\)にしていただく必要がございます。",
    r"Pmda\s*独立行政法人\s*医薬品医療機器総合機構",
    r"標準\s*大\s*特大\s*医療用医薬品\s*詳細表示",
    r"処方せん医薬品(?:以外の医薬品)?",
    r"添付文書番号\s*企業コード\s*作成又は改訂年月",
)

_SECTION10_START = (
    r"10\.2\s*併用注意",
    r"10\.1\s*併用禁忌",
    r"10\.\s*相互作用",
)
_SECTION10_END = (
    r"11\.\s*副作用",
    r"11\.1\s*重大な副作用",
)
_SECTION11_START = (
    r"11\.1\s*重大な副作用",
    r"11\.2\s*その他の副作用",
    r"11\.\s*副作用",
)
_SECTION11_END = (
    r"12\.\s*臨床検査",
    r"13\.\s*過量投与",
    r"14\.\s*適用上の注意",
    r"16\.\s*薬物動態",
    r"17\.\s*臨床成績",
    r"18\.\s*薬効",
)


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
        fast_backfill: bool = False,
    ) -> None:
        self.min_interval_sec = min_interval_sec
        self.batch_size = batch_size
        if fast_backfill:
            self._jitter_min = FAST_BACKFILL_JITTER_MIN_SEC
            self._jitter_max = FAST_BACKFILL_JITTER_MAX_SEC
        else:
            self._jitter_min = JITTER_MIN_SEC
            self._jitter_max = JITTER_MAX_SEC
        self.fast_backfill = fast_backfill
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
        self._otc_form_data: Optional[Dict[str, str]] = None
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
        delay = random.uniform(self._jitter_min, self._jitter_max)
        delay = max(delay, self.min_interval_sec)
        elapsed = time.time() - self._last_request_at
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self._last_request_at = time.time()

    def _can_request(self) -> bool:
        if self.stats.aborted:
            return False
        if self.batch_size > 0 and self.stats.requested >= self.batch_size:
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

    def _fetch_detail_html_for_ingredient(self, ingredient: str) -> Tuple[str, str, str]:
        """Returns (detail_html, detail_fname, result_list_html)."""
        if self.stats.aborted:
            return "", "", ""
        cache_key = f"ingredient_detail::{normalize_text(ingredient)}"
        if cache_key in self._html_cache:
            self.stats.cache_hits += 1
            cached = self._html_cache[cache_key]
            meta_key = f"ingredient_meta::{normalize_text(ingredient)}"
            meta = self._html_cache.get(meta_key, "")
            parts = meta.split("\x1f", 2) if meta else ["", ""]
            fname = parts[0] if parts else ""
            result_html = parts[1] if len(parts) > 1 else ""
            return cached, fname, result_html
        try:
            result_html = self._fetch_result_list_with_docs(ingredient)
        except PmdaFetchAborted:
            return "", "", ""
        if not result_html:
            return "", "", ""
        fnames = self._extract_detail_fnames(result_html)
        if not fnames:
            self.stats.empty_html += 1
            meta_key = f"ingredient_meta::{normalize_text(ingredient)}"
            self._html_cache[meta_key] = f"\x1f{result_html}"
            return "", "", result_html
        detail_html = self.fetch_iyaku_detail_html(fnames[0])
        if detail_html:
            self._html_cache[cache_key] = detail_html
            meta_key = f"ingredient_meta::{normalize_text(ingredient)}"
            self._html_cache[meta_key] = f"{fnames[0]}\x1f{result_html}"
        return detail_html, fnames[0], result_html

    def fetch_ingredient_sections(self, ingredient: str) -> Tuple[str, str, Dict[str, str]]:
        detail_html, detail_fname, result_list_html = self._fetch_detail_html_for_ingredient(ingredient)
        meta = {
            "ingredient": normalize_text(ingredient),
            "detail_html": detail_html,
            "detail_fname": detail_fname,
            "result_list_html": result_list_html,
        }
        if not detail_html:
            return "", "", meta
        section10 = self._extract_section(detail_html, "10")
        section11 = self._extract_section(detail_html, "11")
        ing_key = normalize_text(ingredient)
        if section10:
            self._html_cache[f"{ing_key}::10"] = section10
        if section11:
            self._html_cache[f"{ing_key}::11"] = section11
        meta["section10"] = section10
        meta["section11"] = section11
        return section10, section11, meta

    def fetch_packins_section(self, ingredient: str, section: str) -> str:
        """ユニーク成分×セクションを 1 回だけ fetch（キャッシュあり）。"""
        if self.stats.aborted:
            return ""
        cache_key = f"{normalize_text(ingredient)}::{section}"
        if cache_key in self._html_cache:
            self.stats.cache_hits += 1
            return self._html_cache[cache_key]

        detail_html, _, _ = self._fetch_detail_html_for_ingredient(ingredient)
        if not detail_html:
            return ""

        section_html = self._extract_section(detail_html, section)
        if section_html:
            self._html_cache[cache_key] = section_html
        return section_html

    @staticmethod
    def strip_pmda_boilerplate(text: str) -> str:
        cleaned = text or ""
        for pattern in _PMDA_BOILERPLATE_PATTERNS:
            cleaned = re.sub(pattern, " ", cleaned)
        return normalize_text(cleaned)

    @staticmethod
    def extract_section_from_html(html: str, section: str) -> str:
        text = PmdaLiveSession.strip_pmda_boilerplate(PmdaLiveSession.strip_html(html))
        if section == "10":
            start_patterns = _SECTION10_START
            end_patterns = _SECTION10_END
        elif section == "11":
            start_patterns = _SECTION11_START
            end_patterns = _SECTION11_END
        else:
            return ""

        best = ""
        for start_pattern in start_patterns:
            for match in re.finditer(start_pattern, text):
                start = match.start()
                end = len(text)
                for end_pattern in end_patterns:
                    end_match = re.search(end_pattern, text[match.end() :])
                    if end_match:
                        end = min(end, match.end() + end_match.start())
                chunk = normalize_text(text[start:end])
                if len(chunk) > len(best):
                    best = chunk
        return best if len(best) >= 25 else ""

    @staticmethod
    def _extract_section(html: str, section: str) -> str:
        return PmdaLiveSession.extract_section_from_html(html, section)

    def _ensure_otc_form_data(self) -> Dict[str, str]:
        if self._otc_form_data is not None:
            return dict(self._otc_form_data)
        resp = self._request("GET", PMDA_OTC_SEARCH)

        class _OtcFormParser(HTMLParser):
            def __init__(self) -> None:
                super().__init__()
                self.in_form = False
                self.data: Dict[str, str] = {}
                self._current_select: Optional[str] = None
                self._opts: List[tuple[str, bool]] = []

            def handle_starttag(self, tag: str, attrs) -> None:
                d = dict(attrs)
                if tag == "form" and d.get("id") == "otcSearchForm":
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

        otc_parser = _OtcFormParser()
        otc_parser.feed(resp.text)
        self._otc_form_data = otc_parser.data or {
            "ListRows": "20",
            "howtoMatchRadioValue": "1",
            "nameWord": "",
        }
        return dict(self._otc_form_data)

    def _build_otc_search_payload(self, product_name: str) -> Dict[str, str]:
        data = self._ensure_otc_form_data()
        data.update(
            {
                "nameWord": product_name,
                "howtoMatchRadioValue": "1",
                "ListRows": "20",
                "btnA.x": "39",
                "btnA.y": "12",
            }
        )
        return data

    def fetch_otc_search(self, product_name: str) -> str:
        if not self._can_request():
            return ""
        try:
            payload = self._build_otc_search_payload(product_name)
            resp = self._request("POST", PMDA_OTC_SEARCH, data=payload)
            html = resp.text
        except PmdaFetchAborted:
            return ""
        try:
            self._record_html(html, allow_no_results=True)
        except PmdaFetchAborted:
            return ""
        return html

    def fetch_otc_detail_html(self, fname_or_url: str) -> str:
        """OTC 詳細 HTML を取得。fname または GeneralList URL 断片を受け取る。"""
        fname = fname_or_url.strip()
        if "otcDetail/" in fname:
            fname = fname.split("otcDetail/", 1)[1]
        fname = fname.lstrip("/")
        if fname.startswith("GeneralList/"):
            fname = fname[len("GeneralList/") :]
        cache_key = f"otc_detail::{fname}"
        if cache_key in self._html_cache:
            self.stats.cache_hits += 1
            return self._html_cache[cache_key]
        if not self._can_request():
            return ""
        url = f"{PMDA_OTC_DETAIL}{fname}"
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
    def extract_otc_result_hits(html: str) -> List[Dict[str, str]]:
        """検索結果テーブルから (製品名, メーカー, detail fname) を抽出。"""
        hits: List[Dict[str, str]] = []
        table_match = re.search(
            r"<table[^>]*id=['\"]ResultList['\"][^>]*>(.*?)</table>",
            html or "",
            re.I | re.S,
        )
        body = table_match.group(1) if table_match else (html or "")
        row_re = re.compile(
            r"<tr[^>]*>\s*<td[^>]*>\s*<div>\s*<a[^>]+href=['\"]([^'\"]+)['\"][^>]*>(.*?)</a>"
            r".*?</td>\s*<td[^>]*>(.*?)</td>",
            re.I | re.S,
        )
        for href, name_html, mfr_html in row_re.findall(body):
            name = normalize_text(re.sub(r"<[^>]+>", " ", name_html))
            mfr = normalize_text(re.sub(r"<[^>]+>", " ", mfr_html))
            mfr = re.sub(r"^(製造販売元|販売元|製造元|発売元)\s*/\s*", "", mfr)
            fname = href
            if "otcDetail/" in href:
                fname = href.split("otcDetail/", 1)[1]
            fname = fname.split("GeneralList/", 1)[-1].strip("/")
            if name and fname:
                hits.append(
                    {
                        "product_name": name,
                        "manufacturer": mfr,
                        "fname": fname,
                        "href": urljoin(PMDA_OTC_SEARCH, href),
                        "text": name,
                    }
                )
        return hits

    @staticmethod
    def parse_otc_detail_html(html: str) -> Dict[str, str]:
        """OTC 詳細 HTML から効能・用法・成分・年齢制限などを抽出。"""
        fields: Dict[str, str] = {}
        pair_re = re.compile(
            r"<tr[^>]*>\s*<td[^>]*class=['\"]head['\"][^>]*>(.*?)</td>\s*"
            r"<td[^>]*class=['\"]deta['\"][^>]*>(.*?)</td>\s*</tr>",
            re.I | re.S,
        )
        for raw_key, raw_val in pair_re.findall(html or ""):
            key = normalize_text(re.sub(r"<[^>]+>", " ", raw_key))
            if key == "成分分量":
                ingredients: List[str] = []
                for ing_html, qty_html in _OTC_INGREDIENT_ROW_RE.findall(raw_val):
                    ing = normalize_text(re.sub(r"<[^>]+>", " ", ing_html))
                    qty = normalize_text(re.sub(r"<[^>]+>", " ", qty_html))
                    if not ing or ing == "成分":
                        continue
                    ingredients.append(f"{ing}{(' ' + qty) if qty and qty != '分量' else ''}".strip())
                if ingredients:
                    fields["成分"] = "、".join(ingredients)
                # keep leading quantity note if present
                lead = normalize_text(re.sub(r"<table.*", "", raw_val, flags=re.I | re.S))
                lead = normalize_text(re.sub(r"<[^>]+>", " ", lead))
                if lead and "成分" in fields:
                    fields["成分"] = f"{lead} {fields['成分']}".strip()
                continue
            val = normalize_text(re.sub(r"<[^>]+>", " ", raw_val))
            if key and val:
                fields[key] = val

        efficacy = fields.get("効能・効果") or fields.get("効能効果") or ""
        usage = fields.get("用法・用量") or fields.get("用法用量") or ""
        ingredients = fields.get("成分") or fields.get("成分分量") or ""
        age = fields.get("年齢制限") or ""

        # テーブル構造が無いプレーンテキスト向けフォールバック
        if not any((efficacy, usage, ingredients)):
            text = normalize_text(re.sub(r"<[^>]+>", " ", html or ""))
            for label, key in (
                (r"効能[・･]?効果", "efficacy"),
                (r"用法[・･]?用量", "usage"),
                (r"年齢制限", "age"),
                (r"成分(?!分量)", "ingredients"),
            ):
                m = re.search(
                    label + r"\s*[:：]?\s*(.+?)(?=(?:効能|用法|成分|年齢制限|添加物|$))",
                    text,
                )
                if not m:
                    continue
                val = normalize_text(m.group(1)).rstrip("。")
                if key == "efficacy":
                    efficacy = val
                elif key == "usage":
                    usage = val
                elif key == "age":
                    age = val
                elif key == "ingredients":
                    ingredients = val

        if not age:
            for blob in (usage, fields.get("使用上の注意") or "", fields.get("■してはいけないこと") or ""):
                m = _AGE_RESTRICT_RE.search(blob)
                if m:
                    age = normalize_text(m.group(1))
                    break
            if not age and re.search(r"(歳|才)未満[：:]\s*服用しない", usage):
                m2 = re.search(r"([^。]*?(?:歳|才)未満[：:]\s*服用しないこと?)", usage)
                if m2:
                    age = normalize_text(m2.group(1))

        product = fields.get("製品名") or fields.get("承認販売名") or ""
        pmda_yakkou = fields.get("薬効分類") or ""
        pmda_risk = fields.get("リスク区分") or fields.get("医薬品区分") or ""
        manufacturer = fields.get("製造販売会社") or ""
        if manufacturer:
            manufacturer = normalize_text(re.split(r"添付文書情報", manufacturer)[0])
            manufacturer = re.sub(r"^会社名[：:]\s*", "", manufacturer)

        out = {
            "製品名": product,
            "メーカー名": manufacturer,
            # 社内タクソノミ用の「分類」「医薬品の種類」には入れない
            "pmda_薬効分類": pmda_yakkou,
            "pmda_リスク区分": pmda_risk,
            "効能効果": efficacy,
            "用法用量": usage,
            "年齢制限": age,
            "成分": ingredients,
            "出典": PMDA_OTC_SOURCE_LABEL,
        }
        if any(
            out.get(k)
            for k in ("効能効果", "用法用量", "成分", "年齢制限", "pmda_薬効分類", "pmda_リスク区分")
        ):
            return out
        return {}

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

    @staticmethod
    def _interaction_description(text: str, partner: str, idx: int) -> str:
        aliases = PARTNER_ALIASES.get(partner, [partner])
        start = max(0, idx - 20)
        end = min(len(text), idx + 420)
        snippet = normalize_text(text[start:end])
        for alias in aliases:
            alias_idx = snippet.find(alias)
            if alias_idx >= 0:
                snippet = snippet[alias_idx:]
                break
        snippet = re.sub(r"^[\s、,.]+", "", snippet)
        snippet = re.sub(r"\s+", " ", snippet).strip()
        return snippet[:500]

    def parse_interactions_from_html(
        self,
        html: str,
        ingredient_a: str,
        partners: List[str],
    ) -> List[Dict[str, str]]:
        text = self.strip_pmda_boilerplate(self.strip_html(html) if "<" in html else html)
        if not text:
            return []
        rows: List[Dict[str, str]] = []
        level_default = "高" if "併用禁忌" in text else "中"
        seen_partners: Set[str] = set()
        for partner in partners:
            if not partner or partner in seen_partners:
                continue
            idx = -1
            for alias in PARTNER_ALIASES.get(partner, [partner]):
                idx = text.find(alias)
                if idx >= 0:
                    break
            if idx < 0:
                continue
            seen_partners.add(partner)
            snippet = self._interaction_description(text, partner, idx)
            if len(snippet) < 30:
                continue
            level = "高" if "併用禁忌" in snippet or partner in ("ワーファリン", "MAO阻害薬") else level_default
            rows.append(
                {
                    "成分A": ingredient_a,
                    "成分B": partner,
                    "相互作用レベル": level,
                    "説明": snippet,
                    "出典": PMDA_SOURCE_LABEL,
                }
            )
            self.stats.hits += 1
        return rows

    @staticmethod
    def _summarize_side_effects(text: str) -> str:
        cleaned = normalize_text(text)
        if not cleaned:
            return ""
        for pattern in (
            r"11\.1\s*重大な副作用",
            r"11\.2\s*その他の副作用",
            r"11\.\s*副作用",
        ):
            match = re.search(pattern, cleaned)
            if match:
                cleaned = cleaned[match.start() :]
                break
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        for end_pat in (r"17\.\s*臨床成績", r"18\.\s*薬効"):
            end_match = re.search(end_pat, cleaned)
            if end_match:
                cleaned = cleaned[: end_match.start()].strip()
                break
        if len(cleaned) > 800:
            cut = cleaned[:800]
            last_space = cut.rfind("。")
            if last_space >= 400:
                cut = cut[: last_space + 1]
            cleaned = cut
        return cleaned

    def parse_side_effects_from_html(self, html: str, ingredient: str) -> List[Dict[str, str]]:
        text = self.strip_pmda_boilerplate(self.strip_html(html) if "<" in html else html)
        if not text:
            return []
        summary = self._summarize_side_effects(text)
        if len(summary) < 50:
            return []
        level = "高" if "重大な副作用" in summary or "11.1" in summary else "中"
        self.stats.hits += 1
        return [
            {
                "成分名": ingredient,
                "副作用レベル": level,
                "副作用症状": summary,
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
        return self.extract_otc_result_hits(html)[:20]

    def parse_interactions_from_html(self, html: str, ingredient_a: str, ingredient_b: str) -> List[Dict[str, str]]:
        return super().parse_interactions_from_html(html, ingredient_a, [ingredient_b])
