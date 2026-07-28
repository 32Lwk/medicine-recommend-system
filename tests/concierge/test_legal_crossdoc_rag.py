"""法務横断 FAQ retrieve のテスト。"""
from __future__ import annotations

import pytest

from src.services.local_rag_index import clear_bm25_index


@pytest.fixture(autouse=True)
def _fresh_concierge_rag_index():
    clear_bm25_index()
    yield
    clear_bm25_index()


from src.agents.concierge_agent import _build_legal_crossdoc_reference, _retrieve_legal_crossdoc_rag
from src.services.legal_crossdoc_retrieve import (
    _extract_chunk_section,
    _is_public_legal_md_chunk,
    augment_doc_reference_with_legal_faq,
    build_legal_crossdoc_retrieval_query,
    retrieve_legal_crossdoc_faq,
    score_legal_crossdoc_chunk,
    select_legal_crossdoc_chunks,
)
from src.services.bedrock_kb_retrieve import retrieve_concierge_context


@pytest.mark.parametrize(
    "query,expected_section_part,intent",
    [
        ("免責事項・利用規約（β版）とプライバシーの違いは？", "プライバシーポリシーと利用規約の違い", "doc_privacy"),
        ("データ削除を依頼したい", "削除", "doc_privacy"),
        ("会話履歴は残りますか", "会話履歴", "doc_privacy"),
        ("禁止事項を教えて", "禁止事項", "doc_terms"),
        ("β版 試験運用 保証", "試験運用", "doc_terms"),
        ("医療免責 診断しない理由", "医療免責", "doc_terms"),
        ("薬機法 合法ですか", "薬機法", "doc_terms"),
        ("いつ人間オペレーターに案内", "人間オペレーター", "doc_operator"),
    ],
)
def test_retrieve_legal_crossdoc_faq_matches_topic(query, expected_section_part, intent):
    result = retrieve_legal_crossdoc_faq(query, intent)
    chunks = result.get("chunks") or []
    assert chunks, f"no chunks for {query!r}"
    section = _extract_chunk_section(chunks[0])
    assert expected_section_part in section or expected_section_part in chunks[0], (
        f"query={query!r} section={section!r}"
    )
    assert not _is_public_legal_md_chunk(chunks[0])


def test_retrieve_legal_crossdoc_rag_prefers_q1():
    q = "免責事項・利用規約（β版）とプライバシーの違いは？"
    result = _retrieve_legal_crossdoc_rag(q)
    chunks = result.get("chunks") or []
    assert chunks
    assert "プライバシーポリシーと利用規約の違い" in _extract_chunk_section(chunks[0])


def test_local_rag_prioritizes_crossdoc_for_deletion():
    q = "データ削除を依頼したい"
    r = retrieve_concierge_context(q, top_k=2, intent="doc_privacy")
    uris = r.get("source_uris") or []
    assert uris
    assert "legal-crossdoc-rag" in uris[0]
    assert not _is_public_legal_md_chunk((r.get("chunks") or [""])[0])


def test_build_legal_crossdoc_reference_includes_q1_faq():
    q = "免責事項・利用規約（β版）とプライバシーの違いは？"
    ref = _build_legal_crossdoc_reference(q)
    assert "法務横断 FAQ" in ref
    assert "プライバシーポリシーと利用規約の違い" in ref
    assert "要点抜粋" in ref


def test_augment_doc_reference_appends_faq_block():
    base = "🔒 プライバシーポリシー（試験運用版）\n第7条"
    out = augment_doc_reference_with_legal_faq("データ削除を依頼したい", "doc_privacy", base)
    assert out.startswith(base)
    assert "法務横断 FAQ（補助" in out
    assert "削除" in out


def test_build_legal_crossdoc_retrieval_query_enriches_deletion():
    q = build_legal_crossdoc_retrieval_query("データ削除を依頼したい", "doc_privacy")
    assert "削除" in q
    assert "プライバシー" in q


def test_select_legal_crossdoc_chunks_ranks_by_keywords():
    chunks = [
        "[section: Q: 利用規約の禁止事項は何ですか]\n[keywords: 禁止 禁止事項]",
        "[section: Q: データの削除・訂正・開示請求はできますか]\n[keywords: 削除 訂正 開示]",
    ]
    selected = select_legal_crossdoc_chunks("データ削除を依頼したい", chunks)
    assert "削除" in _extract_chunk_section(selected[0])


def test_normalize_legal_crossdoc_info_hint_strips_inline_emoji():
    from src.agents.concierge_agent import (
        _LEGAL_CROSSDOC_INFO_HINT,
        _normalize_legal_crossdoc_info_hint,
    )

    raw = (
        "迷ったときは、データをどう扱うかが気になるならプライバシーポリシー、"
        "サービスの利用条件や責任の範囲が知りたいなら利用規約・免責、"
        "と考えると分かりやすいです。ℹ️ それぞれの全文もあわせて確認できます。"
    )
    out = _normalize_legal_crossdoc_info_hint(raw)
    assert "ℹ️ それぞれ" not in out
    assert out.count("ℹ️") == 1
    assert out.endswith(_LEGAL_CROSSDOC_INFO_HINT)
    assert " の ℹ️ " not in out
    assert out.count(_LEGAL_CROSSDOC_INFO_HINT) == 1
    assert "迷ったときは" in out.split("\n\n")[0]


def test_normalize_legal_crossdoc_info_hint_dedupes_llm_footer():
    from src.agents.concierge_agent import (
        _LEGAL_CROSSDOC_INFO_HINT,
        _normalize_legal_crossdoc_info_hint,
    )

    raw = (
        "プライバシーポリシーはデータの扱いを定めます。\n\n"
        "利用規約・免責は使い方と責任の範囲を定めます。\n\n"
        f"{_LEGAL_CROSSDOC_INFO_HINT}"
    )
    out = _normalize_legal_crossdoc_info_hint(raw)
    paras = [p for p in out.split("\n\n") if p.strip()]
    assert paras[-1] == _LEGAL_CROSSDOC_INFO_HINT
    assert out.count(_LEGAL_CROSSDOC_INFO_HINT) == 1
    assert "詳細は画面右上の から" not in out


def test_score_legal_crossdoc_chunk_prefers_keyword_overlap():
    chunk = "[section: Q: データの削除・訂正・開示請求はできますか]\n[keywords: 削除 訂正 開示]"
    assert score_legal_crossdoc_chunk("データ削除を依頼したい", chunk) > score_legal_crossdoc_chunk(
        "禁止事項を教えて", chunk
    )
