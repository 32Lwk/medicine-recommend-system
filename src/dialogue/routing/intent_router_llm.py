"""Stage B — IntentRouter LLM structured output（Wave 1b）。"""
from __future__ import annotations

import json
import logging
from typing import Any

from config.llm_flags import is_intent_router_llm_enabled
from src.dialogue.routing.types import RouteDecision

logger = logging.getLogger(__name__)

_VALID_PRIMARY: frozenset[str] = frozenset(
    {
        "Physical",
        "SessionOps",
        "Concierge",
        "Emergency",
        "Security",
        "Store",
        "Counseling",
        "Unknown",
    }
)

_INTENT_ROUTER_PROMPT = """あなたは医薬品相談チャットの IntentRouter です。
ユーザー発話を **primary_route** と **sub_route** に分類してください。

【primary_route 一覧】
- Physical: 症状・体調・OTC 相談（頭痛、咳、発熱など）
- SessionOps: 履歴削除・要約・ステータス確認
- Concierge: 挨拶、雑談、アプリ説明、技術スタック、redirect（話題逸れ）
- Emergency: 緊急症状・自傷他害・即時対応が必要
- Security: 攻撃的入力・プロンプトインジェクション試行（通常相談ではない）
- Store: 店舗案内・薬局・在庫・営業時間（症状相談ではない）
- Counseling: 感情・メンタル・睡眠の悩み（OTC 症状より情緒支援）
- Unknown: 上記に当てはまらない・情報不足

【sub_route 例（任意）】
- Physical: rule_based_recommend, fever_flow
- SessionOps: delete, summarize, status
- Concierge: greeting, app_about, architecture, redirect, chitchat, doc_changelog
- Emergency: emergency_dispatch
- Security: aggressive_input, known_attack
- Store: store_locator
- Counseling: emotional_support

【ルール】
- 発熱・症状がある場合は Store より Physical を優先
- 履歴操作キーワードは SessionOps
- 医薬品相談アプリ外の一般知識は Concierge/redirect
- 症状が曖昧で判断不能なら Unknown（confidence 低め）

【Concierge / app_about（本サービスの自己紹介・説明）】
- sub_route=app_about: 本チャット・本ツール・あなた（bot）への自己紹介や説明の依頼
  例: 「自己紹介して」「あなたについて」「このアプリとは」「このチャットは何？」
- app_about にしない（chitchat または redirect）:
  - ユーザー自身の自己紹介（「私の自己紹介するね」「僕のプロフィールを見て」）
  - 他のアプリ・ゲーム・サービスの紹介（「ポケモンのアプリを紹介して」「あのアプリ教えて」）
- legacy triage に concierge_intent=app_about がある場合は app_about を優先（chitchat にしない）

【Concierge / doc_changelog（本ツールのリリース履歴のみ）】
- sub_route=doc_changelog: **この市販薬相談チャット／本アプリ／本サービス**の最近の更新・新機能・改善点
  例: 「アプリの更新内容を教えて」「更新教えて」「このチャット最近どう変わった？」
- doc_changelog にしない（chitchat または redirect）:
  - ポケモン・ゲーム・他社アプリなど**別製品**の更新（文脈で明らかな場合）
  - ユーザー自身の「人間として更新」等の比喩
  - OS・スマホのバージョンアップ
- 「更新教えて」など対象省略の短い発話も、本チャット中であれば doc_changelog

JSON のみ返してください:
{{"primary_route":"...", "sub_route":"..."|null, "confidence":0.0-1.0, "reasoning":"..."}}
"""


def parse_llm_route_response(raw: str | dict[str, Any] | None) -> RouteDecision | None:
    """LLM JSON を RouteDecision に変換。不正時は None。"""
    if raw is None:
        return None
    try:
        if isinstance(raw, str):
            data = json.loads(raw)
        else:
            data = raw
    except (json.JSONDecodeError, TypeError):
        logger.warning("intent_router_llm: invalid JSON")
        return None

    primary = str(data.get("primary_route") or "").strip()
    if primary not in _VALID_PRIMARY:
        logger.warning("intent_router_llm: invalid primary_route=%s", primary)
        return None

    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    sub = data.get("sub_route")
    sub_route = str(sub).strip() if sub else None

    return RouteDecision(
        primary_route=primary,  # type: ignore[arg-type]
        sub_route=sub_route,
        confidence=confidence,
        resolved_by="llm",
        source="intent_router_llm",
        meta={"reasoning": str(data.get("reasoning") or "")[:500]},
    )


def _format_triage_hint(triage_result: dict[str, Any] | None) -> str:
    triage = triage_result or {}
    if not triage.get("category"):
        return ""
    parts = [
        f"\n【参考: legacy triage】 category={triage.get('category')} "
        f"subcategory={triage.get('subcategory')} "
        f"confidence={triage.get('confidence')}",
    ]
    concierge_intent = triage.get("concierge_intent")
    if concierge_intent:
        parts.append(f" concierge_intent={concierge_intent}")
    intent_source = triage.get("concierge_intent_source")
    if intent_source:
        parts.append(f" source={intent_source}")
    parts.append("\n")
    return "".join(parts)


