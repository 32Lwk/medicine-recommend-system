"""Bedrock Knowledge Base retrieve（Concierge RAG 補助）。"""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _cache_key(query: str, top_k: int) -> str:
    digest = hashlib.sha256(f"{top_k}:{query}".encode("utf-8")).hexdigest()[:32]
    return f"kb:{digest}"


def retrieve_concierge_context(
    query: str,
    *,
    top_k: int = 5,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """
    Bedrock KB から関連チャンクを取得。

    Returns:
        {chunks, sources, kb_retrieve_ms, chunk_count, source_uris, provider}
    """
    from config.aws_features import get_bedrock_kb_id, get_aws_region, use_bedrock_kb_rag

    cleaned = (query or "").strip()
    empty: Dict[str, Any] = {
        "chunks": [],
        "sources": [],
        "kb_retrieve_ms": 0.0,
        "chunk_count": 0,
        "source_uris": [],
        "provider": "local",
    }
    if not use_bedrock_kb_rag() or not cleaned:
        return empty

    kb_id = get_bedrock_kb_id()
    if not kb_id:
        logger.warning("CONCIERGE_RAG_PROVIDER=bedrock_kb but BEDROCK_KB_ID is unset")
        return empty

    cache_key = _cache_key(cleaned, top_k)
    if use_cache:
        from src.services.redis_cache import cache_get_json, cache_set_json

        cached = cache_get_json(cache_key)
        if isinstance(cached, dict) and cached.get("chunks") is not None:
            cached["provider"] = "bedrock_kb_cache"
            return cached

    import boto3

    start = time.time()
    client = boto3.client("bedrock-agent-runtime", region_name=get_aws_region())
    try:
        resp = client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={"text": cleaned},
            retrievalConfiguration={
                "vectorSearchConfiguration": {"numberOfResults": max(1, min(top_k, 10))}
            },
        )
    except Exception as exc:
        logger.warning("Bedrock KB retrieve failed: %s", exc)
        return empty

    chunks: List[str] = []
    sources: List[Dict[str, Any]] = []
    source_uris: List[str] = []
    for item in resp.get("retrievalResults") or []:
        text = str(item.get("content", {}).get("text") or "").strip()
        if text:
            chunks.append(text)
        loc = item.get("location") or {}
        s3_loc = loc.get("s3Location") or {}
        uri = str(s3_loc.get("uri") or "").strip()
        if uri and uri not in source_uris:
            source_uris.append(uri)
        sources.append(
            {
                "uri": uri,
                "score": item.get("score"),
            }
        )

    elapsed_ms = round((time.time() - start) * 1000, 2)
    result = {
        "chunks": chunks,
        "sources": sources,
        "kb_retrieve_ms": elapsed_ms,
        "chunk_count": len(chunks),
        "source_uris": source_uris,
        "provider": "bedrock_kb",
    }
    logger.info(
        "Bedrock KB retrieve: chunks=%d ms=%.2f uris=%s",
        len(chunks),
        elapsed_ms,
        source_uris[:3],
    )
    if use_cache and chunks:
        from src.services.redis_cache import cache_set_json

        cache_set_json(cache_key, result, ttl_sec=600)
    return result


def format_kb_context_block(result: Dict[str, Any]) -> str:
    chunks = result.get("chunks") or []
    if not chunks:
        return ""
    lines = ["【Bedrock Knowledge Base 参照（補助）】"]
    for idx, chunk in enumerate(chunks[:5], start=1):
        snippet = chunk[:1200].strip()
        lines.append(f"[{idx}] {snippet}")
    uris = result.get("source_uris") or []
    if uris:
        lines.append("")
        lines.append("【参照ソース URI】")
        for uri in uris[:5]:
            lines.append(f"- {uri}")
    return "\n".join(lines)


def augment_reference_with_kb(query: str, base_reference: str) -> str:
    """ローカル参照ブロックに KB チャンクを追記（障害時は base のみ）。"""
    from config.aws_features import use_bedrock_kb_rag

    if not use_bedrock_kb_rag():
        return base_reference
    result = retrieve_concierge_context(query, top_k=5)
    block = format_kb_context_block(result)
    if not block:
        return base_reference
    return f"{base_reference.rstrip()}\n\n{block}"
