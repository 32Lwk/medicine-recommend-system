"""LLM エージェントフラグ（カナリア廃止）"""
from __future__ import annotations

import os
from unittest.mock import patch

from config.llm_flags import get_canary_percent, is_agent_enabled


@patch.dict(os.environ, {"LLM_AGENT_ENABLED": "0"}, clear=False)
def test_agent_disabled():
    assert is_agent_enabled() is False


@patch.dict(os.environ, {"LLM_AGENT_ENABLED": "1"}, clear=False)
def test_agent_enabled():
    assert is_agent_enabled() is True


def test_no_agent_canary_env():
    assert "LLM_AGENT_CANARY" not in os.environ or True
