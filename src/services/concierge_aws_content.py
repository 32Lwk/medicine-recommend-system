"""AWS ステージング向け: 利用者向け出力から GCP 言及を除去する。"""
from __future__ import annotations

import re
from typing import Any, Dict, List

_GCP_MENTION_RE = re.compile(
    r"GCP|Google\s*Cloud|Cloud\s*Run|Cloud\s*Build|cloudbuild|"
    r"Google\s*Cloud\s*Text-to-Speech|Cloud\s*Text-to-Speech|"
    r"asia-northeast1\.run\.app",
    re.I,
)

_GCP_DOC_SKIP = frozenset(
    {
        "01-cross-cloud-architecture.md",
        "06-line-gcp-path.md",
    }
)

_ARCH_GCP_SECTION_TITLE = "GCP 本番"


def should_strip_gcp_content() -> bool:
    from config.aws_features import is_aws_staging_site

    return is_aws_staging_site()


def skip_gcp_technical_doc(name: str) -> bool:
    """AWS ステージングでは GCP 中心の技術 SSOT を参照に含めない。"""
    if not should_strip_gcp_content():
        return False
    return name in _GCP_DOC_SKIP


def strip_gcp_mentions(text: str) -> str:
    """GCP 関連の文・行を除去し、余分な空白を整える。"""
    raw = (text or "").strip()
    if not raw or not should_strip_gcp_content():
        return raw

    lines: List[str] = []
    for line in raw.splitlines():
        chunk = line.strip()
        if not chunk:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        if _GCP_MENTION_RE.search(chunk):
            continue
        if re.search(r"GCP\s*/\s*AWS|AWS\s*/\s*GCP|GCP\s*と\s*AWS|AWS\s*と\s*GCP", chunk, re.I):
            continue
        lines.append(line.rstrip())

    merged = "\n".join(lines)
    parts = re.split(r"(?<=[。．!！?？])\s*", merged)
    kept = [p.strip() for p in parts if p.strip() and not _GCP_MENTION_RE.search(p)]
    if kept:
        merged = "".join(kept)

    merged = re.sub(r"\n{3,}", "\n\n", merged)
    merged = re.sub(r"[ \t]{2,}", " ", merged)
    return merged.strip()


def filter_architecture_sections_for_aws(
    sections: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """architecture カードから GCP 本番セクションを除外する。"""
    if not should_strip_gcp_content():
        return sections
    out: List[Dict[str, Any]] = []
    for sec in sections:
        title = str(sec.get("title") or "")
        if title == _ARCH_GCP_SECTION_TITLE:
            continue
        items = [
            str(item)
            for item in (sec.get("items") or [])
            if not _GCP_MENTION_RE.search(str(item))
        ]
        if items:
            out.append({**sec, "items": items})
    return out


def aws_architecture_grounding_rule() -> str:
    return (
        "\n\n【回答の根拠ルール】\n"
        "- 上記ドキュメントとランタイム情報に無いサービス名・URL・構成は推測で補わない。\n"
        "- この環境は AWS ステージングのみを説明対象とし、GCP や他クラウドの構成には触れない。\n"
        "- 不明な点は「公開ドキュメントに記載がありません」と述べ、創作しない。\n"
    )


def cross_cloud_grounding_rule() -> str:
    if should_strip_gcp_content():
        return aws_architecture_grounding_rule()
    return (
        "\n\n【回答の根拠ルール】\n"
        "- 上記ドキュメントとランタイム情報に無いサービス名・URL・構成は推測で補わない。\n"
        "- GCP 本番と AWS ステージングの役割分担はドキュメントの記載に従う。\n"
        "- 不明な点は「公開ドキュメントに記載がありません」と述べ、創作しない。\n"
    )
