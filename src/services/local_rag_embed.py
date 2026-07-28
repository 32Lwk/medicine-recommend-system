"""Local RAG — OpenAI query embedding + prebuilt npz index."""
from __future__ import annotations

import hashlib
import logging
import time
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
INDEX_DIR = ROOT / "build" / "local_rag"

_QUERY_CACHE: Dict[str, Tuple[float, np.ndarray]] = {}


def _cache_key(namespace: str, model: str, query: str) -> str:
    digest = hashlib.sha256(f"{namespace}:{model}:{query}".encode()).hexdigest()[:24]
    return digest


def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return matrix / norms


@lru_cache(maxsize=2)
def _load_npz(namespace: str) -> Optional[Tuple[np.ndarray, Tuple[str, ...]]]:
    path = INDEX_DIR / f"{namespace}_index.npz"
    if not path.is_file():
        return None
    try:
        data = np.load(path, allow_pickle=False)
    except ValueError:
        # 旧形式（uris dtype=object）との互換
        data = np.load(path, allow_pickle=True)
    try:
        vectors = np.asarray(data["vectors"], dtype=np.float32)
        uris = tuple(str(u) for u in data["uris"].tolist())
        return _normalize_rows(vectors), uris
    except (KeyError, TypeError) as exc:
        logger.warning("Failed to parse local RAG npz %s: %s", path, exc)
        return None
    except (OSError,) as exc:
        logger.warning("Failed to load local RAG npz %s: %s", path, exc)
        return None


def embed_query(
    query: str,
    *,
    namespace: str,
    model: str,
    ttl_sec: int = 600,
) -> Optional[np.ndarray]:
    cleaned = (query or "").strip()
    if not cleaned:
        return None
    key = _cache_key(namespace, model, cleaned)
    now = time.time()
    cached = _QUERY_CACHE.get(key)
    if cached and now - cached[0] < ttl_sec:
        _emit_embed_log(
            namespace=namespace,
            model=model,
            query_chars=len(cleaned),
            cache_hit=True,
        )
        return cached[1]

    start = time.time()
    try:
        from src.core.openai_client import client

        if client is None:
            return None
        resp = client.embeddings.create(input=[cleaned], model=model)
        vec = np.asarray(resp.data[0].embedding, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        _QUERY_CACHE[key] = (now, vec)
        _emit_embed_log(
            namespace=namespace,
            model=model,
            query_chars=len(cleaned),
            cache_hit=False,
            embed_ms=round((time.time() - start) * 1000, 2),
        )
        return vec
    except Exception as exc:
        logger.warning("Local RAG query embed failed (%s): %s", model, exc)
        return None


def _emit_embed_log(
    *,
    namespace: str,
    model: str,
    query_chars: int,
    cache_hit: bool,
    embed_ms: float = 0.0,
) -> None:
    try:
        from src.utils.structured_logger import emit_local_rag_detail

        emit_local_rag_detail(
            event="embed",
            namespace=namespace,
            model=model,
            query_chars=query_chars,
            cache_hit=cache_hit,
            embed_ms=embed_ms,
        )
    except Exception:
        pass


def cosine_scores(
    query_vec: np.ndarray,
    namespace: str,
) -> Dict[str, float]:
    loaded = _load_npz(namespace)
    if loaded is None:
        return {}
    vectors, uris = loaded
    if vectors.shape[0] != len(uris):
        return {}
    sims = vectors @ query_vec
    return {uri: float(max(0.0, min(1.0, s))) for uri, s in zip(uris, sims)}


def clear_embed_cache() -> None:
    _QUERY_CACHE.clear()
    _load_npz.cache_clear()
