"""Local RAG — BM25 index + section chunking + intent pool filter."""
from __future__ import annotations

import json
import logging
import math
import re
import threading
import time
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
_SUBSECTION_RE = re.compile(r"^###\s+(.+)$", re.MULTILINE)
_RAG_KEYWORDS_RE = re.compile(r"<!--\s*rag-keywords:\s*(.+?)\s*-->", re.I | re.DOTALL)
_CONCIERGE_RAG_CHUNK_PATHS = ("docs/concierge/technical/", "docs/concierge/rag/", "docs/public/")

_CONCIERGE_INTENT_POOLS: Dict[str, Tuple[str, ...]] = {
    "capabilities": ("local/concierge/", "local/content/concierge_knowledge", "local/public/アプリ概要"),
    "app_about": ("local/concierge/", "local/public/", "local/content/concierge_knowledge"),
    "doc_changelog": ("local/content/changelog-digest.json",),
    "doc_privacy": (
        "local/public/プライバシー",
        "local/concierge/rag/legal-crossdoc-rag",
    ),
    "doc_terms": (
        "local/public/免責",
        "local/concierge/rag/legal-crossdoc-rag",
    ),
    "doc_app_overview": (
        "local/public/アプリ概要",
        "local/concierge/technical/11",
        "local/concierge/rag/app-overview-rag",
        "local/concierge/rag/author-mission-rag",
    ),
    "doc_consultation": ("local/public/医薬品相談先",),
    "doc_operator": (
        "local/concierge/お問い合わせ",
        "local/public/運営者",
        "local/concierge/rag/legal-crossdoc-rag",
    ),
    # architecture: technical SSOT + ops + pipeline/dev（法務 doc は横断時のみ public 参照）
    "architecture": (
        "local/ops/",
        "local/concierge/",
        "local/public/",
        "local/dev/",
        "local/content/concierge_knowledge",
    ),
}

# docs/public/*.md の RAG doc_type（retrieve boost / pool フィルタ用）
_PUBLIC_DOC_TYPE_BY_NAME: Dict[str, str] = {
    "プライバシーポリシー.md": "legal_privacy",
    "免責事項・利用規約.md": "legal_terms",
    "アプリ概要.md": "overview",
    "医薬品相談先.md": "consultation",
    "運営者情報.md": "operator",
    "会社向け概要書類.md": "enterprise",
    "企業向け簡略版概要資料.md": "enterprise",
}

# Concierge 技術 FAQ RAG index から除外（digest + SSOT 直接注入で代替）
_CONCIERGE_RAG_EXCLUDED_CONTENT: Tuple[str, ...] = ("CHANGELOG.md",)


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
_INDEX_LOCK = threading.Lock()
_INDEX_BUILDING: set[str] = set()


def is_bm25_index_ready(namespace: str) -> bool:
    """BM25 index が構築済みか（構築中は False）。"""
    with _INDEX_LOCK:
        return namespace in _INDEX


def is_bm25_index_building(namespace: str) -> bool:
    """別スレッドが index を構築中か。"""
    with _INDEX_LOCK:
        return namespace in _INDEX_BUILDING


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


def _strip_rag_keywords(text: str) -> Tuple[str, str]:
    match = _RAG_KEYWORDS_RE.search(text)
    if not match:
        return text, ""
    keywords = match.group(1).strip()
    cleaned = _RAG_KEYWORDS_RE.sub("", text).strip()
    return cleaned, keywords


def _prepend_rag_index_text(body: str, section: str, keywords: str) -> str:
    parts: List[str] = []
    if section:
        parts.append(f"[section: {section}]")
    if keywords:
        parts.append(f"[keywords: {keywords}]")
    if parts:
        parts.append("")
    parts.append(body.strip())
    return "\n".join(parts).strip()


def _should_subsection_chunk(path: Path) -> bool:
    rel = str(path).replace("\\", "/")
    return (
        "docs/concierge/technical/" in rel
        or "docs/concierge/rag/" in rel
        or "docs/public/" in rel
    )


def _section_keywords_for_chunk(path: Path, doc_keywords: str, sec_kw: str) -> str:
    """FAQ RAG md はセクション固有 keywords のみ（Q1 の keywords が全 chunk に漏れない）。"""
    rel = str(path).replace("\\", "/")
    if "/docs/concierge/rag/" in rel and rel.endswith("-rag.md"):
        return sec_kw
    return ", ".join(x for x in (doc_keywords, sec_kw) if x)


