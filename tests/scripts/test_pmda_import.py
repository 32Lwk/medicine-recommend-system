"""PMDA import パイプラインのテスト。"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.pmda.common import INTERACTIONS_CSV, read_csv_rows  # noqa: E402
from scripts.pmda.expand_interactions import expand_interactions_from_catalog  # noqa: E402
from scripts.pmda.expand_side_effects import expand_side_effects_from_catalog  # noqa: E402
from scripts.pmda.http_client import PmdaFetchAborted, PmdaLiveSession  # noqa: E402
from scripts.pmda.normalize import (  # noqa: E402
    map_interaction_level,
    normalize_interaction_row,
    pair_key,
)
from scripts.pmda.run_pmda_import import run_import  # noqa: E402
from scripts.pmda.validate_pmda_import import validate_all_staging  # noqa: E402


def test_map_interaction_level():
    assert map_interaction_level("併用禁忌") == "高"
    assert map_interaction_level("併用注意") == "中"
    assert map_interaction_level("高") == "高"


def test_normalize_interaction_row_dedupes_pair_order():
    a = normalize_interaction_row({"成分A": "ワーファリン", "成分B": "イブプロフェン", "相互作用レベル": "高", "説明": "x"})
    b = normalize_interaction_row({"成分A": "イブプロフェン", "成分B": "ワーファリン", "相互作用レベル": "高", "説明": "x"})
    assert a and b
    assert pair_key(a["成分A"], a["成分B"]) == pair_key(b["成分A"], b["成分B"])


def test_expand_interactions_reaches_500_plus():
    rows = expand_interactions_from_catalog()
    assert len(rows) >= 500
    existing = read_csv_rows(INTERACTIONS_CSV)
    for row in existing[:5]:
        norm = normalize_interaction_row(row)
        assert norm
        assert any(
            pair_key(r["成分A"], r["成分B"]) == pair_key(norm["成分A"], norm["成分B"])
            or norm["成分A"] in r["成分A"]
            or norm["成分B"] in r["成分B"]
            for r in rows
        )


def test_expand_side_effects_reaches_200_plus():
    rows = expand_side_effects_from_catalog()
    assert len(rows) >= 200


def test_run_import_dry_run_ok():
    result = run_import(
        sources=["interactions", "side_effects", "otc"],
        live=False,
        dry_run=True,
        fixture_dir=ROOT / "tests" / "fixtures" / "pmda",
    )
    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["validation"]["interactions"]["count"] >= 500
    assert result["validation"]["side_effects"]["count"] >= 200


def test_validate_all_staging_after_fetch():
    run_import(
        sources=["interactions"],
        live=False,
        dry_run=True,
        fixture_dir=ROOT / "tests" / "fixtures" / "pmda",
    )
    validation = validate_all_staging()
    assert validation["interactions"]["errors"] == []


def test_live_session_dedupes_ingredient_fetch():
    session = PmdaLiveSession(min_interval_sec=0.01, batch_size=10)
    detail = "<html>10.2併用注意 ワーファリン 出血</html>" * 5
    result = '<a onclick=\'detailDisp("PmdaSearch", "430574_1149019C1149_1_13")\'>HTML</a>'
    with mock.patch.object(session, "_fetch_result_list_with_docs", return_value=result) as mocked_search:
        with mock.patch.object(session, "fetch_iyaku_detail_html", return_value=detail):
            html1 = session.fetch_packins_section("ロキソプロフェン", "10")
            html2 = session.fetch_packins_section("ロキソプロフェン", "10")
            assert html1 == html2
            assert mocked_search.call_count == 1
            assert session.stats.cache_hits == 1
    session.close()


def test_live_session_aborts_on_429():
    session = PmdaLiveSession(min_interval_sec=0.01, batch_size=10)

    def _raise_429(*args, **kwargs):
        session._abort("HTTP 429")
        raise PmdaFetchAborted("HTTP 429")

    with mock.patch.object(session, "_request", side_effect=_raise_429):
        with mock.patch("scripts.pmda.http_client.time.sleep"):
            html = session.fetch_packins_section("イブプロフェン", "10")
    assert html == ""
    assert session.stats.aborted is True
    assert "429" in session.stats.abort_reason
    session.close()
