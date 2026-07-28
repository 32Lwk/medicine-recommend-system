"""legal-crossdoc RAG インデックスの chunk keywords テスト。"""
from __future__ import annotations

from src.services.local_rag_index import clear_bm25_index, get_bm25_index


def test_legal_crossdoc_chunks_have_section_specific_keywords():
    clear_bm25_index()
    idx = get_bm25_index("concierge")
    by_section = {
        c.section: c.text
        for c in idx.chunks
        if c.virtual_uri.startswith("local/concierge/rag/legal-crossdoc-rag")
    }
    assert "Q: プライバシーポリシーと利用規約の違いは何ですか" in by_section
    assert "Q: いつ人間オペレーター（運営者）に案内すべきですか" in by_section

    q1 = by_section["Q: プライバシーポリシーと利用規約の違いは何ですか"]
    op = by_section["Q: いつ人間オペレーター（運営者）に案内すべきですか"]

    assert "違い 規約 ポリシー" in q1
    assert "人間 オペレーター 運営者" in op
    assert "違い 規約 ポリシー" not in op
