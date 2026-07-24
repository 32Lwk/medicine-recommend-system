"""PMDA パーサー・品質フィルタのテスト。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.pmda.http_client import PmdaLiveSession  # noqa: E402
from scripts.pmda.quality_filter import filter_interactions, filter_side_effects  # noqa: E402
from scripts.pmda.raw_store import raw_file_path  # noqa: E402


def test_extract_section_handles_spaced_markers():
    html = (
        "<html><body>"
        "10. 相互作用 10.2 併用注意(併用に注意すること) "
        "薬剤名等 臨床症状・措置方法 機序・危険因子 "
        "クマリン系抗凝血剤 ワルファリン 抗凝血作用を増強するおそれがあるので注意し、必要があれば減量すること。 "
        "11. 副作用 11.1 重大な副作用 ショック、アナフィラキシー "
        "18. 薬効薬理"
        "</body></html>"
    )
    s10 = PmdaLiveSession.extract_section_from_html(html, "10")
    s11 = PmdaLiveSession.extract_section_from_html(html, "11")
    assert "ワルファリン" in s10
    assert "11. 副作用" not in s10
    assert "ショック" in s11
    assert "18. 薬効" not in s11


def test_extract_section_does_not_return_full_document():
    html = "<html><body>2. 禁忌 only document without section 10</body></html>"
    assert PmdaLiveSession.extract_section_from_html(html, "10") == ""


def test_parse_side_effects_from_real_raw_sample():
    path = raw_file_path("ロキソプロフェンナトリウム水和物")
    if not path.is_file():
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    section11 = PmdaLiveSession.extract_section_from_html(payload["detail_html"], "11")
    rows = PmdaLiveSession(min_interval_sec=0, batch_size=0).parse_side_effects_from_html(
        section11, "ロキソプロフェンナトリウム水和物"
    )
    assert rows
    assert "11." in rows[0]["副作用症状"]
    assert "JavaScript" not in rows[0]["副作用症状"]
    kept, stats = filter_side_effects(rows)
    assert kept
    assert stats["accepted"] == 1


def test_quality_filter_rejects_boilerplate_interaction():
    rows = [
        {
            "成分A": "X",
            "成分B": "Y",
            "相互作用レベル": "中",
            "説明": "当ウェブサイトを快適にご覧いただくには、ブラウザのJavaScript設定を有効(オン)にしていただく必要がございます。",
            "出典": "PMDA iyakuSearch",
        }
    ]
    kept, stats = filter_interactions(rows)
    assert not kept
    assert stats["reject_html_boilerplate"] == 1
