"""Local RAG — 会話文脈から retrieve クエリを合成（省略・指示語・LLM 補助）。"""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional, Sequence

from src.services.local_rag_query import (
    expand_concepts,
    extract_brand_tokens,
    extract_coordination_pairs,
    normalize_text,
)

logger = logging.getLogger(__name__)

_ANAPHORA_RE = re.compile(
    r"(?:^|[、。?\s])"
    r"(?:それ|この|その|あれ|あの|こっち|そっち|さっき(?:の|言った)?|先ほど(?:の)?|上記|前述)"
    r"(?:の)?(?:薬|やつ|成分|錠|もの)?",
    re.I,
)
_SHORT_QUERY = 18
_HISTORY_ROLES = ("user", "human")

# 会話から拾う「薬剤・概念」ヒント（カテゴリ非依存）
_CONTEXT_HINT_PATTERNS: Sequence[tuple[str, str]] = (
    (r"ロキソニン|ロキソプロフェン", "ロキソプロフェン"),
    (r"ワーファリン|ワルファリン", "ワーファリン"),
    (r"バファリン|アスピリン", "アスピリン"),
    (r"イブ(?:プロフェン)?", "イブプロフェン"),
    (r"カロナール|タイレノール|アセトアミノフェン", "アセトアミノフェン"),
    (r"SSRI|SNRI|抗うつ", "SSRI"),
    (r"デキストロメトルファン|咳止め", "デキストロメトルファン"),
    (r"アレグラ|フェキソフェナジン|花粉症", "花粉症薬"),
    (r"エナジードリンク|エナドリ|カフェイン", "カフェイン"),
    (r"麻黄|プソイドエフェドリン|鼻薬", "プソイドエフェドリン"),
    (r"固まりにく|サラサラ|抗凝固", "ワーファリン"),
    (r"推奨(?:してもらった|いただいた|の)(?:やつ|もの)?", "推奨医薬品"),
    (r"ハーフマラソン|マラソン|大会|競技", "競技会"),
    (r"ビール|お酒|アルコール", "アルコール"),
    (r"小学|小[1-6]|小児|未就学", "小児"),
    (r"風邪薬|市販", "風邪薬"),
)


def normalize_conversation_history(
    history: Optional[Sequence[Dict[str, Any]]],
) -> List[Dict[str, str]]:
    """v2 `{type: user|bot}` と OpenAI `{role, content}` を統一。"""
    out: List[Dict[str, str]] = []
    for msg in history or []:
        if not isinstance(msg, dict):
            continue
        role = str(msg.get("role") or "").strip().lower()
        if not role:
            msg_type = str(msg.get("type") or "").strip().lower()
            if msg_type == "user":
                role = "user"
            elif msg_type in ("bot", "assistant"):
                role = "assistant"
        content = str(msg.get("content") or "").strip()
        if role and content:
            out.append({"role": role, "content": content})
    return out


def _history_user_texts(history: Sequence[Dict[str, Any]], *, max_turns: int = 6) -> List[str]:
    texts: List[str] = []
    for turn in normalize_conversation_history(history)[-max_turns:]:
        if turn.get("role") in _HISTORY_ROLES:
            content = normalize_text(str(turn.get("content") or ""))
            if content:
                texts.append(content)
    return texts


def extract_context_substances(history: Sequence[Dict[str, Any]]) -> List[str]:
    """直近ユーザー発話から薬剤・概念語を抽出（重複除去・新しい順優先）。"""
    found: List[str] = []
    for text in reversed(_history_user_texts(history)):
        for brand in extract_brand_tokens(text):
            if brand not in found:
                found.append(brand)
        for pattern, hint in _CONTEXT_HINT_PATTERNS:
            if re.search(pattern, text, re.I) and hint not in found:
                found.append(hint)
        for coord in extract_coordination_pairs(text):
            if len(coord) >= 2 and coord not in found:
                found.append(coord)
    return found[:8]


def needs_context_enrichment(query: str, history: Sequence[Dict[str, Any]]) -> bool:
    q = normalize_text(query)
    if not q or not history:
        return False
    if _ANAPHORA_RE.search(q):
        return True
    if history:
        age_in_hist = any(
            re.search(r"小[1-6]|小学|小児|\d+歳|\d+代", t)
            for t in _history_user_texts(history)
        )
        if age_in_hist and re.search(r"風邪薬|市販|使える|使っても", q):
            return True
    if len(q) <= _SHORT_QUERY and not extract_brand_tokens(q):
        subs = extract_context_substances(history)
        if subs and not any(s.lower() in q.lower() for s in subs[:3]):
            return True
    if re.search(r"併用|一緒|混ぜ|ダブル|combo|mix", q, re.I) and history:
        if extract_context_substances(history):
            return True
    hist_blob = " ".join(_history_user_texts(history))
    if re.search(r"マラソン|大会|競技|ハーフ", hist_blob):
        if re.search(r"鼻|スプレー|点鼻|あれ|手助け|使う", q):
            return True
    return False


