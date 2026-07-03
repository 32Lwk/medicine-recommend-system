"""CHANGELOG.md のコンパクト要約と build-meta 参照（Concierge 用）。"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CHANGELOG_PATH = _REPO_ROOT / "CHANGELOG.md"
_BUILD_META_PATH = _REPO_ROOT / "static" / "build-meta.json"
_BAKED_DIGEST_PATH = _REPO_ROOT / "static" / "changelog-digest.json"

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


@lru_cache(maxsize=1)
def _load_baked_digest() -> Optional[Tuple[str, Tuple[ChangelogRelease, ...]]]:
    """Docker / Cloud Run 向け: ビルド時に焼き込んだ JSON（CHANGELOG.md 不要）。"""
    try:
        if not _BAKED_DIGEST_PATH.is_file():
            return None
        data = json.loads(_BAKED_DIGEST_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        header_date = str(data.get("header_date") or "").strip()
        raw_releases = data.get("releases")
        if not isinstance(raw_releases, list):
            return None
        releases: List[ChangelogRelease] = []
        for item in raw_releases:
            if not isinstance(item, dict):
                continue
            heading = str(item.get("heading") or "").strip()
            if not heading:
                continue
            highlights_raw = item.get("highlights")
            highlights = tuple(
                str(x).strip() for x in highlights_raw if str(x).strip()
            ) if isinstance(highlights_raw, list) else ()
            releases.append(
                ChangelogRelease(
                    heading=heading,
                    overview=str(item.get("overview") or "").strip(),
                    highlights=highlights,
                )
            )
        return header_date, tuple(releases)
    except (OSError, json.JSONDecodeError, TypeError):
        return None


@lru_cache(maxsize=4)
def load_changelog_digest(*, max_releases: int = 6) -> Tuple[str, Tuple[ChangelogRelease, ...]]:
    baked = _load_baked_digest()
    if baked is not None:
        header_date, releases = baked
        return header_date, releases[:max_releases]

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
    if not releases:
        lines.append(
            "（要約データが未配置です。デプロイ時に static/changelog-digest.json の"
            "生成を確認してください。）"
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
    return "最近の更新"


_RELEASE_DATE_RE = re.compile(r"(\d{4}年\d{1,2}月\d{1,2}日)")


def release_display_title(heading: str, *, max_len: int = 36) -> str:
    """Sage カード用の短い見出し。"""
    text = (heading or "").strip()
    if not text:
        return "更新"
    if "—" in text:
        date_part, _, rest = text.partition("—")
        date_match = _RELEASE_DATE_RE.search(date_part)
        label = rest.strip() or date_part.strip()
        if date_match:
            prefix = date_match.group(1)
            if len(label) > max_len:
                label = label[: max_len - 1].rstrip() + "…"
            return f"{prefix} — {label}"
    if len(text) > max_len + 4:
        return text[: max_len - 1].rstrip() + "…"
    return text


def soften_changelog_highlight(text: str, *, max_len: int = 96) -> str:
    """開発者向け CHANGELOG 行をユーザー向けに短く整える。"""
    line = (text or "").strip()
    if not line:
        return ""
    line = re.sub(r"`([^`]+)`", r"\1", line)
    line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
    line = re.sub(r"\bdoc_changelog\b", "更新内容の案内", line, flags=re.I)
    line = re.sub(r"\bintent\b", "機能", line, flags=re.I)
    if re.match(r"^(src/|static/|tests/|config/|docs/)", line) and ":" in line:
        line = line.split(":", 1)[1].strip()
    line = re.sub(r"\s+", " ", line).strip()
    if len(line) > max_len:
        line = line[: max_len - 1].rstrip() + "…"
    return line


_DEV_BULLET_RE = re.compile(
    r"src/|static/|CHANGELOG\.md|build-meta|\.py\b|scripts/|docker-compose|"
    r"meta_triage|concierge_intent|ALLOWLIST|LEGACY_FALLBACK|Neon dev|"
    r"プロンプト|LLM|intent_router|dispatcher",
    re.I,
)

_USER_DISPLAY_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    (r"doc_changelog\s*intent", "更新内容の案内"),
    (r"CHANGELOG\s*要約", "更新履歴の案内"),
    (r"IntentRouter", "会話の振り分け"),
    (r"app_about", "自己紹介まわり"),
    (r"処理中ステータスマスコット", "処理中の表示"),
    (r"オンボーディング", "はじめの案内"),
    (r"チャットビューポート", "チャット画面"),
    (r"シーズン装飾", "季節の装飾"),
    (r"管理画面（admin_chat）", "管理画面"),
    (r"Sage Terrace UI", "画面デザイン"),
)


_USER_FACING_SKIP_RE = re.compile(
    r"Concierge|intent|IntentRouter|doc_changelog|CHANGELOG|プローブ|ガード|"
    r"meta_triage|dispatcher|Neon|docker|Postgres|sslmode",
    re.I,
)


def _is_dev_only_bullet(text: str) -> bool:
    if _DEV_BULLET_RE.search(text):
        return True
    return bool(_USER_FACING_SKIP_RE.search(text))


def _soften_for_user_display(text: str, *, max_len: int = 72) -> str:
    line = soften_changelog_highlight(text, max_len=max_len + 40)
    if not line or _is_dev_only_bullet(line):
        return ""
    for pattern, replacement in _USER_DISPLAY_REPLACEMENTS:
        line = re.sub(pattern, replacement, line, flags=re.I)
    line = re.sub(r"\s+", " ", line).strip(" ・")
    if len(line) > max_len:
        line = line[: max_len - 1].rstrip() + "…"
    return line


def overview_to_user_bullets(overview: str, *, max_items: int = 3) -> List[str]:
    """CHANGELOG の概要文からユーザー向け箇条書きを作る（ファイルパスは使わない）。"""
    ov = (overview or "").strip()
    if not ov:
        return []
    ov = re.sub(r"^ブランチ\s+\S+\s+に、?", "", ov)
    ov = re.sub(r"[。．]$", "", ov)
    ov = re.sub(r"、?を実装$", "", ov)
    chunks = [c.strip() for c in re.split(r"、", ov) if c.strip()]
    items: List[str] = []
    for chunk in chunks:
        cleaned = _soften_for_user_display(chunk)
        if cleaned and len(cleaned) >= 4:
            items.append(cleaned)
        if len(items) >= max_items:
            break
    return items


def _user_friendly_release_label(raw: str, *, max_len: int = 18) -> str:
    t = (raw or "").strip()
    shortcuts = (
        (r"CHANGELOG Concierge.*", "案内と画面"),
        (r"Phase 4.*", "会話の振り分け"),
        (r"ローカル DB.*", "安定性と入力ブロック"),
        (r"UX 品質.*", "使いやすさ"),
    )
    for pat, label in shortcuts:
        if re.search(pat, t, re.I):
            return label
    if "・" in t:
        t = t.split("・", 1)[0]
    if len(t) > max_len:
        return t[: max_len - 1].rstrip() + "…"
    return t


def release_user_section_title(heading: str) -> str:
    """セクション見出し（日付中心・短く）。"""
    m = _RELEASE_DATE_RE.search(heading or "")
    date = m.group(1) if m else ""
    if "—" in (heading or ""):
        _, _, rest = heading.partition("—")
        label = _user_friendly_release_label(rest)
        if date and label:
            return f"{date}（{label}）"
    return date or "更新"


def format_changelog_deploy_subtitle(header_date: str) -> str:
    """導入文直下の最終更新日（コミットは先頭セクション見出しへ）。"""
    base = (header_date or "").split("（", 1)[0].strip()
    if base:
        return f"最終更新日 {base}"
    return ""


def wants_changelog_detail(
    user_text: str,
    history: Optional[List[Dict[str, str]]],
) -> bool:
    """直前が更新履歴カードのとき、詳しく／もっと等は詳細表示。"""
    from src.services.concierge_agent_history import is_meta_follow_up_utterance

    if not is_meta_follow_up_utterance(user_text):
        return False
    for msg in reversed(history or []):
        role = msg.get("type") or msg.get("role")
        if role == "bot":
            intent = msg.get("concierge_intent") or (
                (msg.get("diagnosis") or {}).get("kind")
                if isinstance(msg.get("diagnosis"), dict)
                else None
            )
            return intent in ("doc_changelog", "concierge_doc_changelog")
        if role == "user":
            break
    return False


def build_changelog_ui_sections(
    releases: Tuple[ChangelogRelease, ...],
    *,
    max_releases: int = 2,
    max_items_per_release: int = 3,
    detailed: bool = False,
) -> List[dict[str, Any]]:
    """Sage status カードの sections 用（概要ベース・ユーザー向け文言）。"""
    if detailed:
        max_releases = min(max(max_releases, 4), 6)
        max_items_per_release = min(max(max_items_per_release, 4), 6)
    sections: List[dict[str, Any]] = []
    seen_titles: set[str] = set()
    deploy_commit = str(load_build_meta().get("gitCommitShort") or "").strip()[:7]
    for idx, release in enumerate(releases[:max_releases]):
        items = overview_to_user_bullets(
            release.overview,
            max_items=max_items_per_release,
        )
        if not items:
            continue
        title = release_user_section_title(release.heading)
        if title in seen_titles:
            title = f"{title} ②"
        seen_titles.add(title)
        section: dict[str, Any] = {"title": title, "items": items}
        if idx == 0 and deploy_commit:
            section["commit"] = deploy_commit
        sections.append(section)
    return sections


def format_changelog_llm_reference(
    releases: Tuple[ChangelogRelease, ...],
    header_date: str,
    *,
    max_releases: int = 4,
) -> str:
    """LLM 向け参照（ユーザーにそのまま見せないメタ文は入れない）。"""
    lines: List[str] = []
    if header_date:
        lines.append(f"最終更新: {header_date}")
    for release in releases[:max_releases]:
        lines.append(f"- {release.heading}")
        if release.overview:
            lines.append(f"  概要: {release.overview}")
        for item in release.highlights[:5]:
            lines.append(f"  ・{soften_changelog_highlight(item, max_len=140)}")
    return "\n".join(lines).strip()


def changelog_unavailable_user_message() -> str:
    """要約データが無いときの固定文案（LLM を通さない）。"""
    meta = load_build_meta()
    commit = str(meta.get("gitCommitShort") or "").strip()
    date_iso = str(meta.get("gitCommitDateIso") or "").strip()
    lines = [
        "いま詳しい更新履歴を読み込めませんでした。",
        "しばらくしてから、もう一度お試しください。",
    ]
    if date_iso or commit:
        detail = []
        if date_iso:
            detail.append(f"反映日 {date_iso}")
        if commit:
            detail.append(f"ビルド {commit}")
        lines.insert(1, "（" + " / ".join(detail) + "）")
    return "\n\n".join(lines)


def changelog_fallback_intro(header_date: str, releases: Tuple[ChangelogRelease, ...]) -> str:
    if releases:
        latest = release_display_title(releases[0].heading, max_len=48)
        return (
            f"最近のアップデートをまとめました。"
            f"直近では「{latest}」などの改善を行っています。"
        )
    if header_date:
        base = header_date.split("（", 1)[0].strip()
        return f"更新履歴の最終記録は {base} です。"
    return changelog_unavailable_user_message()