def _chunk_markdown(
    path: Path,
    text: str,
    virtual_uri: str,
    doc_type: str,
    meta: Dict[str, object],
    *,
    subsection_split: bool = False,
) -> List[IndexedChunk]:
    product_name = str(meta.get("product_name") or "")
    rel = str(path).replace("\\", "/")
    is_faq_rag = "/docs/concierge/rag/" in rel and rel.endswith("-rag.md")
    if is_faq_rag:
        doc_keywords = ""
    else:
        text, doc_keywords = _strip_rag_keywords(text)
    sections = list(_SECTION_RE.finditer(text))
    if subsection_split and sections:
        chunks: List[IndexedChunk] = []
        for idx, match in enumerate(sections):
            start = match.start()
            end = sections[idx + 1].start() if idx + 1 < len(sections) else len(text)
            section_title = match.group(1).strip()
            section_body = text[start:end].strip()
            if not section_body:
                continue
            subs = list(_SUBSECTION_RE.finditer(section_body))
            if len(subs) <= 1:
                _, sec_kw = _strip_rag_keywords(section_body)
                kw = _section_keywords_for_chunk(path, doc_keywords, sec_kw)
                indexed = _prepend_rag_index_text(section_body, section_title, kw)
                chunks.append(
                    IndexedChunk(
                        chunk_id=f"{virtual_uri}#{idx}",
                        virtual_uri=virtual_uri,
                        text=indexed,
                        path=str(path),
                        doc_type=doc_type,
                        section=section_title,
                        product_name=product_name,
                    )
                )
                continue
            for sub_idx, sub in enumerate(subs):
                sub_start = sub.start()
                sub_end = subs[sub_idx + 1].start() if sub_idx + 1 < len(subs) else len(section_body)
                sub_title = sub.group(1).strip()
                sub_body = section_body[sub_start:sub_end].strip()
                if not sub_body:
                    continue
                _, sec_kw = _strip_rag_keywords(sub_body)
                kw = _section_keywords_for_chunk(path, doc_keywords, sec_kw)
                full_section = f"{section_title} / {sub_title}"
                indexed = _prepend_rag_index_text(sub_body, full_section, kw)
                chunks.append(
                    IndexedChunk(
                        chunk_id=f"{virtual_uri}#{idx}-{sub_idx}",
                        virtual_uri=virtual_uri,
                        text=indexed,
                        path=str(path),
                        doc_type=doc_type,
                        section=full_section,
                        product_name=product_name,
                    )
                )
        if chunks:
            return chunks
    if doc_type in ("interaction", "side_effect", "topic", "doping") or len(sections) <= 1:
        indexed = _prepend_rag_index_text(text.strip(), "", doc_keywords)
        return [
            IndexedChunk(
                chunk_id=f"{virtual_uri}#0",
                virtual_uri=virtual_uri,
                text=indexed,
                path=str(path),
                doc_type=doc_type,
                product_name=product_name,
            )
        ]
    chunks = []
    for idx, match in enumerate(sections):
        start = match.start()
        end = sections[idx + 1].start() if idx + 1 < len(sections) else len(text)
        section_title = match.group(1).strip()
        body = text[start:end].strip()
        if not body:
            continue
        _, sec_kw = _strip_rag_keywords(body)
        kw = _section_keywords_for_chunk(path, doc_keywords, sec_kw)
        indexed = _prepend_rag_index_text(body, section_title, kw)
        chunks.append(
            IndexedChunk(
                chunk_id=f"{virtual_uri}#{idx}",
                virtual_uri=virtual_uri,
                text=indexed,
                path=str(path),
                doc_type=doc_type,
                section=section_title,
                product_name=product_name,
            )
        )
    if not chunks and text.strip():
        indexed = _prepend_rag_index_text(text.strip(), "", doc_keywords)
        chunks.append(
            IndexedChunk(
                chunk_id=f"{virtual_uri}#0",
                virtual_uri=virtual_uri,
                text=indexed,
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
    from config.concierge_rag_sources import CONCIERGE_DEV_DOCS, CONCIERGE_OPS_DOCS

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
            if prefix == "concierge" and rel.startswith("technical/research/"):
                continue
            docs.append((path, f"local/{prefix}/{rel}", prefix))
    for rel in CONCIERGE_OPS_DOCS:
        path = ROOT / rel
        if path.is_file():
            docs.append((path, f"local/ops/{path.name}", "ops"))
    for rel in CONCIERGE_DEV_DOCS:
        path = ROOT / rel
        if path.is_file():
            docs.append((path, f"local/dev/{path.name}", "dev"))
    for rel, uri in (
        ("static/changelog-digest.json", "local/content/changelog-digest.json"),
        ("src/content/concierge_knowledge.ja.json", "local/content/concierge_knowledge.ja.json"),
    ):
        path = ROOT / rel
        if path.is_file():
            docs.append((path, uri, "content"))
    return docs


def _concierge_chunk_doc_type(prefix: str, path: Path) -> str:
    if prefix == "public":
        return _PUBLIC_DOC_TYPE_BY_NAME.get(path.name, "public")
    return prefix


def _build_concierge_chunks() -> List[IndexedChunk]:
    out: List[IndexedChunk] = []
    for path, virtual_uri, doc_type in _concierge_docs_raw():
        if path.name in _CONCIERGE_RAG_EXCLUDED_CONTENT:
            continue
        text = _read_text(path)
        if path.suffix == ".json" and text:
            try:
                text = json.dumps(json.loads(text), ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                pass
        if not text.strip():
            continue
        chunk_type = _concierge_chunk_doc_type(doc_type, path)
        if path.name == "changelog-digest.json":
            chunk_type = "changelog_digest"
        elif path.name == "concierge_knowledge.ja.json":
            chunk_type = "capabilities"
        chunks = _chunk_markdown(
            path,
            text,
            virtual_uri,
            chunk_type,
            {},
            subsection_split=_should_subsection_chunk(path),
        )
        if (
            "12-technical-faq-rag" in str(path)
            or "technical-security-rag" in str(path)
            or "author-mission-rag" in str(path)
        ):
            chunks = [
                IndexedChunk(
                    chunk_id=c.chunk_id,
                    virtual_uri=c.virtual_uri,
                    text=c.text,
                    path=c.path,
                    doc_type="technical_faq",
                    section=c.section,
                    product_name=c.product_name,
                    score_hint=max(c.score_hint, 1.5),
                )
                for c in chunks
            ]
        elif "app-overview-rag" in str(path):
            chunks = [
                IndexedChunk(
                    chunk_id=c.chunk_id,
                    virtual_uri=c.virtual_uri,
                    text=c.text,
                    path=c.path,
                    doc_type="app_overview_faq",
                    section=c.section,
                    product_name=c.product_name,
                    score_hint=max(c.score_hint, 1.5),
                )
                for c in chunks
            ]
        elif "enterprise-overview-rag" in str(path):
            chunks = [
                IndexedChunk(
                    chunk_id=c.chunk_id,
                    virtual_uri=c.virtual_uri,
                    text=c.text,
                    path=c.path,
                    doc_type="enterprise_faq",
                    section=c.section,
                    product_name=c.product_name,
                    score_hint=max(c.score_hint, 1.5),
                )
                for c in chunks
            ]
        elif "legal-crossdoc-rag" in str(path):
            chunks = [
                IndexedChunk(
                    chunk_id=c.chunk_id,
                    virtual_uri=c.virtual_uri,
                    text=c.text,
                    path=c.path,
                    doc_type="legal_crossdoc_faq",
                    section=c.section,
                    product_name=c.product_name,
                    score_hint=max(c.score_hint, 1.5),
                )
                for c in chunks
            ]
        if path.name == "changelog-digest.json":
            chunks = [
                IndexedChunk(
                    chunk_id=c.chunk_id,
                    virtual_uri=c.virtual_uri,
                    text=c.text,
                    path=c.path,
                    doc_type=c.doc_type,
                    section=c.section,
                    product_name=c.product_name,
                    score_hint=2.0,
                )
                for c in chunks
            ]
        out.extend(chunks)
    return out


def get_bm25_index(namespace: str) -> BM25Index:
    cached = _INDEX.get(namespace)
    if cached is not None:
        return cached

    should_build = False
    with _INDEX_LOCK:
        cached = _INDEX.get(namespace)
        if cached is not None:
            return cached
        if namespace not in _INDEX_BUILDING:
            _INDEX_BUILDING.add(namespace)
            should_build = True

    if not should_build:
        deadline = time.time() + 120.0
        while time.time() < deadline:
            cached = _INDEX.get(namespace)
            if cached is not None:
                return cached
            time.sleep(0.05)
        with _INDEX_LOCK:
            cached = _INDEX.get(namespace)
            if cached is not None:
                return cached
            if namespace not in _INDEX_BUILDING:
                _INDEX_BUILDING.add(namespace)
                should_build = True

    if should_build:
        idx = BM25Index()
        if namespace == "medicine":
            idx.build(_build_medicine_chunks())
        elif namespace == "concierge":
            idx.build(_build_concierge_chunks())
        else:
            idx.build([])
        with _INDEX_LOCK:
            _INDEX_BUILDING.discard(namespace)
            existing = _INDEX.get(namespace)
            if existing is not None:
                return existing
            _INDEX[namespace] = idx
            logger.info(
                "Local RAG BM25 index %s: %d chunks", namespace, len(idx.chunks)
            )
            return idx

    empty = BM25Index()
    empty.build([])
    return empty


def clear_bm25_index() -> None:
    with _INDEX_LOCK:
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
