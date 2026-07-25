"""OTC 品名正規化・詳細 parse・マッチの fixture テスト。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.pmda.fetch_otc import pick_best_otc_hit, score_otc_match  # noqa: E402
from scripts.pmda.http_client import PmdaLiveSession  # noqa: E402
from scripts.pmda.queue import normalize_product_search_name  # noqa: E402


def test_normalize_product_search_name_strips_form_and_capacity():
    # NFKC で全角英数 → 半角
    assert normalize_product_search_name("ロキソニンＳ１２錠") == "ロキソニンS"
    assert normalize_product_search_name("パブロンゴールドＡ錠") == "パブロンゴールドA"
    assert normalize_product_search_name("バファリンＡ") == "バファリンA"


def test_score_otc_match_exact_normalized_partial():
    assert score_otc_match("バファリンA", "", "バファリンA", "") == 100
    assert score_otc_match("バファリンＡ錠", "", "バファリンＡ", "") >= 90
    assert score_otc_match("バファリン", "", "バファリンA", "") >= 50
    assert score_otc_match("完全に別物", "", "バファリンA", "") == 0
    # 空白・括弧差異
    assert score_otc_match("ニコチネルパッチ10", "", "ニコチネル パッチ10", "") >= 90
    assert score_otc_match("恵命我神散S<細粒>", "", "恵命我神散S〈細粒〉", "") >= 90


def test_pick_best_otc_hit_prefers_exact():
    hits = [
        {"product_name": "バファリンプラス", "manufacturer": "ライオン", "fname": "a"},
        {"product_name": "バファリンA", "manufacturer": "ライオン", "fname": "b"},
    ]
    best, score = pick_best_otc_hit("バファリンA", "ライオン", hits)
    assert best is not None
    assert best["fname"] == "b"
    assert score >= 90


def test_parse_otc_detail_from_fixture_sample():
    fixture = ROOT / "tests" / "fixtures" / "pmda" / "otc_live_sample.json"
    data = json.loads(fixture.read_text(encoding="utf-8"))
    sample = data["samples"][0]
    parsed = PmdaLiveSession.parse_otc_detail_html(sample["detail_html"])
    assert parsed
    expected = sample["expected"]
    for key, value in expected.items():
        assert value in (parsed.get(key) or "")


def test_extract_otc_result_hits_from_fixture_sample():
    fixture = ROOT / "tests" / "fixtures" / "pmda" / "otc_live_sample.json"
    data = json.loads(fixture.read_text(encoding="utf-8"))
    sample = data["samples"][0]
    # enrich sample HTML to ResultList shape used in production
    html = (
        "<table class='SearchResultTable' id='ResultList'>"
        "<tr><th>販売名</th><th>製造販売業者等</th></tr>"
        "<tr class='TrColor01'><td><div>"
        f"<a target='_blank' href='/PmdaSearch/otcDetail/GeneralList/001'>"
        f"{sample['product_name']}</a></div></td>"
        "<td>製造販売元／ライオン（株）</td></tr></table>"
    )
    hits = PmdaLiveSession.extract_otc_result_hits(html)
    assert len(hits) == 1
    assert hits[0]["product_name"] == sample["product_name"]
    assert hits[0]["fname"] == "001"
