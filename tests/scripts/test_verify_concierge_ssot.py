"""Concierge SSOT 検証のテスト。"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TECH = ROOT / "docs" / "concierge" / "technical"

REQUIRED = (
    "00-disclosure-policy.md",
    "01-cross-cloud-architecture.md",
    "02-chat-pipeline-agents.md",
    "03-deployment-operations.md",
    "04-data-security.md",
    "05-chat-pipeline-v2-flags.md",
    "06-line-gcp-path.md",
    "07-observability-ops.md",
    "08-technical-decisions.md",
    "09-glossary.md",
    "10-agent-routing-rationale.md",
    "11-app-mission-and-status.md",
    "12-technical-faq-rag.md",
    "README.md",
)


def test_technical_ssot_files_exist():
    for name in REQUIRED:
        assert (TECH / name).is_file(), name


def test_technical_ssot_no_env_assignments():
    import re

    pattern = re.compile(r"[A-Z][A-Z0-9_]{2,}=[^\s`]+")
    for path in TECH.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        match = pattern.search(text)
        assert match is None, f"{path.name}: {match.group() if match else ''}"


def test_changelog_digest_exists():
    assert (ROOT / "static" / "changelog-digest.json").is_file()


def test_kb_sync_script_references_concierge_docs():
    sync = (ROOT / "scripts" / "sync-concierge-kb-to-s3.sh").read_text(encoding="utf-8")
    assert "docs/concierge" in sync
