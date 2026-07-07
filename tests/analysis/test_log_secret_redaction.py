"""Tests for log secret redaction."""

from __future__ import annotations

import json

from src.analysis.log_secret_redaction import (
    REDACTED,
    is_sensitive_env_name,
    redact_gcp_log_entries,
    redact_object,
    redact_text,
)


def test_is_sensitive_env_name_matches_known_keys():
    assert is_sensitive_env_name("DATABASE_URL")
    assert is_sensitive_env_name("OPENAI_API_KEY")
    assert is_sensitive_env_name("medicine-recommend-db")
    assert not is_sensitive_env_name("APP_ENV")


def test_redact_text_masks_connection_string_and_api_keys():
    raw = (
        "postgresql://neondb_owner:npg_secret123@ep-example.aws.neon.tech/neondb "
        "openai=sk-proj-abcDEF123 "
        "deepl=***REDACTED***:fx"
    )
    redacted = redact_text(raw)
    assert "npg_secret123" not in redacted
    assert "sk-proj-abcDEF123" not in redacted
    assert "postgresql://REDACTED:REDACTED@" in redacted
    assert "REDACTED:fx" in redacted


def test_redact_object_masks_cloud_run_env_block():
    payload = {
        "name": "DATABASE_URL",
        "value": "postgresql://neondb_owner:npg_secret123@ep-example.aws.neon.tech/neondb",
    }
    redacted = redact_object(payload)
    assert redacted["value"] == REDACTED


def test_redact_gcp_log_entries_preserves_structure():
    entries = [
        {
            "timestamp": "2026-06-25T00:00:00Z",
            "textPayload": "ok",
            "protoPayload": {
                "serviceData": {
                    "env": [
                        {"name": "APP_ENV", "value": "development"},
                        {
                            "name": "OPENAI_API_KEY",
                            "value": "sk-proj-should-not-leak",
                        },
                    ]
                }
            },
        }
    ]
    redacted = redact_gcp_log_entries(entries)
    env = redacted[0]["protoPayload"]["serviceData"]["env"]
    assert env[0]["value"] == "development"
    assert env[1]["value"] == REDACTED


from src.analysis.log_secret_redaction import redact_json_text


def test_redact_json_text_roundtrip():
    payload = {"DATABASE_URL": "postgresql://user:pass@host/db"}
    redacted = json.loads(redact_json_text(json.dumps(payload)))
    assert redacted["DATABASE_URL"] == "postgresql://REDACTED:REDACTED@host/db"
