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


def _extract_highlights(section_body: str, *, max_items: int = 24) -> Tuple[str, ...]:
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
    r"プロンプト|LLM|intent_router|dispatcher|"
    r"\.env|env\s*ゲート|env\s*未設定|Secrets|buildspec|CodeBuild|CodePipeline|"
    r"config/|Dockerfile|ECS|ECR|WAF|CloudFront|S3|IAM|OAuth|"
    r"commit\s+[0-9a-f]{6,}|ブランチ\s+\S+|"
    r"data/|Medicine eval|OK 率|\d+/\d+|raw \d+%|ingestion failed|metadata boolean|"
    r"§\d|live fetch|live_replace|reparse_from_raw|quality_filter|"
    r"side_effects|interactions PMDA|\d+\.?\d*%→\d+%|"
    r"catalog expansion|detail_html|live のみ|ingredients/",
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
    r"meta_triage|dispatcher|Neon|docker|Postgres|sslmode|"
    r"env\s|\.env|Secrets|設定/env|環境変数|medicine\.yutok\.dev|aws\.medicine",
    re.I,
)

_POSITIVE_REWRITE_RULES: tuple[tuple[str, str], ...] = (
    (r"Translate\s*/?\s*Polly|Amazon Translate|Amazon Polly|TTS_PROVIDER", "翻訳と読み上げの選択肢が増えました"),
    (r"Bedrock KB|ナレッジベース|RAG", "技術的な質問への案内が厚くなりました"),
    (r"更新履歴.*表示|doc_changelog|CHANGELOG.*要約", "更新内容の案内が見やすくなりました"),
    (r"技術質問.*GCP|architecture|技術.*回答", "技術的な質問への案内が整いました"),
    (r"CodeBuild|static S3|CloudFront invalidation|自動.*同期", "画面の更新がよりスムーズに反映されるようになりました"),
    (r"デプロイ.*遅延|ビルド.*遅延|tune-aws-ecs", "表示の反映が速くなるよう調整しました"),
    (r"障害.*UX|system_error|llm_unavailable|fail loud", "不具合時の案内が分かりやすくなりました"),
    (r"Chat Pipeline v2|IntentRouter PRIMARY", "相談の流れがより安定しました"),
    (r"風邪.*水泳|cold_symptom|RECO_.*V2|年齢未入力", "風邪の相談で候補が出やすくなりました"),
    (r"処理中ステータス|マスコット", "処理中の表示が分かりやすくなりました"),
    (r"オンボーディング|はじめの案内", "はじめの案内が見やすくなりました"),
    (r"チャットビューポート|シーズン装飾|季節", "チャット画面の見た目が整いました"),
    (r"画像.*CDN|R2|OTC 画像|パッケージ画像", "お薬の画像表示が充実しました"),
    (r"Comprehend Medical|Personalize", "相談内容の理解・おすすめ表示がより賢くなりました"),
    (
        r"PMDA live fetch|添付文書 HTML|data/pmda|raw HTML 永続化|680 件 raw",
        "公的なお薬情報の取り込みがより正確になりました",
    ),
    (
        r"§マーカー|パーサー|merge バグ|全文フォールバック|正本 CSV|CSV を再生成|"
        r"interactions.*side_effects|品質フィルタ",
        "相互作用・副作用の案内がより信頼しやすくなりました",
    ),
    (r"PMDA 公的情報|市販薬検索|§10|§11", "公的データに基づく案内が強化されました"),
)

_RELEASE_THEME_LABELS: tuple[tuple[str, str], ...] = (
    (r"AWS/Cloudflare|ステージング|Translate|Polly|Bedrock", "体験の向上"),
    (r"Concierge|更新履歴|doc_changelog", "案内の改善"),
    (r"Chat Pipeline|障害|CodePipeline|ECS", "安定性の向上"),
    (r"風邪|RECO_|cold_symptom", "相談まわりの改善"),
    (r"UX|オンボーディング|Sage Terrace|画面", "使いやすさの向上"),
)


def _is_dev_only_bullet(text: str) -> bool:
    if _DEV_BULLET_RE.search(text):
        return True
    return bool(_USER_FACING_SKIP_RE.search(text))


def _strip_infra_noise(text: str) -> str:
    line = (text or "").strip()
    line = re.sub(r"GCP 本番（[^）]+）を変更せず\s*", "", line)
    line = re.sub(r"AWS ステージング（[^）]+）(で|に)?\s*", "", line)
    line = re.sub(r"（commit\s+[0-9a-f]+\）?", "", line, flags=re.I)
    line = re.sub(r"env ゲート付きで\s*", "", line, flags=re.I)
    line = re.sub(r"env 未設定で\s*", "", line, flags=re.I)
    line = re.sub(r"`?(?:data|src|static|scripts)/[^\s`、。]+`?", "", line)
    line = re.sub(r"（\d+\s*件）", "", line)
    return re.sub(r"\s+", " ", line).strip(" 、。")


