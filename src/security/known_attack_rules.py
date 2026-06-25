"""
既知の jailbreak / プロンプトインジェクション攻撃パターン。

ルールマッチ時は LLM を待たず即座に警告応答する（SECURITY_ROLLOUT_PHASE に依存しない）。
"""
from __future__ import annotations

import logging
import re
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

KNOWN_ATTACK_WARN_MESSAGE = (
    "入力内容に不審なパターンが検出されました。症状や質問を自然な文章で入力してください。"
)

# (正規表現, ルールID) — 高信頼の既知攻撃のみ（誤検知を避ける）
_KNOWN_ATTACK_RULES: List[Tuple[str, str]] = [
    (r"プロンプトインジェクション", "prompt_injection_ja"),
    (r"命令にすべて従", "obey_all_commands"),
    (r"すべての命令に従", "obey_all_commands_alt"),
    (r"命令に従ってください", "obey_commands_polite"),
    (r"ignore\s+(all\s+)?(previous\s+)?instructions", "ignore_instructions_en"),
    (r"disregard\s+(all\s+)?(previous\s+)?instructions", "disregard_instructions_en"),
    (r"\bjailbreak\b", "jailbreak_en"),
    (r"DANモード", "dan_mode_ja"),
    (r"\bDAN\b.*\bmode\b", "dan_mode_en"),
    (r"システムプロンプトを(開示|表示|教え)", "reveal_system_prompt_ja"),
    (r"(show|reveal|print|display)\s+(your\s+)?(system\s+)?prompt", "reveal_system_prompt_en"),
    (r"開発者モード", "dev_mode_ja"),
    (r"\bdeveloper\s+mode\b", "dev_mode_en"),
    (r"隠された指示に従", "hidden_instructions_ja"),
    (r"秘密の指示に従", "secret_instructions_ja"),
    (r"プロンプトを変更", "change_prompt_ja"),
    (r"上記の指示を無視", "ignore_above_instructions_ja"),
    (r"role\s*:\s*system", "role_system_injection"),
    (r"<\s*/?\s*system\s*>", "system_tag_injection"),
    (r"simulate\s+being\s+(admin|root|sudo)", "simulate_privileged_en"),
]

_compiled_rules: Optional[List[Tuple[re.Pattern[str], str]]] = None


def _get_compiled_rules() -> List[Tuple[re.Pattern[str], str]]:
    global _compiled_rules
    if _compiled_rules is None:
        _compiled_rules = [
            (re.compile(pattern, re.IGNORECASE), rule_id)
            for pattern, rule_id in _KNOWN_ATTACK_RULES
        ]
    return _compiled_rules


def match_known_attack(text: str) -> Tuple[bool, str]:
    """
    既知攻撃パターンにマッチするか判定する。

    Returns:
        (マッチしたか, ルールIDまたは空文字)
    """
    if not text or not isinstance(text, str):
        return False, ""
    stripped = text.strip()
    if not stripped:
        return False, ""
    for pattern, rule_id in _get_compiled_rules():
        if pattern.search(stripped):
            logger.warning("🛡️ 既知攻撃パターン検出: rule=%s", rule_id)
            return True, rule_id
    return False, ""
