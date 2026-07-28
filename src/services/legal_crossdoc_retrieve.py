"""法務横断 FAQ（legal-crossdoc-rag）の intent 別・質問別 retrieve。"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

_LEGAL_CROSSDOC_URI = "local/concierge/rag/legal-crossdoc-rag"

_COMPARISON_RAG_QUERY = "プライバシーポリシーと利用規約の違い 法務横断 境界"

# (pattern, retrieval hint) — user_text にマッチした hint を retrieve クエリへ追加
_LEGAL_FAQ_QUERY_HINTS: Tuple[Tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"違い|比較|どっち|境界|"
            r"(?:プライバシー|プラポリ).*(?:規約|免責)|(?:規約|免責).*(?:プライバシー|プラポリ)",
            re.I,
        ),
        "プライバシーポリシーと利用規約の違い 法務横断",
    ),
    (
        re.compile(r"削除|消して|忘れて|訂正|開示請求|データ削除", re.I),
        "データの削除 訂正 開示請求 権利",
    ),
    (
        re.compile(r"会話|履歴|チャット.*残|保存.*残", re.I),
        "会話履歴 チャット 保存 削除 セッション",
    ),
    (
        re.compile(r"どんなデータ|何を保存|収集|取得.*情報|個人情報.*取り", re.I),
        "データ 保存 取得 収集 情報 症状 ログ",
    ),
    (
        re.compile(r"第三者|提供|共有|売却|外部.*渡", re.I),
        "第三者 提供 共有 売却 外部",
    ),
    (
        re.compile(r"匿名加工|匿名化|統計.*利用", re.I),
        "匿名加工 匿名化 統計",
    ),
    (
        re.compile(r"医療免責|診断.*しない|診断.*理由|医療.*免責", re.I),
        "医療免責 診断 しない 理由 参考",
    ),
    (
        re.compile(r"薬機法|合法|違法|問題ない|大丈夫.*法令", re.I),
        "薬機法 合法 違法 問題ない 法令 遵守",
    ),
    (
        re.compile(r"禁止|してはいけない|転送|商用.*利用", re.I),
        "禁止 禁止事項 転送 商用 規約",
    ),
    (
        re.compile(r"試験運用|β|ベータ|保証|変更.*停止", re.I),
        "試験運用 β 保証 変更 停止",
    ),
    (
        re.compile(r"開示ポリシー|Concierge.*規約|チャット.*規約.*関係", re.I),
        "開示 ポリシー Concierge 規約 関係",
    ),
    (
        re.compile(r"人間|オペレーター|運営者.*案内|エスカレ|薬剤師要請", re.I),
        "人間 オペレーター 運営者 エスカレーション 削除依頼",
    ),
    (
        re.compile(r"ℹ️|モーダル|チャット.*違い|全文.*表示", re.I),
        "モーダル ℹ️ チャット 規約 表示 カード",
    ),
)

_INTENT_FAQ_HINTS: Dict[str, str] = {
    "doc_privacy": "プライバシー 個人情報 データ 削除 第三者",
    "doc_terms": "利用規約 免責 禁止 試験運用 医療",
    "doc_operator": "問い合わせ 運営者 削除依頼 不具合 連絡先",
}


def _is_public_legal_md_chunk(chunk: str) -> bool:
    c = (chunk or "").strip()
    return c.startswith("🔒") or c.startswith("🧾") or c.startswith("第1条（")


def _extract_chunk_section(chunk: str) -> str:
    m = re.search(r"\[section:\s*Q:\s*([^\]]+)\]", chunk or "")
    return (m.group(1).strip() if m else "")


def _extract_chunk_keywords(chunk: str) -> List[str]:
    m = re.search(r"\[keywords:\s*([^\]]+)\]", chunk or "")
    if not m:
        return []
    return [k.strip() for k in m.group(1).split() if k.strip()]


def build_legal_crossdoc_retrieval_query(
    user_text: str,
    intent: str = "",
    *,
    comparison: bool = False,
) -> str:
    """質問内容 + intent から legal-crossdoc FAQ 向け retrieve クエリを組み立てる。"""
    if comparison:
        return _COMPARISON_RAG_QUERY

    parts: List[str] = []
    cleaned = (user_text or "").strip()
    if cleaned:
        parts.append(cleaned)

    intent_key = (intent or "").strip().lower()
    intent_hint = _INTENT_FAQ_HINTS.get(intent_key)
    if intent_hint:
        parts.append(intent_hint)

    matched_hint = ""
    for pattern, hint in _LEGAL_FAQ_QUERY_HINTS:
        if pattern.search(cleaned):
            matched_hint = hint
            break

    if matched_hint:
        parts.append(matched_hint)

    try:
        from src.services.concierge_intent import is_legal_crossdoc_comparison_question

        if is_legal_crossdoc_comparison_question(cleaned):
            parts.append(_COMPARISON_RAG_QUERY)
    except ImportError:
        pass

    merged = " ".join(dict.fromkeys(parts)).strip()
    try:
        from src.services.concierge_tech_synonyms import expand_concierge_query

        return expand_concierge_query(merged)
    except ImportError:
        return merged


def score_legal_crossdoc_chunk(user_text: str, chunk: str, *, comparison: bool = False) -> float:
    """FAQ チャンクと user_text の関連度（大きいほど優先）。"""
    c = chunk or ""
    ut = (user_text or "").strip()
    if not c:
        return -999.0
    if _is_public_legal_md_chunk(c):
        return -100.0

    score = 0.0
    section = _extract_chunk_section(c)
    keywords = _extract_chunk_keywords(c)

    if comparison and "プライバシーポリシーと利用規約の違い" in section:
        score += 100.0

    for token in re.findall(r"[\u3040-\u9fff]{2,}|[A-Za-z]{3,}", ut):
        if token in section:
            score += 12.0
        elif token in c:
            score += 1.0

    for pattern, hint in _LEGAL_FAQ_QUERY_HINTS:
        if pattern.search(ut):
            for token in hint.split():
                if len(token) >= 2 and token in section:
                    score += 6.0
                elif len(token) >= 2 and token in c:
                    score += 1.5

    for kw in keywords:
        if kw and kw in ut:
            score += 5.0
        elif kw and len(kw) >= 2 and re.search(re.escape(kw), ut, re.I):
            score += 3.0

    if "[section:" in c:
        score += 1.0

    return score


def select_legal_crossdoc_chunks(
    user_text: str,
    chunks: List[str],
    *,
    comparison: bool = False,
    max_chunks: int = 2,
) -> List[str]:
    """public md を除き、質問に最も関連する FAQ チャンクを選ぶ。"""
    filtered = [c for c in chunks if not _is_public_legal_md_chunk(c)]
    if not filtered:
        filtered = list(chunks)

    ranked = sorted(
        filtered,
        key=lambda c: (-score_legal_crossdoc_chunk(user_text, c, comparison=comparison), len(c)),
    )

    if comparison:
        q1 = [c for c in ranked if "プライバシーポリシーと利用規約の違い" in _extract_chunk_section(c)]
        if q1:
            return q1[:1]

    return ranked[: max(1, max_chunks)]


def should_prioritize_legal_crossdoc_faq(user_text: str, intent: str = "") -> bool:
    """legal-crossdoc FAQ を public md より優先すべき retrieve か。"""
    cleaned = (user_text or "").strip()
    if not cleaned:
        return False
    try:
        from src.services.concierge_intent import is_legal_crossdoc_comparison_question

        if is_legal_crossdoc_comparison_question(cleaned):
            return True
    except ImportError:
        pass

    intent_key = (intent or "").strip().lower()
    if intent_key not in ("doc_privacy", "doc_terms", "doc_operator"):
        return False

    for pattern, _ in _LEGAL_FAQ_QUERY_HINTS:
        if pattern.search(cleaned):
            return True
    return False


def _all_legal_crossdoc_faq_chunk_texts() -> List[str]:
    from src.services.local_rag_index import get_bm25_index

    idx = get_bm25_index("concierge")
    return [c.text for c in idx.chunks if c.virtual_uri.startswith(_LEGAL_CROSSDOC_URI)]


def retrieve_legal_crossdoc_faq(
    user_text: str,
    intent: str = "",
    *,
    comparison: bool = False,
    top_k: int = 12,
    max_chunks: int = 2,
) -> Dict[str, Any]:
    """legal-crossdoc-rag から質問に合う FAQ チャンクを retrieve。"""
    from src.services.bedrock_kb_retrieve import retrieve_concierge_context

    query = build_legal_crossdoc_retrieval_query(
        user_text,
        intent,
        comparison=comparison,
    )
    result = retrieve_concierge_context(
        query,
        top_k=top_k,
        intent=intent or "doc_privacy",
        uri_prefixes=(_LEGAL_CROSSDOC_URI,),
        use_cache=False,
    )
    chunks = list(result.get("chunks") or [])
    pool = list(dict.fromkeys(chunks + _all_legal_crossdoc_faq_chunk_texts()))
    selected = select_legal_crossdoc_chunks(
        user_text,
        pool,
        comparison=comparison,
        max_chunks=max_chunks,
    )
    uris = [u for u in (result.get("source_uris") or []) if _LEGAL_CROSSDOC_URI in u]
    out = dict(result)
    out["chunks"] = selected
    out["chunk_count"] = len(selected)
    out["source_uris"] = uris or ([f"{_LEGAL_CROSSDOC_URI}.md"] if selected else [])
    out["legal_crossdoc_query"] = query
    return out


def format_legal_crossdoc_faq_block(
    result: Dict[str, Any],
    *,
    heading: str = "【法務横断 FAQ（補助・条項創作禁止）】",
) -> str:
    from src.services.bedrock_kb_retrieve import format_kb_context_block

    return format_kb_context_block(result, heading=heading)


def augment_doc_reference_with_legal_faq(
    user_text: str,
    intent: str,
    base_reference: str,
    *,
    comparison: bool = False,
) -> str:
    """
    doc_privacy / doc_terms / doc_operator 向け。
    正本 md（base_reference）の後に、関連 FAQ を補助参照として付与する。
    """
    base = (base_reference or "").strip()
    if not base:
        return base

    result = retrieve_legal_crossdoc_faq(
        user_text,
        intent,
        comparison=comparison,
        max_chunks=2 if comparison else 1,
    )
    if not result.get("chunks"):
        return base

    heading = (
        "【法務横断 FAQ（比較の補助・条項創作禁止）】"
        if comparison
        else "【法務横断 FAQ（補助・正本は上記ドキュメント）】"
    )
    block = format_legal_crossdoc_faq_block(result, heading=heading)
    if not block:
        return base
    return f"{base}\n\n---\n\n{block.rstrip()}"