def build_contextual_retrieval_query(
    query: str,
    history: Optional[Sequence[Dict[str, Any]]] = None,
    *,
    recommended_medicines: Optional[List[Dict[str, Any]]] = None,
    use_llm: Optional[bool] = None,
) -> str:
    """
    省略・指示語の follow-up を、会話履歴と推奨薬で自己完結クエリにする。
    ルールベースを優先し、不足時のみ LLM リライト（LOCAL_RAG_CONTEXT_LLM=1）。
    """
    cleaned = normalize_text(query)
    hist = normalize_conversation_history(history)
    if not cleaned:
        return ""

    # 最終 user 発話が現在 query と同一なら文脈抽出から除外（二重計上防止）
    prior_hist = hist
    if hist and str(hist[-1].get("role") or "") in _HISTORY_ROLES:
        last = normalize_text(str(hist[-1].get("content") or ""))
        if last and (last == cleaned or last in cleaned or cleaned in last):
            prior_hist = hist[:-1]

    parts: List[str] = [cleaned]
    if prior_hist and needs_context_enrichment(cleaned, prior_hist):
        ctx_subs = extract_context_substances(prior_hist)
        if ctx_subs:
            parts.append("会話文脈: " + ", ".join(ctx_subs[:5]))
        prior = _history_user_texts(prior_hist, max_turns=2)
        if prior and prior[-1] != cleaned:
            parts.append("直前: " + prior[-1][:120])
        hist_blob = " ".join(_history_user_texts(prior_hist))
        if re.search(r"マラソン|大会|競技|ハーフ", hist_blob) and re.search(
            r"あれ|それ|使う|スプレー|点鼻|鼻", cleaned
        ):
            parts.append("鼻薬 プソイドエフェドリン ドーピング")

    for med in recommended_medicines or []:
        name = str(med.get("product_name") or med.get("name") or "").strip()
        if name and name not in cleaned:
            parts.append(name)

    merged = expand_concepts(" ".join(parts).strip())

    if use_llm is None:
        use_llm = os.getenv("LOCAL_RAG_CONTEXT_LLM", "").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
    if use_llm and prior_hist and needs_context_enrichment(cleaned, prior_hist):
        rewritten = _llm_rewrite_query(cleaned, prior_hist, merged)
        if rewritten:
            return expand_concepts(rewritten)
    return merged


def _llm_rewrite_query(
    query: str,
    history: Sequence[Dict[str, Any]],
    rule_based: str,
) -> str:
    transcript = []
    for turn in list(history)[-8:]:
        role = str(turn.get("role") or "user")
        content = str(turn.get("content") or "").strip()
        if content:
            transcript.append(f"{role}: {content}")
    transcript.append(f"user: {query}")

    system = (
        "あなたは医薬品KB検索用のクエリリライターです。"
        "会話の省略・指示語を解決し、単独で意味が通る日本語の検索クエリ1文を出力してください。"
        "薬品名・成分名・併用/副作用/用法/年齢/ドーピングの意図を保持。"
        "説明や前置きは不要。クエリ文のみ。"
    )
    user = (
        "以下の会話の最後のユーザー発話を、検索クエリ1文にしてください。\n\n"
        + "\n".join(transcript)
        + f"\n\nルールベース案: {rule_based}"
    )
    try:
        from src.core.llm_client import chat_completion_create, extract_completion_text
        from src.core.openai_client import client as openai_client

        if not openai_client:
            return ""
        model = os.getenv("LOCAL_RAG_CONTEXT_LLM_MODEL", "gpt-4o-mini")
        resp = chat_completion_create(
            openai_client,
            model_role="router",
            path="local_rag/context_rewrite",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            model=model,
            temperature=0.1,
            max_tokens=180,
        )
        text = extract_completion_text(resp)
        return normalize_text(text.split("\n")[0][:300])
    except Exception as exc:
        logger.debug("local_rag_context LLM rewrite skipped: %s", exc)
        return ""
