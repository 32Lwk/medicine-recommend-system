"""Local RAG retrieve — cache key helper."""
from __future__ import annotations

import hashlib


def local_retrieve_cache_key(
    namespace: str,
    query: str,
    *,
    top_k: int,
    category: str = "",
) -> str:
    digest = hashlib.sha256(
        f"{top_k}:{category}:{query}".encode("utf-8")
    ).hexdigest()[:32]
    return f"local_rag:{namespace}:{digest}"
