"""
E2E / ローカル v2 テスト用 GPT ユーザーシミュレータ。

患者ロールを固定し、bot 風のアドバイス・ヒアリング・役割逆転を抑止する。
"""
from __future__ import annotations

import os
import re
from typing import Any, Optional

# シミュレータ出力から除外する bot / 薬剤師風パターン
_BOT_STYLE_OUTPUT_RE = re.compile(
    r"^(?:ユーザー\s*[:：]|アシスタント\s*[:：]|ボット\s*[:：]|"
    r"assistant\s*[:：]|bot\s*[:：])",
    re.I,
)
_PATIENT_MUST_NOT_RE = re.compile(
    r"(?:"
    r"教えて(?:ください|もらえる)|"
    r"どんな症状|具体的に.{0,8}教えて|"
    r"おすすめ(?:です|しましょう)|"
    r"試してみ(?:て|る)|"
    r"水分を(?:しっかり|と)|"
    r"受診(?:を|してください)|"
    r"登録販売者|"
    r"診断書を用意|"
    r"規制が異なる|"
    r"問題ないことが多い"
    r")",
    re.I,
)

_SIM_SYSTEM = """あなたは市販薬相談チャットの「患者・相談者」ロールプレイ専用シミュレータです。

【役割】
- あなたは薬局のボットではありません。医師・薬剤師でもありません。
- 自分の症状・状況・質問だけを、短い口語（1〜2文）で返してください。

【禁止】
- ボット/アシスタントの返答を模倣・要約・引用しない
- ユーザー（自分）に症状を聞き返すヒアリング（「どんな症状？」等）
- 医療アドバイス・生活指導・受診勧告を患者口調で言う（例: 水分を取りましょう、試してみて）
- 「ユーザー:」「アシスタント:」等のラベル
- 攻撃・不適切表現・個人情報の捏造

【許可】
- 自分の症状の追加・訂正（「やっぱ咳の方がキツい」等）
- 推奨薬への追質問（「それ飲める？」「1番目の成分は？」）
- 旅行・持ち込みの不安や確認（「空港で止められる？」）
"""


def build_persona_block(
    *,
    system: str = "",
    demographics: dict[str, Any] | None = None,
    label: str = "",
) -> str:
    """ペルソナ YAML からシミュレータ用属性ブロックを組み立てる。"""
    parts: list[str] = []
    if label:
        parts.append(f"ラベル: {label}")
    demo = demographics or {}
    demo_bits = []
    for key in ("age", "gender", "region", "occupation", "life_stage"):
        val = demo.get(key)
        if val:
            demo_bits.append(f"{key}={val}")
    if demo_bits:
        parts.append("属性: " + ", ".join(demo_bits))
    if system.strip():
        parts.append(f"口調・背景: {system.strip()}")
    if not parts:
        return ""
    return "\n".join(parts) + "\n"


def sanitize_simulated_user_text(text: str, *, opening: str = "") -> str:
    """bot 風・ラベル付き出力を除去し、フォールバックする。"""
    t = (text or "").strip()
    t = _BOT_STYLE_OUTPUT_RE.sub("", t).strip()
    t = re.sub(r"^(ユーザー|user)\s*[:：]\s*", "", t, flags=re.I).strip()
    if not t:
        return opening or "もう少し教えてほしい"
    if _PATIENT_MUST_NOT_RE.search(t) and len(t) > 40:
        # 長文でアドバイス調 → 短い患者質問に縮退
        return opening or "それについてもう少し教えて"
    return t


def validate_simulated_user_output(text: str) -> tuple[bool, str]:
    """
    GPT シミュレータ出力が患者ロール違反か判定。
    Returns (ok, violation_reason).
    """
    t = (text or "").strip()
    if not t:
        return False, "empty_output"
    if _BOT_STYLE_OUTPUT_RE.search(t):
        return False, "bot_style_prefix"
    try:
        from src.services.reco_followup_signals import is_bot_echo_symptom_interview

        if is_bot_echo_symptom_interview(t):
            return False, "bot_echo_symptom_interview"
    except ImportError:
        pass
    if _PATIENT_MUST_NOT_RE.search(t):
        return False, "patient_must_not_pattern"
    return True, ""


def gpt_user_reply(
    history: list[tuple[str, str]],
    *,
    goal: str,
    system: str = "",
    opening: str = "",
    turn_index: int = 0,
    demographics: dict[str, Any] | None = None,
    label: str = "",
) -> str:
    """次ターンのユーザー発話を GPT で生成（患者ロール固定）。"""
    if turn_index == 0 and opening:
        return opening

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return opening or "もう少し詳しく教えてください"

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        convo_lines: list[str] = []
        for role, text in history[-12:]:
            prefix = "相談者" if role == "user" else "薬局ボット"
            convo_lines.append(f"{prefix}: {text[:400]}")

        persona_block = build_persona_block(
            system=system,
            demographics=demographics,
            label=label,
        )
        user_prompt = (
            f"{_SIM_SYSTEM}\n\n"
            f"【このセッションの目的】\n{goal}\n\n"
            f"【ペルソナ】\n{persona_block or '(未指定)'}\n"
            f"【会話履歴】\n"
            + ("\n".join(convo_lines) if convo_lines else "(初回)")
            + "\n\n"
            "上記を踏まえ、相談者としての次の発話のみをプレーンテキストで返してください。"
        )
        resp = client.chat.completions.create(
            model=os.getenv("V2_TEST_GPT_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": _SIM_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=100,
            temperature=0.4,
        )
        content = (resp.choices[0].message.content or "").strip()
        return sanitize_simulated_user_text(content, opening=opening)
    except Exception:
        return opening or "もう少し詳しく教えてください"