def _positive_rewrite(text: str) -> str:
    line = _strip_infra_noise(text)
    if not line:
        return ""
    for pattern, replacement in _POSITIVE_REWRITE_RULES:
        if re.search(pattern, line, re.I):
            return replacement
    for pattern, replacement in _USER_DISPLAY_REPLACEMENTS:
        line = re.sub(pattern, replacement, line, flags=re.I)
    line = re.sub(
        r"(を|の)(実装|追加|修正|改善|更新|刷新|整備|導入)(した|しました|した。)",
        r"が\2されました",
        line,
    )
    line = re.sub(r"^あわせて\s*", "", line)
    line = re.sub(r"^ブランチ\s+\S+\s+に、?", "", line)
    line = re.sub(r"一括 ON", "標準で有効", line)
    line = re.sub(r"\s+", " ", line).strip(" ・、。")
    if len(line) < 8:
        return ""
    if re.match(r"^[にをがはへでと]\s", line):
        return ""
    if _is_dev_only_bullet(line):
        return ""
    if re.search(r"問題|不足|エラー|障害|修正|解消|fail|bug", line, re.I):
        line = re.sub(r"(問題|不足|エラー|障害).{0,12}(修正|解消|改善)", "案内が整い", line)
        line = re.sub(r"を修正した", "が改善されました", line)
    return line


def _format_positive_bullet(text: str, *, max_len: int = 72) -> str:
    line = _positive_rewrite(text)
    if not line:
        return ""
    line = line.lstrip("＋ ").strip()
    if len(line) > max_len:
        cut = line[: max_len - 1]
        if "、" in cut:
            cut = cut.rsplit("、", 1)[0]
        line = cut.rstrip(" 、。") + "…"
    return line


def _soften_for_user_display(text: str, *, max_len: int = 96) -> str:
    line = soften_changelog_highlight(text, max_len=max_len + 80)
    if not line or _is_dev_only_bullet(line):
        return ""
    bullet = _format_positive_bullet(line, max_len=max_len)
    return bullet.lstrip("＋ ").strip() if bullet.startswith("＋ ") else bullet


def overview_to_user_bullets(overview: str, *, max_items: int = 3) -> List[str]:
    """CHANGELOG の概要文からユーザー向け箇条書きを作る（ファイルパスは使わない）。"""
    ov = (overview or "").strip()
    if not ov:
        return []
    ov = _strip_infra_noise(ov)
    ov = re.sub(r"^ブランチ\s+\S+\s+に、?", "", ov)
    ov = re.sub(r"[。．]$", "", ov)
    ov = re.sub(r"、?を実装$", "", ov)
    chunks = [c.strip() for c in re.split(r"[、。]", ov) if c.strip()]
    items: List[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        bullet = _format_positive_bullet(chunk)
        if not bullet or bullet in seen:
            continue
        if len(bullet) < 4:
            continue
        items.append(bullet)
        seen.add(bullet)
        if len(items) >= max_items:
            break
    return items


def _user_friendly_release_label(raw: str, *, max_len: int = 28) -> str:
    t = (raw or "").strip()
    shortcuts = (
        (r"AWS/Cloudflare|ステージング展開", "体験の向上"),
        (r"Concierge|更新履歴", "案内の改善"),
        (r"Chat Pipeline|障害 UX|CodePipeline", "安定性の向上"),
        (r"CHANGELOG Concierge.*", "案内と画面"),
        (r"Phase 4.*", "会話の振り分け"),
        (r"ローカル DB.*", "安定性と入力ブロック"),
        (r"UX 品質.*", "使いやすさ"),
        (r"風邪|RECO_", "相談まわり"),
    )
    for pat, label in shortcuts:
        if re.search(pat, t, re.I):
            return label
    for pat, label in _RELEASE_THEME_LABELS:
        if re.search(pat, t, re.I):
            return label
    if "・" in t:
        t = t.split("・", 1)[0]
    t = re.sub(r"\s*/\s*", "・", t)
    t = re.sub(r"CI\s*自動化", "自動更新", t, flags=re.I)
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


def _release_date_key(heading: str) -> str:
    m = _RELEASE_DATE_RE.search(heading or "")
    return m.group(1) if m else ""


def release_user_facing_items(
    release: ChangelogRelease,
    *,
    max_items: int = 4,
) -> List[str]:
    """概要＋ハイライトからユーザー向け箇条書き（ファイルパスは除外）。"""
    items = overview_to_user_bullets(release.overview, max_items=max_items)
    if len(items) >= max_items:
        return items[:max_items]
    seen = set(items)
    for highlight in release.highlights:
        bullet = _format_positive_bullet(highlight)
        if not bullet or bullet in seen:
            continue
        items.append(bullet)
        seen.add(bullet)
        if len(items) >= max_items:
            break
    return items


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
    deploy_commit = str(load_build_meta().get("gitCommitShort") or "").strip()[:7]

    grouped: List[dict[str, Any]] = []
    for idx, release in enumerate(releases[:max_releases]):
        items = release_user_facing_items(
            release,
            max_items=max_items_per_release,
        )
        if not items:
            continue
        date_key = _release_date_key(release.heading)
        if grouped and grouped[-1].get("_date_key") == date_key and date_key:
            bucket = grouped[-1]
            bucket["_sources"] = int(bucket.get("_sources") or 1) + 1
            bucket["title"] = date_key
        else:
            bucket = {
                "_date_key": date_key,
                "_sources": 1,
                "title": release_user_section_title(release.heading),
                "items": [],
            }
            if idx == 0 and deploy_commit:
                bucket["commit"] = deploy_commit
            grouped.append(bucket)

        raw_cap = max_items_per_release * int(bucket.get("_sources") or 1)
        cap = raw_cap if detailed else min(raw_cap, 3)
        seen = set(bucket["items"])
        for item in items:
            if item in seen:
                continue
            if len(bucket["items"]) >= cap:
                break
            bucket["items"].append(item)
            seen.add(item)

    sections: List[dict[str, Any]] = []
    for bucket in grouped:
        bucket.pop("_date_key", None)
        bucket.pop("_sources", None)
        if bucket.get("items"):
            sections.append(bucket)
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

