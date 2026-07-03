"""CHANGELOG ダイジェストと doc_changelog ルーティング。"""
from __future__ import annotations

from src.content.changelog_digest import (
    format_changelog_reference_for_llm,
    load_build_meta,
    parse_changelog_releases,
)
from src.services.concierge_intent import probe_meta_concierge_intent


SAMPLE_CHANGELOG = """# 開発履歴・更新日誌

**最終更新日: 2026年7月3日**（テスト用）

---

## 2026年7月3日 — テストリリース A

### 概要

**ブランチ `feature/x`** に、機能 A を実装。

| 列 | 値 |
|----|-----|
| a | b |

### セクション1

- 変更点 Alpha
- 変更点 Beta

## 2026年6月1日 — テストリリース B

### 概要

古いリリースの概要です。

- 変更点 Gamma
"""


def test_parse_changelog_releases_extracts_header_and_sections():
    header, releases = parse_changelog_releases(SAMPLE_CHANGELOG, max_releases=2)
    assert "2026年7月3日" in header
    assert len(releases) == 2
    assert releases[0].heading.startswith("2026年7月3日")
    assert "機能 A" in releases[0].overview
    assert "変更点 Alpha" in releases[0].highlights


def test_format_changelog_reference_is_bounded():
    ref = format_changelog_reference_for_llm(max_releases=3)
    assert "CHANGELOG" in ref or "開発履歴" in ref
    assert len(ref) < 20_000
    assert "439070" not in ref  # 全文サイズが混入していない


def test_load_build_meta_reads_json():
    meta = load_build_meta()
    assert isinstance(meta, dict)


def test_probe_meta_changelog_intent():
    assert probe_meta_concierge_intent("最近のあなたの更新内容を教えて") == "doc_changelog"
    assert probe_meta_concierge_intent("CHANGELOGを見せて") == "doc_changelog"
    assert probe_meta_concierge_intent("頭痛がします") is None
