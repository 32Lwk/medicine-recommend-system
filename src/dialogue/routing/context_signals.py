"""Layer 1 — 構造化コンテキストシグナル（決定論的）。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from src.services.concierge_agent_history import (
    is_architecture_explanation_question,
    resolve_last_concierge_intent,
    resolve_prior_meta_intent,
)
from src.services.medicine_brand_resolve import MEDICINE_BRAND_HINTS as _MEDICINE_BRAND_HINTS

_AMBIGUOUS_FOLLOW_UP_RE = re.compile(
    r"^(?:詳しく|もっと|続き|他には|それについて|教えて)[。！？!?]*$|"
    r"^(?:詳しく|もっと).{0,8}(?:教えて|説明)[。！？!?]*$"
)

_DOC_CHANGELOG_CONTINUATION_RE = re.compile(
    r"^(?:もっと|さらに|詳しく|続き|他には|他の更新|更新内容|変更点)"
)

# changelog 固有の継続（汎用の「もっと詳しく」等は含めない）
_DOC_CHANGELOG_TOPIC_RE = re.compile(
    r"(?:他の更新|更新内容|変更点|最近の(?:更新|変更)|チェンジログ|changelog|"
    r"リリースノート|更新履歴)",
    re.IGNORECASE,
)

_APP_ABOUT_TOPIC_RE = re.compile(
    r"あなた(?:について|は|が)|"
    r"(?:この|本)?(?:サービス|アプリ|システム)(?:について|は|の)|"
    r"Sage\s*Terrace|"
    r"何が(?:できる|出来る)|"
    r"使い方|"
    r"誰が(?:作|開発|運営)",
    re.IGNORECASE,
)

_TOPIC_INFRA_COMPARE_RE = re.compile(
    r"aws|gcp|cloud\s*run|インフラ|アーキテクチャ|architecture|"
    r"マルチ[\s　\-]*エージェント|デプロイ|バックエンド",
    re.IGNORECASE,
)

_SIDE_EFFECT_QA_RE = re.compile(
    r"(.+?)(?:って|は|の)(?:眠い|眠くなる|眠気|副作用|安全|飲んでいい|飲んでもいい|ダメ)",
    re.IGNORECASE,
)

_DROWSINESS_SYMPTOM_ONLY_RE = re.compile(
    r"^(?:眠い|眠くなる|眠気が|眠れない)[。！？!?]*$"
)


@dataclass
class ContextFeatures:
    last_bot_card_type: str | None = None
    prior_route: str | None = None
    prior_concierge_intent: str | None = None
    drug_entities: list[str] = field(default_factory=list)
    is_ambiguous_short_follow_up: bool = False
    is_side_effect_question: bool = False
    is_explicit_new_meta_topic: bool = False
    is_doc_changelog_continuation: bool = False
    side_effect_subject: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_bot_card_type": self.last_bot_card_type,
            "prior_route": self.prior_route,
            "prior_concierge_intent": self.prior_concierge_intent,
            "drug_entities": self.drug_entities,
            "is_ambiguous_short_follow_up": self.is_ambiguous_short_follow_up,
            "is_side_effect_question": self.is_side_effect_question,
            "is_explicit_new_meta_topic": self.is_explicit_new_meta_topic,
            "is_doc_changelog_continuation": self.is_doc_changelog_continuation,
            "side_effect_subject": self.side_effect_subject,
        }


def _resolve_last_bot_card_type(messages: list[dict[str, Any]]) -> str | None:
    for msg in reversed(messages or []):
        if not isinstance(msg, dict) or msg.get("type") != "bot":
            continue
        intent = msg.get("concierge_intent")
        if intent:
            return str(intent)
        diagnosis = msg.get("diagnosis")
        if isinstance(diagnosis, dict):
            kind = str(diagnosis.get("kind") or "").strip()
            if kind:
                return kind.replace("concierge_", "", 1) if kind.startswith("concierge_") else kind
            render = str(diagnosis.get("render") or "").strip()
            if render:
                return render
    return None


def extract_drug_entities(text: str) -> list[str]:
    t = (text or "").strip()
    if not t:
        return []
    found: list[str] = []
    for hint in _MEDICINE_BRAND_HINTS:
        if hint.lower() in t.lower() or hint in t:
            found.append(hint)
    return found


def is_medicine_side_effect_question(text: str) -> bool:
    """副作用・眠気 Q&A 判定（gate / unified router 用。厳密判定に委譲）。"""
    from src.services.medicine_qa_routing import is_strict_medicine_side_effect_question

    return is_strict_medicine_side_effect_question(text)


def extract_side_effect_subject(text: str) -> str | None:
    t = (text or "").strip()
    m = _SIDE_EFFECT_QA_RE.search(t)
    if m:
        subject = m.group(1).strip()
        if subject and len(subject) <= 30:
            return subject
    drugs = extract_drug_entities(t)
    return drugs[0] if drugs else None


def is_symptom_drowsiness_declaration(text: str) -> bool:
    """ユーザー自身の眠気症状申告（副作用 QA ではない）。"""
    t = (text or "").strip()
    if not t:
        return False
    if is_medicine_side_effect_question(t):
        return False
    if _DROWSINESS_SYMPTOM_ONLY_RE.match(t):
        return True
    if any(k in t for k in ("眠い", "眠くなる", "眠気")) and not extract_drug_entities(t):
        return "?" not in t and not t.endswith(("?", "？"))
    return False


def suggest_meta_intent_family(text: str) -> str | None:
    """
    発話からメタ intent ファミリーを推定する（ルーティング用の粗い信号）。

    返り値は app_about / architecture / doc_changelog / capabilities 等。
    曖昧な継続（もっと詳しく）は None。
    フレーズ列挙ではなく、話題ファミリー単位で判定する。
    """
    t = (text or "").strip()
    if not t:
        return None

    try:
        from src.services.concierge_agent_history import (
            is_architecture_explanation_question,
            is_who_is_answering_question,
        )
    except ImportError:
        is_architecture_explanation_question = lambda _t: False  # type: ignore
        is_who_is_answering_question = lambda _t: False  # type: ignore

    # 汎用の深掘り（もっと詳しく / 続き 等）はファミリー未定。
    # sticky follow-up が prior intent を継承できるようにする。
    if is_ambiguous_short_follow_up(t):
        return None

    if is_who_is_answering_question(t):
        return "app_about"
    if _APP_ABOUT_TOPIC_RE.search(t):
        return "app_about"
    if is_architecture_explanation_question(t) or _TOPIC_INFRA_COMPARE_RE.search(t):
        return "architecture"
    # changelog 固有語のみファミリー確定（汎用継続フレーズはここに落とさない）
    if _DOC_CHANGELOG_TOPIC_RE.search(t) and len(t) <= 48:
        return "doc_changelog"
    # 能力・対応範囲の短い確認（言語など）
    if re.search(r"(英語|多言語|対応言語|何語|使える|できますか)", t, re.I):
        return "capabilities"
    return None


def looks_like_substantive_meta_question(text: str) -> bool:
    """短い継続（もっと詳しく）ではなく、独立したメタ／技術質問っぽいか。"""
    t = (text or "").strip()
    if not t or len(t) < 4:
        return False
    if suggest_meta_intent_family(t):
        return True
    if is_ambiguous_short_follow_up(t):
        return False
    # 「〜は？」「違いは？」など独立質問。構造で判定。
    if re.search(r"[?？]$", t) and len(t) <= 40:
        if re.search(
            r"(違い|なに|何|どう|誰|だれ|仕組み|構成|役割|担当|エージェント|"
            r"デプロイ|システム|インフラ)",
            t,
            re.IGNORECASE,
        ):
            return True
    return False


def is_explicit_new_meta_topic(text: str, *, prior_intent: str | None = None) -> bool:
    """
    直前メタ話題からの「話題転換」か。

    同一ファミリー内の深掘り（architecture → Cloud Runは？）は False。
    ファミリーが変わる場合（doc_changelog → AWS/GCP、app_about → アーキテクチャ）は True。
    """
    t = (text or "").strip()
    if not t:
        return False

    suggested = suggest_meta_intent_family(t)
    if not suggested:
        # ファミリー不明でも、十分な独立質問で prior と食い違う可能性があれば転換候補
        if prior_intent and looks_like_substantive_meta_question(t):
            # 曖昧継続は除外済み。prior と無関係な独立質問として転換扱い。
            return True
        return False

    if not prior_intent:
        return True

    # 同一ファミリー内は継続（sticky follow-up / layer1 継続を許可）
    if suggested == prior_intent:
        return False

    # 例: architecture 中の Cloud Run → 継続 / changelog → AWS/GCP → 転換
    # 汎用「もっと詳しく」は suggested=None で上の分岐により継続
    return True


def is_doc_changelog_continuation(text: str) -> bool:
    """直前が doc_changelog のときの汎用・固有の継続発話か。"""
    t = (text or "").strip()
    if not t or len(t) > 40:
        return False
    # 他ファミリーが明示されているときは changelog 継続ではない
    family = suggest_meta_intent_family(t)
    if family and family != "doc_changelog":
        return False
    if _DOC_CHANGELOG_TOPIC_RE.search(t):
        return True
    # 汎用深掘り（もっと詳しく等）も changelog 文脈では継続扱い
    return bool(_DOC_CHANGELOG_CONTINUATION_RE.search(t))


def is_ambiguous_short_follow_up(text: str) -> bool:
    t = (text or "").strip()
    if not t or len(t) > 24:
        return False
    return bool(_AMBIGUOUS_FOLLOW_UP_RE.search(t))


def extract_context_features(
    user_text: str,
    session: Any,
    sid: str | None,
) -> ContextFeatures:
    messages = (session or {}).get("messages") or [] if session is not None else []
    prior = resolve_prior_meta_intent(session=session, sid=sid)
    prior_concierge = resolve_last_concierge_intent(messages)
    last_card = _resolve_last_bot_card_type(messages)
    text = (user_text or "").strip()

    side_effect = is_medicine_side_effect_question(text)
    return ContextFeatures(
        last_bot_card_type=last_card,
        prior_route=prior,
        prior_concierge_intent=prior_concierge,
        drug_entities=extract_drug_entities(text),
        is_ambiguous_short_follow_up=is_ambiguous_short_follow_up(text),
        is_side_effect_question=side_effect,
        is_explicit_new_meta_topic=is_explicit_new_meta_topic(text, prior_intent=prior),
        is_doc_changelog_continuation=is_doc_changelog_continuation(text),
        side_effect_subject=extract_side_effect_subject(text) if side_effect else None,
    )
