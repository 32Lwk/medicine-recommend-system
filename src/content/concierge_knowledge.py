"""ConciergeAgent 用ナレッジ SSOT ローダ（concierge_knowledge.ja.json）"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

_KNOWLEDGE_PATH = Path(__file__).resolve().parent / "concierge_knowledge.ja.json"

_REQUIRED_TOP_KEYS = ("meta", "app", "capabilities", "limitations", "agents", "policy_snippet")


@lru_cache(maxsize=1)
def load_concierge_knowledge() -> Dict[str, Any]:
    with open(_KNOWLEDGE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    validate_concierge_knowledge(data)
    return data


def validate_concierge_knowledge(data: Dict[str, Any]) -> None:
    """SSOT スキーマの最低限バリデーション"""
    for key in _REQUIRED_TOP_KEYS:
        if key not in data:
            raise ValueError(f"concierge_knowledge missing key: {key}")
    if not isinstance(data.get("capabilities"), list) or not data["capabilities"]:
        raise ValueError("capabilities must be a non-empty list")
    if not isinstance(data.get("limitations"), list) or not data["limitations"]:
        raise ValueError("limitations must be a non-empty list")
    if not isinstance(data.get("agents"), list) or not data["agents"]:
        raise ValueError("agents must be a non-empty list")
    app = data.get("app") or {}
    for field in ("name", "purpose", "audience"):
        if not app.get(field):
            raise ValueError(f"app.{field} is required")


def get_capabilities() -> List[Dict[str, str]]:
    return list(load_concierge_knowledge().get("capabilities") or [])


def get_limitations() -> List[str]:
    return list(load_concierge_knowledge().get("limitations") or [])


def get_agents() -> List[Dict[str, str]]:
    return list(load_concierge_knowledge().get("agents") or [])


def get_app_info() -> Dict[str, str]:
    return dict(load_concierge_knowledge().get("app") or {})


def get_policy_snippet() -> str:
    return str(load_concierge_knowledge().get("policy_snippet") or "")


def get_service_identity_block() -> str:
    """meta_triage / Concierge LLM 用のサービス立場説明（SSOT）。"""
    app = get_app_info()
    lines = [
        f"性質: {app.get('service_nature', '')}",
        f"ではない: {app.get('explicitly_not', '')}",
        f"目的: {app.get('purpose', '')}",
    ]
    limits = get_limitations()
    if limits:
        lines.append("制限: " + " / ".join(limits[:4]))
    return "\n".join(line for line in lines if line.strip())


def get_handoff_intro_physical() -> str:
    return str(load_concierge_knowledge().get("handoff_intro_physical") or "")


def key_facts_for_sync_test() -> Dict[str, bool]:
    """ℹ️ モーダル等と照合する主要事実"""
    limits = " ".join(get_limitations())
    return {
        "otc_only": "処方薬" in limits and "行いません" in limits,
        "no_diagnosis": "診断" in limits,
        "multilingual": any(c.get("id") == "i18n" for c in get_capabilities()),
    }
