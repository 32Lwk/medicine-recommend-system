#!/usr/bin/env python3
"""Local RAG embedding index ビルド（増分 manifest + npz）。

Usage:
  .venv/bin/python scripts/build_local_rag_index.py
  .venv/bin/python scripts/build_local_rag_index.py --namespace medicine --full
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUTPUT_DIR = ROOT / "build" / "local_rag"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_manifest() -> Dict[str, object]:
    if not MANIFEST_PATH.is_file():
        return {"entries": {}, "updated_at": ""}
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"entries": {}, "updated_at": ""}


def _save_manifest(data: Dict[str, object]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    MANIFEST_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _collect_chunks(namespace: str):
    from src.services.local_rag_index import get_bm25_index

    index = get_bm25_index(namespace)
    return index.chunks


def _embed_texts(texts: List[str], model: str) -> np.ndarray:
    from src.core.openai_client import client

    if client is None:
        raise SystemExit("OPENAI_API_KEY required for embedding index build")
    batch_size = 64
    vectors: List[List[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        resp = client.embeddings.create(input=batch, model=model)
        ordered = sorted(resp.data, key=lambda x: x.index)
        vectors.extend([item.embedding for item in ordered])
    arr = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return arr / norms


def build_namespace(namespace: str, *, full: bool = False) -> Tuple[int, int]:
    from config.local_rag_config import (
        get_concierge_embedding_model,
        get_medicine_embedding_model,
    )

    model = (
        get_medicine_embedding_model()
        if namespace == "medicine"
        else get_concierge_embedding_model()
    )
    chunks = _collect_chunks(namespace)
    manifest = _load_manifest()
    entries: Dict[str, object] = dict(manifest.get("entries") or {})

    to_embed: List[Tuple[str, str, str]] = []
    for chunk in chunks:
        digest = _sha256(chunk.text)
        prev = entries.get(chunk.chunk_id)
        if not full and isinstance(prev, dict) and prev.get("sha256") == digest:
            continue
        to_embed.append((chunk.chunk_id, chunk.virtual_uri, chunk.text))
        entries[chunk.chunk_id] = {
            "sha256": digest,
            "virtual_uri": chunk.virtual_uri,
            "model": model,
            "path": chunk.path,
        }

    if not to_embed and not full:
        print(f"{namespace}: no changes ({len(chunks)} chunks)")
        return len(chunks), 0

    print(f"{namespace}: embedding {len(to_embed)} / {len(chunks)} chunks ({model})")
    texts = [t for _, _, t in to_embed]
    new_vectors = _embed_texts(texts, model) if texts else np.zeros((0, 1), dtype=np.float32)

    npz_path = OUTPUT_DIR / f"{namespace}_index.npz"
    uri_to_vec: Dict[str, np.ndarray] = {}
    if npz_path.is_file() and not full:
        try:
            old = np.load(npz_path, allow_pickle=False)
        except ValueError:
            old = np.load(npz_path, allow_pickle=True)
        for uri, vec in zip(old["uris"].tolist(), old["vectors"]):
            uri_to_vec[str(uri)] = np.asarray(vec, dtype=np.float32)

    for (chunk_id, virtual_uri, _), vec in zip(to_embed, new_vectors):
        uri_to_vec[virtual_uri] = vec
        entry = entries.get(chunk_id)
        if isinstance(entry, dict):
            entry["embedded"] = True

    # chunk 削除分を manifest から除去
    valid_ids = {c.chunk_id for c in chunks}
    entries = {k: v for k, v in entries.items() if k in valid_ids}

    uris = sorted(uri_to_vec.keys())
    vectors = np.stack([uri_to_vec[u] for u in uris], axis=0)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    max_uri_len = max((len(u) for u in uris), default=64)
    max_uri_len = min(max(max_uri_len, 64), 512)
    uris_arr = np.array(uris, dtype=f"U{max_uri_len}")
    np.savez_compressed(npz_path, vectors=vectors, uris=uris_arr)
    manifest["entries"] = entries
    _save_manifest(manifest)
    print(f"Wrote {npz_path} ({vectors.shape[0]} vectors, dim={vectors.shape[1]})")
    return len(chunks), len(to_embed)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build local RAG embedding index")
    parser.add_argument(
        "--namespace",
        choices=("medicine", "concierge", "all"),
        default="all",
    )
    parser.add_argument("--full", action="store_true", help="Force full re-embed")
    args = parser.parse_args()

    namespaces = ["medicine", "concierge"] if args.namespace == "all" else [args.namespace]
    for ns in namespaces:
        build_namespace(ns, full=args.full)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
