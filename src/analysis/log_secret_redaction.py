"""
GCP ログエクスポート / 解析パイプライン向けのシークレットマスキング。

Cloud Run 監査ログに含まれる環境変数や接続文字列を、保存・解析前に除去する。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping, MutableMapping, Sequence

REDACTED = "***REDACTED***"

SENSITIVE_ENV_NAMES = frozenset(
    {
        "DATABASE_URL",
        "OPENAI_API_KEY",
        "LINE_CHANNEL_ACCESS_TOKEN",
        "LINE_CHANNEL_SECRET",
        "DEEPL_API_KEY",
        "POSTGRES_PASSWORD",
        "POSTGRES_URL",
        "SECRET_KEY",
        "ADMIN_PASSWORD",
        "medicine-recommend-db",
        "postgres",
    }
)

SENSITIVE_ENV_NAME_MARKERS = (
    "API_KEY",
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "CREDENTIAL",
    "PRIVATE_KEY",
    "ACCESS_KEY",
)

TEXT_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"postgresql://[^:\s\"'@]+:[^@\s\"']+@"),
        "postgresql://REDACTED:REDACTED@",
    ),
    (re.compile(r"\bnpg_[A-Za-z0-9]+\b"), "npg_REDACTED"),
    (re.compile(r"\bsk-proj-[A-Za-z0-9_-]+\b"), "sk-proj-REDACTED"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "sk-REDACTED"),
    (
        re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}:fx\b"),
        "REDACTED:fx",
    ),
    (
        re.compile(
            r"R9v1xv\+[A-Za-z0-9+/=]{80,}",
        ),
        "LINE_CHANNEL_ACCESS_TOKEN_REDACTED",
    ),
)


def is_sensitive_env_name(name: str) -> bool:
    upper = name.upper()
    if upper in {item.upper() for item in SENSITIVE_ENV_NAMES}:
        return True
    return any(marker in upper for marker in SENSITIVE_ENV_NAME_MARKERS)


def redact_text(text: str) -> str:
    if not text or REDACTED in text:
        return text
    redacted = text
    for pattern, replacement in TEXT_REPLACEMENTS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def _redact_env_pair(obj: Mapping[str, Any]) -> Mapping[str, Any]:
    name = obj.get("name")
    if not isinstance(name, str) or not is_sensitive_env_name(name):
        return obj
    if "value" not in obj:
        return obj
    updated = dict(obj)
    updated["value"] = REDACTED
    return updated


def redact_object(obj: Any) -> Any:
    if isinstance(obj, str):
        return redact_text(obj)
    if isinstance(obj, list):
        return [redact_object(item) for item in obj]
    if isinstance(obj, dict):
        if "name" in obj and "value" in obj and isinstance(obj.get("name"), str):
            obj = _redact_env_pair(obj)
        result: dict = {}
        for key, value in obj.items():
            if isinstance(key, str) and isinstance(value, str) and is_sensitive_env_name(key):
                result[key] = REDACTED
            else:
                result[key] = redact_object(value)
        return result
    return obj


def redact_gcp_log_entries(entries: Sequence[dict]) -> list[dict]:
    return [redact_object(entry) for entry in entries]


def redact_json_text(text: str) -> str:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return redact_text(text)
    return json.dumps(redact_object(payload), ensure_ascii=False)


def redact_file(path: Path, *, dry_run: bool = False) -> bool:
    original = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        redacted = redact_json_text(original)
    else:
        redacted = redact_text(original)
    if redacted == original:
        return False
    if not dry_run:
        path.write_text(redacted, encoding="utf-8")
    return True


def iter_log_targets(root: Path) -> Iterable[Path]:
    for pattern in ("*.json", "*.md", "*.jsonl"):
        yield from root.rglob(pattern)


def sanitize_log_tree(root: Path, *, dry_run: bool = False) -> list[Path]:
    changed: list[Path] = []
    if not root.exists():
        return changed
    for path in sorted(iter_log_targets(root)):
        if path.is_file() and redact_file(path, dry_run=dry_run):
            changed.append(path)
    return changed
