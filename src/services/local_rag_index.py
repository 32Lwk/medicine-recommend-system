"""Local RAG — BM25 index + section chunking + intent pool filter."""
from __future__ import annotations

import json
import logging
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
BUILD_MEDICINE = ROOT / "build" / "medicine"

_TOKEN_RE = re.compile(r"[\w一-龥ぁ-んァ-ヶ]{2,}")
_QUERY_KEYWORDS: Tuple[str, ...] = (
    "風邪薬",
    "解熱鎮痛薬",
    "解熱鎮痛",
    "頭痛薬",
    "1日",
    "何回",
    "何時間",
    "空腹",
    "空腹時",
    "食後",
    "錠剤",
    "水",
    "用法",
    "用量",
    "副作用",
    "眠気",
    "禁止物質",
    "競技",
    "競技会",
    "ドーピング",
    "年齢",
    "小児",
    "高齢",
    "nsaid",
    "併用",
    "相互作用",
)
_SECTION_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)

_CONCIERGE_INTENT_POOLS: Dict[str, Tuple[str, ...]] = {
    "capabilities": ("local/concierge/", "local/content/concierge_knowledge"),
    "app_about": ("local/concierge/", "local/public/", "local/content/concierge_knowledge"),
    "doc_changelog": ("local/content/",),
    # architecture: technical SSOT + ops + pipeline/dev 説明を広く拾う
    "architecture": (
        "local/ops/",
        "local/concierge/",
        "local/public/",
        "local/dev/",
        "local/content/concierge_knowledge",
    ),
}


@dataclass(frozen=True)
class IndexedChunk:
    chunk_id: str
    virtual_uri: str
    text: str
    path: str
    doc_type: str = ""
    section: str = ""
    product_name: str = ""
    score_hint: float = 0.0