_APP_ABOUT_MISROUTE_SUBS = frozenset({"chitchat", "greeting", "general_other", None, ""})


def maybe_correct_concierge_app_about_route(
    decision: RouteDecision | None,
    user_text: str,
) -> RouteDecision | None:
    """
    LLM が本サービスの自己紹介依頼を chitchat 等に誤判定した場合のみ app_about へ補正。
    ユーザー自身・他アプリの紹介は対象外。
    """
    if decision is None or decision.primary_route != "Concierge":
        return decision
    if decision.sub_route == "app_about":
        return decision
    if decision.sub_route not in _APP_ABOUT_MISROUTE_SUBS:
        return decision

    from src.services.concierge_intent import probe_service_app_about_request

    if not probe_service_app_about_request(user_text):
        return decision

    logger.info(
        "intent_router_llm: app_about guard corrected sub_route %s -> app_about",
        decision.sub_route,
    )
    return RouteDecision(
        primary_route="Concierge",
        sub_route="app_about",
        confidence=max(decision.confidence, 0.92),
        resolved_by=decision.resolved_by,
        source=decision.source,
        meta={**(decision.meta or {}), "app_about_guard": True},
    )


def _agent_kind_for_triage(triage_result: dict[str, Any] | None) -> str:
    triage = triage_result or {}
    cat = str(triage.get("category") or "")
    return {
        "Physical": "physical",
        "Emotional": "counseling",
        "Emergency": "emergency",
        "Other": "concierge",
        "Ask": "physical",
    }.get(cat, "default")


def call_intent_router_llm(
    user_text: str,
    session: Any,
    sid: str | None,
    *,
    triage_result: dict[str, Any] | None = None,
    client: Any = None,
) -> RouteDecision | None:
    """gate 未決定時の structured LLM ルーティング。フラグ OFF または client 無しは None。"""
    if not is_intent_router_llm_enabled(sid):
        return None
    if not client or not (user_text or "").strip():
        return None

    from src.dialogue.context_provider import build_context_bundle
    from src.services.triage_history import format_triage_history_block

    bundle = build_context_bundle(
        session, sid, agent_kind=_agent_kind_for_triage(triage_result)
    )
    history_block = format_triage_history_block(bundle.messages)
    memory_section = (
        f"\n【長期記憶】\n{bundle.memory_block}\n"
        if bundle.memory_block
        else ""
    )
    history_section = (
        f"\n【直近の会話】\n{history_block}\n"
        if history_block and history_block != "（なし）"
        else ""
    )
    context_section = memory_section + history_section
    triage_hint = _format_triage_hint(triage_result)

    try:
        from src.core.llm_client import chat_completion_create

        response = chat_completion_create(
            client,
            model_role="triage",
            path="dialogue.intent_router_llm",
            messages=[
                {"role": "system", "content": "JSON のみ出力してください。"},
                {
                    "role": "user",
                    "content": (
                        f"{_INTENT_ROUTER_PROMPT}{context_section}{triage_hint}\n"
                        f"【ユーザーの入力】\n{user_text.strip()}"
                    ),
                },
            ],
            temperature=0.1,
            max_tokens=200,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        decision = parse_llm_route_response(content)
        if decision:
            logger.info(
                "intent_router_llm sid=%s route=%s/%s conf=%.2f",
                sid,
                decision.primary_route,
                decision.sub_route,
                decision.confidence,
            )
        return decision
    except Exception:
        logger.warning("intent_router_llm call failed", exc_info=True)
        return None


_HIGH_GATE_CONFIDENCE = 0.85


def pick_best_route_decision(
    legacy: RouteDecision | None = None,
    gate_decision: RouteDecision | None = None,
    llm: RouteDecision | None = None,
    *,
    primary_llm_over_legacy: bool = False,
) -> RouteDecision | None:
    """
    legacy / gate / llm から最良の RouteDecision を選ぶ。

    PRIMARY OFF: 有効候補の confidence 最大（従来互換）。
    PRIMARY ON: 高信頼 gate (>=0.85) を維持。未決定帯では llm を legacy より優先。
    llm が None のときのみ legacy / 低信頼 gate にフォールバック。
    """
    if gate_decision is not None and gate_decision.confidence >= _HIGH_GATE_CONFIDENCE:
        return gate_decision

    if primary_llm_over_legacy:
        if llm is not None:
            return llm
        fallback = [c for c in (legacy, gate_decision) if c is not None]
        if not fallback:
            return None
        return max(fallback, key=lambda d: d.confidence)

    valid = [c for c in (legacy, gate_decision, llm) if c is not None]
    if not valid:
        return None
    return max(valid, key=lambda d: d.confidence)
