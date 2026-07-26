"""Local RAG 設定（AWS / GCP 共通）。"""
from __future__ import annotations

import os


def _env(name: str, default: str = "") -> str:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip()


def _flag(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _float(name: str, default: float) -> float:
    raw = _env(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def get_medicine_embedding_model() -> str:
    return _env("LOCAL_RAG_MEDICINE_EMBEDDING_MODEL", "text-embedding-3-large")


def get_concierge_embedding_model() -> str:
    return _env("LOCAL_RAG_CONCIERGE_EMBEDDING_MODEL", "text-embedding-3-small")


def get_hybrid_alpha() -> float:
    """BM25 重み（残りは cosine）。default 0.4 → cosine 0.6。"""
    return max(0.0, min(1.0, _float("LOCAL_RAG_HYBRID_ALPHA", 0.4)))


def get_embed_cache_ttl_sec() -> int:
    return max(0, int(_float("LOCAL_RAG_EMBED_CACHE_TTL_SEC", 600)))


def fallback_bm25_only_on_embed_error() -> bool:
    return _flag("LOCAL_RAG_FALLBACK_BM25_ONLY", True)


def medicine_hybrid_enabled() -> bool:
    """Medicine BM25 フォールバック path で embedding hybrid rerank を使う。"""
    return _flag("LOCAL_RAG_MEDICINE_HYBRID", False)


def local_retrieve_cache_enabled() -> bool:
    return _flag("LOCAL_RAG_RETRIEVE_CACHE", True)


def local_retrieve_cache_ttl_sec() -> int:
    return max(0, int(_float("LOCAL_RAG_RETRIEVE_CACHE_TTL_SEC", 600)))


def category_llm_fallback_enabled() -> bool:
    """カテゴリ confidence が低いときのみ LLM fallback。"""
    return _flag("LOCAL_RAG_CATEGORY_LLM_FALLBACK", False)


def get_default_min_score() -> float:
    return max(0.0, min(1.0, _float("LOCAL_RAG_MIN_SCORE", 0.4)))
