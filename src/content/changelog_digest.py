"""CHANGELOG.md のコンパクト要約と build-meta 参照（Concierge 用）。"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CHANGELOG_PATH = _REPO_ROOT / "CHANGELOG.md"
_BUILD_META_PATH = _REPO_ROOT / "static" / "build-meta.json"

_HEADER_DATE_RE = re.compile(
    r"^\*\*最終更新日:\s*(.+?)\*\*(.*)$",
    re.MULTILINE,
)
_SECTION_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
_OVERVIEW_HEADING = "### 概要"
_TABLE_LINE_RE = re.compile(r"^\s*\|")
_BULLET_RE = re.compile(r"^-\s+(.+)$")


@dataclass(frozen=True)
class ChangelogRelease:
    heading: str
    overview: str
    highlights: Tuple[str, ...]


def _repo_changelog_text() -> str:
    if not _CHANGELOG_PATH.is_file():
        return ""
    return _CHANGELOG_PATH.read_text(encoding="utf-8")


def _strip_md_noise(text: str) -> str:
    lines: List[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or _TABLE_LINE_RE.match(line):
            continue
        if line.startswith("```"):
            continue
        line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
        line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
        line = re.sub(r"`([^`]+)`", r"\1", line)
        lines.append(line)
    return re.sub(r"\s+", " ", " ".join(lines)).strip()


def _extract_overview(section_body: str, *, max_chars: int = 420) -> str:
    idx = section_body.find(_OVERVIEW_HEADING)
    if idx < 0:
        return ""
    rest = section_body[idx + len(_OVERVIEW_HEADING) :]
    next_h3 = rest.find("\n### ")
    if next_h3 >= 0:
        rest = rest[:next_h3]
    plain = _strip_md_noise(rest)
    if len(plain) <= max_chars:
        return plain
    return plain[: max_chars - 1].rstrip() + "…"


def _extract_highlights(section_body: str, *, max_items: int = 8) -> Tuple[str, ...]:
    items: List[str] = []
    for raw in section_body.splitlines():
        if _TABLE_LINE_RE.match(raw):
            continue
        match = _BULLET_RE.match(raw.strip())
        if not match:
            continue
        item = _strip_md_noise(match.group(1))
        if not item or item.startswith("tests/"):
            continue
        if len(item) > 140:
            item = item[:139].rstrip() + "…"
        items.append(item)
        if len(items) >= max_items:
            break
    return tuple(items)


def parse_changelog_releases(
    text: str,
    *,
    max_releases: int = 8,
) -> Tuple[str, List[ChangelogRelease]]:
    """CHANGELOG 本文から最終更新日ラベルと直近リリース要約を抽出する。"""
    header_date = ""
    header_match = _HEADER_DATE_RE.search(text)
    if header_match:
        header_date = (header_match.group(1) + header_match.group(2)).strip()

    matches = list(_SECTION_RE.finditer(text))
    releases: List[ChangelogRelease] = []
    for i, match in enumerate(matches):
        if len(releases) >= max_releases:
            break
        heading = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end]
        overview = _extract_overview(body)
        highlights = _extract_highlights(body)
        if not overview and not highlights:
            overview = _strip_md_noise(body)[:280]
        releases.append(
            ChangelogRelease(
                heading=heading,
                overview=overview,
                highlights=highlights,
            )
        )
    return header_date, releases


@lru_cache(maxsize=1)
def load_build_meta() -> dict[str, str]:
    """static/build-meta.json（デプロイ時に埋め込まれた Git メタ）。"""
    try:
        if _BUILD_META_PATH.is_file():
            data = json.loads(_BUILD_META_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items() if v is not None}
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return {}


@lru_cache(maxsize=4)
def load_changelog_digest(*, max_releases: int = 6) -> Tuple[str, Tuple[ChangelogRelease, ...]]:
    text = _repo_changelog_text()
    if not text:
        return "", ()
    header_date, releases = parse_changelog_releases(text, max_releases=max_releases)
    return header_date, tuple(releases)


def format_build_meta_block() -> str:
    meta = load_build_meta()
    lines = ["【デプロイ反映情報（参照）】"]
    commit = meta.get("gitCommitShort", "").strip()
    date_iso = meta.get("gitCommitDateIso", "").strip()
    if commit:
        lines.append(f"- 反映コミット（短縮）: {commit}")
    if date_iso:
        lines.append(f"- 反映日（ISO）: {date_iso}")
    if len(lines) == 1:
        lines.append("- （デプロイ環境のビルドメタは未設定です）")
    else:
        lines.append(
            "- 上記は本番・デプロイ環境のビルド時に埋め込まれた情報です。"
            "CHANGELOG の最終更新日と異なる場合があります。"
        )
    return "\n".join(lines)


def format_changelog_digest_block(
    *,
    max_releases: int = 6,
    max_total_chars: int = 14_000,
) -> str:
    """LLM プロンプト用の CHANGELOG 要約（全文は渡さない）。"""
    header_date, releases = load_changelog_digest(max_releases=max_releases)
    lines = ["【開発履歴サマリー（CHANGELOG.md 直近要約・唯一の根拠）】"]
    if header_date:
        lines.append(f"ドキュメント記載の最終更新日: {header_date}")
    lines.append(
        f"以下は CHANGELOG.md の直近 {len(releases)} 件です。"
        "記載にない変更は推測で補わないでください。"
    )
    lines.append("")

    for release in releases:
        block = [f"## {release.heading}"]
        if release.overview:
            block.append(f"概要: {release.overview}")
        if release.highlights:
            block.append("主な変更:")
            block.extend(f"・{item}" for item in release.highlights)
        lines.append("\n".join(block))
        lines.append("")
        if sum(len(x) + 1 for x in lines) > max_total_chars:
            lines.append("…（以降の履歴は省略。詳細はリポジトリの CHANGELOG.md を参照）")
            break

    return "\n".join(lines).strip()


def format_changelog_reference_for_llm(
    *,
    max_releases: int = 6,
    max_total_chars: int = 14_000,
) -> str:
    """build-meta + CHANGELOG ダイジェストを結合した参照ブロック。"""
    return "\n\n".join(
        [
            format_build_meta_block(),
            format_changelog_digest_block(
                max_releases=max_releases,
                max_total_chars=max_total_chars,
            ),
        ]
    )


def changelog_doc_title() -> str:
    return "更新履歴・最近の変更（CHANGELOG 要約）"
