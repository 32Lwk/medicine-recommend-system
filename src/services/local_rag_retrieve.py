"""Local hybrid retrieve（Bedrock KB なし — build/medicine + Concierge ローカル SSOT）。"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config.local_rag_config import (
    fallback_bm25_only_on_embed_error,
    get_concierge_embedding_model,
    get_embed_cache_ttl_sec,
    get_hybrid_alpha,
    get_medicine_embedding_model,
    local_retrieve_cache_enabled,
    local_retrieve_cache_ttl_sec,
    medicine_hybrid_enabled,
)
from src.services.local_rag_index import (
    IndexedChunk,
    clear_bm25_index,
    concierge_uri_prefixes,
    get_bm25_index,
)
from src.services.local_rag_query import retrieval_query_enrichment
from src.services.local_rag_router import infer_medicine_category, route_medicine_doc

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]


def clear_local_rag_index() -> None:
    clear_bm25_index()
    try:
        from src.services.local_rag_embed import clear_embed_cache

        clear_embed_cache()
    except ImportError:
        pass


def warmup_local_rag_index() -> None:
    """起動時 BM25 index preload（初回 retrieve のコールドスタート短縮）。"""
    try:
        get_bm25_index("medicine")
        get_bm25_index("concierge")
        logger.info("Local RAG BM25 index warmup complete")
    except Exception as exc:
        logger.warning("Local RAG index warmup skipped: %s", exc)


def _emit_retrieve_log(result: Dict[str, object]) -> None:
    try:
        from src.utils.structured_logger import emit_local_rag_detail

        emit_local_rag_detail(
            event="retrieve",
            namespace=str(result.get("namespace") or ""),
            retrieve_ms=float(result.get("kb_retrieve_ms") or 0),
            chunk_count=int(result.get("chunk_count") or 0),
            route=str(result.get("route") or ""),
            category=str(result.get("category") or ""),
            intent=str(result.get("intent") or ""),
        )
    except Exception:
        pass


def _empty_result(min_score: float = 0.4) -> Dict[str, object]:
    return {
        "chunks": [],
        "sources": [],
        "kb_retrieve_ms": 0.0,
        "chunk_count": 0,
        "source_uris": [],
        "provider": "local_rag",
        "min_score": min_score,
        "dropped_low_score": 0,
    }


def _read_routed_doc(
    path: Path,
    virtual_uri: str,
    score: float,
    *,
    query: str = "",
) -> Dict[str, object]:
    index = get_bm25_index("medicine")
    chunk = index.best_chunk_for_uri(virtual_uri, query) if query else None
    if chunk and chunk.text.strip():
        snippet = chunk.text[:1200].strip()
        section = chunk.section
    else:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            text = ""
        snippet = text[:1200].strip()
        section = ""
    return {
        "chunks": [snippet] if snippet else [],
        "sources": [
            {
                "uri": virtual_uri,
                "score": score,
                "path": str(path),
                "section": section,
            }
        ],
        "source_uris": [virtual_uri],
        "chunk_count": 1 if snippet else 0,
        "dropped_low_score": 0,
        "route": "deterministic",
    }


def _medicine_search_types(category: str) -> Tuple[Optional[Tuple[str, ...]], Tuple[str, ...]]:
    cat = (category or "").strip().lower()
    mapping: Dict[str, Tuple[str, ...]] = {
        "interaction": ("interaction",),
        "side_effect": ("side_effect",),
        "usage": ("product",),
        "age": ("topic", "product"),
        "doping": ("doping", "product"),
    }
    doc_types = mapping.get(cat)
    return doc_types, ("efficacy", "other")


def _hybrid_rerank(
    bm25_scored: List[Tuple[float, IndexedChunk]],
    query: str,
    namespace: str,
    *,
    skip_embed: bool = False,
) -> List[Tuple[float, IndexedChunk]]:
    if skip_embed or not bm25_scored:
        return bm25_scored
    alpha = get_hybrid_alpha()
    if alpha >= 0.99:
        return bm25_scored
    model = (
        get_medicine_embedding_model()
        if namespace == "medicine"
        else get_concierge_embedding_model()
    )
    try:
        from src.services.local_rag_embed import cosine_scores, embed_query

        qvec = embed_query(
            query,
            namespace=namespace,
            model=model,
            ttl_sec=get_embed_cache_ttl_sec(),
        )
        if qvec is None:
            if fallback_bm25_only_on_embed_error():
                return bm25_scored
            return []
        cos_map = cosine_scores(qvec, namespace)
        if not cos_map:
            return bm25_scored
        hybrid: List[Tuple[float, IndexedChunk]] = []
        for bm25_score, chunk in bm25_scored:
            cos = cos_map.get(chunk.virtual_uri, 0.0)
            final = round(alpha * bm25_score + (1.0 - alpha) * (0.35 + cos * 0.6), 4)
            hybrid.append((final, chunk))
        hybrid.sort(key=lambda x: x[0], reverse=True)
        return hybrid
    except Exception as exc:
        logger.warning("Local RAG hybrid rerank failed: %s", exc)
        if fallback_bm25_only_on_embed_error():
            return bm25_scored
        return []


def _format_result(
    scored: List[Tuple[float, IndexedChunk]],
    *,
    top_k: int,
    min_score: float,
    namespace: str,
    start: float,
    extra: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    top = scored[: max(1, min(top_k, 10))]
    chunks: List[str] = []
    sources: List[Dict[str, object]] = []
    source_uris: List[str] = []
    for score, chunk in top:
        snippet = chunk.text[:1200].strip()
        if snippet:
            chunks.append(snippet)
        if chunk.virtual_uri not in source_uris:
            source_uris.append(chunk.virtual_uri)
        sources.append(
            {
                "uri": chunk.virtual_uri,
                "score": score,
                "path": chunk.path,
                "doc_type": chunk.doc_type,
                "section": chunk.section,
            }
        )
    elapsed_ms = round((time.time() - start) * 1000, 2)
    out: Dict[str, object] = {
        "chunks": chunks,
        "sources": sources,
        "kb_retrieve_ms": elapsed_ms,
        "chunk_count": len(chunks),
        "source_uris": source_uris,
        "provider": "local_rag",
        "min_score": min_score,
        "dropped_low_score": max(0, len(scored) - len(top)),
        "namespace": namespace,
    }
    if extra:
        out.update(extra)
    _emit_retrieve_log(out)
    return out


def retrieve_medicine_docs_multi(
    query: str,
    *,
    recommended_medicines: Optional[List[Dict[str, Any]]] = None,
    focuses: Optional[List[str]] = None,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    category: str = "",
    max_docs: int = 4,
    min_score: float = 0.4,
) -> Dict[str, object]:
    """Medicine QA 向け multi-doc retrieve（Local RAG）。"""
    from src.services.local_rag_router import route_medicine_docs

    cleaned = (query or "").strip()
    if not cleaned:
        return _empty_result(min_score)

    search_query = retrieval_query_enrichment(cleaned)
    if conversation_history:
        from src.services.local_rag_context import build_contextual_retrieval_query

        contextual = build_contextual_retrieval_query(
            cleaned,
            conversation_history,
            recommended_medicines=recommended_medicines,
        )
        if contextual:
            search_query = retrieval_query_enrichment(contextual)

    start = time.time()
    cat = category or infer_medicine_category(search_query)
    routed = route_medicine_docs(
        search_query,
        recommended_medicines=recommended_medicines,
        category=cat,
        focuses=focuses,
        max_docs=max_docs,
    )

    chunks: List[str] = []
    sources: List[Dict[str, object]] = []
    source_uris: List[str] = []
    for path, virtual_uri, score in routed:
        body = _read_routed_doc(path, virtual_uri, score, query=search_query)
        for chunk in body.get("chunks") or []:
            text = str(chunk).strip()
            if text and text not in chunks:
                chunks.append(text)
        for uri in body.get("source_uris") or []:
            if uri not in source_uris:
                source_uris.append(str(uri))
        for src in body.get("sources") or []:
            if isinstance(src, dict):
                sources.append(src)

    elapsed_ms = round((time.time() - start) * 1000, 2)
    result: Dict[str, object] = {
        "chunks": chunks[:max_docs],
        "sources": sources,
        "kb_retrieve_ms": elapsed_ms,
        "chunk_count": len(chunks[:max_docs]),
        "source_uris": source_uris[:max_docs],
        "provider": "local_rag",
        "min_score": min_score,
        "namespace": "medicine",
        "category": cat,
        "route": "multi_doc",
    }
    _emit_retrieve_log(result)
    return result


def retrieve_local_context(
    query: str,
    *,
    namespace: str,
    top_k: int = 5,
    min_score: float = 0.4,
    recommended_medicines: Optional[List[Dict[str, Any]]] = None,
    category: str = "",
    intent: str = "",
    use_cache: bool = True,
) -> Dict[str, object]:
    cleaned = (query or "").strip()
    if not cleaned:
        return _empty_result(min_score)

    search_query = retrieval_query_enrichment(cleaned)
    start = time.time()

    if namespace == "medicine":
        cat = category or infer_medicine_category(cleaned)
        cache_key: Optional[str] = None
        if use_cache and local_retrieve_cache_enabled():
            from src.services.local_rag_cache import local_retrieve_cache_key

            cache_key = local_retrieve_cache_key(
                namespace, search_query, top_k=top_k, category=cat
            )
            try:
                from src.services.redis_cache import cache_get_json

                cached = cache_get_json(cache_key)
                if isinstance(cached, dict) and cached.get("chunks") is not None:
                    cached["provider"] = "local_rag_cache"
                    return cached
            except Exception:
                pass

        routed = route_medicine_doc(
            cleaned,
            recommended_medicines=recommended_medicines,
            category=cat,
        )
        if routed:
            path, virtual_uri, score = routed
            body = _read_routed_doc(path, virtual_uri, score, query=cleaned)
            elapsed_ms = round((time.time() - start) * 1000, 2)
            result = {
                **body,
                "kb_retrieve_ms": elapsed_ms,
                "provider": "local_rag",
                "min_score": min_score,
                "namespace": namespace,
                "category": cat,
            }
            _emit_retrieve_log(result)
            if cache_key and use_cache and local_retrieve_cache_enabled():
                try:
                    from src.services.redis_cache import cache_set_json

                    cache_set_json(
                        cache_key,
                        result,
                        ttl_sec=local_retrieve_cache_ttl_sec(),
                    )
                except Exception:
                    pass
            return result

        index = get_bm25_index("medicine")
        doc_types, exclude_types = _medicine_search_types(cat)
        scored = index.search(
            search_query,
            top_k=top_k * 4,
            min_score=min_score * 0.7,
            doc_types=doc_types,
            exclude_doc_types=exclude_types,
        )
        if cat == "doping" and not scored:
            scored = index.search(
                search_query,
                top_k=top_k * 4,
                min_score=min_score * 0.7,
                doc_types=("doping",),
            )
        scored = _hybrid_rerank(
            scored,
            cleaned,
            "medicine",
            skip_embed=not medicine_hybrid_enabled(),
        )
        result = _format_result(
            scored,
            top_k=top_k,
            min_score=min_score,
            namespace=namespace,
            start=start,
            extra={"category": cat},
        )
        if cache_key and use_cache and local_retrieve_cache_enabled():
            try:
                from src.services.redis_cache import cache_set_json

                cache_set_json(
                    cache_key,
                    result,
                    ttl_sec=local_retrieve_cache_ttl_sec(),
                )
            except Exception:
                pass
        return result

    # Concierge
    index = get_bm25_index("concierge")
    pools = concierge_uri_prefixes(intent)
    if "企業向け" in cleaned or ("企業" in cleaned and "概要" in cleaned):
        pools = ("local/public/",)
    uri_boosts: Dict[str, float] = {}
    intent_key = (intent or "").strip().lower()
    if intent_key == "doc_changelog" and "最近" in cleaned:
        uri_boosts["local/content/changelog-digest.json"] = 3.0
    if intent_key == "capabilities":
        uri_boosts["local/content/concierge_knowledge.ja.json"] = 2.5
    scored = index.search(
        cleaned,
        top_k=top_k * 3,
        min_score=min_score * 0.7,
        uri_prefixes=pools,
        uri_boosts=uri_boosts or None,
    )
    if pools and not scored:
        scored = index.search(cleaned, top_k=top_k * 3, min_score=min_score * 0.8)
    scored = _hybrid_rerank(scored, cleaned, "concierge")
    return _format_result(
        scored,
        top_k=top_k,
        min_score=min_score,
        namespace=namespace,
        start=start,
        extra={"intent": intent},
    )
