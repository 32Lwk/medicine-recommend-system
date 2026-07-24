"""PMDA import パイプラインのテスト。"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest import mock

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.pmda.common import INTERACTIONS_CSV, MANIFEST_JSON, read_csv_rows, save_json  # noqa: E402
from scripts.pmda.expand_interactions import expand_interactions_from_catalog  # noqa: E402
from scripts.pmda.expand_side_effects import expand_side_effects_from_catalog  # noqa: E402
from scripts.pmda.http_client import PmdaFetchAborted, PmdaLiveSession  # noqa: E402
from scripts.pmda.merge_into_csv import merge_side_effects  # noqa: E402
from scripts.pmda.normalize import (  # noqa: E402
    map_interaction_level,
    normalize_interaction_row,
    normalize_side_effect_row,
    pair_key,
)
from scripts.pmda.purge_catalog_expansion import purge_interactions, purge_side_effects  # noqa: E402
from scripts.pmda.queue import (  # noqa: E402
    check_live_fetch_session_gap,
    check_live_fetch_time_window,
    init_live_fetch_queue,
    mark_queue_done,
    migrate_failed_to_done,
    normalize_product_search_name,
    pop_queue_batch,
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


def test_resume_skips_done_items(tmp_path, monkeypatch):
    manifest_path = tmp_path / "manifest.json"
    manifest = {"live_fetch_queue": {"interactions": {"pending": ["A", "B", "C"], "done": ["X"], "failed": {}}}}
    save_json(manifest_path, manifest)

    def _load():
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    def _save(path, data):
        if path == manifest_path:
            manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    monkeypatch.setattr("scripts.pmda.queue.load_manifest", _load)
    monkeypatch.setattr("scripts.pmda.queue.save_json", _save)
    monkeypatch.setattr("scripts.pmda.queue.MANIFEST_JSON", manifest_path)
    batch = pop_queue_batch("interactions", max_items=2)
    assert batch == ["A", "B"]
    mark_queue_done("interactions", ["A"])
    from scripts.pmda.queue import get_live_fetch_queue

    q = get_live_fetch_queue()
    assert "A" in q["interactions"]["done"]
    assert q["interactions"]["pending"] == ["C"]


def test_session_gap_rejects_within_4h(monkeypatch):
    from datetime import datetime, timedelta, timezone

    recent = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    monkeypatch.setattr(
        "scripts.pmda.queue.load_manifest",
        lambda: {"live_fetch": {"last_session_end_at": recent}},
    )
    ok, reason = check_live_fetch_session_gap(min_hours=4.0)
    assert ok is False
    assert "gap too short" in reason


def test_time_window_rejects_daytime(monkeypatch):
    from datetime import datetime
    from scripts.pmda import queue as queue_mod

    class _FakeDT:
        @staticmethod
        def now(tz=None):
            return datetime(2026, 7, 24, 15, 0, tzinfo=tz)

    monkeypatch.setattr(queue_mod, "now_jst", lambda: _FakeDT.now(queue_mod.JST))
    ok, reason = check_live_fetch_time_window()
    assert ok is False
    assert "outside JST live window" in reason


def test_normalize_product_search_name_strips_form_and_capacity():
    assert normalize_product_search_name("イブA錠 12錠") == "イブA"
    assert normalize_product_search_name("ムヒのこどもシロップ") == "ムヒのこども"


def test_purge_catalog_expansion_removes_review_recommended(tmp_path, monkeypatch):
    ix_csv = tmp_path / "interactions.csv"
    ix_csv.write_text(
        "成分A,成分B,相互作用レベル,説明,出典,pmda_updated_at,interaction_id\n"
        "A,B,高,live,PMDA iyakuSearch,,\n"
        "A,B,中,exp,PMDA catalog pair expansion (review recommended),,\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("scripts.pmda.purge_catalog_expansion.INTERACTIONS_CSV", ix_csv)
    result = purge_interactions(dry_run=True)
    assert result["removed"] == 1
    assert result["after"] == 1


def test_merge_side_effects_live_replace(tmp_path, monkeypatch):
    se_csv = tmp_path / "side_effects.csv"
    se_csv.write_text(
        "成分名,副作用レベル,副作用症状,禁忌条件,出典\n"
        "イブプロフェン,中,旧,PMDA catalog ingredient expansion (review recommended),\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("scripts.pmda.merge_into_csv.SIDE_EFFECTS_CSV", se_csv)
    monkeypatch.setattr("scripts.pmda.merge_into_csv.INGREDIENT_DICT_JSON", tmp_path / "ing.json")
    stats = merge_side_effects(
        [
            {
                "成分名": "イブプロフェン",
                "副作用レベル": "高",
                "副作用症状": "live",
                "禁忌条件": "",
                "出典": "PMDA iyakuSearch",
            }
        ],
        live_replace=True,
    )
    rows = se_csv.read_text(encoding="utf-8")
    assert stats["live_replace"] is True
    assert "PMDA iyakuSearch" in rows
    assert "review recommended" not in rows


def test_otc_live_sample_fixture_parse():
    sample_path = ROOT / "tests" / "fixtures" / "pmda" / "otc_live_sample.json"
    data = json.loads(sample_path.read_text(encoding="utf-8"))
    for item in data["samples"]:
        parsed = PmdaLiveSession.parse_otc_detail_html(item["detail_html"])
        for key, expected in item["expected"].items():
            assert expected in parsed.get(key, ""), f"{item['product_name']} {key}"
        link = PmdaLiveSession.match_otc_product_link(item["search_html"], item["product_name"])
        assert link is not None


def test_migrate_failed_to_done(tmp_path, monkeypatch):
    manifest_path = tmp_path / "manifest.json"
    manifest = {
        "live_fetch_queue": {
            "interactions": {
                "pending": ["C"],
                "done": ["X"],
                "failed": {
                    "A": {"reason": "no_interaction_rows", "at": "2026-07-24T00:00:00+00:00"},
                    "B": {"reason": "empty_section", "at": "2026-07-24T00:00:00+00:00"},
                },
            }
        }
    }
    save_json(manifest_path, manifest)

    def _load():
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    def _save(path, data):
        manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    monkeypatch.setattr("scripts.pmda.queue.load_manifest", _load)
    monkeypatch.setattr("scripts.pmda.queue.save_json", _save)
    monkeypatch.setattr("scripts.pmda.queue.MANIFEST_JSON", manifest_path)

    result = migrate_failed_to_done("interactions", reason="no_interaction_rows")
    assert result["count"] == 1
    assert "A" in result["migrated"]
    from scripts.pmda.queue import get_live_fetch_queue

    q = get_live_fetch_queue()["interactions"]
    assert "A" in q["done"]
    assert "B" in q["failed"]
    assert "A" not in q["failed"]


def test_no_interaction_rows_marks_done_not_failed(monkeypatch):
    from scripts.pmda.fetch_interactions import fetch_interactions

    done_calls: list[list[str]] = []
    failed_calls: list[tuple[str, str, str]] = []

    monkeypatch.setattr(
        "scripts.pmda.fetch_interactions.pop_queue_batch",
        lambda source, max_items=10: ["ビタミンC"],
    )
    monkeypatch.setattr(
        "scripts.pmda.fetch_interactions.mark_queue_done",
        lambda source, items: done_calls.append(list(items)),
    )
    monkeypatch.setattr(
        "scripts.pmda.fetch_interactions.mark_queue_failed",
        lambda source, item, reason: failed_calls.append((source, item, reason)),
    )
    monkeypatch.setattr(
        "scripts.pmda.fetch_interactions.write_otc_ingredients_json",
        lambda: None,
    )
    monkeypatch.setattr(
        "scripts.pmda.fetch_interactions.load_common_rx_medications",
        lambda: ["ワーファリン"],
    )
    monkeypatch.setattr(
        "scripts.pmda.fetch_interactions.record_live_fetch_session",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "scripts.pmda.fetch_interactions.write_live_fetch_log",
        lambda payload: None,
    )
    monkeypatch.setattr(
        "scripts.pmda.fetch_interactions.write_fetch_log",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "scripts.pmda.fetch_interactions.save_json",
        lambda path, payload: None,
    )

    class _FakeSession:
        stats = type("S", (), {"aborted": False, "cache_hits": 0, "hits": 0, "errors": 0, "requested": 1, "empty_html": 0, "abort_reason": ""})()

        @property
        def aborted(self):
            return self.stats.aborted

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def fetch_packins_section(self, ingredient, section):
            return "<html>10.2併用注意 該当なし</html>"

        def parse_interactions_from_html(self, html, ingredient, partners):
            return []

    monkeypatch.setattr("scripts.pmda.fetch_interactions.PmdaLiveSession", lambda **kwargs: _FakeSession())

    result = fetch_interactions(live=True, resume=True, ingredient_batch=1, batch_size=30)
    assert result["stats"]["queue_no_data"] == ["ビタミンC"]
    assert done_calls == [["ビタミンC"]]
    assert failed_calls == []


def test_empty_section_marks_failed(monkeypatch):
    from scripts.pmda.fetch_interactions import fetch_interactions

    failed_calls: list[tuple[str, str, str]] = []

    monkeypatch.setattr(
        "scripts.pmda.fetch_interactions.pop_queue_batch",
        lambda source, max_items=10: ["ビタミンC"],
    )
    monkeypatch.setattr(
        "scripts.pmda.fetch_interactions.mark_queue_done",
        lambda source, items: None,
    )
    monkeypatch.setattr(
        "scripts.pmda.fetch_interactions.mark_queue_failed",
        lambda source, item, reason: failed_calls.append((source, item, reason)),
    )
    monkeypatch.setattr(
        "scripts.pmda.fetch_interactions.write_otc_ingredients_json",
        lambda: None,
    )
    monkeypatch.setattr(
        "scripts.pmda.fetch_interactions.load_common_rx_medications",
        lambda: ["ワーファリン"],
    )
    monkeypatch.setattr(
        "scripts.pmda.fetch_interactions.record_live_fetch_session",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "scripts.pmda.fetch_interactions.write_live_fetch_log",
        lambda payload: None,
    )
    monkeypatch.setattr(
        "scripts.pmda.fetch_interactions.write_fetch_log",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "scripts.pmda.fetch_interactions.save_json",
        lambda path, payload: None,
    )

    class _FakeSession:
        stats = type("S", (), {"aborted": False, "cache_hits": 0, "hits": 0, "errors": 0, "requested": 1, "empty_html": 0, "abort_reason": ""})()

        @property
        def aborted(self):
            return self.stats.aborted

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def fetch_packins_section(self, ingredient, section):
            return ""

    monkeypatch.setattr("scripts.pmda.fetch_interactions.PmdaLiveSession", lambda **kwargs: _FakeSession())

    fetch_interactions(live=True, resume=True, ingredient_batch=1, batch_size=30)
    assert failed_calls == [("interactions", "ビタミンC", "empty_section")]
