"""Concierge Meta KB — 会話文脈から retrieve クエリを合成（省略・follow-up 一般化）。"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

from src.services.concierge_agent_history import is_meta_follow_up_utterance
from src.services.local_rag_context import normalize_conversation_history, normalize_text

# 技術・メタ KB で会話から拾うトピック語（カテゴリ非依存の抽象パターン）
_CONCIERGE_TOPIC_HINTS: Sequence[tuple[str, str]] = (
    (r"Local\s*RAG|ローカル\s*RAG|Bedrock\s*KB|ナレッジ", "Local RAG Bedrock KB"),
    (r"CodePipeline|CodeBuild|デプロイ|ECR|ECS", "CodePipeline デプロイ ECS"),
    (r"GCP|Cloud\s*Run|AWS|ECS|Fargate|ステージング", "GCP AWS クロスクラウド"),
    (r"GitHub|GitLab|正本|ミラー", "GitHub GitLab 正本"),
    (r"PostgreSQL|Neon|保存|データ", "PostgreSQL Neon データ保存"),
    (r"マルチ[\s　\-]*エージェント|TriageAgent|IntentRouter", "マルチエージェント IntentRouter"),
    (r"\bSSE\b|Server[\s-]?Sent|ストリーミング", "SSE ストリーミング"),
    (r"Translate|Polly|翻訳|TTS", "Translate Polly 翻訳"),
    (r"企業|会社|B2B|導入", "企業向け B2B"),
    (r"プライバシー|プラポリ|個人情報", "プライバシー 個人情報"),
    (r"作成|意図|背景|なぜ|mission|β", "作成意図 mission β版"),
    (r"ルールベース|スコア|LLM.*薬", "ルールベース スコアリング"),
    (r"R2|CDN|images\.yutok", "R2 CDN 画像"),
    (r"LINE|Cloud\s*Run", "LINE GCP"),
)

_SHORT_QUERY_CHARS = 24


def _history_user_texts(
    history: Sequence[Dict[str, Any]],
    *,
    max_turns: int = 6,
) -> List[str]:
    texts: List[str] = []
    for turn in normalize_conversation_history(history)[-max_turns:]:
        if turn.get("role") == "user":
            content = normalize_text(str(turn.get("content") or ""))
            if content:
                texts.append(content)
    return texts


def extract_concierge_topic_hints(history: Sequence[Dict[str, Any]]) -> List[str]:
    """直近 user 発話から Meta KB 検索用トピック語を抽出。"""
    found: List[str] = []
    blob = " ".join(reversed(_history_user_texts(history, max_turns=8)))
    if not blob.strip():
        return found
    for pattern, hint in _CONCIERGE_TOPIC_HINTS:
        if re.search(pattern, blob, re.I) and hint not in found:
            found.append(hint)
    return found[:6]


def needs_concierge_meta_context_enrichment(
    query: str,
    history: Optional[Sequence[Dict[str, Any]]] = None,
) -> bool:
    """省略・follow-up 発話で履歴から retrieve クエリを補完すべきか。"""
    q = normalize_text(query)
    if not q or not history:
        return False
    if is_meta_follow_up_utterance(q):
        return True
    if len(q) <= _SHORT_QUERY_CHARS and _history_user_texts(history):
        return True
    if re.search(
        r"^(それ|この|その|あれ|さっき|先ほど|上記|続き|詳しく|もっと|もう少し)",
        q,
        re.I,
    ):
        return True
    return False


def build_concierge_meta_contextual_query(
    query: str,
    history: Optional[Sequence[Dict[str, Any]]] = None,
    *,
    intent: str = "",
) -> str:
    """
    Concierge Meta KB 向け contextual retrieve クエリ。
    ルールベースのみ（レイテンシ・コスト優先）。LLM リライトは不要。
    """
    cleaned = normalize_text(query)
    hist = normalize_conversation_history(history)
    if not cleaned:
        return ""

    prior_hist = hist
    if hist and str(hist[-1].get("role") or "") == "user":
        last = normalize_text(str(hist[-1].get("content") or ""))
        if last and (last == cleaned or last in cleaned or cleaned in last):
            prior_hist = hist[:-1]

    parts: List[str] = [cleaned]
    if prior_hist and needs_concierge_meta_context_enrichment(cleaned, prior_hist):
        hints = extract_concierge_topic_hints(prior_hist)
        if hints:
            parts.append(" ".join(hints))
        prior_users = _history_user_texts(prior_hist, max_turns=3)
        if prior_users:
            anchor = prior_users[-1][:100]
            if anchor and anchor not in cleaned:
                parts.append(f"直前トピック: {anchor}")
        intent_key = (intent or "").strip().lower()
        if intent_key == "doc_app_overview":
            parts.append("アプリ概要 作成意図 mission")
        elif intent_key == "architecture":
            parts.append("技術 SSOT architecture")

    return " ".join(p for p in parts if p).strip()