@dataclass
class BM25Index:
    chunks: List[IndexedChunk] = field(default_factory=list)
    doc_freq: Dict[str, int] = field(default_factory=dict)
    doc_lens: List[int] = field(default_factory=list)
    avg_dl: float = 0.0
    _tokenized: List[List[str]] = field(default_factory=list)

    def build(self, chunks: Sequence[IndexedChunk]) -> None:
        self.chunks = list(chunks)
        self._tokenized = []
        self.doc_freq = {}
        self.doc_lens = []
        total = 0
        for chunk in self.chunks:
            tokens = _tokenize(chunk.text + " " + chunk.virtual_uri)
            self._tokenized.append(tokens)
            self.doc_lens.append(len(tokens))
            total += len(tokens)
            seen = set(tokens)
            for tok in seen:
                self.doc_freq[tok] = self.doc_freq.get(tok, 0) + 1
        n = len(self.chunks)
        self.avg_dl = (total / n) if n else 0.0

    def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        min_score: float = 0.0,
        uri_prefixes: Optional[Sequence[str]] = None,
        doc_types: Optional[Sequence[str]] = None,
        exclude_doc_types: Optional[Sequence[str]] = None,
        uri_boosts: Optional[Dict[str, float]] = None,
    ) -> List[Tuple[float, IndexedChunk]]:
        if not self.chunks:
            return []
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []
        allowed_types = set(doc_types) if doc_types else None
        excluded_types = set(exclude_doc_types or ())
        boosts = uri_boosts or {}
        n = len(self.chunks)
        k1, b = 1.5, 0.75
        scored: List[Tuple[float, IndexedChunk]] = []
        for i, chunk in enumerate(self.chunks):
            if uri_prefixes:
                if not any(chunk.virtual_uri.startswith(p) for p in uri_prefixes):
                    continue
            if allowed_types is not None and chunk.doc_type not in allowed_types:
                continue
            if chunk.doc_type in excluded_types:
                continue
            tokens = self._tokenized[i]
            if not tokens:
                continue
            dl = self.doc_lens[i]
            score = 0.0
            for qt in q_tokens:
                tf = tokens.count(qt)
                if tf == 0:
                    continue
                df = self.doc_freq.get(qt, 0)
                idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
                denom = tf + k1 * (1 - b + b * dl / (self.avg_dl or 1))
                score += idf * (tf * (k1 + 1)) / denom
            if chunk.score_hint > 0:
                score += chunk.score_hint
            for uri_prefix, boost in boosts.items():
                if chunk.virtual_uri.startswith(uri_prefix):
                    score += boost
            phrase = query.strip().lower()
            if len(phrase) >= 4 and phrase in chunk.text.lower():
                score += 1.5
            hit_ratio = sum(1 for qt in q_tokens if qt in tokens) / max(1, len(q_tokens))
            norm = _normalize_bm25_score(score, hit_ratio=hit_ratio)
            if norm >= min_score:
                scored.append((norm, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[: max(1, min(top_k, 20))]

    def best_chunk_for_uri(self, virtual_uri: str, query: str) -> Optional[IndexedChunk]:
        """同一 virtual_uri の section chunk から query に最も関連するものを選ぶ。"""
        candidates = [c for c in self.chunks if c.virtual_uri == virtual_uri]
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]
        q_tokens = set(_tokenize(query))
        if not q_tokens:
            return candidates[0]
        best: Optional[IndexedChunk] = None
        best_hits = -1
        for chunk in candidates:
            c_tokens = set(_tokenize(chunk.text + " " + chunk.section))
            hits = len(q_tokens & c_tokens)
            if hits > best_hits:
                best_hits = hits
                best = chunk
        return best or candidates[0]


_INDEX: Dict[str, BM25Index] = {}


from src.services.local_rag_query import tokenize_for_search


def _tokenize(text: str) -> List[str]:
    return tokenize_for_search(text)


def _normalize_bm25_score(raw: float, *, hit_ratio: float = 0.0) -> float:
    """Map raw BM25 to 0.35–0.95 range (eval min_score compatible)."""
    capped = min(raw, 12.0)
    base = 0.35 + (capped / 12.0) * 0.6
    if hit_ratio >= 0.2:
        base = max(base, 0.35 + hit_ratio * 0.65)
    return round(min(0.95, base), 4)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _read_metadata(path: Path) -> Dict[str, object]:
    meta_path = Path(str(path) + ".metadata.json")
    if not meta_path.is_file():
        return {}
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        return dict(data.get("metadataAttributes") or {})
    except (OSError, json.JSONDecodeError):
        return {}


def _chunk_markdown(
    path: Path,
    text: str,
    virtual_uri: str,
    doc_type: str,
    meta: Dict[str, object],
) -> List[IndexedChunk]:
    product_name = str(meta.get("product_name") or "")
    sections = list(_SECTION_RE.finditer(text))
    if doc_type in ("interaction", "side_effect", "topic", "doping") or len(sections) <= 1:
        return [
            IndexedChunk(
                chunk_id=f"{virtual_uri}#0",
                virtual_uri=virtual_uri,
                text=text.strip(),
                path=str(path),
                doc_type=doc_type,
                product_name=product_name,
            )
        ]
    chunks: List[IndexedChunk] = []
    for idx, match in enumerate(sections):
        start = match.start()
        end = sections[idx + 1].start() if idx + 1 < len(sections) else len(text)
        section_title = match.group(1).strip()
        body = text[start:end].strip()
        if not body:
            continue
        chunks.append(
            IndexedChunk(
                chunk_id=f"{virtual_uri}#{idx}",
                virtual_uri=virtual_uri,
                text=body,
                path=str(path),
                doc_type=doc_type,
                section=section_title,
                product_name=product_name,
            )
        )
    if not chunks and text.strip():
        chunks.append(
            IndexedChunk(
                chunk_id=f"{virtual_uri}#0",
                virtual_uri=virtual_uri,
                text=text.strip(),
                path=str(path),
                doc_type=doc_type,
                product_name=product_name,
            )
        )
    return chunks


def _medicine_doc_type(rel: str) -> str:
    if rel.startswith("interactions/"):
        return "interaction"
    if rel.startswith("side_effects/"):
        return "side_effect"
    if rel.startswith("topics/"):
        return "topic"
    if rel.startswith("doping/"):
        return "doping"
    if rel.startswith("products/"):
        return "product"
    if rel.startswith("efficacy/"):
        return "efficacy"
    return "other"


def _build_medicine_chunks() -> List[IndexedChunk]:
    if not BUILD_MEDICINE.is_dir():
        return []
    out: List[IndexedChunk] = []
    for path in sorted(BUILD_MEDICINE.rglob("*.md")):
        if "raw" in path.parts:
            continue
        try:
            rel = path.relative_to(BUILD_MEDICINE).as_posix()
        except ValueError:
            continue
        doc_type = _medicine_doc_type(rel)
        meta = _read_metadata(path)
        text = _read_text(path)
        synonyms = str(meta.get("synonyms") or "").strip()
        if synonyms:
            text = f"{text}\n{synonyms}"
        virtual_uri = f"local/medicine/{rel}"
        out.extend(_chunk_markdown(path, text, virtual_uri, doc_type, meta))
    return out


def _concierge_docs_raw() -> List[Tuple[Path, str, str]]:
    docs: List[Tuple[Path, str, str]] = []
    mappings: List[Tuple[Path, str]] = [
        (ROOT / "docs" / "concierge", "concierge"),
        (ROOT / "docs" / "public", "public"),
    ]
    for base, prefix in mappings:
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".md", ".json", ".txt"}:
                continue
            rel = path.relative_to(base).as_posix()
            docs.append((path, f"local/{prefix}/{rel}", prefix))
    for rel in (
        "docs/ops/AWS_FEATURES_ROLLOUT.md",
        "docs/ops/AWS_INFRA.md",
        "docs/ops/AWS_CODEPIPELINE.md",
        "docs/ops/CLOUDFLARE_R2_IMAGES.md",
        "docs/ops/AWS_BEDROCK_KB.md",
        "docs/ops/AWS_STAGING_CHECKLIST.md",
        "docs/ops/LOCAL_RAG.md",
        "docs/ops/GCP_RAG_MIGRATION_ADR.md",
        "docs/ops/CLOUD_RUN_LLM_ENV.md",
        "docs/ops/CAPACITY_PLANNING.md",
        "docs/dev/CHAT_PIPELINE_V2.md",
        "docs/dev/MEDICINE_QA_ROUTING.md",
        "docs/dev/MEDICINE_BRAND_RESOLVE.md",
    ):
        path = ROOT / rel
        if path.is_file():
            # docs/dev は virtual URI を local/dev/ に分離（architecture pool から参照）
            if rel.startswith("docs/dev/"):
                docs.append((path, f"local/dev/{path.name}", "dev"))
            else:
                docs.append((path, f"local/ops/{path.name}", "ops"))
    for rel, uri in (
        ("CHANGELOG.md", "local/content/CHANGELOG.md"),
        ("static/changelog-digest.json", "local/content/changelog-digest.json"),
        ("src/content/concierge_knowledge.ja.json", "local/content/concierge_knowledge.ja.json"),
    ):
        path = ROOT / rel
        if path.is_file():
            docs.append((path, uri, "content"))
    return docs


def _build_concierge_chunks() -> List[IndexedChunk]:
    out: List[IndexedChunk] = []
    for path, virtual_uri, doc_type in _concierge_docs_raw():
        text = _read_text(path)
        if path.suffix == ".json" and text:
            try:
                text = json.dumps(json.loads(text), ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                pass
        if not text.strip():
            continue
        out.extend(
            _chunk_markdown(path, text, virtual_uri, doc_type, {})
        )
    return out


def get_bm25_index(namespace: str) -> BM25Index:
    if namespace not in _INDEX:
        idx = BM25Index()
        if namespace == "medicine":
            idx.build(_build_medicine_chunks())
        elif namespace == "concierge":
            idx.build(_build_concierge_chunks())
        else:
            idx.build([])
        _INDEX[namespace] = idx
        logger.info("Local RAG BM25 index %s: %d chunks", namespace, len(idx.chunks))
    return _INDEX[namespace]


def clear_bm25_index() -> None:
    _INDEX.clear()


def concierge_uri_prefixes(intent: str) -> Optional[Tuple[str, ...]]:
    key = (intent or "").strip().lower()
    if not key:
        return None
    return _CONCIERGE_INTENT_POOLS.get(key)


def filter_chunks_by_doc_types(
    chunks: Iterable[IndexedChunk],
    doc_types: Sequence[str],
) -> List[IndexedChunk]:
    allowed = set(doc_types)
    return [c for c in chunks if c.doc_type in allowed]
